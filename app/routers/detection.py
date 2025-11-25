"""Routes for the detection/protection API."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.models import AuditLogEntry, DetectionRequest, DetectionResponse
from app.services import AuditLogStore, DetectionService

router = APIRouter(tags=["detection"])


def get_detection_service(request: Request) -> DetectionService:
    return request.app.state.detection_service


def get_audit_log_store(request: Request) -> AuditLogStore:
    return request.app.state.audit_log


@router.post("/detect", response_model=DetectionResponse, summary="Classify prompt topics")
async def detect(
    payload: DetectionRequest,
    service: DetectionService = Depends(get_detection_service),
    audit_log: AuditLogStore = Depends(get_audit_log_store),
) -> DetectionResponse:
    topics = await service.detect(payload)
    await audit_log.append(
        AuditLogEntry(
            timestamp=datetime.now(timezone.utc),
            route="detect",
            prompt=payload.prompt,
            detected_topics=topics,
        )
    )
    return DetectionResponse(detected_topics=topics)


@router.post(
    "/protect",
    response_model=DetectionResponse,
    summary="Fail-fast detection that returns the first matching topic",
)
async def protect(
    payload: DetectionRequest,
    service: DetectionService = Depends(get_detection_service),
    audit_log: AuditLogStore = Depends(get_audit_log_store),
) -> DetectionResponse:
    topics = await service.detect(payload, fast_mode=True)
    await audit_log.append(
        AuditLogEntry(
            timestamp=datetime.now(timezone.utc),
            route="protect",
            prompt=payload.prompt,
            detected_topics=topics,
        )
    )
    return DetectionResponse(detected_topics=topics)


@router.get("/logs", response_model=list[AuditLogEntry], summary="Retrieve audit logs")
async def logs(
    audit_log: AuditLogStore = Depends(get_audit_log_store),
) -> list[AuditLogEntry]:
    return await audit_log.list()

