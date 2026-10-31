"""Human-reviewed AI evidence analysis; no execute or approval authority."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class DecisionAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(default='', max_length=500)

class DecisionAnalysisView(BaseModel):
    model_config = ConfigDict(extra='forbid')
    analysis_id: UUID
    target_type: Literal['dispatch_task', 'incident']
    target_id: UUID
    run_id: UUID
    question: str
    reply: str
    model: str | None = None
    status: Literal['model_success', 'model_unavailable', 'model_failed']
    error_code: str | None = None
    tool_trace: list[dict]
    evidence: dict
    recommendation: str | None = None
    created_at: str
