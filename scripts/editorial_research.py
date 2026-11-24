"""Free, public RSS research. No search API, account login, or paid provider."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote
import requests

ATOM = "{http://www.w3.org/2005/Atom}"

def get_rss(url, requester=None, timeout=8):
    response=(requester or requests.get)(url,timeout=timeout,headers={"User-Agent":"TurkTarihiEditorialResearch/1.0"})
    response.raise_for_status()
    return ET.fromstring(response.content)

def collect_public_research(config, requester=None):
    """Return dated trend and competitor observations with source URLs/errors."""
    timeout=int(config.get("research_timeout_seconds",8))
    result={"collected_at_utc":datetime.now(timezone.utc).isoformat(),"method":"public RSS; no API key",
            "trends":[],"competitors":[],"errors":[]}
    try:
        root=get_rss(config["google_trends_rss"],requester,timeout)
        for item in root.findall(".//item")[:30]:
            result["trends"].append({"title":(item.findtext("title") or "").strip(),
                "url":(item.findtext("link") or "").strip(),"source":"Google Trends RSS (Türkiye)"})
    except Exception as exc:
        result["errors"].append({"source":"Google Trends RSS","error":type(exc).__name__})
    for channel in config.get("competitor_youtube_channels",[]):
        channel_id=str(channel.get("channel_id","")).strip()
        if not channel_id: continue
        url=f"https://www.youtube.com/feeds/videos.xml?channel_id={quote(channel_id)}"
        try:
            root=get_rss(url,requester,timeout)
            videos=[]
            for entry in root.findall(f"{ATOM}entry")[:20]:
                videos.append({"title":(entry.findtext(f"{ATOM}title") or "").strip(),
                    "url":(entry.find(f"{ATOM}link").get("href","") if entry.find(f"{ATOM}link") is not None else ""),
                    "published":(entry.findtext(f"{ATOM}published") or "")})
            result["competitors"].append({"name":channel.get("name",channel_id),"channel_url":f"https://www.youtube.com/channel/{channel_id}","videos":videos})
        except Exception as exc:
            result["errors"].append({"source":channel.get("name",channel_id),"error":type(exc).__name__})
    result["evidence_counts"]={"trend_items":len(result["trends"]),"competitor_channels":len(result["competitors"]),
        "competitor_videos":sum(len(c["videos"]) for c in result["competitors"])}
    return result
