"""Route file extraction to the appropriate extractor based on file type."""

from pathlib import Path

from twinktalks.toc import Chapter

SUPPORTED_EXTENSIONS = {
    ".pdf", ".epub",
    ".md", ".txt",
    ".html", ".htm",
    ".docx", ".rtf", ".fb2",
}

# Plain-text formats: PDF-specific kwargs are dropped silently.
_PLAIN_TEXT_EXTS = {".md", ".txt"}
_HTML_EXTS = {".html", ".htm"}


def detect_file_type(file_path: str) -> str:
    """Return the lowercase file extension, validated against supported types."""
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return ext


def _strip_pdf_kwargs(kwargs: dict) -> dict:
    """Remove PDF-only options that don't apply to other formats."""
    for key in ("page_range", "max_pages", "skip_tables", "chapter_range",
                "ocr", "ocr_language"):
        kwargs.pop(key, None)
    return kwargs


def extract_text(file_path: str, **kwargs) -> str:
    """Extract text from a file, routing to the appropriate extractor."""
    ext = detect_file_type(file_path)
    if ext == ".pdf":
        from twinktalks.pdf_extractor import extract_text as pdf_extract
        return pdf_extract(file_path, **kwargs)
    if ext == ".epub":
        from twinktalks.epub_extractor import extract_text as epub_extract
        if "page_range" in kwargs:
            kwargs["chapter_range"] = kwargs.pop("page_range")
        kwargs.pop("max_pages", None)
        kwargs.pop("skip_tables", None)
        kwargs.pop("ocr", None)
        kwargs.pop("ocr_language", None)
        return epub_extract(file_path, **kwargs)
    if ext in _PLAIN_TEXT_EXTS:
        from twinktalks.text_extractor import extract_text as text_extract
        return text_extract(file_path, **_strip_pdf_kwargs(kwargs))
    if ext in _HTML_EXTS:
        from twinktalks.html_extractor import extract_text as html_extract
        return html_extract(file_path, **_strip_pdf_kwargs(kwargs))
    if ext == ".docx":
        from twinktalks.docx_extractor import extract_text as docx_extract
        return docx_extract(file_path, **_strip_pdf_kwargs(kwargs))
    if ext == ".rtf":
        from twinktalks.rtf_extractor import extract_text as rtf_extract
        return rtf_extract(file_path, **_strip_pdf_kwargs(kwargs))
    if ext == ".fb2":
        from twinktalks.fb2_extractor import extract_text as fb2_extract
        return fb2_extract(file_path, **_strip_pdf_kwargs(kwargs))
    return ""


def extract_text_by_page(file_path: str, **kwargs) -> list[tuple[int, str]]:
    """Extract text as page-annotated list: [(page_num, text), ...]."""
    ext = detect_file_type(file_path)
    if ext == ".pdf":
        from twinktalks.pdf_extractor import extract_text_by_page as pdf_by_page
        return pdf_by_page(file_path, **kwargs)
    if ext == ".epub":
        from twinktalks.epub_extractor import extract_text_by_item as epub_by_item
        if "page_range" in kwargs:
            kwargs["chapter_range"] = kwargs.pop("page_range")
        kwargs.pop("max_pages", None)
        kwargs.pop("skip_tables", None)
        kwargs.pop("ocr", None)
        kwargs.pop("ocr_language", None)
        return epub_by_item(file_path, **kwargs)
    if ext in _PLAIN_TEXT_EXTS:
        from twinktalks.text_extractor import extract_text_by_page as text_by_page
        return text_by_page(file_path, **_strip_pdf_kwargs(kwargs))
    if ext in _HTML_EXTS:
        from twinktalks.html_extractor import extract_text_by_page as html_by_page
        return html_by_page(file_path, **_strip_pdf_kwargs(kwargs))
    if ext == ".docx":
        from twinktalks.docx_extractor import extract_text_by_page as docx_by_page
        return docx_by_page(file_path, **_strip_pdf_kwargs(kwargs))
    if ext == ".rtf":
        from twinktalks.rtf_extractor import extract_text_by_page as rtf_by_page
        return rtf_by_page(file_path, **_strip_pdf_kwargs(kwargs))
    if ext == ".fb2":
        from twinktalks.fb2_extractor import extract_text_by_page as fb2_by_page
        return fb2_by_page(file_path, **_strip_pdf_kwargs(kwargs))
    return []


def get_item_count(file_path: str) -> int:
    """Return page count (PDF), chapter count (EPUB), or 1 for flat-text formats."""
    ext = detect_file_type(file_path)
    if ext == ".pdf":
        from twinktalks.pdf_extractor import get_page_count
        return get_page_count(file_path)
    if ext == ".epub":
        from twinktalks.epub_extractor import get_chapter_count
        return get_chapter_count(file_path)
    return 1


def extract_toc(file_path: str) -> list[Chapter]:
    """Extract table of contents from a file."""
    ext = detect_file_type(file_path)
    if ext == ".pdf":
        from twinktalks.toc import extract_toc as pdf_toc
        return pdf_toc(file_path)
    if ext == ".epub":
        from twinktalks.epub_extractor import extract_toc as epub_toc
        return epub_toc(file_path)
    if ext in _PLAIN_TEXT_EXTS:
        from twinktalks.text_extractor import extract_toc as text_toc
        return text_toc(file_path)
    if ext in _HTML_EXTS:
        from twinktalks.html_extractor import extract_toc as html_toc
        return html_toc(file_path)
    if ext == ".docx":
        from twinktalks.docx_extractor import extract_toc as docx_toc
        return docx_toc(file_path)
    if ext == ".fb2":
        from twinktalks.fb2_extractor import extract_toc as fb2_toc
        return fb2_toc(file_path)
    # .rtf has no structured TOC
    return []
