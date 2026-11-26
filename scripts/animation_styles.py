"""Choose brand-specific local animation and optionally render a bounded collage insert."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unicodedata

from PIL import Image

from scripts.motion_toolkit import ROOT, verified_local, sha256_file
from scripts.three_scene import classify_topic

PILOT = ROOT / "media_pilot"
STYLE_NOTES = {
    "tarih": {
        "continuous_camera": "Aynı 3B mekânda konum ve bakış yönünü yumuşakça değiştir. Harita ve yapı temsili kalsın.",
        "paper_collage": "Belge ve basılı kaynaklarda sıcak kâğıt katmanları. Fotoğrafı kaynak ve lisansla göster.",
        "hand_drawn": "Sözlü anlatıda özgün çizimli defter rehberi kullan. Tarihî kişinin görünümü olarak sunma.",
    },
    "bakim": {
        "continuous_camera": "Cilt katmanlarında yavaş makro geçiş. Temsili anatomi ve ölçek uyarısını koru.",
        "paper_collage": "Ambalaj ve içerik listelerinde gül tonlu kâğıt katmanları. Marka veya tedavi iddiası ekleme.",
        "hand_drawn": "Bakım rutininde özgün damla rehberi. Çizim, klinik sonuç veya öncesi-sonrası kanıtı değildir.",
    },
}
ROLE_IDS = {"tarih": {11, 13, 15, 17, 18, 22}, "bakim": {1, 5, 11, 12, 13, 14, 15, 20}}
ENGINES = {"continuous_camera": "three_gsap", "paper_collage": "hyperframes_gsap", "hand_drawn": "remotion_svg"}
RENDER_ERRORS = (OSError, RuntimeError, ValueError, subprocess.SubprocessError)


def _fold(text):
    text = unicodedata.normalize("NFKD", text.casefold().replace("ı", "i"))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).replace("-", " ").replace("_", " ")


def plan_for(brand, topic):
    text = _fold(" ".join(str(topic.get(field, "")) for field in ("id", "title", "category")))
    mode = topic.get("visual_mode")
    style = "base"
    if brand == "tarih":
        if mode != "2d" and classify_topic(topic):
            style = "continuous_camera"
        elif any(word in text for word in ("gazete", "arsiv", "mektup", "fotograf", "elyazma", "matbaa")):
            style = "paper_collage"
        elif any(word in text for word in ("efsane", "rivayet", "destan", "sozlu", "folklor")):
            style = "hand_drawn"
    elif brand == "bakim":
        if mode == "layer_diagram" or any(word in text for word in ("cilt bariyer", "cilt katman", "epidermis")):
            style = "continuous_camera"
        elif any(word in text for word in ("etiket", "ambalaj", "icerik listesi")):
            style = "paper_collage"
        elif any(word in text for word in ("rutin", "nazik", "gunluk bakim")):
            style = "hand_drawn"
    else:
        raise ValueError("Bilinmeyen animasyon markası.")
    return {"brand": brand, "style": style, "engine": ENGINES.get(style),
            "direction": STYLE_NOTES[brand].get(style), "stage": "planned" if style != "base" else "base_selected"}


def style_guidance(brand, role_id=None):
    if role_id is not None and role_id not in ROLE_IDS[brand]:
        return {}
    return {"styles": STYLE_NOTES[brand], "constraints": (
        "Kaynak ve lisansı onaylı yerel varlık kullan. Yalnız izinli yerel stiller. "
        "Aynı içerikte teknikleri gereksiz yere birleştirme. Üçüncü taraf kodu veya URL çalıştırma."
    )}


def commons_collage_photo(directory, record):
    """Adapt one already downloaded Commons photograph, using a narrow license subset."""
    name = record.get("file", "")
    if not isinstance(name, str) or not re.fullmatch(r"[0-9]{2}_commons\.jpg", name):
        return None
    license_name = str(record.get("license", "")).strip().lower()
    licenses = {"public domain": "PDM-1.0", "cc0": "CC0-1.0", "cc0 1.0": "CC0-1.0",
                "cc by 4.0": "CC-BY-4.0"}
    if license_name not in licenses:
        return None
    directory = Path(directory).resolve()
    path = directory / name
    if not path.is_file() or path.is_symlink():
        return None
    return path, {"source": record.get("description_url"), "license": licenses[license_name],
                  "attribution": record.get("attribution"), "commercial_use_reviewed": True,
                  "sha256": sha256_file(path)}


def _local_photo(photo, work):
    if photo is None:
        return ""
    path, receipt = photo
    path = verified_local(path, receipt, maximum_bytes=12_000_000)
    with Image.open(path) as candidate:
        if candidate.format != "JPEG" or candidate.width * candidate.height > 20_000_000:
            raise ValueError("Kolaj için sınırlandırılmış JPEG gerekli.")
        candidate.verify()
    shutil.copyfile(path, work / "photo.jpg")
    return receipt["attribution"]


def render_collage(brand, title, seconds, output, *, photo=None):
    """Use installed local tools only. Returns an optional path and an honest status."""
    hyperframes = PILOT / "node_modules/.bin/hyperframes"
    gsap = PILOT / "node_modules/gsap/dist/gsap.min.js"
    browser = os.getenv("HYPERFRAMES_BROWSER_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
    if not (gsap.is_file() and hyperframes.is_file() and browser and Path(browser).is_file()
            and shutil.which("node") and shutil.which("ffprobe")):
        return None, {"stage": "optional_unavailable", "reason": "local_hyperframes_or_browser_missing"}
    if not 3 <= seconds <= 9:
        return None, {"stage": "optional_unavailable", "reason": "unsupported_duration"}
    env = {key: os.environ[key] for key in ("HOME", "PATH", "LANG", "TMPDIR") if key in os.environ}
    env["HYPERFRAMES_BROWSER_PATH"] = browser
    env["DO_NOT_TRACK"] = "1"
    output = Path(output).absolute()
    try:
        with TemporaryDirectory(prefix="editorial-collage-") as tmp:
            work = Path(tmp)
            credit = _local_photo(photo, work)
            (work / "collage.json").write_text(json.dumps({"brand": brand, "title": str(title)[:170],
                        "seconds": seconds, "photo": bool(credit), "credit": credit}, ensure_ascii=False),
                        encoding="utf-8")
            subprocess.run(["node", str(PILOT / "editorial_collage.mjs"), str(work)],
                           env=env, check=True, timeout=20, capture_output=True)
            clip = work / "insert.mp4"
            subprocess.run([str(hyperframes), "render", str(work), "--no-browser-gpu",
                           "--strict", "--workers=2", "--fps=30", "--quality=looks", "--output", str(clip)],
                           env=env, check=True, timeout=180, capture_output=True)
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                   "-show_entries", "stream=width,height,avg_frame_rate,duration",
                                   "-of", "json", str(clip)], env=env, check=True, timeout=10, capture_output=True)
            streams = json.loads(probe.stdout).get("streams", [])
            if len(streams) != 1 or not (
                    streams[0]["width"] == 1080 and streams[0]["height"] == 1920
                    and streams[0]["avg_frame_rate"] == "30/1" and abs(float(streams[0]["duration"]) - seconds) <= .1):
                raise ValueError("Kolaj biçimi veya süresi eşleşmedi.")
            shutil.copyfile(clip, output)
    except RENDER_ERRORS + (KeyError, TypeError) as exc:
        return None, {"stage": "optional_render_skipped", "reason": type(exc).__name__}
    return output, {"stage": "insert_prepared",
                    "photo": {k: photo[1][k] for k in ("source", "license", "attribution", "sha256")} if photo else None}
