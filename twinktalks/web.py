"""Gradio web UI for TwinkTalks."""

import logging
import tempfile
from pathlib import Path

import gradio as gr

from twinktalks.config import (
    AVAILABLE_SPEAKERS,
    DEFAULT_SPEAKER,
    DEFAULT_LANGUAGE,
)

logger = logging.getLogger(__name__)

# Lazy-loaded engine (shared across requests)
_engine = None


def _get_engine(speaker: str):
    global _engine
    from twinktalks.tts_engine import TTSEngine

    if _engine is None or _engine.speaker != speaker:
        _engine = TTSEngine(speaker=speaker)
    return _engine


def process_pdf(
    pdf_file,
    speaker: str,
    language: str,
    skip_references: bool,
) -> tuple[str, str | None, str]:
    """Full pipeline: PDF -> text -> audio."""
    if pdf_file is None:
        return "No PDF uploaded.", None, ""

    try:
        # Extract
        from twinktalks.pdf_extractor import extract_text

        text = extract_text(
            pdf_file.name,
            skip_references=skip_references,
        )

        # Preprocess
        from twinktalks.text_preprocessor import preprocess

        text = preprocess(text)

        # Chunk
        from twinktalks.chunker import chunk_text

        chunks = chunk_text(text)
        word_count = len(text.split())

        status = f"Extracted {word_count} words, {len(chunks)} chunks. Generating speech..."
        yield status, None, text

        # Synthesize
        engine = _get_engine(speaker)

        def progress(current, total):
            pass  # Gradio doesn't support live updates in yield mode easily

        waveform, sample_rate = engine.synthesize_chunks(
            chunks,
            language=language,
            progress_callback=progress,
        )

        # Save to temp file
        from twinktalks.audio_utils import save_audio, get_duration_seconds

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        save_audio(waveform, tmp.name, sample_rate)
        duration = get_duration_seconds(waveform, sample_rate)

        status = f"Done! {duration:.1f}s of audio ({word_count} words, {len(chunks)} chunks)"
        yield status, tmp.name, text

    except Exception as e:
        yield f"Error: {e}", None, ""


def extract_only(pdf_file, skip_references: bool) -> str:
    """Extract and preprocess text without TTS."""
    if pdf_file is None:
        return "No PDF uploaded."

    from twinktalks.pdf_extractor import extract_text
    from twinktalks.text_preprocessor import preprocess

    text = extract_text(pdf_file.name, skip_references=skip_references)
    return preprocess(text)


def create_app() -> gr.Blocks:
    with gr.Blocks(title="TwinkTalks") as app:
        gr.Markdown("# TwinkTalks\nPDF to Speech using Qwen3-TTS")

        with gr.Row():
            with gr.Column(scale=1):
                pdf_input = gr.File(
                    label="Upload PDF",
                    file_types=[".pdf"],
                )
                speaker = gr.Dropdown(
                    choices=AVAILABLE_SPEAKERS,
                    value=DEFAULT_SPEAKER,
                    label="Speaker",
                )
                language = gr.Dropdown(
                    choices=["Auto", "English", "Chinese", "Japanese", "Korean",
                             "German", "French", "Russian", "Portuguese",
                             "Spanish", "Italian"],
                    value=DEFAULT_LANGUAGE,
                    label="Language",
                )
                skip_refs = gr.Checkbox(
                    value=True,
                    label="Skip References section",
                )

                with gr.Row():
                    preview_btn = gr.Button("Preview Text")
                    generate_btn = gr.Button("Generate Speech", variant="primary")

            with gr.Column(scale=1):
                status = gr.Textbox(label="Status", interactive=False)
                audio_output = gr.Audio(label="Generated Audio", type="filepath")

        with gr.Accordion("Extracted Text Preview", open=False):
            text_preview = gr.Textbox(
                label="Preprocessed text",
                lines=20,
                interactive=False,
            )

        preview_btn.click(
            fn=extract_only,
            inputs=[pdf_input, skip_refs],
            outputs=[text_preview],
        )

        generate_btn.click(
            fn=process_pdf,
            inputs=[pdf_input, speaker, language, skip_refs],
            outputs=[status, audio_output, text_preview],
        )

    return app


def main():
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
