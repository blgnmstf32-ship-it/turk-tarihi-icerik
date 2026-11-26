from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts import auto_produce, beauty_reel, reels_editorial, run
from scripts.instagram_insights import normalize_media_insights
from scripts.performance_learning import reels_benchmarks

ROOT = Path(__file__).resolve().parents[1]


def topic(**overrides):
    return {
        "id": "test-topic", "title": "Antik dişliler", "hook": "Tutulmayı hesaplayan antik dişliler!",
        "category": "mekanizma", "sources": [{"url": "https://example.org/source"}],
        "context": "Kaynakta görülen mekanizma", **overrides,
    }


BODY = [
    "İlk kaynaklı cümle. " * 15,
    "İkinci kaynaklı cümle. " * 15,
    "Üçüncü kaynaklı cümle. " * 15,
]


class ReelsEditorialTests(TestCase):
    def test_both_brands_compare_five_by_three_and_preserve_claims(self):
        reports = [reels_editorial.review(topic(), brand, [topic()["hook"], *BODY])
                   for brand in ("tarih", "bakim")]
        for report in reports:
            self.assertEqual(sum(report["weights"].values()), 100)
            self.assertEqual(len({row["line"] for row in report["hooks"]}), 5)
            self.assertEqual(len(report["scenarios"]), 3)
            self.assertEqual(len(report["rounds"][0]["candidates"]), 15)
            self.assertEqual(len(report["finalists"]), 15)
            self.assertFalse(report["score_is_viral_probability"])
            self.assertFalse(report["media_checked"])
            for row in report["finalists"]:
                self.assertEqual(sum(row["scores"].values()), row["total"])
                self.assertEqual([line for line in row["spoken"] if line in [claim.strip() for claim in BODY]],
                                 [claim.strip() for claim in BODY])
        self.assertNotEqual(reports[0]["scenarios"], reports[1]["scenarios"])

    def test_only_under_threshold_alternatives_are_revised(self):
        with patch.object(reels_editorial, "_score", return_value={"hook": 15}):
            report = reels_editorial.review(topic(), "tarih", BODY)
        self.assertEqual(report["status"], "needs_human_revision")
        self.assertEqual([row["revision"] for row in report["rounds"]], [0, 1, 2])
        self.assertEqual([len(row["candidates"]) for row in report["rounds"]], [15, 15, 15])
        with patch.object(reels_editorial, "_score", side_effect=lambda row, *_: {
            "hook": 0 if row["hook_family"] == "açık_soru" else 90
        }):
            mixed = reels_editorial.review(topic(), "tarih", BODY)
        self.assertEqual([len(row["candidates"]) for row in mixed["rounds"]], [15, 3, 3])

    def test_rights_and_science_block_even_when_index_passes(self):
        with TemporaryDirectory() as tmp:
            with patch.object(reels_editorial, "_score", return_value={"hook": 100}):
                with self.assertRaisesRegex(ValueError, "blocked_by_editorial_safety"):
                    reels_editorial.write_review(tmp, topic(editorial_checks={"rights": "failed",
                                                                               "scientific_accuracy": "failed"}),
                                                 "bakim", BODY, fixed_recording=True)
            report = json.loads((Path(tmp) / "REELS_EDITORIAL_REVIEW.json").read_text())
            self.assertEqual(report["best"]["total"], 100)
            self.assertEqual(report["blockers"], ["scientific_accuracy", "rights"])
            self.assertEqual(len(report["rounds"]), 1)

    def test_all_forty_legacy_roles_have_playbook_guidance(self):
        for brand, file in (("tarih", "agents.json"), ("bakim", "beauty_agents.json")):
            roles = json.loads((ROOT / "config" / file).read_text())
            roster = [role for role in roles if 1 <= role["id"] <= 20]
            self.assertEqual([r["id"] for r in roster], list(range(1, 21)))
            for role in roster:
                self.assertTrue(all(reels_editorial.specialist_guidance(role, brand).values()), role["name"])

    def test_history_saves_report_before_voice_or_images_and_blocks(self):
        data = json.loads((ROOT / "data/topics.json").read_text())[0]
        data["editorial_checks"] = {"source_claims": "blocked"}
        with TemporaryDirectory() as tmp, patch.object(auto_produce, "record"), \
                patch.object(auto_produce, "narrate") as voice, patch.object(auto_produce, "generate") as image:
            with self.assertRaisesRegex(ValueError, "blocked_by_editorial_safety"):
                auto_produce.production(data, tmp)
            self.assertTrue((Path(tmp) / "REELS_EDITORIAL_REVIEW.json").is_file())
            voice.assert_not_called()
            image.assert_not_called()

    def test_selected_history_scenario_is_the_script_sent_to_narration(self):
        data = json.loads((ROOT / "data/topics.json").read_text())[0]
        with TemporaryDirectory() as tmp, patch.object(auto_produce, "record"), \
                patch.object(auto_produce, "narrate", side_effect=RuntimeError("stop at voice")) as voice:
            with self.assertRaisesRegex(RuntimeError, "stop at voice"):
                auto_produce.production(data, tmp)
            report = json.loads((Path(tmp) / "REELS_EDITORIAL_REVIEW.json").read_text())
            self.assertFalse(report["fixed_recording"])
            self.assertEqual([row["spoken"] for row in voice.call_args.args[0]], report["best"]["spoken"])

    def test_silent_video_preview_uses_review_before_images(self):
        data = json.loads((ROOT / "data/topics.json").read_text())[0]
        with TemporaryDirectory() as tmp, patch.object(run, "render_card", side_effect=RuntimeError("stop at image")):
            with self.assertRaisesRegex(RuntimeError, "stop at image"):
                run.build(data, tmp, video=True)
            report = json.loads((Path(tmp) / "REELS_EDITORIAL_REVIEW.json").read_text())
            manifest_voiceover = (Path(tmp) / "voiceover.txt").read_text()
            self.assertEqual(len(report["finalists"]), 15)
            self.assertEqual(manifest_voiceover, " ".join(report["best"]["spoken"]))

    def test_approved_charon_path_keeps_the_exact_recorded_script(self):
        data = next(row for row in json.loads((ROOT / "data/topics.json").read_text())
                    if row["id"] == "piri-reis-kayip-kaynak")
        with TemporaryDirectory() as tmp, patch.object(auto_produce, "record"), \
                patch.object(auto_produce, "narrate", side_effect=RuntimeError("stop at voice")) as voice:
            with self.assertRaisesRegex(RuntimeError, "stop at voice"):
                auto_produce.production(data, tmp)
            self.assertEqual([row["spoken"] for row in voice.call_args.args[0]], data["narration"])
            report = json.loads((Path(tmp) / "REELS_EDITORIAL_REVIEW.json").read_text())
            self.assertTrue(report["fixed_recording"])

    def test_beauty_review_precedes_reuse_and_render(self):
        with TemporaryDirectory() as tmp, patch.object(beauty_reel, "inputs", side_effect=RuntimeError("stop at assets")), \
                patch.object(beauty_reel, "render_models") as render:
            with self.assertRaisesRegex(RuntimeError, "stop at assets"):
                beauty_reel.assemble(Path(tmp), Path(tmp))
            report = json.loads((Path(tmp) / "REELS_EDITORIAL_REVIEW.json").read_text())
            self.assertTrue(report["fixed_recording"])
            self.assertEqual(report["media_direction"]["sound"], "Sulafat")
            render.assert_not_called()

    def test_insights_compares_only_real_brand_matched_snapshots_with_coverage(self):
        first = datetime(2026, 11, 1, tzinfo=timezone.utc)
        base = {
            "source": "instagram_graph_api_read_only", "brand": "tarih", "format": "REELS",
            "published_at": first.isoformat(), "captured_at_utc": (first + timedelta(hours=72)).isoformat(),
            "duration_seconds": 60, "views": 150, "reach": 100, "shares": 10,
            "hook_family": "açık_soru", "scenario": "nesne_izinde",
        }
        rows = [{**base, "content_id": str(i)} for i in range(5)]
        rows += [{**rows[0], "shares": 20, "captured_at_utc": (first + timedelta(hours=91)).isoformat()},
                 {**rows[0], "brand": "bakim"}, {**rows[0], "source": "guess"}]
        result = reels_benchmarks(rows, "tarih")
        [cohort] = result["cohorts"]
        self.assertEqual(cohort["unique_reels"], 5)
        self.assertEqual(cohort["metrics"]["shares_per_reached_account"], {"n": 5, "median": 0.1})
        self.assertEqual(cohort["metrics"]["saves_per_reached_account"], {"n": 0, "median": None})
        self.assertEqual(reels_benchmarks(rows, "bakim")["status"], "insufficient_real_data")

    def test_normalization_carries_provenance_and_does_not_infer_units_for_learning(self):
        data = {"data": [{"name": "saved", "total_value": {"value": 0}},
                         {"name": "ig_reels_avg_watch_time", "values": [{"value": 29520}]}]}
        row = normalize_media_insights(data, {"media_id": "1", "brand": "bakim", "avg_watch_time_unit": "milliseconds"})
        self.assertEqual(row["verified_avg_watch_seconds"], 29.52)
        self.assertEqual(row["saves"], 0)
        self.assertIsNone(row["follows"])
        self.assertIsNone(normalize_media_insights(data, {})["verified_avg_watch_seconds"])
