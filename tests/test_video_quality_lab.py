import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import scene_director, video_quality_lab as lab
from scripts.editorial_state import EditorialState
from scripts.skill_registry import registry_view
from scripts.skill_router import RouteContext
from scripts.tool_router import run_tool


def row(check, values=None, **scope):
    return {"collector": lab.RULES[check][0], "values": values, **scope}


class VideoQualityLabTest(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name)
        self.state = EditorialState(self.out / "state.sqlite3")
        self.history = scene_director._load_topic("tarih", "piri-reis-kayip-kaynak", None)
        self.beauty = scene_director._load_topic("bakim", "kuruluk-nemlendirici-zamani", None)

    def evidence(self, plan, observations=None, reviews=None):
        return {"plan_sha256": scene_director._digest(plan), "observations": observations or {},
                "source_reviews": reviews or []}

    def test_unmeasured_from_both_brands_and_router_cache(self):
        for brand, topic in (("tarih", self.history), ("bakim", self.beauty)):
            plan = scene_director.build_plan(brand, topic)
            first, _ = lab.evaluate(plan, state=self.state, topic=topic)
            second, _ = lab.evaluate(plan, state=self.state)
            self.assertEqual(first["technical"]["status"], "not_measured")
            self.assertTrue(all(r["status"] == "not_measured" for r in first["technical"]["checks"].values()))
            self.assertNotIn("score", first["technical"]["vmaf"])
            self.assertEqual(first["editorial"]["threshold"], 85)
            self.assertEqual(first["editorial"]["hook_candidates"], 5)
            self.assertEqual(first["editorial"]["scenario_candidates"], 3)
            self.assertEqual(first["instagram_performance"]["status"], "insufficient_real_data")
            self.assertEqual(first["tool_route"]["executed_adapter"]["id"], lab.TOOL_ID)
            self.assertEqual(second["tool_route"]["status"], "cache")
            self.assertIsNone(second["tool_route"]["executed_adapter"])

    def test_report_keeps_all_three_axes_and_does_not_score_missing_source_reviews(self):
        plan = scene_director.build_plan("bakim", self.beauty)
        passing = {name: [row(name, {key: (lo + hi) / 2 for key, (lo, hi) in limits.items()})]
                   for name, (_, limits) in lab.RULES.items()}
        topic = {**self.beauty, "editorial_checks": {"scientific_accuracy": "blocked"}}
        report, _ = lab.evaluate(plan, evidence=self.evidence(plan, passing), topic=topic)
        self.assertEqual(report["technical"]["status"], "pass")
        self.assertEqual(report["editorial"]["status"], "blocked_by_editorial_safety")
        self.assertEqual(report["editorial"]["source_accuracy"]["status"], "not_reviewed")
        self.assertFalse(report["editorial"]["score_is_viral_probability"])
        self.assertTrue(report["human_approval_required"])

    def test_source_and_sync_only_recheck_affected_scenes_and_cuts(self):
        plan = scene_director.build_plan("tarih", self.history)
        before = scene_director.preflight(plan, self.state)
        s4 = plan["scenes"][3]
        observations = {"subtitle_sync": [row("subtitle_sync", {"matched_fraction": 0.95, "p95_offset_ms": 420},
                                             frames=[s4["start_frame"], s4["end_frame"]])],
                        "audio_balance": [row("audio_balance", {"integrated_lufs": -24, "true_peak_dbtp": -2,
                                                              "voice_over_bed_db": 4})]}
        evidence = self.evidence(plan, observations, [{"scene_id": "s02", "status": "unverified",
                                                       "finding": "İddia için kaynak pasajı eksik."}])
        report, after = lab.evaluate(plan, evidence=evidence, state=self.state, previous_id=before["report_sha256"])
        self.assertEqual(report["scene_recheck"]["failures"], {"s02": "source_unverified", "s04": "sync_failed"})
        self.assertEqual(report["scene_recheck"]["unlocated_checks"], ["audio_balance"])
        self.assertEqual(after["evaluated_scene_ids"], ["s02", "s04"])
        adjacent = [cut["id"] for cut in plan["transitions"]
                    if {"s02", "s04"}.intersection((cut["left"], cut["right"]))]
        self.assertEqual(after["evaluated_transition_ids"], adjacent)
        self.assertTrue(all(scene["render_status"] == "not_run" for scene in after["scenes"].values()))
        self.assertEqual(after["scenes"]["s01"]["evaluation"], "reused_previous")

    def test_single_transition_targets_two_sides_and_clean_subset_is_partial(self):
        plan = scene_director.build_plan("bakim", self.beauty)
        cut = plan["transitions"][2]
        checks = {"transitions": [row("transitions", {"max_boundary_error_frames": 8, "unexpected_cuts": 0},
                                      transition_id=cut["id"], frames=[cut["frame"], cut["frame"]+1])],
                  "mobile_readability": [row("mobile_readability", {"safe_area_violations": 0,
                                                                  "min_contrast_ratio": 5}, frames=[0, 90])]}
        report, after = lab.evaluate(plan, evidence=self.evidence(plan, checks))
        self.assertIsNone(after)
        self.assertEqual(report["scene_recheck"]["failures"], {cut["left"]: "quality_failed",
                                                                cut["right"]: "quality_failed"})
        self.assertEqual(report["technical"]["checks"]["mobile_readability"]["status"], "partial")

    def test_invalid_or_untrusted_inputs_do_not_pass(self):
        plan = scene_director.build_plan("bakim", self.beauty)
        bad = ({"plan_sha256": "wrong"}, self.evidence(plan, {"shell": ["ignored"]}),
               self.evidence(plan, {"opening": [row("opening", {"first_picture_frame": float("nan"),
                                                                "first_word_frame": 1})]}),
               self.evidence(plan, {"vmaf": {"collector": "ffmpeg-libvmaf", "score": 100, "aligned": False}}),
               self.evidence(plan, reviews=[{"scene_id": "s01", "status": "verified", "source_numbers": [999],
                                            "finding": "Bağlantı yok"}]))
        for evidence in bad:
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                lab.evaluate(plan, evidence=evidence, state=self.state)
        blocked = run_tool(RouteContext("bakim", 1, "video-quality"), topic=plan["topic"], state=self.state,
                           preferred=lab.TOOL_ID, snapshots={lab.TOOL_ID: {"plan": plan}})
        self.assertEqual(blocked["rejected"][0]["reason"], "role_not_allowed")
        self.assertIsNone(blocked["executed_adapter"])

    def test_detector_candidates_require_review_and_vmaf_is_reference_bound(self):
        plan = scene_director.build_plan("bakim", self.beauty)
        log = "[freezedetect] freeze_start: 2\nfreeze_end: 3\nfreeze_start: 60"
        self.assertEqual(lab._detected_intervals(log, "freeze", 2100, 30), [[60, 90], [1800, 2100]])
        evidence = self.evidence(plan, {"frozen_frames": [{"collector": "ffmpeg-freezedetect",
                                                          "candidate": True, "frames": [60, 90]}]})
        evidence["asset_sha256"] = "b" * 64
        evidence["observations"]["vmaf"] = {"collector": "ffmpeg-libvmaf", "aligned": True, "score": 91.3,
                                             "reference_sha256": "a" * 64, "distorted_sha256": evidence["asset_sha256"]}
        report, _ = lab.evaluate(plan, evidence=evidence)
        self.assertEqual(report["technical"]["status"], "needs_review")
        self.assertEqual(report["scene_recheck"]["failures"], {})
        self.assertEqual(report["technical"]["vmaf"]["status"], "measured")
        self.assertEqual(report["technical"]["vmaf"]["score"], 91.3)

    def test_existing_mp4_collector_contract_without_media_or_process(self):
        from subprocess import CompletedProcess

        plan = scene_director.build_plan("bakim", self.beauty)
        fixture = self.out / "existing.mp4"
        fixture.touch()  # only a path placeholder; the probe and decoders are mocked
        responses = [CompletedProcess([], 0, stdout=json.dumps({"streams": [{
            "width": 1080, "height": 1920, "avg_frame_rate": "30/1", "nb_frames": "2100"}]})),
                     CompletedProcess([], 0, stderr="black_start:0.4 black_end:0.7")]
        with patch.object(lab.subprocess, "run", side_effect=responses) as call:
            evidence = lab.collect_ffmpeg(fixture, plan)
        self.assertEqual(evidence["observations"]["black_frames"][0]["frames"], [12, 21])
        self.assertEqual(evidence["observations"]["frozen_frames"][0]["values"]["unexpected_frozen_frames"], 0)
        for args, options in call.call_args_list:
            self.assertIn("-protocol_whitelist", args[0])
            self.assertIn("file", args[0])
            self.assertTrue(options["check"])

    def test_performance_ignores_other_brands_and_sources(self):
        plan = scene_director.build_plan("bakim", self.beauty)
        base = {"brand": "bakim", "format": "reel", "duration_seconds": 70, "hook_family": "question",
                "published_at": "2026-01-01T01:00:00+00:00", "captured_at_utc": "2026-01-04T01:00:00+00:00",
                "source": "instagram_graph_api_read_only", "reach": 100, "saves": 12}
        fixtures = [{**base, "content_id": str(i)} for i in range(5)]
        fixtures += [{**base, "content_id": "history", "brand": "tarih", "saves": 500},
                     {**base, "content_id": "estimated", "source": "editorial_estimate", "saves": 9000}]
        report, _ = lab.evaluate(plan, performance=fixtures)
        metric = report["instagram_performance"]["cohorts"][0]["metrics"]["saves_per_reached_account"]
        self.assertEqual(metric, {"n": 5, "median": 0.12})
        self.assertEqual(report["technical"]["status"], "not_measured")

    def test_registry_preserves_baseline_and_forty_primary_roles(self):
        view = registry_view()
        self.assertEqual(len(view["entries"]), 163)
        for brand in ("tarih", "bakim"):
            roster = {role["id"] for role in view["experts"].values() if role["brand"] == brand}
            self.assertTrue(set(range(1, 21)).issubset(roster))
        self.assertEqual(view["entries"][lab.TOOL_ID]["kind"], "tool")
