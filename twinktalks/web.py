"""Gradio web UI for TwinkTalks."""

import logging
import tempfile

import gradio as gr

from twinktalks.config import (
    AVAILABLE_SPEAKERS,
    DEFAULT_SPEAKER,
    DEFAULT_LANGUAGE,
    DEFAULT_SPEED,
    SPEED_MIN,
    SPEED_MAX,
)

logger = logging.getLogger(__name__)

_engine = None
_temp_dirs: list[str] = []  # track temp dirs for cleanup


def _make_temp_dir() -> str:
    """Create a temp dir and track it for cleanup."""
    import shutil
    # Clean up previous temp dirs (files already served by Gradio)
    for old_dir in _temp_dirs:
        try:
            shutil.rmtree(old_dir, ignore_errors=True)
        except Exception:
            pass
    _temp_dirs.clear()
    d = tempfile.mkdtemp(prefix="twinktalks_")
    _temp_dirs.append(d)
    return d

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #0c0c10;
    --surface: #16161d;
    --surface-hover: #1c1c26;
    --border: #26263a;
    --border-hover: #36365a;
    --accent: #c8ff00;
    --accent-hover: #dfff33;
    --accent-subtle: rgba(200,255,0,0.06);
    --accent-glow: rgba(200,255,0,0.15);
    --text: #e4e4ed;
    --text-secondary: #9191a8;
    --text-dim: #5c5c72;
    --success: #34d399;
    --mono: 'JetBrains Mono', 'SF Mono', monospace;
    --sans: 'Inter', -apple-system, system-ui, sans-serif;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow-sm: 0 2px 8px rgba(0,0,0,0.2);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.3);
    --transition: 0.2s cubic-bezier(0.4,0,0.2,1);
}

body, .gradio-container {
    background: var(--bg) !important;
    font-family: var(--sans) !important;
    max-width: 960px !important;
    margin: 0 auto !important;
    color: var(--text) !important;
}

/* Header */
.header-block {
    padding: 2.5rem 0 1.5rem !important;
    margin-bottom: 1.5rem !important;
    background: none !important;
    border: none !important;
}
.header-block h1 {
    font-family: var(--sans) !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: var(--text) !important;
    letter-spacing: -0.03em !important;
    margin: 0 !important;
    line-height: 1.2 !important;
}
.header-block h1 span.accent {
    color: var(--accent) !important;
}
.header-block p {
    font-family: var(--sans) !important;
    font-size: 0.85rem !important;
    color: var(--text-dim) !important;
    margin: 0.4rem 0 0 !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
}

/* Row containers — clip children to rounded corners */
.gr-group, .gr-row,
div[class*="row"], div[class*="group"] {
    overflow: hidden !important;
}
/* Blocks inside rows — no extra radius (parent clips) */
.gr-group > div, .gr-row > div {
    border-radius: 0 !important;
}

/* Labels */
label, .gr-input-label, span[data-testid="block-label"] {
    font-family: var(--sans) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: var(--text-secondary) !important;
}

/* File upload */
.upload-zone {
    border: 2px dashed var(--border) !important;
    background: var(--surface) !important;
    border-radius: var(--radius) !important;
    padding: 2.5rem 2rem !important;
    transition: all var(--transition) !important;
}
.upload-zone:hover {
    border-color: var(--accent) !important;
    background: var(--accent-subtle) !important;
}

/* Dropdowns & inputs */
select, input[type="text"], textarea,
.gr-input, .gr-text-input, .gr-dropdown {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
    font-size: 0.875rem !important;
    padding: 0.6rem 0.8rem !important;
    transition: all var(--transition) !important;
}
select:focus, input:focus, textarea:focus {
    border-color: var(--accent) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
}

/* Checkbox */
input[type="checkbox"] {
    accent-color: var(--accent) !important;
}

/* Buttons */
.generate-btn {
    background: var(--accent) !important;
    color: #0c0c10 !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-family: var(--sans) !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.75rem 2rem !important;
    cursor: pointer !important;
    transition: all var(--transition) !important;
    box-shadow: 0 2px 12px rgba(200,255,0,0.2) !important;
}
.generate-btn:hover {
    background: var(--accent-hover) !important;
    box-shadow: 0 4px 20px rgba(200,255,0,0.3) !important;
    transform: translateY(-1px) !important;
}
.preview-btn {
    background: var(--surface) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    font-family: var(--sans) !important;
    font-weight: 500 !important;
    font-size: 0.825rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.75rem 1.5rem !important;
    cursor: pointer !important;
    transition: all var(--transition) !important;
}
.preview-btn:hover {
    border-color: var(--border-hover) !important;
    background: var(--surface-hover) !important;
    color: var(--text) !important;
}

/* Status bar */
.status-bar textarea {
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-left: 3px solid var(--accent) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--accent) !important;
    padding: 0.8rem 1rem !important;
}

/* Audio player */
.audio-output {
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    border-radius: var(--radius) !important;
    padding: 1rem !important;
    box-shadow: var(--shadow-sm) !important;
}

/* Accordion */
.gr-accordion {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--surface) !important;
    overflow: hidden !important;
}
.gr-accordion summary, .gr-accordion button {
    font-family: var(--sans) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: var(--text-secondary) !important;
}

/* Text preview */
.text-preview textarea {
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    line-height: 1.7 !important;
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
}

/* Section divider */
.divider {
    border-top: 1px solid var(--border) !important;
    margin: 1.5rem 0 !important;
    background: none !important;
}

/* Options row */
.options-row {
    gap: 0.75rem !important;
}

/* Page range inputs */
.page-range {
    gap: 1rem !important;
    margin-top: 0.5rem !important;
}
.page-input input[type="number"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--accent) !important;
    font-family: var(--mono) !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    text-align: center !important;
    width: 5rem !important;
}

/* Radio buttons — override Gradio orange */
.gr-radio input[type="radio"],
input[type="radio"] {
    accent-color: var(--accent) !important;
}
/* Radio group pill styling */
.gr-radio-row label,
div[data-testid="radio-group"] label {
    border-radius: var(--radius-sm) !important;
}

/* Slider — override Gradio orange track */
input[type="range"] {
    accent-color: var(--accent) !important;
}
input[type="range"]::-webkit-slider-runnable-track {
    background: var(--border) !important;
    border-radius: 4px !important;
    height: 4px !important;
}
input[type="range"]::-webkit-slider-thumb {
    background: var(--accent) !important;
    border: none !important;
    border-radius: 50% !important;
    width: 16px !important;
    height: 16px !important;
    margin-top: -6px !important;
    box-shadow: 0 0 8px var(--accent-glow) !important;
}
/* Gradio 6 slider color override */
.gr-slider input[type="range"],
div[data-testid="slider"] input[type="range"] {
    accent-color: var(--accent) !important;
}

/* Gradio progress/track bar color */
.range-slider .bar,
div[data-testid="slider"] .progress {
    background: var(--accent) !important;
}

/* Checkbox — override Gradio orange */
input[type="checkbox"],
.gr-checkbox input[type="checkbox"] {
    accent-color: var(--accent) !important;
}
.gr-check-radio input:checked {
    background-color: var(--accent) !important;
    border-color: var(--accent) !important;
}
/* Gradio 6 checkbox/radio SVG color */
.checkbox-container input:checked,
label input[type="checkbox"]:checked {
    accent-color: var(--accent) !important;
    background-color: var(--accent) !important;
}
/* Radio selected pill */
.radio-group label.selected,
label.selected span,
.wrap label input[type="radio"]:checked + span {
    color: var(--accent) !important;
    border-color: var(--accent) !important;
}
/* Global accent override for Gradio oranges */
.svelte-cmf5ev, [class*="selected"] {
    --color-accent: var(--accent) !important;
    accent-color: var(--accent) !important;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 6px !important;
    height: 6px !important;
}
::-webkit-scrollbar-track {
    background: var(--bg) !important;
}
::-webkit-scrollbar-thumb {
    background: var(--border) !important;
    border-radius: 3px !important;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--border-hover) !important;
}

/* Completed files panel */
.gr-files {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--surface) !important;
}

/* Number input spinner */
input[type="number"] {
    -moz-appearance: textfield !important;
}
input[type="number"]::-webkit-inner-spin-button {
    opacity: 0.5 !important;
}

/* Footer kill */
footer { display: none !important; }
"""


def _get_engine(speaker: str):
    global _engine
    from twinktalks.tts_engine import TTSEngine

    if _engine is None or _engine.speaker != speaker:
        _engine = TTSEngine(speaker=speaker)
    return _engine


def _get_page_range(start, end, total) -> tuple[int, int] | None:
    """Convert input values to page_range tuple. None means all pages."""
    s = int(start) if start else 1
    e = int(end) if end else total
    if s <= 1 and e >= total:
        return None
    return (max(1, s), min(total, e))


def on_files_upload(files):
    """Called when file(s) are uploaded. Handles single and multi-file modes."""
    if files is None or len(files) == 0:
        return (
            gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False, choices=[], value=None),
            "// READY",
        )

    if len(files) > 1:
        # Queue mode: hide page range & chapter, show queue summary
        from pathlib import Path
        names = [Path(f.name).name for f in files]
        return (
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False, choices=[], value=None),
            f"// QUEUE — {len(files)} files: {', '.join(names)}",
        )

    # Single file: show page range & TOC as before
    pdf_file = files[0]
    from twinktalks.extractor import get_item_count, extract_toc as get_toc
    try:
        total = get_item_count(pdf_file.name)
        is_epub = pdf_file.name.lower().endswith(".epub")

        # Try to extract TOC
        toc_choices = ["All chapters" if is_epub else "All pages"]
        try:
            chapters = get_toc(pdf_file.name)
            for ch in chapters:
                indent = "  " * (ch.level - 1)
                pages = f"p.{ch.start_page}-{ch.end_page}"
                toc_choices.append(f"{indent}{ch.title}  [{pages}]")
        except Exception:
            pass

        show_toc = len(toc_choices) > 1

        return (
            gr.update(visible=True, value=1, maximum=total),
            gr.update(visible=True, value=total, maximum=total),
            gr.update(visible=True, value=f"{total}"),
            gr.update(visible=show_toc, choices=toc_choices, value="All pages"),
            f"// LOADED — {total} pages" + (f", {len(toc_choices) - 1} chapters" if show_toc else ""),
        )
    except Exception as e:
        return (
            gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False, choices=[], value=None),
            f"// ERROR — {e}",
        )


def on_chapter_select(chapter_choice, files):
    """When a chapter is selected from the dropdown, update FROM/TO page inputs."""
    if not files or len(files) != 1:
        return gr.update(), gr.update()

    pdf_file = files[0]
    if not chapter_choice or chapter_choice in ("All pages", "All chapters"):
        from twinktalks.extractor import get_item_count
        try:
            total = get_item_count(pdf_file.name)
            return gr.update(value=1), gr.update(value=total)
        except Exception:
            return gr.update(), gr.update()

    # Parse page range from the choice string: "Title  [p.3-7]"
    import re
    match = re.search(r'\[p\.(\d+)-(\d+)\]', chapter_choice)
    if match:
        return gr.update(value=int(match.group(1))), gr.update(value=int(match.group(2)))
    return gr.update(), gr.update()


def _extract_and_preprocess(file_path: str, skip_references: bool, skip_tables: bool, page_range=None) -> str:
    """Shared extract + preprocess pipeline."""
    from twinktalks.extractor import extract_text
    from twinktalks.text_preprocessor import preprocess
    text = extract_text(
        file_path,
        skip_references=skip_references,
        page_range=page_range,
        skip_tables=skip_tables,
    )
    return preprocess(text)


def _synthesize_single_file(
    file_path: str, stem: str, tmp_dir: str,
    page_range, speaker, language, speed, skip_references, skip_tables, instruct,
    output_format: str = "wav",
    status_prefix: str = "",
):
    """Generator: synthesize one file, yielding (status, audio_path, text) per chunk."""
    from twinktalks.chunker import chunk_text
    from twinktalks.audio_utils import save_audio, get_duration_seconds
    import os

    text = _extract_and_preprocess(file_path, skip_references, skip_tables, page_range)
    chunks = chunk_text(text)
    word_count = len(text.split())

    if not chunks:
        yield f"{status_prefix}// NO TEXT", None, text
        return

    pages_info = f"p.{page_range[0]}-{page_range[1]}" if page_range else "all"
    speed_info = f" @{speed}x" if speed != 1.0 else ""
    yield f"{status_prefix}// PROCESSING — {word_count} words, {len(chunks)} chunks ({pages_info}){speed_info}", None, text

    engine = _get_engine(speaker)

    prev_tmp = None
    final_offsets = None
    for cumulative, sample_rate, current, total_chunks, offsets in engine.synthesize_chunks_streaming(
        chunks, language=language, speed=speed, instruct=instruct or "",
    ):
        tmp_path = os.path.join(tmp_dir, f"{stem}_{current}of{total_chunks}.wav")
        save_audio(cumulative, tmp_path, sample_rate)
        duration = get_duration_seconds(cumulative, sample_rate)

        if offsets is not None:
            final_offsets = offsets

        if prev_tmp and os.path.exists(prev_tmp):
            os.unlink(prev_tmp)
        prev_tmp = tmp_path

        if current < total_chunks:
            yield f"{status_prefix}// GENERATING — chunk {current}/{total_chunks} — {duration:.1f}s", tmp_path, text
        else:
            ext = output_format if output_format in ("wav", "mp3") else "wav"
            final_path = os.path.join(tmp_dir, f"{stem}.{ext}")

            if ext == "mp3":
                save_audio(cumulative, final_path, sample_rate)
                os.unlink(tmp_path)
            else:
                os.rename(tmp_path, final_path)
            prev_tmp = None

            # Embed chapter markers in MP3 if TOC is available
            if ext == "mp3" and final_offsets:
                try:
                    from twinktalks.extractor import extract_toc
                    from twinktalks.audio_utils import add_chapter_markers
                    toc_chapters = extract_toc(file_path)
                    if toc_chapters:
                        total_ms = int(duration * 1000)
                        # Use paged extraction for chapter mapping
                        from twinktalks.extractor import extract_text_by_page
                        from twinktalks.text_preprocessor import preprocess as pp
                        from twinktalks.chunker import chunk_paged_text
                        page_texts = extract_text_by_page(
                            file_path, skip_references=skip_references,
                            page_range=page_range, skip_tables=skip_tables,
                        )
                        page_texts = [(pg, pp(t)) for pg, t in page_texts]
                        paged_chunks = chunk_paged_text(page_texts)

                        from twinktalks.cli import _map_chunks_to_chapters
                        audio_chapters = _map_chunks_to_chapters(
                            paged_chunks, final_offsets, toc_chapters, total_ms,
                        )
                        if audio_chapters:
                            add_chapter_markers(final_path, audio_chapters)
                except Exception:
                    pass  # Chapter markers are best-effort

            yield f"{status_prefix}// DONE — {duration:.1f}s audio / {word_count} words / {total_chunks} chunks", final_path, text


def process_queue(
    files,
    page_start,
    page_end,
    page_info,
    speaker: str,
    language: str,
    speed: float,
    skip_references: bool,
    skip_tables: bool,
    output_format: str,
    instruct: str = "",
):
    """Process one or multiple files. Generator yielding (status, audio, text, completed_files)."""
    if files is None or len(files) == 0:
        yield "// NO FILE", None, "", None
        return

    from pathlib import Path
    fmt = output_format if output_format in ("wav", "mp3") else "wav"

    try:
        if len(files) == 1:
            # Single file mode: use page range as before
            pdf_file = files[0]
            total = int(page_info) if page_info else 9999
            page_range = _get_page_range(page_start, page_end, total)
            stem = Path(pdf_file.name).stem
            tmp_dir = _make_temp_dir()

            for status, audio, text in _synthesize_single_file(
                pdf_file.name, stem, tmp_dir,
                page_range, speaker, language, speed, skip_references, skip_tables, instruct,
                output_format=fmt,
            ):
                yield status, audio, text, None
            return

        # Queue mode: process each file sequentially
        completed_paths = []
        tmp_dir = tempfile.mkdtemp()

        for file_idx, file_obj in enumerate(files, 1):
            stem = Path(file_obj.name).stem
            file_name = Path(file_obj.name).name
            file_tmp_dir = f"{tmp_dir}/{stem}_{file_idx}"
            import os
            os.makedirs(file_tmp_dir, exist_ok=True)

            final_audio = None

            for status, audio, text in _synthesize_single_file(
                file_obj.name, stem, file_tmp_dir,
                None, speaker, language, speed, skip_references, skip_tables, instruct,
                output_format=fmt,
                status_prefix=f"// QUEUE {file_idx}/{len(files)} — \"{file_name}\" — ",
            ):
                final_audio = audio
                yield status, audio, text, completed_paths if completed_paths else None

            if final_audio:
                completed_paths.append(final_audio)

        yield (
            f"// QUEUE COMPLETE — {len(files)} files processed",
            completed_paths[-1] if completed_paths else None,
            "",
            completed_paths,
        )

    except Exception as e:
        yield f"// ERROR — {e}", None, "", None


def extract_only(files, page_start, page_end, page_info, skip_references: bool, skip_tables: bool) -> str:
    """Extract and preprocess text without TTS."""
    if not files or len(files) == 0:
        return "// NO FILE"

    pdf_file = files[0]  # Preview works for first/single file
    total = int(page_info) if page_info else 9999
    page_range = _get_page_range(page_start, page_end, total)

    return _extract_and_preprocess(pdf_file.name, skip_references, skip_tables, page_range)


def create_app() -> gr.Blocks:
    with gr.Blocks(title="TwinkTalks") as app:

        # Header
        gr.Markdown(
            "<h1>Twink<span class='accent'>Talks</span></h1><p>PDF & EPUB to speech — powered by Qwen3-TTS</p>",
            elem_classes=["header-block"],
        )

        # Upload (multiple files supported for queue mode)
        pdf_input = gr.File(
            label="INPUT",
            file_types=[".pdf", ".epub"],
            file_count="multiple",
            elem_classes=["upload-zone"],
        )

        # Page range (hidden until PDF loaded)
        with gr.Row(elem_classes=["page-range"]):
            page_start = gr.Number(
                value=1,
                label="FROM PAGE",
                minimum=1,
                precision=0,
                visible=False,
                elem_classes=["page-input"],
            )
            page_end = gr.Number(
                value=1,
                label="TO PAGE",
                minimum=1,
                precision=0,
                visible=False,
                elem_classes=["page-input"],
            )
            # Hidden field to store total page count
            page_info = gr.Textbox(value="", visible=False)

        # Chapter selector (hidden until PDF with TOC loaded)
        chapter_dropdown = gr.Dropdown(
            choices=["All pages"],
            value="All pages",
            label="CHAPTER",
            visible=False,
        )

        # Options row
        with gr.Row(elem_classes=["options-row"]):
            speaker = gr.Dropdown(
                choices=AVAILABLE_SPEAKERS,
                value=DEFAULT_SPEAKER,
                label="VOICE",
            )
            language = gr.Dropdown(
                choices=["Auto", "English", "Chinese", "Japanese", "Korean",
                         "German", "French", "Russian", "Portuguese",
                         "Spanish", "Italian"],
                value=DEFAULT_LANGUAGE,
                label="LANGUAGE",
            )
            speed_slider = gr.Slider(
                minimum=SPEED_MIN,
                maximum=SPEED_MAX,
                value=DEFAULT_SPEED,
                step=0.1,
                label="SPEED",
            )

        with gr.Row(elem_classes=["options-row"]):
            skip_refs = gr.Checkbox(
                value=True,
                label="SKIP REFERENCES",
            )
            skip_tables = gr.Checkbox(
                value=False,
                label="SKIP TABLES",
            )
            output_format = gr.Radio(
                choices=["wav", "mp3"],
                value="wav",
                label="FORMAT",
            )

        # Voice style
        with gr.Accordion("VOICE STYLE", open=False):
            from twinktalks.presets import get_all_preset_names, resolve_preset, save_user_preset, VoicePreset

            preset_dropdown = gr.Dropdown(
                choices=get_all_preset_names(),
                value="Default",
                label="PRESET",
            )
            instruct_box = gr.Textbox(
                value="",
                label="INSTRUCT",
                placeholder="e.g. Speak calmly like an audiobook narrator",
                lines=2,
            )
            with gr.Row():
                save_name = gr.Textbox(
                    label="SAVE AS",
                    placeholder="My Preset",
                    scale=3,
                )
                save_btn = gr.Button(
                    "SAVE",
                    elem_classes=["preview-btn"],
                    scale=1,
                )

        # Actions
        with gr.Row():
            preview_btn = gr.Button(
                "PREVIEW TEXT",
                elem_classes=["preview-btn"],
            )
            generate_btn = gr.Button(
                "GENERATE",
                variant="primary",
                elem_classes=["generate-btn"],
            )

        # Divider
        gr.HTML("<div class='divider'></div>")

        # Status
        status = gr.Textbox(
            label="STATUS",
            interactive=False,
            value="// READY",
            elem_classes=["status-bar"],
        )

        # Audio output
        audio_output = gr.Audio(
            label="OUTPUT",
            type="filepath",
            elem_classes=["audio-output"],
        )

        # Completed files (queue mode — shows all finished files for download)
        completed_files = gr.Files(
            label="COMPLETED FILES",
            visible=False,
        )

        # Text preview
        with gr.Accordion("EXTRACTED TEXT", open=False):
            text_preview = gr.Textbox(
                label="",
                lines=15,
                interactive=False,
                elem_classes=["text-preview"],
            )

        # Events: on upload -> detect pages, show page selectors and TOC
        pdf_input.change(
            fn=on_files_upload,
            inputs=[pdf_input],
            outputs=[page_start, page_end, page_info, chapter_dropdown, status],
        )

        # Chapter selection -> update page range
        chapter_dropdown.change(
            fn=on_chapter_select,
            inputs=[chapter_dropdown, pdf_input],
            outputs=[page_start, page_end],
        )

        preview_btn.click(
            fn=extract_only,
            inputs=[pdf_input, page_start, page_end, page_info, skip_refs, skip_tables],
            outputs=[text_preview],
        )
        generate_btn.click(
            fn=process_queue,
            inputs=[pdf_input, page_start, page_end, page_info, speaker, language, speed_slider, skip_refs, skip_tables, output_format, instruct_box],
            outputs=[status, audio_output, text_preview, completed_files],
        )

        # Preset selection -> apply settings
        def on_preset_select(preset_name):
            preset = resolve_preset(preset_name)
            if preset is None:
                return gr.update(), gr.update(), gr.update()
            return (
                gr.update(value=preset["speaker"]),
                gr.update(value=preset["speed"]),
                gr.update(value=preset["instruct"]),
            )

        preset_dropdown.change(
            fn=on_preset_select,
            inputs=[preset_dropdown],
            outputs=[speaker, speed_slider, instruct_box],
        )

        # Save preset
        def on_save_preset(name, spkr, spd, inst):
            if not name or not name.strip():
                return gr.update()
            save_user_preset(VoicePreset(
                name=name.strip(),
                speaker=spkr,
                speed=spd,
                instruct=inst,
            ))
            return gr.update(choices=get_all_preset_names(), value=f"* {name.strip()}")

        save_btn.click(
            fn=on_save_preset,
            inputs=[save_name, speaker, speed_slider, instruct_box],
            outputs=[preset_dropdown],
        )

    return app


def _make_theme():
    """Create the custom dark theme with yellow accent for Gradio 6."""
    return gr.themes.Base(
        primary_hue=gr.themes.Color(
            c50="#fefff0", c100="#fcffdb", c200="#f5ffb0",
            c300="#ecff7a", c400="#dfff33", c500="#c8ff00",
            c600="#a3d000", c700="#7da000", c800="#5a7300",
            c900="#3d4f00", c950="#243000",
        ),
        neutral_hue=gr.themes.Color(
            c50="#e4e4ed", c100="#c9c9d6", c200="#9191a8",
            c300="#5c5c72", c400="#36365a", c500="#26263a",
            c600="#1c1c26", c700="#16161d", c800="#111117",
            c900="#0c0c10", c950="#08080c",
        ),
        font=["Inter", "system-ui", "sans-serif"],
        font_mono=["JetBrains Mono", "SF Mono", "monospace"],
    ).set(
        body_background_fill="#0c0c10",
        body_background_fill_dark="#0c0c10",
        block_background_fill="#16161d",
        block_background_fill_dark="#16161d",
        block_border_color="#26263a",
        block_border_color_dark="#26263a",
        block_label_text_color="#9191a8",
        block_label_text_color_dark="#9191a8",
        block_title_text_color="#e4e4ed",
        block_title_text_color_dark="#e4e4ed",
        body_text_color="#e4e4ed",
        body_text_color_dark="#e4e4ed",
        body_text_color_subdued="#5c5c72",
        body_text_color_subdued_dark="#5c5c72",
        input_background_fill="#16161d",
        input_background_fill_dark="#16161d",
        input_border_color="#26263a",
        input_border_color_dark="#26263a",
        button_primary_background_fill="#c8ff00",
        button_primary_background_fill_dark="#c8ff00",
        button_primary_background_fill_hover="#dfff33",
        button_primary_background_fill_hover_dark="#dfff33",
        button_primary_text_color="#0c0c10",
        button_primary_text_color_dark="#0c0c10",
        button_secondary_background_fill="#16161d",
        button_secondary_background_fill_dark="#16161d",
        button_secondary_border_color="#26263a",
        button_secondary_border_color_dark="#26263a",
        button_secondary_text_color="#9191a8",
        button_secondary_text_color_dark="#9191a8",
        border_color_accent="#c8ff00",
        border_color_accent_dark="#c8ff00",
        color_accent="#c8ff00",
        color_accent_soft="rgba(200,255,0,0.06)",
        color_accent_soft_dark="rgba(200,255,0,0.06)",
        block_radius="12px",
        input_radius="8px",
        button_large_radius="8px",
        slider_color="#c8ff00",
        slider_color_dark="#c8ff00",
        checkbox_background_color="#16161d",
        checkbox_background_color_dark="#16161d",
        checkbox_background_color_selected="#c8ff00",
        checkbox_background_color_selected_dark="#c8ff00",
        checkbox_border_color="#26263a",
        checkbox_border_color_dark="#26263a",
        checkbox_border_color_selected="#c8ff00",
        checkbox_border_color_selected_dark="#c8ff00",
    )


def main():
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, max_file_size="100mb", css=CUSTOM_CSS, theme=_make_theme())


if __name__ == "__main__":
    main()
