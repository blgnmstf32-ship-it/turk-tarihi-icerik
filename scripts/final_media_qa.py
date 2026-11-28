"""One-shot CPU comparison of the two approved pilots using existing media only."""
from __future__ import annotations

import argparse
from difflib import SequenceMatcher
from statistics import median
import json
import os
from pathlib import Path
import re
import resource
import shutil
import threading
from time import perf_counter

from PIL import Image, ImageDraw, ImageFilter
import psutil

from scripts import animation_styles, media_pilot
from scripts.auto_produce import audio_mix_command, performance_script, render_motion_or_base
from scripts.beauty_reel import VIDEO, assemble, inputs
from scripts.create_reel import collect_scenes, ffprobe, media_duration, render_reel, subtitle_cues
from scripts.daily_editorial import STORY_CATALOGUE, render_story, story_candidates
from scripts.beauty_studio import draw_story
from scripts.gemini_tts import approved_recording
from scripts.motion_layers import reviewed_parallax
from scripts.motion_quality import optional_vmaf
from scripts.reels_editorial import write_review
from scripts.speech_audit import transcribe_local
from scripts.three_scene import plan_3d_scenes

ROOT = media_pilot.ROOT
write = media_pilot.write
ff = media_pilot.ff
run = media_pilot.run
digest = media_pilot.digest


def cpu():
    return sum(getattr(resource.getrusage(who), attr)
               for who in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)
               for attr in ("ru_utime", "ru_stime"))


class Measurements:
    def __init__(self, path):
        self.path = path
        self.stages = {}
        self.process = psutil.Process()
        self.host = {"logical_cpus": len(self.process.cpu_affinity()), "cpu_model": cpu_model(),
                     "physical_ram_mib": round(psutil.virtual_memory().total / 2**20),
                     "github_run_id": os.getenv("GITHUB_RUN_ID")}

    def save(self):
        write(self.path, {"runner": self.host, "stages": self.stages,
                          "rss": "peak sampled parent and descendant RSS summed every 0.20 s"})

    def measure(self, label, function, *args, **kwargs):
        stopped = threading.Event()
        peak = 0

        def sample():
            nonlocal peak
            while not stopped.is_set():
                resident = 0
                for proc in [self.process, *self.process.children(recursive=True)]:
                    try:
                        resident += proc.memory_info().rss
                    except psutil.Error:
                        pass
                peak = max(peak, resident)
                stopped.wait(.20)

        watcher = threading.Thread(target=sample, daemon=True)
        wall, usage = perf_counter(), cpu()
        watcher.start()
        succeeded = False
        try:
            result = function(*args, **kwargs)
            succeeded = True
            return result
        finally:
            stopped.set()
            watcher.join()
            seconds, cpu_seconds = perf_counter() - wall, cpu() - usage
            self.stages[label] = {
                "status": "completed" if succeeded else "failed",
                "wall_seconds": round(seconds, 3), "cpu_seconds": round(cpu_seconds, 3),
                "mean_core_equivalents": round(cpu_seconds / seconds, 3),
                "peak_tree_rss_mib": round(peak / 2**20, 1),
            }
            self.save()


def cpu_model():
    if Path("/proc/cpuinfo").is_file():
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.partition(":")[2].strip()
    return None


def authored_map_layers(picture, folder):
    # Illustrated relief for a flat manuscript, not reconstructed geographic depth.
    with Image.open(picture) as source:
        image = source.convert("RGBA")
    w, h = image.size
    folder.mkdir()
    layers = []
    zones = (((.08, .16), (.87, .21), (.93, .68), (.13, .77)),
             ((.31, .35), (.73, .32), (.81, .59), (.37, .69)))
    for index, (points, travel) in enumerate(zip(zones, (4, 8)), 1):
        mask = Image.new("L", image.size)
        ImageDraw.Draw(mask).polygon([(round(x*w), round(y*h)) for x, y in points], fill=185 - index*22)
        layer = image.copy()
        layer.putalpha(mask.filter(ImageFilter.GaussianBlur(w*.04)))
        path = folder / f"layer-{index}.png"
        layer.save(path)
        layers.append({"name": path.name, "sha256": digest(path), "travel_px": travel})
    write(folder / "parallax.json", {"image_sha256": digest(picture), "layers": layers,
                                    "human_review_required": True,
                                    "method": "two authored paper planes; no depth model inference"})
    reviewed_parallax(picture, folder)
    return layers


def checked_frame_video(path, *, length=None):
    info = ffprobe(path)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    if (video["width"], video["height"], video["avg_frame_rate"], video["codec_name"]) != (1080, 1920, "30/1", "h264"):
        raise ValueError("Expected a vertical H.264 1080×1920 video at 30 fps.")
    seconds = float(info["format"]["duration"])
    if length is not None and abs(seconds - length) > .15:
        raise ValueError("Narration length changed in the render.")
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    return {"seconds": seconds, "video_frames": int(video["nb_frames"]), "audio_codec": audio and audio["codec_name"],
            "sha256": digest(path), "bytes": path.stat().st_size}


def history_render(args, out, meters, voice, srt, *, route=None):
    topic = next(t for t in media_pilot.read(ROOT / "data/topics.json") if t["id"] == "piri-reis-kayip-kaynak")
    segments = performance_script(topic)
    script = "\n".join(row["spoken"] for row in segments)
    approved_recording(ROOT / "data", script)
    review = meters.measure("viral_review_before_media", write_review, out, topic, "tarih", script.splitlines(),
                            fixed_recording=True)
    media = args.history / "auto"
    photos = collect_scenes(media / "commons_visuals")
    if len(photos) != 10 or digest(photos[1]) != "3677bb061d9f8f784fa7b233062c089660b0d2edec2dd97d45a071a3e23d4804":
        raise ValueError("Unexpected archive pack or licensed collage input.")
    shutil.copyfile(media / "MEDIA_ATTRIBUTION.md", out / "MEDIA_ATTRIBUTION.md")
    shutil.copyfile(srt, out / "subtitles.srt")
    depth = meters.measure("parallax_prepare", authored_map_layers, photos[0], out / "parallax")
    photo = photos[1], {"source": "https://commons.wikimedia.org/wiki/File:Giacomo_Maggiolo_1563_Portolan_chart_(Eastern_Mediterranean)_20260724_110232.jpg",
                        "license": "CC0-1.0", "attribution": "Iacopo Maggiolo · CC0 · Karşılaştırma eseri",
                        "commercial_use_reviewed": True, "sha256": digest(photos[1])}
    collage, collage_status = meters.measure("hyperframes_collage", animation_styles.render_collage,
        "tarih", "Bir portolan haritasını okumak", 5, out / "TARIH_KOLAJ_HYPERFRAMES.mp4", photo=photo)
    style = {"style": "paper_collage", "insert": str(collage), "continuous": True} if collage else {"style": "continuous_camera"}
    silent = out / "tarih_remotion_work.mp4"
    plan = plan_3d_scenes(topic, media_duration(voice))
    def renderer(*inputs, **kwargs):
        return render_reel(*inputs, **kwargs, browser=args.browser)

    _, three, motion = meters.measure("remotion_full_history", render_motion_or_base, renderer,
        media / "commons_visuals", voice, srt, silent, plan=plan,
        edit={"title": topic["title"], "topic": topic["id"], "hook": segments[0]["caption"],
              "effect": route.get("effect") if route is not None else "lines-reveal", "animation": style}, parallax_dir=out / "parallax")
    from scripts.audio_bed import create as create_bed

    music = out / "score_work.wav"
    meters.measure("history_music_bed", create_bed, media_duration(voice), music, maritime=True)
    base = out / "tarih_mix_work.mp4"
    meters.measure("history_voice_music", run, audio_mix_command(silent, voice, music, base), timeout=180)
    return base, {"viral_review_score": review["best"]["total"], "parallax_layers": depth,
                  "history_three": three, "history_motion": motion, "hyperframes": collage_status}


def beauty_render(args, out, meters, *, cache=None, route=None):
    # assemble() runs its fixed-recording editorial review before opening assets or rendering.
    base = out / "beauty_base"
    meters.measure("beauty_full_blender_three_ffmpeg", assemble, args.beauty_assets, base, browser=args.browser,
                   cache=cache, routed_effect=(route or {}).get("effect"))
    result = media_pilot.read(base / "DOGRULAMA.json")
    return base / VIDEO, {"viral_review_score": result["editorial_index"],
                         "beauty_render": result}


def render_character(args, out):
    return run([ROOT/"node_modules/.bin/remotion", "render", "remotion/index.tsx", "EditorialCharacter",
                out, "--props", json.dumps({"brand": "tarih" if args.brand=="history" else "bakim"}),
                "--browser-executable", args.browser, "--muted", "--concurrency=2", "--codec=h264",
                "--license-key=free-license"], timeout=180)


def final_audio(base, effects, final):
    mix = ("[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit[v][key];"
           "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=.65[fx];"
           "[fx][key]sidechaincompress=threshold=.021:ratio=9:attack=14:release=280[duck];"
           "[v][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=.85:level=0:latency=1[o]")
    ff("-i", base, "-i", effects, "-filter_complex", mix, "-map", "0:v", "-map", "[o]",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", final)


def comparison(before, after, out, start):
    # Sequential vertical comparison keeps both captions at readable full width.
    left, right = ["ÖNCE", "SONRA"]
    graph = (f"[0:v]setpts=PTS-STARTPTS,drawtext=text={left}:font=DejaVu Sans:fontsize=40:"
             f"fontcolor=white:box=1:boxcolor=black@0.7:x=64:y=226[v0];"
             f"[1:v]setpts=PTS-STARTPTS,drawtext=text={right}:font=DejaVu Sans:fontsize=40:"
             "fontcolor=white:box=1:boxcolor=black@0.7:x=64:y=226[v1];"
             "[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a0];"
             "[1:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a1];"
             "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
    ff("-ss", start, "-t", 8, "-i", before, "-ss", start, "-t", 8, "-i", after,
       "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
       "-threads", "3", "-preset", "veryfast", "-crf", 20, "-c:a", "aac", "-movflags", "+faststart", out)


def metrics(path, cues, model, *, timeline=False, transcript=None):
    import cv2
    import numpy as np
    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector

    cv2.setNumThreads(2)
    seconds = media_duration(path)
    transcript = transcribe_local(path, model=model) if transcript is None else transcript
    expected = media_pilot.normalize(" ".join(cue["text"] for cue in cues))
    heard = media_pilot.normalize(" ".join(row["text"] for row in transcript["segments"]))
    tokens, times = [], []
    for word in transcript["words"]:
        word_tokens = media_pilot.normalize(word["text"])
        tokens.extend(word_tokens)
        times.extend([word["start"]] * len(word_tokens))
    matches = {i+k: times[j+k] for i, j, length in SequenceMatcher(None, expected, tokens, autojunk=False)
               .get_matching_blocks() for k in range(length)}
    offset, errors, cue_matches = 0, [], []
    for cue in cues:
        count = len(media_pilot.normalize(cue["text"]))
        # A match within the first three tokens limits ambiguous offset estimates.
        first = next((matches[i] for i in range(offset, offset + min(3, count)) if i in matches), None)
        if first is not None:
            errors.append(abs(cue["start"] - first))
        cue_matches.append({"frame": round(cue["start"] * 30), "spoken_start": first,
                            "offset_ms": abs(cue["start"] - first) * 1000 if first is not None else None})
        offset += count
    timing = {"aligned_cues": len(errors), "median_start_error_ms": round(1000*median(errors), 1) if errors else None,
              "mean_start_error_ms": round(1000*sum(errors)/len(errors), 1) if errors else None}
    sample = cv2.VideoCapture(str(path))
    variances, lumas = [], []
    try:
        for step in range(1, 12):
            sample.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000 * step/12)
            ok, frame = sample.read()
            if not ok:
                continue
            gray = cv2.cvtColor(cv2.resize(frame, (270, 480), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
            variances.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            lumas.append(float(gray.mean()))
    finally:
        sample.release()
    if not variances or not heard:
        raise ValueError("No video or Turkish speech samples decoded.")
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=24, min_scene_len=8))
    manager.detect_scenes(open_video(str(path)))
    scenes = manager.get_scene_list(start_in_scene=True)
    lengths = [(end-start).get_seconds() for start, end in scenes]
    levels, _ = media_pilot.loudness(path)
    detail = {"cue_matches": cue_matches, "word_starts": times} if timeline else {}
    return {**detail, "asr": {"language": transcript["language"], "wer": round(media_pilot.distances(expected, heard)/len(expected), 4),
                    "detected_words": len(transcript["words"]), "cue_count": len(cues), **timing},
            "levels": {k: float(levels[k]) for k in ("input_i", "input_tp", "input_lra")},
            "opencv": {"samples": len(variances), "median_sharpness_proxy": round(float(np.median(variances)), 3),
                       "median_luma": round(float(np.median(lumas)), 2)},
            "scenes": {"cuts": max(0, len(scenes)-1), "starts_s": [round(a.get_seconds(), 2) for a, _ in scenes],
                       "median_shot_s": round(float(np.median(lengths)), 2) if lengths else None}}


def vmaf(path, out):
    filters, _ = run(["ffmpeg", "-hide_banner", "-filters"])
    if not re.search(r"\blibvmaf\b", filters):
        return {"status": "not_measured", "reason": "libvmaf_unavailable"}
    ref, copy = out / "vmaf_reference_work.mkv", out / "vmaf_encode_work.mp4"
    try:
        ff("-i", path, "-an", "-frames:v", 90, "-c:v", "ffv1", ref)
        ff("-i", ref, "-an", "-c:v", "libx264", "-crf", 20, copy)
        return optional_vmaf(ref, copy, aligned=True)
    finally:
        ref.unlink(missing_ok=True)
        copy.unlink(missing_ok=True)


def project(args):
    named = args.out / args.brand
    named.mkdir(parents=True, exist_ok=True)
    clock = Measurements(named / "PERFORMANCE.json")
    old, voice, _, srt = media_pilot.source_inputs(args, args.brand)
    if args.brand == "beauty":
        inputs(args.beauty_assets)
        base, art = beauty_render(args, named, clock)
        new_srt = base.parent / "KURU_CILT_BAKIMI.srt"
    else:
        base, art = history_render(args, named, clock, voice, srt)
        new_srt = named / "subtitles.srt"
    new = named / ("PIRI_REIS_FINAL.mp4" if args.brand=="history" else "BAKIM_FINAL.mp4")
    profile = media_pilot.read(ROOT / "media_pilot/profiles.json")[args.brand]
    profile["seconds"] = media_duration(voice)
    sfx = named / "sfx"
    sfx.mkdir()
    try:
        effects, provenance = clock.measure("earshot_real_sfx_cues", media_pilot.effects,
                                            args.brand, profile, sfx, 5.1)
        clock.measure("final_sound_mix", final_audio, base, effects, new)
        art["sound_effects"] = {"status": "mixed", **provenance}
    except (RuntimeError, OSError) as exc:
        shutil.copyfile(base, new)
        art["sound_effects"] = {"status": "unavailable", "reason": type(exc).__name__}
    final = checked_frame_video(new, length=profile["seconds"])
    if final["audio_codec"] != "aac":
        raise ValueError("Missing AAC narration.")
    character = named / "OZGUN_CIZIM.mp4"
    try:
        clock.measure("original_character_remotion", render_character, args, character)
        art["original_character"] = {"status": "rendered", **checked_frame_video(character, length=5)}
    except (RuntimeError, OSError, ValueError) as exc:
        art["original_character"] = {"status": "unavailable", "reason": type(exc).__name__}
    clock.measure("comparison", comparison, old, new, named / "ONCE_SONRA.mp4",
                  "00:00:03" if args.brand=="history" else "00:00:25")
    model = media_pilot.load_local_model(str(args.model))
    before = clock.measure("analysis_before", metrics, old, subtitle_cues(srt), model)
    after = clock.measure("analysis_after", metrics, new, subtitle_cues(new_srt), model)
    video_quality = clock.measure("vmaf", vmaf, new, named)
    story = clock.measure("one_story_sample", story_sample, args.brand, named)
    report = {"status": "human_review_required", "brand": args.brand, "media": final,
        "approved_voice_sha256": digest(voice), "before_sha256": digest(old), "before": before, "after": after,
        "vmaf": video_quality, "animation": art, "story_sample": story, "paid_api_calls": 0,
        "instagram_auto_publish": False, "comparison_excerpt_seconds_per_version": 8}
    write(named / "FINAL_QA.json", report)
    print(json.dumps({key: report[key] for key in ("brand", "media", "before", "after", "vmaf", "story_sample")},
                     ensure_ascii=False), flush=True)


def story_sample(brand, out):
    target = out / "story_probe.png"
    if brand == "beauty":
        from scripts.beauty_studio import DATA, PROFILES

        draw_story(target, media_pilot.read(PROFILES)["bakim"], media_pilot.read(DATA)[0])
    else:
        catalogue = media_pilot.read(STORY_CATALOGUE)
        render_story(target, story_candidates(catalogue)[0])
    with Image.open(target) as image:
        return {"resolution": list(image.size), "design_probe_only": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", required=True, choices=("history", "beauty"))
    for argument in ("history", "beauty", "beauty-assets", "model", "browser", "out"):
        parser.add_argument("--" + argument, required=True, type=lambda p: Path(p).resolve())
    parser.add_argument("--previous", type=lambda p: Path(p).resolve(),
                        help="Pinned previous final pilot artifact; enables the production QA replay")
    args = parser.parse_args()
    if args.previous:
        from scripts.approved_pilot_replay import project as replay
        replay(args)
    else:
        project(args)


if __name__ == "__main__":
    main()
