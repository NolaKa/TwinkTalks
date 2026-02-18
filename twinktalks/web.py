"""Gradio web UI for TwinkTalks — cyber brutalist aesthetic."""

import logging
import tempfile

import gradio as gr

from twinktalks.config import (
    AVAILABLE_SPEAKERS,
    DEFAULT_SPEAKER,
    DEFAULT_LANGUAGE,
)

logger = logging.getLogger(__name__)

_engine = None

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;700;900&display=swap');

:root {
    --bg: #0a0a0a;
    --surface: #111111;
    --border: #2a2a2a;
    --accent: #c8ff00;
    --accent-dim: #4a5f00;
    --text: #e0e0e0;
    --text-dim: #666666;
    --danger: #ff3333;
    --mono: 'Space Mono', 'SF Mono', monospace;
    --sans: 'Inter', system-ui, sans-serif;
}

body, .gradio-container {
    background: var(--bg) !important;
    font-family: var(--sans) !important;
    max-width: 900px !important;
    margin: 0 auto !important;
}

/* Header */
.header-block {
    border-bottom: 3px solid var(--accent) !important;
    padding: 2rem 0 1.5rem !important;
    margin-bottom: 2rem !important;
    background: none !important;
}
.header-block h1 {
    font-family: var(--mono) !important;
    font-size: 2.4rem !important;
    font-weight: 700 !important;
    color: var(--accent) !important;
    letter-spacing: -0.02em !important;
    margin: 0 !important;
    line-height: 1 !important;
}
.header-block p {
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    color: var(--text-dim) !important;
    margin: 0.5rem 0 0 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.15em !important;
}

/* All panels / containers */
.gr-panel, .gr-box, .gr-form, .gr-input-label,
div[class*="block"], div[class*="wrap"] {
    border-radius: 0 !important;
}

/* Input containers */
.input-section {
    border: 2px solid var(--border) !important;
    background: var(--surface) !important;
    padding: 1.5rem !important;
    border-radius: 0 !important;
}
.input-section:hover {
    border-color: var(--accent-dim) !important;
}

/* Labels */
label, .gr-input-label, span[data-testid="block-label"] {
    font-family: var(--mono) !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: var(--text-dim) !important;
}

/* File upload */
.upload-zone {
    border: 2px dashed var(--border) !important;
    background: var(--bg) !important;
    border-radius: 0 !important;
    padding: 3rem 2rem !important;
    transition: border-color 0.2s !important;
}
.upload-zone:hover {
    border-color: var(--accent) !important;
}

/* Dropdowns & inputs */
select, input[type="text"], textarea,
.gr-input, .gr-text-input, .gr-dropdown {
    background: var(--bg) !important;
    border: 2px solid var(--border) !important;
    border-radius: 0 !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.85rem !important;
    padding: 0.6rem 0.8rem !important;
}
select:focus, input:focus, textarea:focus {
    border-color: var(--accent) !important;
    outline: none !important;
    box-shadow: none !important;
}

/* Checkbox */
input[type="checkbox"] {
    accent-color: var(--accent) !important;
}

/* Buttons */
.generate-btn {
    background: var(--accent) !important;
    color: var(--bg) !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    padding: 0.9rem 2rem !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
}
.generate-btn:hover {
    background: #dfff33 !important;
    transform: translateY(-1px) !important;
}
.preview-btn {
    background: transparent !important;
    color: var(--text-dim) !important;
    border: 2px solid var(--border) !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-weight: 400 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    padding: 0.9rem 1.5rem !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
}
.preview-btn:hover {
    border-color: var(--text-dim) !important;
    color: var(--text) !important;
}

/* Status bar */
.status-bar textarea {
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    background: var(--bg) !important;
    border: 2px solid var(--border) !important;
    border-left: 3px solid var(--accent) !important;
    border-radius: 0 !important;
    color: var(--accent) !important;
    padding: 0.8rem 1rem !important;
}

/* Audio player */
.audio-output {
    border: 2px solid var(--border) !important;
    background: var(--surface) !important;
    border-radius: 0 !important;
    padding: 1rem !important;
}

/* Accordion */
.gr-accordion {
    border: 2px solid var(--border) !important;
    border-radius: 0 !important;
    background: var(--surface) !important;
}
.gr-accordion summary, .gr-accordion button {
    font-family: var(--mono) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: var(--text-dim) !important;
}

/* Text preview */
.text-preview textarea {
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    line-height: 1.6 !important;
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 0 !important;
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
    gap: 1rem !important;
}

/* Page range inputs */
.page-range {
    gap: 1rem !important;
    margin-top: 0.5rem !important;
}
.page-input input[type="number"] {
    background: var(--bg) !important;
    border: 2px solid var(--border) !important;
    border-radius: 0 !important;
    color: var(--accent) !important;
    font-family: var(--mono) !important;
    font-size: 1rem !important;
    text-align: center !important;
    width: 5rem !important;
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


def on_pdf_upload(pdf_file):
    """Called when a PDF is uploaded. Returns page count and shows page selectors."""
    if pdf_file is None:
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "// READY"

    from twinktalks.pdf_extractor import get_page_count
    try:
        total = get_page_count(pdf_file.name)
        return (
            gr.update(visible=True, value=1, maximum=total),
            gr.update(visible=True, value=total, maximum=total),
            gr.update(visible=True, value=f"{total}"),
            f"// LOADED — {total} pages",
        )
    except Exception as e:
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), f"// ERROR — {e}"


def process_pdf(
    pdf_file,
    page_start,
    page_end,
    page_info,
    speaker: str,
    language: str,
    skip_references: bool,
) -> tuple[str, str | None, str]:
    """Full pipeline: PDF -> text -> audio."""
    if pdf_file is None:
        return "// NO FILE", None, ""

    try:
        total = int(page_info) if page_info else 9999
        page_range = _get_page_range(page_start, page_end, total)

        from twinktalks.pdf_extractor import extract_text
        text = extract_text(pdf_file.name, skip_references=skip_references, page_range=page_range)

        from twinktalks.text_preprocessor import preprocess
        text = preprocess(text)

        from twinktalks.chunker import chunk_text
        chunks = chunk_text(text)
        word_count = len(text.split())

        pages_info = f"p.{page_range[0]}-{page_range[1]}" if page_range else "all"
        status = f"// PROCESSING — {word_count} words, {len(chunks)} chunks ({pages_info})"
        yield status, None, text

        engine = _get_engine(speaker)
        waveform, sample_rate = engine.synthesize_chunks(
            chunks,
            language=language,
            progress_callback=lambda c, t: None,
        )

        from twinktalks.audio_utils import save_audio, get_duration_seconds
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        save_audio(waveform, tmp.name, sample_rate)
        duration = get_duration_seconds(waveform, sample_rate)

        status = f"// DONE — {duration:.1f}s audio / {word_count} words / {len(chunks)} chunks"
        yield status, tmp.name, text

    except Exception as e:
        yield f"// ERROR — {e}", None, ""


def extract_only(pdf_file, page_start, page_end, page_info, skip_references: bool) -> str:
    """Extract and preprocess text without TTS."""
    if pdf_file is None:
        return "// NO FILE"

    total = int(page_info) if page_info else 9999
    page_range = _get_page_range(page_start, page_end, total)

    from twinktalks.pdf_extractor import extract_text
    from twinktalks.text_preprocessor import preprocess

    text = extract_text(pdf_file.name, skip_references=skip_references, page_range=page_range)
    return preprocess(text)


def create_app() -> gr.Blocks:
    with gr.Blocks(title="TwinkTalks") as app:

        # Header
        gr.Markdown(
            "<h1>TWINKTALKS_</h1><p>pdf &rarr; speech // qwen3-tts</p>",
            elem_classes=["header-block"],
        )

        # Upload
        pdf_input = gr.File(
            label="INPUT",
            file_types=[".pdf"],
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
            skip_refs = gr.Checkbox(
                value=True,
                label="SKIP REFERENCES",
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

        # Text preview
        with gr.Accordion("EXTRACTED TEXT", open=False):
            text_preview = gr.Textbox(
                label="",
                lines=15,
                interactive=False,
                elem_classes=["text-preview"],
            )

        # Events: on upload -> detect pages, show page selectors
        pdf_input.change(
            fn=on_pdf_upload,
            inputs=[pdf_input],
            outputs=[page_start, page_end, page_info, status],
        )

        preview_btn.click(
            fn=extract_only,
            inputs=[pdf_input, page_start, page_end, page_info, skip_refs],
            outputs=[text_preview],
        )
        generate_btn.click(
            fn=process_pdf,
            inputs=[pdf_input, page_start, page_end, page_info, speaker, language, skip_refs],
            outputs=[status, audio_output, text_preview],
        )

    return app


def main():
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, max_file_size="100mb", css=CUSTOM_CSS)


if __name__ == "__main__":
    main()
