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


class TestGetDuration:
    def test_one_second(self):
        waveform = np.zeros(24000, dtype=np.float32)
        assert get_duration_seconds(waveform, 24000) == 1.0

    def test_half_second(self):
        waveform = np.zeros(12000, dtype=np.float32)
        assert get_duration_seconds(waveform, 24000) == 0.5
