# TwinkTalks

PDF & EPUB to speech app using Qwen3-TTS. Converts academic papers, textbooks, and e-books to natural audio.

## Architecture

Pipeline: `file → extract text → preprocess → chunk → TTS → audio`

```
twinktalks/
├── config.py             # All constants (model, speaker, chunking, audio, speed, sessions)
├── extractor.py          # File type router — dispatches to pdf/epub extractor by extension
├── pdf_extractor.py      # pdfplumber (layout=True) + PyMuPDF fallback, table skipping, per-page extraction
├── epub_extractor.py     # ebooklib + BeautifulSoup, spine-based chapter navigation, per-item extraction
├── text_preprocessor.py  # Remove citations, expand abbreviations, truncate at references
├── chunker.py            # Split into ~500 char chunks at sentence boundaries (nltk), page-aware chunking
├── tts_engine.py         # Qwen3-TTS wrapper — MPS/SDPA/float16, streaming + batch synthesis
├── audio_utils.py        # Concatenate waveforms, silence gaps, WAV/MP3 export, ID3v2 chapter markers
├── toc.py                # TOC extraction (PyMuPDF get_toc()), Chapter dataclass
├── session.py            # SessionManager — per-chunk WAV saving, resume support
├── presets.py            # Built-in voice presets + user favorites (~/.twinktalks/presets.json)
├── cli.py                # CLI with batch chapter processing, chapter marker embedding
└── web.py                # Gradio web UI with streaming playback, file queue, format selection
```

## Key Technical Decisions

- **Model**: `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` (preset voices, no cloning needed). Base model requires reference audio. `MODELSCOPE_ID` mirrors HF model ID for fallback downloads.
- **Apple Silicon**: `device_map="mps"`, `attn_implementation="sdpa"`, `dtype=float16`. FlashAttention does NOT work on macOS.
- **PDF extraction**: pdfplumber with `layout=True` handles multi-column papers. Falls back to PyMuPDF. Table skipping via `find_tables()` bbox exclusion. `extract_text_by_page()` returns `list[tuple[int, str]]` for page-aware processing.
- **EPUB extraction**: ebooklib parses EPUB container, BeautifulSoup extracts text from HTML spine items. Chapters map to spine indices (reuses `Chapter` dataclass from `toc.py`). `extract_text_by_item()` returns per-spine-item text.
- **Extractor router** (`extractor.py`): Dispatches `extract_text()`, `extract_text_by_page()`, `get_item_count()`, `extract_toc()` by file extension. Maps PDF-specific kwargs (`page_range`, `skip_tables`) and strips them for EPUB.
- **Chunking**: Sentences grouped into ~500 char chunks. `max_new_tokens=1024`. Never breaks mid-sentence. `Chunk.source_page` tracks origin page. `chunk_paged_text()` preserves page mapping.
- **Voice modulation**: `instruct` parameter passed to `generate_custom_voice()`. Accepts natural language (e.g. "Speak calmly"). Empty string = default voice behavior.
- **Presets** (`presets.py`): 8 built-in presets (Calm Narrator, Audiobook, Whisper, etc.) + user favorites saved to `~/.twinktalks/presets.json`. `resolve_preset()` returns `{speaker, speed, instruct}`. User presets prefixed with `* ` in dropdown.
- **Speed**: Native Qwen3-TTS `speed` parameter (0.5-2.0). No post-processing needed.
- **Streaming**: `synthesize_chunks_streaming()` yields 5-tuple `(cumulative_waveform, sample_rate, current, total, chunk_offsets_ms)`. `chunk_offsets_ms` is `None` for intermediate yields, `list[int]` for final. Web UI writes a new temp WAV per yield (avoids Gradio file cache issues).
- **File queue**: `gr.File(file_count="multiple")`. `on_files_upload()` detects 1 vs N files. `process_queue()` loops over files, streaming per file. `gr.Files` component shows completed files for download.
- **Chapter markers**: `AudioChapter(title, start_ms, end_ms)` dataclass. `add_chapter_markers()` writes ID3v2 CHAP + CTOC frames via mutagen. `compute_chunk_offsets()` calculates per-chunk timing including silence gaps. `_map_chunks_to_chapters()` maps `chunk.source_page` to TOC page ranges.
- **Batch**: `--chapters all` loops over `extract_toc()`, calls `_process_single()` per chapter. Each chapter gets its own session.
- **Sessions**: `~/.twinktalks/sessions/<id>/` stores `session.json` + `chunk_NNNN.wav` files. `synthesize_chunks()` returns 3-tuple `(waveform, sample_rate, chunk_offsets_ms)` and accepts `session_dir` and `start_from` for resume.
- **Model loading**: `TTSEngine(model_path=...)` accepts local dir. `load_model()` tries: 1) local path, 2) HuggingFace, 3) ModelScope fallback on 429/401/403. CLI: `--model-path`. Web UI: `TWINKTALKS_MODEL_PATH` env var.
- **Gradio 6.0**: `css` param goes in `launch()`, not `Blocks()`.

## Running

```bash
# CLI — PDF or EPUB
python -m twinktalks paper.pdf -o output.wav
python -m twinktalks book.epub -o output.wav
python -m twinktalks paper.pdf --dry-run        # text only, no TTS

# Voice presets and instruct
python -m twinktalks paper.pdf --preset "Audiobook" -o output.wav
python -m twinktalks paper.pdf --instruct "Speak calmly" -o output.wav
python -m twinktalks --list-presets

# Batch — one audio file per chapter
python -m twinktalks textbook.pdf --chapters all

# MP3 with chapter markers
python -m twinktalks textbook.pdf --chapter-markers -o output.mp3

# Local model (no HuggingFace account needed)
python -m twinktalks --model-path ./model paper.pdf
TWINKTALKS_MODEL_PATH=./model python -m twinktalks.web

# Web UI
python -m twinktalks.web                         # http://localhost:7860
```

## Tests

```bash
python -m pytest tests/ -v
```

148 unit tests covering preprocessor, chunker (including page-aware), pdf_extractor, epub_extractor, extractor router, toc, session, presets, cli batch helpers, chapter markers (ID3 embedding), chunk offsets, chunk-to-chapter mapping. TTS engine tests require the model (manual).

## Dependencies

System: `brew install portaudio ffmpeg sox`
Python: `pip install -r requirements.txt` (qwen-tts, torch, pdfplumber, PyMuPDF, ebooklib, beautifulsoup4, nltk, soundfile, pydub, mutagen, gradio, tqdm)
Target: Python 3.12+ in venv. Setup script: `./setup.sh`
