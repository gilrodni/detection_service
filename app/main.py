"""
FastAPI entry point for the detection service.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI
from openai import OpenAI

from app.config import get_settings
from app.routers.detection import router as detection_router
from app.services import AuditLogStore, build_detection_service

settings = get_settings()
logger = logging.getLogger("detection-service")
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize shared services on startup and clean them on shutdown."""
    client = OpenAI(
        api_key="aim-haka-7b7018e15bac5cfad7220f562ecc94a6fb116fe3626c4456",
        base_url="https://api.aim.security/fw/v1/proxy/openai",
    )
    app.state.detection_service = build_detection_service(
        client=client,
        topics=settings.detection_topics,
        model=settings.openai_model,
        request_timeout=settings.openai_request_timeout,
    )
    app.state.audit_log = AuditLogStore(max_entries=settings.audit_log_size)
    logger.info("Detection service initialized")
    yield
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
        reload=settings.debug,
        log_level=settings.log_level,
    )
