"""Audio concatenation, silence generation, and export utilities."""

from pathlib import Path

import numpy as np
import soundfile as sf

from twinktalks.config import SAMPLE_RATE


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
