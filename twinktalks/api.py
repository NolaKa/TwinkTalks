"""FastAPI backend for TwinkTalks — replaces the Gradio web UI.

Wraps the existing Python pipeline (extractor, chunker, tts_engine, presets,
session, book_metadata) and exposes it over HTTP + SSE so the React frontend
in `frontend/` can consume it.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from twinktalks.api_routes import (
    files,
    jobs,
    library,
    static_data,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="TwinkTalks",
        description="Local-first PDF/EPUB → audiobook backend",
        version="0.2.0",
    )

    # Dev: Vite serves on :5173, FastAPI on :7860 — allow CORS so they can talk.
    # Prod: Vite-built assets are served by FastAPI itself, same origin, no CORS needed.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.include_router(static_data.router, prefix="/api")
    app.include_router(files.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(library.router, prefix="/api")

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.2.0"}

    # Static frontend (built via `npm run build` into frontend/dist).
    # In dev, this directory may not exist — that's fine, Vite handles it.
    dist = Path(__file__).parent.parent / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

        @app.get("/")
        def root_index():
            return FileResponse(str(dist / "index.html"))

        @app.exception_handler(404)
        def spa_fallback(request, exc):
            # Only fall back to the SPA for non-API routes; API 404s stay JSON.
            if request.url.path.startswith("/api/"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            return FileResponse(str(dist / "index.html"))

    return app


app = create_app()


def main():
    """Entry point for `twinktalks-server` CLI."""
    import uvicorn
    uvicorn.run(
        "twinktalks.api:app",
        host="0.0.0.0",
        port=7860,
        reload=False,
    )


if __name__ == "__main__":
    main()
