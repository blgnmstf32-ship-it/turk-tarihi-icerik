"""Audit a real production package by stage and transcribe its final MP4 audio."""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from scripts.auto_produce import performance_script
from scripts.editorial_llm import discussion_completed
from scripts.create_reel import collect_scenes, ffprobe, media_duration, subtitle_cues
from scripts.run import ROOT, load_json, select_topic
from scripts.speech_audit import compare_reference


def verify(out, explicit_topic="", *, require_approved_charon=False, require_3d=False):
    out = Path(out)
    board = load_json(out / "editorial" / "EDITORIAL_DECISION_REPORT.json")
    report = load_json(out / "AUTO_REPORT.json")
    topic = select_topic(load_json(ROOT / "data/topics.json"), explicit_topic, board)
    research = board["research"]
    llm = board["coordinator_llm"]
    llm_completed = discussion_completed(llm)
    stage = {}

    def assess(name, passed, **details):
        stage[name] = {"status": "passed" if passed else "failed", **details}

    rss_videos = sum(len(channel["videos"]) for channel in research["competitors"] if channel.get("channel_url"))
    assess("research", bool(rss_videos or research["trends"] or research.get("source_leads")),
           rss_competitor_videos=rss_videos, trends=len(research["trends"]),
           academic_metadata_leads=len(research.get("source_leads", [])),
           public_metrics=research.get("metrics_coverage", {}), provider_errors=research.get("errors", []))
    stage["ai_review"] = {"status": "passed" if llm_completed else "blocked" if llm.get("status") == "blocked" else "failed",
                         "calls": llm["calls"], "gemini_calls": llm.get("gemini_calls", 0),
                         "cloudflare_calls": llm.get("cloudflare_calls", 0), "requirements_missing": llm.get("requirements_missing", []),
                         "completed_discussion": llm_completed,
                         "role_statuses": [{k: item.get(k) for k in ("role", "status", "provider", "model", "http_status", "response_source", "error_type", "attempts", "queued")}
                                           for item in llm.get("stages", [])]}
    experts = report.get("ai_editor", {})
    results = [row for row in experts.get("roles", []) if row.get("role_id") and row.get("status") == "proposal"
               and row.get("actual_llm_used") and row.get("model")]
    dispatch, comparison = experts.get("dispatch") or {}, experts.get("comparison") or {}
    assess("specialists", bool(results and dispatch.get("status") == "proposal"
           and comparison.get("status") == "proposal" and comparison.get("actual_llm_used")
           and sorted(comparison.get("answer", {}).get("considered_role_ids", [])) == sorted(row["role_id"] for row in results)
           and llm["calls"] + experts.get("calls", 0) <= experts.get("max_combined_calls", 0)),
           selected_role_ids=[row["role_id"] for row in (dispatch.get("answer") or {}).get("assignments", [])],
           completed_role_ids=[row["role_id"] for row in results], specialist_calls=experts.get("calls", 0),
           comparison_status=comparison.get("status"), comparison_source=comparison.get("response_source"),
           gemini_calls=experts.get("gemini_calls", 0), cloudflare_calls=experts.get("cloudflare_calls", 0))
    assess("topic_selection", bool(topic and topic["id"] == report["topic"]), rendered=report["topic"],
           expected=topic["id"] if topic else None,
           method="manual_topic" if explicit_topic else "editorial_report_and_prepared_catalogue")
    reference = (out / "NARRATION_TR.txt").read_text(encoding="utf-8")
    script_matches = topic and reference.splitlines() == [line["spoken"] for line in performance_script(topic)]
    sources = load_json(out / "sources.json")
    assess("script", bool(script_matches and sources and sources == topic["sources"]),
           word_count=len(reference.split()), source_urls=[s["url"] for s in sources],
           historic_claims_need_human_review=True)

    audio_path = out / "narration.wav"
    duration = media_duration(audio_path)
    captions = subtitle_cues(out / "subtitles.srt")
    from scripts.gemini_tts import APPROVED_AUDIO, MODEL, VOICE
    import hashlib
    gen = report.get("voice_generation", {})
    verified_reuse = (gen.get("source") == "approved_charon_recording" and gen.get("cloud_requests") == 0
                      and APPROVED_AUDIO.get(hashlib.sha256(reference.strip().encode()).hexdigest()) ==
                      hashlib.sha256(audio_path.read_bytes()).hexdigest())
    verified_cache = (gen.get("source") == "cached_charon_recording" and gen.get("cloud_requests") == 0
                      and gen.get("script_sha256") == hashlib.sha256(reference.strip().encode()).hexdigest()
                      and gen.get("audio_sha256") == hashlib.sha256(audio_path.read_bytes()).hexdigest())
    assess("narration", bool(report["voice_generated"] and 60 <= duration <= 75 and captions
                             and gen.get("model") == MODEL and gen.get("voice") == VOICE
                             and (verified_reuse or (not require_approved_charon
                                  and (verified_cache or (gen.get("source") == "live_charon" and gen.get("cloud_requests") == 1))))),
           provider=report["voice_provider"], duration_seconds=round(duration, 2),
           caption_cues=len(captions), gemini_live=gen.get("cloud_requests") == 1, approved_reuse=verified_reuse, generated_cache_reuse=verified_cache)

    scenes = collect_scenes(out / "scenes")
    licensed = report["licensed_visual_count"]
    assess("visuals", len(scenes) >= 10 and (out / "MEDIA_ATTRIBUTION.md").is_file()
           and (not require_3d or report["three_d"]["status"] == "rendered"),
           distinct_input_scenes=len(scenes), licensed_visual_count=licensed, visual_kind=report["visual_kind"],
           realistic_visuals_gate=report["realistic_visuals_gate"], three_d_status=report["three_d"]["status"],
           three_d_scenes_rendered=report["three_d"]["scene_count_rendered"])

    final = out / "REVIEW_REQUIRED_REEL.mp4"
    info = ffprobe(final)
    video = next((stream for stream in info["streams"] if stream["codec_type"] == "video"), {})
    audio = next((stream for stream in info["streams"] if stream["codec_type"] == "audio"), {})
    with TemporaryDirectory(prefix="final_speech_audit_") as work:
        mixed_voice = Path(work) / "mixed.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-map", "0:a:0", "-ac", "1",
                        "-ar", "16000", str(mixed_voice)], check=True, capture_output=True)
        speech = compare_reference(mixed_voice, reference, max_word_error_rate=0.35)
    (out / "TURKCE_SES_KONTROLU.json").write_text(
        json.dumps({"input": final.name, "language_mode": "forced Turkish ASR", **speech}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    assess("editing", (out / "reel_with_voice.mp4").is_file() and (out / "original_soundtrack.wav").is_file(),
           renderer=report["renderer"], role_count=report["roles"], audio_verified_from_final_mix=True)
    video_duration = float(info["format"]["duration"])
    hook = report["first_hook_seconds"]
    assess("mp4", bool(video.get("codec_name") == "h264" and audio.get("codec_name") == "aac" and
                       (video.get("width"), video.get("height")) == (1080, 1920) and
                       Fraction(video.get("r_frame_rate", "0")) == 30 and 60 <= video_duration <= 75 and
                       (not topic or not topic.get("narration") or (hook is not None and hook <= 3)) and
                       report["technical_review"]["technical_gate"] == "passed" and speech["status"] == "passed"),
           file=final.name, duration_seconds=round(video_duration, 2), video_codec=video.get("codec_name"),
           audio_codec=audio.get("codec_name"), dimensions=[video.get("width"), video.get("height")],
           fps=video.get("r_frame_rate"), first_hook_seconds=hook, asr_word_error_rate=speech["word_error_rate"])
    return {"stages": stage, "full_live_path": all(item["status"] == "passed" for item in stage.values()),
            "instagram_published": report["instagram_published"], "human_approval_required": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--topic", default="")
    parser.add_argument("--require-llm", action="store_true")
    parser.add_argument("--require-specialists", action="store_true")
    parser.add_argument("--require-approved-charon", action="store_true")
    parser.add_argument("--require-3d", action="store_true")
    args = parser.parse_args()
    result = verify(args.out, args.topic, require_approved_charon=args.require_approved_charon,
                    require_3d=args.require_3d)
    path = Path(args.out) / "E2E_REPORT.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
    optional = {"ai_review": args.require_llm, "specialists": args.require_specialists}
    for name, stage in result["stages"].items():
        if stage["status"] != "passed" and optional.get(name, True):
            parser.exit(1, f"Aşama doğrulanamadı: {name}\n")


if __name__ == "__main__":
    main()
