import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts import motion_atlas, motion_layers, motion_quality, motion_toolkit
from scripts.ai_agents import _media_advice


def receipt(path, **extra):
    return {"commercial_use_reviewed": True, "license": "CC-BY-4.0", "attribution": "Test source",
            "source": "https://example.org/source", "sha256": motion_toolkit.sha256_file(path), **extra}


class MotionToolkitTests(TestCase):
    def test_index_covers_every_skill_and_options_default_off(self):
        index = motion_toolkit.skill_index()
        iart = [row for row in index if row["repository"].startswith("iart-ai/")]
        self.assertEqual(len(iart), 19)
        self.assertEqual(sum(len(entry["skills"]) for entry in iart), 56)
        self.assertEqual(sum(len(entry["skills"]) for entry in index), 65)
        self.assertEqual(len(motion_toolkit.registry()["tools"]), 15)
        self.assertFalse(motion_toolkit.registry()["default_enabled"])

    def test_advice_is_scoped_and_does_not_unlock_conditional_tools(self):
        editor = motion_toolkit.role_guidance("bakim")
        self.assertIn("manim", editor["assignment_options"]["13"])
        direction = motion_toolkit.role_guidance("tarih", 13)
        self.assertIn("motion-art-direction", direction["techniques"])
        self.assertEqual(direction["tools"]["rembg"]["status"], "conditional")
        choices = {name: row["use"] for name, row in direction["tools"].items() if row["status"] == "optional"}
        self.assertIsNotNone(_media_advice('{"suggestion":"Test","caveat":"Hak kontrolü","media_tool":"rembg"}',
                                           0, choices)[1])

    def test_receipt_binds_commercial_license_to_exact_asset(self):
        with TemporaryDirectory() as temp:
            fixture = Path(temp) / "asset.txt"
            fixture.write_text("ordinary data")
            review = receipt(fixture)
            self.assertEqual(motion_toolkit.verified_local(fixture, review, maximum_bytes=100), fixture.resolve())
            for edits in ({"license": "CC-BY-NC-4.0"}, {"commercial_use_reviewed": False},
                          {"sha256": "wrong"}, {"source": "https://account@example.org"}):
                with self.subTest(edits=edits), self.assertRaises(ValueError):
                    motion_toolkit.verified_local(fixture, {**review, **edits}, maximum_bytes=100)

    def test_atlas_style_is_local_and_period_locked(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "mock.geojson"
            path.write_text(json.dumps({"type": "FeatureCollection", "features": [
                {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-5, 40], [2, 43]]}}
            ]}))
            approved = receipt(path, year=1513)
            approved["attribution"] = "<test>"
            bundle = motion_atlas.atlas_overlay(path, approved, year=1513)
            style = bundle["style"]
            self.assertEqual(style["version"], 8)
            self.assertIsInstance(style["sources"]["historical"]["data"], dict)
            self.assertEqual(style["sources"]["historical"]["attribution"], "&lt;test&gt;")
            self.assertNotIn("glyphs", style)
            self.assertEqual(bundle["atlas"]["year"], 1513)
            self.assertEqual(len(bundle["atlas"]["lines"][0]), 2)
            with self.assertRaises(ValueError):
                motion_atlas.atlas_overlay(path, approved, year=1525)

    def test_poly_haven_only_lists_metadata_and_valid_slugs(self):
        result = motion_toolkit.poly_haven_catalogue({"rock_01": {"name": "Rock"}, "../bad": {}}, kind="models")
        self.assertEqual(result["attribution"], "Powered by Poly Haven")
        self.assertEqual([row["id"] for row in result["assets"]], ["rock_01"])
        self.assertFalse(result["assets"][0]["downloaded"])
        with patch("requests.get") as request, self.assertRaises(ValueError):
            motion_toolkit.load_poly_haven("models")
        request.assert_not_called()

    def test_depth_does_not_accept_other_weight_bytes(self):
        with TemporaryDirectory() as temp:
            fixture = Path(temp) / "not-a-model.onnx"
            fixture.write_text("not model weights")
            with self.assertRaisesRegex(ValueError, "pinned Apache"):
                motion_layers.depth_model(fixture)

    def test_parallax_plan_binds_the_base_before_loading_any_layer(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "input.txt"
            fixture.write_text("generic fixture, no pixels")
            (root / "parallax.json").write_text(json.dumps({"image_sha256": "wrong", "layers": []}))
            with self.assertRaisesRegex(ValueError, "match the original"):
                motion_layers.reviewed_parallax(fixture, root)

    def test_vmaf_requires_explicit_alignment_and_parses_metric_without_a_render(self):
        with patch.object(motion_quality, "_execute") as run, self.assertRaisesRegex(ValueError, "alignment"):
            motion_quality.vmaf_report("reference.mp4", "encoded.mp4")
        run.assert_not_called()
        self.assertEqual(motion_quality.parse_vmaf({"pooled_metrics": {"vmaf": {"mean": 93.5}},
                                                    "frames": [{}, {}]})["vmaf_mean"], 93.5)

    def test_denoise_rejects_absent_noise_confirmation_before_tools(self):
        with patch.object(motion_quality, "_execute") as run, self.assertRaisesRegex(ValueError, "noise"):
            motion_quality.denoise_wav("voice.wav", "model.tar.gz", {}, "output")
        run.assert_not_called()

    def test_glb_validation_rejects_external_assets_using_manifest_only(self):
        data = json.dumps({"asset": {"version": "2.0"}, "images": [{"uri": "https://example.org/img.jpg"}]}).encode()
        with TemporaryDirectory() as temp:
            fixture = Path(temp) / "manifest-only.tmp"
            fixture.write_bytes(struct.pack("<4sIII4s", b"glTF", 2, 20 + len(data), len(data), b"JSON") + data)
            with self.assertRaisesRegex(ValueError, "internal buffers"):
                motion_quality.inspect_glb(fixture)

    def test_manim_uses_only_our_named_scenes(self):
        command = motion_quality.manim_command("barrier", "example")
        self.assertEqual(command[-1], "SkinBarrierDiagram")
        self.assertTrue(command[-2].endswith("scripts/motion_diagrams.py"))
        with self.assertRaises(ValueError):
            motion_quality.manim_command("../external", "example")

    def test_all_forty_techniques_reach_the_primary_expert_roles(self):
        catalogue = {(pack["repository"], row["path"])
                     for pack in motion_toolkit.skill_index() for row in pack["skills"]
                     if row["decision"] == "adapt"}
        attached = {(row["repository"], row["path"])
                    for brand in ("tarih", "bakim") for role in range(1, 21)
                    for row in motion_toolkit.role_guidance(brand, role)["technique_sources"]}
        self.assertEqual(len(catalogue), 40)
        self.assertEqual(attached, catalogue)

    def test_opening_selection_depends_on_the_topic_without_a_tool_install(self):
        select = motion_toolkit.select_opening_effect
        self.assertEqual(select("tarih", {"category": "kesif"}), "lines-reveal")
        self.assertEqual(select("tarih", {"visual_mode": "artifact_gears"}), "lines-reveal")
        self.assertEqual(select("bakim", {"visual_mode": "layer_diagram"}), "lines-reveal")
        self.assertIsNone(select("tarih", {"visual_mode": "atlantic_atlas"}))
        self.assertIsNone(select("bakim", {"category": "genel_bakim"}))
        with self.assertRaises(ValueError):
            select("tarih", {}, requested="mask-reveal", parallax=True)

    def test_history_optional_failure_keeps_the_base_atlas_scene(self):
        from scripts.auto_produce import render_motion_or_base
        from unittest.mock import Mock

        base = {"kind": "atlantic_atlas"}
        overlay = {**base, "historical_overlay": {"year": 1513}}
        render = Mock(side_effect=[FileNotFoundError("optional layer missing"), "base-render"])
        asset, three_d, report = render_motion_or_base(
            render, "scenes", plan={"scenes": [overlay]}, edit={"effect": "lines-reveal", "hook": "Kanıt"},
            parallax_dir="optional-layers")
        self.assertEqual((asset, three_d["status"]), ("base-render", "rendered"))
        self.assertEqual(report["status"], "optional_render_skipped")
        self.assertEqual(render.call_args_list[0].kwargs["three_scenes"], [overlay])
        self.assertEqual(render.call_args_list[1].kwargs, {"three_scenes": [base], "edit": {"hook": "Kanıt"}})

    def test_history_uses_selected_effect_when_available_without_a_second_render(self):
        from scripts.auto_produce import render_motion_or_base
        from unittest.mock import Mock

        render = Mock(return_value="optional-render")
        effect = motion_toolkit.select_opening_effect("tarih", {"category": "kesif"})
        _, _, report = render_motion_or_base(render, plan={"scenes": []}, edit={"effect": effect})
        self.assertEqual(report["status"], "applied")
        self.assertEqual(render.call_args.kwargs["edit"]["effect"], "lines-reveal")
        render.assert_called_once()

    def test_beauty_optional_title_retries_the_unmodified_scene(self):
        from scripts import beauty_reel

        with patch.object(beauty_reel, "shot", side_effect=[RuntimeError("optional failure"), "base"]) as render:
            clip, report = beauty_reel.reviewed_shot("scene", title_effect="lines-reveal")
        self.assertEqual(clip, "base")
        self.assertEqual(report["status"], "optional_render_skipped")
        self.assertEqual(render.call_args_list[0].kwargs, {"title_effect": "lines-reveal"})
        self.assertEqual(render.call_args_list[1].kwargs, {})

    def test_beauty_title_preset_animates_a_repeating_input_without_writing_images(self):
        from scripts import beauty_reel

        with patch.object(beauty_reel, "overlay"), patch.object(beauty_reel, "ffmpeg") as render:
            beauty_reel.shot(Path("out"), 2, 60, "skin", Path("approved.jpg"),
                             "Giriş", "Başlık", "Şema", title_effect="lines-reveal")
        args = render.call_args.args
        self.assertIn("-loop", args)
        self.assertIn("alpha=1", args[args.index("-filter_complex") + 1])

    def test_unavailable_vmaf_reports_no_score_and_does_not_read_the_video(self):
        with patch.object(motion_quality, "_execute", return_value=" ... vmafmotion V->V") as run:
            result = motion_quality.vmaf_report("reference.mp4", "encoded.mp4", aligned=True)
        self.assertEqual(result, {"status": "not_measured", "reason": "libvmaf_unavailable"})
        run.assert_called_once_with(["ffmpeg", "-hide_banner", "-filters"])
        with patch.object(motion_quality, "_execute", side_effect=FileNotFoundError) as run:
            result = motion_quality.optional_vmaf("reference.mp4", "encoded.mp4", aligned=True)
        self.assertEqual(result, {"status": "not_measured", "reason": "ffmpeg_unavailable"})
        run.assert_called_once()

    def test_missing_or_failed_reference_never_yields_a_vmaf_score(self):
        with patch.object(motion_quality, "vmaf_report") as measure:
            result = motion_quality.optional_vmaf(None, "encoded.mp4")
        self.assertEqual(result, {"status": "not_measured", "reason": "no_aligned_reference"})
        measure.assert_not_called()
        with patch.object(motion_quality, "vmaf_report", side_effect=ValueError):
            result = motion_quality.optional_vmaf("reference.mp4", "encoded.mp4", aligned=True)
        self.assertNotIn("vmaf_mean", result)
        self.assertEqual(result["status"], "not_measured")
