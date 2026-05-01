"""Tests for tts_engine module (model mocked)."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

torch = pytest.importorskip("torch", reason="torch not installed")

from twinktalks.chunker import Chunk
from twinktalks.config import detect_device, detect_dtype
from twinktalks.tts_engine import TTSEngine, SynthesisError, ModelDownloadError, _concatenate_segments

_EXPECTED_DTYPE = torch.float16 if detect_dtype(detect_device()) == "float16" else torch.float32


def _make_chunks(texts, paragraph_ends=None):
    """Create Chunk objects from text strings."""
    chunks = []
    for i, text in enumerate(texts):
        is_para = paragraph_ends[i] if paragraph_ends else False
        chunks.append(Chunk(text=text, index=i, is_paragraph_end=is_para))
    return chunks


def _fake_waveform(duration_ms=100, sample_rate=24000):
    """Create a fake waveform of given duration."""
    n_samples = int(sample_rate * duration_ms / 1000)
    return np.random.randn(n_samples).astype(np.float32)


class TestConcatenateSegments:
    def test_single_segment(self):
        seg = _fake_waveform(100)
        chunks = _make_chunks(["hello"])
        result = _concatenate_segments([seg], chunks, 24000)
        np.testing.assert_array_equal(result, seg)

    def test_two_segments_sentence_gap(self):
        seg1 = _fake_waveform(100)
        seg2 = _fake_waveform(100)
        chunks = _make_chunks(["a.", "b."], paragraph_ends=[False, False])
        result = _concatenate_segments([seg1, seg2], chunks, 24000)
        # Result should be longer than both segments combined (gap added)
        assert len(result) > len(seg1) + len(seg2)

    def test_paragraph_gap_longer_than_sentence(self):
        seg1 = _fake_waveform(100)
        seg2 = _fake_waveform(100)
        chunks_sentence = _make_chunks(["a.", "b."], paragraph_ends=[False, False])
        chunks_para = _make_chunks(["a.", "b."], paragraph_ends=[True, False])
        result_sentence = _concatenate_segments([seg1, seg2], chunks_sentence, 24000)
        result_para = _concatenate_segments([seg1, seg2], chunks_para, 24000)
        assert len(result_para) > len(result_sentence)


class TestSynthesisError:
    def test_is_exception(self):
        assert issubclass(SynthesisError, Exception)

    def test_message(self):
        err = SynthesisError("model failed")
        assert "model failed" in str(err)


class TestModelDownloadError:
    def test_is_exception(self):
        assert issubclass(ModelDownloadError, Exception)

    def test_message(self):
        err = ModelDownloadError("download failed")
        assert "download failed" in str(err)


class TestTTSEngineInit:
    def test_default_init(self):
        engine = TTSEngine()
        assert engine.model is None
        assert engine.speaker == "Aiden"
        assert engine.model_path is None

    def test_custom_speaker(self):
        engine = TTSEngine(speaker="Ryan")
        assert engine.speaker == "Ryan"

    def test_model_path(self):
        engine = TTSEngine(model_path="/some/path")
        assert engine.model_path == "/some/path"


class TestLoadModelPath:
    def test_nonexistent_path_raises(self):
        engine = TTSEngine(model_path="/nonexistent/model/dir")
        with pytest.raises(ModelDownloadError, match="does not exist"):
            engine.load_model()

    @patch.object(TTSEngine, "_load_from_path")
    @patch.object(TTSEngine, "_post_load")
    def test_valid_local_path_skips_hf(self, mock_post, mock_load, tmp_path):
        """When model_path is set and exists, should load locally without trying HF."""
        engine = TTSEngine(model_path=str(tmp_path))
        engine.load_model()
        mock_load.assert_called_once_with(str(tmp_path), _EXPECTED_DTYPE)
        mock_post.assert_called_once()

    @patch.object(TTSEngine, "_load_from_huggingface")
    @patch.object(TTSEngine, "_post_load")
    def test_no_path_tries_huggingface(self, mock_post, mock_hf):
        """When no model_path, should try HuggingFace."""
        engine = TTSEngine()
        engine.load_model()
        mock_hf.assert_called_once()
        mock_post.assert_called_once()

    @patch.object(TTSEngine, "_download_from_modelscope", return_value="/tmp/model")
    @patch.object(TTSEngine, "_load_from_path")
    @patch.object(TTSEngine, "_post_load")
    @patch.object(TTSEngine, "_load_from_huggingface", side_effect=Exception("429 Too Many Requests"))
    def test_hf_rate_limit_falls_back_to_modelscope(self, mock_hf, mock_post, mock_load, mock_ms):
        """When HF fails with 429, should fall back to ModelScope."""
        engine = TTSEngine()
        engine.load_model()
        mock_hf.assert_called_once()
        mock_ms.assert_called_once()
        mock_load.assert_called_once_with("/tmp/model", _EXPECTED_DTYPE)

    @patch.object(TTSEngine, "_load_from_huggingface", side_effect=Exception("some random error"))
    def test_non_auth_error_does_not_fallback(self, mock_hf):
        """Non-auth/rate-limit errors should propagate immediately, not fall back."""
        engine = TTSEngine()
        with pytest.raises(Exception, match="some random error"):
            engine.load_model()


class TestSynthesizeChunks:
    @patch.object(TTSEngine, "synthesize")
    def test_empty_chunks(self, mock_synth):
        engine = TTSEngine()
        waveform, sr, offsets = engine.synthesize_chunks([])
        assert len(waveform) == 0
        assert offsets == []
        mock_synth.assert_not_called()

    @patch.object(TTSEngine, "synthesize")
    def test_single_chunk(self, mock_synth):
        fake = _fake_waveform(200)
        mock_synth.return_value = (fake, 24000)
        engine = TTSEngine()
        chunks = _make_chunks(["Hello world."])
        waveform, sr, offsets = engine.synthesize_chunks(chunks)
        assert len(waveform) > 0
        assert sr == 24000
        assert len(offsets) == 1
        assert offsets[0] == 0
        mock_synth.assert_called_once()

    @patch.object(TTSEngine, "synthesize")
    def test_multiple_chunks(self, mock_synth):
        fake = _fake_waveform(200)
        mock_synth.return_value = (fake, 24000)
        engine = TTSEngine()
        chunks = _make_chunks(["One.", "Two.", "Three."])
        waveform, sr, offsets = engine.synthesize_chunks(chunks)
        assert len(offsets) == 3
        assert offsets[0] == 0
        assert offsets[1] > 0
        assert offsets[2] > offsets[1]

    @patch.object(TTSEngine, "synthesize")
    def test_progress_callback(self, mock_synth):
        fake = _fake_waveform(100)
        mock_synth.return_value = (fake, 24000)
        engine = TTSEngine()
        chunks = _make_chunks(["A.", "B."])
        calls = []
        engine.synthesize_chunks(chunks, progress_callback=lambda c, t: calls.append((c, t)))
        assert calls == [(1, 2), (2, 2)]

    @patch.object(TTSEngine, "synthesize")
    def test_retry_on_failure_then_success(self, mock_synth):
        """Should retry on SynthesisError and succeed."""
        fake = _fake_waveform(100)
        mock_synth.side_effect = [
            SynthesisError("fail"),
            (fake, 24000),
        ]
        engine = TTSEngine()
        chunks = _make_chunks(["Test."])
        waveform, sr, offsets = engine.synthesize_chunks(chunks)
        assert len(waveform) > 0
        assert mock_synth.call_count == 2

    @patch.object(TTSEngine, "synthesize")
    def test_silence_fallback_after_max_retries(self, mock_synth):
        """After 3 failures, should insert silence instead of crashing."""
        mock_synth.side_effect = SynthesisError("always fails")
        engine = TTSEngine()
        chunks = _make_chunks(["Test."])
        waveform, sr, offsets = engine.synthesize_chunks(chunks)
        # Should have a 1-second silence (24000 samples at 24kHz)
        assert len(waveform) == 24000
        assert mock_synth.call_count == 3


class TestSynthesizeChunksStreaming:
    @patch.object(TTSEngine, "synthesize")
    def test_empty_chunks(self, mock_synth):
        engine = TTSEngine()
        results = list(engine.synthesize_chunks_streaming([]))
        assert results == []

    @patch.object(TTSEngine, "synthesize")
    def test_yields_per_chunk(self, mock_synth):
        fake = _fake_waveform(100)
        mock_synth.return_value = (fake, 24000)
        engine = TTSEngine()
        chunks = _make_chunks(["A.", "B.", "C."])
        results = list(engine.synthesize_chunks_streaming(chunks))
        assert len(results) == 3
        # Each yield: (cumulative, sr, current, total, offsets)
        for i, (cum, sr, current, total, offsets) in enumerate(results):
            assert sr == 24000
            assert current == i + 1
            assert total == 3

    @patch.object(TTSEngine, "synthesize")
    def test_offsets_only_on_final(self, mock_synth):
        fake = _fake_waveform(100)
        mock_synth.return_value = (fake, 24000)
        engine = TTSEngine()
        chunks = _make_chunks(["A.", "B."])
        results = list(engine.synthesize_chunks_streaming(chunks))
        # Intermediate yields have None offsets
        assert results[0][4] is None
        # Final yield has offsets list
        assert results[1][4] is not None
        assert len(results[1][4]) == 2

    @patch.object(TTSEngine, "synthesize")
    def test_incremental_growth(self, mock_synth):
        """Cumulative waveform should grow with each yield."""
        fake = _fake_waveform(100)
        mock_synth.return_value = (fake, 24000)
        engine = TTSEngine()
        chunks = _make_chunks(["A.", "B.", "C."])
        results = list(engine.synthesize_chunks_streaming(chunks))
        lengths = [len(r[0]) for r in results]
        assert lengths[0] < lengths[1] < lengths[2]

    @patch.object(TTSEngine, "synthesize")
    def test_retry_in_streaming(self, mock_synth):
        """Streaming should also retry on failure."""
        fake = _fake_waveform(100)
        mock_synth.side_effect = [
            SynthesisError("fail"),
            SynthesisError("fail"),
            (fake, 24000),
        ]
        engine = TTSEngine()
        chunks = _make_chunks(["Test."])
        results = list(engine.synthesize_chunks_streaming(chunks))
        assert len(results) == 1
        assert len(results[0][0]) > 0
