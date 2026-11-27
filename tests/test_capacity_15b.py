import copy
import unittest

from scripts import capacity_15b


class Capacity15BTests(unittest.TestCase):
    def test_trial_content_has_distinct_boundaries_and_unchanged_operating_target(self):
        data = capacity_15b.load()
        capacity_15b.validate(data)
        self.assertEqual(capacity_15b.DAILY_TARGET, {"reels_total": 2, "stories": {"tarih": 10, "bakim": 10}})
        self.assertEqual(capacity_15b.REEL_STRESS, {"tarih": 3, "bakim": 2})
        self.assertEqual(len({row["id"] for row in data["stories"]}), 20)
        self.assertTrue(all(reel["boundary"] for reel in data["reels"]))

    def test_reused_story_id_or_unsafe_claim_is_rejected(self):
        data = capacity_15b.load()
        copy_with_duplicate = copy.deepcopy(data)
        rows = copy_with_duplicate["stories"]
        rows[1]["id"] = rows[0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicates"):
            capacity_15b.validate(copy_with_duplicate)
        data["stories"][-1]["text"] = "Kesin tedavi vaadi."
        with self.assertRaisesRegex(ValueError, "Unsupported guarantee"):
            capacity_15b.validate(data)
