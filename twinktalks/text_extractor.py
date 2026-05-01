"""Extract text from plain text and markdown files."""

import re
from pathlib import Path

from twinktalks.toc import Chapter


_MD_CODE_BLOCK = re.compile(r"```[\s\S]*?```")
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_INLINE_CODE = re.compile(r"`([^`]+)`")
_MD_BOLD_ITAL = re.compile(r"(\*{1,3}|_{1,3})(.+?)\1")
# Use [ \t] instead of \s for line-anchored patterns: \s would gobble the
# trailing \n on a heading/HR line, collapsing the paragraph break that follows.
_MD_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]*#+)?[ \t]*$", re.MULTILINE)
_MD_HORIZONTAL = re.compile(r"^[-*_]{3,}[ \t]*$", re.MULTILINE)
_MD_LIST_BULLET = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
_MD_LIST_NUMBER = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
_MD_BLOCKQUOTE = re.compile(r"^>\s?", re.MULTILINE)


def _strip_markdown(text: str) -> str:
    """Reduce basic markdown to plain text so TTS reads the words, not the markup."""
    text = _MD_CODE_BLOCK.sub("", text)
    text = _MD_IMAGE.sub(r"\1", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_INLINE_CODE.sub(r"\1", text)
    text = _MD_BOLD_ITAL.sub(r"\2", text)
    text = _MD_HEADING.sub(r"\2", text)
    text = _MD_HORIZONTAL.sub("", text)
    text = _MD_LIST_BULLET.sub("", text)
    text = _MD_LIST_NUMBER.sub("", text)
    text = _MD_BLOCKQUOTE.sub("", text)
    return text


def extract_text(file_path: str, **kwargs) -> str:
    """Read a .txt or .md file as a single string. Markdown markup is stripped."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".md":
        return _strip_markdown(raw)
    return raw


def extract_text_by_page(file_path: str, **kwargs) -> list[tuple[int, str]]:
    """Plain-text files have no page structure — return everything as page 1."""
    text = extract_text(file_path, **kwargs)
    return [(1, text)] if text.strip() else []


def get_item_count(file_path: str) -> int:
    return 1


def extract_toc(file_path: str) -> list[Chapter]:
    """Build a TOC from markdown headings. .txt files have no TOC."""
    path = Path(file_path)
    if not path.exists() or path.suffix.lower() != ".md":
        return []
    raw = path.read_text(encoding="utf-8", errors="replace")
    chapters: list[Chapter] = []
    for m in _MD_HEADING.finditer(raw):
        level = len(m.group(1))
        title = m.group(2).strip()
        if title:
            chapters.append(Chapter(title=title, level=level, start_page=1, end_page=1))
    return chapters
