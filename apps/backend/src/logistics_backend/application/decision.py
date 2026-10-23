"""Decision-record service (P19/P23 audit subset)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.agent_models import agent_runs
from logistics_backend.persistence.decision_models import decision_records
from logistics_backend.persistence.tool_models import tool_calls
from logistics_contracts.decision import DecisionCreate, DecisionPage, DecisionView
from logistics_domain.decision import DecisionRecord
from logistics_domain.states import EntityState, ErrorCode


class DecisionService:
    def __init__(self, uow_factory, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id

    def record(self, command: DecisionCreate, actor) -> DecisionView:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        with self.uow_factory() as uow:
            if command.run_id is not None:
                exists = uow.connection.execute(select(agent_runs.c.id).where(
                    agent_runs.c.id == command.run_id,
                    agent_runs.c.scope_id == actor.scope_id)).first()
                if exists is None:
                    raise ServiceError(ErrorCode.NOT_FOUND, "agent run not found")
            if command.tool_call_id is not None:
                exists = uow.connection.execute(select(tool_calls.c.id).where(
                    tool_calls.c.id == command.tool_call_id,
                    tool_calls.c.scope_id == actor.scope_id)).first()
                if exists is None:
                    raise ServiceError(ErrorCode.NOT_FOUND, "tool call not found")
            decision = DecisionRecord(id=uuid4(), status=EntityState.PROPOSED,
                created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
                created_by=actor.actor_id, run_id=command.run_id,
                tool_call_id=command.tool_call_id, decision_type=command.decision_type,
                payload_json=json.dumps(command.payload, default=str, sort_keys=True),
                rationale=command.rationale, confidence=float(command.confidence),
                evidence_refs=command.evidence_refs)
            uow.connection.execute(decision_records.insert().values(
                id=decision.id, scope_id=actor.scope_id, status=decision.status.value,
                created_at=now, updated_at=now, created_by=actor.actor_id, row_version=0,
                schema_version="2.0.0", run_id=decision.run_id,
                tool_call_id=decision.tool_call_id, decision_type=decision.decision_type,
                payload=command.payload, rationale=decision.rationale,
                confidence=decision.confidence,
                evidence_refs=[str(value) for value in decision.evidence_refs]))
            return DecisionView(decision_id=decision.id, status=decision.status.value,
                decision_type=decision.decision_type, confidence=decision.confidence,
                rationale=decision.rationale, run_id=decision.run_id,
                tool_call_id=decision.tool_call_id)

    def transition(self, decision_id: UUID, target: EntityState, actor) -> DecisionView:
        if target not in (EntityState.ACCEPTED, EntityState.REJECTED):
            raise ServiceError(ErrorCode.INVALID_INPUT, "unsupported decision transition")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(decision_records).where(
                decision_records.c.id == decision_id,
                decision_records.c.scope_id == actor.scope_id).with_for_update()).mappings().first()
            if row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "decision not found")
            from logistics_domain.states import allowed_next_states

            if target not in allowed_next_states(EntityState(row["status"])):
                raise ServiceError(ErrorCode.INVALID_TRANSITION,
                    "decision cannot move to the requested status")
            uow.connection.execute(decision_records.update().where(
                decision_records.c.id == decision_id).values(status=target.value,
                updated_at=now, row_version=row["row_version"] + 1))
        return DecisionView(decision_id=row["id"], status=target.value,
            decision_type=row["decision_type"], confidence=row["confidence"],
            rationale=row["rationale"], run_id=row["run_id"],
            tool_call_id=row["tool_call_id"])

    def list(self, actor, limit: int = 50) -> DecisionPage:
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(decision_records).where(
                decision_records.c.scope_id == actor.scope_id)
                .order_by(decision_records.c.created_at.desc()).limit(min(max(limit, 1), 200))
            ).mappings().all()
        return DecisionPage(items=tuple(DecisionView(decision_id=row["id"],
            status=row["status"], decision_type=row["decision_type"],
            confidence=row["confidence"], rationale=row["rationale"],
            run_id=row["run_id"], tool_call_id=row["tool_call_id"]) for row in rows))
