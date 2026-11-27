"""Build the source-bound skincare Reel using only the existing Sulafat and Nano Banana assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time
import wave

from PIL import Image

from scripts.beauty_reel_design import SIZE, beauty_score, cover, overlay, still
from scripts.create_reel import ffprobe, media_duration
from scripts.subtitles import create_timed
from scripts.reels_editorial import write_review
from scripts.motion_toolkit import opening_presets, select_opening_effect
from scripts.motion_quality import optional_vmaf
from scripts.animation_styles import plan_for, RENDER_ERRORS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ASSET_RUN = 45654042857
FPS = 30
BLENDER_FRAMES = 96
BLENDER_FRAME_RATE = 12
APPROVED_AUDIO = "811b614f858a4e0ce112547adfdcad64e5af6084d095f975b5525c9f636eb333"
APPROVED_IMAGE = "a9b47437ed22774f968703d44acee1fe6c389bdef7509ea38eb7d9ea67c62ec1"
VIDEO = "KURU_CILT_BAKIMI_REELS.mp4"
COVER = "KURU_CILT_BAKIMI_KAPAK.jpg"
THREE = {"cream": "BeautyCream", "barrier": "BeautySkinBarrier"}
SHOTS = (
    (0, "hook", "KURU CİLT BAKIMI", "Duştan sonra\nbeklemeyin.", "TEMSİLİ AI GÖRSELİ"),
    (3, "damp", "UYGULAMA ZAMANI", "Doğru an\nne zaman?", None),
    (7, "skin", "TEMSİLİ 3D KESİT", "Cildin\ndış tabakası", "STRATUM KORNEUM  ·  ÖLÇEK DIŞI"),
    (15, "wash", "GÜNLÜK RUTİN", "Eller için de\ngeçerli", None),
    (17, "timing", "DUŞ RUTİNİ", "Kısa ve ılık", None),
    (22.65, "towel", "NAZİK KURULAMA", "Havluyu\nhafifçe dokundurun", "TEMSİLİ AI GÖRSELİ"),
    (26.70, "cream", "NEMLENDİRİCİ SEÇİMİ", "Krem veya\nmerhem", "TEMSİLİ 3D ÜRÜN"),
    (34.70, "label", "ÜRÜN ETİKETİ", "Parfüm içermez\nifadesini arayın", None),
    (44.40, "gloves", "EL BAKIMI", "Suyla uzun\nsüre temas", None),
    (51.90, "cold", "EL BAKIMI", "Soğukta da\nkoruma", None),
    (55.70, "barrier", "TEMSİLİ 3D KESİT", "Cilt bariyeri ve\nsu kaybı", "ÖLÇEK DIŞI  ·  SU KAYBI ŞEMASI"),
    (63.70, "sources", "KURU CİLT BAKIMI", "Kuruluk\nsürerse", None),
)
EMPHASIS = re.compile(
    r"beklemeyin|hafif nemliyken|ılık su(?:yu)?|yumuşakça|parfüm içermeyen|"
    r"krem veya merhem|eldiven\w*|dermatoloğa", re.IGNORECASE,
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(directory):
    audio, picture = directory / "SULAFAT.wav", directory / "image-00.jpg"
    narrator, art = (read_json(directory / f"{name}.json") for name in ("SULAFAT", "BAKIM_IMAGE"))
    topic, timing = (read_json(DATA / f"beauty_reel_kuruluk{suffix}.json") for suffix in ("", "_timing"))
    script = "\n".join(topic["script"])
    script_sha = hashlib.sha256(script.encode()).hexdigest()
    if not (digest(audio) == APPROVED_AUDIO == narrator.get("sha256") == timing.get("audio_sha256")
            and script_sha == narrator.get("script_sha256") == timing.get("script_sha256")
            and narrator.get("voice") == "Sulafat" and narrator.get("preview") is True):
        raise ValueError("Sulafat kaydı, senaryo ve altyazı zamanları eşleşmiyor.")
    if not (digest(picture) == APPROVED_IMAGE
            and art.get("brand") == "bakim" and art.get("state") == "complete"
            and any(row.get("sha256") == APPROVED_IMAGE for row in art.get("images", []))):
        raise ValueError("Onaylı Nano Banana görseli doğrulanamadı.")
    with Image.open(picture) as source:
        if source.size != SIZE or source.format != "JPEG":
            raise ValueError("Onaylı Nano Banana görselinin biçimi değişmiş.")
    with wave.open(str(audio), "rb") as source:
        duration = source.getnframes() / source.getframerate()
    if not 60 <= duration <= 75 or abs(duration - narrator["seconds"]) > .02:
        raise ValueError("Sulafat ses süresi üretim kaydıyla eşleşmiyor.")

    cues = timing["cues"]
    if not cues or " ".join(cue["text"] for cue in cues) != " ".join(topic["script"]):
        raise ValueError("Altyazı metni senaryoyla eşleşmiyor.")
    previous = 0
    for cue in cues:
        if not previous <= cue["start"] < cue["end"] <= duration or len(cue["text"]) > 48:
            raise ValueError("Altyazı zamanları örtüşüyor, sınıra taşıyor veya metin çok uzun.")
        previous = cue["end"]
    if cues[0]["end"] > 3:
        raise ValueError("Açılış ilk üç saniyeyi aşıyor.")
    return audio, picture, narrator, art, duration, cues


def command(args, *, cwd, log=None):
    env = os.environ.copy()
    env["NODE_OPTIONS"] = (env.get("NODE_OPTIONS", "") +
                           f" --require={ROOT / 'scripts/remotion_node_compat.cjs'}").strip()
    env["REMOTION_FORCE_LOOPBACK_NETWORK"] = "1"
    result = subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=900)
    if log is not None:
        log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        lines = result.stdout.splitlines()
        errors = [line for line in lines if re.search(r"error|exception|WebGL", line, re.I)]
        detail = "\n".join(errors[:6])[:1800]
        raise RuntimeError(f"{args[0]} exited {result.returncode}: {detail}\n{result.stdout[-1600:]}")


def ffmpeg(directory, *args):
    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
             "-filter_threads", "2", "-filter_complex_threads", "2", *args], cwd=directory)


def render_models(work, *, browser, continuous=False):
    measured = {}
    start = time.monotonic()
    model = work / "blender"
    command(["blender", "-b", "-noaudio", "--threads", "4", "--python-exit-code", "1",
             "--python", str(ROOT / "scripts/beauty_model.py"), "--", "--out", str(model),
             "--frames", str(BLENDER_FRAMES), "--width", "432"], cwd=ROOT, log=work/"blender.log")
    measured["blender"] = round(time.monotonic()-start, 2)
    if not all((model / f"skin-{i:04d}.png").is_file() for i in range(1, BLENDER_FRAMES+1)):
        raise ValueError("Blender 3D dizisi eksik.")
    for key, composition in THREE.items():
        start = time.monotonic()
        args = ["npx", "--no-install", "remotion", "render", "remotion/index.tsx",
                composition, str(work / f"{key}.mp4"), "--codec=h264", "--crf=17",
                "--concurrency=2", "--gl=swangle", "--muted", "--license-key=free-license"]
        if browser:
            args.append(f"--browser-executable={browser}")
        log = work / f"{key}.log"
        if continuous:
            try:
                command([*args, "--props", json.dumps({"kind": key, "continuous": True})], cwd=ROOT, log=log)
            except RENDER_ERRORS as exc:
                command(args, cwd=ROOT, log=log)
                measured[f"{key}_camera"] = {"stage": "base_fallback", "reason": type(exc).__name__}
            else:
                measured[f"{key}_camera"] = {"stage": "applied"}
        else:
            command(args, cwd=ROOT, log=log)
        measured[key] = round(time.monotonic()-start, 2)
    return measured


def ass_time(seconds):
    cs = round(seconds*100)
    return f"{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}"


def styled_captions(cues, path):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Talk,DejaVu Sans,49,&H00E9F3FF,&H00E9F3FF,&H2C271422,&H2C271422,-1,0,0,0,100,100,0,0,3,17,0,2,116,116,350,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [
        f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},Talk,,0,0,0,,"
        + r"{\fad(60,65)}"
        + EMPHASIS.sub(lambda match: r"{\c&HBAEDFF&}" + match[0] + r"{\c&H00E9F3FF&}", cue["text"])
        for cue in cues
    ]
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def shot(work, index, frames, kind, picture, eyebrow, title, note, *, title_effect=None, repair=False):
    out = f"shot-{index:02d}.mp4"
    layer = work / "shot-overlay.png"
    overlay(layer, eyebrow, title, visual_note=note)
    length = frames / FPS
    if kind == "skin":
        source = ["-framerate", str(BLENDER_FRAME_RATE), "-i", "blender/skin-%04d.png"]
        video = "fps=30,scale=1080:1920:flags=lanczos,tpad=stop_duration=0.08:stop_mode=clone"
    elif kind in THREE:
        source = ["-i", f"{kind}.mp4"]
        video = "fps=30,scale=1080:1920:flags=lanczos,tpad=stop_duration=0.08:stop_mode=clone"
    else:
        still(kind, picture, work / "shot-background.jpg")
        source = ["-i", "shot-background.jpg"]
        factor = .00076 if kind == "hook" or repair else .00025
        video = (f"scale=2160:3840,zoompan=z='1.008+on*{factor}':x='iw/2-iw/zoom/2':"
                 f"y='ih/2-ih/zoom/2':d={frames}:s=1080x1920:fps={FPS}")
    # Match cuts between graphic/3D shots, with brief plum dips into the macro shots.
    color = "0x291824"
    dip_in = f",fade=t=in:st=0:d=0.13:color={color}" if kind in {"skin", "cream", "barrier", "sources"} else ""
    dip_out = (f",fade=t=out:st={length-.17:.4f}:d=0.15:color={color}"
               if index in {1, 5, 9, 10, 11} else "")
    if repair:
        dip_in = dip_out = ""
    title_input, overlay_args = "[1:v]", "format=auto"
    title_filter = ""
    if title_effect == "lines-reveal":
        preset = opening_presets()[title_effect]
        reveal = preset["duration_ms"] / 1000
        distance = preset["distance_px"]
        title_filter = f"[1:v]format=rgba,fade=t=in:st=0:d={reveal}:alpha=1[title];"
        title_input = "[title]"
        overlay_args += f":y='{distance}*pow(max(1-t/{reveal},0),3)'"
    animation = (f"[0:v]{video}[bg];{title_filter}[bg]{title_input}overlay={overlay_args},setsar=1"
                 f"{dip_in}{dip_out},format=yuv420p[v]")
    title_source = ["-loop", "1", "-framerate", str(FPS)] if title_effect == "lines-reveal" else []
    ffmpeg(work, *source, *title_source, "-i", layer.name, "-filter_complex", animation,
           "-map", "[v]", "-frames:v", str(frames), "-an", "-c:v", "libx264",
           "-threads", "3", "-preset", "veryfast", "-crf", "17", out)
    return out


def reviewed_shot(*args, title_effect=None):
    if not title_effect:
        return shot(*args), {"status": "base_selected"}
    try:
        return shot(*args, title_effect=title_effect), {"status": "applied", "effect": title_effect}
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        return shot(*args), {"status": "optional_render_skipped", "effect": title_effect,
                             "reason": type(exc).__name__}


def assemble(assets, out, *, browser=None, vmaf_reference=None, vmaf_aligned=False, cache=None, routed_effect=None):
    topic = read_json(DATA / "beauty_reel_kuruluk.json")
    review_topic = {**topic, "hook": topic["script"][0], "category": "kuru_cilt",
                    "visual_mode": "layer_diagram", "instagram_keywords": ["nemlendirici", "kuru cilt", "cilt bariyeri"]}
    review = write_review(out, review_topic, "bakim", topic["script"], fixed_recording=True)
    title_effect = (select_opening_effect("bakim", review_topic) if cache is None else routed_effect)
    animation = plan_for("bakim", review_topic)
    audio, picture, voice, art, duration, cues = inputs(assets)
    out.mkdir(parents=True, exist_ok=True)
    from contextlib import nullcontext
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=False)
    with (TemporaryDirectory(prefix="beauty-reel-") if cache is None else nullcontext(cache)) as tmp:
        work = Path(tmp)
        start = time.monotonic()
        continuous = animation["style"] == "continuous_camera"
        models = render_models(work, browser=browser, continuous=continuous)
        if continuous:
            cameras = {key: models.pop(f"{key}_camera") for key in THREE}
            stages = {value["stage"] for value in cameras.values()}
            animation.update(stage=next(iter(stages)) if len(stages) == 1 else "partially_applied",
                             three_scenes=cameras)
        cuts = [round(row[0]*FPS) for row in SHOTS] + [math.ceil(duration*FPS)]
        clips = []
        motion_result = {"status": "base_selected"}
        for i, (_, kind, eyebrow, title, note) in enumerate(SHOTS):
            effect = title_effect if kind == ("skin" if cache is None else "hook") else None
            clip, result = reviewed_shot(work, i, cuts[i+1]-cuts[i], kind, picture, eyebrow, title, note,
                                         title_effect=effect)
            clips.append(clip)
            if effect:
                motion_result = result
        (work / "cuts.txt").write_text("".join(f"file '{name}'\n" for name in clips))
        styled_captions(cues, work / "captions.ass")
        beauty_score(duration, [i/FPS for i in cuts[1:-1]], work / "score.wav")
        mix = ("[1:a]highpass=f=65,volume=1.15,aformat=channel_layouts=stereo,asplit[v][key];"
               "[2:a]volume=.68[bed];[bed][key]sidechaincompress=threshold=.025:ratio=7:"
               "attack=16:release=340[duck];[v][duck]amix=inputs=2:duration=first:normalize=0,"
               "alimiter=limit=.88:level=false:latency=true,volume=-1.5dB[a]")
        video = out / VIDEO
        ffmpeg(work, "-f", "concat", "-safe", "1", "-i", "cuts.txt", "-i", str(audio), "-i", "score.wav",
               "-vf", "ass=captions.ass", "-filter_complex", mix, "-map", "0:v", "-map", "[a]",
               "-c:v", "libx264", "-threads", "4", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "19",
               "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-metadata:s:a:0", "language=tur",
               "-movflags", "+faststart", str(video))
        shutil.copyfile(work / "captions.ass", out / "KURU_CILT_BAKIMI.ass")
        seconds = round(time.monotonic() - start, 2)

    streams = {item["codec_type"]: item for item in ffprobe(video)["streams"]}
    v, a = streams["video"], streams["audio"]
    total = media_duration(video)
    if (v["codec_name"] != "h264" or a["codec_name"] != "aac"
            or (v["width"], v["height"]) != SIZE or v["avg_frame_rate"] != "30/1"
            or abs(total-duration) > .12):
        raise ValueError("Reels, MP4 biçim veya senkronizasyon kontrolünden geçmedi.")
    cover(picture, out / COVER)
    create_timed(cues, out / "KURU_CILT_BAKIMI.srt")
    for name, file in (("aciklama", "ACIKLAMA.txt"), ("ilk_yorum", "SABIT_YORUM.txt")):
        shutil.copyfile(DATA / f"beauty_reel_{name}.txt", out / file)
    report = {
        "status": "verified_for_review", "duration_seconds": round(total, 2), "resolution": list(SIZE),
        "fps": FPS, "video_sha256": digest(video), "video_frames": int(v["nb_frames"]),
        "media_run_id": ASSET_RUN, "voice": voice["voice"], "voice_model": voice["model"],
        "voice_sha256": APPROVED_AUDIO, "image_model": art["model"], "image_sha256": APPROVED_IMAGE,
        "new_provider_requests": 0, "new_api_cost_usd": 0,
        "reels_editorial_review": "REELS_EDITORIAL_REVIEW.json", "editorial_index": review["best"]["total"],
        "motion_tools": motion_result, "editorial_animation": animation,
        "vmaf": optional_vmaf(vmaf_reference, video, aligned=vmaf_aligned),
        "captions": len(cues), "alignment": "faster-whisper-small, hash-bound Turkish cues",
        "opening_seconds": SHOTS[1][0], "shots": len(SHOTS), "blender_frames": BLENDER_FRAMES,
        "threejs_shots": list(THREE), "render_wall_seconds": seconds, "model_render_wall_seconds": models,
        "sound_rights": "Original programmatic score and effects, no external audio samples",
        "audio_headroom_post_limiter_db": 1.5,
        "instagram_auto_publish": False, "human_approval_required": True,
    }
    write_json(out / "DOGRULAMA.json", report)
    print(json.dumps(report, ensure_ascii=False))


def main():
    from scripts import beauty_production

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--vmaf-reference", type=Path)
    parser.add_argument("--vmaf-aligned", action="store_true")
    beauty_production.add_arguments(parser)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--render-approved", type=Path, metavar="LOCAL_CHROMIUM")
    args = parser.parse_args()
    if args.reel_topic or args.topic_file:
        if args.assets or args.browser or args.vmaf_reference or args.vmaf_aligned:
            parser.error("Genel konu rotasında pilot render seçenekleri kullanılamaz.")
        try:
            result = beauty_production.prepare(beauty_production.selected_topic(args), args.out,
                                               bundle=args.bundle, export_otio=args.otio,
                                               render_browser=args.render_approved)
        except (OSError, ValueError, RuntimeError, wave.Error, EOFError) as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False))
        return
    if not args.assets or args.bundle or args.otio or args.render_approved:
        parser.error("Önceki pilot için --assets, genel konu için --topic veya --topic-file gerekli.")
    assemble(args.assets.resolve(), args.out.resolve(), browser=args.browser,
             vmaf_reference=args.vmaf_reference, vmaf_aligned=args.vmaf_aligned)


if __name__ == "__main__":
    main()
