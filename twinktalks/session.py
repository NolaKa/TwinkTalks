"""Session management for resumable TTS generation."""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from twinktalks.config import SESSION_DIR


@dataclass
class Session:
    """A saved TTS generation session."""
    id: str
    pdf_path: str
    settings: dict  # speaker, language, speed, pages, etc.
    total_chunks: int
    completed_chunk: int  # index of last completed chunk (0-based)
    created_at: str
    updated_at: str


class SessionManager:
    """Manages session persistence in ~/.twinktalks/sessions/."""

    def __init__(self, base_dir: str = SESSION_DIR):
        self.base_dir = Path(base_dir).expanduser()

    def create_session(
        self,
        pdf_path: str,
        total_chunks: int,
        settings: dict,
    ) -> Session:
        """Create a new session and its directory."""
        session_id = uuid.uuid4().hex[:12]
        now = datetime.now().isoformat(timespec="seconds")

        session = Session(
            id=session_id,
            pdf_path=str(pdf_path),
            settings=settings,
            total_chunks=total_chunks,
            completed_chunk=0,
            created_at=now,
            updated_at=now,
        )

        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        self._save_meta(session)

        return session

    def update_progress(self, session: Session, completed_chunk: int):
        """Update the completed chunk index."""
        session.completed_chunk = completed_chunk
        session.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save_meta(session)

    def get_session(self, session_id: str) -> Session | None:
        """Load a session by ID."""
        meta_path = self.base_dir / session_id / "session.json"
        if not meta_path.exists():
            return None
        data = json.loads(meta_path.read_text())
        return Session(**data)

    def get_session_dir(self, session_id: str) -> Path:
        """Return the directory for a session's chunk files."""
        return self.base_dir / session_id

    def list_sessions(self) -> list[Session]:
        """List all saved sessions, newest first."""
        sessions = []
        if not self.base_dir.exists():
            return sessions
        for d in self.base_dir.iterdir():
            if d.is_dir():
                meta = d / "session.json"
                if meta.exists():
                    try:
                        data = json.loads(meta.read_text())
                        sessions.append(Session(**data))
                    except (json.JSONDecodeError, TypeError):
                        continue
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def delete_session(self, session_id: str):
        """Remove a session and its files."""
        import shutil
        session_dir = self.base_dir / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)

    def _save_meta(self, session: Session):
        """Write session metadata to disk."""
        meta_path = self.base_dir / session.id / "session.json"
        meta_path.write_text(json.dumps(asdict(session), indent=2))
