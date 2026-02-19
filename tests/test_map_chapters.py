"""Tests for _map_chunks_to_chapters."""

from twinktalks.audio_utils import AudioChapter
from twinktalks.chunker import Chunk
from twinktalks.cli import _map_chunks_to_chapters
from twinktalks.toc import Chapter


def _chunk(index, source_page):
    return Chunk(text="test", index=index, is_paragraph_end=False, source_page=source_page)


class TestMapChunksToChapters:
    def test_basic_mapping(self):
        chunks = [
            _chunk(0, 1), _chunk(1, 2),  # Chapter 1: pages 1-2
            _chunk(2, 3), _chunk(3, 4),  # Chapter 2: pages 3-4
        ]
        offsets = [0, 1000, 2500, 4000]
        toc = [
            Chapter("Intro", level=1, start_page=1, end_page=2),
            Chapter("Methods", level=1, start_page=3, end_page=4),
        ]

        result = _map_chunks_to_chapters(chunks, offsets, toc, 5500)

        assert len(result) == 2
        assert result[0].title == "Intro"
        assert result[0].start_ms == 0
        assert result[0].end_ms == 2500  # start of next chapter
        assert result[1].title == "Methods"
        assert result[1].start_ms == 2500
        assert result[1].end_ms == 5500  # total duration

    def test_single_chapter(self):
        chunks = [_chunk(0, 1), _chunk(1, 2)]
        offsets = [0, 1000]
        toc = [Chapter("Only", level=1, start_page=1, end_page=2)]

        result = _map_chunks_to_chapters(chunks, offsets, toc, 2000)
        assert len(result) == 1
        assert result[0].start_ms == 0
        assert result[0].end_ms == 2000

    def test_empty_toc(self):
        assert _map_chunks_to_chapters([], [], [], 0) == []

    def test_empty_offsets(self):
        toc = [Chapter("Ch", level=1, start_page=1, end_page=1)]
        assert _map_chunks_to_chapters([], [], toc, 1000) == []

    def test_chapter_with_no_matching_chunks(self):
        chunks = [_chunk(0, 1), _chunk(1, 2)]
        offsets = [0, 1000]
        toc = [
            Chapter("Intro", level=1, start_page=1, end_page=2),
            Chapter("Appendix", level=1, start_page=10, end_page=12),  # no chunks for pages 10-12
        ]

        result = _map_chunks_to_chapters(chunks, offsets, toc, 2000)
        assert len(result) == 1  # only Intro has matching chunks
        assert result[0].title == "Intro"

    def test_three_chapters(self):
        chunks = [
            _chunk(0, 1), _chunk(1, 2),
            _chunk(2, 3), _chunk(3, 4),
            _chunk(4, 5), _chunk(5, 6),
        ]
        offsets = [0, 500, 1000, 1500, 2000, 2500]
        toc = [
            Chapter("A", level=1, start_page=1, end_page=2),
            Chapter("B", level=1, start_page=3, end_page=4),
            Chapter("C", level=1, start_page=5, end_page=6),
        ]

        result = _map_chunks_to_chapters(chunks, offsets, toc, 3000)
        assert len(result) == 3
        assert result[0].end_ms == result[1].start_ms  # seamless
        assert result[1].end_ms == result[2].start_ms
        assert result[2].end_ms == 3000
