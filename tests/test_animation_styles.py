from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from scripts.animation_styles import commons_collage_photo, plan_for, render_collage, style_guidance
from scripts.auto_produce import render_motion_or_base


class AnimationStyleTests(TestCase):
    def test_each_brand_selects_camera_collage_and_original_drawing_by_topic(self):
        cases = {
            "tarih": ("Antik şehir", "Gazete arşivi", "Sözlü destan"),
            "bakim": ("Cilt bariyeri", "İçerik listesi", "Nazik bakım rutini"),
        }
        for brand, titles in cases.items():
            for title, expected in zip(titles, ("continuous_camera", "paper_collage", "hand_drawn")):
                with self.subTest(brand=brand, title=title):
                    self.assertEqual(plan_for(brand, {"title": title})["style"], expected)
            self.assertEqual(plan_for(brand, {"title": "Genel bilgiler"})["stage"], "base_selected")

    def test_explicit_2d_preference_and_other_brand_vocabulary_are_respected(self):
        self.assertEqual(plan_for("tarih", {"title": "Antik şehir", "visual_mode": "2d"})["style"], "base")
        self.assertEqual(plan_for("bakim", {"title": "Osmanlı şehri"})["style"], "base")
        self.assertNotEqual(style_guidance("tarih", 13)["styles"], style_guidance("bakim", 13)["styles"])
        self.assertEqual(style_guidance("tarih", 8), {})
        self.assertEqual(style_guidance("bakim", 19), {})

    def test_optional_animation_falls_back_to_existing_edit_after_render_failure(self):
        renderer = mock.Mock(side_effect=[RuntimeError("optional"), {"path": "base"}])
        result, three, status = render_motion_or_base(
            renderer, plan={"scenes": []}, edit={"title": "Metin", "animation": {"style": "hand_drawn"}},
        )
        self.assertEqual(renderer.call_args_list[0].kwargs["edit"]["animation"]["style"], "hand_drawn")
        self.assertEqual(renderer.call_args_list[-1].kwargs["edit"], {"title": "Metin"})
        self.assertEqual(result, {"path": "base"})
        self.assertEqual(three["status"], "not_applicable_2d_only")
        self.assertEqual(status["status"], "optional_render_skipped")

    def test_missing_optional_hyperframes_reports_unavailable_without_attempting_download(self):
        with TemporaryDirectory() as tmp, mock.patch("scripts.animation_styles.PILOT", Path(tmp)):
            clip, info = render_collage("bakim", "Ürün etiketi", 5, Path(tmp) / "unused.mp4")
        self.assertIsNone(clip)
        self.assertEqual(info["stage"], "optional_unavailable")

    def test_optional_photo_rejects_traversal_and_noncommercial_terms(self):
        with TemporaryDirectory() as tmp:
            with mock.patch("scripts.animation_styles.sha256_file") as digest:
                self.assertIsNone(commons_collage_photo(tmp, {"file": "../photo.jpg", "license": "CC BY 4.0"}))
                self.assertIsNone(commons_collage_photo(tmp, {"file": "01_commons.jpg", "license": "CC BY-NC 4.0"}))
                digest.assert_not_called()
