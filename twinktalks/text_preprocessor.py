"""Clean academic text for natural-sounding TTS output."""

import re


# Pre-compiled regex patterns (compiled once at module load)
_RE_FIGURE_TABLE_CAPTIONS = re.compile(r"^(?:Figure|Fig\.|Table|Tab\.)\s*\d+[.:].+$", re.MULTILINE)
_RE_BRACKET_CITATIONS = re.compile(r"\s*\[[\d,;\s\u2013-]+\]")
_RE_AUTHOR_CITATIONS = re.compile(r"\s*\([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et al\.)?,\s*\d{4}[a-z]?\)")
_RE_MULTI_AUTHOR_CITATIONS = re.compile(r"\s*\([A-Z][a-z]+,\s*\d{4}(?:;\s*[A-Z][a-z]+,\s*\d{4})+\)")
_RE_FOOTNOTE_MARKERS = re.compile(r"(?<=\w)\s*[¹²³⁴⁵⁶⁷⁸⁹⁰]+")
_RE_URLS = re.compile(r"https?://\S+")
_RE_DOIS = re.compile(r"doi:\s*\S+", re.IGNORECASE)
_RE_EMAILS = re.compile(r"\b\S+@\S+\.\S+\b")
_RE_SECTION_NUMBERS = re.compile(r"^(\d+\.)+\d*\s+", re.MULTILINE)
_RE_PAGE_NUMBERS = re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE)
_RE_MULTI_SPACES = re.compile(r"[ \t]+")
_RE_MULTI_NEWLINES = re.compile(r"\n{3,}")
_RE_BLANK_LINES = re.compile(r"^\s+$", re.MULTILINE)
_RE_LATEX_WITH_ARG = re.compile(r"\\[a-zA-Z]+\{([^}]*)\}")
_RE_LATEX_BARE = re.compile(r"\\[a-zA-Z]+")
_RE_BRACES = re.compile(r"[{}]")
_RE_REFERENCES = re.compile(r"\n\s*(?:References|Bibliography|REFERENCES|BIBLIOGRAPHY)\s*\n")

# Abbreviation expansions (pre-compiled)
ABBREVIATIONS = [
    (re.compile(r"\be\.g\."), "for example"),
    (re.compile(r"\bi\.e\."), "that is"),
    (re.compile(r"\bet al\."), "and others"),
    (re.compile(r"\betc\."), "and so on"),
    (re.compile(r"\bcf\."), "compare"),
    (re.compile(r"\bw\.r\.t\."), "with respect to"),
    (re.compile(r"\bvs\."), "versus"),
    (re.compile(r"\bFig\."), "Figure"),
    (re.compile(r"\bEq\."), "Equation"),
    (re.compile(r"\bTab\."), "Table"),
    (re.compile(r"\bSec\."), "Section"),
    (re.compile(r"\bRef\."), "Reference"),
    (re.compile(r"\bApprox\."), "Approximately"),
    (re.compile(r"\bresp\."), "respectively"),
]


def remove_figure_table_captions(text: str) -> str:
    """Remove lines that are figure/table captions."""
    return _RE_FIGURE_TABLE_CAPTIONS.sub("", text)


def remove_inline_citations(text: str) -> str:
    """Remove bracketed citations like [1], [1, 2], [1-3] and author citations."""
    text = _RE_BRACKET_CITATIONS.sub("", text)
    text = _RE_AUTHOR_CITATIONS.sub("", text)
    text = _RE_MULTI_AUTHOR_CITATIONS.sub("", text)
    return text


def remove_footnote_markers(text: str) -> str:
    """Remove superscript-like footnote numbers after words."""
    return _RE_FOOTNOTE_MARKERS.sub("", text)


def expand_abbreviations(text: str) -> str:
    """Expand common academic abbreviations for natural speech."""
    for pattern, replacement in ABBREVIATIONS:
        text = pattern.sub(replacement, text)
    return text


def remove_urls_and_dois(text: str) -> str:
    """Remove URLs, DOIs, and email addresses."""
    text = _RE_URLS.sub("", text)
    text = _RE_DOIS.sub("", text)
    text = _RE_EMAILS.sub("", text)
    return text


def remove_section_numbers(text: str) -> str:
    """Remove leading section numbers like '2.1 ' or '3.2.1 '."""
    return _RE_SECTION_NUMBERS.sub("", text)


def remove_page_numbers(text: str) -> str:
    """Remove isolated page numbers (lines with just a number)."""
    return _RE_PAGE_NUMBERS.sub("", text)


def collapse_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces/newlines."""
    text = _RE_MULTI_SPACES.sub(" ", text)
    text = _RE_MULTI_NEWLINES.sub("\n\n", text)
    text = _RE_BLANK_LINES.sub("", text)
    return text.strip()


def remove_latex_commands(text: str) -> str:
    """Remove common LaTeX artifacts that survive PDF extraction."""
    text = _RE_LATEX_WITH_ARG.sub(r"\1", text)
    text = _RE_LATEX_BARE.sub("", text)
    text = _RE_BRACES.sub("", text)
    return text


def truncate_at_references(text: str) -> str:
    """Truncate text at the References/Bibliography section."""
    match = _RE_REFERENCES.search(text)
    if match:
        return text[: match.start()].strip()
    return text


def preprocess(text: str) -> str:
    """Full preprocessing pipeline: raw academic text -> TTS-ready text."""
    text = remove_figure_table_captions(text)
    text = remove_inline_citations(text)
    text = remove_footnote_markers(text)
    text = remove_urls_and_dois(text)
    text = remove_section_numbers(text)
    text = remove_page_numbers(text)
    text = remove_latex_commands(text)
    text = expand_abbreviations(text)
    text = collapse_whitespace(text)
    return text
