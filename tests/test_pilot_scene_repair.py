from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import approved_pilot_replay as replay, pilot_scene_repair as repair, scene_director as director
from scripts.editorial_state import EditorialState


class PilotSceneRepairTests(unittest.TestCase):
    def test_moves_caption_without_changing_words_or_overlapping_previous(self):
        cues = [{"start": 0., "end": 2.8, "text": "Bir"}, {"start": 3.84, "end": 8., "text": "İki"}]
        edited, spans = repair.retime(cues, [{}, {"spoken_start": 2.52}], (1,))
        self.assertEqual([cue["text"] for cue in edited], ["Bir", "İki"])
        self.assertEqual(edited[0]["end"], edited[1]["start"])
        self.assertEqual(spans, [(76, 120)])
        self.assertEqual(cues[1]["start"], 3.84)

    def test_director_limits_scope_and_rechecks_neighboring_transitions(self):
        topic = director._load_topic("bakim", "kuruluk-nemlendirici-zamani", None)
        plan = replay.production_plan("bakim", topic, [], 2154)
        with TemporaryDirectory() as temp:
            state = EditorialState(Path(temp) / "state.sqlite")
            _, review, scope = repair.scene_scope(plan, state, [(58, 113)], "quality_failed")
        self.assertEqual(scope, [(58, 90, 0), (90, 113, 1)])
        self.assertEqual(review["evaluated_scene_ids"], ["s01", "s02"])
        self.assertEqual(review["evaluated_transition_ids"], ["s01--s02", "s02--s03"])
        self.assertEqual(review["scenes"]["s03"]["evaluation"], "reused_previous")

    def test_only_reported_caption_failures_reach_the_renderer(self):
        cues = [{"start": 0., "end": 2.8}, {"start": 3.84, "end": 6.}]
        original = {"after": {"cue_matches": [{"frame": 0, "offset_ms": 375},
                                               {"frame": 115, "offset_ms": 1320}]}}
        history = {"issues": [{"check": "subtitle_sync", "frames": [96, 202]}]}
        beauty = {"issues": [{"check": "mobile_readability", "frames": [115, 180]}]}
        self.assertEqual(repair.repair_targets(cues, original, history, True), [1])
        self.assertEqual(repair.repair_targets(cues, original, beauty, False), [1])
        with self.assertRaises(ValueError):
            repair.repair_targets(cues, original, {"issues": []}, True)

    def test_visible_cut_pairs_once_and_unexpected_cut_fails_threshold(self):
        plan = {"transitions": [{"id": "a", "frame": 606}, {"id": "b", "frame": 608}]}
        before = {"scenes": {"starts_s": [0, 20.2]}}
        after = {"scenes": {"starts_s": [0, 20.2, 24]}}
        measure, rows = repair.transitions(plan, before, after)
        self.assertEqual(measure, {"max_boundary_error_frames": 0, "unexpected_cuts": 1})
        self.assertEqual([row["reference_cut_frame"] for row in rows], [606, None])


if __name__ == "__main__":
    unittest.main()
