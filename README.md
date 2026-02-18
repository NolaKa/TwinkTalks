# TwinkTalks

PDF & EPUB to Speech converter powered by [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice). Extracts text from academic papers, textbooks, and e-books, then generates natural-sounding speech.

## Features

- **PDF + EPUB support** — handles multi-column academic papers (pdfplumber + PyMuPDF) and e-books (ebooklib)
- **Streaming playback** — web UI plays audio progressively as chunks are generated, no waiting for the full file
- **Batch processing** — `--chapters all` generates a separate audio file per chapter
- **Table of contents & chapters** — auto-detects TOC from PDF or EPUB, select specific chapters by name or index
- **Skip tables** — excludes diagnostic tables, DSM criteria, etc. from speech output
- **Speed control** — adjustable speaking rate (0.5x-2.0x) via native Qwen3-TTS parameter
- **Session resume** — saves progress per chunk, resume interrupted generation from where it stopped
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
# Basic: PDF or EPUB to WAV
python -m twinktalks paper.pdf -o output.wav
python -m twinktalks book.epub -o output.wav

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

# Speed control (0.5 = slow, 2.0 = fast)
python -m twinktalks paper.pdf --speed 0.8 -o output.wav

# Skip tables and diagrams
python -m twinktalks paper.pdf --skip-tables -o output.wav

# Show table of contents
python -m twinktalks paper.pdf --show-toc

# Extract specific chapter (by name or index)
python -m twinktalks paper.pdf --chapter "Introduction" -o output.wav
python -m twinktalks paper.pdf --chapter 3 -o output.wav

# Batch: generate one audio file per chapter
python -m twinktalks textbook.pdf --chapters all
python -m twinktalks textbook.epub --chapters all -o output_dir/

# Resume interrupted session
python -m twinktalks paper.pdf --list-sessions
python -m twinktalks paper.pdf --resume <session-id> -o output.wav
```

### Web UI

```bash
python -m twinktalks.web
# Open http://localhost:7860
```

Upload a PDF or EPUB, pick a voice, hit Generate. Audio streams progressively as chunks are generated. Features: chapter selector (auto-detected TOC), speed slider, skip tables/references checkboxes, page range selection.

## Project Structure

```
twinktalks/
├── config.py             # Model, speaker, chunking, audio settings
├── extractor.py          # File type router (PDF/EPUB dispatch)
├── pdf_extractor.py      # PDF text extraction (pdfplumber + PyMuPDF)
├── epub_extractor.py     # EPUB text extraction (ebooklib + BeautifulSoup)
├── text_preprocessor.py  # Academic text cleanup for TTS
├── chunker.py            # Sentence-aware text splitting
├── tts_engine.py         # Qwen3-TTS wrapper (MPS/SDPA) + streaming
├── audio_utils.py        # Audio concatenation & export
├── toc.py                # Table of contents extraction (PyMuPDF)
├── session.py            # Resumable session management
├── cli.py                # CLI with batch chapter processing
└── web.py                # Gradio web UI with streaming playback
```

## How It Works

1. **Extract** — pdfplumber reads PDF with `layout=True` for multi-column support (or ebooklib for EPUB), crops headers/footers, truncates at References
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
