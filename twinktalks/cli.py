"""CLI entry point for TwinkTalks: PDF to Speech."""

import argparse
import logging
import sys
import time
from pathlib import Path

from twinktalks.config import (
    DEFAULT_SPEAKER,
    DEFAULT_LANGUAGE,
    AVAILABLE_SPEAKERS,
    DEFAULT_OUTPUT_FORMAT,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="twinktalks",
        description="TwinkTalks - Convert PDF documents to speech using Qwen3-TTS",
    )
    parser.add_argument("input_pdf", help="Path to the input PDF file")
    parser.add_argument(
        "-o", "--output",
        help="Output audio file path (default: output/<input_name>.wav)",
    )
    parser.add_argument(
        "--speaker",
        default=DEFAULT_SPEAKER,
        choices=AVAILABLE_SPEAKERS,
        help=f"TTS speaker voice (default: {DEFAULT_SPEAKER})",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Language hint (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "--no-skip-references",
        action="store_true",
        help="Don't truncate at References/Bibliography section",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to extract",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and preprocess text only, print to stdout (no TTS)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed progress information",
    )
    return parser


def main(argv: list[str] | None = None):
    parser = create_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    log = logging.getLogger("twinktalks")

    # Determine output path
    input_path = Path(args.input_pdf)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output") / f"{input_path.stem}.{DEFAULT_OUTPUT_FORMAT}"

    # Step 1: Extract text
    log.info("Extracting text from %s...", input_path.name)
    from twinktalks.pdf_extractor import extract_text

    text = extract_text(
        str(input_path),
        skip_references=not args.no_skip_references,
        max_pages=args.max_pages,
    )
    log.info("Extracted %d characters.", len(text))

    # Step 2: Preprocess
    log.info("Preprocessing text for TTS...")
    from twinktalks.text_preprocessor import preprocess

    text = preprocess(text)
    log.info("Preprocessed: %d characters.", len(text))

    # Step 3: Chunk
    from twinktalks.chunker import chunk_text

    chunks = chunk_text(text)
    word_count = len(text.split())
    log.info("Split into %d chunks (%d words).", len(chunks), word_count)

    # Dry run: print text and exit
    if args.dry_run:
        print("\n--- Extracted & Preprocessed Text ---\n")
        print(text)
        print(f"\n--- {len(chunks)} chunks, {word_count} words ---")
        return

    # Step 4: Synthesize
    log.info("Loading TTS model (this may take a moment)...")
    from twinktalks.tts_engine import TTSEngine

    engine = TTSEngine(speaker=args.speaker)

    try:
        from tqdm import tqdm

        pbar = tqdm(total=len(chunks), desc="Generating speech", unit="chunk")

        def progress(current, total):
            pbar.update(1)

        start_time = time.time()
        waveform, sample_rate = engine.synthesize_chunks(
            chunks,
            language=args.language,
            progress_callback=progress,
        )
        pbar.close()
    except ImportError:
        # tqdm not available, use simple progress
        def progress(current, total):
            log.info("  Chunk %d/%d", current, total)

        start_time = time.time()
        waveform, sample_rate = engine.synthesize_chunks(
            chunks,
            language=args.language,
            progress_callback=progress,
        )

    elapsed = time.time() - start_time

    # Step 5: Save
    from twinktalks.audio_utils import save_audio, get_duration_seconds

    save_audio(waveform, str(output_path), sample_rate)
    duration = get_duration_seconds(waveform, sample_rate)

    log.info("Done! Saved to: %s", output_path)
    log.info("Audio duration: %.1f seconds (%.1f minutes)", duration, duration / 60)
    log.info("Generation time: %.1f seconds", elapsed)


if __name__ == "__main__":
    main()
