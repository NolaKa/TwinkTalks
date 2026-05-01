<div align="center">

# TWINKTALKS

**PDF, EPUB, Markdown, HTML, and TXT to speech — powered by Qwen3-TTS**

Convert academic papers, textbooks, e-books, notes, and web pages into natural-sounding audiobooks.

</div>

---

## Features

- **Multi-format input** — PDF (multi-column papers via pdfplumber `layout=True` + PyMuPDF fallback), EPUB (ebooklib + BeautifulSoup), Markdown (heading-aware), plain text, HTML
- **OCR for scanned PDFs** — `--ocr` runs ocrmypdf (Tesseract) before extraction, opening up old books and image-only PDFs. `--ocr-language auto` picks every Tesseract pack you have installed.
- **M4B audiobook output** — proper audiobook container with embedded chapter atoms (via ffmpeg remux); works in iOS Books, Apple Podcasts.
- **Auto-tagged audio** — title, author, and a cover image (rendered first PDF page or EPUB cover) embedded in MP3 (ID3v2) and M4B (MP4 atoms) via mutagen.
- **Single-file audiobook from chapters** — `--merge-chapters` (CLI) or the *Merge chapters* toggle (web) concatenates every TOC chapter into one file with chapter markers.
- **Voice preview** — `--preview` (CLI) renders only the first chunk so you can audition the voice before committing to a long run.
- **Auto-detect language** — pick "Auto" in the UI / pass `--language Auto` and TwinkTalks runs langdetect on the first ~500 chars to pick the right Qwen3-TTS language.
- **Streaming progress** — web UI streams chunk-level progress over Server-Sent Events; the sidebar's Active Job card updates per chunk with chunk count, rendered duration, and ETA.
- **Library** — every audiobook you've generated is stored in `~/.twinktalks/library/` and listed in the sidebar with cover art read back from embedded tags.
- **Chapter markers** — ID3v2 CHAP/CTOC frames in MP3, MP4 chapter atoms in M4B, jump between sections in VLC / Apple Podcasts / Overcast / iOS Books.
- **WAV / MP3 / M4B export** — choose the format in the web UI segmented control or via file extension in CLI.
- **Batch processing** — `--chapters all` generates a separate audio file per TOC chapter (or one merged M4B with `--merge-chapters`).
- **Table of contents & chapters** — auto-detects TOC from PDF (PyMuPDF `get_toc()`), EPUB (spine items), Markdown headings, or HTML `<h1>`-`<h3>`.
- **Skip tables** — excludes diagnostic tables, DSM criteria, etc. from speech output via `find_tables()` bbox exclusion.
- **Voice style instruct** — natural-language hint passed to Qwen3-TTS `generate_custom_voice()` to control emotion, tone, and pace (e.g. "Speak calmly like an audiobook narrator").
- **8 built-in voice presets** — Default, Calm Narrator, Energetic, Warm & Gentle, Lecture/Academic, Audiobook, Fast Summary, Whisper.
- **Custom presets** — save your own speaker + speed + instruct combos via the *Voice style* row in the web UI (or `--preset` in CLI). Persisted to `~/.twinktalks/presets.json`; user presets show with a ★ prefix.
- **Speed control** — adjustable speaking rate (0.5x–2.0x) via native Qwen3-TTS `speed` parameter, no post-processing.
- **CLI session resume** — saves progress per chunk to `~/.twinktalks/sessions/<id>/` so an interrupted CLI run can continue from where it stopped (`--resume <id>`).
- **Academic text cleanup** — removes `[1,2]` citations, `(Author et al., 2024)`, figure/table captions, URLs, DOIs, section numbers; expands abbreviations (`e.g.` → `for example`).
- **Sentence- and page-aware chunking** — ~500-character chunks at sentence boundaries (NLTK) with cross-page paragraph stitching; each chunk records its source page for accurate chapter-marker placement.
- **Voices** — all 9 Qwen3-TTS-CustomVoice speakers (`aiden`, `dylan`, `eric`, `ono_anna`, `ryan`, `serena`, `sohee`, `uncle_fu`, `vivian`) surfaced verbatim in the web UI as 3×3 tiles. The CLI's `--speaker` flag is case-insensitive.
- **10+ languages** — English, Chinese, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian.

## Requirements

- **Apple Silicon Mac** (M1/M2/M3/M4)
  - **32 GB+ RAM** recommended for the Qwen backend
  - 8 GB RAM is fine for the Kokoro backend
- Auto-detected device: MPS (Apple Silicon) → CUDA (NVIDIA) → CPU fallback
- Python 3.12+
- Node.js 20+ (only for the web UI build)
- System deps: `portaudio`, `ffmpeg`, `sox` (installed via Homebrew)
- Optional for OCR: `tesseract`, `ghostscript`, `qpdf` (also via Homebrew) plus `pip install ocrmypdf`

## TTS backends

TwinkTalks runs on one of two TTS engines. **You pick which one when you install** — they can't share a Python virtualenv (the libraries pin conflicting versions of `numpy` / `transformers`).

|  | **Qwen3-TTS-1.7B** *(default)* | **Kokoro-82M** *(faster)* |
|---|---|---|
| **Install command** | `./setup.sh` | `./setup.sh --kokoro` |
| **Model size on disk** | ~3.5 GB | ~360 MB |
| **RAM during synthesis** | ~6–10 GB | ~1.5–2 GB |
| **Speed (M-series Mac)** | ~1 hour audio in ~30–60 min | **~1 hour audio in ~5–6 min** |
| **Languages** | 10+ with auto-detect | English only (American + British) |
| **Voice-style prompts** ("speak calmly…") | ✓ | ✗ |
| **Voices** | 9 (aiden, dylan, eric, ono_anna, ryan, serena, sohee, uncle_fu, vivian) | 9 (af_heart, af_bella, af_nicole, af_sky, am_adam, am_echo, am_michael, bf_alice, bm_george) |

### Which one should I pick?

- **Use Kokoro** if your document is in English and you want it done fast, especially on a laptop with 8 GB of RAM. A 56-minute audiobook renders in under 6 minutes on an M-series 8 GB.
- **Use Qwen** if your document is in Polish / German / French / Chinese / etc., or if you want to control the delivery with prompts like *"Speak calmly like an audiobook narrator"*. You'll need a Mac with at least 16 GB of RAM (32 GB comfortable) and patience — synthesis runs in real time give-or-take.

The web UI shows whichever backend you installed; nothing to configure once setup is done.

## Quick Start

```bash
git clone https://github.com/NolaKa/TwinkTalks.git
cd TwinkTalks
chmod +x setup.sh
```

Now pick a backend and run setup:

**Qwen (default — multilingual, slower, more RAM):**
```bash
./setup.sh
source .venv/bin/activate
twinktalks-server          # → http://localhost:7860
```

**Kokoro (English only, much faster, low RAM):**
```bash
./setup.sh --kokoro
source .venv/bin/activate
twinktalks-server          # → http://localhost:7860
```

That's it. `setup.sh` is idempotent: it installs Homebrew dependencies (Python 3.12, Node, ffmpeg, Tesseract, ghostscript, qpdf), creates a Python virtualenv, installs the backend you chose, builds the React frontend, and prints next-step instructions. The only prerequisite is [Homebrew](https://brew.sh/) — if it's missing the script tells you the install command and exits.

### Want both backends side by side?

Use separate virtualenvs. They're cheap to create — each is ~1–2 GB of Python packages plus the model weights in `~/.twinktalks/cache/`:

```bash
./setup.sh --venv .venv-qwen           # Qwen in .venv-qwen
./setup.sh --kokoro --venv .venv-kokoro  # Kokoro in .venv-kokoro
```

To switch:

```bash
deactivate                              # leave whichever venv is active
source .venv-kokoro/bin/activate        # activate the other
twinktalks-server
```

The web UI re-detects the active backend on startup, so the voice list, language list, and the visibility of the *Voice style* prompt box all adapt automatically. No config file, no env var.

### Already installed Qwen and want to try Kokoro?

You don't need to reinstall everything — just spin up a second venv:

```bash
./setup.sh --kokoro --venv .venv-kokoro
deactivate
source .venv-kokoro/bin/activate
twinktalks-server
```

Switch back with `deactivate && source .venv/bin/activate`. The original `.venv` (Qwen) is untouched.

### Manual install (no setup.sh)

If you'd rather do it yourself:

```bash
python3.12 -m venv .venv && source .venv/bin/activate

# Pick ONE:
pip install -e ".[qwen]"     # multilingual, slower
pip install -e ".[kokoro]"   # English only, faster

(cd frontend && npm install && npm run build)
twinktalks-server
```

## Usage

### Web UI

```bash
twinktalks-server
# Open http://localhost:7860
```

The interface is a React + Vite SPA served by FastAPI. It exposes:

- **Drop zone / file card** — drag-and-drop or click to upload PDF, EPUB, Markdown, TXT, HTML. Once loaded, you see file size, page/chapter count, word count, and an estimated audio duration. Title and cover art come from the document's metadata.
- **Voice picker** — a 3×3 grid of the active backend's voices (9 Qwen speakers if you ran `./setup.sh`, 9 Kokoro voices if you ran `./setup.sh --kokoro`). The header above the grid tells you which backend is current.
- **Voice style** — collapsible row right under the voice tiles. Click to expand a panel with a *built-in or saved* preset dropdown, a *Save current as…* input + button, an instruct textarea, and a list of your saved presets with ★ delete.
- **Settings list** — Language (with `Auto`), Speed slider (0.5–2.0×), Format segmented (WAV/MP3/M4B), Chapter markers toggle, OCR fallback toggle.
- **Advanced** (inside Settings list) — OCR language, *skip references*, *skip tables*, and *merge all chapters into one audiobook*.
- **Generate** — streams synthesis progress over Server-Sent Events; the sidebar's Active Job card updates per chunk with chunk count, rendered duration, and ETA. ⌘⏎ also triggers it.
- **Library** — every audiobook you've generated, stored in `~/.twinktalks/library/`. Click a row to play in-browser; covers come from embedded ID3/MP4 tags.
- **Theme** — single light/dark toggle in the topbar, persisted in `localStorage`. First-time visit follows your system preference.

### Frontend dev mode

If you want hot reload while editing the UI, run Vite alongside the backend:

```bash
twinktalks-server                # backend on :7860
cd frontend && npm run dev       # frontend on :5173 (proxies /api to :7860)
```

### CLI

Setup creates two folders for convenience: `input/` (drop your documents
here) and `output/` (where audio lands by default). You can pass any
path you want — these are just the defaults the examples assume.

```bash
# Basic: any supported format to WAV/MP3/M4B
twinktalks input/paper.pdf                       # → output/paper.wav (default)
twinktalks input/paper.pdf output/paper.mp3      # output as second positional
twinktalks input/book.epub -o output/book.m4b    # or use the -o flag
twinktalks input/notes.md output/notes.mp3
twinktalks input/article.html output/article.wav

# Choose voice and language (or "Auto" for auto-detect)
python -m twinktalks paper.pdf -o output.mp3 --speaker ryan --language Auto

# 10-second voice preview before committing to the full run
python -m twinktalks paper.pdf --preview -o output.mp3

# OCR a scanned PDF (requires brew: tesseract ghostscript qpdf + pip: ocrmypdf)
python -m twinktalks scanned.pdf --ocr -o output.mp3
python -m twinktalks polish_book.pdf --ocr --ocr-language pol -o output.mp3

# Single audiobook M4B with all chapters merged + embedded chapter markers
python -m twinktalks textbook.pdf --chapters all --merge-chapters -o book.m4b

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

# Voice style instruction
python -m twinktalks paper.pdf --instruct "Speak calmly like a narrator" -o output.wav

# Use a built-in voice preset
python -m twinktalks paper.pdf --preset "Audiobook" -o output.wav
python -m twinktalks paper.pdf --preset "Whisper" -o output.wav

# List all available presets
python -m twinktalks --list-presets

# MP3 with chapter markers (embeds ID3v2 CHAP frames — jump between chapters in VLC/podcast apps)
python -m twinktalks textbook.pdf --chapter-markers -o output.mp3

# Resume interrupted session
python -m twinktalks paper.pdf --list-sessions
python -m twinktalks paper.pdf --resume <session-id> -o output.wav
```

## How It Works

```
PDF / EPUB / MD / TXT / HTML → Extract text → Preprocess → Chunk → TTS → Audio
```

1. **Extract** — pdfplumber reads PDF with `layout=True` for multi-column support (PyMuPDF fallback). EPUB goes through ebooklib + BeautifulSoup. Markdown is unwrapped of its markup; HTML is read with BeautifulSoup. Headers/footers are cropped, References are truncated. Supports per-page extraction for chapter-marker timing. Scanned PDFs route through ocrmypdf when `--ocr` is set.
2. **Preprocess** — removes `[1,2]` citations, `(Author et al., 2024)`, figure/table captions, URLs, DOIs, section numbers, isolated page numbers; expands abbreviations (`e.g.` → `for example`). All 20+ regex patterns are pre-compiled at module load.
3. **Chunk** — splits into ~500-character chunks at sentence boundaries. Page-aware mode stitches paragraphs that cross a page break and tags each chunk with its source page so chapter markers can be placed accurately.
4. **Synthesize** — Qwen3-TTS generates audio chunk by chunk with retry logic (3 attempts, silence fallback), applying voice style via `instruct`. Streaming mode yields cumulative waveform after each chunk; the FastAPI server forwards these as SSE progress events.
5. **Export** — concatenates with natural pauses (400ms between sentences, 800ms between paragraphs), saves as WAV / MP3 / M4B. MP3 and M4B output get title/author/cover tags embedded via mutagen. With chapter markers enabled and a TOC available, the file gets ID3v2 CHAP frames (MP3) or MP4 chapter atoms (M4B, written via an ffmpeg remux).

## Chapter Markers

When generating MP3 or M4B output, TwinkTalks can embed chapter markers that let you jump between sections in your audio player.

**How it works:**
1. Text is extracted per-page (preserving page numbers).
2. Each chunk records which page it came from (`source_page`).
3. After synthesis, chunk timing offsets are computed (accounting for inter-sentence/paragraph silence).
4. TOC chapters are mapped to audio timestamps via page ranges.
5. The audio file is tagged: ID3v2 CHAP + CTOC frames for MP3 (via mutagen), or MP4 chapter atoms for M4B (via an ffmpeg remux with an ffmetadata sidecar).

**CLI:**
```bash
python -m twinktalks textbook.pdf --chapter-markers -o textbook.mp3
python -m twinktalks textbook.pdf --chapter-markers -o textbook.m4b
python -m twinktalks textbook.pdf --chapters all --merge-chapters -o book.m4b   # one merged audiobook
```

**Web UI:** the *Chapter markers* toggle in the Settings list controls embedding; it applies to MP3 and M4B output whenever the source has a detected TOC.

**Supported players:** VLC, Apple Podcasts, Overcast, Pocket Casts, iOS Books (M4B), and any player supporting ID3v2 / MP4 chapter frames.

## Voice Presets

| Preset | Speaker | Speed | Style |
|--------|---------|-------|-------|
| Default | aiden | 1.0x | (neutral) |
| Calm Narrator | aiden | 0.9x | Speak in a calm, measured, soothing tone... |
| Energetic | ryan | 1.1x | Speak with energy and enthusiasm... |
| Warm & Gentle | serena | 0.9x | Speak warmly and gently... |
| Lecture/Academic | aiden | 0.85x | Speak like a university professor giving a clear, structured lecture... |
| Audiobook | ryan | 0.95x | Speak like a professional audiobook narrator... |
| Fast Summary | ryan | 1.3x | Speak quickly and concisely... |
| Whisper | sohee | 0.8x | Speak in a soft, intimate whisper... |

**Custom presets:** save your own speaker + speed + instruct combos via the *Voice style* row in the web UI (open the row → type a name into *Save current as…* → click Save), or manage them directly in `~/.twinktalks/presets.json`. User presets appear with a ★ prefix in the dropdown and can be deleted with the × button.

## Project Structure

```
twinktalks/
├── config.py             # All constants: model ID, speakers, chunking, audio; auto device/dtype detection
├── extractor.py          # File type router — dispatches to per-format extractor by extension
├── pdf_extractor.py      # pdfplumber (layout=True) + PyMuPDF fallback, table skipping, per-page, OCR hook
├── epub_extractor.py     # ebooklib + BeautifulSoup, spine-based chapter navigation, per-item extraction
├── text_extractor.py     # Plain text and Markdown (markup stripping + heading TOC)
├── html_extractor.py     # Standalone HTML files (BeautifulSoup, h1-h3 TOC)
├── ocr.py                # ocrmypdf wrapper for scanned PDF preprocessing (auto language pick)
├── text_preprocessor.py  # Remove citations, expand abbreviations, truncate at references
├── chunker.py            # ~500 char chunks at sentence boundaries (NLTK), page-aware + cross-page stitching
├── tts_engine.py         # Qwen3-TTS wrapper — MPS/SDPA/float16, streaming + batch synthesis
├── audio_utils.py        # Concat + silence gaps, WAV/MP3/M4B export, ID3v2 + MP4 chapter markers, metadata embed
├── toc.py                # TOC extraction (PyMuPDF get_toc()), Chapter dataclass
├── session.py            # SessionManager — per-chunk WAV saving, CLI resume support
├── presets.py            # Built-in voice presets + user favorites (~/.twinktalks/presets.json)
├── book_metadata.py      # Extract title/author/cover from PDF (fitz) and EPUB (DC metadata)
├── language_detect.py    # langdetect → Qwen3-TTS language name mapping
├── cli.py                # CLI with batch + merge-chapters, preview, OCR, chapter markers, sessions
├── api.py                # FastAPI app — entry point for `twinktalks-server`
└── api_routes/
    ├── static_data.py    # Voices, languages, formats, presets endpoints
    ├── files.py          # Upload + metadata + preview endpoints
    ├── jobs.py           # Synthesis jobs with SSE progress streaming + voice preview
    └── library.py        # Previously generated audiobooks (~/.twinktalks/library/)

frontend/
├── package.json
├── vite.config.ts        # Dev server proxies /api → :7860
├── index.html            # Geist + Geist Mono via Google Fonts
└── src/
    ├── App.tsx           # Top-level state: file, settings, job, library, presets
    ├── main.tsx
    ├── api/client.ts     # Typed fetch wrappers for every backend endpoint
    ├── components/       # Topbar, Hero, Dropzone, FileCard, VoicePicker,
    │                     # VoiceStyleControls, SettingsList, GenerateButton,
    │                     # ActiveJob, Library
    ├── hooks/useTheme.ts # light/dark toggle, persisted to localStorage
    ├── styles/           # Design tokens + base.css
    └── types.ts          # TypeScript shapes shared with the API
```

## Model

Uses [Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) with:
- `device_map` auto-detected: MPS (Apple Silicon Metal) → CUDA (NVIDIA) → CPU
- `attn_implementation="sdpa"` (FlashAttention unavailable on macOS)
- `dtype=float16` on MPS/CUDA, `float32` on CPU

The model (~3.5GB) downloads automatically on first run into `~/.twinktalks/cache/` (HuggingFace + ModelScope caches are redirected there so the weights live next to the rest of TwinkTalks' state instead of polluting `~/.cache/huggingface/`). **No HuggingFace account is required** — the model is public. If you hit rate limits, TwinkTalks will automatically try [ModelScope](https://modelscope.cn/models/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) as a fallback.

### Download options

**Automatic (default):** Just run TwinkTalks. It downloads from HuggingFace, falling back to ModelScope on errors.

**Manual — no account needed (ModelScope):**
```bash
pip install modelscope
modelscope download --model Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --local_dir ./model
python -m twinktalks --model-path ./model paper.pdf
```

**Manual — fast download (HuggingFace, free account):**
```bash
pip install -U "huggingface_hub[cli]" hf_transfer
HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --local-dir ./model
python -m twinktalks --model-path ./model paper.pdf
```

**Web UI with local model:**
```bash
TWINKTALKS_MODEL_PATH=./model twinktalks-server
```

### Expected warnings on macOS

```
Warning: flash-attn is not installed. Will only run the manual PyTorch version.
```

This is normal — FlashAttention is CUDA-only. TwinkTalks uses SDPA (Scaled Dot Product Attention) instead, which works on Apple Silicon.

## Dependencies

**System** (via Homebrew):
```bash
brew install portaudio ffmpeg sox
```

**Python** (via pip):
```
qwen-tts                  # TTS model interface
torch                     # PyTorch (MPS backend)
pdfplumber                # PDF extraction with layout mode
PyMuPDF                   # PDF fallback + TOC + cover render
ebooklib                  # EPUB parsing
beautifulsoup4            # HTML text extraction
nltk                      # Sentence tokenization
soundfile                 # WAV I/O
pydub                     # MP3 / M4B export (via ffmpeg)
mutagen                   # ID3v2 / MP4 atoms for chapter markers + metadata
numpy                     # Audio array operations
langdetect                # Auto language detection
fastapi + uvicorn         # Web backend
sse-starlette             # Server-Sent Events for streaming progress
python-multipart          # Multipart upload parsing
tqdm                      # CLI progress bars
pytest                    # Test framework
```

**JavaScript** (via npm, in `frontend/`):
```
react / react-dom         # UI runtime
vite                      # Dev server + bundler
typescript                # Static typing
```

Full Python list: [`requirements.txt`](requirements.txt). Full JS list: [`frontend/package.json`](frontend/package.json).

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

224 unit tests covering: text preprocessor, chunker (page-aware + cross-page paragraph merging), PDF extractor (with mocked OCR), EPUB extractor, plain-text/Markdown/HTML extractors, extractor router, TOC, sessions, presets, CLI batch helpers and flags, TTS engine (model mocked), chapter markers (MP3 ID3 + M4B chapter atoms), chunk offset computation, chunk-to-chapter mapping, audio export (WAV/MP3/M4B), metadata embedding (title, author, cover art), and language auto-detection.
