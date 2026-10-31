"""Bounded natural-language dispatch intent; never a direct vehicle-control command."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class DispatchTaskCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['2.0.0'] = '2.0.0'
    run_id: UUID
    message: str = Field(min_length=3, max_length=1500)

class DispatchTaskRevision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_row_version: int = Field(ge=0)

class DispatchTaskView(BaseModel):
    model_config = ConfigDict(extra='forbid')
    task_id: UUID
    source_run_id: UUID
    candidate_run_id: UUID | None = None
    status: Literal['draft','solving','ready','approved','rejected','failed']
    row_version: int
    instruction: str
    intent: dict
    evidence: dict
    parser: str
    incident_id: UUID | None = None
