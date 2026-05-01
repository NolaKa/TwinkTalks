<div align="center">

# TWINKTALKS

**Drop in a PDF, EPUB, or notes — get out an audiobook with chapter markers. Local. Open. No upload.**

Two TTS engines side by side: **Kokoro-82M** for fast multilingual narration, **Qwen3-TTS-1.7B** for richer delivery and voice-style prompts.

</div>

---

## Why Kokoro?

If you've never used TwinkTalks before, **start with Kokoro**:

- **~10× faster** than Qwen on the same hardware. A 56-minute audiobook renders in **~5–6 minutes on an 8 GB Apple Silicon laptop**.
- **~360 MB on disk** vs Qwen's 3.5 GB.
- **~1.5 GB RAM** at inference vs Qwen's 6–10 GB. Runs comfortably on a base M1/M2 with 8 GB.
- **54 voices across 9 languages**: American English, British English, Spanish, French, Hindi, Italian, Japanese, Brazilian Portuguese, Mandarin.

Kokoro doesn't accept natural-language style prompts ("speak calmly like a narrator…") — Qwen does. That's the only meaningful tradeoff.

```bash
git clone https://github.com/NolaKa/TwinkTalks.git
cd TwinkTalks
chmod +x setup.sh
./setup.sh --kokoro          # Kokoro install (recommended)
source .venv/bin/activate
twinktalks-server            # → http://localhost:7860
```

That's it. Drag a PDF in, pick a voice, click **Generate audio**. The file lands in `~/Audiobooks/`.

---

## Features

### Inputs
- **PDF** with multi-column support (pdfplumber `layout=True` + PyMuPDF fallback)
- **EPUB** with spine-based chapter navigation
- **DOCX** (Word) — Heading 1/2/3 paragraphs become a TOC
- **Markdown** (`.md`) — heading-aware
- **HTML** (`.html` / `.htm`) — `<h1>`–`<h3>` become a TOC
- **Plain text** (`.txt`)
- **RTF** (Rich Text Format)
- **FB2** (FictionBook XML, sections become chapters)
- **OCR for scanned PDFs** — `--ocr` runs `ocrmypdf` (Tesseract) before extraction. `--ocr-language auto` picks every Tesseract pack you have installed. The web UI auto-detects scanned PDFs and offers a one-click toggle.

### TTS engines
- **Kokoro-82M** (recommended) — 54 voices, 9 languages, fast and light.
- **Qwen3-TTS-1.7B** — 9 voices, 10+ languages with auto-detect, supports natural-language voice-style prompts.

### Outputs
- **WAV / MP3 / M4B** — choose via web UI segmented control or CLI file extension.
- **M4B** is a proper audiobook container with embedded chapter atoms — works in iOS Books, Apple Podcasts.
- **Auto-tagged** — title, author, and cover image (rendered first PDF page or EPUB cover) embedded in MP3 (ID3v2) and M4B (MP4 atoms) via mutagen.
- **Chapter markers** — ID3v2 CHAP/CTOC frames in MP3, MP4 chapter atoms in M4B. Jump between sections in VLC, Apple Podcasts, Overcast, iOS Books.
- **Single-file audiobook from chapters** — `--merge-chapters` (CLI) or *Combine chapters* checkbox (web) concatenates every TOC chapter into one file with chapter atoms.

### UI niceties
- **Voice filters** (Kokoro) — chip rows for *Language* and *Gender* shrink 54 tiles to whatever you actually want to scan.
- **Voice preview** — `--preview` (CLI) or *▶ Preview* button (web) renders only the first chunk so you can audition voice + speed before committing to a long run.
- **Smart defaults** — uploading a PDF with a TOC defaults format to M4B + Combine chapters on; short docs default to MP3.
- **Streaming progress** — chunk-level updates over Server-Sent Events; the sidebar's Active Job card shows chunk count, rendered duration, ETA.
- **Library** — every audiobook in `~/Audiobooks/`, also listed in the sidebar with cover art read back from embedded tags. Each entry has download / play / delete buttons.
- **Light / dark toggle** in the hero, persisted in `localStorage`.
- **CLI session resume** — `--resume <id>` continues an interrupted run from the last completed chunk.

### Text cleanup
- **Academic text cleanup** — strips `[1,2]` citations, `(Author et al., 2024)`, figure/table captions, URLs, DOIs, section numbers, isolated page numbers; expands `e.g.` → "for example", etc.
- **Skip references / Skip tables** toggles.
- **Language auto-detect** (Qwen only) — `langdetect` runs on the first ~500 chars when you set Language to *Auto*.

---

## TTS backends side by side

|  | **Kokoro-82M** *(recommended)* | **Qwen3-TTS-1.7B** |
|---|---|---|
| **Install command** | `./setup.sh --kokoro` | `./setup.sh` |
| **Model size on disk** | ~360 MB | ~3.5 GB |
| **RAM during synthesis** | ~1.5 GB | ~6–10 GB |
| **Speed (M-series Mac)** | **~1 hour audio in 5–6 min** | ~1 hour audio in 30–60 min |
| **Languages** | American + British English, Spanish, French, Hindi, Italian, Japanese, Portuguese, Mandarin (9 total) | 10+ with auto-detect |
| **Voice-style prompts** ("speak calmly…") | ✗ | ✓ |
| **Voices** | 54 | 9 |
| **Voice filters in UI** | language + gender chips | not needed (only 9) |

The two backends pin **conflicting versions of `numpy` / `transformers`**, so they can't share a Python virtualenv. The web UI auto-detects whichever you installed.

### Want both side by side?

Use separate virtualenvs — they're cheap to create:

```bash
./setup.sh --kokoro --venv .venv-kokoro
./setup.sh --venv .venv-qwen
```

Switch between them:

```bash
deactivate
source .venv-kokoro/bin/activate
twinktalks-server                # uses Kokoro
```

The web UI re-detects the active backend on startup, so the voice list, language picker, and *Voice style* row all adapt automatically. No config file needed.

### Manual install (no setup.sh)

```bash
python3.12 -m venv .venv && source .venv/bin/activate

# Pick ONE:
pip install -e ".[kokoro]"   # English + 8 other languages, fast, low RAM
pip install -e ".[qwen]"     # Qwen with instruct prompts

(cd frontend && npm install && npm run build)
twinktalks-server
```

---

## Requirements

- **Apple Silicon Mac** (M1/M2/M3/M4) recommended — both backends use Metal/MPS.
  - 8 GB RAM is fine for **Kokoro**.
  - 16 GB+ RAM recommended for **Qwen** (32 GB comfortable).
- Auto-detected device: MPS (Apple Silicon) → CUDA (NVIDIA) → CPU fallback.
- **Python 3.12** — pinned for numpy wheel compatibility on both backends.
- **Node.js 20+** (only needed for the web UI build).
- **Homebrew** is the only prerequisite — `setup.sh` installs everything else through it (Python, Node, ffmpeg, Tesseract, ghostscript, qpdf).

---

## Usage

### Web UI

```bash
twinktalks-server
# Open http://localhost:7860
```

The interface (React + Vite served by FastAPI):

- **Drop zone / FileCard** — drag-drop or click. Accepts PDF, EPUB, DOCX, RTF, FB2, MD, TXT, HTML. Once loaded, you see file size, page/chapter count, word count, and an estimated audio duration that updates live as you drag the Speed slider. Title and cover art come from the document's metadata.
- **Voice picker** — grid of the active backend's voices. With **Kokoro**, two chip rows above the grid filter by **Language** (American English, British English, Spanish, French, Hindi, Italian, Japanese, Portuguese, Mandarin) and **Gender** (Female / Male). With **Qwen**, the 9 voices are shown directly.
- **Voice style** *(Qwen only)* — collapsible row right under the voice tiles. Click to expand a panel with a *built-in or saved* preset dropdown, a *Save current as…* input, an instruct textarea, and a list of your saved presets with × delete.
- **Settings list** — Language picker (Qwen only), Speed slider 0.5–2.0×, Format segmented (WAV/MP3/M4B), Chapter markers toggle.
- **Advanced** (inside Settings list) — OCR language, *Skip references*, *Skip tables*, *Combine chapters into one audiobook file*, *Force OCR*.
- **▶ Preview** — synthesizes only the first chunk so you can audition voice + speed before committing. Files don't pollute the library.
- **Generate audio** — full synthesis. Sticky-bottom button so it stays in reach. ⌘⏎ also triggers it.
- **Active Job** *(sidebar)* — shows the loading-model phase distinctly from synthesis, then per-chunk progress with ETA.
- **Library** *(sidebar)* — everything you've generated. Each row: cover thumbnail (from embedded tags), title + duration, ↓ download, ▶ play, 🗑 delete. Files live in `~/Audiobooks/`.
- **Light / dark toggle** lives in the hero, next to the headline.

### Frontend dev mode

```bash
twinktalks-server                # backend on :7860
cd frontend && npm run dev       # frontend on :5173 (proxies /api to :7860)
```

### CLI

`setup.sh` creates two folders for convenience: `input/` (drop your documents here) and `output/` (where audio lands by default). Examples assume that layout.

```bash
# Basic — any supported format → WAV / MP3 / M4B
twinktalks input/paper.pdf                       # → output/paper.wav
twinktalks input/paper.pdf output/paper.mp3      # output as second positional
twinktalks input/book.epub -o output/book.m4b    # or use the -o flag
twinktalks input/notes.md output/notes.mp3
twinktalks input/article.html output/article.wav
twinktalks input/draft.docx output/draft.mp3

# Voice / language / speed
twinktalks input/paper.pdf --speaker af_heart --speed 0.95
twinktalks input/paper.pdf --speaker ryan --language Auto       # Qwen auto-detect
twinktalks input/paper.pdf --backend kokoro --speaker bm_george # force backend

# 30-second voice preview
twinktalks input/paper.pdf --preview

# Scanned PDF → OCR before extraction
twinktalks input/scanned.pdf --ocr -o output/scanned.mp3
twinktalks input/polish_book.pdf --ocr --ocr-language pol -o output/book.mp3

# Single audiobook with all chapters merged + embedded chapter markers
twinktalks input/textbook.pdf --chapters all --merge-chapters -o output/book.m4b

# Just see what text would be extracted (no TTS)
twinktalks input/paper.pdf --dry-run

# Page range
twinktalks input/paper.pdf --pages 3-7 -o output/intro.wav

# Specific chapter (by name or index)
twinktalks input/paper.pdf --chapter "Introduction" -o output/intro.wav
twinktalks input/paper.pdf --chapter 3 -o output/ch3.wav

# Voice-style instruct (Qwen only)
twinktalks input/paper.pdf --instruct "Speak calmly like a narrator" -o output/calm.wav

# Built-in voice presets (Qwen only)
twinktalks --list-presets
twinktalks input/paper.pdf --preset "Audiobook" -o output/audiobook.wav

# Resume an interrupted run
twinktalks --list-sessions
twinktalks input/paper.pdf --resume <session-id>
```

---

## How it works

```
PDF / EPUB / DOCX / MD / TXT / HTML → Extract → Preprocess → Chunk → TTS → Audio
```

1. **Extract** — pdfplumber reads PDF with `layout=True` for multi-column support (PyMuPDF fallback). EPUB through ebooklib + BeautifulSoup. Markdown/HTML stripped of markup. DOCX through python-docx, FB2 through stdlib XML, RTF through striprtf. Headers/footers cropped, References truncated. Per-page extraction supports chapter-marker timing. Scanned PDFs route through ocrmypdf when `--ocr` is set.
2. **Preprocess** — strips `[1,2]` citations, `(Author et al., 2024)`, figure/table captions, URLs, DOIs, section numbers, isolated page numbers; expands abbreviations (`e.g.` → "for example"). All 20+ regex patterns pre-compiled at module load.
3. **Chunk** — ~500-character chunks at sentence boundaries (NLTK). Page-aware mode stitches paragraphs that cross a page break and tags each chunk with its source page so chapter markers can be placed accurately.
4. **Synthesize** — chunks go through the active backend (Kokoro or Qwen). Retry logic: 3 attempts per chunk, then 1s silence as fallback. Streaming mode yields cumulative waveform after each chunk; the FastAPI server forwards these as SSE events.
5. **Export** — concatenated with natural pauses (400 ms between sentences, 800 ms between paragraphs), saved as WAV / MP3 / M4B. MP3 + M4B get title/author/cover tags. With chapter markers and a TOC, the file gets ID3v2 CHAP frames (MP3) or MP4 chapter atoms (M4B, written via an ffmpeg remux).

---

## Where files live

| Path | What |
|---|---|
| `~/Audiobooks/` | **Visible in Finder.** Final audiobooks. Mirrors what's in the Library sidebar. |
| `~/.twinktalks/cache/huggingface/hub/` | Model weights (Qwen ~3.5 GB / Kokoro ~360 MB). Auto-downloaded on first run. |
| `~/.twinktalks/cache/modelscope/` | ModelScope mirror (used as Qwen fallback when HuggingFace rate-limits). |
| `~/.twinktalks/uploads/` | Source files copied in during web upload. |
| `~/.twinktalks/previews/` | First-chunk previews from the *▶ Preview* button. Not surfaced in Library. |
| `~/.twinktalks/sessions/` | CLI resume state (per-chunk WAVs + JSON). |
| `~/.twinktalks/presets.json` | Saved voice presets (Qwen only). |

To uninstall everything model + state related: `rm -rf ~/.twinktalks ~/Audiobooks`.

---

## Chapter markers

When generating MP3 or M4B output, TwinkTalks embeds chapter markers from the document's TOC.

**How it works:**
1. Text is extracted per-page (preserving page numbers).
2. Each chunk records its source page.
3. After synthesis, chunk timing offsets are computed (accounting for inter-sentence/paragraph silence).
4. TOC chapters map to audio timestamps via page ranges.
5. The audio file is tagged: ID3v2 CHAP + CTOC frames for MP3 (via mutagen), or MP4 chapter atoms for M4B (via an ffmpeg remux with an ffmetadata sidecar).

**CLI:**
```bash
twinktalks input/textbook.pdf --chapter-markers -o output/book.mp3
twinktalks input/textbook.pdf --chapter-markers -o output/book.m4b
twinktalks input/textbook.pdf --chapters all --merge-chapters -o output/book.m4b
```

**Web UI:** the *Chapter markers* toggle controls embedding; applies to MP3 and M4B output whenever the source has a detected TOC.

**Supported players:** VLC, Apple Podcasts, Overcast, Pocket Casts, iOS Books (M4B), and any player supporting ID3v2 / MP4 chapter frames.

---

## Voice presets *(Qwen only)*

| Preset | Speaker | Speed | Style |
|--------|---------|-------|-------|
| Default | aiden | 1.00× | (neutral) |
| Calm Narrator | aiden | 0.90× | Calm, professional narrator. |
| Energetic | ryan | 1.10× | With energy and enthusiasm. |
| Warm & Gentle | serena | 0.90× | Warm and gentle, like a bedtime story. |
| Lecture / Academic | aiden | 0.85× | Clear, structured lecture, methodical and articulate. |
| Audiobook | ryan | 0.95× | Professional audiobook narrator, expressive but natural. |
| Fast Summary | ryan | 1.30× | Quick and efficient, like a brief summary. |
| Whisper | sohee | 0.80× | Soft, intimate whisper. |

**Custom presets:** save your own speaker + speed + instruct combos via the *Voice style* row in the web UI (open the row → type a name into *Save current as…* → click Save), or manage them directly in `~/.twinktalks/presets.json`. User presets show with a ★ prefix in the dropdown and can be deleted with the × button. *Kokoro doesn't accept instruct prompts and uses a different speaker namespace, so the Voice style row is hidden when Kokoro is the active backend.*

---

## Project structure

```
twinktalks/
├── config.py             # Constants + auto device/dtype detection
├── extractor.py          # File type router — dispatches to per-format extractor
├── pdf_extractor.py      # pdfplumber + PyMuPDF, table skipping, OCR hook
├── epub_extractor.py     # ebooklib + BeautifulSoup, spine-based TOC
├── text_extractor.py     # Plain text + Markdown (markup strip + heading TOC)
├── html_extractor.py     # HTML files (BeautifulSoup, h1-h3 TOC)
├── docx_extractor.py     # Word .docx via python-docx (Heading style → TOC)
├── rtf_extractor.py      # Rich Text Format via striprtf
├── fb2_extractor.py      # FictionBook XML (stdlib parser, section TOC)
├── ocr.py                # ocrmypdf wrapper, auto language pick
├── text_preprocessor.py  # Citations, abbreviations, references truncation
├── chunker.py            # ~500-char chunks at sentence boundaries
├── audio_utils.py        # WAV/MP3/M4B export, chapter markers, metadata embed
├── toc.py                # PyMuPDF get_toc(), Chapter dataclass
├── session.py            # CLI per-chunk WAV saving, resume support
├── presets.py            # Built-in voice presets + user favorites
├── book_metadata.py      # Title/author/cover from PDF (fitz) and EPUB (DC)
├── language_detect.py    # langdetect → Qwen language name mapping
├── tts_engine.py         # Orchestrator: chunking + retry + streaming, delegates to backend
├── backends/
│   ├── base.py           # TTSBackend ABC
│   ├── qwen.py           # Qwen3-TTS-1.7B-CustomVoice
│   └── kokoro.py         # Kokoro-82M via mlx-audio
├── cli.py                # CLI with batch + merge-chapters + preview + OCR + sessions
├── api.py                # FastAPI app — entry point for `twinktalks-server`
└── api_routes/
    ├── static_data.py    # /api/backends, /voices (per active backend), /languages, /presets
    ├── files.py          # /api/files upload, metadata, preview, cover
    ├── jobs.py           # /api/jobs synthesis with SSE streaming + voice preview
    └── library.py        # /api/library — list + audio + cover + delete

frontend/
├── package.json
├── vite.config.ts        # Dev server proxies /api → :7860
├── index.html            # Geist + Geist Mono via Google Fonts
└── src/
    ├── App.tsx           # Top-level state: file, settings, job, library, presets, backend
    ├── api/client.ts     # Typed fetch wrappers
    ├── components/       # Hero, Dropzone, FileCard, VoicePicker (with filters),
    │                     # VoiceStyleControls, SettingsList, GenerateButton,
    │                     # ActiveJob, Library, Tooltip
    ├── hooks/useTheme.ts # light/dark toggle
    ├── styles/           # Design tokens + base.css
    └── types.ts          # Types shared with the API
```

---

## Dependencies

**System** (via Homebrew, all installed by `setup.sh`):
```
python@3.12     # Pinned for numpy wheel compatibility
node            # For Vite frontend build
ffmpeg          # MP3 / M4B encoding
portaudio sox   # Audio I/O
tesseract       # OCR (optional, for scanned PDFs)
ghostscript     # ocrmypdf prerequisite
qpdf            # ocrmypdf prerequisite
```

**Python core** (always installed):
```
torch                     # PyTorch (MPS / CUDA / CPU)
soundfile pydub mutagen   # Audio I/O + metadata
pdfplumber PyMuPDF        # PDF
ebooklib beautifulsoup4   # EPUB / HTML
python-docx striprtf      # DOCX / RTF
nltk                      # Sentence tokenization
langdetect                # Language auto-detect
fastapi uvicorn           # Web backend
sse-starlette             # Server-Sent Events
ocrmypdf                  # OCR
```

**Python TTS extras** (pick one):
```
[kokoro]   mlx-audio + misaki[en]   # ~10× faster, multilingual via voice prefix
[qwen]     qwen-tts + numpy<2       # Multilingual + instruct prompts
```

**JavaScript** (`frontend/package.json`):
```
react / react-dom         # UI runtime
vite + typescript         # Dev server + bundler
```

---

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

233 unit tests covering: text preprocessor, chunker (page-aware + cross-page paragraph merging), every extractor (PDF, EPUB, DOCX, RTF, FB2, plain-text/Markdown, HTML), extractor router, TOC, sessions, presets, CLI flag parsing + batch helpers, TTS engine + Qwen backend (model mocked), chapter markers (MP3 ID3 + M4B chapter atoms), chunk offset computation, chunk-to-chapter mapping, audio export (WAV/MP3/M4B), metadata embedding (title, author, cover art), language auto-detection, OCR plumbing.
