"""Verify the primary Workers Free route and report optional models separately."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from unittest.mock import patch

from scripts.cloudflare_editorial import FREE_NEURONS, GEMMA, GLM, LOCAL_NEURONS, QWEN, turkish_json_parser
from scripts.editorial_state import EditorialState
from scripts.gemini_editorial import GeminiReviewSession


CASES = (
    ("Alan Araştırmacısı", {
        "facts": ["Antikythera düzeneği parçalarında dişliler vardır.",
                  "Verilen kaynak bu parçaları açıklar; mucidi kesinleştirmez."],
        "instruction": "Dişli düzeneği için iki cümlelik kaynaklı araştırma özeti yaz. "
                       "Mucidin kesin olarak bilinmediğini ayrı bir sınır cümlesinde açıkla.",
    }),
    ("İçerik Stratejisti", {
        "facts": ["Tanıtım videosu temsili bir cilt katmanı şeması kullanır.",
                  "Şema klinik sonuç veya tedavi başarısı göstermez."],
        "instruction": "Cilt katmanları şeması için merak uyandıran bir Türkçe açılış ve kısa senaryo yaz. "
                       "Şemanın temsili olduğunu, tedavi sonucu göstermediğini sınırda belirt.",
    }),
)


INSTRUCTION = (
    'Verilen iki olgu dışında kaynak, tarih, sayı ve tedavi iddiası ekleme. '
    'Türkçe olarak şu alanları ver: {"hook":"...","text":"...","boundary":"...","fact_ids":[1,2]}. '
    'Hook 3–16 kelime olsun. Sınırı kısa ve açık bir olumsuz cümle ile ifade et.'
)


class GeminiQuotaFixture:
    status_code = 429
    headers = {"Retry-After": "60"}

    @staticmethod
    def json():
        return {"error": {"status": "RESOURCE_EXHAUSTED"}}


def checks_for(case_index, value):
    prose = " ".join(value[field] for field in ("hook", "text", "boundary")).lower()
    bound = value["boundary"].lower()
    return {
        "turkish_json_schema": True,
        "opening_is_concise": 3 <= len(value["hook"].split()) <= 16,
        "uses_supplied_fact": ("dişli" if case_index == 0 else "katman") in prose,
        "states_evidence_boundary": (("muci" in bound and any(w in bound for w in ("bilin", "kesin", "belir")))
                                      if case_index == 0 else ("temsil" in bound and "tedavi" in bound)),
        "adds_no_unsupported_numeric_detail": not bool(re.search(r"\d", prose)),
        "references_only_supplied_evidence": value["fact_ids"] == [1] or value["fact_ids"] == [1, 2],
    }


def parse_case(raw):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw)
    if (not isinstance(data, dict) or set(data) != {"hook", "text", "boundary", "fact_ids"}
            or not all(isinstance(data.get(field), str) and data[field].strip()
                       for field in ("hook", "text", "boundary"))
            or not isinstance(data["fact_ids"], list) or not data["fact_ids"]
            or not all(type(i) is int and i in {1, 2} for i in data["fact_ids"])):
        return None, "benchmark_invalid_schema"
    return data, None



def case_result(case_index, expected, result):
    answer = result.get("answer")
    checks = checks_for(case_index, answer) if answer else {}
    return {**result, "expected_model": expected, "quality_checks": checks,
            "quality_checks_passed": sum(checks.values()),
            "case_passed": (result.get("provider") == "cloudflare_workers_ai"
                            and result.get("model") == expected and result.get("response_source") == "live"
                            and bool(checks) and all(checks.values()))}

def run(state, quota_path, run_id):
    calls = []

    def fake_gemini(url, **_kwargs):
        if not url.startswith("https://generativelanguage.googleapis.com/"):
            raise AssertionError("Unexpected synthetic request destination.")
        calls.append(429)
        return GeminiQuotaFixture()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-gemini-benchmark-key",
                                "ENABLE_GEMINI_EDITORIAL": "1", "GEMINI_FREE_TIER_CONFIRMED": "1"}):
        router = GeminiReviewSession("", state, routed=True, quota_path=quota_path,
                                     requester=fake_gemini, brand="multi-llm-smoke", max_attempts=1)
        rows = []
        for i, (role, prompt) in enumerate(CASES):
            result = router.evaluate(role, INSTRUCTION, prompt, parse_case,
                                     namespace=f"multi-llm-smoke-v2:{run_id}", max_tokens=768)
            rows.append(case_result(i, GEMMA, result))
    cloud = router.cloudflare
    optional = []
    if cloud and cloud.plan_status == "verified_free":
        role, prompt = CASES[1]
        for model in (QWEN, GLM):
            answer, attempt = cloud.probe(model, INSTRUCTION, prompt, turkish_json_parser(parse_case), 768)
            optional.append(case_result(1, model, {
                "role": role, "model": model, "provider": "cloudflare_workers_ai",
                "status": attempt["status"], "answer": answer, "attempts": [attempt],
                "response_source": "live" if answer is not None else None,
            }))
    passed = calls == [429] and all(row["case_passed"] for row in rows)
    return {
        "status": "passed" if passed else "incomplete", "workers_free_check": cloud.plan_status if cloud else "credentials_missing",
        "workers_billing_http_status": cloud.plan_http if cloud else None,
        "cloudflare_billing_read_requests": cloud.plan_checks if cloud else 0,
        "simulated_gemini_responses": calls, "real_gemini_calls": 0,
        "real_cloudflare_model_calls": router.cloudflare_calls, "real_openrouter_calls": 0,
        "workers_daily_free_neurons": FREE_NEURONS, "software_daily_neuron_cap": LOCAL_NEURONS,
        "workers_usage": state.cloudflare_report(), "inference_usd": 0,
        "media_created": False, "instagram_published": False, "cases": rows,
        "optional_model_checks": optional,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    report = run(EditorialState(args.state), args.out / "simulated-gemini.sqlite3",
                 f"{os.getenv('GITHUB_RUN_ID', 'local')}:{os.getenv('GITHUB_RUN_ATTEMPT', '1')}")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "MULTI_LLM_SMOKE.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report["status"] != "passed":
        parser.exit(1, "Canlı metin doğrulaması eksik. MULTI_LLM_SMOKE.json dosyasını inceleyin.\n")


if __name__ == "__main__":
    main()
