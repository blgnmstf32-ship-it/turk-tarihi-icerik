"""Closed tool routing for editorial review, and commercial-license media discovery."""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
BRAND_ROLES = {
    "tarih": {3: ["wikimedia", "openverse", "yt-dlp"], 11: ["hyperframes", "remotion", "gsap"],
              14: ["earshot", "real-sfx-cues", "loudnorm"], 15: ["hyperframes", "remotion", "pyscenedetect"],
              16: ["faster-whisper", "opencv", "pyscenedetect", "loudnorm"], 17: ["wikimedia", "openverse"]},
    "bakim": {12: ["wikimedia", "openverse", "yt-dlp"], 13: ["lottie", "gsap", "three.js", "blender"],
              15: ["hyperframes", "remotion", "pyscenedetect"], 16: ["faster-whisper", "loudnorm"],
              17: ["earshot", "real-sfx-cues", "loudnorm"], 20: ["faster-whisper", "opencv", "pyscenedetect", "loudnorm"]},
}
CAPABILITIES = {
    "wikimedia": "Telif kaydı doğrulanmış açık lisanslı görsel arşivi",
    "openverse": "Bilinen arşiv sonucu yoksa açık lisans adayı ara",
    "yt-dlp": "Yalnız izin kaydı olan doğrudan medya adresi",
    "remotion": "Mevcut sesli kurgu ve üç boyutlu sahneler için varsayılan",
    "hyperframes": "Bağımsız HTML grafik sahnesi gerekiyorsa alternatif; aynı sahneyi iki motorda seri üretme",
    "gsap": "HTML sahnesinde anlamı taşıyan zaman çizelgesi hareketi",
    "lottie": "İki boyutlu süreç veya vektör şema gerekiyorsa",
    "three.js": "Rota, mekân, katman veya mekanizmayı 2B görüntü anlatamıyorsa temsili 3B",
    "blender": "Modellenmiş geometri ve kontrollü kamera gerektiren kısa sahne",
    "earshot": "CPU ile markaya özel yerel efekt",
    "real-sfx-cues": "Çerçeveye kilitli efekt planı ve CC0 uisfx kaynağı",
    "loudnorm": "Konuşma odaklı LUFS ve dBTP kontrolü", "faster-whisper": "Türkçe kelime zamanları",
    "opencv": "Kare benzerliği ve keskinlik sinyali; editoryal değerlendirme ayrıca",
    "pyscenedetect": "Karmaşık kurguda kesme noktası denetimi",
}
OPENVERSE = "https://api.openverse.org/v1/images/"
COMMONS = "https://commons.wikimedia.org/w/api.php"
COMMERCIAL = {"cc0", "pdm", "by", "by-sa"}


def options(brand, role_id):
    return {tool: CAPABILITIES[tool] for tool in BRAND_ROLES[brand].get(role_id, [])}


def homepage(value):
    parsed = urlsplit(value or "")
    return value if parsed.scheme == "https" and parsed.hostname and not parsed.username else None


def discover(provider, query, get=None):
    getter = get or requests.get
    start = perf_counter()
    status, results = None, []
    try:
        if provider == "openverse":
            response = getter(OPENVERSE, params={"q": query, "license": "cc0,pdm,by", "page_size": 6},
                              headers={"User-Agent": "EditorialMediaPilot/1.0"}, timeout=(5, 12))
            status = response.status_code
            response.raise_for_status()
            for row in response.json()["results"]:
                source = homepage(row.get("foreign_landing_url"))
                rights = homepage(row.get("license_url"))
                if (row.get("license") in {"cc0", "pdm", "by"} and source and rights
                        and (row.get("creator") or row["license"] != "by")):
                    results.append({"title": row.get("title"), "author": row.get("creator"),
                                    "license": row["license"], "license_url": rights,
                                    "source": source, "verification": "original_page_review_required"})
        elif provider == "wikimedia":
            from scripts.commons_media import _metadata
            response = getter(COMMONS, params={"action": "query", "format": "json", "generator": "search",
                "gsrnamespace": 6, "gsrsearch": query, "gsrlimit": 6, "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime|mediatype"},
                headers={"User-Agent": "EditorialMediaPilot/1.0 (license provenance)"}, timeout=(5, 12))
            status = response.status_code
            response.raise_for_status()
            for page in response.json().get("query", {}).get("pages", {}).values():
                meta = _metadata(page)
                if meta and homepage(meta["description_url"]):
                    results.append({**meta, "verification": "commons_source_metadata"})
        else:
            raise ValueError("Unknown discovery provider")
        outcome = "found" if results else "no_match"
    except (requests.RequestException, ValueError, AttributeError, KeyError, TypeError):
        outcome = "unavailable"
    return {"service": provider, "status": outcome, "http_status": status, "query": query,
            "candidates": results, "seconds": round(perf_counter()-start, 3)}
