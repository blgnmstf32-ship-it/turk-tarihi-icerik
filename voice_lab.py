"""Legacy voice-test helpers. Production is now Charon-only."""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

from scripts.audio_bed import create as create_bed
from scripts.auto_produce import audio_mix_command, performance_script
from scripts.commons_media import fetch_visuals, write_attribution
from scripts.create_reel import ffprobe, media_duration, render_reel, subtitle_cues
from scripts.gemini_tts import MODEL as GEMINI_MODEL, VOICE, align_captions, request_audio
from scripts.illustrate import generate
from scripts.release_check import check
from scripts.run import ROOT, load_json
from scripts.speech_audit import load_local_model, transcribe_local
from scripts.subtitles import create_timed

TOPIC_ID = "piri-reis-kayip-kaynak"
ASR_MODEL = "small"


def topic_and_script():
    topic = next(item for item in load_json(ROOT / "data/topics.json") if item["id"] == TOPIC_ID)
    segments = performance_script(topic)
    return topic, segments, "\n".join(item["spoken"] for item in segments)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_file(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gemini_take(out, confirmed):
    _, _, script = topic_and_script()
    out.mkdir(parents=True, exist_ok=True)
    audio = out / "GEMINI_CHARON.wav"
    receipt = out / "GEMINI_RECEIPT.json"
    if audio.exists() or receipt.exists():
        raise ValueError("Gemini denemesi için yeni çıktı klasörü kullanın.")
    raw, duration = request_audio(script, confirmed)
    audio.write_bytes(raw)
    json_file(receipt, {"topic": TOPIC_ID, "model": GEMINI_MODEL, "voice": VOICE,
                        "cloud_requests": 1, "free_project_confirmed": True,
                        "duration_seconds": duration, "audio_sha256": digest(raw),
                        "script_sha256": digest(script.encode())})


def validate_gemini_take(out, script):
    receipt = load_json(out / "GEMINI_RECEIPT.json")
    expected = {"topic": TOPIC_ID, "model": GEMINI_MODEL, "voice": VOICE,
                "cloud_requests": 1, "free_project_confirmed": True,
                "script_sha256": digest(script.encode()),
                "audio_sha256": digest((out / "GEMINI_CHARON.wav").read_bytes())}
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("Gemini ses kaydı veya senaryo üretim kaydıyla eşleşmiyor.")
    return receipt


def prepare_visuals(topic, out):
    scenes = out / "scenes"
    generate(topic, scenes)
    commons = out / "commons"
    visuals = fetch_visuals(topic, commons, limit=10)
    for index, item in enumerate(visuals, 1):
        (scenes / f"{index:02d}_scene.jpg").unlink()
        shutil.copy2(commons / item["file"], scenes / item["file"])
    write_attribution(visuals, out / "MEDIA_ATTRIBUTION.md")
    return scenes, len(visuals)


def timing_metrics(captions, words, duration):
    if not captions or not words or any(not 0 <= cue["start"] < cue["end"] <= duration + .04
                                        for cue in captions):
        raise ValueError("Altyazı ve konuşma zamanlaması geçersiz.")
    if any(a["end"] > b["start"] for a, b in zip(captions, captions[1:])):
        raise ValueError("Altyazı aralıkları çakışıyor.")
    word_midpoints = [(word["start"] + word["end"]) / 2 for word in words]
    inside = sum(any(cue["start"] <= midpoint <= cue["end"] for cue in captions)
                 for midpoint in word_midpoints)
    pauses = [b["start"] - a["end"] for a, b in zip(words, words[1:]) if b["start"] - a["end"] >= .25]
    return {"caption_count": len(captions), "first_caption_end_seconds": captions[0]["end"],
            "speech_word_midpoints_in_captions": round(inside / len(words), 3),
            "asr_word_count": len(words), "pause_count_at_least_250ms": len(pauses),
            "longest_detected_pause_seconds": round(max(pauses, default=0), 2)}


def word_error_rate(script, transcript):
    words = lambda text: re.findall(r"[^\W_]+", text.translate(str.maketrans("Iİ", "ıi")).lower())
    expected, heard = words(script), words(transcript)
    row = list(range(len(heard) + 1))
    for i, word in enumerate(expected, 1):
        next_row = [i]
        for j, other in enumerate(heard, 1):
            next_row.append(min(row[j] + 1, next_row[j - 1] + 1, row[j - 1] + (word != other)))
        row = next_row
    return round(row[-1] / len(expected), 4)


def pitch_profile(voice):
    """Estimate pitch on voiced frames of the clean narrator track."""
    rate = 8000
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(voice), "-ac", "1",
                             "-ar", str(rate), "-f", "s16le", "-"], check=True, capture_output=True)
    samples = np.frombuffer(result.stdout, dtype="<i2").astype(float)
    window = rate * 45 // 1000
    first_lag, last_lag = rate // 350, rate // 65
    pitch = []
    for start in range(0, len(samples) - window + 1, rate // 20):
        frame = samples[start:start + window]
        frame = frame - frame.mean()
        if np.sqrt(np.mean(frame ** 2)) < 150:
            continue
        corr = np.correlate(frame, frame, mode="full")[window - 1:]
        region = corr[first_lag:last_lag + 1] / corr[0]
        peaks = [i for i in range(1, len(region) - 1)
                 if region[i - 1] < region[i] >= region[i + 1] and region[i] >= .45]
        if peaks:
            best = max(region[i] for i in peaks)
            lag = first_lag + next(i for i in peaks if region[i] >= best * .9)
            pitch.append(rate / lag)
    return {"estimated_voiced_frames": len(pitch),
            "f0_hz_p10_median_p90": [round(float(value), 1) for value in np.percentile(pitch, [10, 50, 90])]
            if pitch else None}


def render_side(name, out, scenes, voice, cues, segments, script, asr):
    duration = media_duration(voice)
    if len(cues) != len(segments) or not 60 <= duration <= 75 or cues[0]["end"] > 3:
        raise ValueError(f"{name}: senaryo, 60–75 saniye ve ilk 3 saniye koşullarını kontrol edin.")
    captions = out / f"{name}.srt"
    create_timed(cues, captions)
    video = out / f"PIRI_REIS_{name}_INCELEME.mp4"
    rendered = out / f"work_{name}.mp4"
    music = out / f"work_{name}.wav"
    create_bed(duration, music)
    render_reel(scenes, voice, captions, rendered)
    subprocess.run(audio_mix_command(rendered, voice, music, video), check=True, capture_output=True)
    technical = check(video, voice, captions, scenes)
    streams = ffprobe(video)["streams"]
    picture = next(item for item in streams if item["codec_type"] == "video")
    sound = next(item for item in streams if item["codec_type"] == "audio")
    if (picture["codec_name"], sound["codec_name"], Fraction(picture["r_frame_rate"])) != ("h264", "aac", 30):
        raise ValueError(f"{name}: beklenen H.264, AAC ve 30 fps biçimi doğrulanamadı.")
    mixed = out / f"work_{name}_mixed.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0", "-ac", "1",
                    "-ar", "16000", str(mixed)], check=True, capture_output=True)
    asr_result = transcribe_local(mixed, model=asr)
    transcript = " ".join(segment["text"] for segment in asr_result["segments"])
    metrics = timing_metrics(subtitle_cues(captions), asr_result["words"], duration)
    wer = word_error_rate(script, transcript)
    result = {"video": video.name, "technical": technical, "timing": metrics,
              "forced_turkish_asr_word_error_rate": wer, "transcript": transcript,
              "narrator_pitch": pitch_profile(voice),
              "asr_recognized_names": {name: name.casefold() in transcript.casefold()
                                       for name in ("Piri Reis", "Gelibolu", "Kristof Kolomb", "Topkapı")},
              "pronunciation_prosody_and_caption_review": "human_listening_required"}
    json_file(out / f"{name}_SES_KONTROLU.json", result)
    if metrics["speech_word_midpoints_in_captions"] < .85 or wer > .35:
        raise ValueError(f"{name}: son videonun konuşma veya altyazı eşleşmesi denetimden geçmedi.")
    return result


if __name__ == "__main__":
    raise SystemExit("Karşılaştırma emekli edildi. Charon için scripts.auto_produce kullanın.")
