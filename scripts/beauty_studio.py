"""Independent, source-bound Beauty review package. No account or publication functions."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts.daily_editorial import tomorrow, write_json
from scripts.graphics import draw_text, font
from scripts.run import ROOT, load_json
from scripts.ai_agents import run_agents

BRAND = "bakim"
PROFILES = ROOT / "config/brand_profiles.json"
DATA = ROOT / "data/beauty_sources.json"


def draw_story(path, profile, item):
    theme = profile["theme"]
    image = Image.new("RGB", (1080, 1920), theme["base"])
    draw = ImageDraw.Draw(image)
    serif = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
    heading = ImageFont.truetype(str(serif), 32) if serif.is_file() else font(32)
    draw.rounded_rectangle((61, 232, 1019, 1689), 45, outline="#805969", width=3)
    draw.text((100, 286), profile["name"].upper(), font=heading, fill=theme["accent"])
    accent = theme["accent"]
    dark, light = "#553953", "#edbfdb"
    draw.ellipse((246, 402, 834, 990), fill=dark, outline=light, width=2)
    draw.ellipse((269, 425, 811, 967), outline="#856283", width=2)
    motif = item["motif"]
    if motif == "sun":
        for box in ((446, 600, 634, 788), (405, 559, 675, 829), (365, 519, 715, 869)):
            draw.ellipse(box, outline=accent, width=6)
    elif motif == "drop":
        draw.polygon(((540, 486), (425, 676), (470, 803), (613, 803), (656, 675)),
                     fill="#bb829c", outline=accent, width=5)
        draw.ellipse((425, 638, 656, 853), fill="#bb829c", outline=accent, width=5)
    elif motif in {"layers", "hair", "air"}:
        vertical = motif == "hair"
        for i in range(7):
            offset = 38 * i
            points = ((420 + offset, 566), (512 + offset, 694), (394 + offset, 838)) if vertical else (
                (335, 575 + offset), (542, 685 + offset // 2), (726, 570 + offset))
            draw.line(points, fill=accent if i % 2 else light, width=8, joint="curve")
    elif motif == "calendar":
        draw.rounded_rectangle((354, 524, 726, 846), 35, outline=accent, width=6)
        for y in (630, 691, 752):
            for x in (425, 540, 655):
                draw.ellipse((x-13, y-13, x+13, y+13), fill=light)
    elif motif in {"flask", "shelf"}:
        for i, (x, head) in enumerate(((387, 598), (500, 510), (613, 560))):
            if motif == "flask" and i != 1:
                continue
            draw.rounded_rectangle((x, head+72, x+80, 830), 17, fill="#9e617e", outline=accent, width=4)
            draw.rectangle((x+22, head+31, x+56, head+74), outline=light, width=4)
    elif motif == "dialog":
        for x, y in ((342, 553), (469, 674)):
            draw.rounded_rectangle((x, y, x+275, y+110), 45, outline=accent, width=5)
            for offset in (75, 132, 188):
                draw.ellipse((x+offset, y+49, x+offset+12, y+61), fill=light)
    else:
        for x in (430, 472, 514):
            draw.ellipse((x-64, 563, x+277, 835), outline=accent, width=4)
        draw.line((628, 778, 724, 894), fill=light, width=12)
    draw.text((100, 1010), "TEMSİLÎ İLLÜSTRASYON", font=font(22), fill=accent)
    y = draw_text(draw, item["title"], (100, 1087), 880, 63, "#fff4f3", max_lines=2, leading=1.11)
    y = draw_text(draw, item["text"], (100, y+27), 880, 42, "#f7e2ef", bold=False, max_lines=6)
    if y > 1515:
        raise ValueError("Bakım hikâyesinin yazısı güvenli alanı aştı.")
    draw.line((100, 1558, 980, 1558), fill="#805969", width=3)
    draw.text((100, 1592), item["source"], font=font(25, False), fill=accent)
    image.save(path, optimize=True)


def write_brand_calendars(out, day):
    profiles = load_json(PROFILES)
    end = (day.replace(day=1) + timedelta(days=32)).replace(day=1)
    periods = [("HAFTALIK", day-timedelta(days=day.weekday()), 7),
               ("AYLIK", day.replace(day=1), (end-day.replace(day=1)).days)]
    for brand, profile in profiles.items():
        target = out / brand
        target.mkdir(parents=True, exist_ok=True)
        for label, start, count in periods:
            rows = [{"date": (start+timedelta(days=n)).isoformat(), "timezone": profile["timezone"],
                     "reel_slots": profile["reel_times"], "story_slots": profile["story_times"],
                     "status": "content_pending", "auto_publish": False} for n in range(count)]
            write_json(target / f"{label}_TAKVIM.json", rows)


def build_preview(out, day, *, use_llm=False):
    profile = load_json(PROFILES)[BRAND]
    if len(profile["reel_times"]) != 2 or len(profile["story_times"]) != 10:
        raise ValueError("Güzellik marka takvimi hatalı.")
    target = out / BRAND
    stories_path = target / "stories"
    stories_path.mkdir(parents=True, exist_ok=True)
    items = load_json(DATA)
    if len({item["id"] for item in items}) != 10:
        raise ValueError("Kaynaklı on farklı bakım kartı gerekli.")
    rows = []
    for index, entry in enumerate(items):
        picture = stories_path / f"{index+1:02d}-{entry['id']}.png"
        draw_story(picture, profile, entry)
        with Image.open(picture) as image:
            if image.size != (1080, 1920) or image.format != "PNG" or image.n_frames != 1:
                raise ValueError("Bakım hikâyesi doğrulanamadı.")
        rows.append({**entry, "file": picture.relative_to(target).as_posix(),
                     "scheduled": profile["story_times"][index], "asset": "original_local_illustration",
                     "sha256": hashlib.sha256(picture.read_bytes()).hexdigest(), "audio": False})
    if len({row["sha256"] for row in rows}) != 10:
        raise ValueError("Bir bakım görseli tekrar ediyor.")
    role_result = {"actual_llm_used": False, "reason": "preview_without_llm"}
    if use_llm:
        item = items[0]
        role_result = run_agents({"id": item["id"], "title": item["title"], "facts": [item["text"]],
                     "sources": [{"title": item["source"], "url": item["url"]}]},
                     load_json(ROOT / "config/beauty_agents.json"), target, brand=BRAND, media_review=True)
    status = {"brand": BRAND, "date": day.isoformat(), "timezone": profile["timezone"], "stories": rows,
              "preview_voice": profile["preview_voice"], "approved_voice": profile["approved_voice"],
              "real_reels_produced": 0, "paid_images_produced": 0,
              "llm_review": role_result, "instagram_auto_publish": False, "human_approval_required": True}
    write_json(target / "BAKIM_ONIZLEME.json", status)
    write_brand_calendars(out, day)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--use-llm", action="store_true")
    args = parser.parse_args()
    build_preview(args.out, args.date or tomorrow(), use_llm=args.use_llm)


if __name__ == "__main__":
    main()
