from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import beauty_production, pause_review, scene_director
from scripts.editorial_state import EditorialState
from scripts.skill_registry import registry_view
from scripts.skill_router import RouteContext, select_knowledge
from scripts.tool_router import run_tool


class MediaCraftTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.state = EditorialState(Path(folder.name) / "review.sqlite")
        self.snapshot = {
            "fps": 30, "duration_frames": 2100, "alignment": "reviewed_source_frame_alignment",
            "silence": [[10, 50], [105, 127], [180, 210], [224, 254], [300, 307]],
            "narration": [[130, 166]], "captions": [[213, 231]],
        }

    def test_registry_preserves_154_records_with_separate_local_adapter(self):
        registry = registry_view()
        prefixes = {"blender-skills", "lemo-opuscar", "earshot", "video-shotcraft", "rough-js", "auto-editor", "media-craft"}
        added = [row for row in registry["entries"].values() if row["id"].split(":")[0] in prefixes]
        self.assertEqual(sum(row["kind"] == "knowledge" for row in added), 7)
        self.assertEqual([row["id"] for row in added if row["adapter"]], [pause_review.TOOL_ID])
        self.assertGreaterEqual(len(registry["entries"]) - len(added), 154)
        self.assertEqual(sum(row["primary"] for row in registry["experts"].values()), 40)

    def test_scene_director_keeps_existing_renderers_and_adds_specific_review(self):
        historical_topic = scene_director._load_topic("tarih", "piri-reis-kayip-kaynak", None)
        history = scene_director.build_plan("tarih", historical_topic)
        opening = history["scenes"][0]
        self.assertEqual(opening["kind"], "collage")
        self.assertEqual(opening["render"]["primary"]["id"], "media:hyperframes")
        self.assertEqual(opening["craft_review"]["visual_notes"],
                         ["lemo-opuscar:briefing-board-focus", "rough-js:seeded-sketch-strokes"])
        self.assertEqual(opening["craft_review"]["foley_notes"], ["earshot:material-contact-cue"])
        map_scene = next(scene for scene in history["scenes"] if scene["kind"] == "map")
        self.assertEqual(map_scene["render"]["primary"]["id"], "media:three-js")
        self.assertNotIn("craft_review", map_scene)

        care = beauty_production.make_plan(beauty_production.load_topic("cilt-bariyeri-katmanlari"))
        macro = next(scene for scene in care["scenes"] if scene["kind"] == "macro")
        layer = next(scene for scene in care["scenes"] if scene["kind"] == "barrier")
        self.assertEqual(macro["craft_review"], {
            "visual_notes": ["video-shotcraft:product-detail-hold", "blender-skills:material-light-check"],
            "foley_notes": ["earshot:material-contact-cue"],
        })
        self.assertEqual(layer["craft_review"], {"visual_notes": ["blender-skills:material-light-check"], "foley_notes": []})
        report = scene_director.preflight(care, self.state)
        self.assertEqual(report["scenes"][macro["id"]]["render_status"], "not_run")
        self.assertFalse(report["media_created"])
        self.assertTrue(all(pause_review.TOOL_ID not in scene["tools"] for scene in care["scenes"] + history["scenes"]))

    def test_openmontage_delta_is_role_scoped_and_reaches_both_plans(self):
        registry = registry_view()
        notes = {key: row for key, row in registry["entries"].items() if key.startswith("openmontage-15f:")}
        self.assertEqual(len(notes), 8)
        self.assertEqual({expert for row in notes.values() for expert in row["expert_ids"]},
                         {key for key, row in registry["experts"].items() if row["primary"]})
        for row in notes.values():
            self.assertIsNone(row["adapter"])
            self.assertEqual(row["security"]["status"], "curated_reference_only")
            self.assertEqual(row["license"]["scope"], "upstream_reference")
        history = scene_director.build_plan("tarih", scene_director._load_topic("tarih", "piri-reis-kayip-kaynak", None))
        beauty = beauty_production.make_plan(beauty_production.load_topic("cilt-bariyeri-katmanlari"))
        arc = next(scene for scene in history["scenes"] if scene["kind"] == "collage")
        macro = next(scene for scene in beauty["scenes"] if scene["kind"] == "macro")
        self.assertIn("openmontage-15f:archive-shot-evidence", arc["review_skills"])
        self.assertIn("openmontage-15f:surface-exposure", macro["review_skills"])
        self.assertIn("openmontage-15f:sound-cause", macro["review_skills"])
        self.assertFalse(select_knowledge(RouteContext("bakim", 7, "shot-review", "macro")))
        reference = select_knowledge(RouteContext("bakim", 6, "reference-review"))
        self.assertEqual([row["id"] for row in reference],
                         ["cinecode:reference-form", "openmontage-15f:reference-shot-log"])

    def test_pause_review_protects_both_tracks_and_leaves_source_as_received(self):
        before = deepcopy(self.snapshot)
        result = pause_review.review_pauses(self.snapshot)
        self.assertEqual(self.snapshot, before)
        self.assertEqual(result["mode"], "annotations_only")
        self.assertFalse(result["timeline_modified"])
        intervals = result["pause_intervals"]
        self.assertEqual([row["reasons"] for row in intervals],
                         [["opening_protected"], ["narration_protected"], ["captions_protected"],
                          ["captions_protected"], ["short_pause"]])
        self.assertTrue(all(row["status"] == "protected" for row in intervals))
        self.snapshot["silence"] = [[260, 290]]
        neutral, = pause_review.review_pauses(self.snapshot)["pause_intervals"]
        self.assertEqual(neutral, {"start_frame": 260, "end_frame": 290,
                                  "status": "human_review_candidate", "reasons": []})

    def test_misaligned_or_unsafe_snapshots_are_rejected(self):
        for patch in (
            {"alignment": "estimated_from_script"}, {"captions": []}, {"narration": []}, {"fps": 24},
            {"silence": [[120, 180], [140, 200]]}, {"silence": [[120, 3000]]}, {"captions": [[10, True]]},
            {"path": "/samples/voice.wav"},
        ):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                pause_review.review_pauses({**self.snapshot, **patch})

    def test_tool_router_executes_review_metadata_only_and_reuses_cache(self):
        for brand in ("tarih", "bakim"):
            with self.subTest(brand=brand):
                context = RouteContext(brand, 15, "pause-analysis")
                self.assertEqual([n["id"] for n in select_knowledge(context)], ["auto-editor:pause-evidence"])
                arguments = {"topic": {}, "state": self.state, "snapshots": {pause_review.TOOL_ID: self.snapshot}}
                result = run_tool(context, **arguments)
                self.assertEqual(result["status"], "success")
                self.assertFalse(result["result"]["media_created"])
                self.assertEqual(result["executed_adapter"]["id"], pause_review.TOOL_ID)
                reused = run_tool(context, **arguments)
                self.assertEqual(reused["status"], "cache")
                self.assertIsNone(reused["executed_adapter"])
                blocked = run_tool(context, preferred="auto-editor:pause-evidence", **arguments)
                self.assertEqual(blocked["rejected"][0]["reason"], "knowledge_or_asset_reference")
        closed = run_tool(RouteContext("bakim", 17, "pause-analysis"), topic={}, state=self.state,
                          snapshots={pause_review.TOOL_ID: self.snapshot})
        self.assertEqual(closed["rejected"][0]["reason"], "role_not_allowed")
