"""Extract text from PDFs with proper reading order for multi-column layouts."""

import re
from pathlib import Path

import pdfplumber

from twinktalks.config import (
    PDF_CROP_MARGIN_TOP,
    PDF_CROP_MARGIN_BOTTOM,
    LAYOUT_X_TOLERANCE,
    LAYOUT_Y_TOLERANCE,
)


class ExtractionError(Exception):
    """Raised when PDF text extraction fails."""


def get_page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF file."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)


def extract_text(
    pdf_path: str,
    skip_references: bool = True,
    max_pages: int | None = None,
    page_range: tuple[int, int] | None = None,
    skip_tables: bool = False,
) -> str:
    """Extract text from a PDF file.

    Uses pdfplumber with layout mode for multi-column support.
    Falls back to PyMuPDF if pdfplumber fails.

    Args:
        page_range: Optional (start, end) tuple, 1-indexed inclusive.
                    Overrides max_pages if provided.
        skip_tables: If True, exclude text inside detected tables.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {pdf_path}")

    text = _extract_with_pdfplumber(path, max_pages, page_range, skip_tables)

    if not text or len(text.strip()) < 50:
        text = _extract_with_pymupdf(path, max_pages, page_range)

    if not text or len(text.strip()) < 50:
        raise ExtractionError(
            "No text extracted. The PDF may be image-based (scanned). "
            "OCR is not currently supported."
        )

    if skip_references:
        text = _truncate_at_references(text)

    return text


def _select_pages(all_pages: list, max_pages: int | None, page_range: tuple[int, int] | None) -> list:
    """Select pages based on range or max_pages."""
    if page_range:
        start, end = page_range
        # Convert 1-indexed inclusive to 0-indexed slice
        return all_pages[max(0, start - 1):end]
    if max_pages:
        return all_pages[:max_pages]
    return all_pages


def _filter_out_table_chars(page, cropped):
    """Return a filtered page that excludes characters inside table bounding boxes."""
    tables = cropped.find_tables()
    if not tables:
        return cropped

    table_bboxes = [t.bbox for t in tables]

    def _char_outside_tables(char):
        cx, cy = float(char["x0"]), float(char["top"])
        for x0, top, x1, bottom in table_bboxes:
            if x0 <= cx <= x1 and top <= cy <= bottom:
                return False
        return True

    return cropped.filter(_char_outside_tables)


def _extract_with_pdfplumber(
    path: Path,
    max_pages: int | None,
    page_range: tuple[int, int] | None = None,
    skip_tables: bool = False,
) -> str:
    """Extract using pdfplumber with layout mode and page cropping."""
    pages_text = []
    try:
        with pdfplumber.open(path) as pdf:
            page_list = _select_pages(pdf.pages, max_pages, page_range)
            for page in page_list:
                # Crop to remove headers and footers
                crop_box = (
                    0,
                    min(PDF_CROP_MARGIN_TOP, page.height * 0.15),
                    page.width,
                    page.height - min(PDF_CROP_MARGIN_BOTTOM, page.height * 0.15),
                )
                cropped = page.crop(crop_box)

                if skip_tables:
                    cropped = _filter_out_table_chars(page, cropped)

                text = cropped.extract_text(
                    layout=True,
                    x_tolerance=LAYOUT_X_TOLERANCE,
                    y_tolerance=LAYOUT_Y_TOLERANCE,
                )
                if text:
                    pages_text.append(text)
    except Exception:
        return ""

    return "\n\n".join(pages_text)


def _extract_with_pymupdf(path: Path, max_pages: int | None, page_range: tuple[int, int] | None = None) -> str:
    """Fallback extraction using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        return ""

    pages_text = []
    try:
        doc = fitz.open(str(path))
        if page_range:
            start, end = page_range
            indices = range(max(0, start - 1), min(end, len(doc)))
        else:
            count = min(max_pages, len(doc)) if max_pages else len(doc)
            indices = range(count)
        for i in indices:
            page = doc[i]
            # Crop margins
            rect = page.rect
            clip = fitz.Rect(
                rect.x0,
                rect.y0 + min(PDF_CROP_MARGIN_TOP, rect.height * 0.15),
                rect.x1,
                rect.y1 - min(PDF_CROP_MARGIN_BOTTOM, rect.height * 0.15),
            )
            text = page.get_text("text", clip=clip)
            if text:
                pages_text.append(text)
        doc.close()
    except Exception:
        return ""

    return "\n\n".join(pages_text)


def _truncate_at_references(text: str) -> str:
    """Truncate text at the References/Bibliography section."""
    pattern = r"\n\s*(?:References|Bibliography|REFERENCES|BIBLIOGRAPHY)\s*\n"
    match = re.search(pattern, text)
    if match:
        return text[: match.start()].strip()
    return text
