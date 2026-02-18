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


def extract_text(
    pdf_path: str,
    skip_references: bool = True,
    max_pages: int | None = None,
) -> str:
    """Extract text from a PDF file.

    Uses pdfplumber with layout mode for multi-column support.
    Falls back to PyMuPDF if pdfplumber fails.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {pdf_path}")

    text = _extract_with_pdfplumber(path, max_pages)

    if not text or len(text.strip()) < 50:
        text = _extract_with_pymupdf(path, max_pages)

    if not text or len(text.strip()) < 50:
        raise ExtractionError(
            "No text extracted. The PDF may be image-based (scanned). "
            "OCR is not currently supported."
        )

    if skip_references:
        text = _truncate_at_references(text)

    return text


def _extract_with_pdfplumber(path: Path, max_pages: int | None) -> str:
    """Extract using pdfplumber with layout mode and page cropping."""
    pages_text = []
    try:
        with pdfplumber.open(path) as pdf:
            page_list = pdf.pages[:max_pages] if max_pages else pdf.pages
            for page in page_list:
                # Crop to remove headers and footers
                crop_box = (
                    0,
                    min(PDF_CROP_MARGIN_TOP, page.height * 0.15),
                    page.width,
                    page.height - min(PDF_CROP_MARGIN_BOTTOM, page.height * 0.15),
                )
                cropped = page.crop(crop_box)
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


def _extract_with_pymupdf(path: Path, max_pages: int | None) -> str:
    """Fallback extraction using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        return ""

    pages_text = []
    try:
        doc = fitz.open(str(path))
        page_count = min(max_pages, len(doc)) if max_pages else len(doc)
        for i in range(page_count):
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
