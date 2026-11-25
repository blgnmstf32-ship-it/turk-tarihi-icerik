"""Retired speech entry points retained to reject legacy caller configurations."""


def narrate(*args, **kwargs):
    raise RuntimeError("Eski seslendirme yolu kapalı. Yalnız Gemini Charon kullanılabilir.")


narrate_segments = narrate
ensure_model = narrate
