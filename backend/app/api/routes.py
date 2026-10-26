"""Day 1 API endpoints: health checks and PDF ingestion."""

import hashlib
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models import Chunk, Document
from app.services.embeddings import EXPECTED_EMBEDDING_DIMENSION, embed_texts
from app.services.ingestion import chunk_pdf_pages, extract_pdf_pages

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Basic API liveness check; does not claim that the database/model is ready."""
    return {"status": "ok", "service": "Personal AI Workbench API"}


@router.get("/health/ready")
def readiness() -> dict[str, str]:
    """Check database connection and the pgvector extension."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            vector_enabled = connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is not available.") from exc

    if not vector_enabled:
        raise HTTPException(status_code=503, detail="The pgvector extension is not enabled yet.")
    return {"status": "ready", "database": "connected", "pgvector": "enabled"}


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """Extract PDF pages, create chunks, embed locally, then save to PostgreSQL."""
    raw_filename = file.filename or "uploaded.pdf"
    # Normalise slash styles so a client-supplied path cannot become a stored filename.
    filename = PurePosixPath(raw_filename.replace("\\", "/")).name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file (.pdf).")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    pdf_bytes = await file.read(max_bytes + 1)
    await file.close()
    if len(pdf_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum allowed size is {settings.max_upload_mb} MB.",
        )
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file does not look like a PDF.")

    try:
        page_count, page_texts = extract_pdf_pages(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chunks = chunk_pdf_pages(page_texts)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text chunks could be created from this PDF.")

    # Embed before starting the database write transaction, so an unavailable model
    # does not leave a half-created document row in the database.
    try:
        vectors = embed_texts([chunk_text for _, chunk_text, _ in chunks])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if len(vectors) != len(chunks):
        raise HTTPException(status_code=503, detail="Embedding count did not match chunk count.")

    document = Document(
        filename=filename,
        content_type=file.content_type or "application/pdf",
        file_size=len(pdf_bytes),
        sha256=hashlib.sha256(pdf_bytes).hexdigest(),
        page_count=page_count,
        status="processed",
    )

    try:
        db.add(document)
        db.flush()  # Ensures the generated document UUID is available before creating chunks.
        db.add_all(
            [
                Chunk(
                    document_id=document.id,
                    chunk_index=index,
                    page_number=page_number,
                    content=chunk_text,
                    token_count=token_count,
                    embedding=vector,
                )
                for index, ((page_number, chunk_text, token_count), vector) in enumerate(
                    zip(chunks, vectors, strict=True)
                )
            ]
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save the document and chunks.") from exc

    return {
        "status": "processed",
        "document_id": str(document.id),
        "filename": filename,
        "page_count": page_count,
        "chunk_count": len(chunks),
        "embedding_dimension": EXPECTED_EMBEDDING_DIMENSION,
        "note": "PDF text, page metadata, chunks, and embeddings were saved. The original PDF file is not stored on disk.",
    }
