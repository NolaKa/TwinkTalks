"""TTS backend selector. Detects which backends' Python deps are installed
and returns one on demand. Designed so the rest of the code never has to
care which model is doing the work."""

import logging
import os

from twinktalks.backends.base import (
    ModelDownloadError,
    SynthesisError,
    TTSBackend,
)

logger = logging.getLogger(__name__)


def _qwen_available() -> bool:
    try:
        import qwen_tts  # noqa: F401
        return True
    except Exception:
        return False


def _kokoro_available() -> bool:
    try:
        import mlx_audio  # noqa: F401
        return True
    except Exception:
        return False


def detect_available() -> list[str]:
    """Return the list of backend names whose Python deps import cleanly."""
    names: list[str] = []
    if _qwen_available():
        names.append("qwen")
    if _kokoro_available():
        names.append("kokoro")
    return names


def default_backend_name() -> str | None:
    """First available backend, honoring TWINKTALKS_BACKEND if it points at
    a backend whose deps are installed."""
    pref = (os.environ.get("TWINKTALKS_BACKEND") or "").strip().lower()
    available = detect_available()
    if pref and pref in available:
        return pref
    return available[0] if available else None


def get_backend(name: str | None = None, **kwargs) -> TTSBackend:
    """Instantiate a backend by name (or the first available one)."""
    available = detect_available()
    if not available:
        raise ModelDownloadError(
            "No TTS backend installed. Pick one:\n"
            "  pip install -e .[qwen]    # multilingual + instruct, ~3.5 GB model\n"
            "  pip install -e .[kokoro]  # English only, ~360 MB model, much faster"
        )
    chosen = (name or default_backend_name() or "").strip().lower()
    if chosen and chosen not in available:
        raise ModelDownloadError(
            f"Backend '{chosen}' is not installed. Available: {', '.join(available)}.\n"
            f"Install with: pip install -e .[{chosen}]"
        )
    if not chosen:
        chosen = available[0]

    if chosen == "qwen":
        from twinktalks.backends.qwen import QwenBackend
        return QwenBackend(**kwargs)
    if chosen == "kokoro":
        from twinktalks.backends.kokoro import KokoroBackend
        # Kokoro doesn't accept device / model_path kwargs — drop them silently.
        kwargs.pop("device", None)
        kwargs.pop("model_path", None)
        return KokoroBackend(**kwargs)

    raise ModelDownloadError(f"Unknown backend: {chosen}")


__all__ = [
    "TTSBackend",
    "SynthesisError",
    "ModelDownloadError",
    "detect_available",
    "default_backend_name",
    "get_backend",
]
