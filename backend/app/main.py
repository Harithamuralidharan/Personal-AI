"""FastAPI entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # On first API startup, enable pgvector and create the four application tables.
    init_db()
    yield


app = FastAPI(
    title="Personal AI Workbench",
    version="0.1.0",
    description="A local-first GenAI work assistant; Day 1 focuses on PDF ingestion.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        dict.fromkeys(
            [settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"]
        )
    ),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router)
