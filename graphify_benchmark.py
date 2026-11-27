"""Measure Graphify navigation against full-file reads and targeted Git search."""
from collections import Counter
import json
import re
from pathlib import Path
import statistics
import sys
import time

import tiktoken

from graphify_project import run, verify

CASES = {
    "scene_director": ("scripts/scene_director.py", ("build_plan", "preflight")),
    "quality_lab": ("scripts/video_quality_lab.py", ("collect_ffmpeg", "evaluate")),
    "tool_router": ("scripts/tool_router.py", ("run_tool",)),
    "registry": ("scripts/skill_registry.py", ("registry_view",)),
    "media_qa": ("scripts/pilot_scene_repair.py", ("repair_targets", "scene_scope")),
}


def timed(operation):
    samples = []
    for _ in range(3):
        start = time.perf_counter_ns()
        output = operation()
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    return output, round(statistics.median(samples), 3)


def score(case, graph_dir, root, commit, count_tokens):
    keyword, (file, symbols) = case
    pattern = r"^((async )?def|class) (" + "|".join(symbols) + r")\b"
    paths = [root / file]
    baseline, read_ms = timed(lambda: "".join(path.read_text(encoding="utf-8") for path in paths))
    targeted, target_ms = timed(lambda: run(["git", "grep", "-n", "-E", pattern, commit, "--", file], root))
    if len(targeted.splitlines()) != len(symbols):
        raise ValueError(f"Benchmark baseline drift: {file}")
    exact = {match[1]: int(line.split(":")[2]) for line in targeted.splitlines()
             if (match := re.search(r"\b(?:def|class) (\w+)", line))}
    argv = [sys.executable, "-m", "graphify", "query", " ".join((*symbols, keyword)),
            "--depth", "1", "--budget", "500"]
    graph, graph_ms = timed(lambda: run(argv, graph_dir))
    matches = sum(bool(re.search(
        rf"^NODE {re.escape(name)}\(\)\s+\[src={re.escape(file)} loc=L{line}\b", graph, re.M
    )) for name, line in exact.items())
    return {
        "question": keyword, "expected_anchors": len(exact), "full_source_anchors": len(exact),
        "targeted_search_anchors": len(exact), "graph_anchors": matches,
        "full_source_tokens": count_tokens(baseline), "targeted_search_tokens": count_tokens(targeted),
        "graph_tokens": count_tokens(graph), "full_source_ms": read_ms,
        "targeted_search_ms": target_ms, "graph_query_ms": graph_ms,
    }


def main():
    root, graph_dir = (Path(arg).resolve() for arg in sys.argv[1:])
    evidence = verify(root, graph_dir, "HEAD")
    tokenizer = tiktoken.get_encoding("o200k_base")
    rows = [score(case, graph_dir, root, evidence["source_sha"],
                  lambda value: len(tokenizer.encode(value, disallowed_special=()))) for case in CASES.items()]
    totals = Counter()
    for row in rows:
        totals.update({key: val for key, val in row.items() if isinstance(val, (int, float))})
    print(json.dumps({
        "graph": evidence, "tokenizer": "tiktoken 0.14.0 o200k_base",
        "metric": "navigation anchors with exact source path and line",
        "timing": "median milliseconds per query over three fresh invocations",
        "totals": dict(totals), "cases": rows,
    }, indent=2))
    if totals["graph_anchors"] != totals["expected_anchors"]:
        raise SystemExit("Graphify missed one or more expected source anchors")


if __name__ == "__main__":
    main()
