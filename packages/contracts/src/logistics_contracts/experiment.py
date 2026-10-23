"""Paired experiment comparison DTOs (P33-01 subset)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt

from logistics_contracts.planning import Record
from logistics_contracts.simulation import SimulationResultDTO
from logistics_domain import experiment as domain
from logistics_domain.metrics import MissingReason


class MetricDeltaDTO(Record):
    domain_type = domain.MetricDelta
    code: str
    base: float | None
    candidate: float | None
    delta: float | None
    relative_change: float | None
    reason: MissingReason | None


class ExperimentComparisonDTO(Record):
    domain_type = domain.ExperimentComparison
    base_label: str
    candidate_label: str
    deltas: tuple[MetricDeltaDTO, ...]


class ExperimentCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    base_label: str = "base"
    candidate_label: str = "candidate"
    base: SimulationResultDTO
    candidate: SimulationResultDTO
    orders_total: StrictInt
