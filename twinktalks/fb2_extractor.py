"""Extract text from FictionBook (.fb2) files — pure XML, no extra deps."""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from twinktalks.toc import Chapter

logger = logging.getLogger(__name__)

# FictionBook 2.0/2.1 namespace. Old files sometimes omit it; we handle both.
_FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"


def _local_name(tag: str) -> str:
    """Strip the namespace from an ElementTree tag like '{ns}p' → 'p'."""
    return tag.rsplit("}", 1)[-1]


def _parse(file_path: str) -> ET.Element:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    tree = ET.parse(str(path))
    return tree.getroot()


def _iter_paragraphs(elem: ET.Element):
    """Yield all <p>/<v>/<subtitle> texts in document order under the body."""
    for child in elem.iter():
        name = _local_name(child.tag)
        if name in ("p", "v", "subtitle", "text-author"):
            text = "".join(child.itertext()).strip()
            if text:
                yield text


def extract_text(file_path: str, **kwargs) -> str:
    root = _parse(file_path)
    bodies = [el for el in root.iter() if _local_name(el.tag) == "body"]
    parts: list[str] = []
    for body in bodies:
        # Skip auxiliary bodies (notes, footnotes) — main body has no `name` attr.
        if body.get("name") in ("notes", "comments"):
            continue
        for paragraph in _iter_paragraphs(body):
            parts.append(paragraph)
    return "\n\n".join(parts)


def extract_text_by_page(file_path: str, **kwargs) -> list[tuple[int, str]]:
    text = extract_text(file_path, **kwargs)
    return [(1, text)] if text.strip() else []


def get_item_count(file_path: str) -> int:
    return 1


def _section_title(section: ET.Element) -> str | None:
    for child in section:
        if _local_name(child.tag) == "title":
            text = " ".join("".join(p.itertext()).strip()
                            for p in child if "".join(p.itertext()).strip())
            text = text or "".join(child.itertext()).strip()
            return text or None
    return None


def _walk_sections(parent: ET.Element, level: int, out: list[Chapter]):
    for child in parent:
        if _local_name(child.tag) != "section":
            continue
        title = _section_title(child)
        if title:
            out.append(Chapter(title=title, level=level, start_page=1, end_page=1))
        _walk_sections(child, level + 1, out)


def extract_toc(file_path: str) -> list[Chapter]:
    """Top-level <section> tags inside <body> become chapters; nested sections get higher levels."""
    try:
        root = _parse(file_path)
    except Exception as e:
        logger.warning("FB2 parse failed for %s: %s", Path(file_path).name, e)
        return []
    bodies = [el for el in root.iter()
              if _local_name(el.tag) == "body" and el.get("name") not in ("notes", "comments")]
    chapters: list[Chapter] = []
    for body in bodies:
        _walk_sections(body, 1, chapters)
    return chapters
