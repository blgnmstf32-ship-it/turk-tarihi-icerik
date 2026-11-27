"""Build and preflight a local scene plan. The existing render entry points remain separate."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from scripts.editorial_state import EditorialState
from scripts.motion_toolkit import COMMERCIAL_LICENSES, ROOT, https_source
from scripts.skill_registry import registry_view
from scripts.skill_router import RouteContext, select_knowledge
from scripts.three_scene import classify_topic
from scripts.tool_router import run_tool

FPS = 30
VERSION = 1
PLAN = "SCENE_PLAN.json"
REPORT = "SCENE_EXECUTION_REPORT.json"
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,79}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
ROLES = {"tarih": 13, "bakim": 14}
VOICES = {"tarih": "Charon", "bakim": "Sulafat"}
HISTORY_VISUALS = {"atlantic_atlas": "map", "battle_map": "map", "city_flyover": "city",
                   "siege_city": "city", "artifact_gears": "mechanism"}
VISUALS = {
    "flat": ("media:remotion", "katmanlı_2b", "sabit_veya_yavaş_yakınlaşma", "eşit_ve_okunaklı"),
    "collage": ("media:hyperframes", "belge_kolajı", "ayrık_kâğıt_katmanları", "yumuşak_yanal"),
    "map": ("media:three-js", "temsili_atlas", "yavaş_kuşbakışı_alçalma", "dağınık_ve_yazı_korumalı"),
    "city": ("media:three-js", "temsili_mekân", "mekânı_açan_yavaş_geçiş", "yönlü_yumuşak_ana_ışık"),
    "mechanism": ("media:three-js", "temsili_mekanizma", "işleyişe_kilitli_yakın_plan", "temas_gölgeli_ana_ışık"),
    "diagram": ("media:blender", "temsili_cilt_kesiti", "yavaş_makro_geçiş", "ölçek_ve_etiket_korumalı"),
    "macro": ("media:three-js", "temsili_ürün_hareketi", "yavaş_makro_odak", "parlamasız_yumuşak_ışık"),
    "barrier": ("media:three-js", "temsili_cilt_katmanları", "yavaş_makro_geçiş", "ölçek_ve_etiket_korumalı"),
    "science": ("media:remotion", "temsili_bilimsel_2b_şema", "bölgesel_vurgu", "kontrastı_koruyan_paleti"),
    "motion": ("media:remotion", "hareketli_bilgi_grafiği", "sabit_okuma_kadrajı", "eşit_ve_okunaklı"),
}
REASONS = {"render_failed", "renderer_unavailable", "rights_unverified", "source_unverified", "sync_failed"}
ENGINE_FAILURES = {"render_failed", "renderer_unavailable"}


def _digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _read(path):
    if path.stat().st_size > 2_000_000:
        raise ValueError("Scene Director JSON input exceeds 2 MB")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path, value):
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
    try:
        temp.write_text(value, encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _topic_sources(topic):
    sources = topic.get("sources") or [{"url": topic.get("source_url"), "title": topic.get("source")}]
    if not isinstance(sources, list) or len(sources) > 32:
        raise ValueError("Expected a bounded list of source references")
    return [{"number": index, "url": row["url"], "title": str(row.get("title") or "")[:240]}
            for index, row in enumerate(sources, 1) if isinstance(row, dict) and https_source(row.get("url"))]


def _draft_kinds(brand, topic, count):
    kinds = ["flat"] * count
    if brand == "tarih":
        kinds[0] = "collage" if topic.get("id") == "piri-reis-kayip-kaynak" else "flat"
        if count > 2:
            kinds[2] = HISTORY_VISUALS.get(classify_topic(topic), "flat")
    elif count > 2 and (topic.get("visual_mode") == "layer_diagram" or topic["id"] == "kuruluk-nemlendirici-zamani"):
        kinds[2] = "diagram"
        if count > 5:
            kinds[4] = "macro"
    return kinds


def _ends(lines, duration_frames):
    weights = [max(1, len(line.split())) for line in lines[1:]]
    total = sum(weights)
    opening = 75
    remaining = duration_frames - opening - len(weights)
    ends, words = [opening], 0
    for i, weight in enumerate(weights, 1):
        words += weight
        ends.append(opening + i + remaining * words // total)
    return ends


def _engine(identifier, brand, entries):
    row = entries.get(identifier)
    if (not row or row["kind"] != "tool" or row["security"]["status"] != "existing_adapter_only"
            or row["cost"]["metered_or_paid_allowed"] or row["cost"]["category"] != "no_service_fee"
            or row["test"]["status"] != "historical_pass"):
        raise ValueError("Scene renderer requires a reviewed Registry entry and historical evidence")
    roles = sorted(int(key.split(":")[1]) for key in row["expert_ids"] if key.startswith(brand + ":"))
    if not roles:
        raise ValueError("Scene renderer requires an expert in the requested brand")
    return {"id": identifier, "hardware": row["hardware"], "license": row["license"]["code"],
            "registry_evidence": row["test"]["status"], "review_role_id": roles[0], "estimated_api_cost_usd": 0}


def _assets(rows, sources, kind, brand):
    label = "TEMSİLÎ CANLANDIRMA" if brand == "tarih" else "TEMSİLÎ GÖRSEL · ÖLÇEK DIŞI"
    if rows is None or rows == []:
        return [{"id": "planned-placeholder", "kind": "representation", "label": label,
                 "rights_status": "pending", "source_number": None, "sha256": None}]
    if not isinstance(rows, list) or len(rows) > 8:
        raise ValueError("Expected at most eight visual references per scene")
    assets = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("A visual reference must be an object")
        asset_id, license_name, digest = row.get("id"), row.get("license"), row.get("sha256")
        source = row.get("source_number")
        asset_kind = row.get("kind")
        if (not isinstance(asset_id, str) or not SLUG.fullmatch(asset_id)
                or not isinstance(digest, str) or not SHA.fullmatch(digest)
                or not isinstance(license_name, str) or license_name not in COMMERCIAL_LICENSES
                or type(source) is not int or source not in sources
                or asset_kind not in {"archive", "representation"} or row.get("commercial_use_reviewed") is not True
                or not isinstance(row.get("attribution"), str) or not row["attribution"].strip()
                or len(row["attribution"]) > 260 or "path" in row):
            raise ValueError("Visuals require bounded, licensed, attributed references and a SHA-256 receipt")
        if asset_kind == "archive" and (brand != "tarih" or kind in {"map", "city", "mechanism", "diagram", "macro"}):
            raise ValueError("A representational scene cannot be labeled as archive footage")
        assets.append({"id": asset_id, "kind": asset_kind, "source_number": source, "sha256": digest,
                       "license": license_name, "attribution": row["attribution"], "rights_status": "declared_reviewed",
                       "label": "ARŞİV REFERANSI" if asset_kind == "archive" else label})
    return assets


def _cuts(scenes):
    return [{"id": f"{a['id']}--{b['id']}", "left": a["id"], "right": b["id"],
             "frame": b["start_frame"], "default": "cut",
             "review": ["screen_direction", "motion_speed", "caption_legibility", "audio_tail"]}
            for a, b in zip(scenes, scenes[1:])]


def build_plan(brand, topic, *, duration_frames=2100, overrides=None, end_frames=None):
    """Return an integer-frame dry plan for existing script text and declared provenance."""
    if not isinstance(topic, dict):
        raise ValueError("Topic must be a JSON object")
    topic_id = topic.get("id")
    if (brand not in ROLES or not isinstance(topic_id, str) or not SLUG.fullmatch(topic_id)
            or not isinstance(topic.get("title"), str) or not 1 <= len(topic["title"]) <= 240
            or type(duration_frames) is not int or not 900 <= duration_frames <= 2700):
        raise ValueError("Invalid brand, topic or draft duration")
    lines = topic.get("narration") if brand == "tarih" else topic.get("script")
    if (not isinstance(lines, list) or not 2 <= len(lines) <= 40
            or any(not isinstance(line, str) or not line.strip() or len(line) > 1400 for line in lines)):
        raise ValueError("At least two bounded, authored narration lines are required")
    if end_frames is not None and (not isinstance(end_frames, list) or len(end_frames) != len(lines)
            or any(type(frame) is not int for frame in end_frames) or end_frames[-1] != duration_frames
            or not 0 < end_frames[0] <= 90 or any(a >= b for a, b in zip(end_frames, end_frames[1:]))):
        raise ValueError("Supplied cuts must span the timeline and keep the opening within 90 frames")
    overrides = overrides if overrides is not None else {}
    if not isinstance(overrides, dict) or set(overrides) - {str(i) for i in range(1, len(lines) + 1)}:
        raise ValueError("Scene overrides must use existing one-based narration line IDs")
    sources = _topic_sources(topic)
    source_ids = {row["number"] for row in sources}
    entries = registry_view()["entries"]
    brand_role = ROLES[brand]
    category = str(topic.get("category") or "")[:80]
    mode = str(topic.get("visual_mode") or "")[:80]
    if brand == "bakim" and topic_id == "kuruluk-nemlendirici-zamani" and not mode:
        mode = "layer_diagram"
    scenes = []
    start = 0
    for i, (line, end, default_kind) in enumerate(zip(lines, end_frames or _ends(lines, duration_frames),
                                                       _draft_kinds(brand, topic, len(lines))), 1):
        extra = overrides.get(str(i), {})
        if not isinstance(extra, dict) or extra.keys() - {"kind", "source_numbers", "assets"}:
            raise ValueError("Unexpected scene override field")
        kind = extra.get("kind", default_kind)
        if not isinstance(kind, str) or kind not in VISUALS or (brand == "bakim" and kind in {"map", "city", "mechanism"}) or (
                brand == "tarih" and kind in {"diagram", "macro", "barrier", "science", "motion"}):
            raise ValueError("Visual treatment is not supported for this brand")
        bound_sources = extra.get("source_numbers", [])
        if not isinstance(bound_sources, list) or any(type(x) is not int or x not in source_ids for x in bound_sources):
            raise ValueError("Narration source references must point to declared sources")
        target, technique, camera, light = VISUALS[kind]
        skill_scene = "diagram" if kind in {"barrier", "science"} else kind
        skills = select_knowledge(RouteContext(brand, brand_role, "visuals", skill_scene, category))
        fallback = _engine("media:remotion", brand, entries) if target != "media:remotion" else None
        if fallback:
            fallback.update(technique="katmanlı_2b", camera="sabit_kadraj", lighting="2b_okunaklı",
                            visual_label="TEMSİLÎ ŞEMA" if kind != "collage" else "MEVCUT KAYNAK VE ATIF")
        scene_id = f"s{i:02}"
        purpose = "açılış" if i == 1 else "kapanış_ve_kaynak" if i == len(lines) else "kanıt_ve_açıklama"
        scenes.append({"id": scene_id, "purpose": purpose, "kind": kind, "start_frame": start, "end_frame": end,
                       "start_seconds": round(start / FPS, 4), "end_seconds": round(end / FPS, 4),
                       "narration": {"line": i, "text": line, "voice": VOICES[brand],
                                     "source_numbers": list(dict.fromkeys(bound_sources)),
                                     "candidate_source_numbers": [row["number"] for row in sources if row["number"] not in bound_sources],
                                     "source_review": "pending"},
                       "visual_assets": _assets(extra.get("assets"), source_ids, kind, brand),
                       "render": {"primary": _engine(target, brand, entries), "alternative": fallback,
                                  "technique": technique, "illustration_frames": min(270, end - start) if kind in
                                  {"map", "city", "mechanism", "diagram", "macro", "barrier"} else end - start,
                                  "reason": f"{purpose}:{kind}"},
                       "camera": camera, "lighting": light,
                       "captions": {"text": line, "timing": "estimate_pending_voice_alignment"},
                       "sound": {"cue": "room_tone_if_approved", "transition": "J_or_L_cut_if_continuous",
                                 "priority": "narration", "asset_source_review_required": True},
                       "skills": [{"id": note["id"], "reason": note["reason"]} for note in skills],
                       "tools": (["media:opening-presets"] if i == 1 else []) + [target],
                       "quality": ["source_review", "asset_rights_review", "voice_alignment", "phone_safe_area",
                                   "shot_edge_review", "human_review"]})
        start = end
    cuts = _cuts(scenes)
    for index, scene in enumerate(scenes):
        scene["transition_in"] = cuts[index - 1]["id"] if index else None
        scene["transition_out"] = cuts[index]["id"] if index < len(cuts) else None
    return {"schema_version": VERSION, "brand": brand, "topic": {"id": topic_id, "title": topic["title"],
            "category": category, "visual_mode": mode}, "fps": FPS, "duration_frames": duration_frames,
            "resolution": [1080, 1920], "timing": "supplied_frame_boundaries" if end_frames else "estimated_from_script", "sources": sources,
            "quality_policy": {"minimum_scenes_for_release": 10, "opening_max_frames": 90,
                               "human_approval_required": True},
            "scenes": scenes, "transitions": cuts, "paid_api_allowed": False, "instagram_auto_publish": False}


def _local_preflight(plan, scene, state):
    key = f"scene-preflight:v{VERSION}:" + _digest([plan["brand"], plan["topic"], plan["sources"], scene])
    if saved := state.read(key):
        return {**saved, "cache": "hit", "executed_tools": []}
    route = None
    if "media:opening-presets" in scene["tools"]:
        brand = plan["brand"]
        context = RouteContext(brand, ROLES[brand], "opening-preset",
                               "diagram" if brand == "bakim" and plan["topic"]["visual_mode"] == "layer_diagram"
                               else "general")
        route = run_tool(context, topic=plan["topic"], state=state)
    result = {"opening_preset": (route or {}).get("result"), "tool_status": (route or {}).get("status"),
              "tool_rejections": (route or {}).get("rejected", []), "cache": "miss",
              "executed_tools": [route["executed_adapter"]] if route and route["executed_adapter"] else []}
    # Failed tools remain retryable. Pure scene checks and successful local selection can be reused.
    if not route or route["status"] in {"success", "cache"}:
        state.save(key, {**result, "executed_tools": []})
    return result


def _retry_choice(scene, reason, retries, available):
    alt = scene["render"]["alternative"]
    if not reason:
        return scene["render"]["primary"]["id"], "primary_planned", retries
    if reason not in ENGINE_FAILURES:
        return None, "needs_human_review", retries
    if (not retries and alt and alt["id"] == "media:remotion"
            and (available is None or alt["id"] in available)):
        return alt["id"], "fallback_planned", retries + 1
    return None, "no_safe_fallback", retries


def preflight(plan, state, *, previous_id=None, failures=None, available=None):
    """Evaluate scene choices and directly adjacent cuts without invoking any renderer."""
    plan_id = _digest(plan)
    scenes = {scene["id"]: scene for scene in plan["scenes"]}
    failures = failures or {}
    if not isinstance(failures, dict) or any(key not in scenes or not isinstance(code, str) or code not in REASONS
                                             for key, code in failures.items()):
        raise ValueError("Unknown scene or failure reason")
    if bool(previous_id) != bool(failures):
        raise ValueError("Scoped recovery requires both a prior report and a failed scene")
    previous = None
    prefix = f"scene-report:v{VERSION}:"
    if previous_id:
        if not isinstance(previous_id, str) or not SHA.fullmatch(previous_id):
            raise ValueError("Invalid prior report ID")
        previous = state.read(prefix + previous_id)
        if not previous or _digest(previous) != previous_id or previous["plan_sha256"] != plan_id:
            raise ValueError("No prior report matches this scene plan and local state")
    old_scenes = previous["scenes"] if previous else {}
    scene_reports, affected = {}, set(failures) if previous else set(scenes)
    for identifier, scene in scenes.items():
        if identifier not in affected:
            old = old_scenes[identifier]
            scene_reports[identifier] = {**old, "evaluation": "reused_previous",
                                         "local_preflight": {**old["local_preflight"], "executed_tools": []}}
            continue
        previous_attempts = old_scenes.get(identifier, {}).get("fallback_attempts", 0)
        cause = failures.get(identifier)
        planned = scene["render"]["primary"]["id"]
        if not cause and available is not None and planned not in available:
            cause = "renderer_unavailable"
        selected, decision, retries = _retry_choice(scene, cause, previous_attempts, available)
        scene_reports[identifier] = {"planned_renderer": planned, "selected_renderer": selected,
                                     "executed_renderer": None, "render_status": "not_run",
                                     "decision": decision, "reported_failure": cause, "fallback_attempts": retries,
                                     "evaluation": "rechecked" if previous else "initial_preflight",
                                     "local_preflight": (_local_preflight(plan, scene, state) if selected else
                                                         {"cache": "not_checked", "executed_tools": []})}
    cut_reports = {}
    for cut in plan["transitions"]:
        identifier = cut["id"]
        if previous and affected.isdisjoint((cut["left"], cut["right"])):
            cut_reports[identifier] = {**previous["transitions"][identifier], "evaluation": "reused_previous"}
            continue
        left, right = (scene_reports[cut[key]]["selected_renderer"] for key in ("left", "right"))
        cut_reports[identifier] = {"frame": cut["frame"], "method": "cut" if left and right else None,
                                   "evaluation": "rechecked" if previous else "initial_preflight",
                                   "boundary_review": "pending", "render_status": "not_run"}
    report = {"schema_version": VERSION, "phase": "offline_preflight", "plan_sha256": plan_id,
              "previous_report_sha256": previous_id, "scenes": scene_reports, "transitions": cut_reports,
              "evaluated_scene_ids": sorted(affected), "evaluated_transition_ids":
              [key for key, row in cut_reports.items() if row["evaluation"] != "reused_previous"],
              "quality": {"actual_media_checked": False, "human_approval_required": True,
                          "scene_count_meets_release_minimum": len(scenes) >= plan["quality_policy"]["minimum_scenes_for_release"]},
              "api_calls": 0, "api_cost_usd": 0, "media_created": False, "instagram_published": False}
    report_id = _digest(report)
    state.save(prefix + report_id, report)
    return {**report, "report_sha256": report_id}


def _load_topic(brand, topic_id, custom):
    if custom is not None:
        return _read(custom)
    if brand == "tarih":
        matches = [row for row in _read(ROOT / "data/topics.json") if row["id"] == topic_id]
        if matches:
            return matches[0]
    elif topic_id == "kuruluk-nemlendirici-zamani":
        return _read(ROOT / "data/beauty_reel_kuruluk.json")
    raise ValueError("Topic not found")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", required=True, choices=ROLES)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--topic")
    source.add_argument("--topic-file", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--duration-frames", type=int, default=2100)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--failures", type=Path, help="JSON mapping failed scene IDs to approved reason codes")
    parser.add_argument("--otio", action="store_true", help="Write an optional frame-only OTIO interchange file")
    args = parser.parse_args(argv)
    try:
        topic = _load_topic(args.brand, args.topic, args.topic_file)
        overrides = _read(args.overrides) if args.overrides else None
        plan = build_plan(args.brand, topic, duration_frames=args.duration_frames, overrides=overrides)
        previous = _read(args.out / REPORT)["report_sha256"] if args.failures else None
        failures = _read(args.failures) if args.failures else None
        args.out.mkdir(parents=True, exist_ok=True)
        report = preflight(plan, EditorialState(args.out / ".scene-state.sqlite3"), previous_id=previous, failures=failures)
        for name, payload in ((PLAN, plan), (REPORT, report)):
            _write(args.out / name, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    except (KeyError, OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    if args.otio:
        from scripts.scene_otio import timeline_json

        try:
            _write(args.out / "SCENE_TIMELINE.otio", timeline_json(plan))
        except (OSError, RuntimeError) as exc:
            parser.error(str(exc))
    print(json.dumps({"phase": report["phase"], "scenes": len(plan["scenes"]),
                      "report_sha256": report["report_sha256"], "media_created": False}))


if __name__ == "__main__":
    main()
