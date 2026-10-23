"""Exception projection service (P14 subset)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.event_models import exception_events, events
from logistics_contracts.common import EntityRefDTO
from logistics_contracts.events import ExceptionCreate, ExceptionEventView
from logistics_domain.events import ExceptionEvent, ExceptionSeverity
from logistics_domain.states import EntityState, ErrorCode


class ExceptionService:
    def __init__(self, uow_factory, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id

    def record(self, command: ExceptionCreate, actor) -> ExceptionEventView:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        refs = tuple(reference.to_domain() for reference in command.affected_entity_refs)
        with self.uow_factory() as uow:
            event_row = uow.connection.execute(select(events.c.id).where(
                events.c.id == command.event_id,
                events.c.scope_id == actor.scope_id)).first()
            if event_row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "source event not found")
            exception = ExceptionEvent(id=uuid4(), status=EntityState.DETECTED,
                created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
                created_by=actor.actor_id, event_id=command.event_id,
                severity=ExceptionSeverity(command.severity),
                affected_entity_refs=refs,
                impact_report_ref=command.impact_report_ref,
                decision_record_id=command.decision_record_id)
            uow.connection.execute(exception_events.insert().values(
                id=exception.id, scope_id=actor.scope_id, status=exception.status.value,
                created_at=now, updated_at=now, created_by=actor.actor_id, row_version=0,
                schema_version="2.0.0", event_id=exception.event_id,
                severity=exception.severity.value,
                affected_entity_refs=[reference.model_dump(mode="json")
                                      for reference in command.affected_entity_refs],
                impact_report_ref=exception.impact_report_ref,
                decision_record_id=exception.decision_record_id))
            return self._view(exception)

    def list(self, actor, limit: int = 50) -> tuple[ExceptionEventView, ...]:
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(exception_events).where(
                exception_events.c.scope_id == actor.scope_id)
                .order_by(exception_events.c.created_at.desc()).limit(min(max(limit, 1), 200))
            ).mappings().all()
        return tuple(self._row_view(row) for row in rows)

    @staticmethod
    def _view(exception: ExceptionEvent) -> ExceptionEventView:
        return ExceptionEventView(exception_id=exception.id, event_id=exception.event_id,
            severity=exception.severity, status=exception.status,
            affected_entity_refs=tuple(EntityRefDTO.from_domain(reference)
                                       for reference in exception.affected_entity_refs),
            impact_report_ref=exception.impact_report_ref,
            decision_record_id=exception.decision_record_id)

    @staticmethod
    def _row_view(row) -> ExceptionEventView:
        return ExceptionEventView(exception_id=row["id"], event_id=row["event_id"],
            severity=row["severity"], status=row["status"],
            affected_entity_refs=tuple(EntityRefDTO.model_validate(item)
                                       for item in row["affected_entity_refs"]),
            impact_report_ref=row["impact_report_ref"],
            decision_record_id=row["decision_record_id"])
