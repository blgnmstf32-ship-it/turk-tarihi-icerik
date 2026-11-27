import contextlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import beauty_production as beauty, beauty_reel, beauty_studio
from scripts.motion_toolkit import sha256_file
from scripts.skill_registry import registry_view


class GeneralBeautyProductionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.target = Path(tmp.name)

    def read(self, name):
        return json.loads((self.target / name).read_text())

    def save(self, name, data):
        (self.target / name).write_text(json.dumps(data, ensure_ascii=False))

    def mechanisms(self, plan):
        return [row for row in plan["scenes"] if row["purpose"] == "mechanism"]

    def test_laser_plans_a_follicle_diagram_and_visible_risk_without_using_3d(self):
        plan = beauty.make_plan(beauty.load_topic("lazer-on-gorusme"))
        self.assertEqual([(row["kind"], row["motif"]) for row in self.mechanisms(plan)], [("science", "follicle")])
        warning_id, = plan["beauty"]["health_warnings"]
        warning = next(row for row in plan["scenes"] if row["id"] == warning_id)
        self.assertIn("yanık", warning["narration"]["text"])
        self.assertIn(5, warning["review_roles"])
        self.assertTrue(all(row["render"]["primary"]["id"] == "media:remotion" for row in plan["scenes"]))

    def test_barrier_routes_two_3d_models_and_macros_with_safe_planned_alternative(self):
        topic = beauty.load_topic("cilt-bariyeri-katmanlari")
        with patch.object(beauty, "render_local", side_effect=AssertionError("unexpected render")):
            self.assertEqual(beauty.prepare(topic, self.target)["status"], "not_run")
            beauty.prepare(topic, self.target)
        plan, report = self.read("SCENE_PLAN.json"), self.read("SCENE_EXECUTION_REPORT.json")
        three = [row for row in plan["scenes"] if row["render"]["primary"]["id"] == "media:three-js"]
        self.assertEqual([row["kind"] for row in three], ["barrier", "barrier", "macro"])
        self.assertTrue(all(row["render"]["alternative"]["id"] == "media:remotion" and 13 in row["review_roles"]
                            and row["render"]["illustration_frames"] <= 270 for row in three))
        self.assertTrue(all(report["scenes"][row["id"]]["executed_renderer"] is None for row in three))
        self.assertEqual(report["scenes"]["s01"]["local_preflight"]["cache"], "hit")
        self.assertEqual(report["scenes"]["s01"]["local_preflight"]["executed_tools"], [])
        self.assertEqual(len(registry_view()["entries"]), 144)

    def test_sunscreen_uses_uv_graphic_and_keeps_label_jurisdiction(self):
        plan = beauty.make_plan(beauty.load_topic("gunes-koruyucu-etiketi"))
        self.assertEqual(self.mechanisms(plan)[0]["motif"], "uv")
        label = next(row for row in plan["scenes"] if row["purpose"] == "product")
        self.assertEqual(label["kind"], "motion")
        self.assertIn("Amerika Birleşik Devletleri", label["narration"]["text"])

    def test_all_six_topics_preserve_format_sources_and_subtitle_boundaries(self):
        catalogue = beauty.director._read(beauty.CATALOG)
        self.assertEqual(len(catalogue["topics"]), 6)
        for topic_id in catalogue["topics"]:
            with self.subTest(topic=topic_id):
                topic = beauty.load_topic(topic_id)
                plan = beauty.make_plan(topic)
                self.assertEqual((plan["resolution"], plan["fps"], plan["duration_frames"]), ([1080, 1920], 30, 2100))
                self.assertEqual(len(plan["scenes"]), 10)
                self.assertEqual(len(plan["transitions"]), 9)
                self.assertTrue(all(row["narration"]["voice"] == "Sulafat" and row["narration"]["source_numbers"]
                                    and row["captions"]["timing"] == "draft_estimate" for row in plan["scenes"]))
                cues = beauty.draft_cues(plan)
                self.assertEqual(beauty._verify_cues(cues, [row["text"] for row in topic["beats"]], 70),
                                 [row["end_frame"] for row in plan["scenes"]])

    def test_first_plan_logs_opening_adapter_and_twenty_local_briefs_without_render(self):
        beauty.prepare(beauty.load_topic("cilt-bariyeri-katmanlari"), self.target)
        reports = self.read("SCENE_EXECUTION_REPORT.json")
        self.assertTrue(reports["scenes"]["s01"]["local_preflight"]["executed_tools"])
        self.assertTrue(all(row["render_status"] == "not_run" and row["executed_renderer"] is None
                            for row in reports["scenes"].values()))
        render = self.read("BEAUTY_RENDER_REPORT.json")
        self.assertEqual(render, {"status": "not_run", "media_created": False, "instagram_published": False, "api_calls": 0})
        briefs = self.read("BEAUTY_SPECIALIST_BRIEFS.json")
        self.assertEqual(sorted(row["id"] for row in briefs["roles"]), list(range(1, 21)))
        self.assertTrue(all(row["status"] == "brief_only" and row["guidance"] for row in briefs["roles"]))
        self.assertEqual(briefs["llm_calls"], 0)
        editorial = self.read("REELS_EDITORIAL_REVIEW.json")
        self.assertEqual((len(editorial["hooks"]), len(editorial["scenarios"]), editorial["threshold"]), (5, 3, 85))
        self.assertFalse(editorial["media_checked"])
        self.assertIn("Bariyer nerede başlar?", (self.target / "TR_TASLAK.srt").read_text())
        self.assertFalse(list(self.target.glob("*.mp4")))

    def test_refuses_unknown_source_missing_warning_and_sales_promises(self):
        for change, error in (
            (lambda t: t["sources"]["aad-laser-prep"].update(url="https://aad.org.example.org/document"), "Bilimsel kaynak"),
            (lambda t: t["beats"][1].update(references=["yok"]), "bilimsel kaynak"),
            (lambda t: t["beats"][6].update(purpose="context"), "sağlık uyarısı"),
            (lambda t: t["beats"][6].update(text="Dikkat ve özen gösterin."), "dermatolog"),
            (lambda t: t["beats"][2].update(text="Kesin sonuç alırsınız."), "güvenli Türkçe"),
            (lambda t: t["beats"].pop(1), "En az 10"),
        ):
            with self.subTest(error=error):
                topic = beauty.load_topic("lazer-on-gorusme")
                change(topic)
                with self.assertRaisesRegex(ValueError, error):
                    beauty.make_plan(topic)

    def test_external_visual_requires_approved_rights_and_separate_attribution(self):
        topic = beauty.load_topic("kozmetik-parfum-etiketi")
        visual = {"file": "kavanoz.jpg", "license": "CC-BY-NC-4.0", "commercial_use_reviewed": True,
                  "source": "https://commons.wikimedia.org/wiki/File:Jar.jpg", "sha256": "a" * 64,
                  "attribution": "Örnek yazar"}
        topic["beats"][1]["visual"] = visual
        with self.assertRaisesRegex(ValueError, "ticari lisans"):
            beauty.make_plan(topic)
        visual["license"] = "CC-BY-4.0"
        plan = beauty.make_plan(topic)
        scene = plan["scenes"][1]
        asset, = scene["visual_assets"]
        self.assertEqual((scene["kind"], asset["rights_status"], asset["file"]), ("flat", "declared_reviewed", "kavanoz.jpg"))
        self.assertNotIn(asset["source_number"], scene["narration"]["source_numbers"])

    def stub_approved_bundle(self, topic, plan):
        # Metadata tests only. The WAV reader is stubbed and these bytes are never used as audio.
        audio = self.target / "SULAFAT.wav"
        audio.write_bytes(b"immutable local fixture")
        script = plan["beauty"]["script_sha256"]
        timing = {"cues": beauty.draft_cues(plan), "language": "tr", "script_sha256": script,
                  "audio_sha256": sha256_file(audio)}
        self.save("CAPTIONS.json", timing)
        approval = {"human_approved": True, "source_claims_reviewed": True, "health_warnings_reviewed": True,
                    "visual_rights_reviewed": True, "topic_sha256": beauty.director._digest(topic),
                    "captions_sha256": sha256_file(self.target / "CAPTIONS.json"), "voice": "Sulafat",
                    "script_sha256": script, "audio_sha256": sha256_file(audio)}
        self.save("REVIEW.json", approval)
        return approval, timing

    def test_approved_caption_binding_rejects_changed_audio_and_caption_text(self):
        topic = beauty.load_topic("lazer-on-gorusme")
        plan = beauty.make_plan(topic)
        approval, timing = self.stub_approved_bundle(topic, plan)
        with patch.object(beauty.wave, "open") as reader:
            voice = reader.return_value.__enter__.return_value
            voice.getframerate.return_value = 48_000
            voice.getnframes.return_value = 48_000 * 70
            audio, cues, cuts, _, _ = beauty.approved_bundle(topic, plan, self.target)
            self.assertEqual((audio.name, cuts[-1], cues[0]["text"]), ("SULAFAT.wav", 2100, "İlk adım ön görüşme."))
            timing["cues"][0]["text"] = "Başka kayıt."
            self.save("CAPTIONS.json", timing)
            approval["captions_sha256"] = sha256_file(self.target / "CAPTIONS.json")
            self.save("REVIEW.json", approval)
            with self.assertRaisesRegex(ValueError, "birebir"):
                beauty.approved_bundle(topic, plan, self.target)
            audio.write_bytes(b"changed fixture")
            with self.assertRaisesRegex(ValueError, "aynı metin ve dosyalara"):
                beauty.approved_bundle(topic, plan, self.target)

    def test_explicit_render_rejects_missing_bundle_and_reports_failed_renderer(self):
        topic = beauty.load_topic("nazik-sac-bakimi")
        with self.assertRaisesRegex(ValueError, "onaylı Sulafat"):
            beauty.prepare(topic, self.target, render_browser=Path("chromium"))
        plan = beauty.make_plan(topic)
        boundaries = [row["end_frame"] for row in plan["scenes"]]
        bundle = Path("approved_audio"), beauty.draft_cues(plan), boundaries, {}, "a" * 64
        with (patch.object(beauty, "approved_bundle", return_value=bundle),
              patch.object(beauty, "render_local", side_effect=ValueError("test renderer failure"))):
            with self.assertRaisesRegex(ValueError, "render tamamlanmadı"):
                beauty.prepare(topic, self.target, bundle=self.target, render_browser=Path("chromium"))
        self.assertEqual(self.read("SCENE_PLAN.json")["timing"], "approved_caption_frame_boundaries")
        self.assertEqual(self.read("BEAUTY_RENDER_REPORT.json")["status"], "failed")
        self.assertFalse(self.read("BEAUTY_RENDER_REPORT.json")["media_created"])

    def test_old_pilot_cli_and_new_studio_entrypoint(self):
        with (patch.object(beauty_reel, "assemble") as pilot,
              patch("sys.argv", ["beauty_reel", "--assets", str(self.target), "--out", str(self.target)])):
            beauty_reel.main()
        pilot.assert_called_once_with(self.target, self.target, browser=None, vmaf_reference=None, vmaf_aligned=False)
        with (patch("sys.argv", ["beauty_studio", "--reel-topic", "nazik-sac-bakimi", "--out", str(self.target)]),
              patch.object(beauty_studio, "build_preview", side_effect=AssertionError("started daily workflow"))):
            beauty_studio.main()
        self.assertEqual(self.read("SCENE_PLAN.json")["topic"]["id"], "nazik-sac-bakimi")
        with (patch("sys.argv", ["beauty_reel", "--topic", "nazik-cilt-bakimi", "--out", str(self.target)]),
              contextlib.redirect_stdout(StringIO()) as stdout):
            beauty_reel.main()
        self.assertEqual(json.loads(stdout.getvalue())["topic"], "nazik-cilt-bakimi")


if __name__ == "__main__":
    unittest.main()
