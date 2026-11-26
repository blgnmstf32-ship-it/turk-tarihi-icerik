"""Free-only Workers AI transport for Turkish editorial text."""
from __future__ import annotations

import json
import math
import os
import re
import time

import requests

BASE = "https://api.cloudflare.com/client/v4/accounts"
GEMMA = "@cf/google/gemma-4-26b-a4b-it"
GLM = "@cf/zai-org/glm-4.7-flash"
GPT_OSS = "@cf/openai/gpt-oss-20b"
PRODUCTION_MODELS = (GEMMA, GPT_OSS)
READ_TIMEOUTS = {GEMMA: 38, GPT_OSS: 20, GLM: 20}
MODEL_COOLDOWN = 60
# Documented neurons per million input/output tokens (rounded up for GLM).
RATES = {GEMMA: (9091, 27273), GPT_OSS: (18182, 27273), GLM: (5500, 36400)}
FREE_NEURONS = 10_000
LOCAL_NEURONS = 9_000
MAX_RUN_CALLS = 8
MAX_OUTPUT = 4096
TURKISH_WORDS = frozenset(
    "ancak ayrıca başlık belirsiz bilgi bu bölüm bir bile böyle bazı bulundu bulunur da daha de değil "
    "diye dönem elde en göre için ile ilgili incele kalan kaynak kez kısa kesin konu mı mi neden nasıl "
    "olan olarak olabilir olmadan önce örneğin plan sonra soru tarih tek Türkçe uygun uzak var vardır ve "
    "veya veri yerine yeni yine yok yüzyıl".lower().split()
)


def cloudflare_available():
    return (os.getenv("ENABLE_CLOUDFLARE_EDITORIAL", "1") == "1"
            and bool(os.getenv("CLOUDFLARE_API_TOKEN", "").strip())
            and bool(re.fullmatch(r"[0-9a-fA-F]{32}", os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip())))


def redact_text(value):
    from scripts.editorial_llm import _redact

    for name in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        value = _redact(value, os.getenv(name, "").strip())
    return value


def turkish_json_parser(parser):
    """Check prose language before the role-specific schema and source validator."""
    def validate(content):
        content = redact_text(content)
        try:
            stripped = content.strip()
            if stripped.startswith("```"):
                stripped = re.sub(r"^\x60{3}(?:json)?\s*|\s*\x60{3}$", "", stripped, flags=re.I)
            decoded = json.loads(stripped)
        except (ValueError, TypeError):
            return None, "invalid_json"
        if not isinstance(decoded, dict):
            return None, "invalid_schema"

        def prose(value):
            if isinstance(value, dict):
                for sub in value.values():
                    yield from prose(sub)
            elif isinstance(value, list):
                for sub in value:
                    yield from prose(sub)
            elif isinstance(value, str) and len(value.split()) >= 4:
                yield value

        text = " ".join(prose(decoded)).lower()
        words = set(re.findall(r"[^\W\d_]+", text))
        if (not words or (len(words & TURKISH_WORDS) < 2
                          and len(re.findall(r"[çğıöşü]", text)) < 3)):
            return None, "turkish_prose_not_confirmed"
        return parser(content)
    return validate


def neurons(model, inputs, outputs):
    inp, out = RATES[model]
    return math.ceil((inp * inputs + out * outputs) / 1_000_000)


def _free_subscriptions(data):
    """Refuse incomplete billing responses and Workers/AI subscriptions with ambiguous cost."""
    rows = data.get("result")
    if data.get("success") is not True or not isinstance(rows, list):
        return False
    info = data.get("result_info") or {}
    total = info.get("total_count", len(rows))
    if type(total) is not int or total != len(rows):
        return False
    for row in rows:
        plan = row.get("rate_plan") or {}
        identity = " ".join(str(plan.get(name, "")).lower() for name in ("id", "public_name", "scope"))
        if (not plan.get("id") or plan.get("is_contract") or plan.get("externally_managed")
                or row.get("state") in {"Paid", "AwaitingPayment", "Trial"}
                or type(row.get("price")) not in {int, float} or row["price"] != 0
                or (re.search(r"worker|gateway|ai[ _-]?(usage|paid|inference)", identity)
                    and (not re.search(r"\bfree\b", identity.replace("_", " ").replace("-", " "))
                         or "paid" in identity))):
            return False
    return True


class CloudflareEditorial:
    def __init__(self, state, brand, *, requester=None, reader=None):
        self.state = state
        self.brand = brand
        self.account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        self.headers = {"Authorization": "Bearer " + os.getenv("CLOUDFLARE_API_TOKEN", "").strip()}
        self.request = requester or requests.post
        self.read = reader or requests.get
        self.calls = self.plan_checks = 0
        self.plan_status = self.plan_http = None
        self.stopped = False
        self.cooldown_until = {}

    def check_plan(self):
        if self.plan_status is None:
            self.plan_checks += 1
            try:
                response = self.read(f"{BASE}/{self.account}/subscriptions",
                                     headers=self.headers, timeout=(5, 12), allow_redirects=False)
                self.plan_http = response.status_code
                self.plan_status = ("verified_free" if self.plan_http == 200 and _free_subscriptions(response.json())
                                    else "free_plan_unverified")
            except (requests.RequestException, ValueError, AttributeError, TypeError):
                self.plan_status = "free_plan_unverified"
        return self.plan_status == "verified_free"

    def evaluate(self, instruction, prompt, parse_answer, max_tokens, reserve_calls):
        attempts = []
        for model in PRODUCTION_MODELS:
            answer, attempt = self.probe(model, instruction, prompt, parse_answer, max_tokens, reserve_calls)
            attempts.append(attempt)
            if answer is not None or self.stopped or attempt["status"] in {
                "cloudflare_unavailable", "free_plan_unverified", "cloudflare_run_limit",
                "cloudflare_daily_limit", "cloudflare_input_limit",
            }:
                return answer, attempts
        return None, attempts

    def probe(self, model, instruction, prompt, parse_answer, max_tokens, reserve_calls=0):
        attempt = {"provider": "cloudflare_workers_ai", "model": model, "http_status": None,
                   "actual_llm_used": False, "network_attempted": False}
        if not cloudflare_available() or model not in RATES or self.stopped:
            return None, {**attempt, "status": "cloudflare_unavailable"}
        if not self.check_plan():
            return None, {**attempt, "status": self.plan_status, "billing_http_status": self.plan_http}
        if self.calls >= MAX_RUN_CALLS - reserve_calls:
            return None, {**attempt, "status": "cloudflare_run_limit"}
        if self.cooldown_until.get(model, 0) > time.monotonic():
            return None, {**attempt, "status": "cloudflare_model_cooldown"}
        max_tokens = min(max_tokens, MAX_OUTPUT)
        messages = [
            {"role": "system", "content": instruction + " Araç çağırma. Şemaya uyan tek Türkçe JSON nesnesi döndür."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, sort_keys=True)},
        ]
        messages = redact_text(messages)
        size = len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) + 256
        if size > 60_000 or max_tokens < 1:
            return None, {**attempt, "status": "cloudflare_input_limit"}
        reserved = neurons(model, size, max_tokens)
        uid = self.state.reserve_cloudflare(self.brand, model, reserved, LOCAL_NEURONS)
        if uid is None:
            return None, {**attempt, "status": "cloudflare_daily_limit"}
        payload = {"model": model, "messages": messages, "max_completion_tokens": max_tokens,
                   "temperature": 0.35, "stream": False, "store": False,
                   "options": {"rejectIfBusy": True}, "chat_template_kwargs": {"enable_thinking": False}}
        if model == GPT_OSS:
            payload.pop("chat_template_kwargs")
            payload["reasoning_effort"] = "low"
        started = time.monotonic()
        actual = None
        self.calls += 1
        attempt.update(network_attempted=True, reserved_neurons=reserved, paid_usd=0)
        try:
            response = self.request(f"{BASE}/{self.account}/ai/v1/chat/completions", headers=self.headers,
                                    json=payload, timeout=(6, READ_TIMEOUTS[model]), allow_redirects=False)
            attempt["http_status"] = response.status_code
            if response.status_code != 200:
                if response.status_code in {401, 402}:
                    self.stopped = True
                attempt["status"] = f"cloudflare_http_{response.status_code}"
                return None, attempt
            data = response.json()
            reported_model = data.get("model")
            if reported_model is not None and reported_model != model:
                attempt["status"] = "cloudflare_unexpected_model"
                return None, attempt
            usage = data.get("usage") or {}
            inp, out = usage.get("prompt_tokens"), usage.get("completion_tokens")
            if type(inp) is int and type(out) is int and min(inp, out) >= 0:
                actual = neurons(model, inp, out)
                attempt.update(input_tokens=inp, output_tokens=out, estimated_used_neurons=actual)
            choice = data["choices"][0]
            raw = choice["message"].get("content")
            attempt["truncated"] = choice.get("finish_reason") == "length"
            if attempt["truncated"]:
                attempt["actual_llm_used"] = bool(raw)
                attempt["status"] = "cloudflare_truncated"
                return None, attempt
            if not isinstance(raw, str) or not raw.strip():
                attempt["status"] = "cloudflare_empty_response"
                return None, attempt
            attempt["actual_llm_used"] = True
            answer, reason = parse_answer(raw)
            attempt["status"] = "proposal" if answer is not None else reason or "invalid_schema"
            return answer, attempt
        except requests.ConnectTimeout:
            attempt["status"] = "cloudflare_connect_timeout"
            return None, attempt
        except requests.ReadTimeout:
            attempt["status"] = "cloudflare_read_timeout"
            return None, attempt
        except requests.Timeout:
            attempt["status"] = "cloudflare_timeout"
            return None, attempt
        except requests.ConnectionError:
            attempt["status"] = "cloudflare_connection_error"
            return None, attempt
        except (requests.RequestException, ValueError, TypeError, AttributeError, KeyError, IndexError):
            attempt["status"] = ("cloudflare_invalid_response" if attempt["http_status"] == 200
                                 else "cloudflare_request_error")
            return None, attempt
        finally:
            if attempt.get("status") in {
                "cloudflare_connect_timeout", "cloudflare_read_timeout", "cloudflare_timeout",
                "cloudflare_connection_error", "cloudflare_http_403", "cloudflare_http_404", "cloudflare_http_410",
                "cloudflare_http_429", "cloudflare_http_500", "cloudflare_http_502",
                "cloudflare_http_503", "cloudflare_http_504",
            }:
                self.cooldown_until[model] = time.monotonic() + MODEL_COOLDOWN
            attempt["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            self.state.finish_cloudflare(uid, actual)
