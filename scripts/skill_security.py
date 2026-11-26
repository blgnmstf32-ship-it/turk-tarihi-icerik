"""Review tracked agent skills and committed secrets without running skill content."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


REPO = Path(__file__).resolve().parents[1]
BLOCKING = {"HIGH", "CRITICAL"}
CORE_ANALYZERS = {"static_analyzer", "bytecode", "pipeline", "correlation", "behavioral_analyzer"}
SHELL_PREFIX = r"(?:^|[;&|`])\s*(?:\$\s+)?(?:(?:sudo|command|exec)\s+)*"
COMMAND_RULES = {
    "SKILL_NETWORK_COMMAND": re.compile(
        SHELL_PREFIX + r"(?:curl|wget|ssh|scp|sftp|nc|ncat|netcat)\s+"
        r"(?=[^\n`]*\S)", re.IGNORECASE
    ),
    "SKILL_DESTRUCTIVE_COMMAND": re.compile(
        SHELL_PREFIX + r"rm\s+(?:-[A-Za-z]*[rR][A-Za-z]*\s|--recursive\s)"
        r"|\|\s*(?:ba|da|z)?sh\b", re.IGNORECASE
    ),
}
IGNORE_FILE = REPO / "config/gitleaks-history.ignore"


class ScanError(RuntimeError):
    """A scanner could not finish the requested check."""


def command_findings(path: Path) -> list[tuple[str, int]]:
    if path.suffix.lower() not in {".md", ".sh", ".bash", ".zsh"}:
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [(rule, number) for number, line in enumerate(lines, 1)
            for rule, pattern in COMMAND_RULES.items() if pattern.search(line)]


def clean_environment(scratch: Path) -> dict[str, str]:
    return {"PATH": "/usr/bin:/bin", "HOME": str(scratch), "TMPDIR": str(scratch),
            "LANG": "C.UTF-8", "NO_COLOR": "1", "DO_NOT_TRACK": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1"}


def run_tool(args: list, work: Path) -> int:
    try:
        return subprocess.run(args, cwd=work, env=clean_environment(work), stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=150, check=False).returncode
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise ScanError(f"{Path(args[0]).name} could not complete") from exc


def scan_report(path: Path, expected_type: type, tool: str):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, expected_type):
            raise ValueError("Unexpected scanner report type")
        return value
    except (OSError, ValueError) as exc:
        raise ScanError(f"{tool} did not produce a valid report") from exc


def cisco_scan(binary: Path, skill: Path, work: Path) -> list[dict]:
    report = work / "skills-report.json"
    report.unlink(missing_ok=True)
    code = run_tool([binary, "scan", skill, "--policy", "strict", "--use-behavioral",
                     "--fail-on-severity", "high", "--format", "json", "--output", report], work)
    if code not in {0, 1}:
        raise ScanError(f"Cisco scanner failed (exit {code})")
    data = scan_report(report, dict, "Cisco")
    findings = data.get("findings")
    if (not isinstance(findings, list) or data.get("analyzers_failed")
            or not CORE_ANALYZERS.issubset(data.get("analyzers_used", []))
            or code != int(any(f.get("severity") in BLOCKING for f in findings))):
        raise ScanError("Cisco scanner did not finish all requested analyzers")
    return findings


def secret_scan(binary: Path, mode: str, target: Path, work: Path, ignore_file: Path) -> list[dict]:
    config = work / "gitleaks.toml"
    config.write_text("[extend]\nuseDefault = true\n", encoding="utf-8")
    report = work / "secrets-report.json"
    report.unlink(missing_ok=True)
    args = [binary, mode, "--config", config, "--gitleaks-ignore-path", ignore_file,
            "--ignore-gitleaks-allow", "--no-banner", "--redact=100",
            "--report-format=json", "--report-path", report]
    if mode == "git":
        args.append("--log-opts=HEAD --no-ext-diff --no-textconv")
    code = run_tool([*args, target], work)
    if code not in {0, 1}:
        raise ScanError(f"Gitleaks scanner failed (exit {code})")
    findings = scan_report(report, list, "Gitleaks")
    if code != int(bool(findings)):
        raise ScanError("Gitleaks result did not match its exit status")
    return findings


def tracked_skills(repo: Path, target: Path):
    result = subprocess.run(["git", "-C", repo, "ls-files", "-z"], capture_output=True,
                            env=clean_environment(target), timeout=30, check=True)
    paths = [Path(name) for name in result.stdout.decode("utf-8").split("\0") if name]
    roots = sorted({path.parent for path in paths if path.name == "SKILL.md"})
    if not roots:
        raise ScanError("No tracked SKILL.md files were found")
    for root in roots:
        files = [path for path in paths if path.is_relative_to(root)]
        for path in files:
            source = repo / path
            if source.resolve() != source or not source.is_file():
                raise ScanError("A skill contains a symlink or a missing tracked file")
            destination = target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        yield root, files


def safe_label(value: object) -> str:
    return re.sub(r"[^-a-zA-Z0-9_./]", "?", str(value))[:150]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cisco", type=Path, required=True)
    parser.add_argument("--gitleaks", type=Path, required=True)
    args = parser.parse_args()
    failed = False
    try:
        with tempfile.TemporaryDirectory(prefix="skill-audit-") as folder:
            work = Path(folder)
            snapshot = work / "snapshot"
            for root, files in tracked_skills(REPO, snapshot):
                findings = cisco_scan(args.cisco.resolve(), snapshot / root, work)
                print(f"{safe_label(root)}: Cisco findings={len(findings)}")
                for finding in findings:
                    rule = safe_label(finding.get("rule_id"))
                    severity = safe_label(finding.get("severity"))
                    print(f"  {severity} {rule}")
                    failed |= severity in BLOCKING
                for path in files:
                    for rule, number in command_findings(snapshot / path):
                        print(f"  blocked {rule}: {safe_label(path)}:{number}")
                        failed = True

            leaks = secret_scan(args.gitleaks.resolve(), "git", REPO, work, IGNORE_FILE)
            print(f"Gitleaks: {len(leaks)} findings across history reachable from HEAD")
            for leak in leaks:
                print(f"  {safe_label(leak['RuleID'])}: {safe_label(leak['File'])}:"
                      f"{int(leak['StartLine'])} ({safe_label(leak['Commit'])[:12]})")
            failed |= bool(leaks)
    except (ScanError, subprocess.SubprocessError, UnicodeError) as exc:
        print(f"Security checks incomplete ({type(exc).__name__})")
        if isinstance(exc, ScanError):
            print(str(exc))
        return 2
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
