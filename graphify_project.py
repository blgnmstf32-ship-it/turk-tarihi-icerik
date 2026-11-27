"""Build and verify a local, commit-bound Graphify index of tracked application code."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import time

REPOSITORY = "blgnmstf32-ship-it/turk-tarihi-icerik"
VERSION = "0.9.121"
DIRECTORIES = {"scripts", "tests", "remotion", "media_pilot"}
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".mjs"}


def run(args, cwd, *, text=True):
    environment = {
        "PATH": os.environ["PATH"], "LANG": "C.UTF-8",
        "GRAPHIFY_BACKEND": "none", "GRAPHIFY_QUERY_LOG_DISABLE": "1",
        "TIKTOKEN_CACHE_DIR": os.environ.get("TIKTOKEN_CACHE_DIR", ""),
    }
    return subprocess.run(
        args, cwd=cwd, env=environment, check=True, capture_output=True, text=text, timeout=120,
    ).stdout


def source_files(root, commit):
    entries = run(["git", "ls-tree", "-rz", commit], root, text=False).split(b"\0")
    for entry in filter(None, entries):
        info, raw_path = entry.split(b"\t", 1)
        mode, kind, sha = info.split()
        path = PurePosixPath(os.fsdecode(raw_path))
        allowed = str(path) in {"voice_lab.py", "graphify_project.py", "graphify_benchmark.py"} or (
            path.parts[0] in DIRECTORIES and path.suffix in EXTENSIONS
        )
        if mode in {b"100644", b"100755"} and kind == b"blob" and allowed:
            yield path, sha.decode("ascii")


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def verify(root, directory, ref):
    manifest = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    commit = run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], root).strip()
    graph = directory / "graphify-out" / "graph.json"
    if (
        manifest["repository"] != REPOSITORY or manifest["source_sha"] != commit
        or manifest["graphify_version"] != VERSION or manifest["graph_sha256"] != digest(graph)
    ):
        raise ValueError("Graph repository, source commit, version, or checksum mismatch")
    return manifest


def build(root, directory, ref):
    if importlib.metadata.version("graphifyy") != VERSION:
        raise ValueError("Graphify version must match requirements-graphify.txt")
    if directory.exists():
        raise FileExistsError(f"Use a new output directory: {directory}")
    commit = run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], root).strip()
    inventory = list(source_files(root, commit))
    if not inventory:
        raise ValueError("No tracked application source files")
    if not directory.parent.is_dir():
        raise FileNotFoundError(f"Create the output parent first: {directory.parent}")
    with tempfile.TemporaryDirectory(prefix="graphify-stage-", dir=directory.parent) as work:
        prepared = Path(work)
        for path, blob in inventory:
            target = prepared / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(run(["git", "cat-file", "blob", blob], root, text=False))
            target.chmod(0o444)
        started = time.perf_counter()
        run([sys.executable, "-m", "graphify", "extract", ".", "--code-only"], prepared)
        elapsed = time.perf_counter() - started
        graph = prepared / "graphify-out" / "graph.json"
        result = json.loads(graph.read_text(encoding="utf-8"))
        nodes, edges = result["nodes"], result["links"]
        if not nodes or not edges:
            raise ValueError("Empty Graphify result")
        included = {str(path) for path, _ in inventory}
        for row in [*nodes, *edges]:
            filename = row.get("source_file")
            if filename and PurePosixPath(filename).as_posix() not in included:
                raise ValueError("Graph contains a reference outside the tracked source allowlist")
        manifest = {
            "repository": REPOSITORY, "source_sha": commit, "graphify_version": VERSION,
            "code_only": True, "api_requests": 0, "files": len(inventory),
            "nodes": len(nodes), "edges": len(edges), "graph_bytes": graph.stat().st_size,
            "graph_sha256": digest(graph), "extract_seconds": round(elapsed, 3),
        }
        staging = prepared / "deliverable"
        (staging / "graphify-out").mkdir(parents=True)
        graph.rename(staging / "graphify-out" / graph.name)
        (staging / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        staging.rename(directory)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify", "query"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--question")
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    if args.action == "build":
        result = build(root, out, args.ref)
    else:
        result = verify(root, out, args.ref)
        if args.action == "query":
            if importlib.metadata.version("graphifyy") != VERSION:
                parser.error("Installed Graphify version differs from the verified index")
            if not args.question or args.question.startswith("-"):
                parser.error("--question is required for query")
            argv = [sys.executable, "-m", "graphify", "query", args.question, "--budget", "500", "--depth", "1"]
            print(run(argv, out), end="")
            return
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
