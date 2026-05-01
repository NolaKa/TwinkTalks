#!/bin/bash
set -e

echo "=== TwinkTalks Setup ==="

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Warning: This project is optimized for macOS with Apple Silicon."
fi

# System deps
echo "Installing system dependencies..."
brew install portaudio ffmpeg sox 2>/dev/null || echo "Some brew packages already installed."

# Python venv — pin to 3.12 explicitly because numpy<2.0 (required by qwen-tts)
# does not yet ship wheels for newer Python versions and the install will break.
echo "Creating Python 3.12 virtual environment..."
if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Error: python3.12 not found. Install it via 'brew install python@3.12'."
    exit 1
fi
python3.12 -m venv .venv
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# NLTK data
echo "Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

# Verify MPS
echo ""
echo "Checking MPS (Metal) availability..."
python -c "import torch; available = torch.backends.mps.is_available(); print(f'MPS available: {available}')"

# Output dir
mkdir -p output

echo ""
echo "=== Setup complete! ==="
echo "Activate venv: source .venv/bin/activate"
echo "Run CLI:       python -m twinktalks.cli paper.pdf -o output/audio.wav"
echo "Run Web UI:    python -m twinktalks.web"
