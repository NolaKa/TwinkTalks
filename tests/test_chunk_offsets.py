"""Tests for compute_chunk_offsets."""

import numpy as np

from twinktalks.chunker import Chunk
from twinktalks.audio_utils import compute_chunk_offsets
from twinktalks.config import INTER_SENTENCE_SILENCE_MS, INTER_PARAGRAPH_SILENCE_MS


def _make_chunk(index, is_paragraph_end=False, source_page=None):
    return Chunk(text="test", index=index, is_paragraph_end=is_paragraph_end, source_page=source_page)


class TestComputeChunkOffsets:
    def test_single_segment(self):
        segments = [np.zeros(24000)]  # 1 second at 24kHz
        chunks = [_make_chunk(0)]
        offsets = compute_chunk_offsets(segments, chunks, 24000)
        assert offsets == [0]

    def test_two_segments_sentence_boundary(self):
        seg1 = np.zeros(24000)  # 1s
        seg2 = np.zeros(12000)  # 0.5s
        chunks = [_make_chunk(0, is_paragraph_end=False), _make_chunk(1)]
        offsets = compute_chunk_offsets([seg1, seg2], chunks, 24000)

        assert offsets[0] == 0
        # seg1 = 1000ms + sentence silence
        expected = 1000 + INTER_SENTENCE_SILENCE_MS
        assert offsets[1] == expected

    def test_two_segments_paragraph_boundary(self):
        seg1 = np.zeros(24000)  # 1s
        seg2 = np.zeros(12000)  # 0.5s
        chunks = [_make_chunk(0, is_paragraph_end=True), _make_chunk(1)]
        offsets = compute_chunk_offsets([seg1, seg2], chunks, 24000)

        assert offsets[0] == 0
        expected = 1000 + INTER_PARAGRAPH_SILENCE_MS
        assert offsets[1] == expected

    def test_three_segments(self):
        seg1 = np.zeros(24000)  # 1s
        seg2 = np.zeros(24000)  # 1s
        seg3 = np.zeros(24000)  # 1s
        chunks = [
            _make_chunk(0, is_paragraph_end=False),
            _make_chunk(1, is_paragraph_end=True),
            _make_chunk(2),
        ]
        offsets = compute_chunk_offsets([seg1, seg2, seg3], chunks, 24000)

        assert offsets[0] == 0
        assert offsets[1] == 1000 + INTER_SENTENCE_SILENCE_MS
        assert offsets[2] == 2000 + INTER_SENTENCE_SILENCE_MS + INTER_PARAGRAPH_SILENCE_MS

    def test_empty(self):
        assert compute_chunk_offsets([], [], 24000) == []
