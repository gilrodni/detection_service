"""Pydantic models shared between API endpoints and the detection service."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TopicName = Literal["health", "finance", "legal", "hr"]


class DetectionSettings(BaseModel):
    """Settings describing which detectors are active for the call."""

    health: bool = Field(True, description="Enable healthcare topic detection")
    finance: bool = Field(True, description="Enable finance topic detection")
    legal: bool = Field(True, description="Enable legal topic detection")
    hr: bool = Field(True, description="Enable HR topic detection")

    def enabled_topics(self) -> list[TopicName]:
        enabled: list[TopicName] = []
        if self.health:
            enabled.append("health")
        if self.finance:
            enabled.append("finance")
        if self.legal:
            enabled.append("legal")
        if self.hr:
            enabled.append("hr")
        return enabled


class DetectionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt to classify")
    settings: DetectionSettings = Field(
        default_factory=DetectionSettings,
        description="Feature flag per detector; disabled topics are ignored",
    )


class DetectionResponse(BaseModel):
    detected_topics: list[TopicName] = Field(
        default_factory=list, description="Topics detected in the prompt"
    )


class AuditLogEntry(BaseModel):
    timestamp: datetime
    route: Literal["detect", "protect"]
    prompt: str
    detected_topics: list[TopicName]

