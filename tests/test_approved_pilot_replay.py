import unittest

from scripts import approved_pilot_replay as replay
from scripts.scene_director import _load_topic
from scripts.video_quality_lab import _scene_index


class ApprovedPilotReplayTests(unittest.TestCase):
    def test_piri_plan_preserves_cuts_and_overlapping_cues(self):
        plan = replay.production_plan("tarih", _load_topic("tarih", "piri-reis-kayip-kaynak", None),
                                      [{"start": 2.6, "end": 4.3, "text": "Kaynaklı altyazı"}], 2028)
        _scene_index(plan)
        scenes = plan["scenes"]
        self.assertEqual(scenes[0]["end_frame"], 81)
        self.assertEqual(scenes[-1]["end_frame"], 2028)
        for frame, kind in ((96, "collage"), (342, "map"), (606, "flat")):
            self.assertEqual(next(s for s in scenes if s["start_frame"] == frame)["kind"], kind)
        self.assertEqual([s["captions"]["active_cue_indices"] for s in scenes[:3]], [[1], [1], [1]])

    def test_beauty_geometry_source_choices_and_scoped_repair(self):
        topic = _load_topic("bakim", "kuruluk-nemlendirici-zamani", None)
        plan = replay.production_plan("bakim", topic, [], 2154)
        _scene_index(plan)
        self.assertEqual([s["kind"] for s in plan["scenes"] if s["kind"] != "flat"],
                         ["diagram", "macro", "barrier"])
        issues = {"issues": [{"check": "black_frames", "frames": [50, 70]},
                             {"check": "subtitle_sync", "frames": [90, 150]},
                             {"check": "frozen_frames", "frames": [400, 800]}]}
        targets = replay._selected_video_issues(issues, plan)
        self.assertEqual(targets, {"s01"})
        original = [b"same"] * 2154
        self.assertTrue(replay._intact(original, [b"changed"] * 90 + original[90:], targets, plan))
        self.assertFalse(replay._intact(original, [b"changed"] * 91 + original[91:], targets, plan))
