"""Transparent content portfolio scoring, idea debate, and learning from outcomes."""
from __future__ import annotations
from collections import defaultdict
import json, re
from pathlib import Path

CONCEPT = "TARİHİN BİLİNMEYEN GERÇEKLERİ"
CATEGORY_LABELS = {
    "az_bilinen_olay": "Az bilinen gerçekler ve olaylar",
    "tarihi_gizem": "Tarihî gizemler ve açık sorular",
    "kayip_sehir": "Kayıp şehirler, uygarlıklar ve antik yapılar",
    "kesif": "Arkeolojik keşifler ve tarihî eserler",
    "unutulmus_savas": "Unutulmuş savaşlar, hükümdarlar ve askerî stratejiler",
    "siradisi_hikaye": "Türk ve dünya tarihinden sıra dışı hikâyeler",
}
IDEAS_PATH = Path(__file__).resolve().parents[1] / "data" / "editorial_ideas.json"


def load_ideas():
    return json.loads(IDEAS_PATH.read_text(encoding="utf-8"))


def matches(term, title):
    return f" {_norm(term)} " in f" {_norm(title)} "


def _norm(s): return re.sub(r"[^a-z0-9çğıöşü]+"," ",str(s).lower()).strip()

def load_learning(path):
    p=Path(path)
    if not p.exists(): return []
    if p.suffix.lower()==".json":
        data=json.loads(p.read_text(encoding="utf-8")); return data if isinstance(data,list) else data.get("records",[])
    rows=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: continue
    return rows

def score_ideas(research, outcomes):
    category_perf=defaultdict(list)
    for row in outcomes:
        category=row.get("category"); reach=row.get("views",row.get("reach")); shares=row.get("shares")
        watch=row.get("avg_watch_seconds",row.get("watch_time_seconds")); followers=row.get("follows",row.get("follower_gain"))
        if not category: continue
        # Normalize per-view, when denominators exist. Missing measurements remain missing.
        rates=[]
        if reach and shares is not None: rates.append(float(shares)/max(1,float(reach)))
        if reach and followers is not None: rates.append(float(followers)/max(1,float(reach)))
        if watch is not None: rates.append(min(1,float(watch)/75))
        if rates: category_perf[category].append(sum(rates)/len(rates))
    candidates = []
    videos = [v for channel in research.get("competitors", []) for v in channel.get("videos", [])]
    for seed in load_ideas():
        terms = seed["focus_terms"]
        trend_hits = [row for row in research.get("trends", []) if any(matches(t, row["title"]) for t in terms)]
        comparable = []
        for video in videos:
            if not any(matches(t, video.get("title", "")) for t in terms):
                continue
            archived = video.get("archived_public_metrics", {})
            metrics = ({key: video.get(key) for key in ("views", "likes", "comments", "shares")}
                       if video.get("metrics_source") else
                       {key: archived.get(key) for key in ("views", "likes", "comments", "shares")})
            views = metrics["views"]
            interactions = [metrics[k] for k in ("likes", "comments") if metrics[k] is not None]
            comparable.append({"title": video["title"], "url": video.get("url"), "published": video.get("published"),
                **metrics, "known_like_comment_rate": round(sum(interactions)/views, 4) if views and interactions else None,
                "metrics_source": video.get("metrics_source") or archived.get("source"),
                "metrics_retrieved_at": video.get("metrics_retrieved_at") or archived.get("retrieved_on"),
                "freshness": archived.get("freshness") if not video.get("metrics_source") else None})
        history = category_perf.get(seed["category"], [])
        with_views = [row for row in comparable if row["views"] is not None]
        rationale = [seed["potential_reason"]]
        if with_views:
            rationale.append(f"{len(with_views)} benzer YouTube yayını için izlenme verisi bulundu; platform ve format farkı var.")
        else:
            rationale.append("Bu başlık için doğrudan karşılaştırılabilir izlenme verisi bulunamadı.")
        if trend_hits:
            rationale.append("Google Trends başlığında doğrudan konu eşleşmesi bulundu.")
        if len(history) >= 3:
            rationale.append(f"Kendi hesabındaki {len(history)} uyumlu ölçümden kategori sinyali kullanıldı.")
        score = 35 + seed["visual_strength"] * 4 + max(0, 12 - seed["effort_minutes"] // 12)
        score += min(len(trend_hits), 2)*3
        # A capped signal from relevant observations, not a transfer of YouTube reach to Reels.
        score += min(6, max((v["views"] for v in with_views), default=0) // 10000)
        if len(history) >= 3:
            score += min(8, round(sum(history)/len(history)*100))
        candidates.append({**seed, "potential_index": min(100, score),
            "potential_label": "Göreli pilot önceliği; başarı olasılığı değildir",
            "evidence": {"trend_matches": trend_hits[:3], "comparable_videos": comparable,
                         "own_metric_samples": len(history)},
            "success_rationale": rationale, "risks": [seed["evidence_boundary"]],
            "estimated_cost_try": 0, "estimated_cost_basis": "Dış servis/varlık ücreti; iş gücü ve donanım hariç",
            "estimated_production_minutes": seed["effort_minutes"],
            "production_plan": {"visual": seed["visual"], "voice": "Gemini Charon ile Türkçe belgesel anlatımı",
                                "edit": "60–75 s dikey Reels; ilk 3 s açılış; Remotion, FFmpeg ve hareketli altyazı"}})
    return sorted(candidates, key=lambda row: (-row["potential_index"], row["id"]))


def build_debate(candidates, research, outcomes):
    """Fallback diagnostics are explicitly deterministic."""
    return {"method": "kurallı ön değerlendirme", "actual_llm_used": False,
            "rounds": [{"idea_id": idea["id"], "idea": idea["title"], "positions": [
                {"role": "Veri kontrolü", "position": "Karşılaştırma",
                 "reason": f"{len(idea['evidence']['comparable_videos'])} benzer video kaydı."},
                {"role": "Kaynak kontrolü", "position": "Tarihî sınır", "reason": idea["evidence_boundary"]},
                {"role": "Üretim", "position": "Tahmini süre", "reason": f"{idea['effort_minutes']} dakika."}
            ], "counterpoint": "Yayın kararı için kaynak ve izleyici verisi tekrar kontrol edilir."}
                for idea in candidates[:3]]}
