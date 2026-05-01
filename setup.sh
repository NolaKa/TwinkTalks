#!/bin/bash
set -e

echo "=== TwinkTalks Setup ==="

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

# Python 3.12. We pin to 3.12 because numpy<2.0 (required by qwen-tts) does
# not ship wheels for newer Python versions yet — the install will break.
if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Installing Python 3.12 via Homebrew..."
    brew install python@3.12
fi

# Node.js — needed to build the React frontend.
if ! command -v npm >/dev/null 2>&1; then
    echo "Installing Node.js via Homebrew..."
    brew install node
fi

# Audio + OCR system deps. brew install is idempotent and prints a friendly
# "already installed" line, so we don't suppress it.
echo "Installing system audio + OCR dependencies..."
brew install portaudio ffmpeg sox tesseract ghostscript qpdf

# Python venv
echo "Creating Python 3.12 virtual environment..."
python3.12 -m venv .venv
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
# Optional OCR dep — we already installed the system tools above, so this
# pulls in the Python wrapper so --ocr / Force OCR works out of the box.
pip install ocrmypdf

# NLTK data
echo "Downloading NLTK tokenizer data..."
python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

# MPS check (informational)
echo ""
echo "Checking MPS (Metal) availability..."
python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"

mkdir -p output

# Frontend
echo ""
echo "Building frontend (Vite)..."
(cd frontend && npm install --silent && npm run build)

echo ""
echo "=== Setup complete! ==="
echo "Activate venv:  source .venv/bin/activate"
echo "Run CLI:        twinktalks paper.pdf -o output/audio.wav"
echo "Run web UI:     twinktalks-server   →  http://localhost:7860"
echo "Frontend dev:   cd frontend && npm run dev   (with twinktalks-server running)"
