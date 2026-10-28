"""Metric calculation and optional persistence (P32)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from logistics_backend.persistence.metric_models import metric_records
from logistics_contracts.mapping import metric_dto
from logistics_contracts.metrics import (
    MetricHistoryPage,
    MetricPage,
    MetricRecordView,
    SimulationMetricsRequest,
    TransportMetricsRequest,
)
from logistics_domain.errors import InvalidInputError
from logistics_domain.metrics import MetricRecord, MetricValue
from logistics_domain.states import EntityState
from logistics_evaluation.metrics import simulation_metrics, transport_plan_metrics


class MetricsService:
    def __init__(self, uow_factory, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id

    def transport(self, command: TransportMetricsRequest, actor) -> MetricPage:
        try:
            values = transport_plan_metrics(command.plan.to_domain(), command.orders_total,
                                            command.vehicle_count)
        except ValueError as exc:
            raise InvalidInputError(str(exc)) from exc
        return self._page(values, actor, command.persist)

    def simulation(self, command: SimulationMetricsRequest, actor) -> MetricPage:
        try:
            values = simulation_metrics(command.result.to_domain(), command.orders_total)
        except ValueError as exc:
            raise InvalidInputError(str(exc)) from exc
        return self._page(values, actor, command.persist)

    def _page(self, values: tuple[MetricValue, ...], actor, persist: bool) -> MetricPage:
        if persist:
            self._store(values, actor)
        return MetricPage(metrics=tuple(metric_dto(value) for value in values),
                          recorded=len(values) if persist else 0)

    def _store(self, values: tuple[MetricValue, ...], actor) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        with self.uow_factory() as uow:
            for value in values:
                record = MetricRecord(id=uuid4(), status=EntityState.ACTIVE,
                    created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
                    created_by=actor.actor_id, code=value.code,
                    definition_version=value.definition_version, source=value.source,
                    unit=value.unit, value=value.value, numerator=value.numerator,
                    denominator=value.denominator, reason=value.reason,
                    sample_count=value.sample_count)
                uow.connection.execute(metric_records.insert().values(
                    id=record.id, scope_id=actor.scope_id, status=record.status.value,
                    created_at=now, updated_at=now, created_by=actor.actor_id,
                    row_version=0, schema_version="2.0.0", code=record.code,
                    definition_version=record.definition_version,
                    source=record.source.value, unit=record.unit, value=record.value,
                    numerator=record.numerator, denominator=record.denominator,
                    reason=record.reason.value if record.reason else None,
                    sample_count=record.sample_count))

    def history(self, actor, code: str | None = None, limit: int = 50) -> MetricHistoryPage:
        query = select(metric_records).where(metric_records.c.scope_id == actor.scope_id)
        if code:
            query = query.where(metric_records.c.code == code)
        with self.uow_factory() as uow:
            rows = uow.connection.execute(query.order_by(
                metric_records.c.created_at.desc()).limit(min(max(limit, 1), 200))).mappings().all()
        return MetricHistoryPage(items=tuple(MetricRecordView(record_id=row["id"],
            code=row["code"], definition_version=row["definition_version"],
            source=row["source"], unit=row["unit"], value=row["value"],
            numerator=row["numerator"], denominator=row["denominator"],
            reason=row["reason"], sample_count=row["sample_count"],
            created_at=row["created_at"]) for row in rows))
