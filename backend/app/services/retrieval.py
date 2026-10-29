
"""Retrieve relevant PDF chunks using PostgreSQL and pgvector."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.services.embeddings import embed_query


def retrieve_chunks(
    db: Session,
    question: str,
    top_k: int = 5,
    document_id: UUID | None = None,
) -> list[dict[str, object]]:
    """Return relevant chunks, optionally restricted to one PDF."""

    clean_question = question.strip()

    if not clean_question:
        raise ValueError("The search question cannot be empty.")

    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20.")

    # Embed the user's question.
    query_vector = embed_query(clean_question)

    # Calculate cosine distance in PostgreSQL.
    distance_expression = Chunk.embedding.cosine_distance(query_vector)

    # Fetch extra candidates to account for duplicate chunks.
    candidate_limit = min(max(top_k * 4, 20), 80)

    statement = (
        select(
            Chunk,
            Document.filename,
            distance_expression.label("distance"),
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.status == "processed")
    )

    # IMPORTANT: Restrict retrieval to the selected PDF when provided.
    if document_id is not None:
        statement = statement.where(Chunk.document_id == document_id)

    statement = (
        statement
        .order_by(distance_expression)
        .limit(candidate_limit)
    )

    rows = db.execute(statement).all()

    print("\n--- RETRIEVAL DEBUG ---")
    print(f"Question: {clean_question}")
    print(f"Selected document ID: {document_id}")
    print(f"Candidates retrieved: {len(rows)}")

    results: list[dict[str, object]] = []
    seen_chunks: set[tuple[str, int, str]] = set()

    for chunk, filename, distance in rows:
        content = (chunk.content or "").strip()

        if not content:
            continue

        print(
            f"File: {filename} | "
            f"Page: {chunk.page_number} | "
            f"Distance: {float(distance):.4f}"
        )
        print(content[:300])
        print("-" * 50)

        unique_key = (filename, chunk.page_number, content)

        if unique_key in seen_chunks:
            continue

        seen_chunks.add(unique_key)

        results.append(
            {
                "chunk_id": chunk.id,
                "document_id": str(chunk.document_id),
                "filename": filename,
                "page_number": chunk.page_number,
                "content": content,
                "distance": float(distance),
            }
        )

        if len(results) >= top_k:
            break

    print(f"Unique chunks returned: {len(results)}")
    print("--- END RETRIEVAL DEBUG ---\n")

    return results
