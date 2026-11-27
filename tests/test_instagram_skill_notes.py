from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from scripts import reels_editorial, skill_registry
from scripts.performance_learning import reels_benchmarks


class InstagramSkillNotesTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = skill_registry.registry_view()
        self.notes = {key: row for key, row in self.snapshot["entries"].items()
                      if key.startswith("instagram:")}

    def test_preexisting_registry_is_retained_and_notes_are_read_only(self):
        self.assertGreaterEqual(len(self.snapshot["entries"]) - len(self.notes), 135)
        self.assertEqual(len(self.notes), 9)
        for note in self.notes.values():
            self.assertEqual(note["kind"], "knowledge")
            self.assertEqual(note["use"]["mode"], "reference")
            self.assertEqual(note["license"], {"code": "MIT", "scope": "upstream_reference"})
            self.assertEqual(note["source"]["revision"], "d03c56bb598be770c60b201f94237e5d1a4268a6")
            self.assertEqual(note["source"]["repository"], "Jakeschincariol/instagram-agent-skill")
            self.assertEqual(note["source"]["license_path"], "LICENSE")
            self.assertTrue(note["source"]["path"].startswith("skills/ig-"))
            self.assertIsNone(note["adapter"])
            self.assertFalse(note["security"]["authorizes_execution"])
            self.assertFalse(note["cost"]["metered_or_paid_allowed"])

    def test_thirty_relevant_specialists_across_both_intact_rosters(self):
        for brand, count in (("tarih", 14), ("bakim", 16)):
            primary = [row for row in self.snapshot["experts"].values()
                       if row["brand"] == brand and row["primary"]]
            self.assertEqual(len(primary), 20)
            self.assertEqual(sum(bool(self.notes.keys() & set(row["entry_ids"])) for row in primary), count)
        self.assertIn("instagram:competitor-relative-baseline", skill_registry.registry_view("bakim", 6)["entries"])
        self.assertNotIn("instagram:competitor-relative-baseline", skill_registry.registry_view("tarih", 6)["entries"])

    def test_existing_specialist_brief_loads_only_relevant_notes_without_io_calls(self):
        skill_registry._inventory.cache_clear()
        with (patch("subprocess.Popen", side_effect=AssertionError("execution")),
              patch("requests.sessions.Session.request", side_effect=AssertionError("network"))):
            writer = reels_editorial.specialist_guidance({"id": 6, "reels_review": {"technique": "hook"}}, "tarih")
            researcher = reels_editorial.specialist_guidance({"id": 6}, "bakim")
            other = reels_editorial.specialist_guidance({"id": 13}, "tarih")
            tools = skill_registry.review_options("bakim", 6)
        self.assertEqual(writer["skill_notes"], [self.notes["instagram:hook-delivery"]["task"]])
        self.assertEqual(writer["method"], reels_editorial.playbook()["techniques"]["hook"])
        self.assertEqual(researcher["skill_notes"],
                         [self.notes["instagram:competitor-relative-baseline"]["task"]])
        self.assertTrue(all(row["task"] not in other.get("skill_notes", []) for row in self.notes.values()))
        self.assertTrue(self.notes.keys().isdisjoint(tools))

    def test_editorial_review_retains_five_hooks_three_scripts_and_eighty_five(self):
        topic = {"id": "local-example", "title": "Harita notları", "hook": "Haritanın notları ne söylüyor?"}
        for brand in ("tarih", "bakim"):
            result = reels_editorial.review(topic, brand, [topic["hook"], "İkinci anlam birimi."])
            self.assertEqual((len(result["hooks"]), len(result["scenarios"]), result["threshold"]), (5, 3, 85))
            self.assertFalse(result["score_is_viral_probability"])

    def test_editorial_scores_and_competitor_samples_are_not_insights(self):
        start = datetime(2026, 11, 1, tzinfo=timezone.utc)
        shared = {"brand": "tarih", "format": "REELS", "duration_seconds": 60,
                  "published_at": start.isoformat(), "captured_at_utc": (start + timedelta(hours=72)).isoformat(),
                  "reach": 100, "views": 150, "shares": 5, "editorial_score": 85}
        local_rows = [{**shared, "content_id": str(i), "source": source}
                      for source in ("editorial_plan_score", "competitor_observation") for i in range(5)]
        result = reels_benchmarks(local_rows, "tarih")
        self.assertEqual(result["status"], "insufficient_real_data")
        self.assertEqual(result["cohorts"], [])
