"""Extract text from Rich Text Format (.rtf) files."""

import logging
from pathlib import Path

from twinktalks.toc import Chapter

logger = logging.getLogger(__name__)


def _strip(raw: str) -> str:
    from striprtf.striprtf import rtf_to_text
    return rtf_to_text(raw)


def extract_text(file_path: str, **kwargs) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    raw = path.read_text(encoding="utf-8", errors="replace")
    return _strip(raw)


def extract_text_by_page(file_path: str, **kwargs) -> list[tuple[int, str]]:
    text = extract_text(file_path, **kwargs)
    return [(1, text)] if text.strip() else []


def get_item_count(file_path: str) -> int:
    return 1


def extract_toc(file_path: str) -> list[Chapter]:
    """RTF doesn't expose a structured TOC — return empty."""
    return []
