"""Tests for session management."""

import pytest
import tempfile
from pathlib import Path

from twinktalks.session import SessionManager


@pytest.fixture
def mgr(tmp_path):
    return SessionManager(base_dir=str(tmp_path / "sessions"))


class TestSessionManager:
    def test_create_session(self, mgr):
        session = mgr.create_session(
            pdf_path="/tmp/test.pdf",
            total_chunks=10,
            settings={"speaker": "Aiden", "speed": 1.0},
        )
        assert session.id
        assert session.total_chunks == 10
        assert session.completed_chunk == 0
        assert session.pdf_path == "/tmp/test.pdf"

    def test_get_session(self, mgr):
        session = mgr.create_session("/tmp/test.pdf", 5, {})
        loaded = mgr.get_session(session.id)
        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.total_chunks == 5

    def test_get_nonexistent(self, mgr):
        assert mgr.get_session("nonexistent") is None

    def test_update_progress(self, mgr):
        session = mgr.create_session("/tmp/test.pdf", 10, {})
        mgr.update_progress(session, 5)
        loaded = mgr.get_session(session.id)
        assert loaded.completed_chunk == 5

    def test_list_sessions(self, mgr):
        mgr.create_session("/tmp/a.pdf", 5, {})
        mgr.create_session("/tmp/b.pdf", 10, {})
        sessions = mgr.list_sessions()
        assert len(sessions) == 2

    def test_list_empty(self, mgr):
        assert mgr.list_sessions() == []

    def test_delete_session(self, mgr):
        session = mgr.create_session("/tmp/test.pdf", 5, {})
        mgr.delete_session(session.id)
        assert mgr.get_session(session.id) is None

    def test_session_dir(self, mgr):
        session = mgr.create_session("/tmp/test.pdf", 5, {})
        d = mgr.get_session_dir(session.id)
        assert d.exists()
        assert d.is_dir()
