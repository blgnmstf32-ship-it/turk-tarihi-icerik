"""Manual, text-only comparison of the three existing zero-price routes."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from time import perf_counter

from scripts.cloudflare_editorial import CloudflareEditorial, GEMMA, cloudflare_available, turkish_json_parser
from scripts.editorial_llm import MAX_REQUESTS_PER_RUN, FreeReviewSession
from scripts.editorial_state import EditorialState
from scripts.gemini_editorial import GeminiReviewSession, LITE, gemini_authorized
from scripts.multi_llm_smoke import CASES, INSTRUCTION, checks_for, parse_case

MAX_INFERENCE_CALLS = len(CASES)
MAX_TOKENS = 768
REQUIRE_JSON = INSTRUCTION + " Kod bloğu kullanmadan tek JSON nesnesi döndür."


def strict_parser(raw):
    try:
        json.loads(raw)
    except (TypeError, ValueError):
        return None, "invalid_json"
    return parse_case(raw)


def measure(evaluate):
    cases = []
    for index, (role, prompt) in enumerate(CASES):
        start = perf_counter()
        result = evaluate(role, prompt)
        elapsed = round((perf_counter() - start) * 1000)
        attempts = result["attempts"]
        live = result.get("response_source") == "live"
        answer = result.get("answer")
        checks = checks_for(index, answer) if answer else {}
        # Eligibility/cooldown records need not correspond to HTTP requests.
        network = [row for row in attempts if row.get("network_attempted", True)]
        cases.append({
            "fixture": ("history", "beauty")[index],
            "source": result.get("response_source"),
            "model": result.get("model"),
            "inference_attempts": len(network),
            "elapsed_ms": elapsed if network else None,
            "http_statuses": [row.get("http_status") for row in network],
            "attempt_statuses": [row["status"] for row in attempts],
            "usage": [{field: row[field] for field in
                       ("tokens", "input_tokens", "output_tokens", "completion_tokens",
                        "reserved_neurons", "actual_neurons") if field in row}
                      for row in network],
            "valid_turkish_json": bool(answer) if network or answer else None,
            "editorial_checks": checks,
            "live_pass": live and bool(checks) and all(checks.values()),
        })
    if all(row["live_pass"] for row in cases):
        status = "live_pass"
    elif any(row["inference_attempts"] for row in cases):
        status = "incomplete_live"
    elif any(row["source"] == "cache" for row in cases):
        status = "cached"
    else:
        status = "quota_or_route_blocked"
    return {"status": status, "cases": cases}


def skipped(reason):
    return {"status": reason, "cases": []}


def compare(state, quota_path, namespace):
    parser = turkish_json_parser(strict_parser)
    report = {}
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        report["gemini"] = skipped("credentials_missing")
    elif not gemini_authorized():
        report["gemini"] = skipped("free_project_unconfirmed")
    elif gemini_key == os.getenv("GEMINI_IMAGE_API_KEY", "").strip():
        report["gemini"] = skipped("matched_paid_image_key")
    else:
        session = GeminiReviewSession("", state, brand="free-provider-comparison",
                                      quota_path=quota_path, max_attempts=MAX_INFERENCE_CALLS)
        report["gemini"] = measure(lambda role, prompt: session.evaluate(
            role, REQUIRE_JSON, prompt, parser, namespace=namespace, max_tokens=MAX_TOKENS,
            primary_only=True, requested_model=LITE))
        report["gemini"]["inference_calls"] = session.gemini_attempts

    if not cloudflare_available():
        report["cloudflare_workers_ai"] = skipped("credentials_missing")
    else:
        cloud = CloudflareEditorial(state, "free-provider-comparison")
        if cloud.check_plan():
            def evaluate_cloud(_role, prompt):
                answer, attempt = cloud.probe(GEMMA, REQUIRE_JSON, prompt, parser, MAX_TOKENS)
                return {"answer": answer, "model": GEMMA, "attempts": [attempt],
                        "response_source": "live" if answer is not None else None}

            report["cloudflare_workers_ai"] = measure(evaluate_cloud)
        else:
            report["cloudflare_workers_ai"] = skipped(cloud.plan_status)
        report["cloudflare_workers_ai"].update(
            free_plan=cloud.plan_status, plan_http=cloud.plan_http, plan_reads=cloud.plan_checks,
            inference_calls=cloud.calls)

    router_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not router_key:
        report["openrouter_free"] = skipped("credentials_missing")
    else:
        router = FreeReviewSession(router_key, state)
        report["openrouter_free"] = measure(lambda role, prompt: router.evaluate(
            role, REQUIRE_JSON, prompt, parser, namespace, MAX_TOKENS,
            reserve_calls=MAX_REQUESTS_PER_RUN - MAX_INFERENCE_CALLS))
        report["openrouter_free"].update(inference_calls=router.calls, quota_http=router.quota_http)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--state", type=Path, required=True)
    cli.add_argument("--quota", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    now = datetime.now(timezone.utc)
    data = {
        "measured_at_utc": now.isoformat(),
        "per_provider_inference_call_limit": MAX_INFERENCE_CALLS,
        "test_input": "same two public Turkish text fixtures",
        "allowed_inference_price_usd": 0,
        "providers": compare(EditorialState(args.state), args.quota,
                             f"15e-compare-v1:{now.date()}"),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
