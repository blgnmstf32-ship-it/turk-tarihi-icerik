"""Offline 15B capacity trial with separate story, reel, and simulation counts."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import file_digest
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

from scripts import ai_agents, beauty_production, beauty_studio, daily_editorial
from scripts import reels_editorial, scene_director as director, video_quality_lab as lab
from scripts.approved_pilot_replay import _timeline
from scripts.create_reel import ffprobe
from scripts.editorial_state import EditorialState
from scripts.graphics import font
from scripts.skill_registry import registry_view
from scripts.skill_router import select_knowledge, specialist_context

ROOT = Path(__file__).resolve().parents[1]
BRANDS = {"tarih": "agents.json", "bakim": "beauty_agents.json"}
STORY_TARGET = {"tarih": 10, "bakim": 10}
REEL_STRESS = {"tarih": 3, "bakim": 2}
DAILY_TARGET = {"reels_total": 2, "stories": STORY_TARGET}
FPS = director.FPS


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    with path.open("rb") as file:
        return file_digest(file, "sha256").hexdigest()


def load():
    return director._read(ROOT / "data/capacity_15b.json")


def validate(catalogue):
    reels, stories, sources = (catalogue[key] for key in ("reels", "stories", "sources"))
    if Counter(row["brand"] for row in reels) != REEL_STRESS or Counter(row["brand"] for row in stories) != STORY_TARGET:
        raise ValueError("Expected 3+2 Reels and 10+10 stories")
    if any(len(row["beats"]) < 10 or not row["boundary"] for row in reels):
        raise ValueError("Reels require 10 scenes and an evidence boundary")
    normalized = daily_editorial.normalized
    old_rows = []
    for name in ("topics.json", "editorial_ideas.json", "story_sources.json", "beauty_sources.json"):
        old_rows.extend(director._read(ROOT / "data" / name))
    old_beauty = director._read(beauty_production.CATALOG)["topics"]
    old_ids = {row["id"] for row in old_rows} | set(old_beauty)
    old_titles = {normalized(row.get("title", "")) for row in old_rows + list(old_beauty.values())}
    old_titles.update(normalized(title) for row in old_rows for title, _ in row.get("angles", []))
    old_texts = {normalized(str(row.get("text", ""))) for row in old_rows}
    old_texts.update(normalized(text) for row in old_rows for _, text in row.get("angles", []))
    ids = [row["id"] for row in reels + stories]
    titles = [normalized(row["title"]) for row in reels + stories]
    facts = [normalized(row["text"]) for row in stories]
    if (len(set(ids)) != 25 or len(set(titles)) != 25 or len(set(facts)) != 20
            or any(not director.SLUG.fullmatch(key) or key in old_ids for key in ids)
            or old_titles.intersection(titles) or old_texts.intersection(facts)):
        raise ValueError("A new angle duplicates the current topic or story catalogue")
    for row in stories + [beat for reel in reels for beat in reel["beats"]]:
        title, url, finding = sources[row["source"]]
        if not title or not url.startswith("https://") or not finding:
            raise ValueError("Every claim must point to a reviewed source receipt")
        if beauty_production.UNSAFE_PROMISE.search(row["text"]):
            raise ValueError("Unsupported guarantee in a content claim")


def story_file(path, row, source, profiles):
    title, url, _ = source
    if row["brand"] == "tarih":
        daily_editorial.render_story(path, {**row, "fact": row["text"], "source": title, "url": url})
    else:
        beauty_studio.draw_story(path, profiles["bakim"], {**row, "source": title, "url": url})
    with Image.open(path) as image:
        if image.format != "PNG" or image.size != (1080, 1920) or image.n_frames != 1:
            raise ValueError("Silent story failed the image format gate")
        image.verify()
    return {"sha256": digest(path), "file": path.name, "asset": "original_project_illustration",
            "audio": False, "size": [1080, 1920], "source": url}


def prepare_reel(row, sources, out, rosters, *, duration_frames=2100):
    brand = row["brand"]
    beats = row["beats"]
    by_key = {beat["source"]: sources[beat["source"]] for beat in beats}
    source_rows = {key: {"title": entry[0], "url": entry[1]} for key, entry in by_key.items()}
    narration = [beat["text"] for beat in beats]
    topic = {**row, "sources": list(source_rows.values()), "narration": narration, "script": narration,
             "evidence_boundary": row["boundary"]}
    if brand == "bakim":
        plan = beauty_production.make_plan({**row, "sources": source_rows,
            "beats": [{**beat, "references": [beat["source"]]} for beat in beats]}, duration_frames=duration_frames)
    else:
        source_number = {key: index for index, key in enumerate(source_rows, 1)}
        plan = director.build_plan(brand, topic, duration_frames=duration_frames, overrides={
            str(index): {"source_numbers": [source_number[beat["source"]]]}
            for index, beat in enumerate(beats, 1)})
    roles = [{
        "id": role["id"], "name": role["name"], "task": context.task,
        "skill_notes": select_knowledge(context), "mode": "offline_specialist_brief",
    } for role in rosters[brand] for context in [specialist_context(role, brand, topic)]]
    out.mkdir()
    specialists = ai_agents.run_agents(topic, rosters[brand], out,
                                      settings={"editorial_intelligence": {"free_llm_enabled": False}},
                                      brand=brand, media_review=True)
    if specialists["calls"] or specialists["actual_llm_used"]:
        raise ValueError("The CPU trial must stay provider-free")
    state = EditorialState(out / ".scene-state.sqlite3")
    planned = director.preflight(plan, state)
    order = _timeline(plan, out)
    editorial = reels_editorial.review(topic, brand, narration)
    write(out / director.PLAN, plan)
    write(out / "SPECIALIST_BRIEFS.json", roles)
    write(out / "REELS_EDITORIAL_REVIEW.json", editorial)
    write(out / "SOURCE_RECEIPTS.json", {"boundary": row["boundary"], "sources": by_key,
                                        "image_rights": "project_drawn_simulation_only",
                                        "human_release_review": "required"})
    voice = director.VOICES[brand]
    outcome = {"id": row["id"], "title": row["title"], "brand": brand, "narration": voice,
               "production_status": "blocked", "release_status": "human_review_required",
               "blockers": [f"no_approved_{voice.lower()}_for_this_script"],
               "only_existing_script_specific_voice_cleared": True,
               "editorial_status": editorial["status"], "editorial_score": editorial["best"]["total"],
               "scenes": len(order), "role_briefs": len(roles), "provider_calls": 0,
               "planned_renderers": sorted({scene["render"]["primary"]["id"] for scene in plan["scenes"]})}
    if brand == "tarih":
        outcome["blockers"].append("topic_specific_documentary_asset_set_not_cleared")
    if editorial["status"] != "passes_edit_index":
        outcome["blockers"].append("editorial_gate")
    write(out / director.REPORT, planned)
    write(out / "REEL_STATUS.json", outcome)
    return plan, state, planned, outcome


def simulate(video, row, plan, sources, profiles):
    """Real CPU render of an explicitly silent load simulation using the planned cuts."""
    work = video.parent
    inputs, filters = [], []
    for index, (beat, scene) in enumerate(zip(row["beats"], plan["scenes"])):
        picture = work / f"scene-{index:02d}.png"
        card = {**row, **beat, "id": f"{row['id']}-{index}", "motif": row.get("motif", "layers"),
                "title": beat["heading"]}
        story_file(picture, card, sources[beat["source"]], profiles)
        with Image.open(picture) as image:
            marked = image.convert("RGB")
        draw = ImageDraw.Draw(marked)
        draw.rounded_rectangle((100, 1730, 980, 1820), radius=18, fill="#17131d")
        draw.text((540, 1775), "15B · SESSİZ RENDER SİMÜLASYONU", font=font(38), fill="#fff3dd", anchor="mm")
        marked.save(picture)
        frames = scene["end_frame"] - scene["start_frame"]
        inputs.extend(("-i", str(picture)))
        filters.append(f"[{index}:v]scale=2160:3840,zoompan=z='1+on*0.00034':"
                       f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s=1080x1920:fps=30[v{index}]")
    labels = "".join(f"[v{i}]" for i in range(len(filters)))
    filters.append(f"{labels}concat=n={len(filters)}:v=1:a=0,settb=1/30,setpts=N[out]")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-filter_complex_threads", "2", *inputs,
                    "-filter_complex", ";".join(filters), "-map", "[out]", "-an", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "21", "-threads", "3", "-pix_fmt", "yuv420p",
                    "-r", "30", "-fps_mode", "cfr", "-movflags", "+faststart", str(video)],
                   check=True, timeout=300)
    streams = ffprobe(video)["streams"]
    if (len(streams) != 1 or (streams[0]["codec_type"], streams[0]["width"], streams[0]["height"],
                            streams[0]["avg_frame_rate"], int(streams[0]["nb_frames"])) !=
            ("video", 1080, 1920, "30/1", plan["duration_frames"])):
        raise ValueError("Simulation duration, resolution or silent stream structure failed")


def simulate_reel(row, plan, state, planned, outcome, out, sources, profiles, meter):
    key = row["id"]
    video = out / "SILENT_SIMULATION.mp4"
    meter.measure(f"simulation_render/{key}", simulate, video, row, plan, sources, profiles)
    evidence = meter.measure(f"simulation_qa/{key}", lab.collect_ffmpeg, video, plan)
    quality, recheck = lab.evaluate(plan, evidence=evidence, state=state, previous_id=planned["report_sha256"])
    write(out / lab.REPORT, quality)
    if recheck:
        write(out / "SCENE_RECHECK.json", recheck)
    checks = quality["technical"]["checks"]
    return {**outcome, "simulation": {"file": video.name, "sha256": digest(video), "renderer": "FFmpeg",
            "frames": plan["duration_frames"], "seconds": plan["duration_frames"] / FPS,
            "actual_audio_streams": 0, "production_credit": False, "technical_status": quality["technical"]["status"],
            "checked": {key: checks[key]["status"] for key in ("black_frames", "frozen_frames")},
            "instagram_performance": quality["instagram_performance"]["status"]}}


def batch(out, meter):
    catalogue = load()
    validate(catalogue)
    sources = catalogue["sources"]
    profiles = director._read(beauty_studio.PROFILES)
    inventory = registry_view()
    rosters = {brand: [r for r in director._read(ROOT / "config" / path) if 1 <= r["id"] <= 20]
               for brand, path in BRANDS.items()}
    if len(inventory["entries"]) < 163 or any(len(roles) != 20 for roles in rosters.values()):
        raise ValueError("Registry or specialist inventory drift")
    stories, reels = [], []
    for row in catalogue["stories"]:
        folder = out / "stories" / row["brand"]
        folder.mkdir(parents=True, exist_ok=True)
        result = meter.measure(f"story/{row['id']}", story_file,
                               folder / (row["id"] + ".png"), row, sources[row["source"]], profiles)
        stories.append({**row, **result})
    if len({row["sha256"] for row in stories}) != 20:
        raise ValueError("Duplicate rendered story media")
    prepared = []
    (out / "reels").mkdir()
    for row in catalogue["reels"]:
        folder = out / "reels" / row["id"]
        prepared.append((row, folder, meter.measure(f"plan/{row['id']}", prepare_reel, row, sources, folder,
                                                   rosters)))
    for row, folder, (plan, state, planned, result) in prepared:
        try:
            reels.append(simulate_reel(row, plan, state, planned, result, folder, sources, profiles, meter))
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            reels.append({**result, "simulation": {"error": type(exc).__name__, "production_credit": False}})
    simulated = sum("sha256" in reel["simulation"] for reel in reels)
    passed = sum(reel["simulation"].get("checked") == {"black_frames": "pass", "frozen_frames": "pass"}
                 for reel in reels)
    return {"input_version": catalogue["verified_on"], "daily_target": DAILY_TARGET, "stress_reels": REEL_STRESS,
            "stories": stories, "reels": reels, "approved_narrated_reels": 0, "silent_render_simulations": simulated,
            "simulation_visual_gates_passed": passed,
            "source_receipts": sources, "specialists": {brand: len(roles) for brand, roles in rosters.items()},
            "registry_entries": len(inventory["entries"]), "paid_api_calls": 0, "provider_api_calls": 0,
            "instagram_auto_publish": False}


def main():
    from scripts.final_media_qa import Measurements

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    meter = Measurements(out / "PERFORMANCE.json")
    report = meter.measure("complete_serial_batch", batch, out, meter)
    report["performance"] = {"host": meter.host, "transactions": meter.stages}
    write(out / "CAPACITY_15B.json", report)


if __name__ == "__main__":
    main()
