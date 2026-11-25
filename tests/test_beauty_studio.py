from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.beauty_studio import build_preview
from scripts.run import ROOT, load_json


class BeautyStudioTest(TestCase):
    def test_brand_identity_calendar_and_silent_review_drafts(self):
        with TemporaryDirectory() as root:
            out = Path(root)
            build_preview(out, date(2026, 11, 26))
            drafts = load_json(out / "bakim/BAKIM_ONIZLEME.json")
            self.assertEqual(drafts["real_reels_produced"], 0)
            self.assertEqual(drafts["paid_images_produced"], 0)
            self.assertEqual(drafts["preview_voice"], "Sulafat")
            self.assertIsNone(drafts["approved_voice"])
            self.assertEqual(len({row["sha256"] for row in drafts["stories"]}), 10)
            self.assertTrue(all(row["url"].startswith("https://") and not row["audio"] for row in drafts["stories"]))
            self.assertFalse(drafts["instagram_auto_publish"])
            self.assertTrue(drafts["human_approval_required"])
            beauty = load_json(out / "bakim/HAFTALIK_TAKVIM.json")
            history = load_json(out / "tarih/HAFTALIK_TAKVIM.json")
            self.assertEqual(beauty[0]["reel_slots"], ["13:00", "20:00"])
            self.assertEqual(history[0]["reel_slots"], ["12:00", "16:00", "19:00"])
            self.assertEqual(len(load_json(ROOT / "config/beauty_agents.json")), 20)
