"""Gemini text transport and ordered free editorial fallback."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid

import requests

from scripts.cloudflare_editorial import CloudflareEditorial, cloudflare_available, redact_text, turkish_json_parser
from scripts.editorial_llm import FreeReviewSession
from scripts.gemini_tts import free_project_key
from scripts.provider_budget import Budget

FLASH = "gemini-3.8-flash"
LITE = "gemini-3.1-flash-lite"
GEMMA = "gemma-4-26b-a4b-it"
LIMITS = {FLASH: (2, 24_000, 18), LITE: (4, 40_000, 36), GEMMA: (3, 24_000, 24)}
BASE = "https://generativelanguage.googleapis.com/v1beta"
TRANSIENT = {408, 429, 500, 502, 503, 504}
MAX_RETRY_DELAY = 12
MODEL_ALTERNATIVES = {FLASH: LITE, LITE: GEMMA, GEMMA: LITE}


def model_for(role, prompt):
    role = role.lower()
    if any(word in role for word in ("yönetmeni", "doğruluk", "doğrulama", "araştırmacısı")):
        return FLASH
    if any(word in role for word in ("senaryo", "sanat", "başlık", "görsel")):
        return GEMMA
    return LITE


def gemini_authorized():
    return os.getenv("ENABLE_GEMINI_EDITORIAL") == "1" and os.getenv("GEMINI_FREE_TIER_CONFIRMED") == "1"


class GeminiReviewSession:
    def __init__(self, key, state, *, prior_calls=0, requester=None, brand="tarih", quota_path=None,
                 sleep=time.sleep, max_attempts=8, wait_for_slot=False, routed=False,
                 quota_reader=None, cloud_requester=None, cloud_reader=None):
        self.routed = routed
        self.key = (free_project_key(gemini_authorized())
                    if not routed or gemini_authorized() and os.getenv("GEMINI_API_KEY", "").strip() else "")
        if self.key and self.key == os.getenv("GEMINI_IMAGE_API_KEY", "").strip():
            raise RuntimeError("Ücretsiz metin ve ücretli görsel anahtarları aynı olamaz.")
        self.state = state
        self.brand = brand
        self.requester = requester or requests.post
        self.budget = (Budget(quota_path or os.getenv("GEMINI_QUOTA_DB", ".cache/gemini-quota.sqlite3"))
                       if self.key else None)
        self.cloudflare = (CloudflareEditorial(state, brand, requester=cloud_requester, reader=cloud_reader)
                           if routed and cloudflare_available() else None)
        self.fallback = (FreeReviewSession(key, state, requester if routed else None,
                                          quota_reader, sleep, prior_calls) if key else None)
        self.calls = self.cached_roles = 0
        self.gemini_attempts = 0
        self.remaining = None
        self.quota_http = None
        self.stop_reason = None
        self.failed_models = set()
        self.gemini_quota_exhausted = False
        self.sleep = sleep
        self.max_attempts = max_attempts
        self.wait_for_slot = wait_for_slot

    @property
    def cloudflare_calls(self):
        return self.cloudflare.calls if self.cloudflare else 0

    @property
    def provider_priority(self):
        return [provider for enabled, provider in (
            (self.key, "gemini_free"),
            (self.cloudflare, "cloudflare_workers_ai"),
            (self.fallback, "openrouter_free"),
        ) if enabled]

    def evaluate(self, role, instruction, prompt, parse_answer, namespace="editorial-v1", max_tokens=1600,
                 reserve_calls=0, result_tool=None, primary_only=False, requested_model=None):
        model = requested_model or model_for(role, prompt)
        if model not in LIMITS:
            raise ValueError("Model is not in the free editorial allowlist.")
        full_input = instruction + "\n\n" + json.dumps(prompt, ensure_ascii=False, sort_keys=True)
        full_input = redact_text(full_input)
        queue_id = None
        reply_key = None
        if self.routed and not primary_only:
            queue_id = hashlib.sha256(json.dumps(
                ["multi-llm-v1", self.brand, role, namespace, model, max_tokens, full_input,
                 redact_text(result_tool)], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            verified_key = "routed:turkish:" + queue_id
            reply_key = verified_key if self.cloudflare else "routed:" + queue_id
            if self.cloudflare:
                parse_answer = turkish_json_parser(parse_answer)
            previous = self.state.read(verified_key) or (self.state.read(reply_key) if not self.cloudflare else None)
            if previous:
                self.cached_roles += 1
                self.state.clear_review(queue_id)
                return {**previous, "role": role, "response_source": "cache", "attempts": []}

        def accept(outcome):
            if queue_id and outcome["status"] == "proposal":
                self.state.save(reply_key, {
                    key: value for key, value in outcome.items() if key not in {"attempts", "response_source"}
                })
                self.state.clear_review(queue_id)
            return outcome
        cache = "gemini:" + hashlib.sha256(json.dumps(
            [self.brand, namespace, model, max_tokens, full_input], ensure_ascii=False).encode()).hexdigest()
        previous = self.state.read(cache)
        if previous and (not self.cloudflare or primary_only):
            self.cached_roles += 1
            return accept({**previous, "role": role, "response_source": "cache", "attempts": []})
        reserved_tokens = len(full_input.encode("utf-8"))
        routes = (model, model) if primary_only else (model, model, MODEL_ALTERNATIVES[model])
        if not self.key or self.gemini_quota_exhausted and not primary_only:
            routes = ()
        attempts = []
        for index, route in enumerate(routes):
            if route in self.failed_models or self.gemini_attempts >= self.max_attempts - reserve_calls:
                continue
            call_id = uuid.uuid4().hex
            if not self.budget.reserve_free(call_id, self.brand, route, reserved_tokens, LIMITS[route]):
                delay = self.budget.free_slot_delay(route, reserved_tokens, LIMITS[route])
                if self.wait_for_slot and delay is not None and 0 < delay <= 61:
                    self.sleep(delay)
                    if not self.budget.reserve_free(call_id, self.brand, route, reserved_tokens, LIMITS[route]):
                        continue
                else:
                    continue
            self.gemini_attempts += 1
            use_interactions = index == 1 and route != GEMMA
            answer, attempt = self._call(route, full_input, parse_answer, max_tokens, call_id,
                                         interactions=use_interactions)
            attempts.append({"provider": "gemini", **attempt})
            if answer is not None:
                settled = {"status": "proposal", "model": route, "http_status": 200, "provider": "gemini",
                           "actual_llm_used": True, "answer": answer}
                if not self.cloudflare or primary_only:
                    self.state.save(cache, settled)
                return accept({**settled, "role": role, "response_source": "live", "attempts": attempts})
            status = attempt["http_status"]
            if status in {401, 403}:
                self.failed_models.update(LIMITS)
                break
            retryable = status in TRANSIENT or status is None or status == 200
            delay = max(2 ** (index + 1), attempt.get("retry_after_seconds") or 0)
            if not retryable or delay > MAX_RETRY_DELAY or index == 1:
                self.failed_models.add(route)
            # A blocked Cloudflare plan must not take away the existing Gemini alternative.
            if (self.cloudflare and not primary_only and (status == 429 or index == 1)
                    and self.cloudflare.check_plan()):
                self.gemini_quota_exhausted = status == 429
                break
            if index + 1 < len(routes) and retryable and delay <= MAX_RETRY_DELAY:
                self.sleep(delay)
        if self.cloudflare and not primary_only:
            answer, cloud_attempt = self.cloudflare.evaluate(role, instruction, prompt, parse_answer,
                                                               max_tokens, reserve_calls)
            attempts.append(cloud_attempt)
            if answer is not None:
                return accept({"role": role, "status": "proposal", "model": cloud_attempt["model"],
                               "provider": "cloudflare_workers_ai", "http_status": 200,
                               "actual_llm_used": True, "answer": answer,
                               "response_source": "live", "attempts": attempts})
        attempt = attempts[-1] if attempts else {
            "status": "gemini_local_quota_or_cooldown", "model": model,
            "actual_llm_used": False, "http_status": None, "requested_model": model}

        if self.fallback and not primary_only:
            before_calls, before_cache = self.fallback.calls, self.fallback.cached_roles
            fallback_namespace = f"{namespace}:verified-turkish-v1" if self.cloudflare else namespace
            outcome = self.fallback.evaluate(role, redact_text(instruction), redact_text(prompt), parse_answer, fallback_namespace,
                                             max_tokens, reserve_calls, result_tool)
            self.calls += self.fallback.calls - before_calls
            self.cached_roles += self.fallback.cached_roles - before_cache
            self.remaining = self.fallback.remaining
            self.quota_http = self.fallback.quota_http
            outcome = {**outcome, "provider": "openrouter_free",
                       "attempts": [*attempts, *({"provider": "openrouter_free", **a} for a in outcome["attempts"])]}
        else:
            outcome = {"role": role, "status": "failed" if attempts else "blocked", "model": attempt["model"],
                       "actual_llm_used": False, "http_status": attempt["http_status"],
                       "error_type": attempt["status"], "attempts": attempts, "reason": attempt["status"]}
        if queue_id and outcome["status"] != "proposal":
            self.state.queue_review(queue_id, self.brand, role, outcome["reason"])
            outcome.update(queued=True, task_id=queue_id,
                           actual_llm_used=any(a["actual_llm_used"] for a in outcome["attempts"]))
        return accept(outcome)

    def _call(self, model, full_input, parse_answer, max_tokens, call_id, *, interactions=False):
        api = "interactions" if interactions else "generateContent"
        if interactions:
            url = f"{BASE}/interactions"
            payload = {"model": model, "input": full_input, "store": False,
                       "response_format": {"type": "text", "mime_type": "application/json"},
                       "generation_config": {"max_output_tokens": max_tokens}}
        else:
            url = f"{BASE}/models/{model}:generateContent"
            config = {"temperature": 0.35, "maxOutputTokens": max_tokens}
            if model != GEMMA:
                config["responseMimeType"] = "application/json"
                config["thinkingConfig"] = {"thinkingLevel": "minimal" if model == LITE else "low"}
            payload = {"contents": [{"role": "user", "parts": [{"text": full_input}]}], "generationConfig": config}
        status, actual, tokens, retry_after, provider_status = None, False, None, None, None
        try:
            response = self.requester(url,
                                      headers={"x-goog-api-key": self.key}, json=payload,
                                      timeout=(10, 70), allow_redirects=False)
            status = response.status_code
            if status != 200:
                headers = response.headers
                header = headers.get("Retry-After") if headers is not None else None
                if isinstance(header, str) and header.isdigit() and len(header) < 6:
                    retry_after = int(header)
                try:
                    vendor_error = response.json().get("error", {}).get("status")
                    if isinstance(vendor_error, str) and re.fullmatch(r"[A-Z_]{1,48}", vendor_error):
                        provider_status = vendor_error
                except (ValueError, AttributeError):
                    pass
                raise RuntimeError("gemini_http_error")
            data = response.json()
            if interactions:
                if data.get("status") != "completed":
                    raise RuntimeError("gemini_interaction_incomplete")
                usage = data.get("usage", {})
                prompt_tokens, output_tokens = usage.get("total_input_tokens"), usage.get("total_output_tokens")
                if type(prompt_tokens) is int and type(output_tokens) is int:
                    tokens = (prompt_tokens, output_tokens)
                content = "".join(part["text"] for step in data.get("steps", [])
                                  if step.get("type") == "model_output" for part in step.get("content", [])
                                  if part.get("type") == "text")
            else:
                usage = data.get("usageMetadata", {})
                if type(usage.get("promptTokenCount")) is int and type(usage.get("candidatesTokenCount")) is int:
                    tokens = (usage["promptTokenCount"], usage["candidatesTokenCount"] + usage.get("thoughtsTokenCount", 0))
                content = "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"]
                                  if not part.get("thought"))
            actual = bool(content.strip())
            result, reason = parse_answer(content.replace(self.key, "[REDACTED]"))
            if result is None:
                raise RuntimeError(reason or "gemini_invalid_answer")
            self.budget.finish(call_id, "complete", tokens=tokens)
            return result, {"model": model, "requested_model": model, "status": "proposal", "http_status": status,
                            "actual_llm_used": True, "tokens": tokens, "api": api}
        except (requests.RequestException, KeyError, IndexError, ValueError, TypeError, AttributeError, RuntimeError) as exc:
            self.budget.finish(call_id, "failed" if status else "unknown", tokens=tokens)
            reason = str(exc) if isinstance(exc, RuntimeError) else "gemini_response_or_connection_error"
            return None, {"model": model, "requested_model": model, "status": reason,
                          "http_status": status, "actual_llm_used": actual, "tokens": tokens,
                          "provider_status": provider_status, "retry_after_seconds": retry_after, "api": api}
