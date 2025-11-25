"""
FastAPI entry point for the detection service.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI
from openai import AsyncOpenAI

from app.config import get_settings
from app.database import init_db
from app.routers.detection import router as detection_router
from app.services import build_detection_service

settings = get_settings()
logger = logging.getLogger("detection-service")
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize shared services on startup and clean them on shutdown."""
    await init_db()
    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    app.state.detection_service = build_detection_service(
        client=client,
        topics=settings.detection_topics,
        model=settings.openai_model,
        request_timeout=settings.openai_request_timeout,
    )
    app.state.openai_client = client
    logger.info("Detection service initialized")
    yield
    await app.state.openai_client.close()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    description="GenAI policy detection service.",
    lifespan=lifespan,
)

app.include_router(detection_router)


@app.get("/", tags=["meta"])
async def index() -> Dict[str, Any]:
    return {
        "message": "GenAI detection service",
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.get("/health", tags=["meta"])
async def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": settings.version,
    }


if __name__ == "__main__":
    import uvicorn

    port = 8000
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.debug
    )
