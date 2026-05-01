"""Tests for chunk_paged_text and Chunk.source_page."""

from twinktalks.chunker import Chunk, chunk_text, chunk_paged_text


class TestChunkSourcePage:
    def test_default_none(self):
        chunk = Chunk(text="hello", index=0, is_paragraph_end=False)
        assert chunk.source_page is None

    def test_set_source_page(self):
        chunk = Chunk(text="hello", index=0, is_paragraph_end=False, source_page=5)
        assert chunk.source_page == 5

    def test_existing_chunk_text_unchanged(self):
        """Ensure adding source_page field doesn't break existing chunk_text."""
        chunks = chunk_text("Hello world. This is a test sentence.")
        assert len(chunks) >= 1
        assert chunks[0].source_page is None


class TestChunkPagedText:
    def test_basic(self):
        page_texts = [
            (1, "First page has some text. Another sentence here."),
            (2, "Second page text. More sentences on page two."),
        ]
        chunks = chunk_paged_text(page_texts)
        assert len(chunks) >= 2
        assert chunks[0].source_page == 1
        assert all(c.source_page in (1, 2) for c in chunks)

    def test_indices_sequential(self):
        page_texts = [
            (1, "Page one text."),
            (3, "Page three text."),
            (5, "Page five text."),
        ]
        chunks = chunk_paged_text(page_texts)
        for i, c in enumerate(chunks):
            assert c.index == i

    def test_empty(self):
        assert chunk_paged_text([]) == []

    def test_empty_page_text(self):
        page_texts = [
            (1, "Some text here."),
            (2, "   "),  # whitespace only
            (3, "More text."),
        ]
        chunks = chunk_paged_text(page_texts)
        pages = {c.source_page for c in chunks}
        assert 2 not in pages  # empty page produces no chunks

    def test_preserves_paragraph_end(self):
        page_texts = [(1, "First paragraph.\n\nSecond paragraph.")]
        chunks = chunk_paged_text(page_texts)
        assert len(chunks) >= 2
        # First chunk should mark paragraph end
        assert chunks[0].is_paragraph_end is True


class TestPageBoundaryMerging:
    def test_unfinished_sentence_merges_with_next_page(self):
        """When page N ends mid-paragraph, head of page N+1 should be glued in."""
        page_texts = [
            (1, "This is an introduction that runs across the page break and"),
            (2, "continues here with more words."),
        ]
        chunks = chunk_paged_text(page_texts)
        all_text = " ".join(c.text for c in chunks)
        assert "across the page break and continues here" in all_text

    def test_terminated_page_does_not_merge(self):
        """When page N ends with a sentence terminator, no merging happens."""
        page_texts = [
            (1, "Page one ends cleanly."),
            (2, "Page two starts here."),
        ]
        chunks = chunk_paged_text(page_texts)
        # Each page should produce its own chunk(s) with its own source_page
        page_1_chunks = [c for c in chunks if c.source_page == 1]
        page_2_chunks = [c for c in chunks if c.source_page == 2]
        assert len(page_1_chunks) == 1
        assert len(page_2_chunks) == 1
        assert "Page one ends cleanly" in page_1_chunks[0].text
        assert "Page two starts here" in page_2_chunks[0].text

    def test_merged_chunk_keeps_earlier_source_page(self):
        """The continuation should be attributed to the page where it started."""
        page_texts = [
            (5, "Sentence beginning on five and"),
            (6, "ending on six. New paragraph here."),
        ]
        chunks = chunk_paged_text(page_texts)
        # Find the chunk that contains the merged sentence
        merged_chunk = next(c for c in chunks if "and ending" in c.text)
        assert merged_chunk.source_page == 5
        # The "New paragraph here." stays on page 6
        new_para_chunk = next(c for c in chunks if "New paragraph" in c.text)
        assert new_para_chunk.source_page == 6
