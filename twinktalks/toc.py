"""Table of contents extraction using PyMuPDF."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chapter:
    """A chapter/section from the PDF table of contents."""
    title: str
    level: int
    start_page: int  # 1-indexed
    end_page: int     # 1-indexed, inclusive


def extract_toc(pdf_path: str) -> list[Chapter]:
    """Extract table of contents from a PDF using PyMuPDF.

    Returns a list of Chapter objects with page ranges.
    Empty list if no TOC is found.
    """
    import fitz

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(path))
    toc = doc.get_toc()  # [[level, title, page], ...]
    total_pages = len(doc)
    doc.close()

    if not toc:
        return []

    chapters = []
    for i, (level, title, page) in enumerate(toc):
        # Calculate end_page: next entry's start_page - 1, or total_pages
        if i + 1 < len(toc):
            end_page = toc[i + 1][2] - 1
            # If next chapter starts on same page, use same page as end
            if end_page < page:
                end_page = page
        else:
            end_page = total_pages

        chapters.append(Chapter(
            title=title.strip(),
            level=level,
            start_page=page,
            end_page=end_page,
        ))

    return chapters


def find_chapter(chapters: list[Chapter], query: str) -> Chapter | None:
    """Find a chapter by name (substring match) or 1-based index."""
    if not chapters:
        return None

    # Try as index first
    try:
        idx = int(query) - 1
        if 0 <= idx < len(chapters):
            return chapters[idx]
    except ValueError:
        pass

    # Substring match (case-insensitive)
    query_lower = query.lower()
    for ch in chapters:
        if query_lower in ch.title.lower():
            return ch

    return None


def format_toc(chapters: list[Chapter]) -> str:
    """Format TOC for display."""
    if not chapters:
        return "No table of contents found."

    lines = []
    for i, ch in enumerate(chapters, 1):
        indent = "  " * (ch.level - 1)
        page_info = f"p.{ch.start_page}" if ch.start_page == ch.end_page else f"p.{ch.start_page}-{ch.end_page}"
        lines.append(f"{i:3d}. {indent}{ch.title}  [{page_info}]")
    return "\n".join(lines)
