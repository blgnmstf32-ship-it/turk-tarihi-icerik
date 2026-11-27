"""Local, source-bound Reels preflight. It does not call providers or create media."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
THRESHOLD = 85
MAX_REVISIONS = 2
WEIGHTS = {
    "hook": 20, "topic": 20, "retention": 20, "shareability": 15,
    "visual_quality": 10, "sound_quality": 5, "originality": 5, "cover_title": 5,
}
EDITOR_RULE = (
    "Doğruluk, bilimsel güvenilirlik ve telif önceliklidir. Puan dahili kurgu kalitesidir. "
    "Beş açılış ve üç senaryo arasındaki seçimi, ilk üç saniye ile kapanışta karşılanan vaat üzerinden değerlendir. "
    "İstatistik, etiket hacmi, kaynak veya onay uydurma."
)
RISK_CHECKS = ("source_claims", "scientific_accuracy", "rights", "misleading_promise")


@lru_cache(maxsize=1)
def playbook():
    return json.loads((ROOT / "config/reels_playbook.json").read_text(encoding="utf-8"))


def specialist_guidance(role, brand, topic=None):
    from scripts.skill_registry import editorial_method
    from scripts.skill_router import select_knowledge, specialist_context

    guide = playbook()
    focus = role.get("reels_review", {})
    guidance = {
        "task": focus.get("task"),
        "method": editorial_method(focus.get("technique")),
        "brand_strategy": guide["brands"][brand]["topic_strategy"],
    }
    notes = select_knowledge(specialist_context(role, brand, topic))
    if notes:
        guidance["skill_notes"] = [note["guidance"] for note in notes]
    return guidance


def _terms(text):
    return re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)


def _short_subject(topic):
    for value in [topic.get("hook_subject"), *(topic.get("instagram_keywords") or []), topic["title"]]:
        if isinstance(value, str) and 1 <= len(_terms(value)) <= 3 and len(value) <= 32:
            return value.strip().rstrip(".!?")
    # An authored title can be longer than a one-breath opening.
    return ""


def _sources(topic):
    rows = topic.get("sources") or [{"url": topic.get("source_url")}]
    links = []
    for row in rows:
        url = row.get("url") if isinstance(row, dict) else None
        if isinstance(url, str):
            parsed = urlsplit(url)
            if parsed.scheme == "https" and parsed.hostname and not parsed.username:
                links.append(url)
    return list(dict.fromkeys(links))


def _hooks(topic, brand, lines):
    subject = _short_subject(topic)
    authored = topic.get("hook") or lines[0]
    if subject:
        other = [
            f"{subject} hakkında ne biliyoruz?",
            f"{subject}: kanıt ne söylüyor?",
            f"{subject} neden önemli?" if brand == "tarih" else f"{subject}: hangi adım önemli?",
            f"{subject} için neyi hatırlamalıyız?",
        ]
    else:
        other = [
            "Buradaki asıl soru ne?",
            "Kanıt bize ne söylüyor?",
            "Bu ayrıntı neden önemli?",
            "Buradan ne öğreniyoruz?",
        ]
    lines_to_try = [authored, *other]
    existing = set()
    for i, line in enumerate(lines_to_try):
        if tuple(_terms(line)) in existing:
            line = f"Bu konunun {['açılışı', 'sorusu', 'kanıtı', 'bağlamı', 'sonucu'][i]} ne?"
            lines_to_try[i] = line
        existing.add(tuple(_terms(line)))
    return [
        {"family": family, "line": line, "title_on_first_frame": topic["title"],
         "estimated_seconds": round(len(_terms(line)) / 2.5, 1)}
        for family, line in zip(playbook()["brands"][brand]["hook_families"], lines_to_try)
    ]


def media_direction(topic, brand):
    """Plans the technique. Existing production and permission gates own execution."""
    category = topic.get("category", "")
    mechanism = topic.get("visual_mode") in {"battle_map", "siege_city", "layer_diagram"} or category in {
        "kayip_sehir", "mekanizma", "cilt_bariyeri", "anatomi",
    }
    return {
        "source_provider": ["wikimedia", "openverse"],
        "render_default": "remotion",
        "html_graphics_alternative": ["hyperframes", "gsap"],
        "vector_explainer": "lottie" if brand == "bakim" else None,
        "spatial_explainer": ["three.js", "blender"] if mechanism else [],
        "representation_label": "TEMSİLÎ CANLANDIRMA" if brand == "tarih" else "TEMSİLÎ ŞEMA · ÖLÇEK DIŞI",
        "camera": "Kanıtı veya ölçeği açan sakin hareket",
        "transitions": "Anlam değişiminde kesme, ilişki varsa eşlemeli geçiş",
        "captions": "faster-whisper: Türkçe zamanlama, okunaklı vurgu",
        "picture_qa_if_needed": ["opencv", "pyscenedetect"],
        "sound": "Charon" if brand == "tarih" else "Sulafat",
        "audio_qa": "loudnorm, konuşma öncelikli ducking",
        "sfx_if_needed": ["earshot", "real-sfx-cues"],
        "source_review_required": True,
    }


def _variant(brand, structure, hook, title, core, revision):
    first = hook["line"]
    if revision and hook["estimated_seconds"] > 3:
        first = {
            "nesne_izinde": "Bu ipucu ne anlatıyor?",
            "kanıt_adım_adım": "Kanıt ne söylüyor?",
            "bağlam_ve_sonuç": "Bu ayrıntı neden önemli?",
            "uygulama_önce": "Doğru an ne zaman?",
            "kanıt_ve_mekanizma": "İşin püf noktası ne?",
            "rutin_ve_sınır": "Hangi adım önemli?",
        }[structure]
    bridge, early_proof, closing = {
        "nesne_izinde": ("", True, "Başta gördüğümüz ayrıntıyı kaynakla birlikte yeniden düşünün."),
        "kanıt_adım_adım": ("Önce kanıta bakalım.", True, "Kanıtın bize ne anlattığını kaynaklardan takip edebilirsiniz."),
        "bağlam_ve_sonuç": ("Önce bağlamı kuralım.", False, "Başladığımız soruya şimdi bu bağlamla yeniden bakalım."),
        "uygulama_önce": ("", True, "Bu adımı gerektiğinde hatırlamak için kaynaklı özeti saklayabilirsiniz."),
        "kanıt_ve_mekanizma": ("Önce önerinin dayanağına bakalım.", True, "Uygulama koşullarını açıklamadaki kaynaktan kontrol edebilirsiniz."),
        "rutin_ve_sınır": ("Bu adımın günlük rutindeki yerini düşünelim.", False, "Bakım adımlarını kendi ihtiyacınıza göre değerlendirin."),
    }[structure]
    opening_visual = {
        "nesne_izinde": "arşiv nesnesinin ayrıntısı",
        "kanıt_adım_adım": "belgedeki ilk doğrulanabilir ipucu",
        "bağlam_ve_sonuç": "tarih ve konum",
        "uygulama_önce": "rutin adımının yakın planı",
        "kanıt_ve_mekanizma": "adım ve dayanağı",
        "rutin_ve_sınır": "uygulamanın bağlamı",
    }[structure]
    if revision == 2:
        bridge = ""
        if not early_proof:
            opening_visual = "ilk kaynaklı kanıt veya uygulama adımı"
        closing = "Kaynak ve kısa özet açıklamada."
    words = len(_terms(" ".join([first, bridge, *core, closing])))
    return {
        "brand": brand, "scenario": structure, "hook_family": hook["family"], "opening": first,
        "opening_seconds_estimate": round(len(_terms(first)) / 2.5, 1),
        "spoken": [first, *([bridge] if bridge else []), *core, closing],
        "estimated_seconds": round(words / 2.5, 1), "proof_before_context": early_proof or revision == 2,
        "cover_title": title, "lead_in": bridge, "last_line": closing,
        "suggested_first_frame": opening_visual,
    }


def _score(candidate, links, topic, plan, core):
    first = candidate["opening"]
    first_terms = _terms(first)
    title_terms = set(_terms(candidate["cover_title"]))
    subject_on_first_frame = bool(title_terms) and len(candidate["cover_title"]) <= 58
    contains_topic = bool(title_terms.intersection(first_terms))
    clear_exit = any(term in _terms(candidate["last_line"]) for term in ("kaynak", "kaynakla", "kaynaklardan", "saklayabilirsiniz"))
    coherent_length = 30 <= candidate["estimated_seconds"] <= 75
    features = {
        "hook": [(8, 2 <= len(first_terms) and candidate["opening_seconds_estimate"] <= 3),
                 (6, subject_on_first_frame), (6, contains_topic or candidate["proof_before_context"])],
        "topic": [(10, links), (6, len(core) >= 2), (4, bool(topic.get("category") or topic.get("source_url")))],
        "retention": [(7, candidate["proof_before_context"]), (7, coherent_length),
                      (6, 3 <= len(core) <= 16)],
        "shareability": [(7, clear_exit), (4, len(core) >= 2), (4, links)],
        "visual_quality": [(5, subject_on_first_frame), (5, plan["representation_label"])],
        "sound_quality": [(3, candidate["opening_seconds_estimate"] <= 3), (2, plan["audio_qa"])],
        "originality": [(3, contains_topic or bool(topic.get("hook"))), (2, bool(topic.get("context") or topic.get("script")))],
        "cover_title": [(3, subject_on_first_frame), (2, title_terms and links)],
    }
    return {dimension: sum(points for points, met in checks if met) for dimension, checks in features.items()}


def review(topic, brand, narration, *, fixed_recording=False):
    """Evaluate the 5×3 matrix. Keep the source-bound body and its original order."""
    lines = [line.strip() for line in narration if line and line.strip()]
    if not lines:
        raise ValueError("Reels için kaynaklı bir anlatı gerekli.")
    profile = playbook()["brands"][brand]
    links = _sources(topic)
    checks = topic.get("editorial_checks") or {}
    blockers = [name for name in RISK_CHECKS if checks.get(name) in ("failed", "blocked")]
    if not links:
        blockers.append("source_links_missing")
    core = lines[1:] if len(lines) > 1 and lines[0] == topic.get("hook") else lines
    if len(core) < 2:
        blockers.append("evidence_body_missing")
    hooks = _hooks(topic, brand, lines)
    plan = media_direction(topic, brand)
    rounds = []
    finalists = {}
    pending = [(structure, opening) for structure in profile["scenarios"] for opening in hooks]
    for attempt in range(MAX_REVISIONS + 1):
        entries, needs_revision = [], []
        for structure, opening in pending:
            candidate = _variant(brand, structure, opening, topic["title"], core, attempt)
            scores = _score(candidate, links, topic, plan, core)
            row = {**candidate, "scores": scores, "total": sum(scores.values()), "revision": attempt}
            entries.append(row)
            key = (structure, opening["family"])
            if key not in finalists or row["total"] > finalists[key]["total"]:
                finalists[key] = row
            if finalists[key]["total"] < THRESHOLD:
                needs_revision.append((structure, opening))
        leading = max(finalists.values(), key=lambda row: row["total"])
        rounds.append({"revision": attempt, "candidates": entries, "best_score": leading["total"]})
        if blockers or not needs_revision:
            break
        pending = needs_revision
    return {
        "topic_id": topic["id"], "brand": brand, "playbook_version": playbook()["version"],
        "type": "editorial_plan_score", "score_is_viral_probability": False, "threshold": THRESHOLD,
        "weights": WEIGHTS, "source_links": links, "blockers": blockers,
        "status": ("blocked_by_editorial_safety" if blockers else
                   "passes_edit_index" if leading["total"] >= THRESHOLD else "needs_human_revision"),
        "fixed_recording": fixed_recording, "next_step_requires_human_approval": True,
        "score_scope": "script_and_production_plan_only", "media_checked": False,
        "hooks": hooks, "scenarios": profile["scenarios"], "rounds": rounds,
        "finalists": list(finalists.values()), "best": leading,
        "media_direction": plan, "follow_promise": profile["follow_promise"],
    }


def write_review(output, topic, brand, narration, *, fixed_recording=False):
    result = review(topic, brand, narration, fixed_recording=fixed_recording)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    from scripts.content_strategy import load_learning
    from scripts.performance_learning import reels_benchmarks

    observations = load_learning(ROOT / "data/performance.jsonl")
    result["performance_context"] = reels_benchmarks(observations, brand)
    path = output / "REELS_EDITORIAL_REVIEW.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["blockers"] or (not fixed_recording and result["status"] != "passes_edit_index"):
        raise ValueError(f"Reels editoryal ön kontrolü: {result['status']}. Rapor: {path}")
    return result
