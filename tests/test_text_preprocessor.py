"""Tests for text_preprocessor module."""

import pytest
from twinktalks.text_preprocessor import (
    preprocess,
    remove_figure_table_captions,
    remove_inline_citations,
    remove_footnote_markers,
    expand_abbreviations,
    remove_urls_and_dois,
    remove_section_numbers,
    remove_page_numbers,
    collapse_whitespace,
    remove_latex_commands,
)


class TestRemoveFigureTableCaptions:
    def test_figure_caption(self):
        text = "Some text.\nFigure 1: A diagram of the system.\nMore text."
        assert "A diagram" not in remove_figure_table_captions(text)

    def test_table_caption(self):
        text = "Before.\nTable 3. Results summary.\nAfter."
        assert "Results summary" not in remove_figure_table_captions(text)

    def test_fig_abbreviation(self):
        text = "Before.\nFig. 2: Overview.\nAfter."
        assert "Overview" not in remove_figure_table_captions(text)

    def test_preserves_inline_figure_mention(self):
        text = "As shown in Figure 1, the results are clear."
        assert "Figure 1" in remove_figure_table_captions(text)


class TestRemoveInlineCitations:
    def test_single_citation(self):
        assert remove_inline_citations("results [1] show") == "results show"

    def test_multi_citation(self):
        assert remove_inline_citations("prior work [1, 2, 3]") == "prior work"

    def test_range_citation(self):
        assert remove_inline_citations("studies [1-5] found") == "studies found"

    def test_author_citation(self):
        result = remove_inline_citations("shown by (Smith et al., 2024)")
        assert "Smith" not in result

    def test_preserves_normal_brackets(self):
        text = "the array [i] element"
        assert remove_inline_citations(text) == text


class TestRemoveFootnoteMarkers:
    def test_superscript_numbers(self):
        assert remove_footnote_markers("word¹ more²") == "word more"

    def test_no_markers(self):
        assert remove_footnote_markers("normal text") == "normal text"


class TestExpandAbbreviations:
    def test_eg(self):
        assert "for example" in expand_abbreviations("methods (e.g. regression)")

    def test_ie(self):
        assert "that is" in expand_abbreviations("the model (i.e. GPT)")

    def test_et_al(self):
        assert "and others" in expand_abbreviations("Smith et al. proposed")

    def test_etc(self):
        assert "and so on" in expand_abbreviations("trees, graphs, etc.")

    def test_wrt(self):
        assert "with respect to" in expand_abbreviations("w.r.t. accuracy")


class TestRemoveUrlsAndDois:
    def test_url(self):
        assert remove_urls_and_dois("see https://example.com for details").strip() == "see  for details"

    def test_doi(self):
        result = remove_urls_and_dois("doi: 10.1234/abcd")
        assert "10.1234" not in result

    def test_email(self):
        result = remove_urls_and_dois("contact user@example.com for")
        assert "@" not in result


class TestRemoveSectionNumbers:
    def test_simple_section(self):
        assert remove_section_numbers("2.1 Methods") == "Methods"

    def test_deep_section(self):
        assert remove_section_numbers("3.2.1 Results") == "Results"

    def test_no_section_number(self):
        assert remove_section_numbers("Introduction") == "Introduction"


class TestRemovePageNumbers:
    def test_page_number_between_paragraphs(self):
        """The realistic shape: PDF pages joined with \\n\\n, page number stranded between."""
        result = remove_page_numbers("First page text.\n\n  42  \n\nSecond page text.")
        assert "42" not in result
        # Paragraph separation preserved
        assert "First page text." in result
        assert "Second page text." in result

    def test_preserves_numbers_in_text(self):
        text = "There are 42 samples in the dataset."
        assert remove_page_numbers(text) == text

    def test_preserves_digit_line_without_paragraph_context(self):
        """A digit-only line embedded in a single block of text is NOT a page number."""
        text = "text\n  42  \nmore"
        assert remove_page_numbers(text) == text

    def test_preserves_numbered_list_items(self):
        """A bare-number line in a numbered list (no surrounding blank lines) stays."""
        text = "Items:\n1\nfirst\n2\nsecond"
        assert remove_page_numbers(text) == text


class TestCollapseWhitespace:
    def test_multiple_spaces(self):
        assert collapse_whitespace("too   many   spaces") == "too many spaces"

    def test_multiple_newlines(self):
        assert "\n\n\n" not in collapse_whitespace("a\n\n\n\nb")

    def test_empty_string(self):
        assert collapse_whitespace("") == ""


class TestRemoveLatexCommands:
    def test_command_with_arg(self):
        assert remove_latex_commands("the \\textbf{word} is") == "the word is"

    def test_bare_command(self):
        result = remove_latex_commands("use \\alpha for")
        assert "\\" not in result


class TestPreprocessPipeline:
    def test_full_pipeline(self):
        text = (
            "2.1 Introduction\n"
            "Deep learning [1, 2] has shown great results (Smith et al., 2024).\n"
            "Figure 1: Architecture overview.\n"
            "The method (i.e. backpropagation) works w.r.t. the loss.\n"
            "See https://example.com for code.\n"
            "\n42\n"
        )
        result = preprocess(text)
        assert "[1, 2]" not in result
        assert "Smith" not in result
        assert "Figure 1" not in result
        assert "that is" in result
        assert "with respect to" in result
        assert "https://" not in result
        assert "2.1" not in result.split("\n")[0]

    def test_empty_input(self):
        assert preprocess("") == ""

    def test_plain_text_unchanged(self):
        text = "This is a simple sentence with no academic formatting."
        assert preprocess(text) == text
