"""Tests for audio_utils module."""

import os
import tempfile

import numpy as np
import pytest

from twinktalks.audio_utils import (
    generate_silence,
    concatenate_audio,
    save_audio,
    get_duration_seconds,
    MP3ExportError,
)


class TestGenerateSilence:
    def test_correct_length(self):
        silence = generate_silence(1000, sample_rate=24000)
        assert len(silence) == 24000

    def test_all_zeros(self):
        silence = generate_silence(500, sample_rate=16000)
        assert np.all(silence == 0)

    def test_zero_duration(self):
        silence = generate_silence(0)
        assert len(silence) == 0


class TestConcatenateAudio:
    def test_single_segment(self):
        seg = np.ones(100, dtype=np.float32)
        result = concatenate_audio([seg], [])
        np.testing.assert_array_equal(result, seg)

    def test_two_segments_with_silence(self):
        seg1 = np.ones(100, dtype=np.float32)
        seg2 = np.ones(100, dtype=np.float32) * 2
        result = concatenate_audio([seg1, seg2], [100], sample_rate=1000)
        # seg1 (100) + silence (100) + seg2 (100) = 300
        assert len(result) == 300
        assert result[0] == 1.0
        assert result[150] == 0.0  # silence region
        assert result[200] == 2.0

    def test_empty_segments(self):
        result = concatenate_audio([], [])
        assert len(result) == 0

    def test_mismatched_silences_raises(self):
        seg = np.ones(10, dtype=np.float32)
        with pytest.raises(ValueError):
            concatenate_audio([seg, seg], [100, 200])  # should be 1 silence


class TestSaveAudio:
    def test_save_wav(self):
        waveform = np.random.randn(24000).astype(np.float32) * 0.5
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            save_audio(waveform, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    def test_unsupported_format(self):
        waveform = np.zeros(100, dtype=np.float32)
        with pytest.raises(ValueError, match="Unsupported format"):
            save_audio(waveform, "/tmp/test.ogg")

    def test_mp3_failure_raises_and_writes_no_wav(self, tmp_path, monkeypatch):
        """If MP3 export fails, raise MP3ExportError and do NOT write a WAV side-file."""
        waveform = np.zeros(100, dtype=np.float32)
        mp3_path = tmp_path / "test.mp3"

        # Force pydub.AudioSegment.export to fail
        from pydub import AudioSegment
        def _boom(self, *args, **kwargs):
            raise RuntimeError("ffmpeg missing")
        monkeypatch.setattr(AudioSegment, "export", _boom)

        with pytest.raises(MP3ExportError, match="MP3 export failed"):
            save_audio(waveform, str(mp3_path))

        # No side-file should be written
        assert not mp3_path.with_suffix(".wav").exists()
        assert not mp3_path.exists()

    def test_mp3_export_error_is_runtime_error(self):
        """MP3ExportError stays a RuntimeError subclass for backward compat."""
        assert issubclass(MP3ExportError, RuntimeError)

    def test_save_m4b(self, tmp_path):
        """M4B output writes a valid MP4-container file via ffmpeg."""
        waveform = (np.random.randn(24000).astype(np.float32) * 0.3)  # 1s
        m4b_path = tmp_path / "test.m4b"
        save_audio(waveform, str(m4b_path), 24000)
        assert m4b_path.exists()
        # MP4 container files start with an ftyp atom; check first bytes
        head = m4b_path.read_bytes()[:12]
        assert b"ftyp" in head, f"Not an MP4 container: {head!r}"

    def test_unsupported_format_message_lists_m4b(self):
        waveform = np.zeros(100, dtype=np.float32)
        with pytest.raises(ValueError, match="m4b"):
            save_audio(waveform, "/tmp/test.ogg")


class TestM4BChapters:
    def test_remux_preserves_file(self, tmp_path):
        """add_m4b_chapters should remux the file via ffmpeg and keep it valid."""
        from twinktalks.audio_utils import add_m4b_chapters, AudioChapter
        waveform = np.random.randn(48000).astype(np.float32) * 0.3  # 2s
        m4b = tmp_path / "book.m4b"
        save_audio(waveform, str(m4b), 24000)
        original_bytes = m4b.read_bytes()

        chapters = [
            AudioChapter(title="Chapter 1", start_ms=0, end_ms=1000),
            AudioChapter(title="Chapter 2", start_ms=1000, end_ms=2000),
        ]
        add_m4b_chapters(str(m4b), chapters)

        assert m4b.exists()
        new_bytes = m4b.read_bytes()
        # The file should still be a valid MP4 container
        assert b"ftyp" in new_bytes[:32]
        # And it should have changed (chapters added)
        assert new_bytes != original_bytes

    def test_empty_chapter_list_is_noop(self, tmp_path):
        from twinktalks.audio_utils import add_m4b_chapters
        waveform = np.zeros(2400, dtype=np.float32)
        m4b = tmp_path / "book.m4b"
        save_audio(waveform, str(m4b), 24000)
        before = m4b.read_bytes()
        add_m4b_chapters(str(m4b), [])
        assert m4b.read_bytes() == before

    def test_wrong_extension_raises(self, tmp_path):
        from twinktalks.audio_utils import add_m4b_chapters, AudioChapter
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"RIFF....")
        with pytest.raises(ValueError, match=".m4b"):
            add_m4b_chapters(str(wav), [AudioChapter("c", 0, 100)])


class TestGetDuration:
    def test_one_second(self):
        waveform = np.zeros(24000, dtype=np.float32)
        assert get_duration_seconds(waveform, 24000) == 1.0

    def test_half_second(self):
        waveform = np.zeros(12000, dtype=np.float32)
        assert get_duration_seconds(waveform, 24000) == 0.5
