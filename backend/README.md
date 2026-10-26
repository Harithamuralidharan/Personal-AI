# Backend

Run commands from this directory. Python dependencies are managed with `uv`.

```powershell
uv sync
uv run uvicorn app.main:app --reload
```

Configuration is read from the root `.env` file (`../.env`) when the working directory is `backend/`.
