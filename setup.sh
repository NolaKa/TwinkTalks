#!/bin/bash
set -e

# Defaults
BACKEND="qwen"
VENV=".venv"

usage() {
    cat <<'EOF'
Usage: ./setup.sh [--kokoro | --qwen] [--venv PATH]

Sets up TwinkTalks: installs system deps via Homebrew, creates a Python 3.12
virtualenv, installs the chosen TTS backend, and builds the React frontend.

  --qwen          (default) Install the Qwen3-TTS-1.7B backend.
                  Multilingual, supports voice-style prompts, ~3.5 GB model,
                  needs ~6-10 GB RAM during synthesis.
  --kokoro        Install the Kokoro-82M backend instead.
                  English only, no voice-style prompts, ~360 MB model,
                  needs ~1.5 GB RAM, ~10× faster than Qwen.
  --venv PATH     Where to create the virtualenv (default: .venv).
                  Use --venv .venv-kokoro to keep both backends side-by-side
                  in different envs.

Examples:
  ./setup.sh                         # Qwen in .venv
  ./setup.sh --kokoro                # Kokoro in .venv
  ./setup.sh --kokoro --venv .venv-kokoro   # Kokoro alongside an existing Qwen venv
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --kokoro) BACKEND="kokoro"; shift ;;
        --qwen)   BACKEND="qwen";   shift ;;
        --venv)   VENV="$2";        shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

echo "=== TwinkTalks Setup (backend: $BACKEND, venv: $VENV) ==="

# macOS check
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Warning: This project is optimized for macOS with Apple Silicon."
fi

# Homebrew — required for everything else.
if ! command -v brew >/dev/null 2>&1; then
    cat <<'EOF'
Error: Homebrew is required but not installed.

Install Homebrew first by running this in a terminal:

  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Then run ./setup.sh again.
EOF
    exit 1
fi

# Python 3.12. Both backends pin numpy versions that don't ship wheels for
# newer Pythons yet, so we lock to 3.12.
if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Installing Python 3.12 via Homebrew..."
    brew install python@3.12
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "Installing Node.js via Homebrew..."
    brew install node
fi

echo "Installing system audio + OCR dependencies..."
brew install portaudio ffmpeg sox tesseract ghostscript qpdf

echo "Creating Python 3.12 virtual environment at $VENV..."
python3.12 -m venv "$VENV"
# shellcheck disable=SC1090
source "$VENV/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing TwinkTalks with [$BACKEND] backend (this can take a few minutes)..."
pip install -e ".[$BACKEND]"

echo "Installing OCR support..."
pip install ocrmypdf

echo "Downloading NLTK tokenizer data..."
python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

echo ""
echo "Checking compute device..."
python - <<'PY'
try:
    import torch
    print(f"  PyTorch device: MPS available = {torch.backends.mps.is_available()}")
except Exception:
    pass
PY

mkdir -p output input

echo ""
echo "Building frontend (Vite)..."
(cd frontend && npm install --silent && npm run build)

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Activate this venv:  source $VENV/bin/activate"
echo "Run web UI:          twinktalks-server   →  http://localhost:7860"
echo "Run CLI:             twinktalks input/paper.pdf output/audio.mp3"
echo ""
if [[ "$BACKEND" == "kokoro" ]]; then
    cat <<'EOF'
You picked Kokoro: ~10× faster, English only. Voice-style prompts are
disabled (Kokoro doesn't accept them). The Voice block in the web UI shows
9 Kokoro voices (af_heart, af_bella, am_adam, bm_george, ...).
EOF
else
    cat <<'EOF'
You picked Qwen: multilingual, supports voice-style prompts. The Voice
block in the web UI shows 9 Qwen voices (aiden, dylan, eric, ono_anna,
ryan, serena, sohee, uncle_fu, vivian).

Want a faster English-only alternative? Add Kokoro alongside:
    ./setup.sh --kokoro --venv .venv-kokoro
EOF
fi
