# Day 1 verification checklist

- [ ] `uv --version` works.
- [ ] `node --version`, `npm --version`, `docker compose version`, `ollama --version` work.
- [ ] `docker compose up -d db` starts and `docker compose ps` shows healthy.
- [ ] `ollama pull nomic-embed-text` succeeds.
- [ ] `uv run pytest -v` passes in `backend/`.
- [ ] `uv run ruff check .` passes in `backend/`.
- [ ] `GET /health` returns `{"status":"ok", ...}`.
- [ ] `GET /health/ready` confirms database and pgvector.
- [ ] Frontend loads in browser and backend is reachable.
- [ ] A selectable-text PDF uploads and returns a positive chunk count.
- [ ] SQL query shows rows in `documents` and `chunks`.
- [ ] Each chunk row includes `page_number`, `token_count`, and a 768-dimension embedding.
- [ ] No `.env`, secret, or personal PDF is committed to Git.
