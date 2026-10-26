# Personal AI Workbench — Day 1 Starter

A zero-cost local-development starter for PDF ingestion using FastAPI, `uv`, PostgreSQL + pgvector, Ollama, React, and Vite.

## Prerequisites

- Windows 10/11 and VS Code
- `uv`
- Node.js (a version supported by current Vite; use a current LTS release)
- Docker Desktop running
- Ollama running locally
- Internet only to install/download packages, Docker image, and the embedding model. Runtime embeddings are local.

## 1. Environment files

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env` or real documents.

## 2. Backend setup

```powershell
cd backend
uv python install 3.12
uv python pin 3.12
uv sync
cd ..
```

The backend reads `../.env` when commands are run from the `backend/` directory.

## 3. Start database

From the repository root:

```powershell
docker compose up -d db
docker compose ps
```

## 4. Start local embeddings

Install Ollama from https://ollama.com/download/windows, then run:

```powershell
ollama pull nomic-embed-text
```

## 5. Start backend

In Terminal 1:

```powershell
cd backend
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/health, http://127.0.0.1:8000/health/ready and http://127.0.0.1:8000/docs.

## 6. Start frontend

If you scaffolded the frontend using Vite, install packages first. In Terminal 2, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, normally http://localhost:5173.

## 7. Test ingestion

Choose a selectable-text PDF no larger than 15 MB and click **Upload and process**. The original PDF binary is not stored; metadata, extracted chunks, page numbers and embeddings are stored in PostgreSQL.

Run the database queries from the repository root:

```powershell
docker compose exec db psql -U workbench_user -d workbench_db -c "SELECT count(*) AS chunks FROM chunks;"
```

```powershell
docker compose exec db psql -U workbench_user -d workbench_db -c "SELECT d.filename, count(c.id) AS chunks FROM documents d LEFT JOIN chunks c ON c.document_id = d.id GROUP BY d.id, d.filename;"
```

```powershell
docker compose exec db psql -U workbench_user -d workbench_db -c "SELECT page_number, chunk_index, token_count FROM chunks ORDER BY document_id, chunk_index;"
```

## 8. Run backend checks

```powershell
cd backend
uv run pytest -v
uv run ruff check .
```

## Notes / current limitations

- Day 1 supports PDFs with selectable text; image-only scanned PDFs need OCR later.
- Chunks are measured with the local `cl100k_base` tokenizer at 500 tokens with 50-token overlap; this is a consistent chunking convention and is not Nomic's internal tokenizer.
- The first model is `nomic-embed-text`, expected to return 768 dimensions. If changing the embedding model/dimension, update the SQLAlchemy `Vector(768)` column and rebuild the development database schema appropriately.
- The API creates the `vector` extension and tables at first startup. This is a local prototype convenience; production deployments should use reviewed migrations (Alembic).
- The sample database password is for local development only; change it before exposing any service beyond localhost.
