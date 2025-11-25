"""Detection services plus persistence helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Iterable, Sequence
from uuid import uuid4

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import audit_logs_table
from app.models import AuditLogEntry, DetectionRequest, TopicName

logger = logging.getLogger("detection-service")


class AuditLogRepository:
    """Persist audit logs using the Postgres backend."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self, *, route: str, prompt: str, topics: list[TopicName]
    ) -> AuditLogEntry:
        timestamp = datetime.now(timezone.utc)
        stmt = (
            insert(audit_logs_table)
            .values(
                id=uuid4(),
                timestamp=timestamp,
                route=route,
                prompt=prompt,
                detected_topics=topics,
            )
            .returning(audit_logs_table)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.mappings().one()
        return AuditLogEntry(
            timestamp=row["timestamp"],
            route=row["route"],
            prompt=row["prompt"],
            detected_topics=row["detected_topics"],
        )

    async def list(self, limit: int | None = None) -> list[AuditLogEntry]:
        stmt = select(audit_logs_table).order_by(audit_logs_table.c.timestamp.desc())
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        rows = result.mappings().all()
        return [
            AuditLogEntry(
                timestamp=row["timestamp"],
                route=row["route"],
                prompt=row["prompt"],
                detected_topics=row["detected_topics"],
            )
            for row in rows
        ]


class DetectionService:
    """LLM-powered topic detector with keyword fallback."""

    def __init__(
        self,
        client: AsyncOpenAI,
        topics: dict[str, str],
        model: str,
        request_timeout: float | None = None,
        keyword_hints: dict[str, Sequence[str]] | None = None,
    ) -> None:
        self._client = client
        self._topics = topics
        self._model = model
        self._request_timeout = request_timeout
        self._keyword_hints = keyword_hints or {
            "health": ("health", "medical", "doctor", "disease", "therapy"),
            "finance": ("bank", "invest", "loan", "budget", "portfolio"),
            "legal": ("law", "contract", "regulation", "court", "compliance"),
            "hr": ("hire", "payroll", "employee", "termination", "recruit"),
        }

    async def detect(
        self, request: DetectionRequest, fast_mode: bool = False
    ) -> list[TopicName]:
        enabled_topics = request.settings.enabled_topics()
        if not enabled_topics:
            return []

        llm_topics = await self._call_llm(
            prompt=request.prompt, enabled_topics=enabled_topics, fast_mode=fast_mode
        )
        if llm_topics:
            if fast_mode:
                return llm_topics[:1]
            return llm_topics

        # Fall back to keyword heuristics
        return self._keyword_match(request.prompt, enabled_topics, fast_mode=fast_mode)

    async def _call_llm(
        self,
        *,
        prompt: str,
        enabled_topics: Sequence[str],
        fast_mode: bool,
    ) -> list[TopicName]:
        """Invoke GPT and parse the JSON payload it returns."""
        mode_instruction = (
            "Return every matching topic from the active list."
            if not fast_mode
            else "Return **ONLY the first matching topic** from the active list and **STOP GENERATION IMMEDIATELY**. This is a time-critical, fail-fast operation."
        )
        system_prompt = (
            "You are a policy guardrail that classifies user prompts into compliance topics."
            " Only respond with valid JSON that matches the schema"
            ' {"detected_topics": ["topic-name", ...]}.'
        )
        active_topic_text = "\n".join(
            f"- {topic}: {self._topics[topic]}" for topic in enabled_topics
        )
        user_prompt = (
            f"Classify the following user prompt.\n"
            f"Active topics are:\n{active_topic_text}\n\n"
            f"Prompt:\n'''{prompt.strip()}'''\n\n"
            f"{mode_instruction}\n"
            f"Respond using lowercase topic keys exactly as provided above."
        )

        try:
            completion: ChatCompletion = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                timeout=self._request_timeout,
            )
        except Exception as exc:  # pragma: no cover - network failure path
            logger.warning("LLM classification failed: %s", exc)
            return []

        raw_content = (
            completion.choices[0].message.content if completion.choices else None
        )
        if not raw_content:
            return []

        try:
            payload = json.loads(raw_content)
            topics = payload.get("detected_topics", [])
            return [
                topic for topic in topics if topic in enabled_topics  # type: ignore[list-item]
            ]
        except (json.JSONDecodeError, AttributeError, TypeError):
            logger.info("LLM returned non-JSON payload: %s", raw_content)
            return []

    def _keyword_match(
        self, prompt: str, enabled_topics: Iterable[str], fast_mode: bool
    ) -> list[TopicName]:
        """Naive deterministic fallback detector."""
        lowered = prompt.lower()
        detected: list[TopicName] = []
        for topic in enabled_topics:
            hints = self._keyword_hints.get(topic, ())
            if any(keyword in lowered for keyword in hints):
                detected.append(topic)  # type: ignore[arg-type]
                if fast_mode:
                    break
        return detected


def build_detection_service(
    client: AsyncOpenAI,
    topics: dict[str, str],
    model: str,
    request_timeout: float | None,
    keyword_hints: dict[str, Sequence[str]] | None = None,
) -> DetectionService:
    return DetectionService(
        client=client,
        topics=topics,
        model=model,
        request_timeout=request_timeout,
        keyword_hints=keyword_hints,
    )
