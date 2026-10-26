"""Small deterministic tests that do not require Docker or Ollama."""

from app.services.ingestion import CHUNK_SIZE_TOKENS, TOKENIZER, chunk_page_text


def test_short_page_returns_one_chunk_and_keeps_page_number() -> None:
    chunks = chunk_page_text(7, "This is a short test paragraph.")

    assert len(chunks) == 1
    page_number, text, token_count = chunks[0]
    assert page_number == 7
    assert text == "This is a short test paragraph."
    assert token_count <= CHUNK_SIZE_TOKENS


def test_long_page_is_split_into_bounded_chunks() -> None:
    source = " ".join(f"word{i}" for i in range(1200))
    chunks = chunk_page_text(2, source)

    assert len(chunks) >= 2
    assert all(page_number == 2 for page_number, _, _ in chunks)
    assert all(token_count <= CHUNK_SIZE_TOKENS for _, _, token_count in chunks)
    assert all(token_count == len(TOKENIZER.encode(text)) for _, text, token_count in chunks)
