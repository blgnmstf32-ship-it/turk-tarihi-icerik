"""Prepare and verify tomorrow's review package without any publishing client."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
from statistics import median
import subprocess
import unicodedata
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from scripts.graphics import draw_text, font
from scripts.instagram_insights import fetch_read_only_insights
from scripts.run import ROOT, load_json

ISTANBUL = ZoneInfo("Europe/Istanbul")
REEL_TIMES = ("19:00", "19:00", "18:00", "19:00", "20:00", "20:00", "19:00")
STORY_TIMES = ("09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30")
APPROVED_PIRI = "piri-reis-kayip-kaynak"
TOPIC_CATALOGUE = ROOT / "data/topics.json"
STORY_CATALOGUE = ROOT / "data/story_sources.json"
REEL = "REVIEW_REQUIRED_REEL.mp4"


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def tomorrow(now=None):
    return ((now or datetime.now(ISTANBUL)).astimezone(ISTANBUL).date() + timedelta(days=1))


def normalized(text):
    folded = unicodedata.normalize("NFKD", text.casefold()).replace("ı", "i")
    return " ".join(re.findall(r"[a-z0-9]+", folded))


def story_candidates(catalogue):
    return [{"id": f"{item['id']}-{i}", "group": item["id"], "title": title, "fact": fact,
             "place": item["place"], "era": item["era"], "scope": item["scope"],
             "motif": item["motif"], "source": item["source"], "url": item["url"],
             "fingerprint": hashlib.sha256(normalized(fact).encode()).hexdigest()}
            for item in catalogue for i, (title, fact) in enumerate(item["angles"], 1)]


def choose_stories(catalogue, history, reel, target, research):
    prior = [story for day in history.values() for story in day["stories"]]
    used_ids = {story["id"] for story in prior}
    used_facts = {story["fingerprint"] for story in prior}
    groups_used = Counter(story["group"] for story in prior)
    trends = [normalized(row["title"]) for row in research.get("trends", [])]
    pool = [story for story in story_candidates(catalogue)
            if story["id"] not in used_ids and story["fingerprint"] not in used_facts
            and story["group"] != reel.get("story_group", reel["id"])]
    pool.sort(key=lambda story: (groups_used[story["group"]],
                                  not any(normalized(story["group"]) in trend for trend in trends),
                                  int(story["id"].rsplit("-", 1)[1])))
    chosen, groups = [], set()
    for preferred in ("anadolu", "dunya", "anadolu", "dunya", "anadolu", "dunya",
                      "anadolu", "dunya", "dunya", "dunya"):
        eligible = [item for item in pool
                    if item["group"] not in groups and item["fingerprint"] not in used_facts]
        row = next((item for item in eligible if item["scope"] == preferred), None)
        if row is None and eligible:
            row = eligible[0]
        if row is None:
            raise ValueError(f"{target}: tekrar etmeyen on kaynaklı hikâye için katalog yetersiz")
        chosen.append(row)
        groups.add(row["group"])
        used_facts.add(row["fingerprint"])
    return chosen


def choose_reel(topics, history, board, demo=False):
    if demo:
        return next(topic for topic in topics if topic["id"] == APPROVED_PIRI)
    used = {APPROVED_PIRI} | {item["reel_id"] for item in history.values()}
    eligible = [topic for topic in topics
                if topic["id"] not in used and topic.get("narration") and topic.get("sources")]
    if not eligible:
        raise ValueError("Tekrar etmeyen, senaryosu ve kaynakları hazır Reels konusu kalmadı.")
    review = board.get("coordinator_llm", {})
    decision = (review.get("decision") or {}).get("selected_idea_id") if review.get("completed_discussion") else None
    ranking = [decision, *(row["id"] for row in board.get("recommendations", []))]
    ranked = sorted(eligible, key=lambda topic: ranking.index(topic["id"]) if topic["id"] in ranking else len(ranking))
    return ranked[0]


def local_time(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(ISTANBUL) if result.tzinfo else None
    except ValueError:
        return None


def minutes(slot):
    h, m = map(int, slot.split(":"))
    return 60 * h + m


def timing_recommendation(base, weekday, kind, observations):
    """Suggest same-weekday alternatives only with >=3 distinct posts per slot."""
    slots = defaultdict(dict)
    for row in observations:
        published = local_time(row.get("published_at"))
        reach = row.get("reach")
        if (not published or row.get("format") != kind or published.weekday() != weekday
                or isinstance(reach, bool) or not isinstance(reach, (int, float))
                or not math.isfinite(reach) or reach <= 0 or not row.get("content_id")):
            continue
        slot = f"{published.hour:02d}:{30 * (published.minute // 30):02d}"
        if abs(minutes(slot) - minutes(base)) <= (60 if kind == "REEL" else 30):
            slots[slot][row["content_id"]] = reach
    comparable = {slot: median(rows.values()) for slot, rows in slots.items() if len(rows) >= 3}
    if base not in comparable or len(comparable) < 2:
        return {"time": base, "status": "insufficient_comparable_instagram_data"}
    best = max(comparable, key=lambda slot: (comparable[slot], slot == base))
    if best == base or comparable[best] < 1.15 * comparable[base]:
        return {"time": base, "status": "baseline_retained"}
    return {"time": best, "status": "recommendation_only",
            "baseline_sample": len(slots[base]), "candidate_sample": len(slots[best]),
            "baseline_median_reach": comparable[base], "candidate_median_reach": comparable[best]}


def day_slots(day, observations):
    weekday = day.weekday()
    base = REEL_TIMES[weekday]
    return {"date": day.isoformat(), "timezone": ISTANBUL.key,
            "reel": {"time": base, "insights": timing_recommendation(base, weekday, "REEL", observations)},
            "stories": [{"time": slot, "insights": timing_recommendation(slot, weekday, "STORY", observations)}
                        for slot in STORY_TIMES]}


def search_notes(topic, research):
    labels = topic.get("instagram_keywords") or [topic["id"].split("-")[0]]
    category = topic.get("category", "")
    tags = {
        "kesif": "ArkeolojikKeşif", "tarihi_gizem": "TarihîGizem", "kayip_sehir": "KayıpŞehirler",
        "az_bilinen_olay": "AzBilinenTarih", "unutulmus_savas": "DünyaTarihi",
        "siradisi_hikaye": "AzBilinenTarih",
    }
    matches = [row for row in research.get("trends", [])
               if any(f" {normalized(label)} " in f" {normalized(row['title'])} " for label in labels
                      if len(normalized(label)) >= 4)]
    public = load_json(ROOT / "config/research_sources.json")
    tag_observations = [row for row in public.get("public_instagram_hashtag_examples", [])
                        if row["topic_id"] == topic["id"]]
    observed = [row["tag"].removeprefix("#") for row in tag_observations]
    names = ["TarihinBilinmeyenGerçekleri", *observed, *(re.sub(r"[^\w]", "", label.title()) for label in labels[:2]),
             tags.get(category, "TarihBelgeseli"), "Arkeoloji" if category == "kesif" else "TarihBelgeseli"]
    hashtags = list(dict.fromkeys("#" + name for name in names if name))[:5]
    return {"checked_at": research.get("collected_at_utc"), "keywords": labels, "hashtags": hashtags,
            "tag_method": "topic_keywords_and_relevant_google_trends_review",
            "instagram_hashtag_volume_status": "unavailable",
            "matched_google_trends": matches, "public_instagram_hashtag_examples": tag_observations,
            "public_competitor_editorial_examples": public.get("public_competitor_editorial_examples", []),
            "competitors": [
                {"name": channel["name"], "platform": "YouTube", "items": [
                    {key: video.get(key) for key in ("title", "url", "published", "views", "metrics_source",
                                                     "metrics_retrieved_at", "archived_public_metrics")}
                    for video in channel["videos"][:4]]}
                for channel in research.get("competitors", [])],
            "instagram_competitor_metrics_status": "unavailable",
            "research_errors": research.get("errors", [])}


def artwork(draw, motif, shade, light, rng):
    """Topic-specific geometric illustrations made locally for the Story format."""
    px, py = 540, 610
    draw.ellipse((220, 280, 880, 940), outline=shade, width=3)
    draw.ellipse((250, 310, 850, 910), outline=shade, width=2)
    for _ in range(68):
        x, y = rng.randrange(180, 900), rng.randrange(320, 920)
        if math.hypot(x - px, y - py) < 330:
            draw.ellipse((x, y, x + 3, y + 3), fill=shade)
    if motif in {"roof", "tower", "gate", "wall", "arch", "garden"}:
        heights = {"roof": (395, 475, 430, 500, 460), "tower": (400, 275, 350, 322, 455),
                   "gate": (550, 425, 355, 425, 550), "wall": (425, 448, 500, 555, 610),
                   "arch": (615, 545, 380, 560, 620), "garden": (595, 548, 580, 530, 612)}[motif]
        for i, y in enumerate(heights):
            x = 266 + i * 106
            draw.rectangle((x, y, x + 104, 827), fill=shade, outline=light, width=3)
            for step in range(y + 54, 800, 66):
                if motif in {"wall", "roof", "garden"}:
                    draw.line((x + 10, step, x + 93, step), fill=light, width=2)
                else:
                    draw.rounded_rectangle((x + 38, step, x + 64, step + 32), radius=9, fill=light)
        if motif == "roof":
            draw.line((280, 697, 830, 390), fill=light, width=5)
        if motif == "garden":
            for i in range(5):
                draw.arc((224, 495 + i * 50, 855, 845 + i * 10), 15, 170, fill=light, width=3)
    elif motif in {"volcano", "mound", "pyramid", "rock"}:
        if motif == "pyramid":
            for i in range(6):
                draw.polygon([(274 + i * 39, 812 - i * 65), (813 - i * 39, 812 - i * 65),
                              (770 - i * 39, 754 - i * 65), (317 + i * 39, 754 - i * 65)],
                             fill=shade, outline=light, width=3)
        elif motif == "rock":
            draw.rounded_rectangle((282, 360, 799, 874), radius=85, fill=shade, outline=light, width=3)
            draw.polygon([(467, 450), (613, 450), (613, 535), (697, 535), (697, 680), (613, 680),
                          (613, 773), (467, 773), (467, 680), (383, 680), (383, 535), (467, 535)], fill=light)
        else:
            for i in range(5):
                draw.polygon([(243 + i * 21, 825 - i * 17), (480 + i * 8, 545 - i * 29),
                              (608 - i * 9, 550 - i * 29), (840 - i * 18, 825 - i * 17)],
                             fill=shade, outline=light, width=3)
            if motif == "volcano":
                for i in range(10):
                    x, y = 455 + rng.randrange(165), 300 + rng.randrange(137)
                    draw.ellipse((x, y, x + 10, y + 10), fill=light)
    elif motif in {"tablet", "seal"}:
        draw.rounded_rectangle((322, 379, 752, 811), radius=26 if motif == "tablet" else 185,
                               fill=shade, outline=light, width=4)
        for i in range(8):
            y = 452 + 42 * i
            for x in range(419, 688, 28):
                if rng.random() > .22:
                    draw.line((x-8, y+6, x+3, y-5, x+11, y+7), fill=light, width=3)
    elif motif in {"islands", "ship", "water", "tunnel"}:
        for i in range(8):
            y = 481 + i * 42
            draw.arc((207, y - 78, 870, y + 89), 12, 177, fill=shade, width=5)
        if motif == "islands":
            for i in range(11):
                x, y = 300 + i % 4 * 122, 425 + i // 4 * 113 + rng.randrange(26)
                draw.polygon([(x, y), (x + 90, y-24), (x+127, y+40), (x+39, y+64)], fill=shade, outline=light, width=3)
        elif motif == "ship":
            draw.polygon([(282, 670), (759, 670), (696, 780), (363, 780)], fill=shade, outline=light, width=3)
            draw.polygon([(523, 448), (523, 636), (361, 636)], fill=light)
            draw.line((540, 427, 540, 682), fill=light, width=5)
        else:
            for i in range(5):
                x, y = 303 + 101 * i, 475 + 35 * i
                draw.line((x, y, x, 715 + i * 11), fill=light, width=8)
            draw.line((300, 713, 771, 762), fill=light, width=9)


def render_story(path, story):
    rng = random.Random(story["id"])
    background, shade, accent = rng.choice([
        ((15, 32, 38), (52, 80, 82), (119, 219, 202)),
        ((41, 24, 37), (91, 54, 77), (244, 179, 187)),
        ((35, 29, 20), (94, 70, 43), (241, 202, 127)),
        ((17, 26, 49), (52, 73, 127), (171, 195, 252)),
        ((32, 35, 24), (77, 85, 52), (210, 223, 145)),
    ])
    image = Image.new("RGB", (1080, 1920), background)
    draw = ImageDraw.Draw(image)
    for y in range(1920):
        t = 0.31 * max(0, 1 - abs(y - 620) / 740)
        draw.line((0, y, 1080, y), fill=tuple(round(a + (b-a)*t) for a, b in zip(background, shade)))
    draw.rounded_rectangle((55, 235, 1024, 1685), radius=40, outline=shade, width=3)
    draw.text((104, 278), "TARİHİN BİLİNMEYEN GERÇEKLERİ", font=font(28), fill=accent)
    artwork(draw, story["motif"], shade, accent, rng)
    draw.text((104, 934), "TEMSİLÎ İLLÜSTRASYON", font=font(22), fill=accent)
    draw_text(draw, f"{story['place']}  ·  {story['era']}", (104, 991), 872, 31, accent, max_lines=2)
    y = draw_text(draw, story["title"], (104, 1066), 872, 71, "#ffffff", max_lines=2, leading=1.10)
    y = draw_text(draw, story["fact"], (104, y + 36), 872, 41, "#ece9e1", bold=False, max_lines=6)
    if y > 1550:
        raise ValueError(f"Hikâye metni güvenli alana sığmadı: {story['id']}")
    draw.line((104, 1557, 976, 1557), fill=shade, width=3)
    draw_text(draw, story["source"], (104, 1592), 872, 25, accent, bold=False, max_lines=2)
    image.save(path, optimize=True)


def make_calendars(out, date_start, observations, history, planned_id):
    week = date_start - timedelta(days=date_start.weekday())
    month = date_start.replace(day=1)
    next_month = (month + timedelta(days=32)).replace(day=1)
    for name, start, days in (("HAFTALIK", week, 7), ("AYLIK", month, (next_month-month).days)):
        rows = []
        for i in range(days):
            day = start + timedelta(days=i)
            row = day_slots(day, observations)
            already = history.get(day.isoformat())
            row["reel"]["topic"] = (planned_id if day == date_start else (already or {}).get("reel_id"))
            row["planned_status"] = ("review_required" if day == date_start or already else "topic_pending")
            rows.append(row)
        write_json(out / f"{name}_TAKVIM.json", rows)
        text = [f"# {name.title()} yayın takvimi", "",
                "Türkiye saati. Saatler kullanıcı onayıyla uygulanır.", "",
                "| Tarih | Reels | 10 hikâye saati | Konu |",
                "| --- | --- | --- | --- |"]
        for row in rows:
            text.append(f"| {row['date']} | {row['reel']['time']} | "
                        f"{', '.join(item['time'] for item in row['stories'])} | "
                        f"{row['reel']['topic'] or 'Editoryal seçim bekleniyor'} |")
        (out / f"{name}_TAKVIM.md").write_text("\n".join(text) + "\n", encoding="utf-8")


def disclosures(topic, seo):
    facts = "\n\n".join(topic["facts"])
    names = "\n".join(f"{source['title']}\n{source['url']}" for source in topic["sources"])
    caption = (f"{topic['title']}\n\n{topic['hook']}\n\n{facts}\n\n"
               f"Tarihî bağlam • {topic['context']}\n\n"
               f"Kanıtın sınırı • {topic.get('evidence_boundary', '')}\n\n"
               f"Kaynaklar\n{names}\n\n"
               "Görsel notu • Temsilî şemalar ve canlandırmalar görüntü üzerinde etiketlidir.\n\n"
               + " ".join(seo["hashtags"]))
    if len(caption) > 2200:
        # The review package retains all URLs when Instagram's caption limit is reached.
        lead = topic["sources"][0]
        caption = caption.split("\n\nKaynaklar\n", 1)[0] + (
            f"\n\nAna kaynak • {lead['title']}\n{lead['url']}\n"
            "Diğer kaynaklar sabit yorumda.\n\n" + " ".join(seo["hashtags"]))
    if len(caption) > 2200:
        raise ValueError("Instagram açıklaması 2200 karakter sınırını aştı.")
    pin = (f"{topic['hook']} Videoda hangi ayrıntı dikkatinizi çekti?\n\n"
           "Kaynak künyeleri\n" + "\n".join(source["title"] for source in topic["sources"]))
    if len(pin) > 2200:
        raise ValueError("Sabit yorum uzunluk sınırını aştı.")
    return caption, pin


def prepare(out, ledger, date_start, demo=False, observations=None):
    out.mkdir(parents=True, exist_ok=True)
    history = load_json(ledger)
    if not demo and date_start.isoformat() in history:
        raise ValueError(f"{date_start} paketi daha önce oluşturuldu.")
    board = load_json(out / "editorial/EDITORIAL_DECISION_REPORT.json")
    topic = choose_reel(load_json(TOPIC_CATALOGUE), history, board, demo)
    research = board["research"]
    selected = choose_stories(load_json(STORY_CATALOGUE), {} if demo else history, topic, date_start, research)
    if observations is None:
        settings = load_json(ROOT / "config/settings.json")
        settings["instagram_insights_enabled"] = os.getenv("INSTAGRAM_INSIGHTS_ENABLED") == "1"
        insights = fetch_read_only_insights(settings=settings)
        observations = insights["records"]
        insights_status = insights["status"]
    else:
        insights_status = "provided_observations"
    seo = search_notes(topic, research)
    caption, pin = disclosures(topic, seo)
    story_dir = out / "stories"
    story_dir.mkdir(exist_ok=True)
    slots = day_slots(date_start, observations)
    for order, (story, slot) in enumerate(zip(selected, slots["stories"], strict=True), 1):
        story["file"] = f"stories/{order:02d}-{story['id']}.png"
        story["schedule"] = slot
        story["audio"] = False
        render_story(out / story["file"], story)
    make_calendars(out, date_start, observations, history, topic["id"])
    (out / "REELS_ACIKLAMA.txt").write_text(caption + "\n", encoding="utf-8")
    (out / "SABIT_YORUM.txt").write_text(pin + "\n", encoding="utf-8")
    write_json(out / "SEO_ARASTIRMASI.json", seo)
    write_json(out / "DAILY_PLAN.json", {
        "date": date_start.isoformat(), "timezone": ISTANBUL.key, "demo": demo,
        "coordinator": board["coordinator"], "editorial_status": board["status"],
        "insights_status": insights_status,
        "scheduled_reel": slots["reel"], "reel_id": topic["id"],
        "stories": selected, "instagram_auto_publish": False, "human_approval_required": True})
    return topic["id"]


def verify_package(out, ledger, next_ledger):
    plan = load_json(out / "DAILY_PLAN.json")
    reel_audit = load_json(out / "E2E_REPORT.json")
    stages = reel_audit["stages"]
    required = ("research", "topic_selection", "script", "narration", "visuals", "editing", "mp4")
    if any(stages[key]["status"] != "passed" for key in required):
        raise ValueError("Reels doğrulaması tamamlanmadı.")
    if (not plan["human_approval_required"] or plan["instagram_auto_publish"]
            or reel_audit["instagram_published"] or not reel_audit["human_approval_required"]):
        raise ValueError("İnsan onayı ve Instagram kilidi doğrulanamadı.")
    stories = plan["stories"]
    if (len(stories) != 10 or len({row["fingerprint"] for row in stories}) != 10
            or len({row["id"] for row in stories}) != 10
            or len({row["group"] for row in stories}) != 10
            or len(list((out / "stories").glob("*.png"))) != 10):
        raise ValueError("On farklı hikâye bulunamadı.")
    image_hashes = set()
    if [row["schedule"]["time"] for row in stories] != list(STORY_TIMES):
        raise ValueError("Hikâye saatleri planla uyuşmuyor.")
    for row in stories:
        image_path = out / row["file"]
        with Image.open(image_path) as image:
            if image.size != (1080, 1920) or image.format != "PNG" or image.n_frames != 1:
                raise ValueError(f"Geçersiz hikâye görseli {row['id']}")
            image.load()
            image_hashes.add(hashlib.sha256(image.tobytes()).hexdigest())
        if row["audio"] or not row["url"].startswith("https://") or not row["source"]:
            raise ValueError(f"Sessizlik veya kaynak kaydı doğrulanamadı {row['id']}")
    if len(image_hashes) != 10:
        raise ValueError("Hikâye görselleri tekrarlanıyor.")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "0.60",
                    "-i", str(out / REEL), "-frames:v", "1", "-q:v", "2",
                    str(out / "REELS_KAPAK.jpg")], check=True)
    with Image.open(out / "REELS_KAPAK.jpg") as cover:
        if cover.size != (1080, 1920):
            raise ValueError("Reels kapağı dikey formatta değil.")
    history = load_json(ledger)
    if not plan["demo"]:
        existing = [row for day in history.values() for row in day["stories"]]
        known_ids = {row["id"] for row in existing}
        known_facts = {row["fingerprint"] for row in existing}
        if (plan["date"] in history or plan["reel_id"] in {day["reel_id"] for day in history.values()}
                or any(row["id"] in known_ids or row["fingerprint"] in known_facts for row in stories)):
            raise ValueError("Üretim kaydında tarih veya konu tekrarı var.")
        history[plan["date"]] = {"reel_id": plan["reel_id"], "stories": [
            {key: row[key] for key in ("id", "group", "fingerprint")} for row in stories]}
        write_json(next_ledger, history)
    write_json(out / "DAILY_VERIFICATION.json", {
        "status": "verified_review_required", "date": plan["date"], "demo": plan["demo"],
        "reels": 1, "stories": 10, "story_size": [1080, 1920], "audio_in_stories": False,
        "instagram_published": False, "human_approval_required": True,
        "narration": stages["narration"], "reel_checks": stages["mp4"],
        "editorial_status": plan["editorial_status"]})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=("prepare", "verify"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--next-ledger", type=Path)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    try:
        if args.step == "prepare":
            print(prepare(args.out, args.ledger, tomorrow(), args.demo))
        else:
            if args.next_ledger is None:
                parser.error("--next-ledger zorunlu")
            verify_package(args.out, args.ledger, args.next_ledger)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        if args.out.is_dir():
            write_json(args.out / "DAILY_FAILURE.json", {"stage": args.step, "status": "failed", "reason": str(exc)})
        parser.exit(1, f"Günlük paket durdu: {exc}\n")


if __name__ == "__main__":
    main()
