"""Schedule creation/listing service (P16 subset)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from logistics_backend.persistence.planning_models import schedules
from logistics_contracts.planning import ScheduleDTO
from logistics_contracts.schedules import ScheduleCreate, SchedulePage, ScheduleView
from logistics_domain.planning import Schedule
from logistics_domain.states import EntityState


class ScheduleService:
    def __init__(self, uow_factory, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id

    def create(self, command: ScheduleCreate, actor) -> ScheduleView:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        scope = command.scope.to_domain()
        schedule = Schedule(id=uuid4(), status=EntityState.DRAFT, created_at=now,
            updated_at=now, row_version=0, schema_version="2.0.0",
            created_by=actor.actor_id, name=command.name, scope=scope,
            active_version_id=None, epoch_utc=scope.epoch_utc,
            horizon_s=scope.horizon_s)
        payload = ScheduleDTO(id=schedule.id, status=schedule.status,
            created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
            created_by=actor.actor_id, name=schedule.name, scope=command.scope,
            active_version_id=None, epoch_utc=scope.epoch_utc,
            horizon_s=scope.horizon_s).model_dump(mode="json")
        with self.uow_factory() as uow:
            uow.connection.execute(schedules.insert().values(
                id=schedule.id, scope_id=actor.scope_id, status=schedule.status.value,
                created_at=now, updated_at=now, created_by=actor.actor_id, row_version=0,
                schema_version="2.0.0", payload=payload, name=schedule.name,
                active_version_id=None, epoch_utc=scope.epoch_utc,
                horizon_s=scope.horizon_s))
        return self._view(schedule.id, schedule.name, schedule.status.value, scope.epoch_utc,
                          scope.horizon_s, None)

    def list(self, actor, limit: int = 50) -> SchedulePage:
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(schedules).where(
                schedules.c.scope_id == actor.scope_id)
                .order_by(schedules.c.created_at.desc()).limit(min(max(limit, 1), 200))
            ).mappings().all()
        return SchedulePage(items=tuple(self._view(row["id"], row["name"], row["status"],
            row["epoch_utc"], row["horizon_s"], row["active_version_id"]) for row in rows))

    @staticmethod
    def _view(schedule_id, name, status, epoch_utc, horizon_s, active_version_id):
        return ScheduleView(schedule_id=schedule_id, name=name, status=status,
            epoch_utc=epoch_utc, horizon_s=horizon_s, active_version_id=active_version_id)
