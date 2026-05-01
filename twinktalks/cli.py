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


def _process_merged(
    input_path: Path,
    output_path: Path,
    args,
    log: logging.Logger,
):
    """Synthesize every TOC chapter and merge into a single audiobook file.

    Writes one audio file (typically .m4b) with chapter atoms pointing at each
    chapter's start time. Used when --chapters all is combined with --merge-chapters.
    """
    import numpy as np
    from twinktalks.extractor import extract_text, extract_toc
    from twinktalks.text_preprocessor import preprocess
    from twinktalks.chunker import chunk_text
    from twinktalks.tts_engine import TTSEngine
    from twinktalks.audio_utils import (
        AudioChapter,
        add_chapter_markers,
        add_m4b_chapters,
        embed_metadata,
        generate_silence,
        get_duration_seconds,
        save_audio,
    )
    from twinktalks.book_metadata import extract_metadata

    INTER_CHAPTER_SILENCE_MS = 1500

    chapters = extract_toc(str(input_path))
    if not chapters:
        log.error("No table of contents found. Cannot use --merge-chapters.")
        sys.exit(1)

    engine = TTSEngine(speaker=args.speaker, model_path=getattr(args, "model_path", None))

    out_ext = output_path.suffix.lower()
    if out_ext not in (".mp3", ".m4b", ".wav"):
        log.error("--merge-chapters requires .m4b, .mp3, or .wav output. Got: %s", out_ext)
        sys.exit(1)

    segments: list[np.ndarray] = []
    audio_chapters: list[AudioChapter] = []
    cumulative_ms = 0
    sample_rate: int | None = None

    for idx, ch in enumerate(chapters, 1):
        log.info("[%d/%d] %s (pages %d-%d)", idx, len(chapters), ch.title, ch.start_page, ch.end_page)

        text = preprocess(extract_text(
            str(input_path),
            skip_references=not args.no_skip_references,
            page_range=(ch.start_page, ch.end_page),
            skip_tables=args.skip_tables,
        ))
        chunks = chunk_text(text)
        if not chunks:
            log.warning("[%d/%d] no text — skipping.", idx, len(chapters))
            continue

        progress, close_progress = _build_progress(
            f"[{idx}/{len(chapters)}] ", len(chunks), 0, _NullSessionManager(), None,
        )
        try:
            waveform, sr, _offsets = engine.synthesize_chunks(
                chunks,
                language=args.language,
                speed=args.speed,
                instruct=args.instruct,
                progress_callback=progress,
            )
        finally:
            close_progress()
        sample_rate = sr

        if segments:
            segments.append(generate_silence(INTER_CHAPTER_SILENCE_MS, sr))
            cumulative_ms += INTER_CHAPTER_SILENCE_MS

        chapter_start_ms = cumulative_ms
        segments.append(waveform)
        cumulative_ms += int(len(waveform) * 1000 / sr)

        audio_chapters.append(AudioChapter(
            title=ch.title,
            start_ms=chapter_start_ms,
            end_ms=cumulative_ms,
        ))

    if not segments:
        log.error("No audio generated — every chapter was empty.")
        sys.exit(1)

    final_waveform = np.concatenate(segments)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_audio(final_waveform, str(output_path), sample_rate)
    duration = get_duration_seconds(final_waveform, sample_rate)

    # Tag with title, author, cover
    meta = extract_metadata(str(input_path))
    if meta.title or meta.author or meta.has_cover():
        try:
            embed_metadata(str(output_path), meta)
        except Exception as e:
            log.warning("Metadata embedding failed: %s", e)

    # Chapter atoms — format-specific
    if out_ext == ".m4b":
        add_m4b_chapters(str(output_path), audio_chapters)
    elif out_ext == ".mp3":
        add_chapter_markers(str(output_path), audio_chapters)
    # WAV has no chapter container; skip silently.

    log.info(
        "Saved audiobook: %s (%.1fs audio, %d chapters)",
        output_path, duration, len(audio_chapters),
    )


class _NullSessionManager:
    """No-op session manager used by _process_merged where we don't checkpoint."""
    def update_progress(self, *args, **kwargs):
        pass


def _build_progress(prefix: str, total: int, start_from: int, mgr, session):
    """Build (callback, close) backed by tqdm. tqdm is a hard dependency."""
    from tqdm import tqdm
    pbar = tqdm(total=total, initial=start_from, desc=f"{prefix}Generating", unit="chunk")

    def callback(current, _total):
        pbar.update(1)
        mgr.update_progress(session, current)

    return callback, pbar.close


def _sanitize_filename(title: str) -> str:
    """Convert a chapter title to a safe filename component."""
    s = re.sub(r'[^\w\s-]', '', title)
    s = re.sub(r'[\s]+', '_', s.strip())
    return s[:80] if s else "untitled"


def _map_chunks_to_chapters(chunks, chunk_offsets_ms, toc_chapters, total_duration_ms):
    """Map chapter boundaries to audio timestamps based on chunk source pages."""
    from twinktalks.audio_utils import AudioChapter

    if not toc_chapters or not chunk_offsets_ms:
        return []

    audio_chapters = []
    for ch in toc_chapters:
        # Find the first chunk whose source_page falls within this chapter's range
        start_ms = None
        for i, chunk in enumerate(chunks):
            page = chunk.source_page or 1
            if ch.start_page <= page <= ch.end_page:
                if start_ms is None:
                    start_ms = chunk_offsets_ms[i]

        if start_ms is not None:
            audio_chapters.append(AudioChapter(
                title=ch.title,
                start_ms=start_ms,
                end_ms=total_duration_ms,
            ))

    # Fix end_ms: each chapter ends where the next begins
    for i in range(len(audio_chapters) - 1):
        audio_chapters[i] = AudioChapter(
            title=audio_chapters[i].title,
            start_ms=audio_chapters[i].start_ms,
            end_ms=audio_chapters[i + 1].start_ms,
        )

    return audio_chapters


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
        "--instruct",
        type=str,
        default="",
        help="Voice style instruction, e.g. 'Speak calmly like a narrator'",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help="Use a voice preset (e.g. 'Calm Narrator', 'Audiobook'). Overrides speaker/speed/instruct.",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available voice presets and exit",
    )
    parser.add_argument(
        "--skip-tables",
        action="store_true",
        help="Skip tables and diagrams detected in the PDF",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="OCR scanned PDFs before extraction (requires ocrmypdf + tesseract)",
    )
    parser.add_argument(
        "--ocr-language",
        type=str,
        default="eng",
        help="Tesseract language code for --ocr, e.g. 'eng', 'pol', 'eng+pol' (default: eng)",
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
        "--chapter-markers",
        action="store_true",
        help="Embed chapter markers in MP3 output (requires TOC and .mp3 output)",
    )
    parser.add_argument(
        "--merge-chapters",
        action="store_true",
        help="With --chapters all: produce a single audiobook file with all chapters concatenated and embedded chapter markers (best with .m4b output)",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Path to a local model directory (skip HuggingFace download)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and preprocess text only, print to stdout (no TTS)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Synthesize only the first chunk (~30s) so you can audition the voice before committing to a long run",
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
    use_chapter_markers = getattr(args, "chapter_markers", False)

    # Step 1: Extract
    log.info("%sExtracting text from %s...", prefix, input_path.name)
    from twinktalks.text_preprocessor import preprocess

    if use_chapter_markers:
        from twinktalks.extractor import extract_text_by_page
        page_texts = extract_text_by_page(
            str(input_path),
            skip_references=not args.no_skip_references,
            max_pages=args.max_pages,
            page_range=page_range,
            skip_tables=args.skip_tables,
            ocr=getattr(args, "ocr", False),
            ocr_language=getattr(args, "ocr_language", "eng"),
        )
        page_texts = [(pg, preprocess(t)) for pg, t in page_texts]
        text = "\n\n".join(t for _, t in page_texts)
        log.info("%sExtracted %d characters from %d pages.", prefix, len(text), len(page_texts))

        from twinktalks.chunker import chunk_paged_text
        chunks = chunk_paged_text(page_texts)
    else:
        from twinktalks.extractor import extract_text
        text = extract_text(
            str(input_path),
            skip_references=not args.no_skip_references,
            max_pages=args.max_pages,
            page_range=page_range,
            skip_tables=args.skip_tables,
            ocr=getattr(args, "ocr", False),
            ocr_language=getattr(args, "ocr_language", "eng"),
        )
        log.info("%sExtracted %d characters.", prefix, len(text))
        text = preprocess(text)

        from twinktalks.chunker import chunk_text
        chunks = chunk_text(text)

    word_count = len(text.split())
    log.info("%s%d chunks (%d words).", prefix, len(chunks), word_count)

    if not chunks:
        log.warning("%sNo text to synthesize, skipping.", prefix)
        return

    # Auto-detect language if requested
    from twinktalks.language_detect import resolve_language
    resolved_language = resolve_language(args.language, text)
    if resolved_language != args.language:
        log.info("%sDetected language: %s", prefix, resolved_language)
    args.language = resolved_language

    # Dry run
    if args.dry_run:
        print(f"\n--- {prefix}Extracted & Preprocessed Text ---\n")
        print(text)
        print(f"\n--- {len(chunks)} chunks, {word_count} words ---")
        return

    # Preview: synthesize only the first chunk so the user can audition the voice
    if getattr(args, "preview", False):
        from twinktalks.tts_engine import TTSEngine
        from twinktalks.audio_utils import save_audio, get_duration_seconds

        engine = TTSEngine(speaker=args.speaker, model_path=getattr(args, "model_path", None))
        log.info("%sRendering preview of first chunk (%d chars)...",
                 prefix, len(chunks[0].text))
        waveform, sr = engine.synthesize(
            chunks[0].text, language=args.language, speed=args.speed, instruct=args.instruct,
        )
        preview_path = output_path.with_name(f"{output_path.stem}_preview{output_path.suffix}")
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        save_audio(waveform, str(preview_path), sr)
        log.info("%sPreview saved: %s (%.1fs)", prefix, preview_path,
                 get_duration_seconds(waveform, sr))
        return

    # Step 4: Synthesize
    from twinktalks.tts_engine import TTSEngine
    from twinktalks.session import SessionManager

    engine = TTSEngine(speaker=args.speaker, model_path=getattr(args, "model_path", None))
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

    progress, close_progress = _build_progress(prefix, len(chunks), start_from, mgr, session)
    try:
        start_time = time.time()
        waveform, sample_rate, _offsets = engine.synthesize_chunks(
            chunks,
            language=args.language,
            speed=args.speed,
            instruct=args.instruct,
            progress_callback=progress,
            session_dir=session_dir,
            start_from=start_from,
        )
    finally:
        close_progress()

    elapsed = time.time() - start_time

    # Step 5: Save
    from twinktalks.audio_utils import save_audio, get_duration_seconds, embed_metadata

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_audio(waveform, str(output_path), sample_rate)
    duration = get_duration_seconds(waveform, sample_rate)
    out_ext = output_path.suffix.lower()

    # Step 6: Embed metadata (title, author, cover) for tagged formats
    if out_ext in (".mp3", ".m4b"):
        from twinktalks.book_metadata import extract_metadata
        meta = extract_metadata(str(input_path))
        if meta.title or meta.author or meta.has_cover():
            embed_metadata(str(output_path), meta)
            log.info("%sTagged: %s%s%s",
                     prefix,
                     f"title={meta.title!r}" if meta.title else "",
                     f", author={meta.author!r}" if meta.author else "",
                     ", cover" if meta.has_cover() else "")

    # Step 7: Embed chapter markers in MP3
    if use_chapter_markers and out_ext == ".mp3" and _offsets:
        from twinktalks.extractor import extract_toc
        from twinktalks.audio_utils import AudioChapter, add_chapter_markers

        toc_chapters = extract_toc(str(input_path))
        if toc_chapters:
            total_ms = int(duration * 1000)
            audio_chapters = _map_chunks_to_chapters(chunks, _offsets, toc_chapters, total_ms)
            if audio_chapters:
                add_chapter_markers(str(output_path), audio_chapters)
                log.info("%sEmbedded %d chapter markers.", prefix, len(audio_chapters))

    log.info("%sSaved to: %s (%.1fs audio, %.1fs gen time)", prefix, output_path, duration, elapsed)


def main(argv: list[str] | None = None):
    parser = create_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    log = logging.getLogger("twinktalks")

    # Handle --list-presets
    if args.list_presets:
        from twinktalks.presets import BUILTIN_PRESETS, load_user_presets
        print("Built-in presets:")
        for name, p in BUILTIN_PRESETS.items():
            instruct_preview = p["instruct"][:60] + "..." if len(p["instruct"]) > 60 else p["instruct"]
            print(f"  {name:20s}  {p['speaker']:8s}  {p['speed']}x  {instruct_preview or '(default)'}")
        user = load_user_presets()
        if user:
            print("\nUser presets:")
            for p in user:
                instruct_preview = p.instruct[:60] + "..." if len(p.instruct) > 60 else p.instruct
                print(f"  {p.name:20s}  {p.speaker:8s}  {p.speed}x  {instruct_preview or '(default)'}")
        return

    input_path = Path(args.input_file)

    # Apply --preset (overrides speaker, speed, instruct)
    if args.preset:
        from twinktalks.presets import resolve_preset
        preset = resolve_preset(args.preset)
        if preset is None:
            log.error("Preset not found: '%s'. Use --list-presets to see available presets.", args.preset)
            sys.exit(1)
        args.speaker = preset["speaker"]
        args.speed = preset["speed"]
        args.instruct = preset["instruct"]
        log.info("Using preset: %s (speaker=%s, speed=%s)", args.preset, args.speaker, args.speed)

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

    # Handle --chapters all + --merge-chapters: single audiobook file
    if args.chapters and args.chapters.lower() == "all" and args.merge_chapters:
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path("output") / f"{input_path.stem}.m4b"
        _process_merged(input_path, output_path, args, log)
        return

    # Handle --chapters all (batch mode — one file per chapter)
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
