"""Experiment comparison and persistence service (P33 subset)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.experiment_models import experiment_records
from logistics_contracts.experiment import (
    ExperimentCompareRequest,
    ExperimentComparisonDTO,
    ExperimentPage,
    ExperimentView,
)
from logistics_contracts.mapping import experiment_comparison_dto
from logistics_domain.experiment import ExperimentRecord
from logistics_domain.states import EntityState, ErrorCode
from logistics_evaluation.metrics import compare_metrics, simulation_metrics


class ExperimentService:
    def __init__(self, uow_factory, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id

    def compare(self, command: ExperimentCompareRequest, actor) -> ExperimentComparisonDTO:
        base = simulation_metrics(command.base.to_domain(), command.orders_total)
        candidate = simulation_metrics(command.candidate.to_domain(), command.orders_total)
        comparison = experiment_comparison_dto(compare_metrics(command.base_label,
            command.candidate_label, base, candidate))
        if not command.persist:
            return comparison
        now = datetime.now(timezone.utc).replace(microsecond=0)
        comparison_json = comparison.model_dump_json()
        record = ExperimentRecord(id=uuid4(), status=EntityState.COMPLETED,
            created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
            created_by=actor.actor_id, base_label=command.base_label,
            candidate_label=command.candidate_label, orders_total=command.orders_total,
            metric_version="1.0.0",
            base_result_json=command.base.model_dump_json(),
            candidate_result_json=command.candidate.model_dump_json(),
            comparison_json=comparison_json)
        with self.uow_factory() as uow:
            uow.connection.execute(experiment_records.insert().values(
                id=record.id, scope_id=actor.scope_id, status=record.status.value,
                created_at=now, updated_at=now, created_by=actor.actor_id, row_version=0,
                schema_version="2.0.0", base_label=record.base_label,
                candidate_label=record.candidate_label, orders_total=record.orders_total,
                metric_version=record.metric_version,
                base_result=json.loads(record.base_result_json),
                candidate_result=json.loads(record.candidate_result_json),
                comparison=json.loads(record.comparison_json)))
        return comparison

    def list(self, actor, limit: int = 50) -> ExperimentPage:
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(experiment_records).where(
                experiment_records.c.scope_id == actor.scope_id)
                .order_by(experiment_records.c.created_at.desc()).limit(min(max(limit, 1), 200))
            ).mappings().all()
        return ExperimentPage(items=tuple(self._view(row) for row in rows))

    def get(self, experiment_id: UUID, actor) -> ExperimentView:
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(experiment_records).where(
                experiment_records.c.id == experiment_id,
                experiment_records.c.scope_id == actor.scope_id)).mappings().first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, "experiment not found")
        return self._view(row)

    @staticmethod
    def _view(row) -> ExperimentView:
        comparison = ExperimentComparisonDTO.model_validate(row["comparison"])
        return ExperimentView(experiment_id=row["id"], status=row["status"],
            base_label=row["base_label"], candidate_label=row["candidate_label"],
            orders_total=row["orders_total"], metric_version=row["metric_version"],
            comparison=comparison)
