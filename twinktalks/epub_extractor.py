"""Extract text from EPUB files using ebooklib + BeautifulSoup."""

from pathlib import Path

import ebooklib
from ebooklib import epub as ep
from bs4 import BeautifulSoup

from twinktalks.toc import Chapter


class EPUBExtractionError(Exception):
    """Raised when EPUB text extraction fails."""


def get_chapter_count(epub_path: str) -> int:
    """Return the number of content documents (spine items) in the EPUB."""
    book = ep.read_epub(epub_path, options={"ignore_ncx": True})
    return len([i for i in book.spine])


def extract_toc(epub_path: str) -> list[Chapter]:
    """Extract the table of contents from an EPUB.

    The start_page/end_page fields store spine item indices (1-indexed),
    not PDF page numbers.
    """
    path = Path(epub_path)
    if not path.exists():
        raise FileNotFoundError(f"EPUB not found: {epub_path}")

    book = ep.read_epub(epub_path, options={"ignore_ncx": True})
    toc = book.toc

    if not toc:
        return []

    # Build href -> spine index mapping
    spine_ids = [item_id for item_id, _linear in book.spine]
    id_to_href = {}
    for item in book.get_items():
        id_to_href[item.get_id()] = item.get_name()

    href_to_index = {}
    for idx, item_id in enumerate(spine_ids):
        href = id_to_href.get(item_id, "")
        base_href = href.split("#")[0]
        href_to_index[base_href] = idx + 1  # 1-indexed

    chapters: list[Chapter] = []
    _walk_toc(toc, chapters, href_to_index, level=1)

    # Fix end_page values
    total = len(spine_ids)
    for i in range(len(chapters) - 1):
        chapters[i] = Chapter(
            title=chapters[i].title,
            level=chapters[i].level,
            start_page=chapters[i].start_page,
            end_page=max(chapters[i].start_page, chapters[i + 1].start_page - 1),
        )
    if chapters:
        chapters[-1] = Chapter(
            title=chapters[-1].title,
            level=chapters[-1].level,
            start_page=chapters[-1].start_page,
            end_page=total,
        )

    return chapters


def _walk_toc(toc_entries, chapters, href_to_index, level):
    """Recursively walk EPUB TOC structure to build flat chapter list."""
    for entry in toc_entries:
        if isinstance(entry, tuple):
            section, children = entry
            href = section.href.split("#")[0] if section.href else ""
            start = href_to_index.get(href, 1)
            chapters.append(Chapter(title=section.title, level=level, start_page=start, end_page=start))
            _walk_toc(children, chapters, href_to_index, level + 1)
        elif isinstance(entry, ep.Link):
            href = entry.href.split("#")[0] if entry.href else ""
            start = href_to_index.get(href, 1)
            chapters.append(Chapter(title=entry.title, level=level, start_page=start, end_page=start))


def extract_text_by_item(
    epub_path: str,
    skip_references: bool = True,
    chapter_range: tuple[int, int] | None = None,
) -> list[tuple[int, str]]:
    """Extract text from an EPUB, returning per-spine-item results.

    Returns:
        List of (spine_index, text) tuples (1-indexed).
    """
    path = Path(epub_path)
    if not path.exists():
        raise FileNotFoundError(f"EPUB not found: {epub_path}")

    book = ep.read_epub(epub_path, options={"ignore_ncx": True})
    spine_ids = [item_id for item_id, _linear in book.spine]

    if chapter_range is not None:
        start, end = chapter_range
        indices = list(range(max(0, start - 1), min(end, len(spine_ids))))
    else:
        indices = list(range(len(spine_ids)))

    items_by_id = {item.get_id(): item for item in book.get_items()}

    page_texts: list[tuple[int, str]] = []
    for idx in indices:
        if idx >= len(spine_ids):
            continue
        item_id = spine_ids[idx]
        item = items_by_id.get(item_id)
        if item is None:
            continue
        content = item.get_content()
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        if text.strip():
            if skip_references:
                from twinktalks.text_preprocessor import truncate_at_references
                text = truncate_at_references(text)
            if text.strip():
                page_texts.append((idx + 1, text))  # 1-indexed

    return page_texts


def extract_text(
    epub_path: str,
    skip_references: bool = True,
    chapter_range: tuple[int, int] | None = None,
) -> str:
    """Extract text from an EPUB file.

    Args:
        epub_path: Path to the .epub file.
        skip_references: If True, truncate at References/Bibliography.
        chapter_range: Optional (start, end) 1-indexed inclusive range of spine items.

    Returns:
        Extracted plain text.
    """
    path = Path(epub_path)
    if not path.exists():
        raise FileNotFoundError(f"EPUB not found: {epub_path}")

    book = ep.read_epub(epub_path, options={"ignore_ncx": True})
    spine_ids = [item_id for item_id, _linear in book.spine]

    # Select spine items
    if chapter_range is not None:
        start, end = chapter_range
        indices = list(range(max(0, start - 1), min(end, len(spine_ids))))
    else:
        indices = list(range(len(spine_ids)))

    items_by_id = {item.get_id(): item for item in book.get_items()}

    parts = []
    for idx in indices:
        if idx >= len(spine_ids):
            continue
        item_id = spine_ids[idx]
        item = items_by_id.get(item_id)
        if item is None:
            continue
        content = item.get_content()
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        if text.strip():
            parts.append(text)

    full_text = "\n\n".join(parts)

    if skip_references:
        from twinktalks.text_preprocessor import truncate_at_references
        full_text = truncate_at_references(full_text)

    if not full_text or len(full_text.strip()) < 50:
        raise EPUBExtractionError("No text extracted from the EPUB file.")

    return full_text
