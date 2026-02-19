"""Audio concatenation, silence generation, and export utilities."""

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from twinktalks.config import SAMPLE_RATE

logger = logging.getLogger(__name__)


@dataclass
class AudioChapter:
    """A chapter marker for embedding in MP3 files."""

    title: str
    start_ms: int
    end_ms: int


def generate_silence(duration_ms: int, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Create a silence array of the given duration."""
    num_samples = int(sample_rate * duration_ms / 1000)
    return np.zeros(num_samples, dtype=np.float32)


def concatenate_audio(
    segments: list[np.ndarray],
    silences_ms: list[int],
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Concatenate audio segments with silence gaps between them.

    Args:
        segments: List of audio waveform arrays.
        silences_ms: Silence duration (ms) after each segment. Length must be len(segments) - 1.
        sample_rate: Audio sample rate.
    """
    if not segments:
        return np.array([], dtype=np.float32)

    if len(segments) == 1:
        return segments[0]

    if len(silences_ms) != len(segments) - 1:
        raise ValueError(
            f"Expected {len(segments) - 1} silence values, got {len(silences_ms)}"
        )

    parts = []
    for i, seg in enumerate(segments):
        parts.append(seg)
        if i < len(silences_ms):
            parts.append(generate_silence(silences_ms[i], sample_rate))

    return np.concatenate(parts)


def save_audio(
    waveform: np.ndarray,
    output_path: str,
    sample_rate: int = SAMPLE_RATE,
) -> None:
    """Save waveform to WAV or MP3 file.

    Format is determined by file extension.
    MP3 requires ffmpeg to be installed.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ext = path.suffix.lower()

    if ext == ".wav":
        sf.write(str(path), waveform, sample_rate)
    elif ext == ".mp3":
        try:
            from pydub import AudioSegment

            # Convert numpy array to pydub AudioSegment
            audio_int16 = (waveform * 32767).astype(np.int16)
            audio_segment = AudioSegment(
                data=audio_int16.tobytes(),
                sample_width=2,
                frame_rate=sample_rate,
                channels=1,
            )
            audio_segment.export(str(path), format="mp3")
        except Exception as e:
            # Fallback to WAV if MP3 export fails
            wav_path = path.with_suffix(".wav")
            sf.write(str(wav_path), waveform, sample_rate)
            raise RuntimeError(
                f"MP3 export failed ({e}). Saved as WAV instead: {wav_path}"
            )
    else:
        raise ValueError(f"Unsupported format: {ext}. Use .wav or .mp3")


def get_duration_seconds(waveform: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float:
    """Get the duration of a waveform in seconds."""
    return len(waveform) / sample_rate


def compute_chunk_offsets(
    segments: list[np.ndarray],
    chunks: list,
    sample_rate: int,
) -> list[int]:
    """Compute the start time offset (in ms) of each segment in the concatenated waveform.

    Args:
        segments: List of audio waveform arrays.
        chunks: List of Chunk objects (needs is_paragraph_end attribute).
        sample_rate: Audio sample rate.

    Returns:
        List of start offsets in milliseconds, one per segment.
    """
    from twinktalks.config import INTER_SENTENCE_SILENCE_MS, INTER_PARAGRAPH_SILENCE_MS

    offsets = []
    cumulative_samples = 0

    for i, seg in enumerate(segments):
        offset_ms = int(cumulative_samples * 1000 / sample_rate)
        offsets.append(offset_ms)
        cumulative_samples += len(seg)
        if i < len(segments) - 1:
            silence_ms = (
                INTER_PARAGRAPH_SILENCE_MS
                if chunks[i].is_paragraph_end
                else INTER_SENTENCE_SILENCE_MS
            )
            silence_samples = int(sample_rate * silence_ms / 1000)
            cumulative_samples += silence_samples

    return offsets


def add_chapter_markers(mp3_path: str, chapters: list[AudioChapter]) -> None:
    """Embed ID3v2 chapter markers (CHAP + CTOC frames) into an MP3 file.

    Requires mutagen. If mutagen is not installed, logs a warning and returns.
    """
    if not chapters:
        return

    try:
        from mutagen.id3 import ID3, CHAP, CTOC, TIT2, CTOCFlags
    except ImportError:
        logger.warning(
            "mutagen not installed — cannot embed chapter markers. "
            "Install with: pip install mutagen"
        )
        return

    path = Path(mp3_path)
    if not path.exists() or path.suffix.lower() != ".mp3":
        raise ValueError(f"Expected existing .mp3 file, got: {mp3_path}")

    tags = ID3(str(path))

    child_ids = []
    for i, ch in enumerate(chapters):
        chap_id = f"chap{i}"
        child_ids.append(chap_id)
        tags.add(CHAP(
            element_id=chap_id,
            start_time=ch.start_ms,
            end_time=ch.end_ms,
            sub_frames=[TIT2(encoding=3, text=[ch.title])],
        ))

    tags.add(CTOC(
        element_id="toc",
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=child_ids,
        sub_frames=[TIT2(encoding=3, text=["Table of Contents"])],
    ))

    tags.save(str(path))
