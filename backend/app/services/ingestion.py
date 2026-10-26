"""PDF text extraction and repeatable token-based chunking."""

from io import BytesIO

import tiktoken
from pypdf import PdfReader

# This local tokenizer is used only to define a reproducible 500-token chunk size.
# It does not call any external API and is not the internal tokenizer of Nomic embeddings.
TOKENIZER = tiktoken.get_encoding("cl100k_base")
CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50


def extract_pdf_pages(pdf_bytes: bytes) -> tuple[int, list[tuple[int, str]]]:
    """Return (total_page_count, non-empty (1-based page number, text) pairs)."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported in Day 1.")

        page_texts: list[tuple[int, str]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                page_texts.append((page_number, text))

        if not page_texts:
            raise ValueError(
                "No selectable text was found. This may be a scanned/image-only PDF; OCR is not included in Day 1."
            )
        return len(reader.pages), page_texts
    except ValueError:
        raise
    except Exception as exc:  # pypdf can raise several parsing errors for malformed PDFs.
        raise ValueError("The PDF could not be read. Please try a valid, unencrypted PDF.") from exc


def chunk_page_text(page_number: int, text: str) -> list[tuple[int, str, int]]:
    """Chunk one page into <=500 cl100k_base tokens with a 50-token overlap.

    Chunks never cross page boundaries, so citations can retain an exact source page.
    Returns (page_number, chunk_text, token_count) tuples.
    """
    token_ids = TOKENIZER.encode(text)
    if not token_ids:
        return []

    results: list[tuple[int, str, int]] = []
    start = 0
    while start < len(token_ids):
        end = min(start + CHUNK_SIZE_TOKENS, len(token_ids))
        chunk_tokens = token_ids[start:end]
        chunk_text = TOKENIZER.decode(chunk_tokens).strip()
        if chunk_text:
            results.append((page_number, chunk_text, len(chunk_tokens)))
        if end >= len(token_ids):
            break
        start = end - CHUNK_OVERLAP_TOKENS

    return results


def chunk_pdf_pages(page_texts: list[tuple[int, str]]) -> list[tuple[int, str, int]]:
    """Chunk extracted pages while preserving each original page number."""
    all_chunks: list[tuple[int, str, int]] = []
    for page_number, text in page_texts:
        all_chunks.extend(chunk_page_text(page_number, text))
    return all_chunks
