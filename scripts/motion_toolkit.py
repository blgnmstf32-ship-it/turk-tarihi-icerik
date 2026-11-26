"""Opt-in editorial guidance and locally verified motion asset contracts."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
COMMERCIAL_LICENSES = {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "PDM-1.0", "MIT", "Apache-2.0", "GPL-3.0-only", "BSD-3-Clause"}
SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}\Z")


@lru_cache(maxsize=1)
def registry():
    return json.loads((ROOT / "config/motion_toolkit.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def skill_index():
    return json.loads((ROOT / "config/motion_skill_index.json").read_text(encoding="utf-8"))


ROLE_TECHNIQUES = {
    "tarih": {
        6: ("short-form-video", "kinetic-typography"),
        7: ("explainer-video", "presentation-video", "whiteboard-animation"),
        11: ("shot-composition", "map-animation", "animated-infographic", "photo-slideshow"),
        12: ("lower-thirds", "svg-animation"),
        13: ("motion-art-direction", "animation-principles", "motion-background", "color-motion", "gsap-web",
             "threejs-animation", "threejs"),
        14: ("accessible-animation",),
        15: ("beat-sync-editing", "caption-animation", "talking-head-b-roll", "remotion-video", "remotion"),
        16: ("video-delivery-specs", "60fps-animation"),
        22: ("threejs-animation", "threejs", "map-animation", "isometric-animation", "motion-canvas"),
    },
    "bakim": {
        1: ("creative-brief", "brand-motion-guidelines"),
        10: ("explainer-video", "short-form-video"),
        11: ("animated-infographic", "lottie-animation", "product-demo-video"),
        12: ("photo-slideshow", "svg-animation"),
        13: ("manim", "diagram-animation", "isometric-animation", "threejs", "chart-animation"),
        14: ("motion-art-direction", "color-motion", "animation-basics", "gsap-motion"),
        15: ("beat-sync-editing", "caption-animation", "remotion", "motion-canvas"),
        16: ("accessible-animation",),
        17: ("video-delivery-specs",),
        18: ("lower-thirds", "kinetic-typography"),
        20: ("video-delivery-specs",),
    },
}


@lru_cache(maxsize=1)
def opening_presets():
    return json.loads((ROOT / "media_pilot/motion_presets.json").read_text(encoding="utf-8"))


def select_opening_effect(brand, topic, *, parallax=False, requested=None):
    """Select an offline preset from topic metadata. Explicit approved choices win."""
    if requested is not None:
        if requested not in opening_presets() or (requested == "mask-reveal" and parallax):
            raise ValueError("İzinli ve birbiriyle uyumlu açılış seçenekleri gerekli.")
        return requested
    if brand == "bakim" and topic.get("visual_mode") == "layer_diagram":
        return "lines-reveal"
    if brand == "tarih" and topic.get("visual_mode") == "artifact_gears":
        return "lines-reveal"
    if brand == "tarih" and topic.get("category") in {"mekanizma", "kesif"}:
        return "lines-reveal"
    return None


def role_guidance(brand, role_id=None):
    brand_spec = registry()["direction"][brand]
    allowed = brand_spec["roles"].get(str(role_id), [])
    names = ROLE_TECHNIQUES[brand].get(role_id, ())
    if role_id is None:
        names = ("creative-brief", "animation-principles", "video-delivery-specs")
    assignment_notes = ({identifier: [name for name in tools if registry()["tools"][name]["status"] == "optional"]
                         for identifier, tools in brand_spec["roles"].items() if int(identifier) <= 20}
                        if role_id is None else {})
    sources = [
        {"name": row["name"], "repository": pack["repository"], "path": row["path"], "commit": pack["commit"]}
        for pack in skill_index() for row in pack["skills"]
        if row["decision"] == "adapt" and row["name"] in names
    ]
    return {
        "editorial_direction": brand_spec["editor"],
        "technique_sources": sources,
        "assignment_options": assignment_notes,
        "techniques": {row["name"]: row["note"] for pack in skill_index() for row in pack["skills"]
                       if row["decision"] == "adapt" and row["name"] in names},
        "tools": {name: {key: registry()["tools"][name][key] for key in ("status", "use")}
                  for name in allowed},
        "human_review_required": True,
    }


def sha256_file(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def https_source(value):
    if not isinstance(value, str) or len(value) > 600:
        return False
    try:
        url = urlsplit(value)
        return url.scheme == "https" and bool(url.hostname) and url.username is None
    except ValueError:
        return False


def verified_local(path, receipt, *, maximum_bytes):
    """A human attests rights. This checks inputs and binds the decision to exact bytes."""
    path = Path(path).resolve(strict=True)
    if not path.is_file() or not 0 < path.stat().st_size <= maximum_bytes:
        raise ValueError("Missing asset or unsupported size.")
    if (receipt.get("commercial_use_reviewed") is not True
            or receipt.get("license") not in COMMERCIAL_LICENSES
            or not https_source(receipt.get("source"))
            or not isinstance(receipt.get("attribution"), str) or not receipt["attribution"].strip()
            or len(receipt["attribution"]) > 260 or receipt.get("sha256") != sha256_file(path)):
        raise ValueError("Asset license, provenance and content hash must be confirmed.")
    return path


def poly_haven_catalogue(records, *, kind, limit=25):
    """Prepare a zero-download catalogue from a Poly Haven asset index response."""
    if kind not in {"models", "textures", "hdris"} or not 1 <= limit <= 100:
        raise ValueError("Invalid Poly Haven catalogue query.")
    if not isinstance(records, dict):
        raise ValueError("Expected Poly Haven object response.")
    expected_type = {"hdris": 0, "textures": 1, "models": 2}[kind]
    rows = []
    for slug, item in sorted(records.items()):
        if not SLUG.fullmatch(slug) or not isinstance(item, dict):
            continue
        if item.get("type", expected_type) != expected_type:
            continue
        title = item.get("name")
        rows.append({"id": slug, "kind": kind, "title": title[:180] if isinstance(title, str) else slug,
                     "source": f"https://polyhaven.com/a/{slug}", "license": "CC0-1.0",
                     "license_url": "https://polyhaven.com/license", "downloaded": False,
                     "needs_asset_verification": True})
        if len(rows) == limit:
            break
    return {"attribution": "Powered by Poly Haven", "assets": rows}


def load_poly_haven(kind, *, enabled=False):
    if not enabled:
        raise ValueError("Live Poly Haven catalogue lookup is opt-in.")
    if kind not in {"models", "textures", "hdris"}:
        raise ValueError("Unsupported Poly Haven type.")
    import requests

    with requests.get("https://api.polyhaven.com/assets", params={"t": kind},
                      headers={"User-Agent": "HistoryBeautyMotionToolkit/1.0"},
                      timeout=(5, 12), allow_redirects=False, stream=True) as response:
        if response.status_code != 200:
            raise RuntimeError(f"Poly Haven returned HTTP {response.status_code}.")
        body = bytearray()
        for chunk in response.iter_content(65536):
            body.extend(chunk)
            if len(body) > 8_000_000:
                raise ValueError("Poly Haven catalogue response is too large.")
    return poly_haven_catalogue(json.loads(body), kind=kind)
