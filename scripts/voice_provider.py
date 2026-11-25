"""Select the sole permitted narrator without calling any service."""
from __future__ import annotations

import os


def select_provider(settings=None, requested=None):
    configured = (settings or {}).get("voice_provider", "gemini_tts")
    provider = requested or os.getenv("TURK_TARIHI_VOICE_PROVIDER") or configured
    if str(provider).lower() != "gemini_tts" or str(configured).lower() != "gemini_tts":
        raise RuntimeError("Yalnız açıkça onaylanan Gemini Charon kullanılabilir; otomatik geçiş yok.")
    return "gemini_tts"


def synthesize(*args, **kwargs):
    raise RuntimeError("Anlatım yalnız scripts.gemini_tts.narrate ile yapılabilir.")
