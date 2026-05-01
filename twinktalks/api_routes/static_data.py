"""Static reference data for the UI: voices, languages, formats, presets."""

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from twinktalks.presets import (
    BUILTIN_PRESETS,
    VoicePreset,
    delete_user_preset,
    load_user_presets,
    save_user_preset,
)

router = APIRouter(tags=["static"])


# All nine Qwen3-TTS-CustomVoice speakers, surfaced verbatim. id == speaker so
# the UI and the model talk about the same identifier — no translation table,
# no "supported speakers" mismatch like the one that bit the early build.
# Display names are the raw IDs cleaned up for capitalization (underscores to
# spaces, title-cased). Avatar tags are best-effort character hints; users
# should preview-and-pick rather than rely on the labels.
_VOICES = [
    {"id": "aiden",    "name": "Aiden",    "speaker": "aiden",    "tag": "Warm",      "avatarColor": "#e5b8a3"},
    {"id": "dylan",    "name": "Dylan",    "speaker": "dylan",    "tag": "Deep",      "avatarColor": "#a3b3d4"},
    {"id": "eric",     "name": "Eric",     "speaker": "eric",     "tag": "Bright",    "avatarColor": "#f4d8b3"},
    {"id": "ono_anna", "name": "Anna",     "speaker": "ono_anna", "tag": "Calm",      "avatarColor": "#b3d4c5"},
    {"id": "ryan",     "name": "Ryan",     "speaker": "ryan",     "tag": "Narrator",  "avatarColor": "#c8b3d4"},
    {"id": "serena",   "name": "Serena",   "speaker": "serena",   "tag": "Gentle",    "avatarColor": "#d4e3c5"},
    {"id": "sohee",    "name": "Sohee",    "speaker": "sohee",    "tag": "Whisper",   "avatarColor": "#e0d4a3"},
    {"id": "uncle_fu", "name": "Uncle Fu", "speaker": "uncle_fu", "tag": "Mature",    "avatarColor": "#c5d4f0"},
    {"id": "vivian",   "name": "Vivian",   "speaker": "vivian",   "tag": "Lively",    "avatarColor": "#f0c6e0"},
]

_LANGUAGES = [
    {"id": "auto",       "name": "Auto"},
    {"id": "English",    "name": "English"},
    {"id": "Chinese",    "name": "Chinese"},
    {"id": "Japanese",   "name": "Japanese"},
    {"id": "Korean",     "name": "Korean"},
    {"id": "German",     "name": "German"},
    {"id": "French",     "name": "French"},
    {"id": "Russian",    "name": "Russian"},
    {"id": "Portuguese", "name": "Portuguese"},
    {"id": "Spanish",    "name": "Spanish"},
    {"id": "Italian",    "name": "Italian"},
]


def resolve_voice_to_speaker(voice_id: str) -> str:
    """Translate a UI voice slug (e.g. 'sage') to a Qwen speaker name (e.g. 'Mia')."""
    for v in _VOICES:
        if v["id"] == voice_id:
            return v["speaker"]
    # Allow callers to pass a raw Qwen speaker name as a fallback.
    return voice_id


@router.get("/voices")
def list_voices() -> list[dict]:
    return _VOICES


@router.get("/languages")
def list_languages() -> list[dict]:
    return _LANGUAGES


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
