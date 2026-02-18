"""Tests for EPUB text extraction."""

import pytest
from ebooklib import epub as ep


@pytest.fixture
def sample_epub(tmp_path):
    """Create a minimal test EPUB."""
    book = ep.EpubBook()
    book.set_identifier("test-123")
    book.set_title("Test Book")
    book.set_language("en")

    # Chapter 1
    ch1 = ep.EpubHtml(title="Introduction", file_name="ch1.xhtml", lang="en")
    ch1.content = "<h1>Introduction</h1><p>This is the introduction chapter with enough text to pass the minimum threshold for extraction.</p>"
    book.add_item(ch1)

    # Chapter 2
    ch2 = ep.EpubHtml(title="Methods", file_name="ch2.xhtml", lang="en")
    ch2.content = "<h1>Methods</h1><p>This chapter describes the methods used in our study with sufficient detail.</p>"
    book.add_item(ch2)

    # Chapter 3
    ch3 = ep.EpubHtml(title="Results", file_name="ch3.xhtml", lang="en")
    ch3.content = "<h1>Results</h1><p>The results of our analysis show interesting patterns worth discussing at length.</p>"
    book.add_item(ch3)

    book.toc = [
        ep.Link("ch1.xhtml", "Introduction", "ch1"),
        ep.Link("ch2.xhtml", "Methods", "ch2"),
        ep.Link("ch3.xhtml", "Results", "ch3"),
    ]

    book.add_item(ep.EpubNcx())
    book.add_item(ep.EpubNav())
    book.spine = ["nav", ch1, ch2, ch3]

    path = str(tmp_path / "test.epub")
    ep.write_epub(path, book)
    return path


class TestEPUBExtractor:
    def test_file_not_found(self):
        from twinktalks.epub_extractor import extract_text
        with pytest.raises(FileNotFoundError):
            extract_text("/nonexistent/test.epub")

    def test_extract_text(self, sample_epub):
        from twinktalks.epub_extractor import extract_text
        text = extract_text(sample_epub)
        assert "Introduction" in text
        assert "Methods" in text
        assert "Results" in text

    def test_chapter_count(self, sample_epub):
        from twinktalks.epub_extractor import get_chapter_count
        count = get_chapter_count(sample_epub)
        assert count >= 3  # 3 chapters + nav

    def test_extract_toc(self, sample_epub):
        from twinktalks.epub_extractor import extract_toc
        chapters = extract_toc(sample_epub)
        assert len(chapters) == 3
        assert chapters[0].title == "Introduction"
        assert chapters[1].title == "Methods"
        assert chapters[2].title == "Results"

    def test_chapter_range(self, sample_epub):
        from twinktalks.epub_extractor import extract_text
        text = extract_text(sample_epub, chapter_range=(2, 3))
        # Should not contain nav content, should have ch1 and ch2 content
        # (spine indices: nav=1, ch1=2, ch2=3, ch3=4)
        assert "Introduction" in text or "Methods" in text


class TestExtractorRouter:
    def test_detect_pdf(self):
        from twinktalks.extractor import detect_file_type
        assert detect_file_type("test.pdf") == ".pdf"

    def test_detect_epub(self):
        from twinktalks.extractor import detect_file_type
        assert detect_file_type("test.epub") == ".epub"

    def test_detect_unsupported(self):
        from twinktalks.extractor import detect_file_type
        with pytest.raises(ValueError, match="Unsupported"):
            detect_file_type("test.docx")

    def test_router_epub(self, sample_epub):
        from twinktalks.extractor import extract_text
        text = extract_text(sample_epub)
        assert "Introduction" in text
