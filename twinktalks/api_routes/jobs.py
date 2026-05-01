"""Synthesis job endpoints with SSE progress streaming."""

import asyncio
import json
import logging
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from twinktalks.api_routes.files import _STORE as FILE_STORE
from twinktalks.api_routes.static_data import resolve_voice_to_speaker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@dataclass
class Job:
    id: str
    file_id: str
    settings: dict
    status: str = "pending"  # pending | running | done | error | cancelled
    audio_path: Path | None = None
    audio_format: str = "wav"
    error: str | None = None
    queue: "queue.Queue[dict]" = field(default_factory=queue.Queue)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None


_JOBS: dict[str, Job] = {}
_ENGINE = None


def _get_engine(backend_name: str | None = None):
    """Cached TTSEngine — model loads on first synthesize call. If a backend
    different from the cached one is requested, swap (no model preloading)."""
    global _ENGINE
    from twinktalks.tts_engine import TTSEngine
    if _ENGINE is not None and backend_name and _ENGINE.backend.name != backend_name:
        _ENGINE = None  # caller wants the other backend
    if _ENGINE is None:
        _ENGINE = TTSEngine(
            backend=backend_name,
            model_path=os.environ.get("TWINKTALKS_MODEL_PATH"),
        )
    return _ENGINE


def _model_is_cached() -> bool:
    """Best-effort check whether Qwen3-TTS weights are already on disk.

    Returns False if the next load would have to fetch ~3.5 GB from the network.
    Honors HUGGINGFACE_HUB_CACHE / MODELSCOPE_CACHE env vars (which TwinkTalks
    points at ~/.twinktalks/cache/), and also checks the legacy ~/.cache paths
    so users coming from older installs aren't told they need to re-download.
    """
    custom = os.environ.get("TWINKTALKS_MODEL_PATH")
    if custom:
        return Path(custom).expanduser().is_dir()

    hf_candidates = [
        Path(os.environ["HUGGINGFACE_HUB_CACHE"])
        if os.environ.get("HUGGINGFACE_HUB_CACHE") else None,
        Path.home() / ".twinktalks" / "cache" / "huggingface" / "hub",
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    for cache in hf_candidates:
        if cache and (cache / "models--Qwen--Qwen3-TTS-12Hz-1.7B-CustomVoice").exists():
            return True

    ms_candidates = [
        Path(os.environ["MODELSCOPE_CACHE"])
        if os.environ.get("MODELSCOPE_CACHE") else None,
        Path.home() / ".twinktalks" / "cache" / "modelscope",
        Path.home() / ".cache" / "modelscope" / "hub",
    ]
    for cache in ms_candidates:
        if cache and (cache / "Qwen" / "Qwen3-TTS-12Hz-1.7B-CustomVoice").exists():
            return True
    return False


def _model_loaded_in_memory() -> bool:
    return _ENGINE is not None and _ENGINE.model is not None


class JobRequest(BaseModel):
    file_id: str
    voice_id: str = "aiden"
    speed: float = Field(1.0, ge=0.5, le=2.0)
    format: str = "m4b"
    language: str = "Auto"
    instruct: str = ""
    skip_references: bool = True
    skip_tables: bool = False
    page_start: int | None = None
    page_end: int | None = None
    ocr: bool = False
    ocr_language: str = "auto"
    chapter_markers: bool = True
    merge_chapters: bool = False
    preview_only: bool = False
    backend: str | None = None  # 'qwen' | 'kokoro' | None (use default)


class JobCreated(BaseModel):
    job_id: str
    status: str


def _library_dir() -> Path:
    d = Path.home() / ".twinktalks" / "library"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _emit(job: Job, event_type: str, data: dict | None = None) -> None:
    job.queue.put({"type": event_type, "data": data or {}})


def _run_synthesis(job: Job) -> None:
    """Background thread that drives the whole pipeline for one job."""
    from twinktalks.audio_utils import (
        AudioChapter,
        add_chapter_markers,
        add_m4b_chapters,
        embed_metadata,
        save_audio,
    )
    from twinktalks.book_metadata import extract_metadata
    from twinktalks.chunker import chunk_paged_text, chunk_text
    from twinktalks.cli import _map_chunks_to_chapters
    from twinktalks.extractor import extract_text, extract_text_by_page, extract_toc
    from twinktalks.language_detect import resolve_language
    from twinktalks.text_preprocessor import preprocess

    s = job.settings
    stored = FILE_STORE.get(job.file_id)
    if stored is None:
        job.status = "error"
        job.error = f"File not found: {job.file_id}"
        _emit(job, "error", {"message": job.error})
        return

    page_range = None
    if s["page_start"] and s["page_end"]:
        page_range = (s["page_start"], s["page_end"])

    try:
        # When chapter markers are requested we need page-attributed chunks so we
        # can map TOC pages back to audio offsets.
        if s["chapter_markers"] and s["format"] in ("mp3", "m4b"):
            page_texts = extract_text_by_page(
                str(stored.path),
                skip_references=s["skip_references"],
                skip_tables=s["skip_tables"],
                page_range=page_range,
                ocr=s["ocr"],
                ocr_language=s["ocr_language"],
            )
            page_texts = [(pg, preprocess(t)) for pg, t in page_texts]
            text = "\n\n".join(t for _, t in page_texts)
            chunks = chunk_paged_text(page_texts)
        else:
            text = preprocess(extract_text(
                str(stored.path),
                skip_references=s["skip_references"],
                skip_tables=s["skip_tables"],
                page_range=page_range,
                ocr=s["ocr"],
                ocr_language=s["ocr_language"],
            ))
            chunks = chunk_text(text)

        if not chunks:
            job.status = "error"
            job.error = "No text to synthesize."
            _emit(job, "error", {"message": job.error})
            return

        # Preview jobs render only the first chunk so the user can audition the
        # voice in ~10-30 seconds instead of waiting for the full document.
        if s.get("preview_only"):
            chunks = chunks[:1]

        resolved_language = resolve_language(s["language"], text)
        speaker = resolve_voice_to_speaker(s["voice_id"])

        # Tell the UI whether we're about to download or just load — so the
        # user understands why the first generate may take 5+ minutes.
        if not _model_loaded_in_memory():
            _emit(job, "model_loading", {
                "needs_download": not _model_is_cached(),
            })

        engine = _get_engine(s.get("backend"))
        start_time = time.time()
        final_offsets = None
        sample_rate = None
        cumulative = None
        model_load_announced = _model_loaded_in_memory()

        for cumulative, sample_rate, current, total, offsets in engine.synthesize_chunks_streaming(
            chunks,
            language=resolved_language,
            speed=s["speed"],
            instruct=s["instruct"] or "",
            speaker=speaker,
        ):
            if job.cancel_event.is_set():
                job.status = "cancelled"
                _emit(job, "cancelled")
                return

            if not model_load_announced:
                # First iteration means the model finished loading and the first
                # chunk has been synthesized.
                _emit(job, "model_loaded", {})
                model_load_announced = True
                start_time = time.time()  # don't count load time in ETA

            elapsed = time.time() - start_time
            avg = elapsed / current if current else 0
            eta_s = int(round(avg * (total - current)))
            duration_s = len(cumulative) / sample_rate

            _emit(job, "progress", {
                "current": current,
                "total": total,
                "duration_s": round(duration_s, 2),
                "eta_s": eta_s,
            })

            if offsets is not None:
                final_offsets = offsets

        # Save final audio
        ext = s["format"] if s["format"] in ("wav", "mp3", "m4b") else "wav"
        stem = Path(stored.name).stem
        final_path = _library_dir() / f"{stem}_{job.id}.{ext}"
        save_audio(cumulative, str(final_path), sample_rate)

        if ext in ("mp3", "m4b"):
            try:
                meta = extract_metadata(str(stored.path))
                if meta.title or meta.author or meta.has_cover():
                    embed_metadata(str(final_path), meta)
            except Exception as e:
                logger.warning("Metadata embedding failed: %s", e)

        if s["chapter_markers"] and ext in ("mp3", "m4b") and final_offsets:
            try:
                toc_chapters = extract_toc(str(stored.path))
                if toc_chapters:
                    total_ms = int(len(cumulative) * 1000 / sample_rate)
                    audio_chapters = _map_chunks_to_chapters(
                        chunks, final_offsets, toc_chapters, total_ms,
                    )
                    if audio_chapters:
                        if ext == "m4b":
                            add_m4b_chapters(str(final_path), audio_chapters)
                        else:
                            add_chapter_markers(str(final_path), audio_chapters)
            except Exception as e:
                logger.warning("Chapter marker embedding failed: %s", e)

        job.audio_path = final_path
        job.audio_format = ext
        job.status = "done"
        _emit(job, "done", {
            "audio_url": f"/api/jobs/{job.id}/audio",
            "duration_s": round(len(cumulative) / sample_rate, 2),
            "format": ext,
        })
    except Exception as e:
        logger.exception("Job %s failed", job.id)
        job.status = "error"
        job.error = str(e)
        _emit(job, "error", {"message": str(e)})


def _start_job(req: JobRequest, *, preview: bool = False) -> JobCreated:
    if req.file_id not in FILE_STORE:
        raise HTTPException(404, f"File not found: {req.file_id}")

    settings = req.model_dump()
    if preview:
        settings["preview_only"] = True
        settings["format"] = "wav"
        settings["chapter_markers"] = False
        settings["merge_chapters"] = False

    job_id = uuid.uuid4().hex[:12]
    job = Job(id=job_id, file_id=req.file_id, settings=settings, status="running")
    job.thread = threading.Thread(target=_run_synthesis, args=(job,), daemon=True)
    job.thread.start()
    _JOBS[job_id] = job
    return JobCreated(job_id=job_id, status="running")


@router.post("", status_code=201, response_model=JobCreated)
def create_job(req: JobRequest) -> JobCreated:
    return _start_job(req, preview=False)


@router.post("/preview", status_code=201, response_model=JobCreated)
def create_preview(req: JobRequest) -> JobCreated:
    return _start_job(req, preview=True)


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, request: Request) -> EventSourceResponse:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")

    async def events():
        loop = asyncio.get_event_loop()
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await loop.run_in_executor(
                    None, lambda: job.queue.get(timeout=1.0),
                )
            except queue.Empty:
                # Heartbeat keeps the connection alive across reverse proxies.
                yield {"event": "ping", "data": "{}"}
                continue
            yield {"event": event["type"], "data": json.dumps(event["data"])}
            if event["type"] in ("done", "error", "cancelled"):
                break

    return EventSourceResponse(events())


@router.get("/{job_id}")
def job_status(job_id: str) -> dict:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return {
        "job_id": job.id,
        "status": job.status,
        "error": job.error,
        "audio_url": f"/api/jobs/{job.id}/audio" if job.audio_path else None,
        "audio_format": job.audio_format if job.audio_path else None,
    }


@router.get("/{job_id}/audio")
def download_audio(job_id: str) -> FileResponse:
    job = _JOBS.get(job_id)
    if job is None or job.audio_path is None or not job.audio_path.exists():
        raise HTTPException(404, "Audio not available.")
    media_type = {"mp3": "audio/mpeg", "wav": "audio/wav", "m4b": "audio/mp4"}.get(
        job.audio_format, "application/octet-stream",
    )
    return FileResponse(
        str(job.audio_path),
        media_type=media_type,
        filename=job.audio_path.name,
    )


@router.post("/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(job_id: str) -> None:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    job.cancel_event.set()
