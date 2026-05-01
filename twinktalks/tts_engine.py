"""High-level TTS orchestrator.

The actual model-specific code lives in twinktalks/backends/. This module
turns a `TTSBackend` into the chunked, retried, streaming engine the rest of
the app expects. Backend selection (Qwen vs Kokoro) happens at construction
time via twinktalks.backends.get_backend.
"""

import logging
import os
from pathlib import Path
from typing import Callable

# Redirect HuggingFace + ModelScope caches into ~/.twinktalks/cache so the
# multi-GB weights live next to the rest of TwinkTalks' state instead of
# polluting the global ~/.cache/huggingface tree. Set BEFORE the first
# transformers / huggingface_hub import — they read these on module load.
_TT_CACHE = Path.home() / ".twinktalks" / "cache"
_TT_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(_TT_CACHE / "huggingface"))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(_TT_CACHE / "huggingface" / "hub"))
os.environ.setdefault("MODELSCOPE_CACHE", str(_TT_CACHE / "modelscope"))
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "warning")

import numpy as np

from twinktalks.audio_utils import (
    compute_chunk_offsets,
    generate_silence,
    silence_ms_after,
)
from twinktalks.backends import (
    ModelDownloadError,
    SynthesisError,
    TTSBackend,
    get_backend,
)
from twinktalks.chunker import Chunk
from twinktalks.config import (
    DEFAULT_LANGUAGE,
    DEFAULT_SPEED,
    SAMPLE_RATE,
)

logger = logging.getLogger(__name__)


class TTSEngine:
    """Wraps a backend with chunking, retry, streaming, and session-resume.

    Construction options:
        backend: a TTSBackend instance, or a name ('qwen' / 'kokoro'), or None
                 to pick the first available backend.
        speaker: backend-specific voice ID. None = backend's default.
        device, model_path: passed through to the Qwen backend; ignored elsewhere.
    """

    def __init__(
        self,
        backend: TTSBackend | str | None = None,
        speaker: str | None = None,
        device: str | None = None,
        model_path: str | None = None,
    ):
        if isinstance(backend, TTSBackend):
            self.backend = backend
        else:
            kwargs: dict = {}
            if device is not None:
                kwargs["device"] = device
            if model_path is not None:
                kwargs["model_path"] = model_path
            self.backend = get_backend(backend, **kwargs)
        self.speaker = speaker or self.backend.default_voice

    # Compatibility shim: callers (and tests) check `engine.model` to see
    # whether weights are in memory yet.
    @property
    def model(self):
        return self.backend.model

    def load_model(self) -> None:
        self.backend.load_model()

    @property
    def device(self) -> str:
        return getattr(self.backend, "device", "cpu")

    @property
    def model_path(self) -> str | None:
        return getattr(self.backend, "model_path", None)

    # --- Single-chunk synthesis --------------------------------------------

    def synthesize(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        speed: float = DEFAULT_SPEED,
        instruct: str = "",
        speaker: str | None = None,
    ) -> tuple[np.ndarray, int]:
        return self.backend.synthesize_one(
            text,
            voice=speaker or self.speaker,
            speed=speed,
            instruct=instruct,
            language=language,
        )

    # --- Chunk-by-chunk + streaming ----------------------------------------

    def synthesize_chunks(
        self,
        chunks: list[Chunk],
        language: str = DEFAULT_LANGUAGE,
        speed: float = DEFAULT_SPEED,
        instruct: str = "",
        progress_callback: Callable[[int, int], None] | None = None,
        session_dir: "Path | None" = None,
        start_from: int = 0,
        speaker: str | None = None,
    ) -> tuple[np.ndarray, int, list[int]]:
        if not chunks:
            return np.array([], dtype=np.float32), SAMPLE_RATE, []

        segments: list[np.ndarray] = []
        sample_rate = SAMPLE_RATE
        max_retries = 3

        if session_dir and start_from > 0:
            import soundfile as sf
            for i in range(start_from):
                chunk_path = session_dir / f"chunk_{i:04d}.wav"
                if chunk_path.exists():
                    data, sr = sf.read(str(chunk_path))
                    segments.append(data.astype(np.float32))
                    sample_rate = sr

        for i in range(start_from, len(chunks)):
            chunk = chunks[i]
            if progress_callback:
                progress_callback(i + 1, len(chunks))

            waveform = None
            for attempt in range(max_retries):
                try:
                    waveform, sample_rate = self.synthesize(
                        chunk.text, language, speed, instruct, speaker=speaker,
                    )
                    break
                except SynthesisError:
                    if attempt < max_retries - 1:
                        logger.warning(
                            "Chunk %d/%d failed (attempt %d/%d), retrying...",
                            i + 1, len(chunks), attempt + 1, max_retries,
                        )
                    else:
                        logger.error(
                            "Chunk %d/%d failed after %d attempts, inserting silence.",
                            i + 1, len(chunks), max_retries,
                        )

            if waveform is None:
                waveform = generate_silence(1000, sample_rate)

            if session_dir:
                import soundfile as sf
                chunk_path = session_dir / f"chunk_{i:04d}.wav"
                sf.write(str(chunk_path), waveform, sample_rate)

            segments.append(waveform)

        offsets = compute_chunk_offsets(segments, chunks, sample_rate)
        return _concatenate_segments(segments, chunks, sample_rate), sample_rate, offsets

    def synthesize_chunks_streaming(
        self,
        chunks: list[Chunk],
        language: str = DEFAULT_LANGUAGE,
        speed: float = DEFAULT_SPEED,
        instruct: str = "",
        session_dir: "Path | None" = None,
        start_from: int = 0,
        speaker: str | None = None,
    ):
        if not chunks:
            return

        segments: list[np.ndarray] = []
        sample_rate = SAMPLE_RATE
        max_retries = 3
        cumulative: np.ndarray | None = None

        if session_dir and start_from > 0:
            import soundfile as sf
            for i in range(start_from):
                chunk_path = session_dir / f"chunk_{i:04d}.wav"
                if chunk_path.exists():
                    data, sr = sf.read(str(chunk_path))
                    segments.append(data.astype(np.float32))
                    sample_rate = sr
            if segments:
                cumulative = _concatenate_segments(segments, chunks[:len(segments)], sample_rate)

        for i in range(start_from, len(chunks)):
            chunk = chunks[i]

            waveform = None
            for attempt in range(max_retries):
                try:
                    waveform, sample_rate = self.synthesize(
                        chunk.text, language, speed, instruct, speaker=speaker,
                    )
                    break
                except SynthesisError:
                    if attempt < max_retries - 1:
                        logger.warning(
                            "Chunk %d/%d failed (attempt %d/%d), retrying...",
                            i + 1, len(chunks), attempt + 1, max_retries,
                        )
                    else:
                        logger.error(
                            "Chunk %d/%d failed after %d attempts, inserting silence.",
                            i + 1, len(chunks), max_retries,
                        )

            if waveform is None:
                waveform = generate_silence(1000, sample_rate)

            if session_dir:
                import soundfile as sf
                chunk_path = session_dir / f"chunk_{i:04d}.wav"
                sf.write(str(chunk_path), waveform, sample_rate)

            segments.append(waveform)

            if cumulative is None:
                cumulative = waveform
            else:
                prev_chunk = chunks[len(segments) - 2]
                silence = generate_silence(silence_ms_after(prev_chunk), sample_rate)
                cumulative = np.concatenate([cumulative, silence, waveform])

            is_final = i + 1 == len(chunks)
            offsets = (
                compute_chunk_offsets(segments, chunks[:len(segments)], sample_rate)
                if is_final else None
            )
            yield cumulative, sample_rate, i + 1, len(chunks), offsets


def _concatenate_segments(
    segments: list[np.ndarray],
    chunks: list[Chunk],
    sample_rate: int,
) -> np.ndarray:
    if len(segments) == 1:
        return segments[0]
    parts = []
    for i, seg in enumerate(segments):
        parts.append(seg)
        if i < len(segments) - 1:
            parts.append(generate_silence(silence_ms_after(chunks[i]), sample_rate))
    return np.concatenate(parts)


__all__ = [
    "TTSEngine",
    "SynthesisError",
    "ModelDownloadError",
    "_concatenate_segments",
]
