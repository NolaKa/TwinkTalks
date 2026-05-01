"""File upload + metadata + preview endpoints."""

import logging
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel

from twinktalks.book_metadata import extract_metadata
from twinktalks.extractor import (
    SUPPORTED_EXTENSIONS,
    extract_text,
    extract_toc,
    get_item_count,
)
from twinktalks.pdf_extractor import ExtractionError
from twinktalks.text_preprocessor import preprocess
from twinktalks.toc import Chapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])

# Words per minute used for the duration estimate shown on the FileCard.
_WPM = 150


@dataclass
class StoredFile:
    id: str
    name: str
    ext: str
    size_bytes: int
    path: Path
    item_count: int
    title: str | None
    author: str | None
    cover_image: bytes | None = None
    cover_mime: str | None = None
    toc: list[Chapter] = field(default_factory=list)
    needs_ocr: bool = False  # PDF couldn't be extracted (likely scanned)
    # Cached on first preview to avoid re-extracting on every UI call.
    _cached_text: str | None = None


_STORE: dict[str, StoredFile] = {}


def _upload_dir() -> Path:
    d = Path.home() / ".twinktalks" / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


class ChapterOut(BaseModel):
    title: str
    level: int
    start: int
    end: int


class FileMetadata(BaseModel):
    id: str
    name: str
    ext: str
    size_bytes: int
    item_count: int
    word_count: int
    est_duration_s: int
    title: str | None = None
    author: str | None = None
    has_cover: bool = False
    needs_ocr: bool = False  # heuristic: PDF has no extractable text layer
    toc: list[ChapterOut] = []


def _to_metadata(stored: StoredFile, word_count: int) -> FileMetadata:
    return FileMetadata(
        id=stored.id,
        name=stored.name,
        ext=stored.ext,
        size_bytes=stored.size_bytes,
        item_count=stored.item_count,
        word_count=word_count,
        est_duration_s=int(round(word_count / _WPM * 60)) if word_count else 0,
        title=stored.title,
        author=stored.author,
        has_cover=stored.cover_image is not None,
        needs_ocr=stored.needs_ocr,
        toc=[
            ChapterOut(title=c.title, level=c.level, start=c.start_page, end=c.end_page)
            for c in stored.toc
        ],
    )


def _get_or_404(file_id: str) -> StoredFile:
    stored = _STORE.get(file_id)
    if stored is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"File not found: {file_id}")
    return stored


def _ensure_text(stored: StoredFile, **kwargs) -> str:
    """Run extract+preprocess and cache. kwargs override defaults per call."""
    if stored._cached_text is not None and not kwargs:
        return stored._cached_text
    raw = extract_text(str(stored.path), **kwargs)
    text = preprocess(raw)
    if not kwargs:
        stored._cached_text = text
    return text


@router.post("", status_code=201, response_model=FileMetadata)
async def upload(file: UploadFile = File(...)) -> FileMetadata:
    if not file.filename:
        raise HTTPException(400, "Missing filename.")
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            415,
            f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    file_id = uuid.uuid4().hex[:12]
    target_dir = _upload_dir() / file_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / file.filename

    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        item_count = get_item_count(str(target))
    except Exception as e:
        logger.warning("Item count failed for %s: %s", target.name, e)
        item_count = 1

    try:
        toc = extract_toc(str(target))
    except Exception as e:
        logger.warning("TOC extraction failed for %s: %s", target.name, e)
        toc = []

    meta = extract_metadata(str(target))
    stored = StoredFile(
        id=file_id,
        name=file.filename,
        ext=ext,
        size_bytes=target.stat().st_size,
        path=target,
        item_count=item_count,
        title=meta.title,
        author=meta.author,
        cover_image=meta.cover_image,
        cover_mime=meta.cover_mime,
        toc=toc,
    )
    _STORE[file_id] = stored

    # Eagerly extract text so the FileCard can show real word count + duration.
    # If extraction fails the way scanned PDFs fail, mark the file as needing OCR
    # so the UI can flip it on automatically — the user shouldn't have to know
    # about Tesseract.
    word_count = 0
    try:
        text = _ensure_text(stored)
        word_count = len(text.split())
    except ExtractionError as e:
        msg = str(e).lower()
        if ext == ".pdf" and ("image-based" in msg or "scanned" in msg or "no text" in msg):
            stored.needs_ocr = True
            logger.info("Marking %s as needs_ocr=True (no text layer)", target.name)
        else:
            logger.warning("Initial extraction failed for %s: %s", target.name, e)
    except Exception as e:
        logger.warning("Initial extraction failed for %s: %s", target.name, e)

    return _to_metadata(stored, word_count)


@router.get("/{file_id}", response_model=FileMetadata)
def get_metadata(file_id: str) -> FileMetadata:
    stored = _get_or_404(file_id)
    text = stored._cached_text or ""
    return _to_metadata(stored, len(text.split()))


class PreviewResponse(BaseModel):
    text: str
    word_count: int
    char_count: int


@router.get("/{file_id}/preview", response_model=PreviewResponse)
def preview_text(
    file_id: str,
    skip_references: bool = True,
    skip_tables: bool = False,
    page_start: int | None = None,
    page_end: int | None = None,
    ocr: bool = False,
    ocr_language: str = "auto",
) -> PreviewResponse:
    stored = _get_or_404(file_id)
    kwargs: dict = {
        "skip_references": skip_references,
        "skip_tables": skip_tables,
        "ocr": ocr,
        "ocr_language": ocr_language,
    }
    if page_start and page_end:
        kwargs["page_range"] = (page_start, page_end)

    text = _ensure_text(stored, **kwargs)
    return PreviewResponse(
        text=text,
        word_count=len(text.split()),
        char_count=len(text),
    )


@router.get("/{file_id}/cover")
def cover(file_id: str) -> Response:
    stored = _get_or_404(file_id)
    if not stored.cover_image:
        raise HTTPException(404, "No cover image for this file.")
    return Response(content=stored.cover_image, media_type=stored.cover_mime or "image/png")


@router.delete("/{file_id}", status_code=204)
def remove(file_id: str) -> None:
    stored = _STORE.pop(file_id, None)
    if stored is None:
        return
    try:
        shutil.rmtree(stored.path.parent, ignore_errors=True)
    except Exception as e:
        logger.warning("Failed to clean upload dir for %s: %s", file_id, e)
