"""Generate embeddings locally through the Ollama HTTP API."""

import httpx

from app.config import settings

EXPECTED_EMBEDDING_DIMENSION = 768
EMBEDDING_BATCH_SIZE = 32


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create local Nomic document embeddings in small batches; no paid API used."""
    if not texts:
        return []

    base_url = settings.ollama_base_url.rstrip("/")
    all_vectors: list[list[float]] = []

    try:
        with httpx.Client(timeout=httpx.Timeout(180.0)) as client:
            for batch_start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                batch = texts[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
                # Nomic recommends a task prefix for document-retrieval embeddings.
                inputs = [f"search_document: {text}" for text in batch]
                response = client.post(
                    f"{base_url}/api/embed",
                    json={"model": settings.ollama_embed_model, "input": inputs},
                )
                response.raise_for_status()
                vectors = response.json().get("embeddings", [])
                if len(vectors) != len(batch):
                    raise RuntimeError(
                        "Ollama returned a different number of embeddings than input chunks."
                    )
                for vector in vectors:
                    if len(vector) != EXPECTED_EMBEDDING_DIMENSION:
                        raise RuntimeError(
                            f"Expected {EXPECTED_EMBEDDING_DIMENSION}-dimension embeddings, "
                            f"but received {len(vector)}. Check the selected embedding model."
                        )
                all_vectors.extend(vectors)
    except httpx.ConnectError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama. Install/start Ollama and run `ollama pull nomic-embed-text`."
        ) from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400]
        raise RuntimeError(
            f"Ollama returned HTTP {exc.response.status_code}: {detail}. "
            "Check that `nomic-embed-text` is downloaded."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    return all_vectors
