"""Qwen3-TTS wrapper for Apple Silicon (MPS backend)."""

import logging
import os
from typing import Callable

import numpy as np
import torch

from twinktalks.audio_utils import (
    generate_silence,
    get_duration_seconds,
    compute_chunk_offsets,
    silence_ms_after,
)
from twinktalks.chunker import Chunk
from twinktalks.config import (
    MODEL_ID,
    MODELSCOPE_ID,
    DEFAULT_SPEAKER,
    DEFAULT_LANGUAGE,
    DEFAULT_SPEED,
    ATTN_IMPL,
    MAX_NEW_TOKENS,
    TOP_K,
    TOP_P,
    TEMPERATURE,
    REPETITION_PENALTY,
    SAMPLE_RATE,
    detect_device,
    detect_dtype,
)

# Force HuggingFace to show download progress bars
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "info")

logger = logging.getLogger(__name__)


class SynthesisError(Exception):
    """Raised when TTS synthesis fails."""


class ModelDownloadError(Exception):
    """Raised when model download fails from all sources."""


class TTSEngine:
    """Wrapper around Qwen3-TTS CustomVoice model."""

    def __init__(
        self,
        model_id: str = MODEL_ID,
        speaker: str = DEFAULT_SPEAKER,
        device: str | None = None,
        model_path: str | None = None,
    ):
        self.model_id = model_id
        self.speaker = speaker
        self.device = device if device is not None else detect_device()
        self.model_path = model_path
        self.model = None

    def _load_from_path(self, path: str, dtype):
        """Load model from a local directory."""
        from qwen_tts import Qwen3TTSModel

        print(f"[TwinkTalks] Loading model from local path: {path}")
        self.model = Qwen3TTSModel.from_pretrained(
            path,
            device_map=self.device,
            dtype=dtype,
            attn_implementation=ATTN_IMPL,
        )

    def _load_from_huggingface(self, dtype):
        """Try loading from HuggingFace Hub."""
        from qwen_tts import Qwen3TTSModel

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

        print(f"[TwinkTalks] Downloading from HuggingFace: {self.model_id}")
        self.model = Qwen3TTSModel.from_pretrained(
            self.model_id,
            device_map=self.device,
            dtype=dtype,
            attn_implementation=ATTN_IMPL,
        )

    def _download_from_modelscope(self) -> str:
        """Download model from ModelScope and return the local path."""
        try:
            from modelscope import snapshot_download
        except ImportError:
            raise ModelDownloadError(
                "ModelScope fallback requires the 'modelscope' package.\n"
                "Install it with: pip install modelscope\n"
                "Then re-run TwinkTalks."
            )

        print(f"[TwinkTalks] Downloading from ModelScope: {MODELSCOPE_ID}")
        print("[TwinkTalks] This is an alternative source that doesn't require a HuggingFace account.")
        local_dir = snapshot_download(MODELSCOPE_ID)
        return local_dir

    def load_model(self):
        """Load the Qwen3-TTS model onto the specified device.

        Loading order:
        1. Local path (if --model-path was given)
        2. HuggingFace Hub (default, works without account for public models)
        3. ModelScope fallback (if HF fails with rate limit / auth errors)

        On first run, downloads ~3.5GB. Subsequent runs load from cache.
        """
        from qwen_tts import Qwen3TTSModel

        dtype_map = {"float16": torch.float16, "float32": torch.float32}
        dtype_name = detect_dtype(self.device)
        dtype = dtype_map[dtype_name]

        print(f"[TwinkTalks] Device: {self.device} | Dtype: {dtype_name} | Attn: {ATTN_IMPL}")
        logger.info("Loading model on %s...", self.device)

        # 1. Local path takes priority
        if self.model_path:
            from pathlib import Path
            p = Path(self.model_path).expanduser()
            if not p.is_dir():
                raise ModelDownloadError(f"Model path does not exist: {p}")
            self._load_from_path(str(p), dtype)
            self._post_load()
            return

        # 2. Try HuggingFace
        print(f"[TwinkTalks] First run downloads ~3.5GB — this may take a few minutes...")
        try:
            self._load_from_huggingface(dtype)
            self._post_load()
            return
        except Exception as hf_err:
            hf_msg = str(hf_err)
            is_rate_or_auth = any(
                s in hf_msg for s in ("429", "401", "403", "rate limit", "Too Many Requests",
                                       "Unauthorized", "Forbidden", "must be authenticated",
                                       "Access denied", "gated repo")
            )
            if not is_rate_or_auth:
                raise

            print(f"\n[TwinkTalks] HuggingFace download failed: {hf_msg}")
            print("[TwinkTalks] Trying ModelScope as fallback...")
            logger.warning("HuggingFace download failed (%s), trying ModelScope...", hf_msg)

        # 3. ModelScope fallback
        try:
            local_dir = self._download_from_modelscope()
            self._load_from_path(local_dir, dtype)
            self._post_load()
            return
        except ModelDownloadError:
            raise
        except Exception as ms_err:
            raise ModelDownloadError(
                f"Could not download the model from any source.\n\n"
                f"HuggingFace error: {hf_msg}\n"
                f"ModelScope error: {ms_err}\n\n"
                f"You can download the model manually and use --model-path:\n\n"
                f"  Option A — HuggingFace (requires free account):\n"
                f"    pip install -U 'huggingface_hub[cli]'\n"
                f"    huggingface-cli login\n"
                f"    huggingface-cli download {self.model_id} --local-dir ./model\n\n"
                f"  Option B — ModelScope (no account needed):\n"
                f"    pip install modelscope\n"
                f"    modelscope download --model {MODELSCOPE_ID} --local_dir ./model\n\n"
                f"Then run: twinktalks --model-path ./model your_file.pdf"
            ) from ms_err

    def _post_load(self):
        """Post-load setup: MPS sync and success message."""
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
        speaker: str | None = None,
    ) -> tuple[np.ndarray, int]:
        """Generate audio for a single text chunk.

        Args:
            speed: Speaking rate, 0.5 (slow) to 2.0 (fast). Default 1.0.
            instruct: Natural language instruction for voice style (e.g. "Speak calmly").
            speaker: Override the engine's default speaker for this call. The
                model is shared, so switching speakers does not reload weights.

        Returns:
            Tuple of (waveform as numpy array, sample rate).
        """
        if self.model is None:
            self.load_model()

        try:
            wavs, sr = self.model.generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker or self.speaker,
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
        speaker: str | None = None,
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
        speaker: str | None = None,
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

            # Incremental concatenation: append silence + new segment to cumulative
            if cumulative is None:
                cumulative = waveform
            else:
                prev_chunk = chunks[len(segments) - 2]
                silence = generate_silence(silence_ms_after(prev_chunk), sample_rate)
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
            parts.append(generate_silence(silence_ms_after(chunks[i]), sample_rate))

    return np.concatenate(parts)


