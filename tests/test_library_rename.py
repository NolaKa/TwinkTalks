"""Tests for the library rename endpoint helpers."""

import pytest
from fastapi import HTTPException

from twinktalks.api_routes.library import _safe_stem


def test_safe_stem_strips_path_separators():
    assert _safe_stem("evil/../path") == "evil..path"


def test_safe_stem_strips_windows_reserved_chars():
    assert _safe_stem('a:b*c?d"e<f>g|h\\i') == "abcdefghi"


def test_safe_stem_strips_control_chars():
    assert _safe_stem("hello\x00\x1fworld") == "helloworld"


def test_safe_stem_trims_leading_trailing_dots():
    assert _safe_stem("...hidden...") == "hidden"


def test_safe_stem_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        _safe_stem("")
    assert exc.value.status_code == 400


def test_safe_stem_rejects_only_unsafe():
    with pytest.raises(HTTPException) as exc:
        _safe_stem("///")
    assert exc.value.status_code == 400


def test_safe_stem_preserves_unicode():
    assert _safe_stem("Książka — rozdział 1") == "Książka — rozdział 1"


def test_safe_stem_preserves_spaces_and_dashes():
    assert _safe_stem("My Audio (final - v2)") == "My Audio (final - v2)"
