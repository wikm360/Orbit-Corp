from dataclasses import dataclass, field
import logging

from app.features.documents.ingestion.parser import DocumentPage

logger = logging.getLogger(__name__)

_encoding = None
try:
    import tiktoken

    _encoding = tiktoken.get_encoding("cl100k_base")
except Exception as exc:
    logger.warning(
        "Tiktoken encoding cl100k_base not available offline (%s). Using robust built-in chunker.",
        exc,
    )
    _encoding = None


@dataclass
class PageChunk:
    content: str
    page_number: int  # 1-indexed
    chunk_index_in_page: int
    metadata: dict = field(default_factory=dict)


def chunk_text(text: str, chunk_size_tokens: int, overlap_tokens: int) -> list[str]:
    """Split text into overlapping chunks measured in tokens.

    If tiktoken is available locally, it splits using BPE tokens.
    Otherwise, an offline word-based tokenizer is used to eliminate any
    external network dependency and avoid timeouts or connection errors.
    """
    if not text or not text.strip():
        return []

    if _encoding is not None:
        try:
            tokens = _encoding.encode(text)
            if not tokens:
                return []

            chunks: list[str] = []
            step = max(chunk_size_tokens - overlap_tokens, 1)
            for start in range(0, len(tokens), step):
                window = tokens[start : start + chunk_size_tokens]
                chunk = _encoding.decode(window).strip()
                if chunk:
                    chunks.append(chunk)
                if start + chunk_size_tokens >= len(tokens):
                    break
            return chunks
        except Exception as err:
            logger.warning("Tiktoken encode failed (%s), falling back to offline chunker.", err)

    # Robust offline fallback:
    # 1 token is roughly 0.75 words across Persian and English text.
    words = text.split()
    if not words:
        return []

    words_per_chunk = max(int(chunk_size_tokens * 0.75), 10)
    words_overlap = min(max(int(overlap_tokens * 0.75), 1), words_per_chunk - 1)
    step = max(words_per_chunk - words_overlap, 1)

    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + words_per_chunk]
        chunk = " ".join(chunk_words).strip()
        if chunk:
            chunks.append(chunk)
        if start + words_per_chunk >= len(words):
            break

    return chunks


def chunk_document_pages(
    pages: list[DocumentPage],
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> list[PageChunk]:
    """Chunks text page by page, preserving true page numbers and structure."""
    total_pages = len(pages)
    all_chunks: list[PageChunk] = []

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        raw_chunks = chunk_text(text, chunk_size_tokens, overlap_tokens)
        for idx, chunk_content in enumerate(raw_chunks):
            meta = {
                "page": page.page_number,
                "total_pages": total_pages,
                "chunk_in_page": idx + 1,
                "total_chunks_in_page": len(raw_chunks),
                **page.metadata,
            }
            all_chunks.append(
                PageChunk(
                    content=chunk_content,
                    page_number=page.page_number,
                    chunk_index_in_page=idx,
                    metadata=meta,
                )
            )

    return all_chunks
