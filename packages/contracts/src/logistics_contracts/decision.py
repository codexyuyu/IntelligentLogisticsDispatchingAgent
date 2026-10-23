"""Agent decision-record DTOs (P19/P23 audit subset)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt

from logistics_contracts.planning import Record
from logistics_domain import decision as domain


class DecisionRecordDTO(Record):
    domain_type = domain.DecisionRecord
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    row_version: StrictInt
    schema_version: Literal["2.0.0"]
    created_by: UUID
    run_id: UUID | None
    tool_call_id: UUID | None
    decision_type: str
    payload_json: str
    rationale: str
    confidence: StrictFloat
    evidence_refs: tuple[UUID, ...]


class DecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    run_id: UUID | None = None
    tool_call_id: UUID | None = None
    decision_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, object] = Field(default_factory=dict)
    rationale: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    evidence_refs: tuple[UUID, ...] = ()


class DecisionView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    decision_id: UUID
    status: str
    decision_type: str
    confidence: float
    rationale: str
    run_id: UUID | None
    tool_call_id: UUID | None


class DecisionPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[DecisionView, ...]
