"""Classify supplied silence intervals on the original frame clock without editing."""
from __future__ import annotations

TOOL_ID = "media-craft:pause-review"
FPS = 30
PROTECT_OPENING = 3 * FPS
PAD = 6
MIN_PAUSE = 12


def _intervals(rows, duration, maximum, *, required=False):
    if not isinstance(rows, list) or len(rows) > maximum or (required and not rows):
        raise ValueError("Invalid pause review interval list")
    previous = 0
    for row in rows:
        if (not isinstance(row, list) or len(row) != 2 or any(type(value) is not int for value in row)
                or not previous <= row[0] < row[1] <= duration):
            raise ValueError("Pause review requires ordered, nonoverlapping source frames")
        previous = row[1]
    return rows


def review_pauses(snapshot):
    """Review-only output. Caller attests both tracks were aligned to this source."""
    if (not isinstance(snapshot, dict) or set(snapshot) != {
            "fps", "duration_frames", "alignment", "silence", "narration", "captions"}
            or type(snapshot["fps"]) is not int or snapshot["fps"] != FPS
            or type(snapshot["duration_frames"]) is not int or not 900 <= snapshot["duration_frames"] <= 2700
            or snapshot["alignment"] != "reviewed_source_frame_alignment"):
        raise ValueError("Pause review requires reviewed alignment on the 30 fps source")
    duration = snapshot["duration_frames"]
    silence = _intervals(snapshot["silence"], duration, 80)
    narration = _intervals(snapshot["narration"], duration, 240, required=True)
    captions = _intervals(snapshot["captions"], duration, 240, required=True)
    result = []
    for start, end in silence:
        flags = []
        if start < PROTECT_OPENING:
            flags.append("opening_protected")
        if end - start < MIN_PAUSE:
            flags.append("short_pause")
        for name, track in (("narration", narration), ("captions", captions)):
            if any(start < right + PAD and end > left - PAD for left, right in track):
                flags.append(name + "_protected")
        result.append({"start_frame": start, "end_frame": end,
                       "status": "protected" if flags else "human_review_candidate", "reasons": flags})
    return {"source_fps": FPS, "source_duration_frames": duration, "alignment": snapshot["alignment"],
            "mode": "annotations_only", "timeline_modified": False, "media_created": False,
            "human_review_required": True, "pause_intervals": result}
