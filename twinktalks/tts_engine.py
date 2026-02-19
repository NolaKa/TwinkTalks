"""Qwen3-TTS wrapper for Apple Silicon (MPS backend)."""

import logging
import os
from typing import Callable

import numpy as np
import torch

from twinktalks.audio_utils import generate_silence, get_duration_seconds, compute_chunk_offsets
from twinktalks.chunker import Chunk
from twinktalks.config import (
    MODEL_ID,
    DEFAULT_SPEAKER,
    DEFAULT_LANGUAGE,
    DEFAULT_SPEED,
    DEVICE,
    DTYPE,
    ATTN_IMPL,
    MAX_NEW_TOKENS,
    TOP_K,
    TOP_P,
    TEMPERATURE,
    REPETITION_PENALTY,
    SAMPLE_RATE,
    INTER_SENTENCE_SILENCE_MS,
    INTER_PARAGRAPH_SILENCE_MS,
)

# Force HuggingFace to show download progress bars
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "info")

logger = logging.getLogger(__name__)


class SynthesisError(Exception):
    """Raised when TTS synthesis fails."""


class TTSEngine:
    """Wrapper around Qwen3-TTS CustomVoice model."""

    def __init__(
        self,
        model_id: str = MODEL_ID,
        speaker: str = DEFAULT_SPEAKER,
        device: str = DEVICE,
    ):
        self.model_id = model_id
        self.speaker = speaker
        self.device = device
        self.model = None

    def load_model(self):
        """Load the Qwen3-TTS model onto the specified device.

        On first run, downloads ~3.5GB from HuggingFace (with progress bar).
        Subsequent runs load from cache (~/.cache/huggingface/).
        """
        from qwen_tts import Qwen3TTSModel

        dtype_map = {"float16": torch.float16, "float32": torch.float32}
        dtype = dtype_map.get(DTYPE, torch.float16)

        print(f"[TwinkTalks] Loading model: {self.model_id}")
        print(f"[TwinkTalks] Device: {self.device} | Dtype: {DTYPE} | Attn: {ATTN_IMPL}")
        print(f"[TwinkTalks] First run downloads ~3.5GB — this may take a few minutes...")
        print(f"[TwinkTalks] Progress bar should appear below. If stuck, check your network.")
        logger.info("Loading model %s on %s...", self.model_id, self.device)

        # Enable HuggingFace download logging
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

        self.model = Qwen3TTSModel.from_pretrained(
            self.model_id,
            device_map=self.device,
            dtype=dtype,
            attn_implementation=ATTN_IMPL,
        )

        # Sync MPS device after loading
        if self.device == "mps" and torch.backends.mps.is_available():
            torch.mps.synchronize()

        print("[TwinkTalks] Model loaded successfully!")
        logger.info("Model loaded successfully.")

    def synthesize(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        speed: float = DEFAULT_SPEED,
        instruct: str = "",
    ) -> tuple[np.ndarray, int]:
        """Generate audio for a single text chunk.

        Args:
            speed: Speaking rate, 0.5 (slow) to 2.0 (fast). Default 1.0.
            instruct: Natural language instruction for voice style (e.g. "Speak calmly").

        Returns:
            Tuple of (waveform as numpy array, sample rate).
        """
        if self.model is None:
            self.load_model()

        try:
            wavs, sr = self.model.generate_custom_voice(
                text=text,
                language=language,
                speaker=self.speaker,
                speed=speed,
                instruct=instruct,
                max_new_tokens=MAX_NEW_TOKENS,
                top_k=TOP_K,
                top_p=TOP_P,
                temperature=TEMPERATURE,
                repetition_penalty=REPETITION_PENALTY,
            )
            return wavs[0], sr
        except RuntimeError as e:
            raise SynthesisError(f"TTS generation failed: {e}") from e

    def synthesize_chunks(
        self,
        chunks: list[Chunk],
        language: str = DEFAULT_LANGUAGE,
        speed: float = DEFAULT_SPEED,
        instruct: str = "",
        progress_callback: Callable[[int, int], None] | None = None,
        session_dir: "Path | None" = None,
        start_from: int = 0,
    ) -> tuple[np.ndarray, int, list[int]]:
        """Generate audio for all chunks and concatenate.

        Args:
            chunks: List of text chunks to synthesize.
            language: Language hint for the model.
            speed: Speaking rate (0.5-2.0).
            progress_callback: Called with (current_chunk, total_chunks).
            session_dir: If set, save each chunk as WAV for resume support.
            start_from: Resume from this chunk index.

        Returns:
            Tuple of (concatenated waveform, sample rate, chunk_offsets_ms).
        """
        if not chunks:
            return np.array([], dtype=np.float32), SAMPLE_RATE, []

        segments: list[np.ndarray] = []
        sample_rate = SAMPLE_RATE
        max_retries = 3

        # Load previously saved chunks if resuming
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
                    waveform, sample_rate = self.synthesize(chunk.text, language, speed, instruct)
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
                # Insert 1 second of silence as placeholder for failed chunk
                waveform = generate_silence(1000, sample_rate)

            # Save chunk for session resume
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
    ):
        """Generate audio chunk by chunk, yielding cumulative waveform after each.

        Uses incremental concatenation (O(n) total) instead of rebuilding
        from scratch each iteration.

        Yields:
            Tuple of (cumulative_waveform, sample_rate, chunk_index, total_chunks, chunk_offsets_ms).
            chunk_offsets_ms is None for intermediate yields and a list[int] for the final yield.
        """
        if not chunks:
            return

        segments: list[np.ndarray] = []
        sample_rate = SAMPLE_RATE
        max_retries = 3
        cumulative: np.ndarray | None = None

        # Load previously saved chunks if resuming
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
                    waveform, sample_rate = self.synthesize(chunk.text, language, speed, instruct)
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

            # Incremental concatenation: append silence + new segment to cumulative
            if cumulative is None:
                cumulative = waveform
            else:
                prev_chunk = chunks[len(segments) - 2]
                silence_ms = (
                    INTER_PARAGRAPH_SILENCE_MS
                    if prev_chunk.is_paragraph_end
                    else INTER_SENTENCE_SILENCE_MS
                )
                silence = generate_silence(silence_ms, sample_rate)
                cumulative = np.concatenate([cumulative, silence, waveform])

            is_final = i + 1 == len(chunks)
            offsets = compute_chunk_offsets(segments, chunks[:len(segments)], sample_rate) if is_final else None
            yield cumulative, sample_rate, i + 1, len(chunks), offsets


def _concatenate_segments(
    segments: list[np.ndarray],
    chunks: list[Chunk],
    sample_rate: int,
) -> np.ndarray:
    """Concatenate audio segments with silence gaps between them."""
    if len(segments) == 1:
        return segments[0]

    parts = []
    for i, seg in enumerate(segments):
        parts.append(seg)
        if i < len(segments) - 1:
            silence_ms = (
                INTER_PARAGRAPH_SILENCE_MS
                if chunks[i].is_paragraph_end
                else INTER_SENTENCE_SILENCE_MS
            )
            parts.append(generate_silence(silence_ms, sample_rate))

    return np.concatenate(parts)


