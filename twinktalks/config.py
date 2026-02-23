"""Centralized configuration for TwinkTalks."""

# Model
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
MODELSCOPE_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
DEFAULT_SPEAKER = "Aiden"
DEFAULT_LANGUAGE = "English"
AVAILABLE_SPEAKERS = [
    "Aiden", "Ryan", "Aria", "Claire", "Emma",
    "Leo", "Mia", "Noah", "Sophia",
]

# Device (Apple Silicon)
DEVICE = "mps"
DTYPE = "float16"
ATTN_IMPL = "sdpa"

# Generation
MAX_NEW_TOKENS = 1024
TOP_K = 50
TOP_P = 1.0
TEMPERATURE = 0.9
REPETITION_PENALTY = 1.05

# Chunking
MAX_CHUNK_CHARS = 500
INTER_SENTENCE_SILENCE_MS = 400
INTER_PARAGRAPH_SILENCE_MS = 800

# PDF extraction
PDF_CROP_MARGIN_TOP = 72       # ~1 inch
PDF_CROP_MARGIN_BOTTOM = 72    # ~1 inch
LAYOUT_X_TOLERANCE = 3
LAYOUT_Y_TOLERANCE = 3

# Speed
DEFAULT_SPEED = 1.0
SPEED_MIN = 0.5
SPEED_MAX = 2.0

# Tables
SKIP_TABLES = False

# Sessions
SESSION_DIR = "~/.twinktalks/sessions"

# Audio
SAMPLE_RATE = 24000
DEFAULT_OUTPUT_FORMAT = "wav"
