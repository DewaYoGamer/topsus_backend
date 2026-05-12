"""FastAPI application entry-point."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .redis_client import ping as redis_ping
from .routers import auth as auth_router
from .routers import dosen as dosen_router
from .routers import mahasiswa as mahasiswa_router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("topsus3")

settings = get_settings()

app = FastAPI(title="Aplikasi Akademik", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Cache", "X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    from .seed import seed
    seed()
    if redis_ping():
        log.info("Redis connected at %s", settings.redis_url)
    else:
        log.warning(
            "Redis unreachable at %s - caching/blacklist/rate-limit will be skipped",
            settings.redis_url,
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "redis": redis_ping()}


app.include_router(auth_router.router)
app.include_router(dosen_router.router)
app.include_router(mahasiswa_router.router)
