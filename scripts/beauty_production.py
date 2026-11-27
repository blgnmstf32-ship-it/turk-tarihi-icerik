"""Topic-driven beauty production using an offline plan and explicit approved local inputs."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import ceil, isfinite
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
import wave

from scripts import scene_director as director
from scripts.editorial_state import EditorialState
from scripts.motion_toolkit import https_source, sha256_file, verified_local
from scripts.reels_editorial import review, specialist_guidance
from scripts.subtitles import create_timed

ROOT = director.ROOT
BRAND = "bakim"
VOICE = "Sulafat"
MIN_FRAMES, MAX_FRAMES = 60 * director.FPS, 75 * director.FPS
CATALOG = ROOT / "data/beauty_reel_topics.json"
PROFILES = {
    "cilt-bakimi": ("routine", "science"), "lazer-epilasyon": ("follicle", "science"),
    "cilt-bariyeri": ("layers", "barrier"), "kozmetik-icerikler": ("label", "motion"),
    "sac-bakimi": ("hair", "science"), "gunes-korumasi": ("uv", "science"),
}
PURPOSES = {"hook", "context", "mechanism", "application", "product", "label", "safety", "recap", "sources"}
PUBLISHERS = {"aad.org", "dermnetnz.org", "fda.gov", "nih.gov", "nhs.uk", "cdc.gov", "who.int"}
PHOTO_LICENSES = {"CC0-1.0", "PDM-1.0", "CC-BY-4.0", "CC-BY-SA-4.0"}
PHOTO_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\.(?:png|jpe?g|webp)\Z", re.I)
UNSAFE_PROMISE = re.compile(r"%\s*100|yüzde\s+yüz|kesin\s+(?:tedavi|sonuç|çözüm)|"
                            r"(?:sonuç|tedavi)\s+garantisi|tamamen\s+risksiz|yan\s+etkisiz|"
                            r"(?:öncesi|önce)[\s/–-]+sonrası", re.I)


def load_topic(topic_id):
    catalogue = director._read(CATALOG)
    if topic_id not in catalogue["topics"]:
        raise ValueError("Güzellik konusu bulunamadı.")
    row = catalogue["topics"][topic_id]
    refs = list(dict.fromkeys(source for _purpose, _text, _heading, *ids in row["beats"] for source in ids))
    return {"id": topic_id, "title": row["title"], "category": row["category"],
            "sources": {key: catalogue["sources"][key] for key in refs},
            "beats": [{"purpose": purpose, "text": text, "heading": heading, "references": ids}
                      for purpose, text, heading, *ids in row["beats"]]}


def _publisher(url):
    if not https_source(url):
        return False
    host = urlsplit(url).hostname
    return any(host == domain or host.endswith("." + domain) for domain in PUBLISHERS)


def _words(text):
    return text.split()


def _text(value, maximum):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum and not UNSAFE_PROMISE.search(value)


def _validate_topic(topic):
    if (not isinstance(topic, dict) or not isinstance(topic.get("category"), str) or topic["category"] not in PROFILES
            or not isinstance(topic.get("id"), str) or not director.SLUG.fullmatch(topic["id"])
            or not _text(topic.get("title"), 100)):
        raise ValueError("Geçerli güzellik konusu, kategori ve başlık gerekli.")
    sources, beats = topic.get("sources"), topic.get("beats")
    if not isinstance(sources, dict) or not 1 <= len(sources) <= 16 or not all(
        isinstance(key, str) and director.SLUG.fullmatch(key) and isinstance(row, dict)
        and _text(row.get("title"), 200) and _publisher(row.get("url")) for key, row in sources.items()
    ):
        raise ValueError("Bilimsel kaynaklar güvenilir kurum bağlantısı ve başlık içermeli.")
    if not isinstance(beats, list) or not 10 <= len(beats) <= 24:
        raise ValueError("En az 10 özgün anlatım sahnesi gerekli.")
    for beat in beats:
        if (not isinstance(beat, dict) or not isinstance(beat.get("purpose"), str) or beat["purpose"] not in PURPOSES
                or not _text(beat.get("text"), 240) or not _text(beat.get("heading"), 55)):
            raise ValueError("Sahne amacı ve güvenli Türkçe anlatım gerekli.")
        refs = beat.get("references")
        if (not isinstance(refs, list) or not refs
                or any(not isinstance(key, str) or key not in sources for key in refs)):
            raise ValueError("Her sahne en az bir bilimsel kaynakla eşleşmeli.")
    if (beats[0]["purpose"] != "hook" or len(_words(beats[0]["text"])) > 7
            or beats[-1]["purpose"] != "sources" or not any(beat["purpose"] == "safety" for beat in beats)
            or len({" ".join(_words(beat["text"])).casefold() for beat in beats}) != len(beats)):
        raise ValueError("Kısa açılış, farklı sahneler, sağlık uyarısı ve kaynak kapanışı gerekli.")
    safety_text = " ".join(beat["text"].casefold() for beat in beats if beat["purpose"] == "safety")
    if topic["category"] == "lazer-epilasyon" and (
        "dermatolog" not in safety_text or not any(word in safety_text for word in ("yanık", "renk değişikliği", "iz"))
    ):
        raise ValueError("Lazer epilasyon uyarısı dermatolog değerlendirmesini ve olası zararları içermeli.")


def _visual(beat):
    visual = beat.get("visual")
    if visual is None:
        return None
    if (not isinstance(visual, dict) or not isinstance(visual.get("file"), str) or not PHOTO_NAME.fullmatch(visual["file"])
            or not isinstance(visual.get("license"), str) or visual["license"] not in PHOTO_LICENSES
            or visual.get("commercial_use_reviewed") is not True or not https_source(visual.get("source"))
            or not isinstance(visual.get("sha256"), str) or not director.SHA.fullmatch(visual["sha256"])
            or not _text(visual.get("attribution"), 260)):
        raise ValueError("Görsel için yerel dosya adı, ticari lisans, atıf ve SHA-256 gerekli.")
    if beat["purpose"] not in {"context", "application", "product", "label"}:
        raise ValueError("Bu sahne görsel kütüphane yerine orijinal, temsili grafik kullanır.")
    return visual


def _treatment(category, purpose):
    motif, schematic = PROFILES[category]
    if purpose == "mechanism":
        return schematic, motif
    if purpose == "product" and category in {"cilt-bakimi", "cilt-bariyeri", "kozmetik-icerikler"}:
        return "macro", "jar"
    if purpose in {"product", "label"}:
        return "motion", "label"
    if purpose == "application":
        return "science", motif
    return "motion", {"safety": "caution", "sources": "sources", "recap": "recap"}.get(purpose, motif)


def make_plan(topic, *, duration_frames=2100, cuts=None):
    _validate_topic(topic)
    if type(duration_frames) is not int or not MIN_FRAMES <= duration_frames <= MAX_FRAMES:
        raise ValueError("Güzellik Reels süresi 60–75 saniye olmalı.")
    sources = list(topic["sources"].values())
    id_to_number = {key: i for i, key in enumerate(topic["sources"], 1)}
    overrides, display, visual_numbers = {}, [], {}
    for index, beat in enumerate(topic["beats"], 1):
        kind, motif = _treatment(topic["category"], beat["purpose"])
        options = {"kind": kind, "source_numbers": [id_to_number[key] for key in beat["references"]]}
        if visual := _visual(beat):
            credit = visual["source"], visual["attribution"]
            if credit not in visual_numbers:
                sources.append({"title": visual["attribution"], "url": visual["source"]})
                visual_numbers[credit] = len(sources)
            options.update(kind="flat", assets=[{**visual, "id": f"asset-{index:02}", "kind": "representation",
                                                 "source_number": visual_numbers[credit]}])
        overrides[str(index)] = options
        display.append((beat, motif, visual))
    script = [beat["text"] for beat in topic["beats"]]
    plan = director.build_plan(BRAND, {**topic, "sources": sources, "script": script,
                               "visual_mode": "layer_diagram" if topic["category"] == "cilt-bariyeri" else "2d"},
                               duration_frames=duration_frames, overrides=overrides, end_frames=cuts)
    for scene, (beat, motif, visual) in zip(plan["scenes"], display):
        scene.update(purpose=beat["purpose"], heading=beat["heading"], motif=motif)
        scene["visual_assets"][0]["file"] = visual["file"] if visual else None
        if visual is None:
            scene["visual_assets"][0].update(id="beauty-original-graphics", rights_status="original_project_graphics")
        scene["render"]["reason"] = f"{topic['category']}:{beat['purpose']}:{scene['kind']}"
        scene["narration"]["source_review"] = "publisher_and_reference_checked_human_review_pending"
        scene["captions"].update(language="tr", timing="voice_bound" if cuts else "draft_estimate")
        reviewers = {1, 10, 12, 14, 15, 16, 20, scene["render"]["primary"]["review_role_id"]}
        if beat["purpose"] in {"mechanism", "safety", "sources"} or visual:
            reviewers.update((4, 5))
        if scene["kind"] in {"macro", "barrier"}:
            reviewers.add(13)
        scene["review_roles"] = sorted(reviewers)
    plan["beauty"] = {"topic_sha256": director._digest(topic), "voice": VOICE, "language": "tr",
                      "script_sha256": sha256("\n".join(script).encode()).hexdigest(),
                      "health_warnings": [row["id"] for row in plan["scenes"] if row["purpose"] == "safety"],
                      "release_status": "human_review_required"}
    if cuts:
        plan["timing"] = "approved_caption_frame_boundaries"
    return plan


def specialist_briefs(plan):
    roles = director._read(ROOT / "config/beauty_agents.json")
    if sorted(role["id"] for role in roles) != list(range(1, 21)):
        raise ValueError("20 mevcut güzellik uzmanı gerekli.")
    return {"brand": BRAND, "roles": [{"id": role["id"], "name": role["name"], "status": "brief_only",
            "scene_ids": [row["id"] for row in plan["scenes"] if role["id"] in row["review_roles"]],
            "guidance": specialist_guidance(role, BRAND, plan["topic"])} for role in roles], "llm_calls": 0}


def _chunks(text):
    current = ""
    for token in _words(text):
        if len(token) > 48:
            raise ValueError("Altyazıda tek sözcük güvenli yazı alanını aşıyor.")
        if current and len(current) + 1 + len(token) > 48:
            yield current
            current = ""
        current = f"{current} {token}".strip()
    if current:
        yield current


def draft_cues(plan):
    cues = []
    for i, row in enumerate(plan["scenes"], 1):
        parts = list(_chunks(row["narration"]["text"]))
        start, length = row["start_frame"], row["end_frame"] - row["start_frame"]
        for j, part in enumerate(parts):
            cues.append({"line": i, "start": (start + length * j // len(parts)) / director.FPS,
                         "end": (start + length * (j + 1) // len(parts)) / director.FPS, "text": part})
    return cues


def _verify_cues(cues, script, duration):
    if not isinstance(cues, list) or not 1 <= len(cues) <= 240:
        raise ValueError("Zamanlı Türkçe altyazı gerekli.")
    groups = {i: [] for i in range(1, len(script) + 1)}
    previous, line = 0, 1
    for cue in cues:
        if not isinstance(cue, dict) or type(cue.get("line")) is not int or cue["line"] not in groups:
            raise ValueError("Altyazı satırı senaryoda bulunamadı.")
        start, end = cue.get("start"), cue.get("end")
        if (any(type(x) not in (int, float) or not isfinite(x) for x in (start, end))
                or not previous <= start < end <= duration or not _text(cue.get("text"), 48)
                or cue["line"] not in (line, line + 1)):
            raise ValueError("Altyazı zamanlaması, sırası veya metni geçersiz.")
        line, previous = cue["line"], end
        groups[line].append(cue)
    for i, text in enumerate(script, 1):
        if _words(" ".join(cue["text"] for cue in groups[i])) != _words(text):
            raise ValueError("Altyazı onaylı Türkçe senaryoyla birebir eşleşmeli.")
    if groups[1][0]["start"] > .5 or groups[1][-1]["end"] > 3:
        raise ValueError("Sulafat açılışı ilk üç saniyede tamamlanmalı.")
    # Include no more than one frame of rounding on a cut; the captions retain their measured timestamps.
    return [round(groups[i][0]["start"] * director.FPS) for i in range(2, len(script) + 1)] + [ceil(duration * director.FPS)]


def approved_bundle(topic, plan, directory):
    """Verify a human-approved metadata envelope and exact bytes of existing local media."""
    directory = directory.resolve(strict=True)
    files = {name: directory / name for name in ("REVIEW.json", "CAPTIONS.json", "SULAFAT.wav")}
    if any(path.is_symlink() or not path.is_file() for path in files.values()):
        raise ValueError("Onay paketi yerel ve düzenli dosyalardan oluşmalı.")
    review, timing = (director._read(files[name]) for name in ("REVIEW.json", "CAPTIONS.json"))
    audio = files["SULAFAT.wav"]
    if audio.stat().st_size > 25_000_000 or not isinstance(review, dict) or not isinstance(timing, dict):
        raise ValueError("Onay paketi biçimi veya boyutu geçersiz.")
    digest = sha256_file(audio)
    script_digest = plan["beauty"]["script_sha256"]
    if (any(review.get(key) is not True for key in ("human_approved", "source_claims_reviewed",
                                                  "health_warnings_reviewed", "visual_rights_reviewed"))
            or review.get("voice") != VOICE or review.get("topic_sha256") != director._digest(topic)
            or review.get("audio_sha256") != digest or timing.get("audio_sha256") != digest
            or review.get("captions_sha256") != sha256_file(files["CAPTIONS.json"])
            or review.get("script_sha256") != script_digest or timing.get("script_sha256") != script_digest
            or timing.get("language") != "tr"):
        raise ValueError("İnsan, bilim, hak, Sulafat ve altyazı onayı aynı metin ve dosyalara bağlanmalı.")
    with wave.open(str(audio), "rb") as voice:
        duration = voice.getnframes() / voice.getframerate()
    if not 60 <= duration <= 75:
        raise ValueError("Onaylı Sulafat kaydı 60–75 saniye olmalı.")
    cuts = _verify_cues(timing.get("cues"), [beat["text"] for beat in topic["beats"]], duration)
    photos = {}
    for row, beat in zip(plan["scenes"], topic["beats"]):
        if visual := _visual(beat):
            path = directory / visual["file"]
            if path.is_symlink():
                raise ValueError("Görsel sembolik bağlantı olamaz.")
            photos[row["id"]] = verified_local(path, visual, maximum_bytes=8_000_000)
    return audio, timing["cues"], cuts, photos, digest


def _render_inputs(plan, public, audio, cues, photos, opening_effect):
    shutil.copyfile(audio, public / "voice.wav")
    if sha256_file(public / "voice.wav") != plan["beauty"]["approved_audio_sha256"]:
        raise ValueError("Sulafat kaydı doğrulamadan sonra değişmiş.")
    shots = []
    for row in plan["scenes"]:
        src = None
        if path := photos.get(row["id"]):
            src = f"{row['id']}{path.suffix.lower()}"
            shutil.copyfile(path, public / src)
            if sha256_file(public / src) != row["visual_assets"][0]["sha256"]:
                raise ValueError("Sahne görseli doğrulamadan sonra değişmiş.")
        shots.append({"id": row["id"], "start": row["start_frame"], "end": row["end_frame"],
                      "kind": row["kind"], "motif": row["motif"], "heading": row["heading"],
                      "purpose": row["purpose"], "insert": row["render"]["illustration_frames"], "src": src})
    return {"title": plan["topic"]["title"], "frames": plan["duration_frames"], "shots": shots,
            "openingEffect": opening_effect == "lines-reveal",
            "captions": [{k: cue[k] for k in ("start", "end", "text")} for cue in cues], "audio": "voice.wav"}


def render_local(plan, audio, cues, photos, out, *, browser, opening_effect=None):
    """Render the already approved plan with a pinned local runtime and verify only the new output."""
    from scripts.create_reel import ffprobe

    remotion = ROOT / "node_modules/.bin/remotion"
    browser = browser.resolve(strict=True)
    if not remotion.is_file() or not browser.is_file() or not os.access(browser, os.X_OK):
        raise ValueError("Yerel Remotion ve çalıştırılabilir yerel Chromium gerekli.")
    out = out.resolve()
    with TemporaryDirectory(prefix="beauty-local-", dir=out) as directory:
        work = Path(directory)
        public = work / "public"
        public.mkdir()
        props = _render_inputs(plan, public, audio, cues, photos, opening_effect)
        prop_file, output = work / "props.json", work / "reel.mp4"
        prop_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        env = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "TMPDIR") if key in os.environ}
        env.update(NODE_OPTIONS=f"--require={ROOT / 'scripts/remotion_node_compat.cjs'}",
                   REMOTION_FORCE_LOOPBACK_NETWORK="1")
        command = [str(remotion), "render", "remotion/beauty_index.tsx", "GeneralBeautyReel", str(output),
                   "--props", str(prop_file), "--public-dir", str(public), "--browser-executable", str(browser),
                   "--codec=h264", "--audio-codec=aac", "--concurrency=2", "--gl=angle", "--log=error",
                   "--license-key=free-license"]
        subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, timeout=1800)
        streams = ffprobe(output)["streams"]
        video, sound = ([row for row in streams if row["codec_type"] == name] for name in ("video", "audio"))
        if (len(video) != 1 or len(sound) != 1 or video[0]["codec_name"] != "h264" or sound[0]["codec_name"] != "aac"
                or (video[0]["width"], video[0]["height"], video[0]["avg_frame_rate"]) != (1080, 1920, "30/1")
                or int(video[0].get("nb_frames", 0)) != plan["duration_frames"]
                or abs(float(sound[0].get("duration", 0)) - plan["duration_frames"] / director.FPS) > .1):
            raise ValueError("Yeni MP4 biçimi, süre veya ses akışı doğrulanamadı.")
        # Publish only the verified local result, never reuse a stale output as evidence of this run.
        destination = out / "BEAUTY_REEL.mp4"
        if destination.exists():
            raise ValueError("Mevcut MP4'ü korumak için yeni bir çıktı klasörü seçin.")
        sha = sha256_file(output)
        os.link(output, destination)
    return {"media_created": True, "status": "human_review_required", "sha256": sha,
            "renderer": "Remotion", "scenes": [{"id": row["id"], "executed_renderer": row["render"]["primary"]["id"]}
                                                 for row in plan["scenes"]]}


def prepare(topic, out, *, bundle=None, export_otio=False, render_browser=None):
    """The default path writes only text. A separate explicit authorization enables local rendering."""
    out = Path(out)
    if render_browser is not None and bundle is None:
        raise ValueError("Yerel render için onaylı Sulafat, altyazı ve insan incelemesi paketi gerekli.")
    if render_browser is not None and (out / "BEAUTY_REEL.mp4").exists():
        raise ValueError("Mevcut MP4'ü korumak için yeni bir çıktı klasörü seçin.")
    plan = make_plan(topic)
    cues = draft_cues(plan)
    script = [row["text"] for row in topic["beats"]]
    editorial = review({**plan["topic"], "sources": list(topic["sources"].values()),
                        "script": script, "hook": script[0]}, BRAND, script,
                       fixed_recording=bundle is not None)
    if bundle is not None:
        audio, cues, cuts, photos, digest = approved_bundle(topic, plan, Path(bundle))
        plan = make_plan(topic, duration_frames=cuts[-1], cuts=cuts)
        plan["beauty"].update(release_status="human_review_attested_render_pending", approved_audio_sha256=digest)
        for row in plan["scenes"]:
            row["narration"]["source_review"] = "human_review_attested"
            if row["id"] in photos:
                row["visual_assets"][0]["rights_status"] = "human_review_attested_bytes_verified"
    out.mkdir(parents=True, exist_ok=True)
    state = EditorialState(out / ".scene-state.sqlite3")
    report = director.preflight(plan, state)
    for name, value in ((director.PLAN, plan), (director.REPORT, report),
                        ("BEAUTY_SPECIALIST_BRIEFS.json", specialist_briefs(plan)),
                        ("REELS_EDITORIAL_REVIEW.json", editorial)):
        director._write(out / name, json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    create_timed(cues, out / ("TR_ONAYLI.srt" if bundle is not None else "TR_TASLAK.srt"))
    render_path = out / "BEAUTY_RENDER_REPORT.json"
    render = {"status": "not_run", "media_created": False, "instagram_published": False, "api_calls": 0}
    director._write(render_path, json.dumps(render, indent=2) + "\n")
    if export_otio:
        from scripts.scene_otio import timeline_json

        director._write(out / "SCENE_TIMELINE.otio", timeline_json(plan))
    if render_browser is not None:
        try:
            if editorial["status"] != "passes_edit_index":
                raise ValueError("Editoryal inceleme tamamlanmadan yerel render başlatılmaz.")
            preset = report["scenes"]["s01"]["local_preflight"].get("opening_preset") or {}
            render.update(render_local(plan, audio, cues, photos, out, browser=render_browser,
                                       opening_effect=preset.get("effect")))
        except (ValueError, OSError, subprocess.SubprocessError, KeyError, RuntimeError) as exc:
            render.update(status="failed", failure=type(exc).__name__)
            director._write(render_path, json.dumps(render, indent=2) + "\n")
            raise ValueError("Yerel render tamamlanmadı. BEAUTY_RENDER_REPORT.json dosyasını inceleyin.") from exc
        director._write(render_path, json.dumps(render, indent=2) + "\n")
    return {"topic": topic["id"], "scenes": len(plan["scenes"]), "status": render["status"],
            "media_created": render["media_created"], "api_calls": 0}


def add_arguments(parser, *, topic_option="--topic"):
    group = parser.add_mutually_exclusive_group()
    group.add_argument(topic_option, dest="reel_topic")
    group.add_argument("--topic-file", type=Path)
    parser.add_argument("--otio", action="store_true")


def selected_topic(args):
    return load_topic(args.reel_topic) if args.reel_topic else director._read(args.topic_file)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--render-approved", type=Path, metavar="LOCAL_CHROMIUM")
    args = parser.parse_args()
    if not (args.reel_topic or args.topic_file):
        parser.error("--topic veya --topic-file gerekli.")
    try:
        result = prepare(selected_topic(args), args.out, bundle=args.bundle, export_otio=args.otio,
                         render_browser=args.render_approved)
    except (OSError, ValueError, RuntimeError, wave.Error, EOFError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
