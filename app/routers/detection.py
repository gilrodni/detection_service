"""Routes for the detection/protection API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import AuditLogEntry, DetectionRequest, DetectionResponse
from app.services import AuditLogRepository, DetectionService

router = APIRouter(tags=["detection"])


def get_detection_service(request: Request) -> DetectionService:
    return request.app.state.detection_service


async def get_audit_repository(
    session: AsyncSession = Depends(get_session),
) -> AuditLogRepository:
    return AuditLogRepository(session)


@router.post("/detect", response_model=DetectionResponse, summary="Classify prompt topics")
async def detect(
    payload: DetectionRequest,
    service: DetectionService = Depends(get_detection_service),
    audit_repo: AuditLogRepository = Depends(get_audit_repository),
) -> DetectionResponse:
    topics = await service.detect(payload)
    await audit_repo.record(route="detect", prompt=payload.prompt, topics=topics)
    return DetectionResponse(detected_topics=topics)


@router.post(
    "/protect",
    response_model=DetectionResponse,
    summary="Fail-fast detection that returns the first matching topic",
)
async def protect(
    payload: DetectionRequest,
    service: DetectionService = Depends(get_detection_service),
    audit_repo: AuditLogRepository = Depends(get_audit_repository),
) -> DetectionResponse:
    topics = await service.detect(payload, fast_mode=True)
    await audit_repo.record(route="protect", prompt=payload.prompt, topics=topics)
    return DetectionResponse(detected_topics=topics)


@router.get("/logs", response_model=list[AuditLogEntry], summary="Retrieve audit logs")
async def logs(
    audit_repo: AuditLogRepository = Depends(get_audit_repository),
) -> list[AuditLogEntry]:
    return await audit_repo.list()

