"""Local-only structured production and feedback log with secret redaction."""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path

_SECRET = re.compile(r"(?i)(token|api[_-]?key|authorization|password|secret)(\s*[=:]\s*)([^\s,;]+)")
_SENSITIVE_NAME = re.compile(r"(?i)(token|api[_-]?key|authorization|password|secret)")

def _scrub(value):
    if isinstance(value, dict):
        return {str(k): ("[REDACTED]" if _SENSITIVE_NAME.search(str(k)) else _scrub(v)) for k,v in value.items()}
    if isinstance(value, list): return [_scrub(v) for v in value]
    if isinstance(value, str): return _SECRET.sub(r"\1\2[REDACTED]", value)[:4000]
    if value is None or isinstance(value,(bool,int,float)): return value
    return str(value)[:4000]

def record(event, details=None, path="output/observer/events.jsonl"):
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    row={"at":datetime.now(timezone.utc).isoformat(),"event":str(event)[:100],"details":_scrub(details or {})}
    with target.open("a",encoding="utf-8") as stream: stream.write(json.dumps(row,ensure_ascii=False)+"\n")
    return row

def feedback(message, rating=None, path="output/observer/feedback.jsonl"):
    return record("human_feedback",{"message":message,"rating":rating},path)
