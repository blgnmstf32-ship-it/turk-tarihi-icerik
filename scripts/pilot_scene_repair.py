"""Repair the pinned 15A pilot captions without replacing the approved edit or sound."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from scripts import approved_pilot_replay as replay, beauty_reel
from scripts import media_pilot, pilot_media_measure as measure, scene_director as director
from scripts import video_quality_lab as lab
from scripts.create_reel import collect_scenes, render_reel, subtitle_cues
from scripts.editorial_state import EditorialState
from scripts.subtitles import create_timed

FPS = director.FPS
LIMIT_MS = lab.RULES["subtitle_sync"][1]["p95_offset_ms"][1]
PILOTS = {
    "history": ("PIRI_REIS_FINAL.mp4", "1003d3cf0a988bcc161af61d474e20ae596e386bfa3ff9fb9895676ac4854498",
                "tarih", "piri-reis-kayip-kaynak", "subtitles.srt", (1320, 314), "MEDIA_ATTRIBUTION.md"),
    "beauty": ("BAKIM_FINAL.mp4", "c086a69dc6847ef3cbc0816ae4d69c7ddddfb0b8c2fa953e48feed36c59b837a",
               "bakim", "kuruluk-nemlendirici-zamani", "KURU_CILT_BAKIMI.srt", (1440, 168), "MEDIA_SOURCES.txt"),
}
COLLAGE_SHA = "539f34ade6103e7297a8b62d266906bc3a3f36ac43d08955d425161c2ff7fc94"


def caption_panel_pixels(frame, brand, cv2):
    """Distinguish caption glyphs from bright background texture."""
    import numpy as np

    image = cv2.resize(frame, (360, 640), interpolation=cv2.INTER_AREA)
    top, bottom = (440, 543) if brand == "tarih" else (480, 527)
    strip = image[top:bottom]
    blue, green, red = cv2.split(strip)
    light = (red >= 210) & (green >= 160) & (green >= blue)
    dark = (red < 92) & (green < 87) & (blue < 100)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(light.astype("uint8"))
    gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
    bounds, ink, surround = [], [], []
    kernel = np.ones((7, 7), dtype="uint8")
    for index, (x, y, width, height, area) in enumerate(stats[1:count], 1):
        if not (5 <= area <= 450 and 4 <= height <= 23 and 2 <= width <= 45):
            continue
        roi = np.s_[max(0, y-3):min(y+height+3, len(strip)), max(0, x-3):min(x+width+3, 360)]
        glyph = labels[roi] == index
        near = cv2.dilate(glyph.astype("uint8"), kernel).astype(bool) & ~light[roi]
        if not near.any() or dark[roi][near].mean() < .57:
            continue
        bounds.append((int(x), int(x+width)))
        ink.extend(gray[roi][glyph])
        surround.extend(gray[roi][near])
    if len(bounds) < 4:
        return None
    left = min(start for start, _ in bounds)
    right = max(end for _, end in bounds)

    def luminance(values):
        value = float(np.median(values)) / 255
        return ((value + .055) / 1.055) ** 2.4 if value > .04045 else value / 12.92

    return {"safe_area_violations": int(left < 18 or right > 342),
            "min_contrast_ratio": round((luminance(ink) + .05) / (luminance(surround) + .05), 2),
            "glyph_bounds_phone_px": [left, right]}


def retime(cues, matches, indices):
    """Move cue onsets to actual Turkish ASR anchors on the unchanged audio."""
    edited = [dict(cue) for cue in cues]
    spans = []
    for index in indices:
        old = cues[index]
        anchor = matches[index]["spoken_start"]
        if anchor is None or abs(old["start"] - anchor) > 1.8:
            raise ValueError(f"Unreliable word anchor for cue {index+1}")
        first = round(anchor * FPS)
        # Round down to milliseconds so the chosen video frame renders the cue.
        start = math.floor(first * 1000 / FPS) / 1000
        if not 0 <= start < old["end"]:
            raise ValueError(f"Invalid replacement start for cue {index+1}")
        if index and edited[index-1]["end"] > start:
            previous = edited[index-1]
            if previous["start"] >= start:
                raise ValueError(f"Retiming would remove cue {index}")
            previous["end"] = start
        edited[index]["start"] = start
        original_first = math.ceil(old["start"] * FPS)
        # Remotion animates the caption entrance for four frames.
        spans.append((min(first, original_first), min(math.ceil(old["end"] * FPS),
                                                     max(first, original_first) + 4)))
    return edited, spans


def repair_targets(cues, original_report, quality, history):
    """Select documented failures in the hash-bound 15A evidence."""
    check = "subtitle_sync" if history else "mobile_readability"
    intervals = [row["frames"] for row in quality["issues"] if row["check"] == check and row["frames"]]
    if history:
        matches = original_report["after"]["cue_matches"]
        if len(matches) != len(cues):
            raise ValueError("15A report caption count differs from the source")
        indices = [index for index, match in enumerate(matches)
                   if match["offset_ms"] is not None and match["offset_ms"] > LIMIT_MS
                   and any(start <= match["frame"] < end for start, end in intervals)]
    else:
        indices = [index for index, cue in enumerate(cues)
                   if [round(cue["start"]*FPS), round(cue["end"]*FPS)] in intervals]
    if not indices:
        raise ValueError("No observed 15A caption failure matches the approved source")
    return indices


def scene_scope(plan, state, spans, cause):
    initial = director.preflight(plan, state)
    failures = {scene["id"]: cause for scene in plan["scenes"] if any(
        scene["start_frame"] < end and start < scene["end_frame"] for start, end in spans)}
    if not failures or len(failures) >= len(plan["scenes"]):
        raise ValueError("Expected a bounded repair")
    recheck = director.preflight(plan, state, previous_id=initial["report_sha256"], failures=failures)
    selected = set(recheck["evaluated_scene_ids"])
    ranges = []
    for start, end in spans:
        scoped = [(max(start, scene["start_frame"]), min(end, scene["end_frame"]), index)
                  for index, scene in enumerate(plan["scenes"])
                  if scene["id"] in selected and scene["start_frame"] < end and start < scene["end_frame"]]
        if sum(right-left for left, right, _ in scoped) != end-start:
            raise ValueError("Scene Director did not return the full caption scope")
        ranges.extend(scoped)
    return initial, recheck, ranges


def render_history(args, topic, voice, srt, spans, work):
    from scripts import final_media_qa as qa

    photos = args.history / "auto/commons_visuals"
    collage = args.baseline / "TARIH_KOLAJ_HYPERFRAMES.mp4"
    if replay._hash(collage) != COLLAGE_SHA:
        raise ValueError("Approved HyperFrames insert changed")
    layers = work / "parallax"
    qa.authored_map_layers(collect_scenes(photos)[0], layers)
    three = qa.plan_3d_scenes(topic, qa.media_duration(voice))["scenes"]
    edit = {"title": topic["title"], "topic": topic["id"], "hook": qa.performance_script(topic)[0]["caption"],
            "animation": {"style": "paper_collage", "insert": str(collage), "continuous": True}}
    parts = []
    for index, (start, end) in enumerate(spans):
        clip = work / f"caption-{index}.mp4"
        render_reel(photos, voice, srt, clip, three_scenes=three, edit=edit,
                    parallax_dir=layers, browser=args.browser, frame_range=(start, end))
        parts.append((start, end, clip))
    return parts


def render_beauty(plan, ranges, cues, compact, picture, preset, work):
    ass = work / "captions.ass"
    beauty_reel.styled_captions(cues, ass, compact=compact)
    parts = []
    for left, right, index in ranges:
        scene = plan["scenes"][index]
        first, last = scene["start_frame"], scene["end_frame"]
        _, kind, label, title, note = beauty_reel.SHOTS[index]
        shot = beauty_reel.shot(work, index, last-first, kind, picture, label, title, note,
                                title_effect=preset if index == 0 else None)
        part = work / f"caption-{index}.mp4"
        replay._ffmpeg("-i", work / shot, "-vf",
                       f"trim=start_frame={left-first}:end_frame={right-first},"
                       f"settb=1/{FPS},setpts=N+{left},ass={ass},setpts=N,fps={FPS}",
                       "-an", "-c:v", "libx264", "-bf", "0", "-qp", "0", "-threads", "2", part)
        parts.append((left, right, part))
    return parts


def compose(original, parts, band, output):
    """Place the new caption band on its original global frame numbers."""
    from scripts import final_media_qa as qa

    inputs, filters = ["-i", original], ["[0:v]settb=1/30,setpts=N[original]"]
    top, height = band
    previous = "original"
    cursor = 0
    for index, (start, end, path) in enumerate(parts, 1):
        if not cursor <= start < end or qa.checked_frame_video(path)["video_frames"] != end-start:
            raise ValueError("Replacement clip shifted or overlaps the existing timeline")
        inputs.extend(("-i", path))
        filters.append(f"[{index}:v]crop=1080:{height}:0:{top},settb=1/30,setpts=N+{start}[band{index}]")
        filters.append(f"[{previous}][band{index}]overlay=0:{top}:eof_action=pass:repeatlast=0:"
                       f"format=yuv420:enable='between(n,{start},{end-1})'[video{index}]")
        previous = f"video{index}"
        cursor = end
    replay._ffmpeg(*inputs, "-filter_complex", ";".join(filters), "-map", f"[{previous}]", "-map", "0:a:0",
                   "-c:a", "copy", "-c:v", "libx264", "-qp", "0", "-threads", "4", "-pix_fmt", "yuv420p",
                   "-r", "30", "-fps_mode", "cfr", "-movflags", "+faststart", output)


def frame_hashes(path, crop=None):
    args = ["-vf", crop] if crop else []
    data = replay._ffmpeg("-i", path, "-map", "0:v:0", "-an", *args, "-f", "framemd5", "-").stdout
    return [line.rsplit(b",", 1)[-1].strip() for line in data.splitlines() if not line.startswith(b"#")]


def audio_hash(path):
    return replay._ffmpeg("-i", path, "-map", "0:a:0", "-c:a", "copy", "-f", "hash", "-").stdout


def transitions(plan, reference, current):
    def cut_frames(metrics):
        return {round(second * FPS) for second in metrics["scenes"]["starts_s"] if second > 0}

    tolerance = lab.RULES["transitions"][1]["max_boundary_error_frames"][1]
    planned = {cut["frame"] for cut in plan["transitions"]}
    anchors = {}
    for frame in sorted(cut_frames(reference)):
        nearest = min(planned, key=lambda at: (abs(at-frame), at))
        if abs(nearest-frame) > tolerance or nearest in anchors:
            raise ValueError(f"Reference cut {frame} has no distinct planned boundary")
        anchors[nearest] = frame
    remaining = cut_frames(current)
    boundaries = []
    for cut in plan["transitions"]:
        at = cut["frame"]
        before = anchors.get(at)
        matches = [frame for frame in remaining if before is not None and abs(frame-before) <= tolerance]
        actual = min(matches, key=lambda frame: (abs(frame-before), frame)) if matches else None
        remaining.discard(actual)
        error = abs(actual-at) if actual is not None else tolerance+1 if before is not None else 0
        boundaries.append({"id": cut["id"], "plan_frame": at, "reference_cut_frame": before,
                           "measured_cut_frame": actual, "error_frames": error})
    return {"max_boundary_error_frames": max(row["error_frames"] for row in boundaries),
            "unexpected_cuts": len(remaining)}, boundaries


def audit(video, plan, cues, metrics, voice, reference, state):
    import numpy as np

    evidence, sampled = measure.collect(video, plan, cues, metrics, voice, caption_measure=caption_panel_pixels)
    sampled["mobile_scope"] = "backed_glyph_pixels_360x640_each_cue_midpoint"
    observations = evidence["observations"]
    mobile = [row["sampled_phone_pixels"] for row in sampled["mobile_subtitle_samples"]]
    offsets = [row["offset_ms"] for row in metrics["cue_matches"]]
    matched = [value for value in offsets if value is not None]
    if len(matched) == len(cues):
        observations.setdefault("subtitle_sync", []).append(measure._observation("subtitle_sync", {
            "matched_fraction": 1.0, "p95_offset_ms": round(float(np.percentile(matched, 95)), 2)}))
    visibility = [sample for sample in mobile if sample is not None]
    for row in observations.get("mobile_readability", []):
        row["values"] = {key: value for key, value in row["values"].items() if key != "glyph_bounds_phone_px"}
    if len(visibility) == len(cues):
        observations.setdefault("mobile_readability", []).append(measure._observation("mobile_readability", {
            "safe_area_violations": sum(sample["safe_area_violations"] for sample in visibility),
            "min_contrast_ratio": min(sample["min_contrast_ratio"] for sample in visibility),
        }, collector="opencv-caption-pixels"))
    cut_result, sampled["boundaries"] = transitions(plan, reference, metrics)
    observations["transitions"] = [measure._observation("transitions", cut_result)]
    quality, _ = lab.evaluate(plan, evidence=evidence, state=state)
    summary = {"captions": len(cues), "captions_sampled": len(visibility), "captions_aligned": len(matched),
               "max_offset_ms": round(float(max(matched)), 2) if matched else None,
               "mean_offset_ms": metrics["asr"]["mean_start_error_ms"], "levels": metrics["levels"],
               "transitions": cut_result}
    return quality, {"evidence": evidence, "sampled": sampled}, summary


def run(args):
    from scripts import final_media_qa as qa

    name, digest, brand, topic_id, subtitle, band, attribution = PILOTS[args.brand]
    original = args.baseline / name
    baseline = beauty_reel.read_json(args.baseline / "FINAL_QA.json")
    if replay._hash(original) != digest or baseline["media"]["sha256"] != digest:
        raise ValueError("Input is not the pinned 15A MP4")
    prior_quality = beauty_reel.read_json(args.baseline / lab.REPORT)
    if prior_quality["asset_sha256"] != digest:
        raise ValueError("15A quality evidence points to a different video")
    inputs = replay.verify_inputs(args, original)
    history = brand == "tarih"
    source = (args.history / "auto" if history else args.beauty) / subtitle
    if replay._hash(source) != replay._hash(args.baseline / subtitle):
        raise ValueError("Pinned subtitles differ from approved source")
    if history:
        voice = qa.ROOT / "data/GEMINI_CHARON.wav"
    else:
        voice, picture, *_ = beauty_reel.inputs(args.beauty_assets)
    if replay._hash(voice) != baseline["approved_voice_sha256"]:
        raise ValueError("Approved voice checksum changed")

    topic = director._load_topic(brand, topic_id, None)
    media = qa.checked_frame_video(original)
    frames = media["video_frames"]
    cues = subtitle_cues(source)
    plan = replay.production_plan(brand, topic, cues, frames)
    args.out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.baseline / attribution, args.out / attribution)
    state = EditorialState(args.out / ".scene-state.sqlite3")
    meter = qa.Measurements(args.out / "PERFORMANCE.json")
    write = qa.write
    model = media_pilot.load_local_model(str(args.model))
    old = meter.measure("baseline_media", qa.metrics, original, cues, model, timeline=True)
    before, old_evidence, old_summary = meter.measure("baseline_quality", audit, original, plan, cues, old, voice, old, state)
    write(args.out / "BASELINE.json", {"quality": before, "summary": old_summary, "cue_matches": old["cue_matches"]})

    indices = repair_targets(cues, baseline, prior_quality, history)
    if history:
        edited, spans = retime(cues, old["cue_matches"], indices)
        cause, engine = "sync_failed", "media:remotion"
    else:
        edited = cues
        spans = [(round(cues[i]["start"]*FPS), round(cues[i]["end"]*FPS)) for i in indices]
        cause, engine = "quality_failed", "media:ffmpeg"
    initial, recheck, ranges = scene_scope(plan, state, spans, cause)
    srt = create_timed(edited, args.out / subtitle)
    timeline = replay._timeline(plan, args.out)
    write(args.out / director.PLAN, plan)
    write(args.out / "APPROVED_INPUTS.json", inputs)
    candidate = args.out / "CANDIDATE.mp4"
    with TemporaryDirectory(dir=args.out) as tmp:
        work = Path(tmp)
        if history:
            parts = meter.measure("scoped_remotion", render_history, args, topic, voice, srt, spans, work)
        else:
            preset = initial["scenes"]["s01"]["local_preflight"]["opening_preset"]
            parts = meter.measure("scoped_ffmpeg", render_beauty, plan, ranges, edited, [i+1 for i in indices],
                                  picture, preset["effect"], work)
        meter.measure("lossless_assembly", compose, original, parts, band, candidate)

    result = qa.checked_frame_video(candidate, length=media["seconds"])
    left = frame_hashes(original)
    right = frame_hashes(candidate)
    allowed = {i for start, end in spans for i in range(start, end)}
    changed = {i for i, (a, b) in enumerate(zip(left, right)) if a != b}
    upper = f"crop=1080:{band[0]}:0:0"
    upper_equal = frame_hashes(original, upper) == frame_hashes(candidate, upper)
    sound_equal = audio_hash(original) == audio_hash(candidate)
    if not (len(left) == len(right) == frames and changed and changed <= allowed and upper_equal and sound_equal):
        raise ValueError(f"Repair altered approved frames or sound: upper={upper_equal} audio={sound_equal} "
                         f"changed_outside={len(changed-allowed)}")
    new = meter.measure("repaired_media", qa.metrics, candidate, edited, model, timeline=True)
    after, new_evidence, new_summary = meter.measure(
        "repaired_quality", audit, candidate, plan, edited, new, voice, old, state)
    passed = (after["technical"]["status"] == "pass"
              and new_summary["captions_aligned"] == new_summary["captions_sampled"] == len(cues)
              and new_summary["max_offset_ms"] is not None and new_summary["max_offset_ms"] <= LIMIT_MS)
    recovery = {"status": "replaced_selected_scenes" if passed else "candidate_rejected", "renderer": engine,
                "frame_ranges": spans, "scene_ids": recheck["evaluated_scene_ids"],
                "transition_ids": recheck["evaluated_transition_ids"], "changed_frames": len(changed),
                "identical_frames": frames-len(changed), "frames_outside_scope_identical": frames-len(allowed),
                "upper_video_identical": upper_equal, "aac_bitstream_identical": sound_equal}
    write(args.out / director.REPORT, {"phase": "approved_caption_repair", "otio_scene_order": timeline,
                                      "preflight": initial, "quality_recheck": recheck, "recovery": recovery})
    write(args.out / lab.REPORT, after)
    write(args.out / "MEASUREMENT_EVIDENCE.json", {"before": old_evidence, "after": new_evidence})
    report = {"status": "human_review_required" if passed else "candidate_rejected", "technical_pass": passed,
              "original_media": media, "repaired_media": result, "before": old_summary, "after": new_summary,
              "before_caption_offsets": old["cue_matches"], "after_caption_offsets": new["cue_matches"],
              "recovery": recovery, "paid_api_calls": 0, "instagram_auto_publish": False}
    write(args.out / "FINAL_QA.json", report)
    if not passed:
        raise ValueError(f"Repair candidate failed: {after['issues']}; {new_summary}")
    candidate.replace(args.out / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", required=True, choices=PILOTS)
    for field in ("baseline", "history", "beauty", "beauty-assets", "model", "browser", "out"):
        parser.add_argument("--" + field, required=True, type=lambda path: Path(path).resolve())
    run(parser.parse_args())


if __name__ == "__main__":
    main()
