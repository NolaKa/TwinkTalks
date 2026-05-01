"""Tests for CLI batch processing helpers."""

from twinktalks.cli import _sanitize_filename, create_parser


class TestSanitizeFilename:
    def test_basic(self):
        assert _sanitize_filename("Introduction") == "Introduction"

    def test_spaces(self):
        assert _sanitize_filename("Chapter One") == "Chapter_One"

    def test_special_chars(self):
        assert _sanitize_filename("Results & Discussion (2024)") == "Results_Discussion_2024"

    def test_long_title(self):
        result = _sanitize_filename("A" * 200)
        assert len(result) <= 80

    def test_empty(self):
        assert _sanitize_filename("") == "untitled"

    def test_only_special(self):
        assert _sanitize_filename("!!!") == "untitled"


class TestParserChapters:
    def test_chapters_all(self):
        parser = create_parser()
        args = parser.parse_args(["test.pdf", "--chapters", "all"])
        assert args.chapters == "all"

    def test_chapter_alias(self):
        parser = create_parser()
        args = parser.parse_args(["test.pdf", "--chapter", "Introduction"])
        assert args.chapters == "Introduction"

    def test_chapter_index(self):
        parser = create_parser()
        args = parser.parse_args(["test.pdf", "--chapters", "3"])
        assert args.chapters == "3"

    def test_merge_chapters_flag(self):
        parser = create_parser()
        args = parser.parse_args(["test.pdf", "--chapters", "all", "--merge-chapters"])
        assert args.merge_chapters is True

    def test_merge_chapters_default_false(self):
        parser = create_parser()
        args = parser.parse_args(["test.pdf"])
        assert args.merge_chapters is False

    def test_preview_flag(self):
        parser = create_parser()
        args = parser.parse_args(["test.pdf", "--preview"])
        assert args.preview is True

    def test_preview_default_false(self):
        parser = create_parser()
        args = parser.parse_args(["test.pdf"])
        assert args.preview is False


class TestPreviewVoice:
    def test_no_files_returns_error(self):
        from twinktalks.web import preview_voice
        status, audio = preview_voice(None, 1, 1, "", "Aiden", "English", 1.0, True, False, "")
        assert "NO FILE" in status
        assert audio is None

    def test_empty_files_returns_error(self):
        from twinktalks.web import preview_voice
        status, audio = preview_voice([], 1, 1, "", "Aiden", "English", 1.0, True, False, "")
        assert "NO FILE" in status
        assert audio is None
