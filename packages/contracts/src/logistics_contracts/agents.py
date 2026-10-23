"""Agent chat boundary DTOs (P17/P18 subset)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    session_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class AgentChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    reply: str
    model: str
    provider_configured: bool
    trace_id: UUID
