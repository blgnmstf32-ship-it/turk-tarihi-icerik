"""Collect public trend, competition and research metadata with provenance."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from urllib.parse import quote
import xml.etree.ElementTree as ET

import requests

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
YOUTUBE = "{http://www.youtube.com/xml/schemas/2015}"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/videos"
CROSSREF = "https://api.crossref.org/works"
HEADERS = {"User-Agent": "TarihinBilinmeyenGercekleri/1.0"}


def get_rss(url, requester=None, timeout=8):
    response = (requester or requests.get)(url, timeout=timeout, headers=HEADERS)
    response.raise_for_status()
    return ET.fromstring(response.content)


def count(value):
    if isinstance(value, (str, int)) and str(value).isdigit():
        return int(value)
    return None


def discover_sources(queries, get, timeout, result):
    """Retrieve paper leads; metadata alone is never marked as historical verification."""
    for category, query in queries.items():
        try:
            response = get(CROSSREF, params={"query.bibliographic": query, "rows": 3,
                           "select": "title,DOI,publisher"}, timeout=timeout, headers=HEADERS)
            response.raise_for_status()
            for paper in response.json()["message"]["items"]:
                if paper.get("title") and paper.get("DOI"):
                    result["source_leads"].append({"category": category, "title": paper["title"][0],
                        "url": "https://doi.org/" + paper["DOI"], "publisher": paper.get("publisher"),
                        "verification": "metadata_only_open_before_use"})
        except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
            result["errors"].append({"source": f"Crossref/{category}", "error": type(exc).__name__})


def collect_public_research(config, requester=None):
    get = requester or requests.get
    timeout = int(config.get("research_timeout_seconds", 8))
    captured = datetime.now(timezone.utc).isoformat()
    result = {"collected_at_utc": captured, "method": "public RSS, public metrics, Crossref metadata",
              "trends": [], "competitors": [], "source_leads": [], "errors": []}
    try:
        root = get_rss(config["google_trends_rss"], get, timeout)
        for item in root.findall(".//item")[:30]:
            result["trends"].append({"title": (item.findtext("title") or "").strip(),
                "url": (item.findtext("link") or "").strip(), "source": "Google Trends RSS (Türkiye)"})
    except Exception as exc:
        result["errors"].append({"source": "Google Trends RSS", "error": type(exc).__name__})

    for channel in config.get("competitor_youtube_channels", []):
        channel_id = str(channel.get("channel_id", "")).strip()
        if not channel_id:
            continue
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={quote(channel_id)}"
        try:
            root = get_rss(url, get, timeout)
            videos = []
            for entry in root.findall(f"{ATOM}entry")[:20]:
                link = entry.find(f"{ATOM}link")
                rss_metrics = entry.find(f".//{MEDIA}statistics")
                views = count(rss_metrics.get("views")) if rss_metrics is not None else None
                videos.append({"title": (entry.findtext(f"{ATOM}title") or "").strip(),
                    "video_id": entry.findtext(f"{YOUTUBE}videoId"),
                    "url": link.get("href", "") if link is not None else "",
                    "published": entry.findtext(f"{ATOM}published"),
                    "views": views, "likes": None, "comments": None, "shares": None,
                    "metrics_source": url if views is not None else None,
                    "metrics_retrieved_at": captured if views is not None else None})
            result["competitors"].append({"name": channel.get("name", channel_id),
                "channel_url": f"https://www.youtube.com/channel/{channel_id}", "videos": videos})
        except Exception as exc:
            result["errors"].append({"source": channel.get("name", channel_id), "error": type(exc).__name__})

    videos = [v for channel in result["competitors"] for v in channel["videos"]]
    existing = {v["video_id"]: v for v in videos if v.get("video_id")}
    for snapshot in config.get("comparison_videos", []):
        video_id = snapshot["video_id"]
        url = f"https://www.youtube.com/watch?v={video_id}"
        video = existing.get(video_id)
        if video is None:
            video = {"video_id": video_id, "url": url, "title": snapshot["title"],
                "published": snapshot["published"], "views": None, "likes": None, "shares": None, "comments": None}
            videos.append(video)
            result["competitors"].append({"name": snapshot["name"], "videos": [video], "comparison_example": True})
        video["archived_public_metrics"] = {**{key: snapshot.get(key) for key in ("views", "likes", "comments", "shares")},
            "source": url, "retrieved_on": snapshot["retrieved_on"], "freshness": snapshot["freshness"]}
        existing[video_id] = video

    key = os.getenv("YOUTUBE_DATA_API_KEY")
    result["youtube_data_api_status"] = "missing_key" if not key else "no_video_ids"
    if key and existing:
        result["youtube_data_api_status"] = "queried"
        ids = list(existing)
        for start in range(0, len(ids), 50):
            try:
                res = get(YOUTUBE_API, params={"part": "statistics", "id": ",".join(ids[start:start+50]),
                          "key": key}, timeout=timeout, headers=HEADERS)
                res.raise_for_status()
                for item in res.json().get("items", []):
                    video = existing.get(item["id"])
                    if video is None:
                        continue
                    stats = item.get("statistics", {})
                    for field in ("views", "likes", "comments"):
                        value = count(stats.get({"views":"viewCount", "likes":"likeCount", "comments":"commentCount"}[field]))
                        if value is not None:
                            video[field] = value
                    video.update(metrics_source=YOUTUBE_API, metrics_retrieved_at=captured)
            except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
                result["youtube_data_api_status"] = "failed_or_partial"
                result["errors"].append({"source": "YouTube Data API", "error": type(exc).__name__})

    discover_sources(config.get("source_discovery_queries", {}), get, timeout, result)
    result["evidence_counts"] = {"trend_items": len(result["trends"]),
        "competitor_channels": len(result["competitors"]), "competitor_videos": len(videos)}
    result["metrics_coverage"] = {field: sum(v.get(field) is not None or
        v.get("archived_public_metrics", {}).get(field) is not None for v in videos)
        for field in ("views", "likes", "comments", "shares")}
    return result
