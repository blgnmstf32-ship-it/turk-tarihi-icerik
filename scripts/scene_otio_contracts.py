"""Run the optional native OTIO round-trip check in an isolated test environment."""
import unittest
from unittest.mock import patch

import opentimelineio as otio

from scripts.scene_director import _load_topic, build_plan
from scripts.scene_otio import timeline_json


class TimelineInteropTests(unittest.TestCase):
    def test_native_cpu_round_trip_for_both_brands_without_plugin_discovery(self):
        topics = (("tarih", "piri-reis-kayip-kaynak"), ("bakim", "kuruluk-nemlendirici-zamani"))
        for brand, identifier in topics:
            plan = build_plan(brand, _load_topic(brand, identifier, None))
            with (self.subTest(brand=brand),
                  patch("opentimelineio.plugins.ActiveManifest", side_effect=AssertionError("plugin discovery"))):
                timeline = otio.core.deserialize_json_from_string(timeline_json(plan))
                track = timeline.tracks[0]
                cut_lengths = [scene["end_frame"] - scene["start_frame"] for scene in plan["scenes"]]
                self.assertEqual([clip.name for clip in track], [row["id"] for row in plan["scenes"]])
                self.assertEqual([(clip.duration().value, clip.duration().rate) for clip in track],
                                 [(frames, plan["fps"]) for frames in cut_lengths])
                self.assertEqual(track.duration().value, plan["duration_frames"])
                self.assertTrue(all(isinstance(clip.media_reference, otio.schema.MissingReference) for clip in track))
                self.assertFalse(timeline.metadata["scene_director"]["rendered"])
