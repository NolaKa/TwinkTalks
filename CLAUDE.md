# TwinkTalks

PDF & EPUB to speech app using Qwen3-TTS. Converts academic papers, textbooks, and e-books to natural audio.

## Architecture

Pipeline: `file → extract text → preprocess → chunk → TTS → audio`

```
twinktalks/
├── config.py             # All constants (model, speaker, chunking, audio, speed, sessions)
├── extractor.py          # File type router — dispatches to pdf/epub extractor by extension
├── pdf_extractor.py      # pdfplumber (layout=True) + PyMuPDF fallback, table skipping
├── epub_extractor.py     # ebooklib + BeautifulSoup, spine-based chapter navigation
├── text_preprocessor.py  # Remove citations, expand abbreviations, truncate at references
├── chunker.py            # Split into ~500 char chunks at sentence boundaries (nltk)
├── tts_engine.py         # Qwen3-TTS wrapper — MPS/SDPA/float16, streaming + batch synthesis
├── audio_utils.py        # Concatenate waveforms, silence gaps, WAV/MP3 export
├── toc.py                # TOC extraction (PyMuPDF get_toc()), Chapter dataclass
├── session.py            # SessionManager — per-chunk WAV saving, resume support
├── cli.py                # CLI with batch chapter processing (_process_single pipeline)
└── web.py                # Gradio web UI with streaming playback
```

## Key Technical Decisions

- **Model**: `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` (preset voices, no cloning needed). Base model requires reference audio.
- **Apple Silicon**: `device_map="mps"`, `attn_implementation="sdpa"`, `dtype=float16`. FlashAttention does NOT work on macOS.
- **PDF extraction**: pdfplumber with `layout=True` handles multi-column papers. Falls back to PyMuPDF. Table skipping via `find_tables()` bbox exclusion.
- **EPUB extraction**: ebooklib parses EPUB container, BeautifulSoup extracts text from HTML spine items. Chapters map to spine indices (reuses `Chapter` dataclass from `toc.py`).
- **Extractor router** (`extractor.py`): Dispatches `extract_text()`, `get_item_count()`, `extract_toc()` by file extension. Maps PDF-specific kwargs (`page_range`, `skip_tables`) and strips them for EPUB.
- **Chunking**: Sentences grouped into ~500 char chunks. `max_new_tokens=1024`. Never breaks mid-sentence.
- **Speed**: Native Qwen3-TTS `speed` parameter (0.5-2.0). No post-processing needed.
- **Streaming**: `synthesize_chunks_streaming()` is a generator that yields cumulative waveform after each chunk. Web UI writes a new temp WAV per yield (avoids Gradio file cache issues).
- **Batch**: `--chapters all` loops over `extract_toc()`, calls `_process_single()` per chapter. Each chapter gets its own session.
- **Sessions**: `~/.twinktalks/sessions/<id>/` stores `session.json` + `chunk_NNNN.wav` files. `synthesize_chunks()` accepts `session_dir` and `start_from` for resume.
- **Gradio 6.0**: `css` param goes in `launch()`, not `Blocks()`.

## Running

```bash
# CLI — PDF or EPUB
python -m twinktalks paper.pdf -o output.wav
python -m twinktalks book.epub -o output.wav
python -m twinktalks paper.pdf --dry-run        # text only, no TTS

# Batch — one audio file per chapter
python -m twinktalks textbook.pdf --chapters all

# Web UI
python -m twinktalks.web                         # http://localhost:7860
```

## Tests

```bash
python -m pytest tests/ -v
```

92 unit tests covering preprocessor, chunker, pdf_extractor, epub_extractor, extractor router, toc, session, cli batch helpers. TTS engine tests require the model (manual).

## Dependencies

System: `brew install portaudio ffmpeg sox`
Python: `pip install -r requirements.txt` (qwen-tts, torch, pdfplumber, PyMuPDF, ebooklib, beautifulsoup4, nltk, soundfile, pydub, gradio, tqdm)
Target: Python 3.12 in venv. Setup script: `./setup.sh`
