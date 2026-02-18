# TwinkTalks

PDF-to-speech app using Qwen3-TTS. Converts academic papers (including multi-column) to natural audio.

## Architecture

Pipeline: `PDF → extract text → preprocess → chunk → TTS → audio file`

```
twinktalks/
├── config.py             # All constants (model, speaker, chunking, audio)
├── pdf_extractor.py      # pdfplumber (layout=True) + PyMuPDF fallback
├── text_preprocessor.py  # Remove citations, expand abbreviations, clean for TTS
├── chunker.py            # Split into ~500 char chunks at sentence boundaries (nltk)
├── tts_engine.py         # Qwen3-TTS wrapper — MPS device, SDPA attention, float16
├── audio_utils.py        # Concatenate waveforms, silence gaps, WAV/MP3 export
├── cli.py                # CLI entry point (argparse + tqdm)
└── web.py                # Gradio web UI
```

## Key Technical Decisions

- **Model**: `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` (preset voices, no cloning needed). Base model requires reference audio.
- **Apple Silicon**: `device_map="mps"`, `attn_implementation="sdpa"`, `dtype=float16`. FlashAttention does NOT work on macOS.
- **PDF extraction**: pdfplumber with `layout=True` handles multi-column papers. Falls back to PyMuPDF.
- **Chunking**: Sentences grouped into ~500 char chunks. `max_new_tokens=1024`. Never breaks mid-sentence.
- **Gradio 6.0**: `theme` param goes in `launch()`, not `Blocks()`.

## Running

```bash
# CLI
python -m twinktalks paper.pdf -o output.wav
python -m twinktalks paper.pdf --dry-run        # text only, no TTS

# Web UI
python -m twinktalks.web                         # http://localhost:7860
```

## Tests

```bash
python -m pytest tests/ -v
```

56 unit tests covering preprocessor, chunker, pdf_extractor, audio_utils. TTS engine tests require the model (manual).

## Dependencies

System: `brew install portaudio ffmpeg sox`
Python: `pip install -r requirements.txt` (qwen-tts, torch, pdfplumber, PyMuPDF, nltk, soundfile, pydub, gradio, tqdm)
Target: Python 3.12 in venv. Setup script: `./setup.sh`
