"""CLI entry point for TwinkTalks: PDF to Speech."""

import argparse
import logging
import re
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


def _sanitize_filename(title: str) -> str:
    """Convert a chapter title to a safe filename component."""
    s = re.sub(r'[^\w\s-]', '', title)
    s = re.sub(r'[\s]+', '_', s.strip())
    return s[:80] if s else "untitled"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="twinktalks",
        description="TwinkTalks - Convert PDF documents to speech using Qwen3-TTS",
    )
    parser.add_argument("input_file", help="Path to the input PDF or EPUB file")
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
        "--chapters", "--chapter",
        type=str,
        default=None,
        dest="chapters",
        help="Extract chapter(s): 'all' for every chapter, or a name/index (e.g. '3', 'Introduction')",
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


def _process_single(
    input_path: Path,
    output_path: Path,
    args,
    page_range: tuple[int, int] | None,
    log: logging.Logger,
    label: str = "",
):
    """Run the full extract -> preprocess -> chunk -> synthesize -> save pipeline."""
    prefix = f"{label} " if label else ""

    # Step 1: Extract
    log.info("%sExtracting text from %s...", prefix, input_path.name)
    from twinktalks.extractor import extract_text

    text = extract_text(
        str(input_path),
        skip_references=not args.no_skip_references,
        max_pages=args.max_pages,
        page_range=page_range,
        skip_tables=args.skip_tables,
    )
    log.info("%sExtracted %d characters.", prefix, len(text))

    # Step 2: Preprocess
    from twinktalks.text_preprocessor import preprocess

    text = preprocess(text)

    # Step 3: Chunk
    from twinktalks.chunker import chunk_text

    chunks = chunk_text(text)
    word_count = len(text.split())
    log.info("%s%d chunks (%d words).", prefix, len(chunks), word_count)

    if not chunks:
        log.warning("%sNo text to synthesize, skipping.", prefix)
        return

    # Dry run
    if args.dry_run:
        print(f"\n--- {prefix}Extracted & Preprocessed Text ---\n")
        print(text)
        print(f"\n--- {len(chunks)} chunks, {word_count} words ---")
        return

    # Step 4: Synthesize
    from twinktalks.tts_engine import TTSEngine
    from twinktalks.session import SessionManager

    engine = TTSEngine(speaker=args.speaker)
    mgr = SessionManager()

    start_from = 0
    session = None
    if args.resume:
        session = mgr.get_session(args.resume)
        if session is None:
            log.error("Session not found: %s", args.resume)
            sys.exit(1)
        start_from = session.completed_chunk
        log.info("%sResuming session %s from chunk %d/%d", prefix, session.id, start_from, session.total_chunks)
    else:
        session = mgr.create_session(
            pdf_path=str(input_path),
            total_chunks=len(chunks),
            settings={
                "speaker": args.speaker,
                "language": args.language,
                "speed": args.speed,
                "output": str(output_path),
                "label": label,
            },
        )

    session_dir = mgr.get_session_dir(session.id)

    try:
        from tqdm import tqdm

        pbar = tqdm(total=len(chunks), initial=start_from, desc=f"{prefix}Generating", unit="chunk")

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
        def progress(current, total):
            log.info("%s  Chunk %d/%d", prefix, current, total)
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_audio(waveform, str(output_path), sample_rate)
    duration = get_duration_seconds(waveform, sample_rate)

    log.info("%sSaved to: %s (%.1fs audio, %.1fs gen time)", prefix, output_path, duration, elapsed)


def main(argv: list[str] | None = None):
    parser = create_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    log = logging.getLogger("twinktalks")

    input_path = Path(args.input_file)

    # Handle --show-toc
    if args.show_toc:
        from twinktalks.extractor import extract_toc
        from twinktalks.toc import format_toc
        chapters = extract_toc(str(input_path))
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

    # Handle --chapters all (batch mode)
    if args.chapters and args.chapters.lower() == "all":
        from twinktalks.extractor import extract_toc
        chapters = extract_toc(str(input_path))
        if not chapters:
            log.error("No table of contents found. Cannot use --chapters all.")
            sys.exit(1)

        out_dir = Path(args.output) if args.output else Path("output") / input_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        log.info("Batch mode: %d chapters found.", len(chapters))

        for idx, ch in enumerate(chapters, 1):
            safe_title = _sanitize_filename(ch.title)
            chapter_output = out_dir / f"{idx:02d}_{safe_title}.{DEFAULT_OUTPUT_FORMAT}"
            label = f"[{idx}/{len(chapters)}]"

            log.info("\n%s %s (pages %d-%d)", label, ch.title, ch.start_page, ch.end_page)

            _process_single(
                input_path, chapter_output, args,
                page_range=(ch.start_page, ch.end_page),
                log=log,
                label=label,
            )

        log.info("\nAll %d chapters complete! Files saved to: %s/", len(chapters), out_dir)
        return

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output") / f"{input_path.stem}.{DEFAULT_OUTPUT_FORMAT}"

    # Parse page range
    page_range = None
    if args.pages:
        try:
            parts = args.pages.split("-")
            page_range = (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            log.error("Invalid --pages format. Use e.g. '3-7'")
            sys.exit(1)

    # If --chapters specified with a name/index, override page_range
    if args.chapters:
        from twinktalks.extractor import extract_toc
        from twinktalks.toc import find_chapter
        chapters = extract_toc(str(input_path))
        ch = find_chapter(chapters, args.chapters)
        if ch is None:
            log.error("Chapter not found: '%s'. Use --show-toc to see available chapters.", args.chapters)
            sys.exit(1)
        page_range = (ch.start_page, ch.end_page)
        log.info("Chapter: %s (pages %d-%d)", ch.title, ch.start_page, ch.end_page)

    _process_single(input_path, output_path, args, page_range=page_range, log=log)


if __name__ == "__main__":
    main()
