"""Tests for book_metadata extraction."""

from pathlib import Path

from twinktalks.book_metadata import BookMetadata, extract_metadata


class TestBookMetadataDataclass:
    def test_defaults_to_none(self):
        m = BookMetadata()
        assert m.title is None
        assert m.author is None
        assert m.cover_image is None
        assert m.cover_mime is None
        assert m.has_cover() is False

    def test_has_cover_true(self):
        m = BookMetadata(cover_image=b"\x89PNG", cover_mime="image/png")
        assert m.has_cover() is True

    def test_has_cover_false_when_only_one_field_set(self):
        assert BookMetadata(cover_image=b"x").has_cover() is False
        assert BookMetadata(cover_mime="image/png").has_cover() is False


class TestExtractMetadata:
    def test_unsupported_extension_returns_empty(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("hello")
        m = extract_metadata(str(f))
        assert m == BookMetadata()

    def test_missing_pdf_returns_empty(self):
        m = extract_metadata("/nonexistent/path/to.pdf")
        assert m == BookMetadata()

    def test_missing_epub_returns_empty(self):
        m = extract_metadata("/nonexistent/path/to.epub")
        assert m == BookMetadata()

    def test_pdf_with_metadata(self, tmp_path):
        """Build a minimal PDF with title/author and verify extraction."""
        import fitz
        path = tmp_path / "sample.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.set_metadata({"title": "Test Title", "author": "Test Author"})
        doc.save(str(path))
        doc.close()

        m = extract_metadata(str(path))
        assert m.title == "Test Title"
        assert m.author == "Test Author"
        # First page rendered as cover
        assert m.has_cover() is True
        assert m.cover_mime == "image/png"
        assert m.cover_image is not None and len(m.cover_image) > 0

    def test_pdf_without_metadata(self, tmp_path):
        """A PDF with no title/author still gets a rendered cover."""
        import fitz
        path = tmp_path / "blank.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(path))
        doc.close()

        m = extract_metadata(str(path))
        assert m.title is None
        assert m.author is None
        # Cover render still works
        assert m.has_cover() is True
