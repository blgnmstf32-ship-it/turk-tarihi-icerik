"""Compact routine terminal output and repeated notes while retaining their sources."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


# Only a bare, successful unittest record may be grouped.
PASS_LINE = re.compile(
    rb"^(test_[A-Za-z0-9_]+) \((?:[A-Za-z_][A-Za-z0-9_]*\.)+\1\) \.\.\. ok\r?\n$"
)
OK_FOOTER = re.compile(rb"(?m)^Ran [0-9]+ tests? in [0-9.]+s\r?\n\r?\nOK\r?\n?\Z")


def unittest_view(raw: bytes, exit_code: int) -> bytes:
    """Keep unsuccessful or incomplete logs byte-for-byte."""
    if exit_code or not OK_FOOTER.search(raw):
        return raw

    output = []
    pending = 0
    for line in raw.splitlines(keepends=True):
        if PASS_LINE.fullmatch(line) and not any(48 <= byte <= 57 for byte in line):
            pending += 1
            continue
        if pending:
            output.append(f"[{pending} passing unittest records grouped. See the full log.]\n".encode())
            pending = 0
        output.append(line)
    return b"".join(output)


def notes_view(paths: list[Path], *, deduplicate: bool = True) -> bytes:
    """Include every unique file body unchanged and cross-reference exact repeats."""
    sections = []
    seen = {}
    for number, path in enumerate(paths, start=1):
        body = path.read_bytes()
        reference = seen.setdefault(body, number)
        heading = f"\n=== {number}. {path.as_posix()} ===\n".encode()
        if deduplicate and reference != number:
            body = f"[Identical to section {reference}. Original file path above.]\n".encode()
        sections.append(heading + body)
    return b"".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    unittest_log = modes.add_parser("unittest")
    unittest_log.add_argument("path", type=Path)
    unittest_log.add_argument("--exit-code", required=True, type=int)
    notes = modes.add_parser("notes")
    notes.add_argument("paths", type=Path, nargs="+")
    notes.add_argument("--no-dedup", action="store_true")
    args = parser.parse_args()
    view = (unittest_view(args.path.read_bytes(), args.exit_code) if args.mode == "unittest"
            else notes_view(args.paths, deduplicate=not args.no_dedup))
    sys.stdout.buffer.write(view)


if __name__ == "__main__":
    main()
