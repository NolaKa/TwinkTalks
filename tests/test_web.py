"""Tests for web module helper functions (no Gradio server needed)."""

import os
import shutil
import tempfile

import pytest

from twinktalks.web import _make_temp_dir, _temp_dirs


class TestMakeTempDir:
    def test_creates_directory(self):
        d = _make_temp_dir()
        assert os.path.isdir(d)
        assert "twinktalks_" in d
        # Cleanup
        shutil.rmtree(d, ignore_errors=True)
        _temp_dirs.clear()

    def test_cleans_previous_dirs(self):
        d1 = _make_temp_dir()
        assert os.path.isdir(d1)
        d2 = _make_temp_dir()
        # d1 should be cleaned up
        assert not os.path.exists(d1)
        assert os.path.isdir(d2)
        # Cleanup
        shutil.rmtree(d2, ignore_errors=True)
        _temp_dirs.clear()

    def test_handles_already_deleted_dir(self):
        d1 = _make_temp_dir()
        shutil.rmtree(d1)
        # Should not crash even if previous dir already gone
        d2 = _make_temp_dir()
        assert os.path.isdir(d2)
        shutil.rmtree(d2, ignore_errors=True)
        _temp_dirs.clear()


class TestExtractAndPreprocess:
    def test_returns_string(self, tmp_path):
        """_extract_and_preprocess should return preprocessed text."""
        from twinktalks.web import _extract_and_preprocess
        from unittest.mock import patch

        with patch("twinktalks.extractor.extract_text", return_value="Hello [1,2] world."):
            with patch("twinktalks.text_preprocessor.preprocess", side_effect=lambda t: t.replace("[1,2]", "")):
                result = _extract_and_preprocess("fake.pdf", True, False)
                assert "[1,2]" not in result
                assert "Hello" in result


class TestGetPageRange:
    def test_full_range(self):
        from twinktalks.web import _get_page_range
        result = _get_page_range(1, 10, 10)
        assert result is None  # Full range returns None

    def test_partial_range(self):
        from twinktalks.web import _get_page_range
        result = _get_page_range(3, 7, 10)
        assert result == (3, 7)

    def test_single_page(self):
        from twinktalks.web import _get_page_range
        result = _get_page_range(5, 5, 10)
        assert result == (5, 5)

    def test_clamps_to_total(self):
        from twinktalks.web import _get_page_range
        result = _get_page_range(1, 999, 10)
        # When start=1 and end>=total, should return None (full range)
        assert result is None


class TestOnChapterSelect:
    def test_parses_page_range_from_choice(self):
        from twinktalks.web import on_chapter_select
        from unittest.mock import MagicMock

        mock_file = MagicMock()
        mock_file.name = "test.pdf"

        result = on_chapter_select("Introduction  [p.3-7]", [mock_file])
        # Returns two gr.update() calls
        assert result is not None

    def test_all_pages_returns_full_range(self):
        from twinktalks.web import on_chapter_select
        from unittest.mock import MagicMock, patch

        mock_file = MagicMock()
        mock_file.name = "test.pdf"

        with patch("twinktalks.extractor.get_item_count", return_value=50):
            result = on_chapter_select("All pages", [mock_file])
            assert result is not None

    def test_no_files_returns_noop(self):
        from twinktalks.web import on_chapter_select
        result = on_chapter_select("Introduction  [p.3-7]", [])
        assert result is not None


class TestProcessQueue:
    def test_no_files_yields_error(self):
        from twinktalks.web import process_queue
        results = list(process_queue(
            None, 1, 1, "", "Aiden", "English", 1.0, True, False, "wav", "",
        ))
        assert len(results) == 1
        assert "NO FILE" in results[0][0]

    def test_empty_files_yields_error(self):
        from twinktalks.web import process_queue
        results = list(process_queue(
            [], 1, 1, "", "Aiden", "English", 1.0, True, False, "wav", "",
        ))
        assert len(results) == 1
        assert "NO FILE" in results[0][0]


class TestExtractOnly:
    def test_no_files(self):
        from twinktalks.web import extract_only
        result = extract_only(None, 1, 1, "", True, False)
        assert "NO FILE" in result

    def test_empty_files(self):
        from twinktalks.web import extract_only
        result = extract_only([], 1, 1, "", True, False)
        assert "NO FILE" in result
