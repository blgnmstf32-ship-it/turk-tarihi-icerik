import json
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import scene_director, scene_otio
from scripts.editorial_state import EditorialState


def history(identifier="piri-reis-kayip-kaynak"):
    return scene_director._load_topic("tarih", identifier, None)


def beauty():
    return scene_director._load_topic("bakim", "kuruluk-nemlendirici-zamani", None)


class ScenePlanTests(unittest.TestCase):
    def test_history_plan_keeps_exact_narration_and_contiguous_frames(self):
        topic = history()
        plan = scene_director.build_plan("tarih", topic, overrides={"3": {"source_numbers": [1]}})
        scenes = plan["scenes"]
        self.assertEqual([row["narration"]["text"] for row in scenes], topic["narration"])
        self.assertEqual((plan["fps"], scenes[0]["start_frame"], scenes[0]["end_frame"], scenes[-1]["end_frame"]),
                         (30, 0, 75, 2100))
        self.assertEqual([row["end_frame"] for row in scenes[:-1]], [row["start_frame"] for row in scenes[1:]])
        self.assertEqual(scenes[2]["narration"]["source_numbers"], [1])
        self.assertEqual(scenes[0]["narration"]["candidate_source_numbers"], [1])
        self.assertEqual(plan["sources"][0]["url"], topic["sources"][0]["url"])
        self.assertEqual(scenes[0]["render"]["primary"]["id"], "media:hyperframes")
        self.assertEqual(scenes[2]["render"]["primary"]["id"], "media:three-js")
        self.assertEqual(scenes[2]["kind"], "map")
        self.assertLessEqual(scenes[2]["render"]["illustration_frames"], 270)
        self.assertEqual([x["id"] for x in scenes[2]["skills"]],
                         ["openmontage:storyboard", "cinecode:camera-cut-continuity"])
        self.assertEqual(scenes[2]["transition_in"], "s02--s03")
        self.assertEqual(scenes[2]["visual_assets"][0]["rights_status"], "pending")

    def test_historical_mechanism_and_city_use_distinct_camera_plans(self):
        options = [("antikythera-disli", "mechanism"), ("ani-belgesel", "city")]
        scenes = [scene_director.build_plan("tarih", history(topic_id))["scenes"][2] for topic_id, _ in options]
        self.assertEqual([row["kind"] for row in scenes], [kind for _, kind in options])
        self.assertNotEqual(scenes[0]["camera"], scenes[1]["camera"])
        self.assertTrue(all(row["visual_assets"][0]["label"] == "TEMSİLÎ CANLANDIRMA" for row in scenes))

    def test_beauty_diagram_and_different_routine_have_different_treatments(self):
        topic = beauty()
        plan = scene_director.build_plan("bakim", topic)
        routine = {**topic, "id": "nazik-rutin", "title": "Nazik bakım rutini", "visual_mode": "2d"}
        other = scene_director.build_plan("bakim", routine)
        self.assertEqual([row["captions"]["text"] for row in plan["scenes"]], topic["script"])
        self.assertEqual(plan["scenes"][2]["narration"]["voice"], "Sulafat")
        self.assertEqual(plan["scenes"][2]["render"]["primary"]["id"], "media:blender")
        self.assertEqual(plan["scenes"][4]["render"]["primary"]["id"], "media:three-js")
        self.assertEqual(other["scenes"][2]["render"]["primary"]["id"], "media:remotion")
        self.assertIn("cinecode:motivated-light", [x["id"] for x in plan["scenes"][2]["skills"]])
        self.assertEqual(plan["timing"], "estimated_from_script")
        self.assertEqual(plan["scenes"][2]["sound"]["priority"], "narration")

    def test_invalid_source_or_unreviewed_visual_cannot_be_bound(self):
        asset = {"id": "map-record", "kind": "archive", "source_number": 1, "sha256": "a" * 64,
                 "attribution": "Test reference", "license": "CC-BY-4.0", "commercial_use_reviewed": True}
        plan = scene_director.build_plan("tarih", history(), overrides={"1": {"assets": [asset]}})
        self.assertEqual(plan["scenes"][0]["visual_assets"][0]["rights_status"], "declared_reviewed")
        for bad in ({"2": {"source_numbers": [99]}}, {"3": {"assets": [asset]}},
                    {"1": {"assets": [{**asset, "license": "CC-BY-NC-4.0"}]}},
                    {"1": {"assets": [{**asset, "path": "incoming-map.png"}]}},
                    {"1": {"assets": [{**asset, "commercial_use_reviewed": False}]}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                scene_director.build_plan("tarih", history(), overrides=bad)

    def test_otio_is_optional_and_rejects_an_unpinned_version(self):
        plan = scene_director.build_plan("tarih", history())
        with patch("scripts.scene_otio.version", side_effect=PackageNotFoundError):
            with self.assertRaisesRegex(RuntimeError, "optional pinned"):
                scene_otio.timeline_json(plan)
        with patch("scripts.scene_otio.version", return_value="0.20.0"):
            with self.assertRaisesRegex(RuntimeError, "0.18.1"):
                scene_otio.timeline_json(plan)


class SceneExecutionTests(unittest.TestCase):
    def setUp(self):
        work = TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.output = Path(work.name)
        self.state = EditorialState(self.output / "existing.sqlite3")
        self.plan = scene_director.build_plan("bakim", beauty())

    def test_actual_local_adapter_is_recorded_separately_from_unrun_renderer(self):
        with (patch("socket.socket.connect", side_effect=AssertionError("network")),
              patch("subprocess.Popen", side_effect=AssertionError("process"))):
            report = scene_director.preflight(self.plan, self.state)
        opening = report["scenes"]["s01"]
        self.assertEqual(opening["local_preflight"]["opening_preset"]["effect"], "lines-reveal")
        self.assertEqual(opening["local_preflight"]["executed_tools"], [{"id": "media:opening-presets",
                         "entrypoint": "scripts/motion_toolkit.py:select_opening_effect"}])
        self.assertEqual(report["scenes"]["s03"]["planned_renderer"], "media:blender")
        self.assertTrue(all(row["render_status"] == "not_run" and row["executed_renderer"] is None
                            for row in report["scenes"].values()))
        self.assertFalse(report["quality"]["actual_media_checked"])
        self.assertFalse(report["quality"]["scene_count_meets_release_minimum"])

    def test_recovery_rechecks_only_failed_scene_and_two_adjacent_cuts(self):
        first = scene_director.preflight(self.plan, self.state)
        with patch.object(scene_director, "_local_preflight", wraps=scene_director._local_preflight) as check:
            report = scene_director.preflight(self.plan, self.state, previous_id=first["report_sha256"],
                                              failures={"s03": "render_failed"})
        self.assertEqual([call.args[1]["id"] for call in check.call_args_list], ["s03"])
        self.assertEqual(report["evaluated_scene_ids"], ["s03"])
        self.assertEqual(report["evaluated_transition_ids"], ["s02--s03", "s03--s04"])
        self.assertEqual(report["scenes"]["s03"]["selected_renderer"], "media:remotion")
        self.assertEqual(report["scenes"]["s03"]["decision"], "fallback_planned")
        self.assertIsNone(report["scenes"]["s03"]["executed_renderer"])
        self.assertEqual(report["scenes"]["s01"]["evaluation"], "reused_previous")
        self.assertEqual(report["scenes"]["s01"]["local_preflight"]["executed_tools"], [])
        self.assertEqual(report["transitions"]["s01--s02"]["evaluation"], "reused_previous")

    def test_boundary_rechecks_dedupe_and_rights_problem_stops_selection(self):
        first = scene_director.preflight(self.plan, self.state)
        report = scene_director.preflight(self.plan, self.state, previous_id=first["report_sha256"],
                                          failures={"s03": "rights_unverified", "s04": "source_unverified"})
        self.assertEqual(report["evaluated_transition_ids"], ["s02--s03", "s03--s04", "s04--s05"])
        self.assertIsNone(report["transitions"]["s02--s03"]["method"])
        self.assertEqual(report["scenes"]["s03"]["decision"], "needs_human_review")
        self.assertIsNone(report["scenes"]["s03"]["selected_renderer"])

    def test_missing_and_repeated_fallback_stop_without_a_renderer_attempt(self):
        no_local = scene_director.preflight(self.plan, self.state, available=set())
        self.assertEqual(no_local["scenes"]["s03"]["decision"], "no_safe_fallback")
        first = scene_director.preflight(self.plan, self.state)
        second = scene_director.preflight(self.plan, self.state, previous_id=first["report_sha256"],
                                          failures={"s03": "renderer_unavailable"})
        third = scene_director.preflight(self.plan, self.state, previous_id=second["report_sha256"],
                                         failures={"s03": "render_failed"})
        self.assertEqual(third["scenes"]["s03"]["decision"], "no_safe_fallback")
        self.assertIsNone(third["scenes"]["s03"]["executed_renderer"])

    def test_identical_preflight_reuses_sqlite_and_changed_plan_rejects_prior_receipt(self):
        first = scene_director.preflight(self.plan, self.state)
        with patch.object(scene_director, "run_tool", side_effect=AssertionError("cached tool reran")):
            second = scene_director.preflight(self.plan, EditorialState(self.state.path))
        self.assertEqual(second["scenes"]["s01"]["local_preflight"]["cache"], "hit")
        self.assertEqual(second["scenes"]["s01"]["local_preflight"]["executed_tools"], [])
        revised = scene_director.build_plan("bakim", beauty(), duration_frames=2110)
        with self.assertRaisesRegex(ValueError, "No prior report matches"):
            scene_director.preflight(revised, self.state, previous_id=first["report_sha256"],
                                     failures={"s03": "render_failed"})

    def test_cli_writes_only_plan_and_preflight_reports_and_can_resume(self):
        argv = ["--brand", "tarih", "--topic", "antikythera-disli", "--out", str(self.output)]
        with patch("builtins.print"):
            scene_director.main(argv)
            failed = self.output / "failed.json"
            failed.write_text('{"s03":"renderer_unavailable"}', encoding="utf-8")
            scene_director.main([*argv, "--failures", str(failed)])
        plan = json.loads((self.output / scene_director.PLAN).read_text())
        report = json.loads((self.output / scene_director.REPORT).read_text())
        self.assertFalse(plan["instagram_auto_publish"])
        self.assertFalse(report["media_created"])
        self.assertEqual(report["evaluated_scene_ids"], ["s03"])
        self.assertEqual(report["api_calls"], 0)
        self.assertFalse(any(path.suffix in {".wav", ".mp4", ".png"} for path in self.output.iterdir()))
