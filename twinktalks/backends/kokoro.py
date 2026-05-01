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

# All Kokoro-82M-bf16 voices we know about. Voice id encodes language + gender:
#   first letter  → language (a=AmE, b=BrE, e=Spanish, f=French, h=Hindi,
#                   i=Italian, j=Japanese, p=Portuguese, z=Mandarin)
#   second letter → gender (f=female, m=male)
#   _suffix       → the speaker's name
# lang_code passed to model.generate is just voice_id[0].
_VOICES = [
    # American English
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa",
    # British English
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    # Spanish
    "ef_dora", "em_alex", "em_santa",
    # French
    "ff_siwis",
    # Hindi
    "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
    # Italian
    "if_sara", "im_nicola",
    # Japanese
    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo",
    # Portuguese (Brazilian)
    "pf_dora", "pm_alex", "pm_santa",
    # Mandarin
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
]


class KokoroBackend(TTSBackend):
    name = "kokoro"
    voices = list(_VOICES)
    default_voice = "af_heart"
    supported_languages = ["English"]  # tied to voice — UI hides this dropdown.
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
        # First letter of voice id is the Kokoro lang_code:
        # a=American, b=British, e=Spanish, f=French, h=Hindi, i=Italian,
        # j=Japanese, p=Portuguese, z=Mandarin.
        lang_code = v[0] if v and v[0] in "abefhijpz" else "a"
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
