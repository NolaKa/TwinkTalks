"""CLI entry point for TwinkTalks: PDF to Speech."""

import argparse
import logging
import sys
import time
from pathlib import Path

from twinktalks.config import (
    DEFAULT_SPEAKER,
    DEFAULT_LANGUAGE,
    DEFAULT_SPEED,
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
        "--pages",
        type=str,
        default=None,
        help="Page range to extract, e.g. '3-7' or '5-5' for single page",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=DEFAULT_SPEED,
        help=f"Speaking speed 0.5-2.0 (default: {DEFAULT_SPEED})",
    )
    parser.add_argument(
        "--skip-tables",
        action="store_true",
        help="Skip tables and diagrams detected in the PDF",
    )
    parser.add_argument(
        "--show-toc",
        action="store_true",
        help="Show table of contents and exit",
    )
    parser.add_argument(
        "--chapter",
        type=str,
        default=None,
        help="Extract specific chapter by name or index (e.g. '3' or 'Introduction')",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume a previous session by ID",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List saved sessions and exit",
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

    # Handle --show-toc and --chapter
    if args.show_toc or args.chapter:
        from twinktalks.toc import extract_toc, format_toc, find_chapter
        chapters = extract_toc(str(input_path))

        if args.show_toc:
            print(format_toc(chapters))
            return

    # Handle --list-sessions
    if args.list_sessions:
        from twinktalks.session import SessionManager
        mgr = SessionManager()
        sessions = mgr.list_sessions()
        if not sessions:
            print("No saved sessions.")
        else:
            for s in sessions:
                print(f"  {s.id}  {Path(s.pdf_path).name}  chunk {s.completed_chunk}/{s.total_chunks}  [{s.updated_at}]")
        return

    # Parse page range
    page_range = None
    if args.pages:
        try:
            parts = args.pages.split("-")
            page_range = (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            log.error("Invalid --pages format. Use e.g. '3-7'")
            sys.exit(1)

    # If --chapter specified, override page_range
    if args.chapter:
        from twinktalks.toc import extract_toc, find_chapter
        chapters = extract_toc(str(input_path))
        ch = find_chapter(chapters, args.chapter)
        if ch is None:
            log.error("Chapter not found: '%s'. Use --show-toc to see available chapters.", args.chapter)
            sys.exit(1)
        page_range = (ch.start_page, ch.end_page)
        log.info("Chapter: %s (pages %d-%d)", ch.title, ch.start_page, ch.end_page)

    # Step 1: Extract text
    log.info("Extracting text from %s...", input_path.name)
    from twinktalks.pdf_extractor import extract_text

    text = extract_text(
        str(input_path),
        skip_references=not args.no_skip_references,
        max_pages=args.max_pages,
        page_range=page_range,
        skip_tables=args.skip_tables,
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
    from twinktalks.session import SessionManager

    engine = TTSEngine(speaker=args.speaker)
    mgr = SessionManager()

    # Resume or create session
    start_from = 0
    session = None
    if args.resume:
        session = mgr.get_session(args.resume)
        if session is None:
            log.error("Session not found: %s", args.resume)
            sys.exit(1)
        start_from = session.completed_chunk
        log.info("Resuming session %s from chunk %d/%d", session.id, start_from, session.total_chunks)
    else:
        session = mgr.create_session(
            pdf_path=str(input_path),
            total_chunks=len(chunks),
            settings={
                "speaker": args.speaker,
                "language": args.language,
                "speed": args.speed,
                "output": str(output_path),
            },
        )
        log.info("Session created: %s", session.id)

    session_dir = mgr.get_session_dir(session.id)

    try:
        from tqdm import tqdm

        pbar = tqdm(total=len(chunks), initial=start_from, desc="Generating speech", unit="chunk")

        def progress(current, total):
            pbar.update(1)
            mgr.update_progress(session, current)

        start_time = time.time()
        waveform, sample_rate = engine.synthesize_chunks(
            chunks,
            language=args.language,
            speed=args.speed,
            progress_callback=progress,
            session_dir=session_dir,
            start_from=start_from,
        )
        pbar.close()
    except ImportError:
        # tqdm not available, use simple progress
        def progress(current, total):
            log.info("  Chunk %d/%d", current, total)
            mgr.update_progress(session, current)

        start_time = time.time()
        waveform, sample_rate = engine.synthesize_chunks(
            chunks,
            language=args.language,
            speed=args.speed,
            progress_callback=progress,
            session_dir=session_dir,
            start_from=start_from,
        )

    elapsed = time.time() - start_time

    # Step 5: Save
    from twinktalks.audio_utils import save_audio, get_duration_seconds

    save_audio(waveform, str(output_path), sample_rate)
    duration = get_duration_seconds(waveform, sample_rate)

    log.info("Done! Saved to: %s", output_path)
    log.info("Audio duration: %.1f seconds (%.1f minutes)", duration, duration / 60)
    log.info("Generation time: %.1f seconds", elapsed)
    log.info("Session ID (for resume): %s", session.id)


if __name__ == "__main__":
    main()
