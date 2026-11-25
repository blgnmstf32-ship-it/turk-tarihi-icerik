import json
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from scripts import daily_editorial as daily


class DailyEditorialTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = daily.load_json(daily.STORY_CATALOGUE)
        self.topics = daily.load_json(daily.TOPIC_CATALOGUE)
        self.day = date(2026, 11, 26)
        self.board = {"status": "preliminary_only", "coordinator": "AI Genel Yayın Yönetmeni",
                      "research": {}, "recommendations": [{"id": "antikythera-disli"}]}

    def test_tomorrow_and_exact_turkey_slots(self):
        after_midnight = datetime(2026, 11, 25, 21, 30, tzinfo=timezone.utc)
        self.assertEqual(daily.tomorrow(after_midnight), date(2026, 11, 27))
        statuses = [daily.day_slots(date(2026, 11, day), []) for day in range(23, 30)]
        self.assertEqual([row["reel"]["time"] for row in statuses], list(daily.REEL_TIMES))
        self.assertEqual([row["time"] for row in statuses[0]["stories"]], list(daily.STORY_TIMES))
        self.assertEqual(statuses[0]["reel"]["insights"]["status"], "insufficient_comparable_instagram_data")

    def test_optimization_uses_distinct_posts_for_same_weekday_and_format(self):
        records = [{"content_id": f"{hour}-{i}", "format": "REEL", "reach": reach,
                    "published_at": f"2026-11-{day:02}T{hour}:04:00Z"}
                   for i, day in enumerate([9, 16, 23]) for hour, reach in (("16", 100), ("17", 140))]
        suggestion = daily.timing_recommendation("19:00", 0, "REEL", records)
        self.assertEqual(suggestion["time"], "20:00")
        self.assertEqual(suggestion["status"], "recommendation_only")
        self.assertEqual(daily.timing_recommendation("19:00", 0, "REEL", records[:2]*3)["time"], "19:00")
        self.assertEqual(daily.timing_recommendation("19:00", 0, "STORY", records)["time"], "19:00")

    def test_story_history_blocks_ids_and_fact_hashes(self):
        reel = daily.choose_reel(self.topics, {}, self.board)
        first = daily.choose_stories(self.catalogue, {}, reel, self.day, {})
        following = daily.choose_stories(self.catalogue, {"2026-11-25": {"stories": first}}, reel, self.day, {})
        self.assertEqual(len({row["group"] for row in first}), 10)
        self.assertEqual({row["scope"] for row in first}, {"anadolu", "dunya"})
        self.assertFalse({row["id"] for row in first} & {row["id"] for row in following})
        self.assertFalse({row["fingerprint"] for row in first} & {row["fingerprint"] for row in following})
        with self.assertRaisesRegex(ValueError, "katalog yetersiz"):
            daily.choose_stories(self.catalogue[:1], {}, reel, self.day, {})

    def test_verified_director_choice_wins_until_used(self):
        board = {**self.board, "coordinator_llm": {"completed_discussion": True,
                 "decision": {"selected_idea_id": "pig-war-1859"}}}
        self.assertEqual(daily.choose_reel(self.topics, {}, board)["id"], "pig-war-1859")
        used = {"2026-11-25": {"reel_id": "pig-war-1859"}}
        self.assertEqual(daily.choose_reel(self.topics, used, board)["id"], "antikythera-disli")
        self.assertEqual(daily.choose_reel(self.topics, used, board, demo=True)["id"], daily.APPROVED_PIRI)

    def test_caption_limits_sources_and_no_fake_trend(self):
        topic = daily.choose_reel(self.topics, {}, self.board, demo=True)
        seo = daily.search_notes(topic, {"trends": [{"title": "Piri Reis haritası"}]})
        caption, pin = daily.disclosures(topic, seo)
        self.assertLessEqual(len(caption), 2200)
        self.assertGreater(len(caption), 400)
        self.assertIn(topic["sources"][0]["url"], caption)
        self.assertIn(topic["sources"][0]["title"], pin)
        self.assertLessEqual(len(seo["hashtags"]), 5)
        self.assertEqual(seo["instagram_hashtag_volume_status"], "unavailable")
        self.assertEqual(len(seo["matched_google_trends"]), 1)

    def test_real_silent_vertical_story_package_and_date_guard(self):
        with TemporaryDirectory() as folder:
            out = Path(folder)
            (out / "editorial").mkdir()
            daily.write_json(out / "editorial/EDITORIAL_DECISION_REPORT.json", self.board)
            ledger = out / "ledger.json"
            daily.write_json(ledger, {})
            self.assertEqual(daily.prepare(out, ledger, self.day, demo=True, observations=[]), daily.APPROVED_PIRI)
            plan = daily.load_json(out / "DAILY_PLAN.json")
            self.assertEqual(len(plan["stories"]), 10)
            self.assertFalse(plan["instagram_auto_publish"])
            self.assertTrue(plan["human_approval_required"])
            for story in plan["stories"]:
                with Image.open(out / story["file"]) as image:
                    self.assertEqual((image.size, image.format), ((1080, 1920), "PNG"))
                self.assertFalse(story["audio"])
            self.assertEqual(len(daily.load_json(out / "HAFTALIK_TAKVIM.json")), 7)
            self.assertEqual(len(daily.load_json(out / "AYLIK_TAKVIM.json")), 30)
            ledger.write_text(json.dumps({self.day.isoformat(): {}}))
            with self.assertRaisesRegex(ValueError, "daha önce"):
                daily.prepare(out, ledger, self.day)

    def test_verification_cannot_pass_a_failed_narration_stage(self):
        with TemporaryDirectory() as folder:
            out = Path(folder)
            daily.write_json(out / "DAILY_PLAN.json", {})
            names = ("research", "topic_selection", "script", "narration", "visuals", "editing", "mp4")
            stages = {stage: {"status": "failed" if stage == "narration" else "passed"} for stage in names}
            daily.write_json(out / "E2E_REPORT.json", {"stages": stages})
            with self.assertRaisesRegex(ValueError, "doğrulaması"):
                daily.verify_package(out, out / "ledger.json", out / "next.json")
            self.assertFalse((out / "DAILY_VERIFICATION.json").exists())


if __name__ == "__main__":
    unittest.main()
