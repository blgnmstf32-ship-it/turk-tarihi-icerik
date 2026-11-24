"""Persist anonymized content outcomes and summarize what did/did not work."""
from __future__ import annotations
import argparse, json, statistics
from datetime import datetime, timezone
from pathlib import Path
from scripts.content_strategy import load_learning
from scripts.instagram_insights import fetch_read_only_insights

ROOT=Path(__file__).resolve().parents[1]

def benchmark(records):
    groups={}
    for row in records:
        if row.get("category"): groups.setdefault(row["category"],[]).append(row)
    result=[]
    for category, rows in sorted(groups.items()):
        views=[float(r["views"]) for r in rows if r.get("views") is not None]
        shares=[float(r["shares"])/max(1,float(r.get("reach") or r.get("views") or 0)) for r in rows if r.get("shares") is not None]
        watch=[float(r["avg_watch_seconds"]) for r in rows if r.get("avg_watch_seconds") is not None]
        follows=[float(r["follows"]) for r in rows if r.get("follows") is not None]
        result.append({"category":category,"sample_size":len(rows),"views_median":statistics.median(views) if views else None,
            "share_rate_median":statistics.median(shares) if shares else None,"avg_watch_seconds_median":statistics.median(watch) if watch else None,
            "follows_median":statistics.median(follows) if follows else None,
            "evidence_quality":"descriptive only; small samples are not predictive"})
    return result

def record_outcome(record,path=None):
    required=("content_id","category")
    if any(not record.get(k) for k in required): raise ValueError("content_id and category are required")
    target=Path(path or ROOT/"data/performance.jsonl")
    prior=load_learning(target)
    comparable=[float(r["views"]) for r in prior if r.get("category")==record["category"] and r.get("views") is not None]
    if len(comparable)<3:
        learning_outcome="insufficient_baseline"
    else:
        median=statistics.median(comparable)
        value=float(record.get("views") or record.get("reach") or 0)
        learning_outcome="above_category_median" if value>=median else "below_category_median"
    row={**record,"learning_outcome":learning_outcome,"recorded_at_utc":datetime.now(timezone.utc).isoformat()}
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    return row

def ingest_insights(path=None,insights_fn=None):
    result=(insights_fn or fetch_read_only_insights)()
    if result.get("status")!="ok": return {"status":result.get("status"),"records_added":0,"read_only":True}
    target=Path(path or ROOT/"data/performance.jsonl")
    known={(r.get("content_id"),str(r.get("captured_at_utc",""))[:10]) for r in load_learning(target)}
    count=0
    for row in result.get("records",[]):
        marker=(row.get("content_id"),str(row.get("captured_at_utc",""))[:10])
        if row.get("source") and row.get("category") and marker not in known:
            record_outcome(row,target);known.add(marker);count+=1
    return {"status":"ok","records_added":count,"read_only":True,"published":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--insights",action="store_true");p.add_argument("--file",default="");p.add_argument("--out",default="output/editorial")
    a=p.parse_args();path=Path(a.file) if a.file else ROOT/"data/performance.jsonl"
    if a.insights:ingest_insights(path)
    rows=load_learning(path);report={"records":len(rows),"categories":benchmark(rows),"source_file":str(path),"publication":False}
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/"PERFORMANCE_LEARNING.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
