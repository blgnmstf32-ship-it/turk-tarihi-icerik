"""Optional Gemini narration for an explicitly confirmed, unbilled AI Studio project."""
from __future__ import annotations

import base64
import binascii
from difflib import SequenceMatcher
import io
import os
from pathlib import Path
import re
import tempfile
import wave

import requests

MODEL = "gemini-3.8-flash-tts"
VOICE = "Charon"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
STYLE = (
    "Türkiye Türkçesi konuşan, sıcak ve sinematik bir erkek belgesel anlatıcısı. "
    "İlk cümleye hemen gir ve ilk üç saniyede bitir. Metni aynen, başlık veya yorum eklemeden oku. "
    "Cümlelerin akışına göre hızı, vurguyu ve doğal durakları kendin belirle. "
    "Keşif anlarında merakı artır, tarihsel belirsizlikleri ölçülü söyle. "
    "Müzik veya efekt üretme. Belgesel anlatımı boyunca 60–75 saniyeyi hedefle."
)


def free_project_key(confirmed):
    if not confirmed:
        raise RuntimeError(
            "Gemini yalnız faturalandırma bağlanmamış bir AI Studio projesiyle ve "
            "--confirm-gemini-free-project seçeneğiyle çalışır."
        )
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY eksik. Ücretsiz AI Studio projesinin anahtarını ortamdan sağlayın.")
    return key


def request_audio(script, confirmed, requester=None):
    """One request; no retries, alternate model, credentials in URLs, or paid fallback."""
    key = free_project_key(confirmed)
    payload = {
        "model": MODEL,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": script,
            "annotations": [{"type": "speech_metadata", "style": STYLE}],
        }]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": VOICE}]},
        "store": False,
    }
    try:
        response = (requester or requests.post)(
            ENDPOINT, headers={"x-goog-api-key": key}, json=payload,
            timeout=(10, 180), allow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            raise ValueError("Unexpected redirect")
        response.raise_for_status()
        result = response.json()
        if result.get("status") != "completed":
            raise ValueError("Interaction did not complete")
        audio = [
            item["data"] for step in result["steps"] if step["type"] == "model_output"
            for item in step["content"] if item["type"] == "audio"
        ]
        if len(audio) != 1:
            raise ValueError("Expected one continuous audio response")
        raw = base64.b64decode(audio[0], validate=True)
        with wave.open(io.BytesIO(raw), "rb") as stream:
            duration = stream.getnframes() / stream.getframerate()
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
                raise ValueError("Expected a mono PCM WAV")
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", None)
        raise RuntimeError(f"Gemini TTS isteği başarısız (HTTP {status or 'bağlantı hatası'}).") from None
    except (KeyError, ValueError, TypeError, AttributeError, binascii.Error, wave.Error, EOFError):
        raise RuntimeError("Gemini TTS geçerli bir kesintisiz PCM WAV üretmedi.") from None
    if not 60 <= duration <= 75:
        raise ValueError(f"Gemini anlatımı {duration:.1f} saniye. Metni gözden geçirip açıkça yeniden çalıştırın.")
    return raw, duration


def _tokens(text):
    return re.findall(r"[^\W_]+", text.translate(str.maketrans("Iİ", "ıi")).lower())


def align_captions(segments, transcript_words, duration):
    expected, spans = [], []
    for segment in segments:
        start = len(expected)
        expected.extend(_tokens(segment["spoken"]))
        spans.append(range(start, len(expected)))

    heard, timings = [], []
    for word in transcript_words:
        for token in _tokens(word["text"]):
            heard.append(token)
            timings.append((word["start"], word["end"]))
    matcher = SequenceMatcher(a=expected, b=heard, autojunk=False)
    matched = {
        block.a + i: timings[block.b + i]
        for block in matcher.get_matching_blocks() for i in range(block.size)
    }
    if not expected or len(matched) / max(len(expected), len(heard)) < 0.70:
        raise ValueError("Gemini konuşması ile senaryo arasında güvenilir eşleşme bulunamadı.")
    if 0 not in matched or spans[0][-1] not in matched:
        raise ValueError("Gemini açılış cümlesinin başlangıç veya bitişi doğrulanamadı.")
    cues, last_end = [], 0.0
    for segment, span in zip(segments, spans):
        times = [matched[i] for i in span if i in matched]
        if not times or len(times) / len(span) < 0.60:
            raise ValueError("Gemini altyazısında bir cümle konuşmaya güvenle eşlenemedi.")
        start = max(last_end, times[0][0])
        end = min(duration, times[-1][1])
        if end <= start:
            raise ValueError("Gemini altyazı zamanlaması geçersiz.")
        cues.append({"start": start, "end": end, "text": segment["caption"]})
        last_end = end
    return cues


def narrate(segments, output, confirmed):
    from scripts.speech_audit import load_local_model, transcribe_local

    free_project_key(confirmed)
    # Check the local alignment model before any external request.
    model = load_local_model("tiny")
    script = "\n".join(segment["spoken"] for segment in segments)
    raw, duration = request_audio(script, confirmed)
    output = Path(output)
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        audio = Path(work) / "gemini.wav"
        audio.write_bytes(raw)
        transcript = transcribe_local(audio, model=model)
        cues = align_captions(segments, transcript["words"], duration)
        audio.replace(output)
    return cues
