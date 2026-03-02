from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import interests, leads, sources

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="One-A-Day API",
        description="Surfaces one interesting contact lead per day.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(leads.router, prefix="/api/v1")
    app.include_router(interests.router, prefix="/api/v1")
    app.include_router(sources.router, prefix="/api/v1")

    @app.get("/health")
    def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok"}

    logger.info("app_created")
    return app


app = create_app()
