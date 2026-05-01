"""Extract text from standalone HTML files."""

from pathlib import Path

from bs4 import BeautifulSoup

from twinktalks.toc import Chapter


def _read_soup(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")


def extract_text(file_path: str, **kwargs) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    soup = _read_soup(path)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def extract_text_by_page(file_path: str, **kwargs) -> list[tuple[int, str]]:
    text = extract_text(file_path, **kwargs)
    return [(1, text)] if text.strip() else []


def get_item_count(file_path: str) -> int:
    return 1


def extract_toc(file_path: str) -> list[Chapter]:
    """Build a TOC from h1-h3 elements."""
    path = Path(file_path)
    if not path.exists():
        return []
    soup = _read_soup(path)
    chapters: list[Chapter] = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        level = int(h.name[1])
        title = h.get_text(strip=True)
        if title:
            chapters.append(Chapter(title=title, level=level, start_page=1, end_page=1))
    return chapters
