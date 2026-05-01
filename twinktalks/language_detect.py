"""Detect document language and map it to Qwen3-TTS language names."""

import logging

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "English"

# langdetect codes → Qwen3-TTS language name. Codes outside this mapping
# fall back to English; the model still synthesizes intelligibly.
_LANG_MAP = {
    "en": "English",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "de": "German",
    "fr": "French",
    "ru": "Russian",
    "pt": "Portuguese",
    "es": "Spanish",
    "it": "Italian",
}


def detect_language(text: str, sample_chars: int = 500) -> str:
    """Return the Qwen3-TTS language name guessed from the first chars of text.

    Defaults to English on detector failure, missing dependency, or unmapped code.
    """
    if not text or not text.strip():
        return DEFAULT_LANGUAGE

    sample = text[:sample_chars].strip()
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0  # deterministic across runs
        code = detect(sample)
    except ImportError:
        logger.warning(
            "langdetect not installed — auto-detection disabled. "
            "Install with: pip install langdetect"
        )
        return DEFAULT_LANGUAGE
    except Exception as e:
        logger.warning("Language detection failed: %s", e)
        return DEFAULT_LANGUAGE

    return _LANG_MAP.get(code, DEFAULT_LANGUAGE)


def resolve_language(requested: str, text: str) -> str:
    """If the user asked for 'Auto', detect from text. Otherwise pass through."""
    if requested and requested.strip().lower() == "auto":
        return detect_language(text)
    return requested
