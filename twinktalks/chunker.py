"""Split text into TTS-appropriate chunks with sentence and paragraph awareness."""

from dataclasses import dataclass

import nltk

from twinktalks.config import MAX_CHUNK_CHARS


@dataclass
class Chunk:
    """A text chunk ready for TTS synthesis."""

    text: str
    index: int
    is_paragraph_end: bool
    source_page: int | None = None


def _ensure_nltk_data():
    """Download punkt tokenizer if not available."""
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[Chunk]:
    """Split text into chunks suitable for TTS generation.

    Strategy:
    1. Split into paragraphs
    2. Split paragraphs into sentences
    3. Group sentences into chunks that fit within max_chars
    4. Never break mid-sentence
    """
    _ensure_nltk_data()

    if not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    chunk_index = 0

    for para_idx, paragraph in enumerate(paragraphs):
        is_last_paragraph = para_idx == len(paragraphs) - 1
        sentences = nltk.sent_tokenize(paragraph)

        current_chunk_sentences: list[str] = []
        current_length = 0

        for sent_idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            is_last_sentence = sent_idx == len(sentences) - 1
            addition_length = len(sentence) + (1 if current_chunk_sentences else 0)

            # If adding this sentence would exceed limit, flush current chunk
            if current_chunk_sentences and current_length + addition_length > max_chars:
                chunks.append(Chunk(
                    text=" ".join(current_chunk_sentences),
                    index=chunk_index,
                    is_paragraph_end=False,
                ))
                chunk_index += 1
                current_chunk_sentences = []
                current_length = 0

            current_chunk_sentences.append(sentence)
            current_length += addition_length

            # If this is the last sentence in the paragraph, flush
            if is_last_sentence and current_chunk_sentences:
                chunks.append(Chunk(
                    text=" ".join(current_chunk_sentences),
                    index=chunk_index,
                    is_paragraph_end=not is_last_paragraph,
                ))
                chunk_index += 1
                current_chunk_sentences = []
                current_length = 0

    return chunks


def chunk_paged_text(
    page_texts: list[tuple[int, str]],
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[Chunk]:
    """Chunk text while preserving page origin.

    Args:
        page_texts: List of (page_number, text) tuples.

    Returns:
        Chunks with source_page set to the page they originated from.
    """
    chunks: list[Chunk] = []
    chunk_index = 0

    for page_num, page_text in page_texts:
        page_chunks = chunk_text(page_text, max_chars)
        for pc in page_chunks:
            chunks.append(Chunk(
                text=pc.text,
                index=chunk_index,
                is_paragraph_end=pc.is_paragraph_end,
                source_page=page_num,
            ))
            chunk_index += 1

    return chunks
