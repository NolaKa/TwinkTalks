"""Kokoro-82M backend via mlx-audio.

82-million-parameter model (~360 MB on disk, ~1.5 GB RAM at inference).
Order of magnitude faster than Qwen3-TTS-1.7B but English only and no
natural-language instruct prompts. Optimized for Apple Silicon via MLX.
"""

import logging
import os
from pathlib import Path

import numpy as np

from twinktalks.backends.base import (
    ModelDownloadError,
    SynthesisError,
    TTSBackend,
)

logger = logging.getLogger(__name__)


# Repo on the HuggingFace Hub. mlx-audio's load_model takes the same identifier.
KOKORO_MODEL_ID = "mlx-community/Kokoro-82M-bf16"

# Subset of the 50+ Kokoro voices — mix of American + British, female + male.
# Voice id prefix encodes both: a/b = American/British, f/m = female/male.
_VOICES = [
    "af_heart",   # American female
    "af_bella",
    "af_nicole",
    "af_sky",
    "am_adam",    # American male
    "am_echo",
    "am_michael",
    "bf_alice",   # British female
    "bm_george",  # British male
]


class KokoroBackend(TTSBackend):
    name = "kokoro"
    voices = list(_VOICES)
    default_voice = "af_heart"
    supported_languages = ["English"]  # Kokoro is English-only.
    default_language = "English"
    supports_instruct = False
    sample_rate = 24000

    def __init__(self, model_id: str = KOKORO_MODEL_ID):
        self.model_id = model_id
        self.model = None

    @classmethod
    def is_cached(cls) -> bool:
        candidates = [
            Path(os.environ["HUGGINGFACE_HUB_CACHE"])
            if os.environ.get("HUGGINGFACE_HUB_CACHE") else None,
            Path.home() / ".twinktalks" / "cache" / "huggingface" / "hub",
            Path.home() / ".cache" / "huggingface" / "hub",
        ]
        target = "models--mlx-community--Kokoro-82M-bf16"
        for cache in candidates:
            if cache and (cache / target).exists():
                return True
        return False

    def load_model(self) -> None:
        try:
            from mlx_audio.tts.utils import load_model as mlx_load
        except ImportError as e:
            raise ModelDownloadError(
                "Kokoro requires the 'mlx-audio' package.\n"
                "Install with: pip install -e .[kokoro]\n"
                "(this will upgrade transformers and break the qwen backend in the same venv —\n"
                "use a separate venv if you want both)"
            ) from e

        print(f"[TwinkTalks] Loading Kokoro: {self.model_id}")
        try:
            self.model = mlx_load(self.model_id)
        except Exception as e:
            raise ModelDownloadError(f"Could not load Kokoro: {e}") from e
        # Pre-fetch the misaki text-processing data the first generate call
        # would otherwise trigger silently.
        print("[TwinkTalks] Kokoro model loaded.")
        logger.info("Kokoro model loaded successfully.")

    def synthesize_one(
        self, text, *, voice, speed=1.0, instruct="", language="",
    ) -> tuple[np.ndarray, int]:
        if self.model is None:
            self.load_model()
        v = voice or self.default_voice
        # Voice prefix encodes language variant: bf_/bm_ → British, else American.
        lang_code = "b" if v.startswith(("bf_", "bm_")) else "a"
        try:
            chunks = []
            for result in self.model.generate(
                text=text, voice=v, speed=speed, lang_code=lang_code,
            ):
                chunks.append(np.array(result.audio, dtype=np.float32))
        except Exception as e:
            raise SynthesisError(f"Kokoro generation failed: {e}") from e
        if not chunks:
            raise SynthesisError("Kokoro produced no audio.")
        waveform = np.concatenate(chunks).astype(np.float32)
        return waveform, self.sample_rate
