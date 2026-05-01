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


_nltk_ready = False


def _ensure_nltk_data():
    """Download punkt tokenizer if not available (cached after first check)."""
    global _nltk_ready
    if _nltk_ready:
        return
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)
    _nltk_ready = True


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


_SENTENCE_TERMINATORS = (".", "!", "?", '"', "'", ")", "]", "”", "’", ":", ";")


def _split_continuation(text: str) -> tuple[str, str]:
    """Pick the head of a continuation page: a paragraph break wins, else the first sentence."""
    if "\n\n" in text:
        head, _, rest = text.partition("\n\n")
        return head, rest
    _ensure_nltk_data()
    sentences = nltk.sent_tokenize(text)
    if not sentences:
        return text, ""
    head = sentences[0]
    rest = " ".join(sentences[1:])
    return head, rest


def _merge_page_continuations(
    page_texts: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    """Merge a page's tail into the next page when it appears to be mid-paragraph.

    PDFs frequently break paragraphs across page boundaries. Treating each page
    as an independent unit causes chunk_text to cut at the page break instead of
    at a sentence boundary, producing audibly clipped chunks. We detect this by
    checking whether the page's text ends with a sentence terminator; if not,
    the head of the next page (up to the first paragraph break, falling back to
    the first sentence) is appended to it. The continued chunk keeps the
    earlier page as its source_page.
    """
    nonempty = [(p, t) for p, t in page_texts if t and t.strip()]
    if not nonempty:
        return []

    result: list[tuple[int, str]] = [nonempty[0]]
    for page_num, text in nonempty[1:]:
        prev_page, prev_text = result[-1]
        if prev_text and not prev_text.rstrip().endswith(_SENTENCE_TERMINATORS):
            head, rest = _split_continuation(text)
            result[-1] = (prev_page, prev_text.rstrip() + " " + head.lstrip())
            if rest.strip():
                result.append((page_num, rest))
        else:
            result.append((page_num, text))
    return result


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

    for page_num, page_text in _merge_page_continuations(page_texts):
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
