"""Free, deterministic planning for short Three.js history scenes.

Scenes are visual reconstructions, not archival evidence. No external API,
model download, or Blender installation is required. Remotion renders them;
the caller can fall back to the existing 2D scene sequence on any render error.
"""
from __future__ import annotations

import json
from pathlib import Path
import re


def classify_topic(topic: dict) -> str | None:
    """Return battle_map, siege_city, or None using metadata then safe heuristics."""
    explicit = str(topic.get("visual_mode", "")).strip().lower()
    if explicit in {"battle_map", "siege_city"}:
        return explicit
    text = " ".join(str(topic.get(k, "")) for k in ("id", "title", "hook", "context"))
    text = re.sub(r"\s+", " ", text).casefold()
    if any(word in text for word in ("fetih", "kuşatma", "kusatma", "şehir", "istanbul")):
        return "siege_city"
    if any(word in text for word in ("savaş", "savas", "malazgirt", "muharebe", "meydan muharebesi", "battle")):
        return "battle_map"
    return None


def plan_3d_scenes(topic: dict, duration_seconds: float = 70) -> dict:
    """Plan 1-2 compact scenes within the narrated documentary timeline."""
    mode = classify_topic(topic)
    topic_id = str(topic.get("id", "unknown"))
    scenes: list[dict] = []
    if mode == "battle_map":
        scenes.append({
            "kind": "battle_map",
            "from_sec": 8.0,
            "duration_sec": 9.0,
            "title": "KUŞBAKIŞI 3D SAVAŞ HARİTASI • TEMSİLÎ CANLANDIRMA",
            "motion": "Selçuklu ve Bizans birlikleri karşı yönlerden ilerler; kamera harita üzerinde yaklaşır.",
            "labels": ["SELÇUKLU ORDUSU", "BİZANS ORDUSU"],
        })
    elif mode == "siege_city":
        scenes.extend([
            {"kind": "city_flyover", "from_sec": 8.0, "duration_sec": 7.0,
             "title": "TARİHÎ ŞEHİR • TEMSİLÎ 3D CANLANDIRMA",
             "motion": "Kamera surlarla çevrili temsili şehir üzerinde yavaşça alçalır.",
             "labels": ["TEMSİLÎ ŞEHİR" ]},
            {"kind": "siege", "from_sec": min(34.0, max(20.0, duration_seconds - 10.0)), "duration_sec": 7.0,
             "title": "KUŞATMA DÜZENİ • TEMSİLÎ 3D CANLANDIRMA",
             "motion": "Kuşatma hatları ve kuşatma kuleleri dış sur önünde görünür.",
             "labels": ["SURLAR", "KUŞATMA HATTI"]},
        ])
    return {
        "topic_id": topic_id,
        "status": "planned" if scenes else "not_applicable_2d_only",
        "renderer": "Remotion + Three.js (@remotion/three)",
        "blender_optional": True,
        "ai_generation": False,
        "paid_api_calls": 0,
        "fallback": "existing 2D scene sequence",
        "scenes": scenes,
    }


def save_plan(plan: dict, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def render_with_2d_fallback(render_fn, *args, three_scenes: list[dict], **kwargs):
    """Render with 3D and retry the unchanged edit as 2D if the 3D layer fails."""
    if not three_scenes:
        return render_fn(*args, three_scenes=[], **kwargs), {"status": "not_applicable_2d_only", "fallback_used": False}
    try:
        result = render_fn(*args, three_scenes=three_scenes, **kwargs)
        return result, {"status": "rendered", "fallback_used": False}
    except Exception as exc:
        result = render_fn(*args, three_scenes=[], **kwargs)
        return result, {"status": "fallback_2d_after_3d_failure", "fallback_used": True,
                        "error": f"{type(exc).__name__}: {str(exc)[:300]}"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Save a free Three.js history-scene plan")
    parser.add_argument("--topic", required=True, help="Topic ID from data/topics.json")
    parser.add_argument("--out", default="output/three_d")
    args = parser.parse_args()
    topics = json.loads((Path(__file__).resolve().parents[1] / "data" / "topics.json").read_text(encoding="utf-8"))
    topic = next((row for row in topics if row["id"] == args.topic), None)
    if topic is None:
        parser.error("Unknown topic")
    path = save_plan(plan_3d_scenes(topic), Path(args.out) / "3D_SCENE_PLAN.json")
    print(f"3D scene plan written: {path}")
