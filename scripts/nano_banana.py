"""Paid image transport for one approved model with a reservation-first ledger."""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import os
from pathlib import Path
import re

from PIL import Image, ImageOps
import requests

from scripts.gemini_editorial import BASE
from scripts.provider_budget import image_quote

MODEL = "gemini-3.1-flash-lite-image"
BRANDS = {"tarih", "bakim"}
PRICE_URL = "https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-flash-lite-image"


def identity(brand, prompt):
    return hashlib.sha256(json.dumps([brand, prompt, MODEL, "9:16", "1K"], ensure_ascii=False).encode()).hexdigest()


def image_config(prompt):
    if not 20 <= len(prompt.encode()) <= 720:
        raise ValueError("Görsel istemi 20–720 UTF-8 bayt olmalı.")
    return {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"},
                                 "candidateCount": 1, "maxOutputTokens": 1184}}


def check_key(confirmed):
    key = os.getenv("GEMINI_IMAGE_API_KEY", "").strip()
    if not confirmed or not key:
        raise RuntimeError("Ücretli görsel üretimi için açık onay ve GEMINI_IMAGE_API_KEY gerekli.")
    if key == os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("Ücretli görsel ve ücretsiz Gemini anahtarları farklı olmalı.")
    return key


def image_result(data, output):
    parts = data["candidates"][0]["content"]["parts"]
    images = [p["inlineData"] for p in parts if "inlineData" in p and not p.get("thought")]
    if len(images) != 1 or images[0].get("mimeType") not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError("Gemini tek geçerli görsel döndürmedi.")
    compressed = base64.b64decode(images[0]["data"], validate=True)
    if len(compressed) > 12_000_000:
        raise ValueError("Görsel veri boyutu sınırı aşıldı.")
    with Image.open(io.BytesIO(compressed)) as source:
        width, height = source.size
        if min(source.size) < 640 or max(source.size) > 2560 or abs(width / height - 9 / 16) > .03:
            raise ValueError("Nano Banana beklenen dikey 1K çıktı boyutunu üretmedi.")
        converted = ImageOps.fit(source.convert("RGB"), (1080, 1920), Image.Resampling.LANCZOS)
        converted.save(output, format="JPEG", quality=92, optimize=True)
    usage = data.get("usageMetadata", {})
    counts = {row.get("modality"): row.get("tokenCount") for row in usage.get("candidatesTokensDetails", [])}
    return {"width": width, "height": height, "input_tokens": usage.get("promptTokenCount"),
            "output_tokens": usage.get("candidatesTokenCount"), "image_tokens": counts.get("IMAGE"),
            "thinking_tokens": usage.get("thoughtsTokenCount", 0),
            "model_version": data.get("modelVersion") if isinstance(data.get("modelVersion"), str) else None,
            "sha256": hashlib.sha256(Path(output).read_bytes()).hexdigest()}


def measured_image_cost(mode, info):
    values = [info.get(k) for k in ("input_tokens", "output_tokens", "image_tokens", "thinking_tokens")]
    if any(type(value) is not int or value < 0 for value in values):
        return None
    inputs, outputs, images, thinking = values
    if images > outputs or not images:
        return None
    return image_quote(mode, 1, input_tokens=inputs, output_text_tokens=outputs-images+thinking, image_tokens=images)


def submit(budget, sync, brand, prompts, path, *, confirmed, mode="batch", requester=None):
    """Sync the new reservation to shared storage before the one POST. Poll batches separately."""
    if brand not in BRANDS or not 1 <= len(prompts) <= 35 or len(set(prompts)) != len(prompts):
        raise ValueError("Marka veya görsel istemleri geçersiz.")
    if mode == "standard" and len(prompts) != 1:
        raise ValueError("Standart istek bir görselle sınırlı.")
    configs = [image_config(prompt) for prompt in prompts]
    key = check_key(confirmed)
    uid = identity(brand, json.dumps(prompts, ensure_ascii=False))
    quote = image_quote(mode, len(configs))
    if not budget.reserve_image(uid, brand, MODEL, mode, len(configs)):
        prior = budget.entry(uid)
        if prior and prior["status"] == "complete" and len(prompts) == 1 and path.is_file():
            return {"id": uid, "brand": brand, "model": MODEL, "state": "cache", "cloud_requests": 0}
        if prior and prior["operation"]:
            return {"id": uid, "brand": brand, "model": MODEL, "state": "submitted",
                    "operation": prior["operation"], "cloud_requests": 0}
        raise RuntimeError("Görsel bütçesi doldu veya aynı işin isteği daha önce kayda alındı.")
    sync()
    if mode == "batch":
        payload = {"batch": {"displayName": f"{brand}-{uid[:14]}",
                   "inputConfig": {"requests": {"requests": [
                       {"request": config, "metadata": {"key": str(index)}} for index, config in enumerate(configs)]}}}}
    else:
        payload = configs[0]
    action = "batchGenerateContent" if mode == "batch" else "generateContent"
    try:
        response = (requester or requests.post)(f"{BASE}/models/{MODEL}:{action}",
                     json=payload, headers={"x-goog-api-key": key}, timeout=(10, 120), allow_redirects=False)
        if response.status_code != 200:
            status = response.status_code
            budget.finish(uid, "failed" if 400 <= status < 500 and status != 408 else "unknown")
            raise RuntimeError(f"Nano Banana HTTP {status}. İstek otomatik tekrarlanmadı.")
        data = response.json()
        report = {"id": uid, "brand": brand, "model": MODEL, "mode": mode, "state": "submitted",
                  "quoted_usd_micros": quote, "cloud_requests": 1, "submit_http_status": response.status_code}
        if mode == "batch":
            operation = data["name"]
            if not re.fullmatch(r"batches/[a-zA-Z0-9_-]+", operation):
                raise ValueError("Geçersiz Batch kimliği.")
            budget.finish(uid, "submitted", operation=operation)
            return {**report, "operation": operation}
        info = image_result(data, path)
        measured = measured_image_cost(mode, info)
        budget.finish(uid, "complete", tokens=(info["input_tokens"], info["output_tokens"]),
                      measured_cost=max(quote, measured) if measured is not None else None)
        return {**report, **info, "state": "complete", "output": path.name,
                "estimated_metered_usd_micros": measured}
    except (requests.RequestException, KeyError, ValueError, OSError, TypeError, IndexError, binascii.Error):
        budget.finish(uid, "unknown")
        raise RuntimeError("Nano Banana bağlantısı veya çıktısı doğrulanamadı. Rezervasyon korundu.") from None
    finally:
        sync()


def collect_batch(budget, sync, uid, out, *, confirmed, expected_count=1, requester=None):
    entry = budget.entry(uid)
    if not entry or not entry["operation"] or entry["status"] not in {"submitted", "complete"}:
        raise RuntimeError("Geçerli bir Batch kaydı gerekli.")
    key = check_key(confirmed)
    operation = entry["operation"]
    if not re.fullmatch(r"batches/[a-zA-Z0-9_-]+", operation):
        raise ValueError("Geçersiz Batch kimliği.")
    try:
        response = (requester or requests.get)(f"{BASE}/{operation}", headers={"x-goog-api-key": key},
                                              timeout=(10, 80), allow_redirects=False)
        if response.status_code != 200:
            raise RuntimeError(f"Batch durum kontrolü HTTP {response.status_code}.")
        data = response.json()
        status = data.get("state") or data.get("metadata", {}).get("state")
        if ("error" in data or status in {"JOB_STATE_FAILED", "JOB_STATE_EXPIRED", "JOB_STATE_CANCELLED",
                                         "BATCH_STATE_FAILED", "BATCH_STATE_EXPIRED", "BATCH_STATE_CANCELLED"}):
            budget.finish(uid, "failed")
            sync()
            raise RuntimeError("Gemini Batch işini tamamlayamadı. Rezervasyon korundu.")
        if not data.get("done") and status not in {"JOB_STATE_SUCCEEDED", "BATCH_STATE_SUCCEEDED"}:
            return {"id": uid, "operation": operation, "state": "submitted", "poll_requests": 1}
        result = data.get("dest") or data["response"]
        rows = result["inlinedResponses"]
        if isinstance(rows, dict):
            rows = rows["inlinedResponses"]
        if not 1 <= expected_count <= 35 or len(rows) != expected_count:
            raise ValueError("Batch görsel sonuç sayısı geçersiz.")
        images = []
        for row in rows:
            number = int(row["metadata"]["key"])
            if number < 0 or number >= expected_count or any(item["index"] == number for item in images):
                raise ValueError("Batch sonucu anahtarı geçersiz.")
            images.append({"index": number, **image_result(row["response"], out / f"image-{number:02d}.jpg")})
        estimates = [measured_image_cost(entry["mode"], image) for image in images]
        measured = sum(estimates) if all(value is not None for value in estimates) else None
        budget.finish(uid, "complete", tokens=(
            sum(x["input_tokens"] or 0 for x in images), sum(x["output_tokens"] or 0 for x in images)),
            measured_cost=max(entry["reserved_usd_micros"], measured) if measured is not None else None)
        sync()
        return {"id": uid, "operation": operation, "state": "complete", "poll_requests": 1,
                "poll_http_status": response.status_code, "images": images, "requested_model": MODEL,
                "estimated_metered_usd_micros": measured, "price_reference": PRICE_URL}
    except (requests.RequestException, KeyError, ValueError, IndexError, TypeError, OSError):
        raise RuntimeError("Batch durumu veya görseller doğrulanamadı. Rezervasyon korundu.") from None
