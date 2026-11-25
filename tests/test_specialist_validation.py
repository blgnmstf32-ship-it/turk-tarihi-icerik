import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.provider_budget import Budget
from scripts.specialist_validation import parse_group


class SpecialistValidationTests(TestCase):
    def test_individual_rows_require_a_decision_reason_and_valid_source(self):
        valid = {"role_id": 1, "decision": "incele", "rationale": "Nesneyi kaynakla karşılaştır.",
                 "suggestion": "Koleksiyon kaydını aç.", "caveat": "Tarih kesin değil.", "source_numbers": [1]}
        bad = {**valid, "role_id": 2, "source_numbers": [7]}
        result, error = parse_group(json.dumps({"roles": [valid, bad]}), {1, 2}, 2)
        self.assertIsNone(error)
        self.assertEqual(list(result["roles"]), ["1"])
        self.assertEqual(result["missing_role_ids"], [2])
        self.assertEqual(parse_group(json.dumps({"roles": [valid, valid]}), {1, 2}, 2),
                         (None, "wrong_or_duplicate_role"))

    def test_shared_minute_limit_delays_without_resetting_daily_limit(self):
        with TemporaryDirectory() as tmp:
            project = Budget(Path(tmp) / "quota.db")
            now = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)
            limits = (2, 100, 3)
            self.assertTrue(project.reserve_free("h", "tarih", "flash", 80, limits, now))
            self.assertTrue(project.reserve_free("b", "bakim", "flash", 20, limits, now + timedelta(seconds=2)))
            delay = project.free_slot_delay("flash", 60, limits, now + timedelta(seconds=10))
            self.assertAlmostEqual(delay, 50.1, places=4)
            self.assertTrue(project.reserve_free("b2", "bakim", "flash", 60, limits, now + timedelta(seconds=61)))
            self.assertIsNone(project.free_slot_delay("flash", 60, limits, now + timedelta(minutes=10)))
