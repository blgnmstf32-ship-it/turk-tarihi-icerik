"""Opt-in OpenTimelineIO core export of approved plan timing, with no media references."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

OTIO_VERSION = "0.18.1"


def timeline_json(plan):
    try:
        installed = version("OpenTimelineIO")
    except PackageNotFoundError:
        raise RuntimeError("OTIO export requires the optional pinned requirements-scene-otio.txt") from None
    if installed != OTIO_VERSION:
        raise RuntimeError(f"OTIO export requires version {OTIO_VERSION}")
    try:
        import opentimelineio as otio
    except ImportError:
        raise RuntimeError("The optional OpenTimelineIO core could not be loaded") from None

    rate = plan["fps"]
    timeline = otio.schema.Timeline(name=plan["topic"]["id"])
    timeline.metadata["scene_director"] = {"timing": plan["timing"], "rendered": False,
                                          "transition_review": plan["transitions"]}
    track = otio.schema.Track(name="Storyboard", kind=otio.schema.TrackKind.Video)
    for scene in plan["scenes"]:
        duration = scene["end_frame"] - scene["start_frame"]
        track.append(otio.schema.Clip(
            name=scene["id"], media_reference=otio.schema.MissingReference(),
            source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, rate),
                                                 otio.opentime.RationalTime(duration, rate)),
            metadata={"scene_director": {"purpose": scene["purpose"], "start_frame": scene["start_frame"],
                                         "planned_renderer": scene["render"]["primary"]["id"]}},
        ))
    timeline.tracks.append(track)
    # Core JSON serialization is explicit. No adapters, plugin discovery or media-linker hooks.
    return otio.core.serialize_json_to_string(timeline) + "\n"
