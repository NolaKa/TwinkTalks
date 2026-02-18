"""Route file extraction to the appropriate extractor based on file type."""

from pathlib import Path

from twinktalks.toc import Chapter

SUPPORTED_EXTENSIONS = {".pdf", ".epub"}


def detect_file_type(file_path: str) -> str:
    """Return the lowercase file extension, validated against supported types."""
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return ext


def extract_text(file_path: str, **kwargs) -> str:
    """Extract text from a file, routing to the appropriate extractor."""
    ext = detect_file_type(file_path)
    if ext == ".pdf":
        from twinktalks.pdf_extractor import extract_text as pdf_extract
        return pdf_extract(file_path, **kwargs)
    elif ext == ".epub":
        from twinktalks.epub_extractor import extract_text as epub_extract
        # Map page_range to chapter_range for EPUB
        if "page_range" in kwargs:
            kwargs["chapter_range"] = kwargs.pop("page_range")
        # Remove PDF-specific kwargs that EPUB doesn't support
        kwargs.pop("max_pages", None)
        kwargs.pop("skip_tables", None)
        return epub_extract(file_path, **kwargs)


def get_item_count(file_path: str) -> int:
    """Return page count (PDF) or chapter count (EPUB)."""
    ext = detect_file_type(file_path)
    if ext == ".pdf":
        from twinktalks.pdf_extractor import get_page_count
        return get_page_count(file_path)
    elif ext == ".epub":
        from twinktalks.epub_extractor import get_chapter_count
        return get_chapter_count(file_path)


def extract_toc(file_path: str) -> list[Chapter]:
    """Extract table of contents from a file."""
    ext = detect_file_type(file_path)
    if ext == ".pdf":
        from twinktalks.toc import extract_toc as pdf_toc
        return pdf_toc(file_path)
    elif ext == ".epub":
        from twinktalks.epub_extractor import extract_toc as epub_toc
        return epub_toc(file_path)
    return []
