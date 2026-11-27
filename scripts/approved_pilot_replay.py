"""Render and audit the two hash-pinned pilot asset packs without providers."""
from __future__ import annotations

import json
import math
from pathlib import Path
from importlib.metadata import version
import shutil
import subprocess
from tempfile import TemporaryDirectory

from scripts import beauty_reel, scene_director as director, scene_otio, video_quality_lab as lab
from scripts.create_reel import ffprobe, render_reel, subtitle_cues
from scripts.editorial_state import EditorialState
from scripts.skill_router import RouteContext, select_knowledge

FPS = 30
ASSET_LOCK = Path(__file__).resolve().parents[1] / "data/pilot_replay_lock.json"
TIMELINE = "SCENE_TIMELINE.otio"
REPAIR_CHECKS = {"black_frames", "frozen_frames"}
RENDER_EXCEPTIONS = (OSError, RuntimeError, ValueError, subprocess.SubprocessError)


def _hash(path):
    from scripts.motion_toolkit import sha256_file

    return sha256_file(path)


def verify_inputs(args, previous):
    """Verify exact Actions inputs, including all ten archival images and the prior final."""
    locked = json.loads(ASSET_LOCK.read_text())
    roots = {"history": args.history, "beauty": args.beauty,
             "assets": args.beauty_assets, "previous": previous.parent}
    receipt = []
    for folder, files in locked[args.brand].items():
        for name, expected in files.items():
            source = roots[folder] / name
            allowed = expected if isinstance(expected, list) else [expected]
            found = _hash(source) if source.is_file() else None
            if found not in allowed:
                raise ValueError(f"Missing or changed approved asset: {folder}/{name}")
            receipt.append({"asset_set": folder, "file": name, "sha256": found})
    return receipt


def _history_cuts(frames):
    # Match DocumentaryReel's base scene boundaries and the established overlay compositions.
    regular = [math.floor(i * frames / 10) for i in range(1, 10)]
    return sorted({81, 96, 246, 342, 606, *regular, frames})


def production_plan(brand, topic, cues, frames):
    if brand == "tarih":
        ends = _history_cuts(frames)
        starts = [0, *ends[:-1]]
        kinds = ["collage" if 96 <= start < 246 else "map" if 342 <= start < 606 else "flat"
                 for start in starts]
        starts_at = {81: "opening_title_end", 96: "collage_insert_start", 246: "collage_insert_end",
                     342: "atlas_start", 606: "atlas_end"}
    else:
        kinds_by_shot = {"skin": "diagram", "cream": "macro", "barrier": "barrier"}
        ends = [round(row[0] * FPS) for row in beauty_reel.SHOTS[1:]] + [frames]
        starts = [0, *ends[:-1]]
        kinds = [kinds_by_shot.get(row[1], "flat") for row in beauty_reel.SHOTS]
        starts_at = {}
    # Keep the approved words separate from the visual cut boundaries. A cue may span multiple shots.
    lines = [" ".join(cue["text"] for cue in cues if round(cue["start"]*FPS) < end
                       and round(cue["end"]*FPS) > start) or "—" for start, end in zip(starts, ends)]
    script_key = "narration" if brand == "tarih" else "script"
    scene_topic = {**topic, script_key: lines}
    plan = director.build_plan(brand, scene_topic, duration_frames=frames, end_frames=ends,
                               overrides={str(i): {"kind": kind} for i, kind in enumerate(kinds, 1)})
    plan["opening_has_parallax"] = brand == "tarih"
    plan["timing"] = "approved_pilot_visual_boundaries"
    plan["narration_scope"] = "approved_caption_overlap_not_recording_chunks"
    for index, scene in enumerate(plan["scenes"]):
        start, end = starts[index], ends[index]
        scene["captions"] = {"source": "approved_srt", "active_cue_indices": [
            i for i, cue in enumerate(cues, 1) if round(cue["start"] * FPS) < end
            and round(cue["end"] * FPS) > start]}
        if brand == "tarih":
            image_index = min(9, max(i for i in range(10) if math.floor(i * frames / 10) <= start))
            scene["approved_visual"] = {"archive_index": image_index + 1,
                                        "layer_change": starts_at.get(start)}
        else:
            scene["approved_visual"] = {"shot": beauty_reel.SHOTS[index][1]}
            # The finished video uses FFmpeg for its 2D beauty scenes. Keep the director proposal visible.
            scene["production_recipe"] = "existing_pilot_ffmpeg_assembly"
    return plan


def _timeline(plan, out):
    from opentimelineio import core, schema

    serialized = scene_otio.timeline_json(plan)
    decoded = core.deserialize_json_from_string(serialized)
    track = decoded.tracks[0]
    expected = [(s["id"], s["end_frame"]-s["start_frame"]) for s in plan["scenes"]]
    if [(clip.name, clip.duration().to_frames(FPS)) for clip in track] != expected or any(
            not isinstance(clip.media_reference, schema.MissingReference) for clip in track):
        raise ValueError("OpenTimelineIO round-trip changed scene timing or references")
    (out / TIMELINE).write_text(serialized, encoding="utf-8")
    return [clip.name for clip in track]


def actual_scenes(plan, preflight, art):
    result = {}
    for scene in plan["scenes"]:
        key = scene["id"]
        kind = scene["kind"]
        if plan["brand"] == "tarih":
            renderer, technique = "media:remotion", "archive_camera_and_captions"
            support = []
            if kind == "map" and art["history_three"]["status"] == "rendered":
                support.append("media:three-js")
                technique = "three_js_gsap_atlas"
            if kind == "collage" and art["history_motion"]["status"] == "applied" and art["hyperframes"]["stage"] == "insert_prepared":
                support.append("media:hyperframes")
                technique = "hyperframes_gsap_paper_insert"
            if art["history_motion"]["status"] == "applied" and scene["approved_visual"]["archive_index"] == 1:
                technique += "+authored_2_5d"
        else:
            renderer = "media:ffmpeg"
            technique = {"diagram": "blender_cross_section", "macro": "three_js_cream_macro",
                         "barrier": "three_js_barrier_macro"}.get(kind, "layered_graphic_pan")
            support = (["media:blender"] if kind == "diagram" else
                       ["media:remotion", "media:three-js"] if kind in {"macro", "barrier"} else [])
        result[key] = {**preflight["scenes"][key], "render_status": "rendered",
                       "frame_range": [scene["start_frame"], scene["end_frame"]],
                       "executed_renderer": renderer, "executed_scene_tools": support,
                       "actual_technique": technique, "selected_skill_notes": scene["skills"],
                       "craft_notes": scene.get("craft_review"), "specialist_llm_called": False}
    return result


def _ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-filter_threads", "2",
                           "-filter_complex_threads", "2", *[str(arg) for arg in args]],
                          check=True, capture_output=True, timeout=360)


def _merge_ranges(failures, plan):
    return [(scene["id"], scene["start_frame"], scene["end_frame"], i)
            for i, scene in enumerate(plan["scenes"]) if scene["id"] in failures]


def _selected_video_issues(quality, plan):
    found = set()
    for issue in quality["issues"]:
        if issue["check"] in REPAIR_CHECKS and issue["frames"]:
            start, end = issue["frames"]
            # Only a bounded defect is repairable. A defective source across the whole video needs review.
            if 0 < end-start <= 300:
                found.update(scene["id"] for scene in plan["scenes"]
                             if scene["start_frame"] < end and scene["end_frame"] > start)
    return found


def _replace_visual(args, named, voice, srt, topic, plan, previous, selections, cache):
    """Replace only selected decoded frame intervals; retain the intact AAC track."""
    from scripts import final_media_qa as previous_pipeline

    repaired = named / "repair_candidate.mp4"
    with TemporaryDirectory(dir=named, prefix="scene-repair-") as temporary:
        work = Path(temporary)
        pieces, inputs, cursor = [], ["-i", previous], 0
        for _, start, end, index in _merge_ranges(selections, plan):
            part = work / f"repair-{index:02d}.mp4"
            if args.brand == "history":
                render_reel(args.history / "auto/commons_visuals", voice, srt, part,
                            edit={"title": topic["title"], "topic": topic["id"], "hook": topic.get("hook") or topic["title"]},
                            browser=args.browser, frame_range=(start, end))
            else:
                _, picture, *_ = beauty_reel.inputs(args.beauty_assets)
                _, kind, label, title, note = beauty_reel.SHOTS[index]
                clip = beauty_reel.shot(cache, index, end-start, kind, picture, label, title, note, repair=True)
                # ASS positioning is evaluated at the original global caption frame times.
                _ffmpeg("-i", cache / clip, "-vf",
                        f"settb=1/{FPS},setpts=N+{start},ass={cache / 'captions.ass'},setpts=N,fps={FPS}",
                        "-an", "-c:v", "libx264", "-bf", "0", "-fps_mode", "cfr",
                        "-crf", "17", "-threads", "2", part)
            checked = previous_pipeline.checked_frame_video(part)
            if checked["video_frames"] != end-start:
                raise ValueError("Repair render changed the scene's exact frame count")
            if cursor < start:
                pieces.append(f"[0:v]trim=start_frame={cursor}:end_frame={start},setpts=PTS-STARTPTS[v{len(pieces)}]")
            number = len(inputs) // 2
            inputs += ["-i", part]
            pieces.append(f"[{number}:v]setpts=PTS-STARTPTS[v{len(pieces)}]")
            cursor = end
        if cursor < plan["duration_frames"]:
            pieces.append(f"[0:v]trim=start_frame={cursor},setpts=PTS-STARTPTS[v{len(pieces)}]")
        labels = "".join(f"[v{i}]" for i in range(len(pieces)))
        # Lossless final reassembly preserves decoded pixels outside the replacement intervals.
        _ffmpeg(*inputs, "-filter_complex", ";".join(pieces) + f";{labels}concat=n={len(pieces)}:v=1:a=0[out]",
                "-map", "[out]", "-map", "0:a:0", "-c:a", "copy", "-c:v", "libx264", "-qp", "0",
                "-threads", "3", "-pix_fmt", "yuv420p", "-r", FPS, "-fps_mode", "cfr",
                "-movflags", "+faststart", repaired)
    return repaired


def _frame_hashes(video):
    output = _ffmpeg("-i", video, "-map", "0:v:0", "-an", "-f", "framemd5", "-").stdout
    return [line.rsplit(b",", 1)[-1].strip() for line in output.splitlines() if not line.startswith(b"#")]


def _intact(original_hashes, new_hashes, selections, plan):
    if len(original_hashes) != len(new_hashes) or len(new_hashes) != plan["duration_frames"]:
        return False
    return all(original_hashes[a:b] == new_hashes[a:b] for s in plan["scenes"] if s["id"] not in selections
               for a,b in [(s["start_frame"], s["end_frame"])])


def project(args):
    from scripts import final_media_qa as qa, media_pilot
    from scripts.pilot_media_measure import collect

    named = args.out / args.brand
    named.mkdir(parents=True, exist_ok=False)
    write = qa.write
    clock = qa.Measurements(named / "PERFORMANCE.json")
    name = "PIRI_REIS_FINAL.mp4" if args.brand == "history" else "BAKIM_FINAL.mp4"
    previous = args.previous / name
    receipts = verify_inputs(args, previous)
    write(named / "APPROVED_INPUTS.json", receipts)
    node_versions = {name: json.loads((qa.ROOT / location / name / "package.json").read_text())["version"]
                     for location, name in (("node_modules", "remotion"), ("node_modules", "three"),
                                            ("node_modules", "gsap"), ("media_pilot/node_modules", "hyperframes"))}
    write(named / "TOOL_VERSIONS.json", {
        **node_versions, **{name: version(name) for name in ("OpenTimelineIO", "faster-whisper", "scenedetect")},
        "browser": subprocess.check_output([args.browser, "--version"], text=True, timeout=10).strip(),
        "ffmpeg": subprocess.check_output(["ffmpeg", "-version"], text=True, timeout=10).splitlines()[0],
        "blender": (subprocess.check_output(["blender", "--version"], text=True, timeout=10).splitlines()[0]
                    if args.brand == "beauty" else None)})
    _, voice, _, srt = media_pilot.source_inputs(args, args.brand)
    brand = "tarih" if args.brand == "history" else "bakim"
    if brand == "tarih":
        topic = director._load_topic(brand, "piri-reis-kayip-kaynak", None)
        cues = subtitle_cues(srt)
    else:
        topic = {**beauty_reel.read_json(beauty_reel.DATA / "beauty_reel_kuruluk.json"),
                 "category": "kuru_cilt", "visual_mode": "layer_diagram"}
        *_, cues = beauty_reel.inputs(args.beauty_assets)
        shutil.copyfile(beauty_reel.DATA / "beauty_reel_aciklama.txt", named / "MEDIA_SOURCES.txt")
    duration = qa.media_duration(voice)
    plan = production_plan(brand, topic, cues, math.ceil(duration * FPS))
    state = EditorialState(named / ".scene-state.sqlite3")
    initial = director.preflight(plan, state)
    write(named / director.PLAN, plan)
    timeline_order = clock.measure("otio_plan_round_trip", _timeline, plan, named)
    role_id = 16 if brand == "tarih" else 20
    knowledge = select_knowledge(RouteContext(brand, role_id, "video-quality"))
    preset = initial["scenes"]["s01"]["local_preflight"].get("opening_preset") or {}
    cache = named / "_beauty_shots"
    if brand == "tarih":
        base, art = qa.history_render(args, named, clock, voice, srt, route=preset)
    else:
        base, art = qa.beauty_render(args, named, clock, cache=cache, route=preset)
        srt = base.parent / "KURU_CILT_BAKIMI.srt"
        shutil.copyfile(srt, named / srt.name)
    final = named / name
    profile = qa.media_pilot.read(qa.ROOT / "media_pilot/profiles.json")[args.brand]
    profile["seconds"] = duration
    effects = named / "sfx"
    effects.mkdir()
    try:
        foley, receipt = clock.measure("earshot_real_sfx_cues", media_pilot.effects, args.brand, profile, effects, 5.1)
    except RENDER_EXCEPTIONS as exc:
        shutil.copyfile(base, final)
        art["sound_effects"] = {"status": "unavailable", "reason": type(exc).__name__}
    else:
        clock.measure("final_sound_mix", qa.final_audio, base, foley, final)
        art["sound_effects"] = {"status": "mixed", **receipt}
    former = qa.checked_frame_video(previous, length=duration)
    if qa.checked_frame_video(final, length=duration)["audio_codec"] != "aac":
        raise ValueError("Expected the approved audio in an AAC track")
    model = media_pilot.load_local_model(str(args.model))
    old = clock.measure("analysis_previous", qa.metrics, previous, cues, model, timeline=True)
    before_evidence, before_measured = clock.measure("quality_evidence_previous", collect,
                                                      previous, plan, cues, old, voice)
    before_quality, _ = lab.evaluate(plan, evidence=before_evidence, state=state)
    new = clock.measure("analysis_current", qa.metrics, final, cues, model, timeline=True)
    evidence, measured = clock.measure("quality_evidence", collect, final, plan, cues, new, voice)
    quality, recheck = lab.evaluate(plan, evidence=evidence, state=state, previous_id=initial["report_sha256"])
    chosen = _selected_video_issues(quality, plan)
    recovery = {"status": "not_needed" if not chosen else "candidate_pending",
                "eligible_scene_ids": [key for key in timeline_order if key in chosen]}
    if chosen:
        try:
            video = clock.measure("scoped_repair", _replace_visual, args, named, voice, srt, topic,
                                  plan, final, chosen, cache)
            pixels_unchanged = _intact(_frame_hashes(final), _frame_hashes(video), chosen, plan)
            repair_evidence, repair_measured = clock.measure("repair_quality_evidence", collect,
                                                            video, plan, cues, new, voice)
            repaired, _ = lab.evaluate(plan, evidence=repair_evidence, state=state)
            if pixels_unchanged and not _selected_video_issues(repaired, plan):
                video.replace(final)
                recovery["status"] = "replaced_selected_scenes"
                recovery["preserved_non_target_decoded_frames"] = True
                recovery["executed_renderer"] = "media:remotion" if brand == "tarih" else "media:ffmpeg"
                evidence, measured, quality = repair_evidence, repair_measured, repaired
            else:
                recovery.update(status="candidate_rejected", non_target_frames_preserved=pixels_unchanged)
        except RENDER_EXCEPTIONS as exc:
            recovery.update(status="repair_failed", reason=type(exc).__name__)
    final_media = qa.checked_frame_video(final, length=duration)
    clock.measure("comparison", qa.comparison, previous, final, named / "ONCE_SONRA.mp4", "00:00:00")
    review_path = (named if brand == "tarih" else named / "beauty_base") / "REELS_EDITORIAL_REVIEW.json"
    original_review = json.loads(review_path.read_text())
    quality["editorial"].update(status=original_review["status"], score=original_review["best"]["total"],
                                score_scope=original_review["score_scope"])
    # Actual renderer events and offline Scene Director review remain separate.
    rendered = actual_scenes(plan, initial, art)
    if recovery["status"] == "replaced_selected_scenes":
        for key in chosen:
            rendered[key].update(render_status="rendered_after_scoped_repair",
                                 initial_executed_renderer=rendered[key]["executed_renderer"],
                                 executed_renderer=recovery["executed_renderer"],
                                 actual_technique="scoped_approved_pilot_repair")
    write(named / director.REPORT, {
        "phase": "approved_pilot_render", "plan_sha256": director._digest(plan), "otio_scene_order": timeline_order,
        "scenes": rendered, "transitions": plan["transitions"], "preflight": initial,
        "quality_recheck": recheck, "scene_recovery": recovery, "qa_skill_notes": knowledge, "animation": art})
    write(named / lab.REPORT, quality)
    write(named / "MEASUREMENT_EVIDENCE.json", {"evidence": evidence, "observed": measured,
                                                       "before_evidence": before_evidence, "before_observed": before_measured})
    write(named / "FINAL_QA.json", {
        "status": "human_review_required", "brand": args.brand, "media": final_media, "previous_media": former,
        "before": old, "after": new, "previous_technical": before_quality["technical"], "technical_status": quality["technical"]["status"], "recovery": recovery,
        "paid_api_calls": 0, "instagram_auto_publish": False, "approved_voice_sha256": _hash(voice)})
    checks = quality["technical"]["checks"]
    mobile = measured["mobile_subtitle_samples"]
    print(json.dumps({
        "brand": brand, "media": final_media, "technical": quality["technical"]["status"],
        "check_statuses": {key: review["status"] for key, review in checks.items()},
        "opening": checks["opening"]["observations"], "sync_ms": [old["asr"]["mean_start_error_ms"],
                                                                 new["asr"]["mean_start_error_ms"]],
        "audio_separation": measured["audio_separation"], "mixed_loudness": new["levels"],
        "mobile_samples": sum(bool(row["sampled_phone_pixels"]) for row in mobile), "captions_sampled": len(mobile),
        "before_issues": before_quality["issues"], "issues": quality["issues"], "recovery": recovery,
        "actual_scene_tools": sorted({tool for row in rendered.values() for tool in row["executed_scene_tools"]}),
    }, ensure_ascii=False), flush=True)
