"""Gemini free-tier role transport. OpenRouter fallback is delegated to the existing guard."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
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
    def __init__(self, key, state, *, prior_calls=0, requester=None, brand="tarih", quota_path=None):
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

    def evaluate(self, role, instruction, prompt, parse_answer, namespace="editorial-v1", max_tokens=1600,
                 reserve_calls=0, result_tool=None):
        model = model_for(role, prompt)
        full_input = instruction + "\n\n" + json.dumps(prompt, ensure_ascii=False, sort_keys=True)
        full_input = full_input.replace(self.key, "[REDACTED]")
        cache = "gemini:" + hashlib.sha256(json.dumps(
            [self.brand, namespace, model, max_tokens, full_input], ensure_ascii=False).encode()).hexdigest()
        previous = self.state.read(cache)
        if previous:
            self.cached_roles += 1
            return {**previous, "role": role, "response_source": "cache", "attempts": []}
        call_id = uuid.uuid4().hex
        reserved_tokens = len(full_input.encode("utf-8"))
        permitted = (model not in self.failed_models and self.gemini_attempts < 8
                     and self.budget.reserve_free(call_id, self.brand, model, reserved_tokens, LIMITS[model]))
        if permitted:
            self.gemini_attempts += 1
            answer, attempt = self._call(model, full_input, parse_answer, max_tokens, call_id)
            if answer is not None:
                settled = {"status": "proposal", "model": model, "http_status": 200, "provider": "gemini",
                           "actual_llm_used": True, "answer": answer}
                self.state.save(cache, settled)
                return {**settled, "role": role, "response_source": "live", "attempts": [attempt]}
            self.failed_models.add(model)
        else:
            attempt = {"status": "gemini_local_quota_or_cooldown", "model": model,
                       "actual_llm_used": False, "http_status": None, "requested_model": model}
        if self.fallback:
            before_calls, before_cache = self.fallback.calls, self.fallback.cached_roles
            outcome = self.fallback.evaluate(role, instruction, prompt, parse_answer, namespace,
                                             max_tokens, reserve_calls, result_tool)
            self.calls += self.fallback.calls - before_calls
            self.cached_roles += self.fallback.cached_roles - before_cache
            self.remaining = self.fallback.remaining
            self.quota_http = self.fallback.quota_http
            return {**outcome, "provider": "openrouter_free", "attempts": [attempt, *outcome["attempts"]]}
        return {"role": role, "status": "failed" if permitted else "blocked", "model": model,
                "actual_llm_used": attempt["actual_llm_used"], "http_status": attempt["http_status"],
                "error_type": attempt["status"], "attempts": [attempt], "reason": attempt["status"]}

    def _call(self, model, full_input, parse_answer, max_tokens, call_id):
        config = {"temperature": 0.35, "maxOutputTokens": max_tokens}
        if model != GEMMA:
            config["responseMimeType"] = "application/json"
            config["thinkingConfig"] = {"thinkingLevel": "minimal" if model == LITE else "low"}
        payload = {"contents": [{"role": "user", "parts": [{"text": full_input}]}], "generationConfig": config}
        status, actual, tokens = None, False, None
        try:
            response = self.requester(f"{BASE}/models/{model}:generateContent",
                                      headers={"x-goog-api-key": self.key}, json=payload,
                                      timeout=(10, 70), allow_redirects=False)
            status = response.status_code
            if status != 200:
                raise RuntimeError("gemini_http_error")
            data = response.json()
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
                            "actual_llm_used": True, "tokens": tokens}
        except (requests.RequestException, KeyError, IndexError, ValueError, TypeError, AttributeError, RuntimeError) as exc:
            self.budget.finish(call_id, "failed" if status else "unknown", tokens=tokens)
            reason = str(exc) if isinstance(exc, RuntimeError) else "gemini_response_or_connection_error"
            return None, {"model": model, "requested_model": model, "status": reason,
                          "http_status": status, "actual_llm_used": actual, "tokens": tokens}
