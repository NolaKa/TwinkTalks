"""Tests for pdf_extractor module."""

import pytest
from twinktalks.pdf_extractor import (
    extract_text,
    _truncate_at_references,
    ExtractionError,
)


class TestTruncateAtReferences:
    def test_truncates_at_references(self):
        text = "Introduction.\n\nMethods.\n\nReferences\n\n[1] Some paper."
        result = _truncate_at_references(text)
        assert "Some paper" not in result
        assert "Methods" in result

    def test_truncates_at_bibliography(self):
        text = "Content here.\n\nBibliography\n\nEntry 1."
        result = _truncate_at_references(text)
        assert "Entry 1" not in result

    def test_no_references_section(self):
        text = "Just regular text without a references section."
        assert _truncate_at_references(text) == text


class TestExtractText:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_text("/nonexistent/file.pdf")

    def test_not_a_pdf(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        with pytest.raises(ValueError, match="Not a PDF"):
            extract_text(str(txt_file))
