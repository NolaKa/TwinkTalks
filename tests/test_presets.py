"""Tests for voice presets."""

import pytest
from unittest.mock import patch
from twinktalks.presets import (
    BUILTIN_PRESETS,
    VoicePreset,
    get_builtin_names,
    get_builtin,
    load_user_presets,
    save_user_preset,
    delete_user_preset,
    get_all_preset_names,
    resolve_preset,
)


class TestBuiltinPresets:
    def test_has_default(self):
        assert "Default" in BUILTIN_PRESETS

    def test_has_multiple(self):
        assert len(BUILTIN_PRESETS) >= 5

    def test_all_have_required_keys(self):
        for name, p in BUILTIN_PRESETS.items():
            assert "speaker" in p, f"{name} missing speaker"
            assert "speed" in p, f"{name} missing speed"
            assert "instruct" in p, f"{name} missing instruct"

    def test_get_builtin_names(self):
        names = get_builtin_names()
        assert "Default" in names
        assert "Calm Narrator" in names

    def test_get_builtin(self):
        from twinktalks.config import AVAILABLE_SPEAKERS
        p = get_builtin("Audiobook")
        assert p is not None
        assert p["speaker"] in AVAILABLE_SPEAKERS

    def test_get_builtin_missing(self):
        assert get_builtin("nonexistent") is None


class TestUserPresets:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "presets.json")
        with patch("twinktalks.presets.PRESETS_FILE", path):
            save_user_preset(VoicePreset("My Voice", "ryan", 0.9, "Speak calmly"))
            presets = load_user_presets()
            assert len(presets) == 1
            assert presets[0].name == "My Voice"
            assert presets[0].instruct == "Speak calmly"

    def test_overwrite_same_name(self, tmp_path):
        path = str(tmp_path / "presets.json")
        with patch("twinktalks.presets.PRESETS_FILE", path):
            save_user_preset(VoicePreset("Test", "ryan", 1.0, "old"))
            save_user_preset(VoicePreset("Test", "aiden", 0.8, "new"))
            presets = load_user_presets()
            assert len(presets) == 1
            assert presets[0].instruct == "new"

    def test_delete(self, tmp_path):
        path = str(tmp_path / "presets.json")
        with patch("twinktalks.presets.PRESETS_FILE", path):
            save_user_preset(VoicePreset("ToDelete", "ryan", 1.0, ""))
            delete_user_preset("ToDelete")
            assert len(load_user_presets()) == 0

    def test_load_empty(self, tmp_path):
        path = str(tmp_path / "presets.json")
        with patch("twinktalks.presets.PRESETS_FILE", path):
            assert load_user_presets() == []


class TestResolvePreset:
    def test_resolve_builtin(self):
        p = resolve_preset("Calm Narrator")
        assert p is not None
        assert "instruct" in p

    def test_resolve_user(self, tmp_path):
        path = str(tmp_path / "presets.json")
        with patch("twinktalks.presets.PRESETS_FILE", path):
            save_user_preset(VoicePreset("Custom", "vivian", 0.7, "whisper"))
            p = resolve_preset("* Custom")
            assert p is not None
            assert p["instruct"] == "whisper"

    def test_resolve_missing(self):
        assert resolve_preset("nonexistent_xyz") is None

    def test_all_preset_names(self, tmp_path):
        path = str(tmp_path / "presets.json")
        with patch("twinktalks.presets.PRESETS_FILE", path):
            save_user_preset(VoicePreset("Mine", "ryan", 1.0, ""))
            names = get_all_preset_names()
            assert "Default" in names
            assert "* Mine" in names
