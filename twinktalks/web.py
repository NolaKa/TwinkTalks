"""Gradio web UI for TwinkTalks."""

import logging
import os
import tempfile
from pathlib import Path

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

_CSS_PATH = Path(__file__).parent / "assets" / "twinktalks.css"
CUSTOM_CSS = _CSS_PATH.read_text()


def _get_engine():
    """Return the cached TTSEngine. Speaker is selected per call, not per engine —
    Qwen3-TTS-CustomVoice takes speaker as a generation parameter, so the model
    weights are shared across all speakers."""
    global _engine
    from twinktalks.tts_engine import TTSEngine

    model_path = os.environ.get("TWINKTALKS_MODEL_PATH")
    if _engine is None:
        _engine = TTSEngine(model_path=model_path)
    return _engine


def _get_page_range(start, end, total) -> tuple[int, int] | None:
    """Convert input values to page_range tuple. None means all pages."""
    s = int(start) if start else 1
    e = int(end) if end else total
    if s <= 1 and e >= total:
        return None
    return (max(1, s), min(total, e))


def on_files_upload(files):
    """Called when file(s) are uploaded. Handles single and multi-file modes.

    Returns: (page_range_row, page_start, page_end, page_info, chapter_dropdown, status)
    """
    if files is None or len(files) == 0:
        return (
            gr.update(visible=False), gr.update(), gr.update(), "",
            gr.update(visible=False, choices=[], value=None),
            "// READY",
        )

    if len(files) > 1:
        # Queue mode: hide page range & chapter, show queue summary
        from pathlib import Path
        names = [Path(f.name).name for f in files]
        return (
            gr.update(visible=False), gr.update(), gr.update(), "",
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
        except Exception as e:
            logger.warning("TOC extraction failed: %s", e)

        show_toc = len(toc_choices) > 1

        return (
            gr.update(visible=True),
            gr.update(value=1, maximum=total),
            gr.update(value=total, maximum=total),
            f"{total}",
            gr.update(visible=show_toc, choices=toc_choices, value="All pages"),
            f"// LOADED — {total} pages" + (f", {len(toc_choices) - 1} chapters" if show_toc else ""),
        )
    except Exception as e:
        logger.exception("File upload failed: %s", e)
        return (
            gr.update(visible=False), gr.update(), gr.update(), "",
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
        except Exception as e:
            logger.warning("Failed to get page count: %s", e)
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

    text = _extract_and_preprocess(file_path, skip_references, skip_tables, page_range)
    chunks = chunk_text(text)
    word_count = len(text.split())

    if not chunks:
        yield f"{status_prefix}// NO TEXT", None, text
        return

    pages_info = f"p.{page_range[0]}-{page_range[1]}" if page_range else "all"
    speed_info = f" @{speed}x" if speed != 1.0 else ""
    yield f"{status_prefix}// PROCESSING — {word_count} words, {len(chunks)} chunks ({pages_info}){speed_info}", None, text

    engine = _get_engine()

    prev_tmp = None
    final_offsets = None
    for cumulative, sample_rate, current, total_chunks, offsets in engine.synthesize_chunks_streaming(
        chunks, language=language, speed=speed, instruct=instruct or "", speaker=speaker,
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
                except Exception as e:
                    logger.warning("Chapter marker embedding failed: %s", e)

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
        logger.exception("Generation failed: %s", e)
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
            "<h1>TWINKTALKS</h1><p>pdf / epub &rarr; speech &mdash; qwen3-tts</p>",
            elem_classes=["header-block"],
        )

        # === Two-column layout ===
        with gr.Row(elem_classes=["main-row"], equal_height=False):

            # ---- LEFT COLUMN: Input & Controls ----
            with gr.Column(scale=1, elem_classes=["panel-left"]):
                gr.Markdown("&gt; input", elem_classes=["panel-label"])

                pdf_input = gr.File(
                    label="FILE",
                    file_types=[".pdf", ".epub"],
                    file_count="multiple",
                    elem_classes=["upload-zone"],
                )

                # Page range — compact inline
                with gr.Row(visible=False, elem_classes=["page-range"]) as page_range_row:
                    page_start = gr.Number(
                        value=1, label="PAGES", minimum=1, precision=0,
                        elem_classes=["page-input"],
                    )
                    page_end = gr.Number(
                        value=1, label="\u2014", minimum=1, precision=0,
                        elem_classes=["page-input"],
                    )
                page_info = gr.State("")

                chapter_dropdown = gr.Dropdown(
                    choices=["All pages"], value="All pages",
                    label="CHAPTER", visible=False,
                )


                # Voice settings
                with gr.Row(elem_classes=["options-row"]):
                    speaker = gr.Dropdown(
                        choices=AVAILABLE_SPEAKERS, value=DEFAULT_SPEAKER,
                        label="VOICE",
                    )
                    language = gr.Dropdown(
                        choices=["Auto", "English", "Chinese", "Japanese", "Korean",
                                 "German", "French", "Russian", "Portuguese",
                                 "Spanish", "Italian"],
                        value=DEFAULT_LANGUAGE, label="LANGUAGE",
                    )

                speed_slider = gr.Slider(
                    minimum=SPEED_MIN, maximum=SPEED_MAX,
                    value=DEFAULT_SPEED, step=0.1, label="SPEED",
                )

                with gr.Row(elem_classes=["options-row"]):
                    skip_refs = gr.Checkbox(value=True, label="SKIP REFERENCES")
                    skip_tables = gr.Checkbox(value=False, label="SKIP TABLES")

                output_format = gr.Radio(
                    choices=["wav", "mp3"], value="wav", label="FORMAT",
                    elem_classes=["format-inline"],
                )


                # Voice style
                with gr.Accordion("VOICE STYLE", open=False):
                    from twinktalks.presets import get_all_preset_names, resolve_preset, save_user_preset, VoicePreset

                    preset_dropdown = gr.Dropdown(
                        choices=get_all_preset_names(), value="Default",
                        label="PRESET",
                    )
                    instruct_box = gr.Textbox(
                        value="", label="INSTRUCT",
                        placeholder="e.g. Speak calmly like an audiobook narrator",
                        lines=2,
                    )
                    with gr.Row():
                        save_name = gr.Textbox(
                            label="SAVE AS", placeholder="My Preset", scale=3,
                        )
                        save_btn = gr.Button("SAVE", elem_classes=["preview-btn"], scale=1)

                # Action buttons
                with gr.Row():
                    preview_btn = gr.Button("PREVIEW TEXT", elem_classes=["preview-btn"])
                    generate_btn = gr.Button("GENERATE", variant="primary", elem_classes=["generate-btn"])

            # ---- RIGHT COLUMN: Output ----
            with gr.Column(scale=1, elem_classes=["panel-right"]):
                gr.Markdown("&gt; output", elem_classes=["panel-label"])

                status = gr.Textbox(
                    label="STATUS", interactive=False, value="// READY",
                    elem_classes=["status-bar"],
                )

                audio_output = gr.Audio(
                    label="OUTPUT", type="filepath",
                    elem_classes=["audio-output"],
                )

                completed_files = gr.Files(
                    label="COMPLETED FILES", visible=False,
                )


                with gr.Accordion("EXTRACTED TEXT", open=False):
                    text_preview = gr.Textbox(
                        label="", lines=15, interactive=False,
                        show_label=False,
                        elem_classes=["text-preview"],
                    )

        # === Events ===
        pdf_input.change(
            fn=on_files_upload, inputs=[pdf_input],
            outputs=[page_range_row, page_start, page_end, page_info, chapter_dropdown, status],
        )
        chapter_dropdown.change(
            fn=on_chapter_select, inputs=[chapter_dropdown, pdf_input],
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
            fn=on_preset_select, inputs=[preset_dropdown],
            outputs=[speaker, speed_slider, instruct_box],
        )

        def on_save_preset(name, spkr, spd, inst):
            if not name or not name.strip():
                return gr.update()
            save_user_preset(VoicePreset(
                name=name.strip(), speaker=spkr, speed=spd, instruct=inst,
            ))
            return gr.update(choices=get_all_preset_names(), value=f"* {name.strip()}")

        save_btn.click(
            fn=on_save_preset,
            inputs=[save_name, speaker, speed_slider, instruct_box],
            outputs=[preset_dropdown],
        )

    return app


def _make_theme():
    """Create the retro amber terminal theme for Gradio 6."""
    return gr.themes.Base(
        primary_hue=gr.themes.Color(
            c50="#fef3d0", c100="#fde6a0", c200="#f8d060",
            c300="#f0c030", c400="#e8b82a", c500="#d4a017",
            c600="#b08010", c700="#8a600a", c800="#604005",
            c900="#3a2500", c950="#1a1000",
        ),
        neutral_hue=gr.themes.Color(
            c50="#d4a017", c100="#a07810", c200="#7a5a10",
            c300="#6b5010", c400="#4a3800", c500="#2a2000",
            c600="#1a1400", c700="#0f0f0f", c800="#0c0c0c",
            c900="#0a0a0a", c950="#050505",
        ),
        font=[gr.themes.GoogleFont("IBM Plex Mono"), "SF Mono", "Courier New", "monospace"],
        font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "SF Mono", "Courier New", "monospace"],
    ).set(
        body_background_fill="#0a0a0a",
        body_background_fill_dark="#0a0a0a",
        block_background_fill="#0a0a0a",
        block_background_fill_dark="#0a0a0a",
        block_border_color="transparent",
        block_border_color_dark="transparent",
        block_label_text_color="#7a5a10",
        block_label_text_color_dark="#7a5a10",
        block_title_text_color="#d4a017",
        block_title_text_color_dark="#d4a017",
        body_text_color="#d4a017",
        body_text_color_dark="#d4a017",
        body_text_color_subdued="#6b5010",
        body_text_color_subdued_dark="#6b5010",
        input_background_fill="#0a0a0a",
        input_background_fill_dark="#0a0a0a",
        input_border_color="#2a2000",
        input_border_color_dark="#2a2000",
        button_primary_background_fill="transparent",
        button_primary_background_fill_dark="transparent",
        button_primary_background_fill_hover="#d4a017",
        button_primary_background_fill_hover_dark="#d4a017",
        button_primary_text_color="#d4a017",
        button_primary_text_color_dark="#d4a017",
        button_primary_border_color="#d4a017",
        button_primary_border_color_dark="#d4a017",
        button_secondary_background_fill="transparent",
        button_secondary_background_fill_dark="transparent",
        button_secondary_border_color="#2a2000",
        button_secondary_border_color_dark="#2a2000",
        button_secondary_text_color="#7a5a10",
        button_secondary_text_color_dark="#7a5a10",
        border_color_accent="#d4a017",
        border_color_accent_dark="#d4a017",
        color_accent="#d4a017",
        color_accent_soft="rgba(212,160,23,0.06)",
        color_accent_soft_dark="rgba(212,160,23,0.06)",
        block_radius="0px",
        input_radius="0px",
        button_large_radius="0px",
        slider_color="#d4a017",
        slider_color_dark="#d4a017",
        checkbox_background_color="#0a0a0a",
        checkbox_background_color_dark="#0a0a0a",
        checkbox_background_color_selected="#d4a017",
        checkbox_background_color_selected_dark="#d4a017",
        checkbox_border_color="#2a2000",
        checkbox_border_color_dark="#2a2000",
        checkbox_border_color_selected="#d4a017",
        checkbox_border_color_selected_dark="#d4a017",
    )


def main():
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, max_file_size="100mb", css=CUSTOM_CSS, theme=_make_theme())


if __name__ == "__main__":
    main()
