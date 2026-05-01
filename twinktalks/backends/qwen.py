"""Qwen3-TTS-12Hz-1.7B-CustomVoice backend.

Multilingual (10+ languages), supports natural-language instruct prompts,
voice cloning. ~3.5 GB on disk, ~6-10 GB RAM at inference time.
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
from twinktalks.config import (
    AVAILABLE_SPEAKERS,
    ATTN_IMPL,
    DEFAULT_LANGUAGE,
    MAX_NEW_TOKENS,
    MODEL_ID,
    MODELSCOPE_ID,
    REPETITION_PENALTY,
    SAMPLE_RATE,
    TEMPERATURE,
    TOP_K,
    TOP_P,
    detect_device,
    detect_dtype,
)

logger = logging.getLogger(__name__)


class QwenBackend(TTSBackend):
    name = "qwen"
    voices = list(AVAILABLE_SPEAKERS)
    default_voice = "aiden"
    supported_languages = [
        "English", "Chinese", "Japanese", "Korean", "German",
        "French", "Russian", "Portuguese", "Spanish", "Italian",
    ]
    default_language = DEFAULT_LANGUAGE
    supports_instruct = True
    sample_rate = SAMPLE_RATE

    def __init__(self, device: str | None = None, model_path: str | None = None):
        self.device = device if device is not None else detect_device()
        self.model_path = model_path
        self.model = None

    @classmethod
    def is_cached(cls) -> bool:
        custom = os.environ.get("TWINKTALKS_MODEL_PATH")
        if custom:
            return Path(custom).expanduser().is_dir()
        candidates = [
            Path(os.environ["HUGGINGFACE_HUB_CACHE"])
            if os.environ.get("HUGGINGFACE_HUB_CACHE") else None,
            Path.home() / ".twinktalks" / "cache" / "huggingface" / "hub",
            Path.home() / ".cache" / "huggingface" / "hub",
        ]
        target = "models--Qwen--Qwen3-TTS-12Hz-1.7B-CustomVoice"
        for cache in candidates:
            if cache and (cache / target).exists():
                return True
        ms_candidates = [
            Path(os.environ["MODELSCOPE_CACHE"])
            if os.environ.get("MODELSCOPE_CACHE") else None,
            Path.home() / ".twinktalks" / "cache" / "modelscope",
            Path.home() / ".cache" / "modelscope" / "hub",
        ]
        for cache in ms_candidates:
            if cache and (cache / "Qwen" / "Qwen3-TTS-12Hz-1.7B-CustomVoice").exists():
                return True
        return False

    # --- Model loading ------------------------------------------------------

    def _torch_dtype(self):
        import torch
        return torch.float16 if detect_dtype(self.device) == "float16" else torch.float32

    def _load_from_path(self, path: str, dtype) -> None:
        from qwen_tts import Qwen3TTSModel
        print(f"[TwinkTalks] Loading Qwen model from local path: {path}")
        self.model = Qwen3TTSModel.from_pretrained(
            path, device_map=self.device, dtype=dtype, attn_implementation=ATTN_IMPL,
        )

    def _load_from_huggingface(self, dtype) -> None:
        from qwen_tts import Qwen3TTSModel
        try:
            import huggingface_hub
            huggingface_hub.logging.set_verbosity_info()
        except Exception:
            pass
        try:
            import transformers
            transformers.logging.set_verbosity_info()
        except Exception:
            pass
        print(f"[TwinkTalks] Downloading Qwen from HuggingFace: {MODEL_ID}")
        self.model = Qwen3TTSModel.from_pretrained(
            MODEL_ID, device_map=self.device, dtype=dtype, attn_implementation=ATTN_IMPL,
        )

    def _download_from_modelscope(self) -> str:
        try:
            from modelscope import snapshot_download
        except ImportError:
            raise ModelDownloadError(
                "ModelScope fallback requires the 'modelscope' package.\n"
                "Install it with: pip install modelscope"
            )
        print(f"[TwinkTalks] Downloading Qwen from ModelScope: {MODELSCOPE_ID}")
        return snapshot_download(MODELSCOPE_ID)

    def load_model(self) -> None:
        import torch
        dtype = self._torch_dtype()
        dtype_name = detect_dtype(self.device)
        print(f"[TwinkTalks] Device: {self.device} | Dtype: {dtype_name} | Attn: {ATTN_IMPL}")
        logger.info("Loading Qwen model on %s...", self.device)

        if self.model_path:
            p = Path(self.model_path).expanduser()
            if not p.is_dir():
                raise ModelDownloadError(f"Model path does not exist: {p}")
            self._load_from_path(str(p), dtype)
            self._post_load()
            return

        print("[TwinkTalks] First run downloads ~3.5GB — this may take a few minutes...")
        try:
            self._load_from_huggingface(dtype)
            self._post_load()
            return
        except Exception as hf_err:
            hf_msg = str(hf_err)
            is_rate_or_auth = any(
                s in hf_msg for s in (
                    "429", "401", "403", "rate limit", "Too Many Requests",
                    "Unauthorized", "Forbidden", "must be authenticated",
                    "Access denied", "gated repo",
                )
            )
            if not is_rate_or_auth:
                raise
            print(f"\n[TwinkTalks] HuggingFace download failed: {hf_msg}")
            print("[TwinkTalks] Trying ModelScope as fallback...")
            logger.warning("HuggingFace download failed (%s), trying ModelScope...", hf_msg)

        try:
            local_dir = self._download_from_modelscope()
            self._load_from_path(local_dir, dtype)
            self._post_load()
        except ModelDownloadError:
            raise
        except Exception as ms_err:
            raise ModelDownloadError(
                f"Could not download Qwen from any source.\n"
                f"HuggingFace error: {hf_msg}\n"
                f"ModelScope error: {ms_err}"
            ) from ms_err
        return
        # unreachable; kept to mirror original control flow
        del torch  # noqa

    def _post_load(self) -> None:
        try:
            import torch
            if self.device == "mps" and torch.backends.mps.is_available():
                torch.mps.synchronize()
        except Exception:
            pass
        try:
            import transformers
            transformers.logging.set_verbosity_warning()
        except Exception:
            pass
        print("[TwinkTalks] Qwen model loaded.")
        logger.info("Qwen model loaded successfully.")

    # --- Synthesis ----------------------------------------------------------

    def synthesize_one(
        self, text, *, voice, speed=1.0, instruct="", language="",
    ) -> tuple[np.ndarray, int]:
        if self.model is None:
            self.load_model()
        # Qwen speakers are lowercase IDs — defensively lowercase in case an
        # old saved preset shows up with capitalized "Aiden".
        speaker = (voice or self.default_voice).lower()
        try:
            wavs, sr = self.model.generate_custom_voice(
                text=text,
                language=language or self.default_language,
                speaker=speaker,
                speed=speed,
                instruct=instruct,
                max_new_tokens=MAX_NEW_TOKENS,
                top_k=TOP_K, top_p=TOP_P,
                temperature=TEMPERATURE, repetition_penalty=REPETITION_PENALTY,
            )
            return wavs[0], sr
        except RuntimeError as e:
            raise SynthesisError(f"Qwen TTS generation failed: {e}") from e
