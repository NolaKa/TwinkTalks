"""Library: previously generated audiobooks."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/library", tags=["library"])


_AUDIO_EXTS = {".wav", ".mp3", ".m4b"}
_MEDIA_TYPE = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4b": "audio/mp4"}


def _library_dir() -> Path:
    d = Path.home() / ".twinktalks" / "library"
    d.mkdir(parents=True, exist_ok=True)
    return d


class LibraryEntry(BaseModel):
    id: str  # filename used as stable handle
    name: str
    title: str | None = None
    author: str | None = None
    duration_s: float | None = None
    size_bytes: int
    format: str
    audio_url: str
    cover_url: str | None = None


def _read_tags(path: Path) -> dict:
    """Pull title/author/duration from MP3/M4B/WAV headers; defaults to empty dict."""
    ext = path.suffix.lower()
    out: dict = {"title": None, "author": None, "duration_s": None, "has_cover": False}
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3, ID3NoHeaderError
            from mutagen.mp3 import MP3
            try:
                tags = ID3(str(path))
                if "TIT2" in tags: out["title"] = tags["TIT2"].text[0]
                if "TPE1" in tags: out["author"] = tags["TPE1"].text[0]
                out["has_cover"] = any(k.startswith("APIC") for k in tags.keys())
            except ID3NoHeaderError:
                pass
            out["duration_s"] = round(MP3(str(path)).info.length, 2)
        elif ext == ".m4b":
            from mutagen.mp4 import MP4
            audio = MP4(str(path))
            if "\xa9nam" in audio.tags: out["title"] = audio.tags["\xa9nam"][0]
            if "\xa9ART" in audio.tags: out["author"] = audio.tags["\xa9ART"][0]
            out["has_cover"] = "covr" in audio.tags
            out["duration_s"] = round(audio.info.length, 2)
        elif ext == ".wav":
            import soundfile as sf
            info = sf.info(str(path))
            out["duration_s"] = round(info.duration, 2)
    except Exception as e:
        logger.warning("Could not read tags for %s: %s", path.name, e)
    return out


def _resolve(entry_id: str) -> Path:
    """Resolve a library id (filename) back to a path inside the library dir."""
    library = _library_dir().resolve()
    target = (library / entry_id).resolve()
    if library not in target.parents:
        raise HTTPException(400, "Invalid library id.")
    if not target.exists():
        raise HTTPException(404, "Library entry not found.")
    return target


@router.get("", response_model=list[LibraryEntry])
def list_library() -> list[LibraryEntry]:
    entries: list[LibraryEntry] = []
    for path in sorted(_library_dir().iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.suffix.lower() not in _AUDIO_EXTS:
            continue
        info = _read_tags(path)
        entries.append(LibraryEntry(
            id=path.name,
            name=path.name,
            title=info["title"],
            author=info["author"],
            duration_s=info["duration_s"],
            size_bytes=path.stat().st_size,
            format=path.suffix.lower().lstrip("."),
            audio_url=f"/api/library/{path.name}/audio",
            cover_url=f"/api/library/{path.name}/cover" if info["has_cover"] else None,
        ))
    return entries


@router.get("/{entry_id}/audio")
def stream_audio(entry_id: str) -> FileResponse:
    path = _resolve(entry_id)
    media_type = _MEDIA_TYPE.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(path), media_type=media_type, filename=path.name)


@router.get("/{entry_id}/cover")
def cover(entry_id: str) -> Response:
    path = _resolve(entry_id)
    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3
            tags = ID3(str(path))
            for key, frame in tags.items():
                if key.startswith("APIC"):
                    return Response(content=frame.data, media_type=frame.mime or "image/jpeg")
        elif ext == ".m4b":
            from mutagen.mp4 import MP4
            audio = MP4(str(path))
            if "covr" in audio.tags and audio.tags["covr"]:
                cover = audio.tags["covr"][0]
                mime = "image/png" if cover.imageformat == 14 else "image/jpeg"
                return Response(content=bytes(cover), media_type=mime)
    except Exception as e:
        logger.warning("Cover read failed for %s: %s", path.name, e)
    raise HTTPException(404, "No cover for this entry.")


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: str) -> None:
    path = _resolve(entry_id)
    path.unlink(missing_ok=True)
