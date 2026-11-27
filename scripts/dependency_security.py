"""Audit declared Python dependencies and repository workflow permissions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from packaging.requirements import Requirement
import yaml


ROOT = Path(__file__).resolve().parents[1]
EARSHOT = "earshot @ git+https://github.com/Leonxlnx/earshot.git@7a7f7c5c70d4a763a1eca4b3666af7c77e313f97"
# Metadata of the reviewed revision. Audit its PyPI dependencies without building Git code.
EARSHOT_REQUIREMENTS = ("numpy>=1.26", "scipy>=1.11", "soundfile>=0.12", "soxr>=0.3", "numba>=0.58")
WRITE_JOBS = {
    ("apply_editorial_recovery.yml", "recover"): (
        {"push": {"branches": ["editorial-recovery"], "paths": [".github/workflows/apply_editorial_recovery.yml"]}},
        "github.ref == 'refs/heads/editorial-recovery'",
    ),
    ("daily.yml", "track"): (
        {"workflow_dispatch"},
        "github.ref == 'refs/heads/main' && inputs.demo != true",
    ),
}
# Additional wheel currently installed inline by media_final_qa.yml.
INLINE_REQUIREMENTS = ("psutil==7.2.2",)
HASH = re.compile(r"\s+--hash=sha256:[a-f0-9]{64}$")


def permissions_findings(name: str, workflow: dict) -> list[str]:
    findings = []
    triggers = workflow.get("on", {})
    events = {triggers} if isinstance(triggers, str) else set(triggers)
    if events & {"pull_request_target", "workflow_run"}:
        findings.append(f"{name}: privileged trigger requires review")
    permissions = workflow.get("permissions")
    if not isinstance(permissions, dict) or set(permissions.values()) - {"read", "none"}:
        findings.append(f"{name}: declare read-only workflow token permissions")
    for job_id, job in workflow["jobs"].items():
        context = f"{name}/{job_id}"
        if job.get("secrets") == "inherit":
            findings.append(f"{context}: pass named reusable-workflow secrets")
        if "permissions" not in job:
            continue
        job_permissions = job["permissions"]
        if isinstance(job_permissions, dict) and not set(job_permissions.values()) - {"read", "none"}:
            continue
        allowed = WRITE_JOBS.get((name, job_id))
        if allowed:
            scope, guard = allowed
            if job_permissions == {"contents": "write"} and (scope == triggers or scope == events) and job.get("if") == guard:
                continue
        findings.append(f"{context}: unexpected write permission or trigger scope")
    if name == "dependency_security.yml" and re.search(r"\bsecrets\s*[.\[]", json.dumps(workflow), re.I):
        findings.append(f"{name}: dependency audit must not reference repository secrets")
    return findings


def check_workflows() -> int:
    paths = sorted(p for p in (ROOT / ".github/workflows").iterdir() if p.suffix in {".yml", ".yaml"})
    if not paths:
        raise RuntimeError("No GitHub workflows found")
    findings = []
    for path in paths:
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        findings.extend(permissions_findings(path.name, workflow))
    for finding in findings:
        print(finding)
    print(f"Workflow permissions: {len(paths)} files, {len(findings)} findings")
    return int(bool(findings))


def requirement_lines(path: Path, *, allow_earshot=False):
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.partition("#")[0].strip()
        if not line or line == "-r requirements.txt":
            continue
        if allow_earshot and line == EARSHOT:
            yield from EARSHOT_REQUIREMENTS
            continue
        requirement = Requirement(HASH.sub("", line))
        if requirement.url:
            raise ValueError(f"Unexpected direct dependency in {path.name}")
        yield str(requirement)


def run_audit(pinned: Path) -> int:
    return subprocess.run([sys.executable, "-m", "pip_audit", "--disable-pip", "--no-deps",
                           "--strict", "--progress-spinner", "off", "--timeout", "25",
                           "-r", pinned], check=False).returncode


def check_python() -> int:
    with tempfile.TemporaryDirectory(prefix="dependency-audit-") as tmp:
        work = Path(tmp)
        lock_files = ("requirements-skill-security.txt", "requirements-dependency-audit.txt",
                      "requirements-research-documents.txt")
        runtime_paths = sorted(p for p in ROOT.glob("requirements*.txt") if p.name not in lock_files)
        if not runtime_paths:
            raise RuntimeError("No Python application requirements were found")
        inputs = work / "runtime.txt"
        requirements = list(INLINE_REQUIREMENTS)
        for path in runtime_paths:
            requirements.extend(requirement_lines(path, allow_earshot=path.name == "requirements-media-pilot.txt"))
        inputs.write_text("\n".join(dict.fromkeys(requirements)) + "\n", encoding="utf-8")
        report = work / "resolution.json"
        print("Resolve wheel metadata: " + ", ".join(p.name for p in runtime_paths), flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--dry-run", "--ignore-installed",
                        "--only-binary=:all:", "--disable-pip-version-check", "--quiet",
                        "--index-url", "https://pypi.org/simple", "--report", report, "-r", inputs], check=True)
        lock = work / "resolved.txt"
        resolved = json.loads(report.read_text(encoding="utf-8"))["install"]
        if not resolved:
            raise RuntimeError("Python application dependency resolution returned no packages")
        lock.write_text("".join(f"{p['metadata']['name']}=={p['metadata']['version']}\n" for p in resolved),
                        encoding="utf-8")
        status = 0
        for source in (lock, *(ROOT / filename for filename in lock_files)):
            print(f"pip-audit: {source.name}", flush=True)
            audit_input = work / "audit-input.txt"
            audit_input.write_text("\n".join(requirement_lines(source)) + "\n", encoding="utf-8")
            status |= run_audit(audit_input)
        return status


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("check", choices=("python", "workflows"))
    raise SystemExit(check_python() if cli.parse_args().check == "python" else check_workflows())
