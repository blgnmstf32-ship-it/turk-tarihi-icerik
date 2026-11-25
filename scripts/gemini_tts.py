"""Optional Gemini narration for an explicitly confirmed, unbilled AI Studio project."""
from __future__ import annotations

import base64
import binascii
from difflib import SequenceMatcher
import io
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import wave

import requests

MODEL = "gemini-3.8-flash-tts"
VOICE = "Charon"
ALIGNMENT_MODEL = "small"
# Approved by the owner after listening to voice-comparison run 45601433415.
APPROVED_AUDIO = {
    "169a62476f05eb536c82d9b67c9dd8e4017d93324ca20e6a3dfcaee81f866":
        "3c1b6e038fa28d36289146d63dcf0e0b5c17b56a62beb4b444ba7e4144d0d83b",
}
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


def align_captions(segments, transcript_words, duration, *, compact=False):
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
        tokens = segment["caption"].split()
        if compact and len(tokens) > 6 and [t for token in tokens for t in _tokens(token)] == expected[span.start:span.stop]:
            chunks = [tokens[i:i + 5] for i in range(0, len(tokens), 5)]
            if len(chunks[-1]) <= 2:
                chunks[-2].extend(chunks.pop())
            starts = [start]
            offset = span.start
            for chunk in chunks[:-1]:
                offset += sum(len(_tokens(token)) for token in chunk)
                # A missing boundary must not be replaced by a guessed word time.
                if offset not in matched or not starts[-1] < matched[offset][0] < end:
                    break
                starts.append(matched[offset][0])
            if len(starts) == len(chunks):
                cues.extend({"start": a, "end": b, "text": " ".join(chunk)}
                            for a, b, chunk in zip(starts, [*starts[1:], end], chunks))
            else:
                cues.append({"start": start, "end": end, "text": segment["caption"]})
        else:
            cues.append({"start": start, "end": end, "text": segment["caption"]})
        last_end = end
    return cues


def approved_recording(directory, script):
    directory = Path(directory)
    receipt = json.loads((directory / "GEMINI_RECEIPT.json").read_text(encoding="utf-8"))
    raw = (directory / "GEMINI_CHARON.wav").read_bytes()
    script_hash = hashlib.sha256(script.encode("utf-8")).hexdigest()
    audio_hash = hashlib.sha256(raw).hexdigest()
    if (APPROVED_AUDIO.get(script_hash) != audio_hash or receipt.get("audio_sha256") != audio_hash
            or receipt.get("script_sha256") != script_hash or receipt.get("model") != MODEL
            or receipt.get("voice") != VOICE or receipt.get("free_project_confirmed") is not True):
        raise ValueError("Onaylı Charon kaydı, senaryo veya dosya doğrulaması eşleşmedi.")
    with wave.open(io.BytesIO(raw), "rb") as stream:
        duration = stream.getnframes() / stream.getframerate()
    if not 60 <= duration <= 75:
        raise ValueError("Onaylı Charon kaydının süresi üretim aralığında değil.")
    return raw, duration


def narrate(segments, output, confirmed, *, approved_voice=None):
    from scripts.speech_audit import load_local_model, transcribe_local

    if approved_voice is None:
        free_project_key(confirmed)
    # Check the local alignment model before any external request.
    model = load_local_model(ALIGNMENT_MODEL)
    script = "\n".join(segment["spoken"] for segment in segments)
    raw, duration = (approved_recording(approved_voice, script) if approved_voice is not None
                     else request_audio(script, confirmed))
    output = Path(output)
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        audio = Path(work) / "gemini.wav"
        audio.write_bytes(raw)
        transcript = transcribe_local(audio, model=model)
        cues = align_captions(segments, transcript["words"], duration, compact=True)
        audio.replace(output)
    return cues
