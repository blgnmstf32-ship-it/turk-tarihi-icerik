"""Offline, read-only assessment of a Scene Director timeline and local evidence."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from hashlib import file_digest
from pathlib import Path

from scripts import reels_editorial
from scripts.editorial_state import EditorialState
from scripts.performance_learning import reels_benchmarks

TOOL_ID = "quality-lab:local-review"
REPORT = "VIDEO_QUALITY_LAB.json"

# Production review thresholds, expressed in frames or the unit in the field name.
RULES = {
    "opening": ("ffmpeg+faster-whisper", {"first_picture_frame": (0, 15), "first_word_frame": (0, 89)}),
    "narration": ("faster-whisper", {"words_per_minute": (95, 180)}),
    "visual_repeat": ("opencv-dhash64", {"min_hamming_distance": (6, 64)}),
    "subtitle_sync": ("faster-whisper+srt", {"matched_fraction": (0.9, 1), "p95_offset_ms": (0, 350)}),
    "mobile_readability": ("playwright-dom", {"safe_area_violations": (0, 0), "min_contrast_ratio": (4.5, 21)}),
    "black_frames": ("ffmpeg-blackdetect", {"unexpected_black_frames": (0, 0)}),
    "frozen_frames": ("ffmpeg-freezedetect", {"unexpected_frozen_frames": (0, 0)}),
    "audio_balance": ("ffmpeg-loudnorm+stems", {"integrated_lufs": (-19, -13), "true_peak_dbtp": (-99, -1),
                                              "voice_over_bed_db": (8, 70)}),
    "transitions": ("pyscenedetect+review", {"max_boundary_error_frames": (0, 6),
                                           "unexpected_cuts": (0, 0)}),
}
DIAGNOSTICS = {"vmaf": "ffmpeg-libvmaf"}
CODES = {"subtitle_sync": "sync_failed", "source_accuracy": "source_unverified"}
RECHECK_PRIORITY = ("source_unverified", "sync_failed", "quality_failed")
QA_ROLES = {"tarih": 16, "bakim": 20}


def _number(value):
    return type(value) in (int, float) and -1e12 <= value <= 1e12


def _span(value, end):
    if (not isinstance(value, list) or len(value) != 2 or any(type(x) is not int for x in value)
            or not 0 <= value[0] < value[1] <= end):
        raise ValueError("Invalid half-open frame interval")
    return value


def _scene_index(plan):
    from scripts import scene_director as director

    if (plan["brand"] not in QA_ROLES or plan["fps"] != director.FPS or plan["resolution"] != [1080, 1920]
            or type(plan["duration_frames"]) is not int or not 900 <= plan["duration_frames"] <= 2700):
        raise ValueError("Unsupported Scene Director timeline")
    scenes = plan["scenes"]
    if not 2 <= len(scenes) <= 40:
        raise ValueError("Invalid scene count")
    index = {}
    cursor = 0
    for position, scene in enumerate(scenes, 1):
        start, end = _span([scene["start_frame"], scene["end_frame"]], plan["duration_frames"])
        if start != cursor or scene["id"] != f"s{position:02}":
            raise ValueError("Invalid scene boundaries")
        cursor = end
        index[scene["id"]] = scene
    if cursor != plan["duration_frames"] or plan["transitions"] != director._cuts(scenes):
        raise ValueError("Scene timeline or cuts do not match")
    return index


def _covers(spans, end):
    cursor = 0
    for start, stop in sorted(spans):
        if start > cursor:
            return False
        cursor = max(cursor, stop)
    return cursor == end


def _metrics(name, values):
    _, rules = RULES[name]
    if not isinstance(values, dict) or values.keys() != rules.keys() or not all(map(_number, values.values())):
        raise ValueError("Missing or invalid numeric measures")
    return [metric for metric, (lo, hi) in rules.items() if not lo <= values[metric] <= hi]


def inspect_snapshot(snapshot, *, brand):
    """Allowlisted Tool Router entrypoint. It interprets evidence and has no I/O."""
    from scripts import scene_director as director

    if not isinstance(snapshot, dict) or set(snapshot) - {"plan", "evidence"}:
        raise ValueError("Invalid local quality snapshot")
    plan = snapshot["plan"]
    if plan["brand"] != brand:
        raise ValueError("Quality snapshot brand mismatch")
    scenes = _scene_index(plan)
    duration = plan["duration_frames"]
    plan_id = director._digest(plan)
    evidence = snapshot.get("evidence")
    if evidence is None:
        evidence = {"plan_sha256": plan_id, "observations": {}, "source_reviews": []}
    if evidence.get("plan_sha256") != plan_id:
        raise ValueError("Quality evidence does not match this scene plan")
    asset_id = evidence.get("asset_sha256")
    if asset_id is not None and (not isinstance(asset_id, str) or not director.SHA.fullmatch(asset_id)):
        raise ValueError("Invalid media fingerprint")
    observations = evidence.get("observations", {})
    if observations.keys() - (RULES.keys() | DIAGNOSTICS.keys()):
        raise ValueError("Unknown measurement")
    technical, issues = {}, []
    for name, (collector, thresholds) in RULES.items():
        rows = observations.get(name, [])
        if not isinstance(rows, list) or len(rows) > 160:
            raise ValueError("Invalid measurement samples")
        limit = min(3 * plan["fps"], duration) if name == "opening" else duration
        results = []
        for row in rows:
            if row.get("collector") != collector:
                raise ValueError("Unsupported measurement provenance")
            frames = (_span(row["frames"], limit) if "frames" in row else
                      [0, limit] if name == "opening" else None)
            cut_id = row.get("transition_id")
            if cut_id is not None and (name != "transitions" or not frames or not any(
                    cut["id"] == cut_id and frames[0] <= cut["frame"] < frames[1] for cut in plan["transitions"])):
                raise ValueError("Invalid transition scope")
            if row.get("candidate") is True:
                if name not in {"black_frames", "frozen_frames"} or not frames or "values" in row:
                    raise ValueError("Invalid detector candidate")
                results.append({"frames": frames, "candidate": True, "outside_thresholds": []})
                continue
            failed = _metrics(name, row["values"])
            results.append({"frames": frames, "transition_id": cut_id, "values": row["values"],
                            "outside_thresholds": failed})
            if failed:
                issues.append({"check": name, "frames": frames, "transition_id": cut_id})
        covered = (any(r["frames"] is None for r in results) or
                   _covers([r["frames"] for r in results if r["frames"]], limit))
        technical[name] = {"status": ("fail" if any(r["outside_thresholds"] for r in results)
                                      else "needs_review" if any(r.get("candidate") for r in results)
                                      else "pass" if covered else "partial" if results else "not_measured"),
                           "collector": collector, "thresholds": thresholds, "observations": results}

    # VMAF is a reference-dependent diagnostic, with no pass gate and no fallback score.
    vmaf = observations.get("vmaf")
    diagnostic = {"status": "not_measured", "reason": "aligned_reference_and_libvmaf_required"}
    if vmaf is not None:
        if (vmaf.get("collector") != DIAGNOSTICS["vmaf"] or vmaf.get("aligned") is not True
                or not _number(vmaf.get("score")) or not 0 <= vmaf["score"] <= 100
                or not director.SHA.fullmatch(vmaf.get("reference_sha256", ""))
                or not director.SHA.fullmatch(vmaf.get("distorted_sha256", ""))
                or vmaf["distorted_sha256"] != asset_id
                or vmaf["reference_sha256"] == asset_id):
            raise ValueError("Unsupported VMAF evidence")
        diagnostic = {"status": "measured", **{key: vmaf[key] for key in (
            "collector", "score", "reference_sha256", "distorted_sha256")}}

    raw_reviews = evidence.get("source_reviews", [])
    if not isinstance(raw_reviews, list) or len(raw_reviews) > len(scenes):
        raise ValueError("Invalid source review list")
    reviews = {}
    for row in raw_reviews:
        scene_id = row["scene_id"]
        scene = scenes.get(scene_id)
        if not scene or scene_id in reviews or row["status"] not in {"verified", "unverified"}:
            raise ValueError("Invalid or repeated source review")
        refs = row.get("source_numbers", [])
        if (not isinstance(refs, list) or any(type(n) is not int for n in refs)
                or not set(refs).issubset({r["number"] for r in plan["sources"]})):
            raise ValueError("Unknown source reference")
        note = row.get("finding")
        if (not isinstance(note, str) or not note.strip() or len(note) > 480
                or row["status"] == "verified" and not refs):
            raise ValueError("A source finding and verified passage reference are required")
        reviews[scene_id] = {"status": row["status"], "source_numbers": refs, "finding": note}
        if row["status"] == "unverified":
            issues.append({"check": "source_accuracy", "frames": [scene["start_frame"], scene["end_frame"]],
                           "transition_id": None})
    source_accuracy = {"method": "supplied_human_source_review", "scenes": {
        key: reviews.get(key, {"status": "not_reviewed"}) for key in scenes}}
    source_accuracy["status"] = ("needs_review" if any(r["status"] == "unverified" for r in reviews.values())
                                 else "verified" if len(scenes) == len(reviews) else "not_reviewed")

    scene_causes, untargeted = {}, []
    for issue in issues:
        start_end = issue["frames"]
        if start_end is None or start_end == [0, duration]:
            untargeted.append(issue["check"])
            continue
        if issue["transition_id"]:
            cut = next(cut for cut in plan["transitions"] if cut["id"] == issue["transition_id"])
            targets = (cut["left"], cut["right"])
        else:
            start, end = start_end
            targets = [key for key, row in scenes.items()
                       if row["start_frame"] < end and row["end_frame"] > start]
        for key in targets:
            scene_causes.setdefault(key, set()).add(CODES.get(issue["check"], "quality_failed"))
    failures = {key: next(code for code in RECHECK_PRIORITY if code in causes)
                for key, causes in sorted(scene_causes.items())}
    status = ("fail" if any(r["status"] == "fail" for r in technical.values()) else
              "pass" if all(r["status"] == "pass" for r in technical.values()) else
              "needs_review" if any(r["status"] == "needs_review" for r in technical.values()) else
              "partial" if any(r["observations"] for r in technical.values()) else "not_measured")
    return {"plan_sha256": plan_id, "asset_sha256": asset_id, "brand": brand, "duration_frames": duration,
            "technical": {"status": status, "checks": technical, "vmaf": diagnostic},
            "source_accuracy": source_accuracy, "issues": issues,
            "scene_recheck": {"failures": failures, "unlocated_checks": sorted(set(untargeted))}}


def evaluate(plan, *, evidence=None, topic=None, performance=(), state=None, previous_id=None):
    """Run the same local assessment used by the router and optionally scope a dry recheck."""
    from scripts import scene_director as director

    from scripts.skill_router import RouteContext
    from scripts.tool_router import run_tool

    brand = plan["brand"]
    if state is None:
        result = inspect_snapshot({"plan": plan, "evidence": evidence}, brand=brand)
        routing = None
    else:
        routing = run_tool(RouteContext(brand, QA_ROLES[brand], "video-quality"),
                           topic=plan["topic"], state=state,
                           snapshots={TOOL_ID: {"plan": plan, "evidence": evidence}})
        if routing["status"] not in {"success", "cache"}:
            raise ValueError("Video quality Tool Router rejected the local evidence")
        result = routing.pop("result")
    edit = {"status": "not_scored", "threshold": reels_editorial.THRESHOLD}
    if topic is not None:
        lines = [scene["narration"]["text"] for scene in plan["scenes"]]
        script = "narration" if brand == "tarih" else "script"
        if (topic["id"] != plan["topic"]["id"] or lines != [line.strip() for line in topic[script]]
                or director._topic_sources(topic) != plan["sources"]):
            raise ValueError("Editorial input does not match the planned script and sources")
        rating = reels_editorial.review(topic, brand, lines, fixed_recording=True)
        edit.update(status=rating["status"], score=rating["best"]["total"], blockers=rating["blockers"],
                    hook_score=rating["best"]["scores"]["hook"], hook_candidates=len(rating["hooks"]),
                    scenario_candidates=len(rating["scenarios"]))
    source_accuracy = result.pop("source_accuracy")
    failures = result["scene_recheck"]["failures"]
    if previous_id and state is None:
        raise ValueError("Scene continuity requires the original local state")
    recheck = director.preflight(plan, state, previous_id=previous_id, failures=failures) if previous_id and failures else None
    return {**result, "schema_version": 1,
            "editorial": {**edit, "score_is_viral_probability": False, "source_accuracy": source_accuracy},
            "instagram_performance": reels_benchmarks(performance, brand),
            "scene_recheck": {**result["scene_recheck"],
                              "status": "offline_rechecked" if recheck else "awaiting_prior_preflight" if failures else "no_targets",
                              "report_sha256": (recheck or {}).get("report_sha256")},
            "tool_route": routing, "human_approval_required": True, "media_created": False,
            "api_calls": 0, "instagram_published": False}, recheck



def _detected_intervals(log, name, duration, fps):
    """Parse FFmpeg event boundaries. A freeze reaching EOF lacks an end event."""
    fragments = re.findall(rf"\b{name}_(start|end):\s*(-?\d+(?:\.\d+)?)", log)
    start, spans = None, []
    for edge, time in fragments:
        frame = max(0, min(duration, round(float(time) * fps)))
        if edge == "start" and start is None:
            start = frame
        elif edge == "end" and start is not None and frame > start:
            spans.append([start, frame])
            start = None
        else:
            raise ValueError("Invalid FFmpeg interval")
    if start is not None and start < duration:
        spans.append([start, duration])
    return spans


def collect_ffmpeg(path, plan):
    """Optional local measurement of an existing MP4. No render or output media."""
    from scripts import scene_director as director

    _scene_index(plan)
    media = Path(path).resolve(strict=True)
    if media.suffix.casefold() != ".mp4" or not media.is_file() or media.stat().st_size > 1_000_000_000:
        raise ValueError("Expected an existing local MP4 of up to 1 GB")
    # Force the MOV/MP4 demuxer, prohibit network protocols and external MP4 media references.
    policy = ["-protocol_whitelist", "file", "-f", "mov", "-enable_drefs", "0"]
    probe = subprocess.run(["ffprobe", "-v", "error", *policy, "-i", str(media), "-select_streams", "v:0",
                            "-show_entries", "stream=width,height,avg_frame_rate,nb_frames", "-of", "json"],
                           capture_output=True, text=True, check=True, timeout=30)
    stream, = json.loads(probe.stdout)["streams"]
    if ([stream["width"], stream["height"]] != plan["resolution"]
            or stream["avg_frame_rate"] != f"{plan['fps']}/1"
            or int(stream["nb_frames"]) != plan["duration_frames"]):
        raise ValueError("MP4 dimensions or frame timebase differ from the scene plan")
    filters = "blackdetect=d=0.25:pix_th=0.10,freezedetect=n=-60dB:d=1"
    measured = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-xerror", "-v", "info", *policy,
                               "-threads", "2", "-i", str(media), "-map", "0:v:0", "-an", "-sn", "-dn",
                               "-filter_threads", "1", "-vf", filters, "-f", "null", "-"],
                              capture_output=True, text=True, check=True, timeout=120)
    observations = {}
    for check, event, metric in (("black_frames", "black", "unexpected_black_frames"),
                                 ("frozen_frames", "freeze", "unexpected_frozen_frames")):
        spans = _detected_intervals(measured.stderr, event, plan["duration_frames"], plan["fps"])
        # Detector hits are candidates until an editor resolves intentional fades/holds.
        observations[check] = [
            {"collector": RULES[check][0], "frames": span, "candidate": True} for span in spans
        ] or [{"collector": RULES[check][0], "values": {metric: 0}}]
    with media.open("rb") as handle:
        asset_id = file_digest(handle, "sha256").hexdigest()
    return {"plan_sha256": director._digest(plan), "asset_sha256": asset_id, "observations": observations}


def main(argv=None):
    from scripts import scene_director as director

    from scripts.content_strategy import load_learning

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--evidence", type=Path)
    inputs.add_argument("--existing-mp4", type=Path, help="Read-only FFmpeg black/frozen-frame review")
    parser.add_argument("--topic", type=Path)
    parser.add_argument("--performance", type=Path, help="Local read-only Meta Insights JSONL archive")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--previous-report", help="Report SHA-256 in the original Scene Director state")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.previous_report and args.state is None:
        parser.error("--previous-report requires --state")
    args.out.mkdir(parents=True, exist_ok=True)
    state = EditorialState(args.state or args.out / ".scene-state.sqlite3")
    plan = director._read(args.plan)
    evidence = (director._read(args.evidence) if args.evidence else
                collect_ffmpeg(args.existing_mp4, plan) if args.existing_mp4 else None)
    report, recheck = evaluate(plan, state=state, previous_id=args.previous_report, evidence=evidence,
                               topic=director._read(args.topic) if args.topic else None,
                               performance=load_learning(args.performance) if args.performance else ())
    director._write(args.out / REPORT, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if recheck:
        director._write(args.out / director.REPORT, json.dumps(recheck, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"technical": report["technical"]["status"], "editorial": report["editorial"]["status"],
                      "instagram": report["instagram_performance"]["status"]}))
    failed = (report["technical"]["status"] == "fail"
              or report["editorial"]["status"] in {"blocked_by_editorial_safety", "needs_human_revision"}
              or report["editorial"]["source_accuracy"]["status"] == "needs_review")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
