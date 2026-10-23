"""Validation request bodies (P10 subset)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from logistics_contracts.planning import RouteStopDTO, TransportPlanDTO
from logistics_contracts.transport import TransportProblemDTO


class TransportValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    problem: TransportProblemDTO
    plan: TransportPlanDTO
    stops: tuple[RouteStopDTO, ...]
