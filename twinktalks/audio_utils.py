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


def silence_ms_after(prev_chunk) -> int:
    """Silence (ms) to insert after a chunk before the next one.

    Single source of truth shared by concatenation and offset computation —
    keeping these in lockstep is required for chapter markers to land correctly.
    """
    from twinktalks.config import INTER_SENTENCE_SILENCE_MS, INTER_PARAGRAPH_SILENCE_MS
    return INTER_PARAGRAPH_SILENCE_MS if prev_chunk.is_paragraph_end else INTER_SENTENCE_SILENCE_MS


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


class MP3ExportError(RuntimeError):
    """Raised when MP3/M4B encoding fails (e.g. ffmpeg missing)."""


def _waveform_to_audio_segment(waveform: np.ndarray, sample_rate: int):
    """Convert a float32 waveform to a pydub AudioSegment (16-bit mono)."""
    from pydub import AudioSegment

    audio_int16 = (np.clip(waveform, -1.0, 1.0) * 32767).astype(np.int16)
    return AudioSegment(
        data=audio_int16.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=1,
    )


def save_audio(
    waveform: np.ndarray,
    output_path: str,
    sample_rate: int = SAMPLE_RATE,
) -> None:
    """Save waveform to WAV, MP3, or M4B file.

    Format is determined by file extension.
    MP3 and M4B require ffmpeg; on failure, raises MP3ExportError without
    writing a side-file. Callers decide whether to retry as WAV.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ext = path.suffix.lower()

    if ext == ".wav":
        sf.write(str(path), waveform, sample_rate)
    elif ext == ".mp3":
        try:
            seg = _waveform_to_audio_segment(waveform, sample_rate)
            seg.export(str(path), format="mp3")
        except Exception as e:
            raise MP3ExportError(
                f"MP3 export failed ({e}). Install ffmpeg, or save with a .wav extension."
            ) from e
    elif ext == ".m4b":
        # M4B is the audiobook variant of M4A — same MP4/AAC container, .m4b
        # extension signals "audiobook" to iOS Books, Apple Podcasts, etc.
        # pydub format="ipod" produces an MP4 container with AAC audio.
        try:
            seg = _waveform_to_audio_segment(waveform, sample_rate)
            seg.export(str(path), format="ipod", codec="aac")
        except Exception as e:
            raise MP3ExportError(
                f"M4B export failed ({e}). Install ffmpeg, or save with a .wav extension."
            ) from e
    else:
        raise ValueError(f"Unsupported format: {ext}. Use .wav, .mp3, or .m4b")


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
    offsets = []
    cumulative_samples = 0

    for i, seg in enumerate(segments):
        offset_ms = int(cumulative_samples * 1000 / sample_rate)
        offsets.append(offset_ms)
        cumulative_samples += len(seg)
        if i < len(segments) - 1:
            silence_ms = silence_ms_after(chunks[i])
            silence_samples = int(sample_rate * silence_ms / 1000)
            cumulative_samples += silence_samples

    return offsets


def embed_metadata(audio_path: str, metadata) -> None:
    """Tag an MP3 or M4B file with title, author, album, and cover art.

    Silently skips fields that are missing on the BookMetadata. No-op for WAV.

    Args:
        metadata: BookMetadata-like object with .title, .author, .cover_image, .cover_mime.
    """
    path = Path(audio_path)
    if not path.exists():
        raise ValueError(f"Audio file does not exist: {audio_path}")

    ext = path.suffix.lower()
    if ext == ".mp3":
        _embed_mp3(path, metadata)
    elif ext == ".m4b":
        _embed_m4b(path, metadata)
    elif ext == ".wav":
        return  # WAV has no standard metadata container we use
    else:
        raise ValueError(f"Cannot embed metadata in {ext}")


def _embed_mp3(path: Path, metadata) -> None:
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, APIC
    except ImportError:
        logger.warning("mutagen not installed — skipping MP3 metadata embedding.")
        return

    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        tags = ID3()

    if metadata.title:
        tags.add(TIT2(encoding=3, text=[metadata.title]))
        tags.add(TALB(encoding=3, text=[metadata.title]))
    if metadata.author:
        tags.add(TPE1(encoding=3, text=[metadata.author]))
    if metadata.has_cover():
        tags.add(APIC(
            encoding=3,
            mime=metadata.cover_mime,
            type=3,  # front cover
            desc="Cover",
            data=metadata.cover_image,
        ))
    tags.save(str(path))


def _embed_m4b(path: Path, metadata) -> None:
    try:
        from mutagen.mp4 import MP4, MP4Cover
    except ImportError:
        logger.warning("mutagen not installed — skipping M4B metadata embedding.")
        return

    audio = MP4(str(path))
    tags = audio.tags
    if tags is None:
        audio.add_tags()
        tags = audio.tags

    if metadata.title:
        tags["\xa9nam"] = [metadata.title]
        tags["\xa9alb"] = [metadata.title]
    if metadata.author:
        tags["\xa9ART"] = [metadata.author]
    if metadata.has_cover():
        cover_format = (
            MP4Cover.FORMAT_PNG if metadata.cover_mime == "image/png"
            else MP4Cover.FORMAT_JPEG
        )
        tags["covr"] = [MP4Cover(metadata.cover_image, imageformat=cover_format)]
    audio.save()


def add_m4b_chapters(m4b_path: str, chapters: list[AudioChapter]) -> None:
    """Embed chapter atoms in an M4B by remuxing with ffmpeg.

    Mutagen's MP4 module cannot write chapter atoms, so we use ffmpeg to remux
    the existing audio with an ffmetadata sidecar describing chapter boundaries.
    The remux is lossless (-codec copy).
    """
    if not chapters:
        return

    import os
    import subprocess
    import tempfile

    path = Path(m4b_path)
    if not path.exists() or path.suffix.lower() != ".m4b":
        raise ValueError(f"Expected existing .m4b file, got: {m4b_path}")

    lines = [";FFMETADATA1"]
    for ch in chapters:
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={ch.start_ms}")
        lines.append(f"END={ch.end_ms}")
        # Escape special chars per ffmetadata spec: =, ;, #, \, newline
        title = ch.title.replace("\\", "\\\\").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#").replace("\n", "\\\n")
        lines.append(f"title={title}")

    meta_fd, meta_path = tempfile.mkstemp(suffix=".ffmetadata.txt")
    os.close(meta_fd)
    Path(meta_path).write_text("\n".join(lines), encoding="utf-8")

    out_fd, out_path = tempfile.mkstemp(suffix=".m4b", dir=str(path.parent))
    os.close(out_fd)

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(path), "-i", meta_path,
                "-map_metadata", "1", "-codec", "copy",
                "-f", "ipod", out_path,
            ],
            check=True,
        )
        os.replace(out_path, str(path))
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        Path(out_path).unlink(missing_ok=True)
        raise RuntimeError(
            f"M4B chapter embedding failed: {e}. ffmpeg must be installed."
        ) from e
    finally:
        Path(meta_path).unlink(missing_ok=True)


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
