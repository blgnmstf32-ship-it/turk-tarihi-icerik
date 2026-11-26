"""Read-only Instagram Insights connector. Disabled unless settings and env opt in."""
import json, os
from datetime import datetime, timezone
from pathlib import Path
import requests

def normalize_media_insights(payload, metadata):
    metrics = {}
    for item in payload.get("data", []):
        values = item.get("values") or []
        value = values[0].get("value") if values else (item.get("total_value") or {}).get("value")
        metrics[item.get("name")] = value

    def number(name):
        value = metrics.get(name)
        try:
            result = float(value) if value is not None and not isinstance(value, bool) else None
        except (ValueError, TypeError, OverflowError):
            return None
        return result if result is not None and 0 <= result < float("inf") else None

    watch = number("ig_reels_avg_watch_time")
    unit = metadata.get("avg_watch_time_unit")
    unit = unit if isinstance(unit, str) else None
    factors = {"milliseconds": 1000, "seconds": 1}
    verified_watch = watch / factors[unit] if watch is not None and unit in factors else None
    return {
        "source": "instagram_graph_api_read_only",
        "content_id": metadata.get("content_id", metadata.get("media_id")),
        **{key: metadata.get(key) for key in ("topic_id", "category", "brand", "format", "published_at",
                                               "duration_seconds", "hook_family", "scenario")},
        "views": number("views"), "reach": number("reach"), "shares": number("shares"),
        "saves": number("saved"), "follows": number("follows"),
        "avg_watch_seconds": verified_watch if verified_watch is not None else watch,
        "verified_avg_watch_seconds": verified_watch, "avg_watch_time_unit": unit,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "metrics_missing": [key for key in ("views", "reach", "shares", "saved", "ig_reels_avg_watch_time", "follows")
                            if number(key) is None],
    }

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
                params={"metric":"views,reach,shares,saved,ig_reels_avg_watch_time","period":"lifetime","access_token":token})
            response.raise_for_status(); rows.append(normalize_media_insights(response.json(),item))
        except Exception as exc:
            # Never propagate the request URL/exception text because it may contain credentials.
            rows.append({"content_id":item.get("content_id",media_id),"topic_id":item.get("topic_id"),
                "category":item.get("category"),"status":"fetch_failed","error_type":type(exc).__name__})
    return {"status":"ok" if (rows and any(r.get("source") for r in rows)) or account_metrics else "no_media_records",
        "read_only":True,"published":False,"records":rows,"account_metrics":account_metrics,"api_version":api_version}

def get_insights(*args,**kwargs):
    return fetch_read_only_insights(*args,**kwargs)
