"""Extract text from Microsoft Word (.docx) files."""

import logging
import re
from pathlib import Path

from twinktalks.toc import Chapter

logger = logging.getLogger(__name__)


def _open_doc(file_path: str):
    from docx import Document
    return Document(file_path)


def extract_text(file_path: str, **kwargs) -> str:
    """Read every paragraph from a .docx in document order."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    doc = _open_doc(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text_by_page(file_path: str, **kwargs) -> list[tuple[int, str]]:
    """DOCX has no fixed page layout — return one virtual page."""
    text = extract_text(file_path, **kwargs)
    return [(1, text)] if text.strip() else []


def get_item_count(file_path: str) -> int:
    return 1


_HEADING_RE = re.compile(r"^heading\s*(\d+)$", re.IGNORECASE)


def extract_toc(file_path: str) -> list[Chapter]:
    """Build a TOC from Heading 1-6 style paragraphs."""
    path = Path(file_path)
    if not path.exists():
        return []
    try:
        doc = _open_doc(file_path)
    except Exception as e:
        logger.warning("DOCX open failed for %s: %s", path.name, e)
        return []

    chapters: list[Chapter] = []
    for p in doc.paragraphs:
        style_name = (p.style.name if p.style else "") or ""
        m = _HEADING_RE.match(style_name)
        if not m:
            continue
        level = int(m.group(1))
        title = (p.text or "").strip()
        if title:
            chapters.append(Chapter(title=title, level=level, start_page=1, end_page=1))
    return chapters
