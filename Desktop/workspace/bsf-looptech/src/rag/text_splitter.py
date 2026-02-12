"""Text chunking utilities for knowledge base ingestion."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    index: int
    source_title: str


def split_text(
    text: str,
    source_title: str = "",
    chunk_size: int = 512,
    overlap: int = 50,
) -> list[TextChunk]:
    """Split text into overlapping chunks by character count.

    Uses sentence boundaries (。 or \\n) when possible.
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= chunk_size:
        return [TextChunk(text=text, index=0, source_title=source_title)]

    chunks: list[TextChunk] = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to break at sentence boundary
        if end < len(text):
            # Look for Japanese period or newline near the end
            best_break = -1
            for sep in ("。", "\n"):
                pos = text.rfind(sep, start, end)
                if pos > start and pos > best_break:
                    best_break = pos + len(sep)
            if best_break > start:
                end = best_break

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(TextChunk(text=chunk_text, index=idx, source_title=source_title))
            idx += 1

        # Advance with overlap — ensure forward progress
        new_start = end - overlap if end < len(text) else len(text)
        if new_start <= start:
            new_start = end
        start = new_start

    return chunks
