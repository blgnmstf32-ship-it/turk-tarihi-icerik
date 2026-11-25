"""Gemini free-tier role transport. OpenRouter fallback is delegated to the existing guard."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid

import requests

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
                 sleep=time.sleep):
        self.key = free_project_key(gemini_authorized())
        if self.key == os.getenv("GEMINI_IMAGE_API_KEY", "").strip():
            raise RuntimeError("Ücretsiz metin ve ücretli görsel anahtarları aynı olamaz.")
        self.state = state
        self.brand = brand
        self.requester = requester or requests.post
        self.budget = Budget(quota_path or os.getenv("GEMINI_QUOTA_DB", ".cache/gemini-quota.sqlite3"))
        self.fallback = FreeReviewSession(key, state, prior_calls=prior_calls) if key else None
        self.calls = self.cached_roles = 0
        self.gemini_attempts = 0
        self.remaining = None
        self.quota_http = None
        self.stop_reason = None
        self.failed_models = set()
        self.sleep = sleep

    def evaluate(self, role, instruction, prompt, parse_answer, namespace="editorial-v1", max_tokens=1600,
                 reserve_calls=0, result_tool=None, primary_only=False):
        model = model_for(role, prompt)
        full_input = instruction + "\n\n" + json.dumps(prompt, ensure_ascii=False, sort_keys=True)
        full_input = full_input.replace(self.key, "[REDACTED]")
        cache = "gemini:" + hashlib.sha256(json.dumps(
            [self.brand, namespace, model, max_tokens, full_input], ensure_ascii=False).encode()).hexdigest()
        previous = self.state.read(cache)
        if previous:
            self.cached_roles += 1
            return {**previous, "role": role, "response_source": "cache", "attempts": []}
        reserved_tokens = len(full_input.encode("utf-8"))
        routes = (model, model) if primary_only else (model, model, MODEL_ALTERNATIVES[model])
        attempts = []
        for index, route in enumerate(routes):
            if route in self.failed_models or self.gemini_attempts >= 8:
                continue
            call_id = uuid.uuid4().hex
            if not self.budget.reserve_free(call_id, self.brand, route, reserved_tokens, LIMITS[route]):
                self.failed_models.add(route)
                continue
            self.gemini_attempts += 1
            use_interactions = index == 1 and route != GEMMA
            answer, attempt = self._call(route, full_input, parse_answer, max_tokens, call_id,
                                         interactions=use_interactions)
            attempts.append(attempt)
            if answer is not None:
                settled = {"status": "proposal", "model": route, "http_status": 200, "provider": "gemini",
                           "actual_llm_used": True, "answer": answer}
                self.state.save(cache, settled)
                return {**settled, "role": role, "response_source": "live", "attempts": attempts}
            status = attempt["http_status"]
            if status in {401, 403}:
                self.failed_models.update(LIMITS)
                break
            retryable = status in TRANSIENT or status is None
            delay = max(2 ** (index + 1), attempt.get("retry_after_seconds") or 0)
            if not retryable or delay > MAX_RETRY_DELAY or index == 1:
                self.failed_models.add(route)
            if index + 1 < len(routes) and retryable and delay <= MAX_RETRY_DELAY:
                self.sleep(delay)
        attempt = attempts[-1] if attempts else {
            "status": "gemini_local_quota_or_cooldown", "model": model,
            "actual_llm_used": False, "http_status": None, "requested_model": model}

        if self.fallback:
            before_calls, before_cache = self.fallback.calls, self.fallback.cached_roles
            outcome = self.fallback.evaluate(role, instruction, prompt, parse_answer, namespace,
                                             max_tokens, reserve_calls, result_tool)
            self.calls += self.fallback.calls - before_calls
            self.cached_roles += self.fallback.cached_roles - before_cache
            self.remaining = self.fallback.remaining
            self.quota_http = self.fallback.quota_http
            return {**outcome, "provider": "openrouter_free", "attempts": [*attempts, *outcome["attempts"]]}
        return {"role": role, "status": "failed" if attempts else "blocked", "model": model,
                "actual_llm_used": attempt["actual_llm_used"], "http_status": attempt["http_status"],
                "error_type": attempt["status"], "attempts": attempts, "reason": attempt["status"]}

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
