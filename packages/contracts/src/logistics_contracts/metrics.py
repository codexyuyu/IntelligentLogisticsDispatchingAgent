"""Metric boundary projections and evaluation request bodies (P32)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt

from logistics_contracts.planning import Record, TransportPlanDTO
from logistics_contracts.simulation import SimulationResultDTO
from logistics_domain import metrics as domain


class MetricValueDTO(Record):
    domain_type = domain.MetricValue
    code: str
    definition_version: str
    source: domain.MetricSource
    unit: str
    value: float | None
    numerator: float | None
    denominator: float | None
    reason: domain.MissingReason | None
    sample_count: StrictInt


class TransportMetricsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    plan: TransportPlanDTO
    orders_total: StrictInt
    vehicle_count: StrictInt
    persist: bool = False


class SimulationMetricsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    result: SimulationResultDTO
    orders_total: StrictInt
    persist: bool = False


class MetricPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    metrics: tuple[MetricValueDTO, ...]
    recorded: StrictInt = 0


class MetricRecordView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: UUID
    code: str
    definition_version: str
    source: domain.MetricSource
    unit: str
    value: float | None
    numerator: float | None
    denominator: float | None
    reason: domain.MissingReason | None
    sample_count: StrictInt
    created_at: datetime


class MetricHistoryPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[MetricRecordView, ...]
