"""Tests for plain text, markdown, and HTML extractors + the router."""

import pytest

from twinktalks import extractor
from twinktalks.text_extractor import _strip_markdown


class TestStripMarkdown:
    def test_headings(self):
        assert _strip_markdown("# Title\n\n## Sub").strip() == "Title\n\nSub"

    def test_bold_and_italic(self):
        assert _strip_markdown("**bold** and *italic*") == "bold and italic"

    def test_links(self):
        assert _strip_markdown("[click](http://example.com) here") == "click here"

    def test_inline_code(self):
        assert _strip_markdown("use `print()` to debug") == "use print() to debug"

    def test_code_block_removed(self):
        text = "Before\n\n```python\ncode here\n```\n\nAfter"
        assert "code here" not in _strip_markdown(text)
        assert "Before" in _strip_markdown(text) and "After" in _strip_markdown(text)

    def test_list_bullets(self):
        text = "- one\n- two\n- three"
        assert _strip_markdown(text) == "one\ntwo\nthree"

    def test_horizontal_rule(self):
        assert _strip_markdown("Above\n\n---\n\nBelow").strip() == "Above\n\n\n\nBelow".strip()


class TestTextExtractor:
    def test_txt_passes_through_unchanged(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("Plain text content. Two sentences.")
        assert extractor.extract_text(str(f)) == "Plain text content. Two sentences."

    def test_md_strips_markup(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Heading\n\n**Bold** text and `code`.")
        result = extractor.extract_text(str(f))
        assert "Heading" in result
        assert "Bold text" in result
        assert "**" not in result
        assert "`" not in result

    def test_md_toc_from_headings(self, tmp_path):
        f = tmp_path / "book.md"
        f.write_text("# Chapter 1\n\nIntro text.\n\n## Section A\n\nMore text.\n\n# Chapter 2\n\nText.")
        toc = extractor.extract_toc(str(f))
        assert len(toc) == 3
        assert toc[0].title == "Chapter 1" and toc[0].level == 1
        assert toc[1].title == "Section A" and toc[1].level == 2

    def test_txt_has_no_toc(self, tmp_path):
        f = tmp_path / "plain.txt"
        f.write_text("Just text.")
        assert extractor.extract_toc(str(f)) == []


class TestHtmlExtractor:
    def test_strips_tags(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><body><p>Hello <strong>world</strong>.</p></body></html>")
        result = extractor.extract_text(str(f))
        assert "Hello" in result and "world" in result
        assert "<" not in result

    def test_strips_script_and_style(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text(
            "<html><head><style>body { color: red; }</style></head>"
            "<body><script>alert('hi')</script><p>Visible</p></body></html>"
        )
        result = extractor.extract_text(str(f))
        assert "Visible" in result
        assert "color: red" not in result
        assert "alert" not in result

    def test_toc_from_headings(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text(
            "<html><body>"
            "<h1>Intro</h1><p>x</p>"
            "<h2>Background</h2><p>y</p>"
            "<h3>Detail</h3><p>z</p>"
            "</body></html>"
        )
        toc = extractor.extract_toc(str(f))
        titles = [c.title for c in toc]
        assert titles == ["Intro", "Background", "Detail"]


class TestRouter:
    def test_supported_extensions_includes_new_formats(self):
        assert ".md" in extractor.SUPPORTED_EXTENSIONS
        assert ".txt" in extractor.SUPPORTED_EXTENSIONS
        assert ".html" in extractor.SUPPORTED_EXTENSIONS
        assert ".htm" in extractor.SUPPORTED_EXTENSIONS

    def test_get_item_count_is_one_for_flat_text(self, tmp_path):
        for ext in (".txt", ".md", ".html"):
            f = tmp_path / f"doc{ext}"
            f.write_text("anything")
            assert extractor.get_item_count(str(f)) == 1

    def test_extract_text_by_page_returns_single_page(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("Hello world.")
        pages = extractor.extract_text_by_page(str(f))
        assert pages == [(1, "Hello world.")]

    def test_pdf_kwargs_dropped_for_text_formats(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("Some text.")
        # These PDF-specific kwargs would otherwise raise TypeError
        result = extractor.extract_text(
            str(f), page_range=(1, 5), max_pages=10, skip_tables=True,
        )
        assert result == "Some text."
