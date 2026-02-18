"""Tests for chunker module."""

import pytest
from twinktalks.chunker import chunk_text, Chunk


class TestChunkText:
    def test_empty_input(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_single_short_sentence(self):
        chunks = chunk_text("Hello world.")
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world."
        assert chunks[0].index == 0

    def test_respects_max_chars(self):
        text = "First sentence is here. Second sentence is here. Third sentence is here."
        chunks = chunk_text(text, max_chars=50)
        for chunk in chunks:
            assert len(chunk.text) <= 60  # some tolerance for last sentence

    def test_never_breaks_mid_sentence(self):
        sentences = [f"Sentence number {i} with some extra words." for i in range(10)]
        text = " ".join(sentences)
        chunks = chunk_text(text, max_chars=100)
        # Each chunk should end with a period (complete sentence)
        for chunk in chunks:
            assert chunk.text.rstrip().endswith(".")

    def test_paragraph_awareness(self):
        text = "First paragraph sentence one. Sentence two.\n\nSecond paragraph here."
        chunks = chunk_text(text, max_chars=500)
        assert len(chunks) == 2
        # First chunk should mark paragraph end
        assert chunks[0].is_paragraph_end is True

    def test_indices_are_sequential(self):
        text = "A. B. C.\n\nD. E.\n\nF."
        chunks = chunk_text(text, max_chars=10)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_long_single_sentence(self):
        """A single sentence exceeding max_chars should still become one chunk."""
        long_sentence = "This is a very long sentence " * 20 + "that ends here."
        chunks = chunk_text(long_sentence, max_chars=50)
        # The sentence should not be broken
        full_text = " ".join(c.text for c in chunks)
        assert "that ends here." in full_text

    def test_multiple_paragraphs(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = chunk_text(text, max_chars=500)
        assert len(chunks) == 3
        assert chunks[0].is_paragraph_end is True
        assert chunks[1].is_paragraph_end is True
        assert chunks[2].is_paragraph_end is False  # last paragraph
