"""Extract title, author, and cover art from PDF and EPUB documents."""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BookMetadata:
    """Document-level metadata used to tag exported audio."""

    title: str | None = None
    author: str | None = None
    cover_image: bytes | None = None
    cover_mime: str | None = None  # "image/jpeg" or "image/png"

    def has_cover(self) -> bool:
        return self.cover_image is not None and self.cover_mime is not None


def extract_metadata(file_path: str) -> BookMetadata:
    """Read metadata from a PDF or EPUB. Missing fields stay None."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return _from_pdf(file_path)
    if ext == ".epub":
        return _from_epub(file_path)
    return BookMetadata()


def _from_pdf(path: str) -> BookMetadata:
    try:
        import fitz
    except ImportError:
        return BookMetadata()

    try:
        doc = fitz.open(path)
        meta = doc.metadata or {}
        title = (meta.get("title") or "").strip() or None
        author = (meta.get("author") or "").strip() or None

        # PDFs rarely embed a cover image directly. Render the first page as a
        # PNG and use it as a stand-in — better than no artwork in the player.
        cover_image, cover_mime = _render_first_page_as_cover(doc)
        doc.close()
        return BookMetadata(title=title, author=author, cover_image=cover_image, cover_mime=cover_mime)
    except Exception as e:
        logger.warning("PDF metadata extraction failed for %s: %s", Path(path).name, e)
        return BookMetadata()


def _render_first_page_as_cover(doc) -> tuple[bytes | None, str | None]:
    """Rasterize page 1 to PNG. Returns (None, None) on failure."""
    try:
        if len(doc) == 0:
            return None, None
        page = doc[0]
        # Aim for ~600px on the long edge — large enough to look good in players,
        # small enough to keep audio file size reasonable.
        zoom = min(600 / page.rect.width, 600 / page.rect.height, 2.0)
        import fitz
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png"), "image/png"
    except Exception as e:
        logger.warning("Could not render PDF cover: %s", e)
        return None, None


def _from_epub(path: str) -> BookMetadata:
    try:
        from ebooklib import epub as ep
    except ImportError:
        return BookMetadata()

    try:
        book = ep.read_epub(path, options={"ignore_ncx": True})
        title = _first_dc_value(book, "title")
        author = _first_dc_value(book, "creator")
        cover_image, cover_mime = _epub_cover(book)
        return BookMetadata(title=title, author=author, cover_image=cover_image, cover_mime=cover_mime)
    except Exception as e:
        logger.warning("EPUB metadata extraction failed for %s: %s", Path(path).name, e)
        return BookMetadata()


def _first_dc_value(book, key: str) -> str | None:
    """Return the first Dublin Core value for a key, or None."""
    entries = book.get_metadata("DC", key)
    if not entries:
        return None
    value, _attrs = entries[0]
    return value.strip() or None


def _epub_cover(book) -> tuple[bytes | None, str | None]:
    """Find the cover image: explicit OPF cover-image property wins; otherwise
    the first item whose name suggests it's a cover."""
    cover_id = None
    for name, value in book.get_metadata("OPF", "meta") or []:
        # Some EPUBs declare <meta name="cover" content="cover-id"/>
        attrs = value if isinstance(value, dict) else {}
        if attrs.get("name") == "cover":
            cover_id = attrs.get("content")
            break

    if cover_id:
        item = book.get_item_with_id(cover_id)
        if item is not None:
            return item.get_content(), item.media_type

    # Fallback: heuristic search by name
    for item in book.get_items():
        media_type = getattr(item, "media_type", "") or ""
        name = getattr(item, "file_name", "") or ""
        if media_type.startswith("image/") and "cover" in name.lower():
            return item.get_content(), media_type

    return None, None
