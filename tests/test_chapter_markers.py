"""Tests for chapter markers (AudioChapter, add_chapter_markers, ID3 embedding)."""

import struct
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from twinktalks.audio_utils import AudioChapter, add_chapter_markers, save_audio


class TestAudioChapter:
    def test_create(self):
        ch = AudioChapter(title="Introduction", start_ms=0, end_ms=5000)
        assert ch.title == "Introduction"
        assert ch.start_ms == 0
        assert ch.end_ms == 5000

    def test_multiple(self):
        chapters = [
            AudioChapter("Ch 1", 0, 3000),
            AudioChapter("Ch 2", 3000, 8000),
            AudioChapter("Ch 3", 8000, 12000),
        ]
        assert len(chapters) == 3
        assert chapters[1].start_ms == 3000


class TestAddChapterMarkers:
    def _make_mp3(self, tmp_path: Path) -> str:
        """Create a real MP3 file for testing."""
        mp3_path = str(tmp_path / "test.mp3")
        # Generate 2 seconds of silence
        waveform = np.zeros(48000, dtype=np.float32)
        save_audio(waveform, mp3_path, 24000)
        return mp3_path

    def test_embed_chapters(self, tmp_path):
        mp3_path = self._make_mp3(tmp_path)
        chapters = [
            AudioChapter("Chapter 1", 0, 1000),
            AudioChapter("Chapter 2", 1000, 2000),
        ]
        add_chapter_markers(mp3_path, chapters)

        # Verify with mutagen
        from mutagen.id3 import ID3
        tags = ID3(mp3_path)

        # Check CHAP frames
        chap_frames = [f for f in tags.values() if f.__class__.__name__ == "CHAP"]
        assert len(chap_frames) == 2
        assert chap_frames[0].start_time == 0
        assert chap_frames[0].end_time == 1000
        assert chap_frames[1].start_time == 1000
        assert chap_frames[1].end_time == 2000

        # Check CTOC frame
        ctoc_frames = [f for f in tags.values() if f.__class__.__name__ == "CTOC"]
        assert len(ctoc_frames) == 1
        assert len(ctoc_frames[0].child_element_ids) == 2

    def test_embed_single_chapter(self, tmp_path):
        mp3_path = self._make_mp3(tmp_path)
        add_chapter_markers(mp3_path, [AudioChapter("Only Chapter", 0, 2000)])

        from mutagen.id3 import ID3
        tags = ID3(mp3_path)
        chap_frames = [f for f in tags.values() if f.__class__.__name__ == "CHAP"]
        assert len(chap_frames) == 1

    def test_empty_chapters(self, tmp_path):
        mp3_path = self._make_mp3(tmp_path)
        # Should not raise
        add_chapter_markers(mp3_path, [])

    def test_not_mp3_raises(self, tmp_path):
        wav_path = str(tmp_path / "test.wav")
        waveform = np.zeros(24000, dtype=np.float32)
        save_audio(waveform, wav_path, 24000)
        with pytest.raises(ValueError, match="Expected existing .mp3"):
            add_chapter_markers(wav_path, [AudioChapter("Ch", 0, 1000)])

    def test_missing_file_raises(self):
        with pytest.raises(ValueError):
            add_chapter_markers("/nonexistent/file.mp3", [AudioChapter("Ch", 0, 1000)])

    def test_graceful_without_mutagen(self, tmp_path):
        mp3_path = self._make_mp3(tmp_path)
        with patch.dict("sys.modules", {"mutagen": None, "mutagen.id3": None}):
            # Should not raise, just warn
            add_chapter_markers(mp3_path, [AudioChapter("Ch", 0, 1000)])
