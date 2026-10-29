
"""API endpoints: health checks, PDF ingestion, and document-specific Q&A."""

import hashlib
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models import Chunk, Document
from app.services.answering import generate_answer
from app.services.embeddings import EXPECTED_EMBEDDING_DIMENSION, embed_texts
from app.services.ingestion import chunk_pdf_pages, extract_pdf_pages
from app.services.retrieval import retrieve_chunks

router = APIRouter()


class AskRequest(BaseModel):
    """Validate a user's document question."""

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_name: str = Field(min_length=1, max_length=255)


@router.get("/health")
def health() -> dict[str, str]:
    """Basic API liveness check."""
    return {"status": "ok", "service": "Personal AI Workbench API"}


@router.get("/health/ready")
def readiness() -> dict[str, str]:
    """Check database connection and pgvector availability."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            vector_enabled = connection.execute(
                text(
                    "SELECT EXISTS "
                    "(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
            ).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is not available.",
        ) from exc

    if not vector_enabled:
        raise HTTPException(
            status_code=503,
            detail="The pgvector extension is not enabled yet.",
        )

    return {
        "status": "ready",
        "database": "connected",
        "pgvector": "enabled",
    }


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """Extract, chunk, embed, and save an uploaded PDF."""
    raw_filename = file.filename or "uploaded.pdf"
    filename = PurePosixPath(raw_filename.replace("\\", "/")).name

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file (.pdf).",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    pdf_bytes = await file.read(max_bytes + 1)
    await file.close()

    if len(pdf_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File is too large. Maximum allowed size is "
                f"{settings.max_upload_mb} MB."
            ),
        )

    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file does not look like a PDF.",
        )

    try:
        page_count, page_texts = extract_pdf_pages(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chunks = chunk_pdf_pages(page_texts)

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No text chunks could be created from this PDF.",
        )

    try:
        vectors = embed_texts([chunk_text for _, chunk_text, _ in chunks])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if len(vectors) != len(chunks):
        raise HTTPException(
            status_code=503,
            detail="Embedding count did not match chunk count.",
        )

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
        db.flush()

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
                for index, (
                    (page_number, chunk_text, token_count),
                    vector,
                ) in enumerate(zip(chunks, vectors, strict=True))
            ]
        )

        db.commit()
        db.refresh(document)

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the document and chunks.",
        ) from exc

    return {
        "status": "processed",
        "document_name": filename,
        "filename": filename,
        "page_count": page_count,
        "chunk_count": len(chunks),
        "embedding_dimension": EXPECTED_EMBEDDING_DIMENSION,
        "note": (
            "PDF text, page metadata, chunks, and embeddings were saved. "
            "The original PDF file is not stored on disk."
        ),
    }


@router.post("/ask")
def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """Retrieve evidence only from the PDF matching the supplied filename."""
    question = request.question.strip()
    document_name = request.document_name.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="The question cannot be empty.",
        )

    if not document_name:
        raise HTTPException(
            status_code=400,
            detail="The document name cannot be empty.",
        )

    # Confirm that a processed PDF with this exact filename exists.
    document = (
        db.query(Document)
        .filter(
            Document.filename == document_name,
            Document.status == "processed",
        )
        .order_by(Document.created_at.desc())
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="No processed document was found with that filename.",
        )

    try:
        chunks = retrieve_chunks(
            db,
            question,
            top_k=request.top_k,
            document_id=document.id,
        )

        result = generate_answer(question, chunks)

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

   
    return {
        "question": question,
        "document_name": document.filename,
        "answer": result["answer"],
        "sources": result["sources"],
        "retrieved_chunks": len(chunks)
    }

