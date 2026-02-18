# TwinkTalks

PDF to Speech converter powered by [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice). Extracts text from academic papers (including multi-column layouts) and generates natural-sounding speech.

## Features

- **Smart PDF extraction** — handles multi-column academic papers with correct reading order (pdfplumber + PyMuPDF fallback)
- **Academic text cleanup** — removes citations, figure captions, URLs, expands abbreviations for natural TTS output
- **Sentence-aware chunking** — splits long documents into optimal chunks for stable generation
- **9 preset voices** — Aiden, Ryan, Aria, Claire, Emma, Leo, Mia, Noah, Sophia
- **10+ languages** — English, Chinese, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian
- **CLI + Web UI** — terminal interface with progress bar or Gradio browser app
- **WAV & MP3 export**

## Requirements

- **Apple Silicon Mac** (M1/M2/M3/M4) with **32GB+ unified memory** recommended
- Python 3.12
- System deps: `portaudio`, `ffmpeg`, `sox` (installed via brew)

## Quick Start

```bash
git clone https://github.com/NolaKa/TwinkTalks.git
cd TwinkTalks
chmod +x setup.sh && ./setup.sh
source .venv/bin/activate
```

## Usage

### CLI

```bash
# Basic: PDF to WAV
python -m twinktalks paper.pdf -o output.wav

# Choose voice and language
python -m twinktalks paper.pdf -o output.mp3 --speaker Ryan --language English

# Preview extracted text (no TTS)
python -m twinktalks paper.pdf --dry-run

# Specific page range
python -m twinktalks paper.pdf --pages 3-7 -o output.wav

# Limit to first N pages
python -m twinktalks paper.pdf --max-pages 5 -o output.wav

# Include references section
python -m twinktalks paper.pdf --no-skip-references -o output.wav
```

### Web UI

```bash
python -m twinktalks.web
# Open http://localhost:7860
```

Upload a PDF, pick a voice, hit Generate.

## Project Structure

```
twinktalks/
├── config.py             # Model, speaker, chunking, audio settings
├── pdf_extractor.py      # PDF text extraction (pdfplumber + PyMuPDF)
├── text_preprocessor.py  # Academic text cleanup for TTS
├── chunker.py            # Sentence-aware text splitting
├── tts_engine.py         # Qwen3-TTS wrapper (MPS/SDPA)
├── audio_utils.py        # Audio concatenation & export
├── cli.py                # Command-line interface
└── web.py                # Gradio web interface
```

## How It Works

1. **Extract** — pdfplumber reads PDF with `layout=True` for multi-column support, crops headers/footers, truncates at References
2. **Preprocess** — removes `[1,2]` citations, `(Author et al., 2024)`, figure/table captions, URLs, DOIs, section numbers; expands abbreviations (`e.g.` → `for example`)
3. **Chunk** — splits into ~500 character chunks at sentence boundaries, preserving paragraph structure
4. **Synthesize** — Qwen3-TTS generates audio chunk by chunk with retry logic
5. **Export** — concatenates with natural pauses between sentences/paragraphs, saves as WAV or MP3

## Model

Uses [Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) with:
- `device_map="mps"` (Apple Silicon Metal)
- `attn_implementation="sdpa"` (FlashAttention unavailable on macOS)
- `dtype=float16`

The model (~3.5GB) downloads automatically on first run.

### Slow download?

The default download can be slow. For faster speeds, pre-download the model manually:

```bash
pip install -U "huggingface_hub[cli]" hf_transfer
HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
```

`hf_transfer` uses multi-threaded downloads and is significantly faster than the default.

### Expected warnings on macOS

```
Warning: flash-attn is not installed. Will only run the manual PyTorch version.
```

This is normal — FlashAttention is CUDA-only. TwinkTalks uses SDPA (Scaled Dot Product Attention) instead, which works on Apple Silicon.

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```
