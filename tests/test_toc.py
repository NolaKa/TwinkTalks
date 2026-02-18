"""Tests for TOC extraction and chapter finding."""

import pytest
from twinktalks.toc import Chapter, find_chapter, format_toc


class TestFindChapter:
    def setup_method(self):
        self.chapters = [
            Chapter("Introduction", 1, 1, 5),
            Chapter("Methods", 1, 6, 15),
            Chapter("Participants", 2, 6, 9),
            Chapter("Results", 1, 16, 30),
        ]

    def test_find_by_index(self):
        ch = find_chapter(self.chapters, "2")
        assert ch.title == "Methods"

    def test_find_by_name(self):
        ch = find_chapter(self.chapters, "Results")
        assert ch.start_page == 16

    def test_find_by_partial_name(self):
        ch = find_chapter(self.chapters, "Intro")
        assert ch.title == "Introduction"

    def test_find_case_insensitive(self):
        ch = find_chapter(self.chapters, "methods")
        assert ch.title == "Methods"

    def test_not_found(self):
        assert find_chapter(self.chapters, "Conclusion") is None

    def test_index_out_of_range(self):
        assert find_chapter(self.chapters, "99") is None

    def test_empty_chapters(self):
        assert find_chapter([], "anything") is None


class TestFormatToc:
    def test_empty(self):
        assert format_toc([]) == "No table of contents found."

    def test_basic(self):
        chapters = [
            Chapter("Introduction", 1, 1, 5),
            Chapter("Background", 2, 2, 5),
        ]
        result = format_toc(chapters)
        assert "Introduction" in result
        assert "Background" in result
        assert "p.1-5" in result

    def test_single_page_chapter(self):
        chapters = [Chapter("Preface", 1, 1, 1)]
        result = format_toc(chapters)
        assert "p.1" in result
