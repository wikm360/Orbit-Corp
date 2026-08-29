import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size_tokens: int, overlap_tokens: int) -> list[str]:
    """Split text into overlapping chunks measured in tokens.

    Token-based (rather than character-based) sizing keeps chunks close to a
    predictable size regardless of source format, and lines up with how the
    embedding/LLM providers bill and limit context.
    """
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
