"""Static reference data for the UI: backends, voices, languages, formats, presets."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from twinktalks.backends import default_backend_name, detect_available, get_backend
from twinktalks.presets import (
    BUILTIN_PRESETS,
    VoicePreset,
    delete_user_preset,
    load_user_presets,
    save_user_preset,
)

router = APIRouter(tags=["static"])


# Hand-tuned overrides for Qwen voices (and any Kokoro voice we want named
# differently than the auto-derived display).
_VOICE_META: dict[str, dict] = {
    "aiden":    {"name": "Aiden",    "tag": "Warm",      "avatarColor": "#e5b8a3"},
    "dylan":    {"name": "Dylan",    "tag": "Deep",      "avatarColor": "#a3b3d4"},
    "eric":     {"name": "Eric",     "tag": "Bright",    "avatarColor": "#f4d8b3"},
    "ono_anna": {"name": "Anna",     "tag": "Calm",      "avatarColor": "#b3d4c5"},
    "ryan":     {"name": "Ryan",     "tag": "Narrator",  "avatarColor": "#c8b3d4"},
    "serena":   {"name": "Serena",   "tag": "Gentle",    "avatarColor": "#d4e3c5"},
    "sohee":    {"name": "Sohee",    "tag": "Whisper",   "avatarColor": "#e0d4a3"},
    "uncle_fu": {"name": "Uncle Fu", "tag": "Mature",    "avatarColor": "#c5d4f0"},
    "vivian":   {"name": "Vivian",   "tag": "Lively",    "avatarColor": "#f0c6e0"},
}

# Kokoro voice id prefix → human language label.
_KOKORO_LANG = {
    "a": "American English", "b": "British English",
    "e": "Spanish",          "f": "French",
    "h": "Hindi",            "i": "Italian",
    "j": "Japanese",         "p": "Portuguese",
    "z": "Mandarin",
}

# Kokoro avatar colors per language so the grid is scannable at a glance.
_KOKORO_COLOR = {
    "a": "#bfdbfe",  # blue
    "b": "#fce7f3",  # pink
    "e": "#fde68a",  # yellow
    "f": "#bbf7d0",  # mint
    "h": "#fbcfe8",  # rose
    "i": "#c7d2fe",  # indigo
    "j": "#fecaca",  # coral
    "p": "#d4e3c5",  # sage
    "z": "#fed7aa",  # peach
}


def _kokoro_voice_payload(voice_id: str) -> dict | None:
    """Auto-derive UI metadata from a Kokoro voice id like 'bf_alice'."""
    if len(voice_id) < 3 or voice_id[1] not in ("f", "m") or voice_id[2] != "_":
        return None
    lang_letter, gender_letter = voice_id[0], voice_id[1]
    lang = _KOKORO_LANG.get(lang_letter)
    if lang is None:
        return None
    gender = "Female" if gender_letter == "f" else "Male"
    name = voice_id[3:].replace("_", " ").title()
    return {
        "id": voice_id,
        "speaker": voice_id,
        "name": name,
        "tag": f"{lang} · {gender}",
        "avatarColor": _KOKORO_COLOR.get(lang_letter, "#d4d4d4"),
        # Extra fields the frontend's voice filter uses.
        "language": lang,
        "gender": gender,
    }


def _voice_payload(voice_id: str) -> dict:
    if voice_id in _VOICE_META:
        meta = _VOICE_META[voice_id]
        return {
            "id": voice_id,
            "speaker": voice_id,
            "name": meta.get("name", voice_id.replace("_", " ").title()),
            "tag": meta.get("tag", ""),
            "avatarColor": meta.get("avatarColor", "#d4d4d4"),
            "language": "",
            "gender": "",
        }
    kokoro = _kokoro_voice_payload(voice_id)
    if kokoro:
        return kokoro
    # Generic fallback for unknown ids.
    return {
        "id": voice_id, "speaker": voice_id,
        "name": voice_id.replace("_", " ").title(),
        "tag": "", "avatarColor": "#d4d4d4",
        "language": "", "gender": "",
    }


def _active_backend():
    """Build a backend instance for metadata queries (cheap — no model load)."""
    name = default_backend_name()
    if name is None:
        return None
    return get_backend(name)


def resolve_voice_to_speaker(voice_id: str) -> str:
    """Pass-through: voice_id == speaker now. Kept for caller compat."""
    return voice_id


# --- /api/backends ----------------------------------------------------------

class BackendInfo(BaseModel):
    name: str
    available: bool
    is_current: bool
    is_cached: bool
    voices: list[str]
    default_voice: str
    languages: list[str]
    default_language: str
    supports_instruct: bool


@router.get("/backends", response_model=list[BackendInfo])
def list_backends() -> list[BackendInfo]:
    available = set(detect_available())
    current = default_backend_name()

    payload: list[BackendInfo] = []
    # Always advertise both backends so the UI can explain what's missing.
    for name in ("qwen", "kokoro"):
        if name in available:
            inst = get_backend(name)
            payload.append(BackendInfo(
                name=name, available=True, is_current=(name == current),
                is_cached=type(inst).is_cached(),
                voices=list(inst.voices),
                default_voice=inst.default_voice,
                languages=list(inst.supported_languages),
                default_language=inst.default_language,
                supports_instruct=inst.supports_instruct,
            ))
        else:
            payload.append(BackendInfo(
                name=name, available=False, is_current=False, is_cached=False,
                voices=[], default_voice="", languages=[],
                default_language="", supports_instruct=False,
            ))
    return payload


@router.get("/voices")
def list_voices() -> list[dict]:
    backend = _active_backend()
    if backend is None:
        return []
    return [_voice_payload(v) for v in backend.voices]


@router.get("/languages")
def list_languages() -> list[dict]:
    backend = _active_backend()
    if backend is None:
        return [{"id": "auto", "name": "Auto"}]
    langs = [{"id": l, "name": l} for l in backend.supported_languages]
    if len(backend.supported_languages) > 1:
        langs = [{"id": "auto", "name": "Auto"}] + langs
    return langs


@router.get("/formats")
def list_formats() -> list[str]:
    return ["wav", "mp3", "m4b"]


class PresetIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    speaker: str
    speed: float = Field(..., ge=0.5, le=2.0)
    instruct: str = ""


class PresetOut(BaseModel):
    name: str
    speaker: str
    speed: float
    instruct: str
    builtin: bool


@router.get("/presets")
def list_presets() -> dict[str, list[PresetOut]]:
    builtin = [
        PresetOut(name=name, builtin=True, **data)
        for name, data in BUILTIN_PRESETS.items()
    ]
    user = [PresetOut(builtin=False, **asdict(p)) for p in load_user_presets()]
    return {"builtin": builtin, "user": user}


@router.post("/presets", status_code=201)
def upsert_preset(preset: PresetIn) -> PresetOut:
    if preset.name in BUILTIN_PRESETS:
        raise HTTPException(409, "Cannot overwrite a built-in preset; choose another name.")
    save_user_preset(VoicePreset(
        name=preset.name, speaker=preset.speaker,
        speed=preset.speed, instruct=preset.instruct,
    ))
    return PresetOut(**preset.model_dump(), builtin=False)


@router.delete("/presets/{name}", status_code=204)
def remove_preset(name: str) -> None:
    if name in BUILTIN_PRESETS:
        raise HTTPException(409, "Built-in presets cannot be deleted.")
    delete_user_preset(name)
