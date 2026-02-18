"""Clean academic text for natural-sounding TTS output."""

import re


# Abbreviation expansions
ABBREVIATIONS = {
    r"\be\.g\.": "for example",
    r"\bi\.e\.": "that is",
    r"\bet al\.": "and others",
    r"\betc\.": "and so on",
    r"\bcf\.": "compare",
    r"\bw\.r\.t\.": "with respect to",
    r"\bvs\.": "versus",
    r"\bFig\.": "Figure",
    r"\bEq\.": "Equation",
    r"\bTab\.": "Table",
    r"\bSec\.": "Section",
    r"\bRef\.": "Reference",
    r"\bApprox\.": "Approximately",
    r"\bresp\.": "respectively",
}


def remove_figure_table_captions(text: str) -> str:
    """Remove lines that are figure/table captions."""
    pattern = r"^(?:Figure|Fig\.|Table|Tab\.)\s*\d+[.:].+$"
    return re.sub(pattern, "", text, flags=re.MULTILINE)


def remove_inline_citations(text: str) -> str:
    """Remove bracketed citations like [1], [1, 2], [1-3] and author citations."""
    # Bracketed: [1], [1, 2], [1-3], [1, 2, 3]
    text = re.sub(r"\s*\[[\d,;\s–-]+\]", "", text)
    # Parenthetical author citations: (Author et al., 2024), (Author, 2023)
    text = re.sub(r"\s*\([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et al\.)?,\s*\d{4}[a-z]?\)", "", text)
    # Multiple author citations: (Author1, 2020; Author2, 2021)
    text = re.sub(r"\s*\([A-Z][a-z]+,\s*\d{4}(?:;\s*[A-Z][a-z]+,\s*\d{4})+\)", "", text)
    return text


def remove_footnote_markers(text: str) -> str:
    """Remove superscript-like footnote numbers after words."""
    return re.sub(r"(?<=\w)\s*[¹²³⁴⁵⁶⁷⁸⁹⁰]+", "", text)


def expand_abbreviations(text: str) -> str:
    """Expand common academic abbreviations for natural speech."""
    for pattern, replacement in ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)
    return text


def remove_urls_and_dois(text: str) -> str:
    """Remove URLs, DOIs, and email addresses."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"doi:\s*\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\S+@\S+\.\S+\b", "", text)
    return text


def remove_section_numbers(text: str) -> str:
    """Remove leading section numbers like '2.1 ' or '3.2.1 '."""
    return re.sub(r"^(\d+\.)+\d*\s+", "", text, flags=re.MULTILINE)


def remove_page_numbers(text: str) -> str:
    """Remove isolated page numbers (lines with just a number)."""
    return re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)


def collapse_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces/newlines."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s+$", "", text, flags=re.MULTILINE)
    return text.strip()


def remove_latex_commands(text: str) -> str:
    """Remove common LaTeX artifacts that survive PDF extraction."""
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}]", "", text)
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
