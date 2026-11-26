"""CPU-only documentary media comparison. Accepts only the verified review assets."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from difflib import SequenceMatcher
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
from time import perf_counter

import numpy as np

from scripts.ai_agents import _media_advice
from scripts.beauty_reel import styled_captions
from scripts.create_reel import ffprobe, subtitle_cues
from scripts.gemini_tts import _tokens
from scripts.media_tools import BRAND_ROLES, ROOT, discover, options
from scripts.speech_audit import load_local_model, transcribe_local
from scripts.subtitles import create_timed

PACKAGE = ROOT / "media_pilot"
FPS = 30
HASHES = {
    "history_video": "58ce9221ba434332c1246edcb29ddc504766404c3bd823debc4394fb1d972d3b",
    "beauty_video": "f660f1a0991cf8edb3b1af7e295ad0f456faa7cd3eb017238abc3652a59ef80c",
    "history_voice": "3c1b6e038fa28d36289146d63dcf0e0b5c17b56a62beb4b444ba7e4144d0d83b",
    "beauty_voice": "811b614f858a4e0ce112547adfdcad64e5af6084d095f975b5525c9f636eb333",
    "history_image": "52b32897ede7487aaf8745032dc2de9f5374f5695ee60d025a298aac0b158ecd",
    "beauty_image": "a9b47437ed22774f968703d44acee1fe6c389bdef7509ea38eb7d9ea67c62ec1",
}
TOOL_ROUTES = {
    "history": {3: "wikimedia", 11: "hyperframes", 14: "earshot", 15: "pyscenedetect",
                16: "faster-whisper", 17: "wikimedia"},
    "beauty": {12: "wikimedia", 13: "lottie", 15: "hyperframes", 16: "faster-whisper",
               17: "earshot", 20: "loudnorm"},
}
ATOM_DUCK = "sidechaincompress=threshold=.019:ratio=8:attack=13:release=260"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def digest(path):
    with path.open("rb") as handle:
        import hashlib
        return hashlib.file_digest(handle, "sha256").hexdigest()


def run(args, *, cwd=ROOT, more=None, timeout=180):
    # Deliberately omit any inherited provider keys, tokens, proxy credentials and user agent settings.
    env = {name: os.environ[name] for name in (
        "PATH", "HOME", "LANG", "TMPDIR", "LD_LIBRARY_PATH", "SYSTEMROOT", "XDG_CACHE_HOME",
    ) if name in os.environ}
    env.update({"DO_NOT_TRACK": "1", "HYPERFRAMES_NO_TELEMETRY": "1",
                "NUMBA_NUM_THREADS": "2", "OMP_NUM_THREADS": "2", "HF_HUB_OFFLINE": "1",
                "NODE_OPTIONS": f"--require={ROOT / 'scripts/remotion_node_compat.cjs'}",
                "REMOTION_FORCE_LOOPBACK_NETWORK": "1"})
    env.update(more or {})
    start = perf_counter()
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} ({result.returncode}): {result.stdout[-2400:]}")
    return result.stdout, round(perf_counter()-start, 3)


def ff(*args, cwd=ROOT, quiet=True):
    return run(["ffmpeg", "-hide_banner", "-loglevel", "error" if quiet else "info",
                "-nostdin", "-y", "-filter_threads", "2", "-filter_complex_threads", "2", *args], cwd=cwd)


def source_inputs(args, brand):
    if brand == "history":
        media = args.history / "auto"
        video = media / "REVIEW_REQUIRED_REEL.mp4"
        voice = ROOT / "data/GEMINI_CHARON.wav"
        picture = media / "commons_visuals/01_commons.jpg"
        titles = media / "subtitles.srt"
        if not (media / "MEDIA_ATTRIBUTION.md").is_file():
            raise ValueError("Missing Wikimedia attribution for the Piri Reis source.")
    else:
        video = args.beauty / "KURU_CILT_BAKIMI_REELS.mp4"
        voice = args.beauty_assets / "SULAFAT.wav"
        picture = args.beauty_assets / "image-00.jpg"
        titles = args.beauty / "KURU_CILT_BAKIMI.srt"
    for item, path in {"voice": voice, "video": video, "image": picture}.items():
        if digest(path) != HASHES[f"{brand}_{item}"]:
            raise ValueError(f"Unapproved {brand} {item}.")
    return video, voice, picture, titles


def plan(brand, profile):
    roster = read(ROOT / "config" / ("agents.json" if brand == "history" else "beauty_agents.json"))
    roster_key = "tarih" if brand == "history" else "bakim"
    names = {r["id"]: r["name"] for r in roster}
    selected = []
    for role_id, tool in TOOL_ROUTES[brand].items():
        pick, err = _media_advice(json.dumps({"suggestion": "CPU pilotu", "caveat": "İnsan incelemesi",
                                             "source_numbers": [], "media_tool": tool}), 0, options(roster_key, role_id))
        if err:
            raise ValueError(f"Invalid media tool for role {role_id}: {tool}")
        selected.append({"role_id": role_id, "role": names[role_id], "choices": options(roster_key, role_id),
                         "selected_tool": pick["media_tool"]})
    return {"brand": brand, "visual": profile["animation"], "dispatch": selected,
            "renderers": ["remotion", "hyperframes"], "provider": "local_rules",
            "external_llm_calls": 0, "paid_api_calls": 0, "approval_required": True}


def normalize(text):
    return _tokens(re.sub(r"\b1513\b", "bin beş yüz on üç", text))


def distances(expected, observed):
    row = list(range(len(observed)+1))
    for index, word in enumerate(expected, 1):
        new = [index]
        for j, guess in enumerate(observed, 1):
            new.append(min(row[j]+1, new[-1]+1, row[j-1]+(word != guess)))
        row = new
    return row[-1]


def time_subtitles(cues, transcript, seconds):
    original = normalize(" ".join(cue["text"] for cue in cues))
    observed, times = [], []
    for word in transcript["words"]:
        tokens = normalize(word["text"])
        observed.extend(tokens)
        times.extend([(word["start"], word["end"])] * len(tokens))
    matches = {a+k: times[b+k] for a,b,size in SequenceMatcher(None,original,observed,autojunk=False)
               .get_matching_blocks() for k in range(size)}
    after, old_offsets, new_offsets = [], [], []
    index = 0
    for cue in cues:
        words = cue["text"].split()
        chunks = [words[i:i+5] for i in range(0,len(words),5)]
        for chunk_index, chunk in enumerate(chunks):
            length = len(normalize(" ".join(chunk)))
            edges = [matches[i] for i in range(index,index+length) if i in matches]
            index += length
            if not edges:
                raise ValueError("Subtitle phrase had no matching Turkish ASR timestamps.")
            start = max(after[-1]["end"] if after else 0, edges[0][0])
            end = min(seconds,max(start+.08,edges[-1][1]))
            if end <= start:
                raise ValueError("Subtitle phrase crosses the pilot boundary.")
            if chunk_index == 0:
                old_offsets.append(abs(cue["start"]-edges[0][0]))
                new_offsets.append(abs(start-edges[0][0]))
            after.append({"start": start, "end": end, "text": " ".join(chunk)})
    return after, {"words": len(original), "matched_words": len(matches),
                   "reference_start_error_ms": round(1000*np.mean(old_offsets),1),
                   "retimed_start_error_ms": round(1000*np.mean(new_offsets),1),
                   "wer": round(distances(original,observed)/max(1,len(original)),4)}


def loudness(media):
    log, elapsed = ff("-i", media, "-vn", "-af", "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json",
                      "-f", "null", "-", quiet=False)
    data = json.loads(re.findall(r'\{\s*"input_i"[^}]+\}',log)[-1])
    return data, elapsed


def render_scene(brand, profile, picture, work, browser):
    work.mkdir(parents=True)
    shutil.copyfile(picture, work/"background.jpg")
    write(work/"props.json", profile)
    run(["node", PACKAGE/"design.mjs", work, brand])
    hyper = work/"hyperframes.mp4"
    rem = work/"remotion.mp4"
    environment = {"HYPERFRAMES_BROWSER_PATH": str(browser)}
    _, hyper_seconds = run([PACKAGE/"node_modules/.bin/hyperframes", "render", work, "--no-browser-gpu",
                             "--strict", "--workers=2", "--fps=30", "--quality=looks", "--output", hyper],
                            more=environment, timeout=240)
    _, rem_seconds = run([ROOT/"node_modules/.bin/remotion", "render", "media_pilot/remotion.tsx",
                          "MediaPilot", rem, "--props", work/"props.json", "--public-dir", work,
                          "--muted", "--concurrency=2", "--gl=angle", "--crf=16",
                          "--browser-executable", browser, "--license-key=free-license"], timeout=240)
    return {"hyperframes": (hyper,hyper_seconds), "remotion": (rem,rem_seconds)}


def effects(brand, profile, folder, second):
    output = folder/"effects.wav"
    assets = [folder/f"earshot-{i}.wav" for i in range(2)]
    evidence = []
    for name, target in zip(profile["foley"], assets):
        log, elapsed = run([Path(shutil.which("earshot") or Path(os.sys.executable).with_name("earshot")),
                            "make", name, "-o", target])
        evidence.append({"file": target.name, "query": name, "seconds": elapsed, "sha256": digest(target),
                         "resolved": log.splitlines()[0], "source": "https://github.com/Leonxlnx/earshot/tree/7a7f7c5c70d4a763a1eca4b3666af7c77e313f97",
                         "license": "MIT engine; upstream grants use of generated sounds"})
    click = PACKAGE/"node_modules/uisfx/sounds/minimal"/("swipe.mp3" if brand=="history" else "check.mp3")
    frames = [round(second*FPS), round((second+.55)*FPS)]
    cues = [round(1000*frame/FPS) for frame in frames]
    filters = (f"[0:a]volume=.065,adelay={cues[0]}:all=1[a];"
               f"[1:a]volume=.035,adelay={cues[1]}:all=1[b];"
               "[2:a]volume=.025,adelay=133:all=1[c];"
               "[a][b][c]amix=inputs=3:normalize=0,apad[o]")
    _, cue_seconds = ff("-i", assets[0], "-i", assets[1], "-i", click, "-filter_complex", filters, "-map", "[o]",
       "-t", profile["seconds"], "-ar", "48000", output)
    return output, {"cues": [{"frame": frame, "offset_ms": delay, "file": asset.name}
                             for frame,delay,asset in zip(frames,cues,assets)] +
                             [{"frame": 4, "offset_ms": 133, "file": click.name}],
                    "cue_mix_seconds": cue_seconds, "earshot": evidence, "uisfx": {"asset": click.name, "sha256": digest(click),
                    "license": "CC0-1.0", "source": "https://www.npmjs.com/package/uisfx/v/0.4.0"},
                    "upstream_real_sfx": "cue design and licensed uisfx media; upstream scripts not executed"}


def mix(voice, effect, seconds, folder):
    temp, final = folder/"mix.wav", folder/"final.wav"
    ff("-i", voice, "-i", effect, "-filter_complex",
       f"[0:a]aformat=channel_layouts=stereo,asplit[v][key];[1:a][key]{ATOM_DUCK}[s];"
       "[v][s]amix=inputs=2:duration=first:normalize=0[out]", "-t", seconds,
       "-map", "[out]", "-ar", "48000", temp)
    scan, t1 = loudness(temp)
    targets = ("loudnorm=I=-16:TP=-1.5:LRA=7" + "".join(
        f":{key}={scan[field]}" for key, field in (
            ("measured_I","input_i"),("measured_TP","input_tp"),("measured_LRA","input_lra"),
            ("measured_thresh","input_thresh"),("offset","target_offset"))) + ":linear=true")
    _, t2 = ff("-i", temp, "-af", targets, "-ar", "48000", final)
    return final, t1+t2


def photo_metrics(reels):
    import cv2
    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector

    results, frames = {}, {}
    for engine, path in reels.items():
        start = perf_counter()
        cap = cv2.VideoCapture(str(path))
        cap.set(cv2.CAP_PROP_POS_MSEC,2000)
        found, frame = cap.read()
        cap.release()
        if not found:
            raise RuntimeError(f"OpenCV could not decode the {engine} frame.")
        small = cv2.resize(frame,(180,320))
        frames[engine] = small.astype("float32")
        sharp = cv2.Laplacian(cv2.cvtColor(small,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()
        decode_seconds = perf_counter()-start
        manager = SceneManager()
        manager.add_detector(ContentDetector(threshold=24,min_scene_len=8))
        start = perf_counter()
        manager.detect_scenes(open_video(str(path)))
        results[engine] = {"opencv_decode_seconds": round(decode_seconds,3),
                           "sample_laplacian_variance": round(sharp,2),
                           "detected_cuts": len(manager.get_scene_list())-1 if manager.get_scene_list() else 0,
                           "scenedetect_seconds": round(perf_counter()-start,3)}
    rm, hf = frames["remotion"], frames["hyperframes"]
    results["matched_frame_pixel_mae_0_255"] = round(float(np.abs(rm-hf).mean()),3)
    return results


@contextmanager
def local_media_server(directory):
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    with ThreadingHTTPServer(("127.0.0.1",0),handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            thread.join()


def download_self_authored(work):
    # Permission record refers only to this tool-authored fixture, served via a loopback-only socket.
    sample = work/"own-clip.mp4"
    ff("-f", "lavfi", "-i", "color=c=black:s=160x284:d=1", "-c:v", "libx264", sample)
    target = work/"downloaded.mp4"
    with local_media_server(work) as port:
        _, elapsed = run([os.sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-plugin-dirs",
                          "--no-cookies", "--no-cache-dir", "--no-playlist", "--no-exec",
                          "--max-filesize", "2M", "--retries", "0", "--no-part",
                          "--output", target, f"http://127.0.0.1:{port}/{sample.name}"])
    if digest(sample) != digest(target):
        raise ValueError("yt-dlp test changed bytes of the approved local asset.")
    return {"seconds": elapsed, "sha256": digest(sample), "license": "CC0-1.0 project test fixture",
            "scope": "local fixture only; external downloads disabled"}


def comparison(before, after, output):
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    filt = (f"[0:v]scale=360:640,drawtext=fontfile={font}:text=ÖNCE:x=18:y=35:"
            f"fontcolor=white:fontsize=22:box=1:boxcolor=black@0.7:boxborderw=9[a];"
            f"[1:v]scale=360:640,drawtext=fontfile={font}:text=YENİ:x=18:y=35:"
            "fontcolor=white:fontsize=22:box=1:boxcolor=black@0.7:boxborderw=9[b];"
            "[a][b]hstack=inputs=2[v]")
    return ff("-i",before,"-i",after,"-filter_complex",filt,"-map","[v]","-map","1:a",
              "-c:v","libx264","-pix_fmt","yuv420p","-crf","18","-threads","3",
              "-c:a","copy","-movflags","+faststart",output)[1]


def brand_pilot(args, brand, profile, target, model):
    target.mkdir()
    work = target/"work"
    video, voice, picture, subtitles = source_inputs(args, brand)
    write(target/"UZMAN_ARAC_PLANI.json", plan(brand,profile))
    search = {provider: discover(provider,profile["query"]) for provider in ("openverse","wikimedia")}
    write(target/"LISANSLI_GORSEL_ADAYLARI.json",search)
    variants = render_scene(brand,profile,picture,work,args.browser)
    seconds = profile["seconds"]
    selected = [cue for cue in subtitle_cues(subtitles) if cue["end"] <= seconds]
    if not selected:
        raise ValueError("No verified reference captions in this excerpt.")
    approved_excerpt = work/"excerpt.wav"
    ff("-i",voice,"-t",seconds,"-ar","24000",approved_excerpt)
    old = target/"ONCE.mp4"
    ff("-i",video,"-t",seconds,"-vf","scale=720:1280","-c:v","libx264","-threads","3","-crf","17","-c:a","aac",old)
    start = perf_counter()
    transcript = transcribe_local(approved_excerpt, model=model)
    asr_seconds = round(perf_counter()-start,3)
    refined, timing = time_subtitles(selected,transcript,seconds)
    styled_captions(refined,work/"captions.ass")
    create_timed(refined,target/"KELIME_ZAMANLI.srt")
    effect, provenance = effects(brand,profile,work,2.33 if brand=="history" else 1.47)
    mixed, audio_seconds = mix(approved_excerpt,effect,seconds,work)
    outputs = {"before":old}
    for engine,(source,_) in variants.items():
        output = target/f"SONRA_{engine.upper()}.mp4"
        ff("-i",source,"-i",mixed,"-map","0:v","-map","1:a","-vf","ass=captions.ass",
           "-c:v","libx264","-crf","17","-threads","3","-pix_fmt","yuv420p","-c:a","aac","-b:a","144k",
           "-movflags","+faststart","-t",seconds,output,cwd=work)
        formats = {row["codec_type"]: row for row in ffprobe(output)["streams"]}
        if (formats["video"]["width"], formats["video"]["height"], formats["audio"]["codec_name"]) != (720,1280,"aac"):
            raise ValueError("Unexpected review preview format.")
        outputs[engine] = output
    old_scan = loudness(old)[0]
    new_scan = loudness(outputs["remotion"])[0]
    ref = normalize(" ".join(cue["text"] for cue in selected))
    start = perf_counter()
    measured = {}
    for label, file in (("before",old),("after",outputs["remotion"])):
        result = transcribe_local(file,model=model)
        heard = normalize(" ".join(s["text"] for s in result["segments"]))
        measured[label] = round(distances(ref,heard)/len(ref),4)
    provenance.update({"voice_sha256": digest(voice), "voice_name": "Charon" if brand=="history" else "Sulafat",
                       "visual_sha256":digest(picture), "original_video_sha256":digest(video),
                       "visual_rights":profile["credit"], "visual_source":
                       "https://commons.wikimedia.org/wiki/File:A_peculiar_map_drawn_by_the_Turkish_admiral_Piri_Reis_around_1513.jpg"
                       if brand=="history" else "GitHub Actions 45654042857 / prior Nano Banana Batch output",
                       "original_video_provenance": "GitHub Actions 45649575775" if brand=="history" else "GitHub Actions 45702177750"})
    write(target/"MEDYA_KAYNAKLARI.json",provenance)
    asset_dir = target/"SES_EFEKTLERI"
    asset_dir.mkdir()
    for name in ("earshot-0.wav","earshot-1.wav","effects.wav"):
        shutil.copyfile(work/name,asset_dir/name)
    report = {"seconds": seconds, "resolution": [720,1280], "engine_wall_seconds":
              {name:sec for name,(_,sec) in variants.items()}, "asr_cpu_int8_seconds":asr_seconds,
              "original_and_mixed_audio_asr_seconds":round(perf_counter()-start,3),
              "wer_against_verified_excerpt":measured, "asr_timestamp_comparison":timing,
              "caption_count": {"before":len(selected),"after":len(refined)},
              "loudnorm_two_pass_seconds":round(audio_seconds,3),
              "loudness": {"before": {"lufs":old_scan["input_i"],"dbtp":old_scan["input_tp"]},
                           "after": {"lufs":new_scan["input_i"],"dbtp":new_scan["input_tp"]}},
              "image_checks":photo_metrics(outputs), "media_search": {k:{x:y for x,y in v.items() if x!="candidates"}
                                                                      for k,v in search.items()}}
    report["comparison_wall_seconds"] = comparison(old,outputs["remotion"],target/"KARSILASTIRMA.mp4")
    report["comparison_audio"] = "new_mix_only"
    report["cue_mix_seconds"] = provenance["cue_mix_seconds"]
    report["earshot_seconds"] = sum(asset["seconds"] for asset in provenance["earshot"])
    write(target/"KALITE.json",report)
    # Export the original design and source image. Rebuild local runtime assets from the lockfile.
    animation = target/"ANIMASYON"
    animation.mkdir()
    for name in ("index.html","background.jpg"):
        if (work/name).is_file():
            shutil.copy2(work/name, animation/name)
    if brand == "history":
        shutil.copyfile(args.history/"auto/MEDIA_ATTRIBUTION.md",target/"ONCE_GORSEL_ATIFLARI.md")
        (animation/"ATIF.txt").write_text(
            "Piri Reis map photograph, Yair Haklai, CC BY-SA 4.0. "
            "Framing and pan are modified. Adapted photograph retains CC BY-SA 4.0.\n"
            "https://commons.wikimedia.org/wiki/File:A_peculiar_map_drawn_by_the_Turkish_admiral_Piri_Reis_around_1513.jpg\n"
            "https://creativecommons.org/licenses/by-sa/4.0/\n",encoding="utf-8")
    for name, source_license in (
        ("UISFX-LICENSE-AUDIO.txt", PACKAGE/"node_modules/uisfx/LICENSE-AUDIO"),
        ("FONT-LICENSE.txt", Path("/usr/share/doc/fonts-dejavu-core/copyright")),
    ):
        if source_license.exists():
            shutil.copyfile(source_license,target/name)
    shutil.rmtree(work)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("history","beauty","beauty-assets","model","browser","out"):
        parser.add_argument("--"+arg,required=True,type=lambda path:Path(path).resolve())
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    results = {}
    with TemporaryDirectory(prefix="approved-media-") as root:
        retrieval = download_self_authored(Path(root))
    model = load_local_model(str(args.model))
    for brand, profile in read(PACKAGE/"profiles.json").items():
        try:
            results[brand] = brand_pilot(args,brand,profile,args.out/brand,model)
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            write(args.out/"FAILURE.json", {"brand": brand, "type":type(exc).__name__, "message":str(exc)})
            raise
    note = {"status":"review_only","provider_cost_usd":0,"instagram_auto_publish":False,
            "daily_production":False,"yt_dlp":retrieval,"ffmpeg":run(["ffmpeg","-version"])[0].splitlines()[0],
            "brands":results}
    tools = {
        "HyperFrames": {key: val["engine_wall_seconds"]["hyperframes"] for key,val in results.items()},
        "Faster Whisper": {key: val["asr_cpu_int8_seconds"] for key,val in results.items()},
        "Openverse": {key: val["media_search"]["openverse"] for key,val in results.items()},
        "Real SFX": {"status":"approved_uisfx_assets_and_local_cues_only",
                     "cue_mix_seconds": {key: val["cue_mix_seconds"] for key,val in results.items()}},
        "Earshot": {key:val["earshot_seconds"] for key,val in results.items()},
        "yt-dlp": retrieval,
        "GSAP": {"status":"rendered_on_both_HyperFrames_scenes","timing_included_in_HyperFrames":True},
        "Lottie": {"status":"rendered_on_beauty_scene","timing_included_in_engine_seconds":True},
        "OpenCV": {key: {engine:data["opencv_decode_seconds"] for engine,data in val["image_checks"].items()
                         if isinstance(data,dict)} for key,val in results.items()},
        "PySceneDetect": {key: {engine:data["scenedetect_seconds"] for engine,data in val["image_checks"].items()
                              if isinstance(data,dict)} for key,val in results.items()},
        "FFmpeg Loudnorm": {key: val["loudnorm_two_pass_seconds"] for key,val in results.items()},
        "Wikimedia Commons": {key: val["media_search"]["wikimedia"] for key,val in results.items()},
        "Freesound": {"status":"disabled_commercial_api_terms","seconds":None,"cost_usd":0},
    }
    note["tools"] = tools
    shutil.copyfile(PACKAGE/"ARACLAR.md",args.out/"ARACLAR.md")
    write(args.out/"PILOT_REPORT.json",note)
    print(json.dumps(note,ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()
