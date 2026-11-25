"""Read-only Instagram Insights connector. Disabled unless settings and env opt in."""
import json, os
from pathlib import Path
import requests

def normalize_media_insights(payload, metadata):
    metrics={item.get("name"):item.get("values",[{}])[0].get("value") for item in payload.get("data",[])}
    def number(value):
        try:return float(value) if value is not None else None
        except (ValueError,TypeError):return None
    return {"source":"instagram_graph_api_read_only","content_id":metadata.get("content_id",metadata.get("media_id")),
        "topic_id":metadata.get("topic_id"),"category":metadata.get("category"),
        "published_at":metadata.get("published_at"),"format":metadata.get("format"),"views":number(metrics.get("views")),
        "reach":number(metrics.get("reach")),"shares":number(metrics.get("shares")),
        "avg_watch_seconds":number(metrics.get("ig_reels_avg_watch_time")),"follows":number(metrics.get("follows")),
        "captured_at_utc":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "metrics_missing":[k for k in ("views","reach","shares","ig_reels_avg_watch_time","follows") if metrics.get(k) is None]}

def fetch_read_only_insights(requester=None,settings=None):
    settings=settings or json.loads((Path(__file__).resolve().parents[1]/"config/settings.json").read_text(encoding="utf-8"))
    token=os.getenv("IG_INSIGHTS_ACCESS_TOKEN","")
    api_version=os.getenv("META_GRAPH_API_VERSION","v27.0")
    raw_map=os.getenv("INSTAGRAM_MEDIA_MAP","[]")
    if not settings.get("instagram_insights_enabled",False) or os.getenv("INSTAGRAM_INSIGHTS_ENABLED")!="1" or not token:
        return {"status":"disabled","read_only":True,"published":False,"records":[]}
    if not api_version.startswith("v") or not api_version[1:].replace(".","").isdigit():
        return {"status":"invalid_api_version","read_only":True,"published":False,"records":[]}
    try: media_map=json.loads(raw_map)
    except json.JSONDecodeError: return {"status":"invalid_media_map","read_only":True,"published":False,"records":[]}
    if not isinstance(media_map,list): return {"status":"invalid_media_map","read_only":True,"published":False,"records":[]}
    get=requester or requests.get
    rows=[];account_metrics=[]
    account_id=os.getenv("IG_INSIGHTS_ACCOUNT_ID","").strip()
    if account_id:
        try:
            response=get(f"https://graph.facebook.com/{api_version}/{account_id}/insights",timeout=15,
                params={"metric":"follows_and_unfollows,follower_count","period":"day","access_token":token})
            response.raise_for_status()
            for item in response.json().get("data",[]):
                account_metrics.append({"name":item.get("name"),"values":[{"end_time":v.get("end_time"),"value":v.get("value")} for v in item.get("values",[])]})
        except Exception as exc:
            account_metrics.append({"status":"fetch_failed","error_type":type(exc).__name__})
    for item in media_map:
        media_id=str(item.get("media_id","")).strip()
        if not media_id: continue
        try:
            response=get(f"https://graph.facebook.com/{api_version}/{media_id}/insights",timeout=15,
                params={"metric":"views,reach,shares,ig_reels_avg_watch_time","period":"lifetime","access_token":token})
            response.raise_for_status(); rows.append(normalize_media_insights(response.json(),item))
        except Exception as exc:
            # Never propagate the request URL/exception text because it may contain credentials.
            rows.append({"content_id":item.get("content_id",media_id),"topic_id":item.get("topic_id"),
                "category":item.get("category"),"status":"fetch_failed","error_type":type(exc).__name__})
    return {"status":"ok" if (rows and any(r.get("source") for r in rows)) or account_metrics else "no_media_records",
        "read_only":True,"published":False,"records":rows,"account_metrics":account_metrics,"api_version":api_version}

def get_insights(*args,**kwargs):
    return fetch_read_only_insights(*args,**kwargs)
