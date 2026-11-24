"""AI General Editor: coordinate research, strategy, role debate and reviewable reports."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import requests
from scripts.content_strategy import build_debate, load_learning, score_ideas, CATEGORY_HYPOTHESES
from scripts.performance_learning import record_outcome
from scripts.editorial_research import collect_public_research
from scripts.instagram_insights import fetch_read_only_insights

ROOT=Path(__file__).resolve().parents[1]

def _llm_review(candidates, debate):
    """One coordinator call via explicitly enabled free-only model route; fail closed."""
    settings=json.loads((ROOT/"config/settings.json").read_text(encoding="utf-8"))
    if not settings.get("editorial_intelligence",{}).get("free_llm_enabled",False) or os.getenv("ENABLE_FREE_LLM")!="1" or not os.getenv("OPENROUTER_API_KEY"):
        return {"status":"disabled_or_not_configured","calls":0,"actual_llm_used":False}
    prompt=("You are an editorial coordinator. Compare these candidate proposals and debate notes. "
        "Return concise Turkish JSON with selected_idea_id, rationale, counterargument, checks. "
        "Use only supplied evidence, do not invent history, metrics, sources or probabilities. "
        "Potential scores are relative editorial indices, not success probabilities. Human review required.\n"+
        json.dumps({"candidates":candidates[:5],"debate":debate},ensure_ascii=False))
    try:
        response=requests.post("https://openrouter.ai/api/v1/chat/completions",timeout=30,
            headers={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"X-Title":"Turk Tarihi AI Editor"},
            json={"model":"openrouter/free","messages":[{"role":"user","content":prompt}],"temperature":0.2,"max_tokens":500})
        response.raise_for_status(); answer=response.json()["choices"][0]["message"]["content"]
        return {"status":"suggestion_review_required","calls":1,"actual_llm_used":True,"model":"openrouter/free",
                "paid_fallback":False,"suggestion":str(answer)[:5000]}
    except Exception as exc:
        return {"status":"failed_closed","calls":1,"actual_llm_used":False,"error_type":type(exc).__name__,"paid_fallback":False}

def run_board(output, research_config=None, performance_path=None, research_fn=None, llm_fn=None, insights_fn=None):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    config=research_config or json.loads((ROOT/"config/research_sources.json").read_text(encoding="utf-8"))
    performance_path=Path(performance_path or ROOT/config.get("historical_data_file","data/performance.jsonl"))
    research=(research_fn or collect_public_research)(config)
    insights=(insights_fn or fetch_read_only_insights)()
    external_rows=insights.get("records",[]) if insights.get("status")=="ok" else []
    persisted=load_learning(performance_path)
    known={(r.get("content_id"),str(r.get("captured_at_utc",""))[:10]) for r in persisted}
    new_records=0
    for row in external_rows:
        marker=(row.get("content_id"),str(row.get("captured_at_utc",""))[:10])
        if row.get("content_id") and row.get("category") and marker not in known:
            record_outcome(row,performance_path);known.add(marker);new_records+=1
    outcomes=load_learning(performance_path)
    candidates=score_ideas(research,outcomes)
    debate=build_debate(candidates,research,outcomes)
    llm=(llm_fn or _llm_review)(candidates,debate)
    category_comparison=[]
    for category in ("tarih","tarihi_gizem","az_bilinen_olay","kesif"):
        items=[c for c in candidates if c["category"]==category]
        category_comparison.append({"category":category,"idea_count":len(items),
            "mean_relative_index":round(sum(x["potential_index"] for x in items)/len(items),1) if items else None,
            "editorial_hypothesis":CATEGORY_HYPOTHESES[category]["reason"],
            "sample_size":len([r for r in outcomes if r.get("category")==category])})
    report={"coordinator":"AI Genel Yayın Yönetmeni","status":"recommendations_ready",
        "research":research,"learning":{"source":"Instagram Insights read-only" if external_rows else str(performance_path),
           "records_used":len(outcomes),"new_insights_records_saved":new_records,
           "insights_status":insights.get("status"),"real_metrics_available":bool(outcomes),
           "account_follower_change_metrics":insights.get("account_metrics",[]),
           "media_metric_coverage":{key:sum(1 for r in external_rows if r.get(key) is not None)
               for key in ("views","reach","avg_watch_seconds","shares","follows")},
           "account_follow_change_available":any(x.get("name")=="follows_and_unfollows" and x.get("values") for x in insights.get("account_metrics",[])),
           "account_metric_attribution":"account-level follower changes are not attributed to an individual Reel without a supported post-level metric"},
        "strategy":{"categories_compared":category_comparison,
            "ranking_method":"relative 0-100 editorial test index from category hypothesis, curiosity/visual/effort heuristic, direct public trend matches, monitored competitor-title coverage, and normalized own historical outcomes; not a probability"},
        "recommendations":candidates,"debate":debate,"coordinator_llm":llm,
        "decision":"İlk sıradaki fikri 1 küçük pilot olarak test et; bu rapor yayın kararı değildir.",
        "estimated_paid_cost_try":0,"human_approval_required":True,"instagram_publish_enabled":False,
        "paid_api_services_enabled":False}
    (out/"EDITORIAL_DECISION_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Haftalık Türk tarihi içerik karar raporu","","Koordinatör: AI Genel Yayın Yönetmeni",
        f"Araştırma: {research['evidence_counts']['trend_items']} trend öğesi; {research['evidence_counts']['competitor_videos']} rakip video başlığı; {len(outcomes)} performans kaydı.",
        "Potansiyel endeksi başarı olasılığı değildir. Trend ve rakip RSS verileri izlenme sayısı göstermez.","","## Kategori karşılaştırması"]
    for item in category_comparison:
        lines.append(f"- **{item['category']}**: fikir ortalaması {item['mean_relative_index']}/100; geçmiş örneklem {item['sample_size']}. Hipotez: {item['editorial_hypothesis']}.")
    lines += ["","## Öneriler"]
    for i,c in enumerate(candidates[:5],1):
        lines += [f"### {i}. {c['title']} — {c['potential_index']}/100 göreli endeks",
            f"Kategori: {c['category']}. Süre: yaklaşık {c['estimated_production_minutes']} dakika. Ücretli API/medya maliyeti: 0 TL (iş gücü ve yerel donanım hariç).",
            "Plan: "+json.dumps(c["production_plan"],ensure_ascii=False),
            "Gerekçe: "+" ".join(c["success_rationale"]),"Karşı görüş: "+c["risks"][0]]
    lines += ["","## Fikir değerlendirmesi"]
    for round_ in debate["rounds"]:
        lines += [f"- **{round_['idea']}**: "+"; ".join(f"{p['role']}: {p['position']} — {p['reason']}" for p in round_["positions"]),
                  "  Karşı sav: "+round_["counterpoint"]]
    lines += ["","## LLM ve güvenlik durumu",f"Gerçek LLM kullanıldı: {llm.get('actual_llm_used',False)} ({llm.get('calls',0)} çağrı).",
        "Bu öneriler taslaktır; yayın ve ücretli hizmetler kapalıdır. İnsan kaynak/tarih incelemesi gerekir."]
    (out/"EDITORIAL_DECISION_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return report

def main():
    parser=argparse.ArgumentParser(description="Ücretsiz RSS araştırması ve haftalık içerik karar raporu")
    parser.add_argument("--out",default="output/editorial");parser.add_argument("--performance",default="")
    args=parser.parse_args();report=run_board(args.out,performance_path=args.performance or None)
    print(json.dumps({"status":report["status"],"top_idea":report["recommendations"][0]["id"],
        "recommendations":len(report["recommendations"]),"research":report["research"]["evidence_counts"],
        "actual_llm_used":report["coordinator_llm"]["actual_llm_used"],"llm_calls":report["coordinator_llm"]["calls"],
        "report":str(Path(args.out)/"EDITORIAL_DECISION_REPORT.md")},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
