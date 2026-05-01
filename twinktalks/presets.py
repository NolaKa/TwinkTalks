"""Voice presets — built-in styles and user favorites."""

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from twinktalks.config import DEFAULT_SPEAKER, DEFAULT_SPEED

PRESETS_FILE = "~/.twinktalks/presets.json"

# Built-in voice style presets
BUILTIN_PRESETS: dict[str, dict] = {
    "Default": {
        "speaker": "aiden",
        "speed": 1.0,
        "instruct": "",
    },
    "Calm Narrator": {
        "speaker": "aiden",
        "speed": 0.9,
        "instruct": "Speak in a calm, professional narrator style. Clear and steady.",
    },
    "Energetic": {
        "speaker": "ryan",
        "speed": 1.1,
        "instruct": "Speak with energy and enthusiasm, lively and engaging.",
    },
    "Warm & Gentle": {
        "speaker": "serena",
        "speed": 0.9,
        "instruct": "Speak warmly and gently, like reading a bedtime story.",
    },
    "Lecture / Academic": {
        "speaker": "aiden",
        "speed": 0.85,
        "instruct": "Speak like a university professor giving a clear, structured lecture. Methodical and articulate.",
    },
    "Audiobook": {
        "speaker": "ryan",
        "speed": 0.95,
        "instruct": "Speak like a professional audiobook narrator. Expressive but natural, with good pacing.",
    },
    "Fast Summary": {
        "speaker": "ryan",
        "speed": 1.3,
        "instruct": "Speak quickly and efficiently, like giving a brief summary.",
    },
    "Whisper": {
        "speaker": "sohee",
        "speed": 0.8,
        "instruct": "Speak softly in a hushed, intimate whisper.",
    },
}


@dataclass
class VoicePreset:
    """A saved voice preset."""
    name: str
    speaker: str
    speed: float
    instruct: str


def get_builtin_names() -> list[str]:
    """Return names of all built-in presets."""
    return list(BUILTIN_PRESETS.keys())


def get_builtin(name: str) -> dict | None:
    """Get a built-in preset by name."""
    return BUILTIN_PRESETS.get(name)


def _presets_path() -> Path:
    return Path(PRESETS_FILE).expanduser()


def load_user_presets() -> list[VoicePreset]:
    """Load user-saved presets from disk."""
    path = _presets_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return [VoicePreset(**p) for p in data]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def save_user_preset(preset: VoicePreset):
    """Save a new user preset. Overwrites if name already exists."""
    presets = load_user_presets()
    presets = [p for p in presets if p.name != preset.name]
    presets.append(preset)

    path = _presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(p) for p in presets], indent=2))


def delete_user_preset(name: str):
    """Delete a user preset by name."""
    presets = load_user_presets()
    presets = [p for p in presets if p.name != name]

    path = _presets_path()
    if path.exists():
        path.write_text(json.dumps([asdict(p) for p in presets], indent=2))


def get_all_preset_names() -> list[str]:
    """Return all preset names: built-in + user (prefixed with a star)."""
    names = list(BUILTIN_PRESETS.keys())
    user = load_user_presets()
    for p in user:
        names.append(f"* {p.name}")
    return names


def resolve_preset(name: str) -> dict | None:
    """Resolve a preset name to its settings dict. Handles both built-in and user presets."""
    # Built-in
    if name in BUILTIN_PRESETS:
        return BUILTIN_PRESETS[name]
    # User (strip star prefix)
    clean_name = name.lstrip("* ").strip()
    for p in load_user_presets():
        if p.name == clean_name:
            return {"speaker": p.speaker, "speed": p.speed, "instruct": p.instruct}
    return None
