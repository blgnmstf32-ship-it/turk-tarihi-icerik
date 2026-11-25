"""Real provider integration checks. Paid mode requires durable state and explicit opt-in."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from scripts.daily_editorial import write_json
from scripts.editorial_state import EditorialState
from scripts.gemini_editorial import GeminiReviewSession
from scripts.nano_banana import collect_batch, submit, MODEL
from scripts.provider_budget import Budget, image_quote

LEDGER_REF = "refs/heads/provider-cost-ledger"
DB_FILE = "provider-usage.sqlite3"
PROMPT = (
    "Vertical editorial illustration, aged maritime chart on a 16th-century cartographer's workbench, "
    "bronze dividers, ink and daylight, cinematic chiaroscuro, tactile parchment, subtly defocused Atlantic "
    "coastline impression, no letters, no labels, no portraits, no modern objects. This is an interpretive "
    "scene, not a facsimile or archive photo. Clear focal point in the central third."
)


class RemoteJournal:
    """Publish a Git CAS checkpoint before spending so runner loss cannot erase a reservation."""

    def __init__(self, path):
        self.path = path
        result = self.git("ls-remote", "--exit-code", "origin", LEDGER_REF, check=False)
        self.parent = None
        if result.returncode == 0:
            self.git("fetch", "--no-tags", "origin", LEDGER_REF)
            self.parent = self.git("rev-parse", "FETCH_HEAD").stdout.decode().strip()
            path.write_bytes(self.git("show", f"{self.parent}:{DB_FILE}").stdout)
        elif result.returncode != 2:
            raise RuntimeError("Uzak API bütçe geçmişi okunamadı.")

    @staticmethod
    def git(*args, data=None, check=True):
        result = subprocess.run(["git", *args], input=data, capture_output=True, timeout=45,
                                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        if check and result.returncode:
            raise RuntimeError(f"Uzak bütçe kaydı Git adımında durdu ({args[0]}).")
        return result

    def sync(self):
        blob = self.git("hash-object", "-w", str(self.path)).stdout.decode().strip()
        tree = self.git("mktree", data=f"100644 blob {blob}\t{DB_FILE}\n".encode()).stdout.decode().strip()
        commit = self.git(
            "-c", "user.name=github-actions", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit-tree", tree, *(["-p", self.parent] if self.parent else []),
            "-m", "Checkpoint reserved editorial API usage",
        ).stdout.decode().strip()
        # Explicit lease also rejects a concurrent creation of the previously absent branch.
        self.git("push", f"--force-with-lease={LEDGER_REF}:{self.parent or ''}", "origin", f"{commit}:{LEDGER_REF}")
        self.parent = commit


def free_checks(out):
    budget_path = out / "free-smoke-quota.sqlite3"
    sessions = GeminiReviewSession("", EditorialState(out / "free-smoke-content.sqlite3"), quota_path=budget_path)
    results = []
    for role in ("Genel Yayın Yönetmeni", "İçerik Stratejisti", "Senaryo Yazarı"):
        def validate(text):
            data = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
            return (data, None) if data.get("draft_only") == "evet" else (None, "unexpected_response")

        review = sessions.evaluate(role, 'Kısa JSON ver: {"draft_only":"evet"}.',
                                   {"subject": "tarih ve kişisel bakım için taslak editoryal inceleme"},
                                   validate, namespace="provider-smoke-v1", max_tokens=768)
        results.append({key: review.get(key) for key in
                        ("role", "status", "model", "provider", "response_source", "http_status", "attempts")})
    confirmed = sum(row["status"] == "proposal" and row["provider"] == "gemini" for row in results)
    report = {"status": "passed" if confirmed == 3 else "failed",
              "confirmed_models": confirmed, "live_gemini_calls": sessions.gemini_attempts,
              "openrouter_calls": 0, "notes": "Each model is checked without fallback.", "roles": results,
              "quota": sessions.budget.report()}
    write_json(out / "FREE_GEMINI_TEST.json", report)
    if confirmed != 3:
        raise RuntimeError("Üç ücretsiz Gemini/Gemma model doğrulamasından en az biri başarısız.")


def paid_check(out, mode, confirmed):
    state = RemoteJournal(out / "private-budget.sqlite3")
    budget = Budget(state.path)
    quote = image_quote(mode, 1)
    write_json(out / "NANO_BANANA_QUOTE.json", {"model": MODEL, "count": 1, "mode": mode,
               "reserved_usd": quote / 1_000_000, "image_only": True, "instagram_auto_publish": False})
    report = submit(budget, state.sync, "tarih", [PROMPT], out / "NANO_BANANA_SAMPLE.jpg",
                    mode=mode, confirmed=confirmed)
    write_json(out / "NANO_BANANA_TEST.json", report)
    if report["state"] == "submitted":
        for _ in range(10):
            time.sleep(35)
            result = collect_batch(budget, state.sync, report["id"], out, confirmed=confirmed)
            if result["state"] == "complete":
                report = {**report, **result}
                write_json(out / "NANO_BANANA_TEST.json", report)
                break
        else:
            raise RuntimeError("Nano Banana Batch bekliyor. Aynı iş yeniden satın alınmadan tekrar sorgulanabilir.")
    write_json(out / "NANO_BANANA_BUDGET.json", budget.report())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=("free", "paid"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("batch", "standard"), default="batch")
    parser.add_argument("--allow-one-paid-image", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        if args.check == "free":
            free_checks(args.out)
        else:
            if not args.allow_one_paid_image or os.getenv("GITHUB_REF_NAME") != "main":
                raise RuntimeError("Ücretli test main ve bir görsel için açık onay gerektirir.")
            paid_check(args.out, args.mode, args.allow_one_paid_image)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        write_json(args.out / "PROVIDER_FAILURE.json", {"status": "failed", "reason": str(exc)})
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
