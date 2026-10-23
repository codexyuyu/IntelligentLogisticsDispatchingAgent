"""Agent chat boundary DTOs (P17/P18 subset)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt


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


class AgentRunView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    run_id: UUID
    status: str
    session_id: UUID | None
    model: str | None
    provider_configured: bool
    latency_ms: StrictInt
    trace_id: UUID


class AgentRunPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[AgentRunView, ...]


class AgentToolSpecView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    name: str
    description: str
    allowed_roles: tuple[str, ...]


class AgentToolPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[AgentToolSpecView, ...]


class AgentToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    arguments: dict[str, object] = Field(default_factory=dict)


class AgentToolResultView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    name: str
    ok: bool
    content: dict[str, object]
    error_code: str | None
    call_id: UUID | None = None


class AgentToolCallView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    call_id: UUID
    tool_name: str
    status: str
    error_code: str | None
    duration_ms: StrictInt
    trace_id: UUID


class AgentToolCallPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[AgentToolCallView, ...]
