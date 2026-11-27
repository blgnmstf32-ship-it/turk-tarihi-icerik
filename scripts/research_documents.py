"""Find bounded evidence leads in an explicitly supplied, permitted HTML snapshot."""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from scripts.motion_toolkit import https_source

TOOL_ID = "research:trafilatura"
TRAFILATURA_VERSION = "2.4.0"
MAX_HTML_BYTES = 120_000
MAX_RECEIPT_BYTES = 240_000
MAX_EXCERPT_CHARS = 240


class ResearchInputError(ValueError):
    """Public reason codes. No snapshot fields are included in messages."""


def _normalize(text):
    return " ".join(text.split())


def _provenance(snapshot):
    if type(snapshot) is not dict:
        raise ResearchInputError("invalid_html_snapshot")
    html, url = snapshot.get("html"), snapshot.get("source_url")
    if (set(snapshot) - {"html", "source_url", "captured_on", "sha256", "analysis_permitted", "literal_excerpt"}
            or not isinstance(html, str) or not html.strip() or len(html.encode()) > MAX_HTML_BYTES):
        raise ResearchInputError("invalid_html_snapshot")
    if snapshot.get("analysis_permitted") is not True:
        raise ResearchInputError("missing_analysis_permission")
    if (not https_source(url) or any(ch.isspace() or ord(ch) < 32 for ch in url)
            or urlsplit(url).query or urlsplit(url).fragment):
        raise ResearchInputError("canonical_https_source_required")
    captured = snapshot.get("captured_on")
    if not isinstance(captured, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", captured):
        raise ResearchInputError("invalid_capture_date")
    try:
        capture_date = date.fromisoformat(captured)
    except ValueError:
        raise ResearchInputError("invalid_capture_date") from None
    digest = sha256(html.encode()).hexdigest()
    if snapshot.get("sha256") != digest:
        raise ResearchInputError("snapshot_hash_mismatch")
    return {"source_url": url, "captured_on": capture_date.isoformat(), "snapshot_sha256": digest}


def read_snapshot(snapshot):
    """Inspect only provided bytes. A text match never verifies an editorial claim."""
    provenance = _provenance(snapshot)
    literal = snapshot.get("literal_excerpt")
    if literal is not None and (not isinstance(literal, str) or not 12 <= len(_normalize(literal)) <= 160):
        raise ResearchInputError("invalid_literal_excerpt")
    try:
        installed = version("trafilatura")
    except PackageNotFoundError:
        raise ResearchInputError("optional_parser_missing") from None
    if installed != TRAFILATURA_VERSION:
        raise ResearchInputError("unreviewed_parser_version")
    try:
        from lxml import etree, html
        from trafilatura import extract
    except ImportError:
        raise ResearchInputError("optional_parser_missing") from None

    try:
        parse = html.HTMLParser(no_network=True, huge_tree=False, encoding="utf-8")
        tree = html.document_fromstring(snapshot["html"].encode(), parser=parse)
        body = extract(tree, fast=True, favor_precision=True, include_comments=False, include_tables=False,
                       include_links=False, include_images=False, with_metadata=False, output_format="txt")
    except (etree.LxmlError, ValueError):
        raise ResearchInputError("html_parse_failed") from None
    if not body:
        raise ResearchInputError("article_text_unavailable")

    lines = [row for raw in body.splitlines() if (row := _normalize(raw))]
    excerpts, match_status = [], "not_requested"
    if literal is not None:
        needle = _normalize(literal)
        for pos, line in enumerate(lines, 1):
            offset = line.find(needle)
            if offset >= 0:
                start = max(0, offset - 35)
                excerpts.append({"extracted_line": pos, "text": line[start:start + MAX_EXCERPT_CHARS]})
                break
        match_status = "literal_found" if excerpts else "literal_not_found"
    else:
        excerpts = [{"extracted_line": pos, "text": line[:MAX_EXCERPT_CHARS]}
                    for pos, line in enumerate(lines[:3], 1)]
    return {**provenance, "parser": f"trafilatura {installed}", "status": "human_source_review_required",
            "literal_status": match_status, "evidence_leads": excerpts, "content_is_untrusted": True,
            "claim_verified": False, "live_http": False, "external_api_calls": 0}


def main():
    from scripts.editorial_state import EditorialState
    from scripts.skill_router import RouteContext
    from scripts.tool_router import run_tool

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", choices=("tarih", "bakim"), required=True)
    parser.add_argument("--role", type=int, required=True)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    args = parser.parse_args()
    try:
        if not args.snapshot.is_file() or args.snapshot.is_symlink():
            raise ValueError
        with args.snapshot.open("rb") as handle:
            raw = handle.read(MAX_RECEIPT_BYTES + 1)
        if len(raw) > MAX_RECEIPT_BYTES:
            raise ValueError
        snapshot = json.loads(raw)
    except (OSError, ValueError, RecursionError):
        parser.error("Expected a bounded local UTF-8 JSON snapshot")
    report = run_tool(RouteContext(args.brand, args.role, "document-evidence"), topic={},
                      snapshots={TOOL_ID: snapshot}, state=EditorialState(args.state))
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] in {"success", "cache"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
