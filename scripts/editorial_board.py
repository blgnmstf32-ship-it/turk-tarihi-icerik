"""AI General Editor: coordinate research, strategy, role debate and reviewable reports."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from scripts.content_strategy import build_debate, load_learning, score_ideas, CATEGORY_LABELS, CONCEPT
from scripts.editorial_llm import discussion_completed, review
from scripts.performance_learning import record_outcome, reels_benchmarks
from scripts.editorial_research import collect_public_research
from scripts.instagram_insights import fetch_read_only_insights

ROOT=Path(__file__).resolve().parents[1]

def _llm_review(candidates, research):
    settings = json.loads((ROOT / "config/settings.json").read_text(encoding="utf-8"))
    return review(settings, candidates, research)


def run_board(output, research_config=None, performance_path=None, research_fn=None, llm_fn=None, insights_fn=None):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    config=research_config or json.loads((ROOT/"config/research_sources.json").read_text(encoding="utf-8"))
    performance_path=Path(performance_path or ROOT/config.get("historical_data_file","data/performance.jsonl"))
    research=(research_fn or collect_public_research)(config)
    insights=(insights_fn or fetch_read_only_insights)()
    external_rows=insights.get("records",[]) if insights.get("status")=="ok" else []
    persisted=load_learning(performance_path)
    known={(r.get("brand"),r.get("content_id"),str(r.get("captured_at_utc",""))[:10]) for r in persisted}
    new_records=0
    for row in external_rows:
        marker=(row.get("brand"),row.get("content_id"),str(row.get("captured_at_utc",""))[:10])
        if row.get("content_id") and row.get("category") and marker not in known:
            record_outcome(row,performance_path);known.add(marker);new_records+=1
    outcomes=[row for row in load_learning(performance_path) if row.get("brand") in (None, "tarih")]
    candidates=score_ideas(research,outcomes)
    debate=build_debate(candidates,research,outcomes)
    llm=(llm_fn or _llm_review)(candidates,research)
    llm_complete = discussion_completed(llm)
    idea_reviews = {row["idea_id"]: {**row, "role": stage["role"], "model": stage["model"],
                                    "response_source": stage.get("response_source")}
                    for stage in llm.get("stages", []) if stage.get("status") == "proposal"
                    for row in stage["answer"].get("idea_reviews", [])}
    for candidate in candidates:
        candidate["idea_assessment"] = idea_reviews.get(candidate["id"])
    category_comparison=[]
    for category, label in CATEGORY_LABELS.items():
        items=[c for c in candidates if c["category"]==category]
        category_comparison.append({"category":category,"idea_count":len(items),
            "mean_relative_index":round(sum(x["potential_index"] for x in items)/len(items),1) if items else None,
            "label":label,
            "sample_size":len([r for r in outcomes if r.get("category")==category])})
    report={"coordinator":"AI Genel Yayın Yönetmeni","concept":CONCEPT,"status":"recommendations_ready" if llm_complete else "preliminary_only",
        "research":research,"learning":{"source":"Instagram Insights read-only" if external_rows else str(performance_path),
           "records_used":len(outcomes),"new_insights_records_saved":new_records,
           "reels_cohorts":reels_benchmarks(outcomes,"tarih"),
           "insights_status":insights.get("status"),"real_metrics_available":bool(outcomes),
           "account_follower_change_metrics":insights.get("account_metrics",[]),
           "media_metric_coverage":{key:sum(1 for r in external_rows if r.get(key) is not None)
               for key in ("views","reach","avg_watch_seconds","shares","follows")},
           "account_follow_change_available":any(x.get("name")=="follows_and_unfollows" and x.get("values") for x in insights.get("account_metrics",[])),
           "account_metric_attribution":"account-level follower changes are not attributed to an individual Reel without a supported post-level metric"},
        "strategy":{"categories_compared":category_comparison,
            "ranking_method":"Göreli pilot önceliği. Görsel plan, süre, doğrudan trend eşleşmesi, karşılaştırılabilir izlenme ve yeterli geçmiş ölçümü kullanılır."},
        "recommendations":candidates,"deterministic_prescreen":debate,"coordinator_llm":llm,
        "idea_review_coverage":{"llm_assessed":sum(bool(c["idea_assessment"]) for c in candidates),
                                "total":len(candidates)},
        "decision":"İlk sıradaki fikri 1 küçük pilot olarak test et; bu rapor yayın kararı değildir.",
        "estimated_paid_cost_try":0,"human_approval_required":True,"instagram_publish_enabled":False,
        "paid_api_services_enabled":False}
    (out/"EDITORIAL_DECISION_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    coverage = research.get("metrics_coverage", {})
    lines = [f"# {CONCEPT}", "", "Haftalık yayın kararı • AI Genel Yayın Yönetmeni", "",
        f"Araştırma {research['evidence_counts']['trend_items']} trend, {research['evidence_counts']['competitor_videos']} video ve "
        f"{len(research.get('source_leads', []))} akademik kaynak ipucu içeriyor.",
        f"Rakip metrik kapsamı: {coverage.get('views', 0)} izlenme, {coverage.get('likes', 0)} beğeni, "
        f"{coverage.get('comments', 0)} yorum, {coverage.get('shares', 0)} paylaşım kaydı. "
        f"Kendi performans arşivinde {len(outcomes)} kayıt var.",
        "İzlenme potansiyeli, pilot önceliği için editoryal bir hipotezdir. YouTube ölçümleri Reels tahmini olarak aktarılmaz. "
        "Süre tahminleri araştırma ve kurguyu kapsar. 0 TL dış servis/varlık maliyeti öngörülür; iş gücü ve donanım hariçtir.",
        "", "## Kategori karşılaştırması"]
    for item in category_comparison:
        lines.append(f"- {item['label']} • {item['idea_count']} öneri • {item['sample_size']} geçmiş kayıt")
    lines += ["", "## İlk 10 video fikri"]
    for i, candidate in enumerate(candidates, 1):
        lines += ["", f"### {i}. {candidate['title']}",
            f"- Kategori: {CATEGORY_LABELS[candidate['category']]}",
            f"- İlk üç saniye: {candidate['hook']}",
            "- İzlenme hipotezi: " + " ".join(candidate["success_rationale"]),
            f"- Görsel: {candidate['visual']}",
            f"- Üretim: yaklaşık {candidate['effort_minutes']} dakika, 0 TL dış servis/varlık.",
            f"- Kanıt sınırı: {candidate['evidence_boundary']}",
            "- Kaynaklar: " + " · ".join(f"[{src['title']}]({src['url']})" for src in candidate["sources"])]
        for video in candidate["evidence"]["comparable_videos"]:
            if any(video[key] is not None for key in ("views", "likes", "comments", "shares")):
                metrics = ", ".join(f"{video[key]:,} {label}" for key, label in
                    (("views", "izlenme"), ("likes", "beğeni"), ("comments", "yorum"), ("shares", "paylaşım"))
                    if video[key] is not None)
                freshness = f" ({video['freshness']})" if video.get("freshness") else ""
                lines.append(f"- Benzer [YouTube videosu]({video['url']}) • {metrics}{freshness}.")
        assessment = candidate["idea_assessment"]
        if assessment:
            lines.extend([f"- {assessment['role']} görüşü: {assessment['rationale']}",
                          f"- Açık araştırma sorusu: {assessment['open_question']}",
                          f"- İncelenecek [kaynak]({assessment['source_url']})."])
        else:
            lines.append("- Bu konu için modelden ayrı bir görüş alınamadı. Yukarıdaki değerlendirme kurallı ön elemedir.")
    lines += ["", "## Ajan değerlendirmesi",
        f"OpenRouter: {llm.get('calls', 0)} yeni istek, {llm.get('cached_roles', 0)} onaylı kayıt • {llm.get('status')}.",
        "Yayın ve ücretli API kullanımı insan onayına bağlıdır."]
    if llm.get("requirements_missing"):
        lines.append("Eksik yapılandırma: " + ", ".join(llm["requirements_missing"]))
    if not llm_complete:
        lines.append("Sıralama kurallı ön değerlendirmedir. Tamamlanmış LLM tartışması yok.")
    for stage in llm.get("stages", []):
        model = stage.get("model") or "bilinmiyor"
        http = stage.get("http_status") or "yok"
        lines.append(f"- **{stage['role']}** • {stage['status']} • model: {model} • HTTP: {http}")
        if stage.get("reason"):
            lines.append(f"  Durma nedeni: {stage['reason']}.")
        if stage.get("response_source") == "cache":
            lines.append("  Aynı girdiye verilen önceki gerçek model yanıtı kullanıldı.")
        for index, item in enumerate(stage.get("attempts", []), 1):
            lines.append(f"  Deneme {index}: {item['status']}, HTTP {item.get('http_status') or 'yok'}, "
                         f"model {item.get('model') or 'bilinmiyor'} "
                         f"(istenen {item.get('requested_model') or 'yok'}).")
        if stage.get("status") == "proposal":
            answer = stage["answer"]
            lines.append(f"- **{stage['role']}** • {answer['rationale']}")
            if answer.get("counterargument"):
                lines.append(f"  Karşı görüş: {answer['counterargument']}")
            for lead in answer.get("research_queue", []):
                lines.append(f"  Araştırma kuyruğu: {lead.get('title', 'Kaynak önerisi')} ({lead['source_url']})")
    if llm_complete and llm.get("decision"):
        lines.append(f"Önerilen hazır aday: {llm['decision'].get('selected_idea_id') or 'yok'}.")
    (out/"EDITORIAL_DECISION_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return report

def main():
    parser=argparse.ArgumentParser(description="Ücretsiz RSS araştırması ve haftalık içerik karar raporu")
    parser.add_argument("--out",default="output/editorial");parser.add_argument("--performance",default="")
    parser.add_argument("--require-llm", action="store_true",
                        help="Exit unsuccessfully unless all four real free-model reviews complete")
    args=parser.parse_args();report=run_board(args.out,performance_path=args.performance or None)
    print(json.dumps({"status":report["status"],"top_idea":report["recommendations"][0]["id"],
        "recommendations":len(report["recommendations"]),"research":report["research"]["evidence_counts"],
        "actual_llm_used":report["coordinator_llm"]["actual_llm_used"],"llm_calls":report["coordinator_llm"]["calls"],
        "report":str(Path(args.out)/"EDITORIAL_DECISION_REPORT.md")},ensure_ascii=False,indent=2))

    if args.require_llm and not discussion_completed(report["coordinator_llm"]):
        parser.exit(1, "Dört gerçek OpenRouter görüşü tamamlanamadı. Ayrıntılar karar raporunda.\n")


if __name__=="__main__":main()
