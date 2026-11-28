"""Produce the five approved 15G narration takes within the shared free budget."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter, sleep
from uuid import uuid4

import requests

from scripts import capacity_15b, gemini_tts
from scripts.provider_budget import Budget

TARGETS = {
    "kultepe-kil-borc-kaydi": 72,
    "lewis-satranc-tasim-takim": 68,
    "ife-heykel-mum-kalip": 65,
    "firca-kurutma-duzeni": 67,
    "goz-makyaji-aplikatoru": 73,
}
USAGE_FIELDS = ("total_input_tokens", "total_output_tokens", "total_tokens")


def take(topic, budget, folder, *, retry=False):
    identifier = topic["id"]
    brand = topic["brand"]
    voice = {"tarih": "Charon", "bakim": "Sulafat"}[brand]
    script = "\n".join(beat["text"] for beat in topic["beats"])
    result = {"id": identifier, "brand": brand, "model": gemini_tts.MODEL, "voice": voice,
              "script_sha256": sha256(script.encode()).hexdigest(), "requested_seconds": TARGETS[identifier],
              "api_calls": 0, "http_status": None, "usage": {}}
    request_id = uuid4().hex
    reservation = len(script.encode()) + len(gemini_tts.STYLE.encode()) + 512
    model = gemini_tts.MODEL
    delay = budget.free_slot_delay(model, reservation, gemini_tts.LOCAL_LIMIT)
    if delay is None or delay > 61:
        return {**result, "status": "local_quota"}
    if delay:
        sleep(delay)
    if not budget.reserve_free(request_id, brand, model, reservation, gemini_tts.LOCAL_LIMIT):
        return {**result, "status": "local_quota"}

    def request(url, *, json, **kwargs):
        if url != gemini_tts.ENDPOINT or kwargs.get("allow_redirects") is not False:
            raise RuntimeError("invalid_transport")
        style = json["input"][0]["content"][0]["annotations"][0]
        style["style"] += (
            f" Yaklaşık {TARGETS[identifier]} saniyelik doğal bir okuma yap. 60–75 saniye içinde kal."
            " İlk kısa cümle ile hemen başla. Sonuna sessizlik ekleme."
        )
        if retry:
            tempo = {"lewis-satranc-tasim-takim": 110, "ife-heykel-mum-kalip": 101}[identifier]
            style["style"] += (
                f" Açılışı ilk üç saniyede bitirdikten sonra anlatımı dakikada yaklaşık {tempo} kelimeye yavaşlat. "
                "Sonraki cümle aralarında düşünceyi belirginleştiren kısa doğal duraklar bırak. "
                "Hedefi konuşmanın kendi akışıyla 65 ila 71 saniye tut."
            )
        result["api_calls"] += 1
        response = requests.post(url, json=json, **kwargs)
        result["http_status"] = response.status_code
        if response.ok:
            try:
                usage = response.json().get("usage", {})
                result["usage"] = {field: usage[field] for field in USAGE_FIELDS
                                   if type(usage.get(field)) is int and usage[field] >= 0}
            except (AttributeError, ValueError):
                pass
        return response

    started = perf_counter()
    try:
        raw, duration = gemini_tts.request_audio(script, True, requester=request, brand=brand, voice=voice)
    except (RuntimeError, ValueError) as exc:
        # The provider's body, request headers and arbitrary exceptions never enter logs.
        status = result["http_status"]
        result.update(status="duration_out_of_range" if isinstance(exc, ValueError) else
                      "provider_quota" if status == 429 else "provider_error")
        budget.finish(request_id, "unknown")
    else:
        filename = identifier + ".wav"
        temporary = folder / (filename + ".tmp")
        temporary.write_bytes(raw)
        temporary.replace(folder / filename)
        result.update(status="recorded", audio_file=filename, audio_sha256=sha256(raw).hexdigest(),
                      seconds=round(duration, 3))
        usage = result["usage"]
        budget.finish(request_id, "complete",
                      tokens=(usage.get("total_input_tokens", reservation),
                              usage.get("total_output_tokens", round(duration * 25))))
    return {**result, "wall_seconds": round(perf_counter() - started, 3)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--quota", type=Path, required=True)
    args = cli.parse_args()
    catalog = capacity_15b.load()
    capacity_15b.validate(catalog)
    if {item["id"] for item in catalog["reels"]} != TARGETS.keys():
        raise ValueError("15G source catalogue changed")
    args.out.mkdir(parents=True, exist_ok=True)
    args.quota.parent.mkdir(parents=True, exist_ok=True)
    budget = Budget(args.quota)
    report_path = args.out / "TTS_REPORT.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {
        "free_project_confirmation": "owner_verified_and_runner_matched",
        "model": gemini_tts.MODEL, "local_limits": list(gemini_tts.LOCAL_LIMIT), "takes": []}
    saved = {row["id"]: row for row in report["takes"] if row["status"] == "recorded"}
    retries = {"lewis-satranc-tasim-takim", "ife-heykel-mum-kalip"}
    attempted = {row["id"] for row in report["takes"] if row["status"] == "duration_out_of_range"}
    for topic in catalog["reels"]:
        if prior := saved.get(topic["id"]):
            expected = sha256("\n".join(beat["text"] for beat in topic["beats"]).encode()).hexdigest()
            wav = args.out / prior["audio_file"]
            if prior["script_sha256"] != expected or capacity_15b.digest(wav) != prior["audio_sha256"]:
                raise ValueError("Existing narration does not match its receipt")
            continue
        if topic["id"] in attempted and topic["id"] not in retries:
            continue
        row = take(topic, budget, args.out, retry=topic["id"] in attempted)
        report["takes"].append(row)
        capacity_15b.write(report_path, report)
        print(json.dumps({"id": row["id"], "status": row["status"], "http_status": row["http_status"]}),
              flush=True)
        if row["status"] in {"local_quota", "provider_quota"} or row["http_status"] in {401, 403}:
            break


if __name__ == "__main__":
    main()
