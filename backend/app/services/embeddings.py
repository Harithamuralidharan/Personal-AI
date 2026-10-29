
"""Generate document and query embeddings locally through Ollama."""

import httpx

from app.config import settings

EXPECTED_EMBEDDING_DIMENSION = 768
EMBEDDING_BATCH_SIZE = 32


def _embed_with_prefix(texts: list[str], prefix: str) -> list[list[float]]:
    """Embed a list of texts using the appropriate Nomic task prefix."""
    if not texts:
        return []

    base_url = settings.ollama_base_url.rstrip("/")
    all_vectors: list[list[float]] = []

    try:
        with httpx.Client(timeout=httpx.Timeout(180.0)) as client:
            for batch_start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                batch = texts[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
                inputs = [f"{prefix}{text}" for text in batch]

                response = client.post(
                    f"{base_url}/api/embed",
                    json={
                        "model": settings.ollama_embed_model,
                        "input": inputs,
                    },
                )
                response.raise_for_status()
                vectors = response.json().get("embeddings", [])

                if len(vectors) != len(batch):
                    raise RuntimeError(
                        "Ollama returned a different number of embeddings "
                        "than input texts."
                    )

                for vector in vectors:
                    if len(vector) != EXPECTED_EMBEDDING_DIMENSION:
                        raise RuntimeError(
                            f"Expected {EXPECTED_EMBEDDING_DIMENSION}-dimension "
                            f"embeddings, but received {len(vector)}. "
                            "Check the selected embedding model."
                        )

                all_vectors.extend(vectors)

    except httpx.ConnectError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama. Ensure Ollama is running and "
            "`nomic-embed-text` is downloaded."
        ) from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400]
        raise RuntimeError(
            f"Ollama returned HTTP {exc.response.status_code}: {detail}. "
            "Check that the embedding model is available."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    return all_vectors


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create embeddings for document chunks."""
    return _embed_with_prefix(texts, "search_document: ")


def embed_query(query: str) -> list[float]:
    """Create a single embedding for a user's search question."""
    if not query.strip():
        raise ValueError("The search question cannot be empty.")

    vectors = _embed_with_prefix([query], "search_query: ")
    return vectors[0]
