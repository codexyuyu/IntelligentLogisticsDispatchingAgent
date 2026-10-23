"""Durable agent-run audit around the provider chat adapter (P19/P23 subset)."""

from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from uuid import UUID, uuid4

from sqlalchemy import select

from logistics_agents.service import AgentChatService
from logistics_contracts.agents import AgentChatResponse, AgentRunPage, AgentRunView
from logistics_domain.agent import AgentRun
from logistics_domain.states import EntityState


class AgentRunService:
    def __init__(self, uow_factory, chat: AgentChatService, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.chat = chat
        self.workspace_id = workspace_id

    @property
    def configured(self) -> bool:
        return self.chat.configured

    def chat_once(self, command, actor, trace_id: UUID) -> AgentChatResponse:
        started = monotonic()
        try:
            reply = self.chat.reply(command.message)
        except Exception as exc:
            self._record(actor, command, trace_id, None, None, False,
                         int((monotonic() - started) * 1000), EntityState.FAILED)
            raise exc
        self._record(actor, command, trace_id, reply.content, reply.model,
                     self.configured, int((monotonic() - started) * 1000),
                     EntityState.COMPLETED)
        return AgentChatResponse(reply=reply.content, model=reply.model,
            provider_configured=self.configured, trace_id=trace_id)

    def _record(self, actor, command, trace_id, reply, model, configured, latency_ms, status):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        run = AgentRun(id=uuid4(), status=status, created_at=now, updated_at=now,
            row_version=0, schema_version="2.0.0", created_by=actor.actor_id,
            session_id=command.session_id, prompt=command.message, reply=reply,
            model=model, provider_configured=configured, latency_ms=latency_ms,
            trace_id=trace_id)
        with self.uow_factory() as uow:
            uow.connection.execute(_insert_values(run, actor.scope_id))

    def list(self, actor, limit: int = 50) -> AgentRunPage:
        from logistics_backend.persistence.agent_models import agent_runs

        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(agent_runs).where(
                agent_runs.c.scope_id == actor.scope_id)
                .order_by(agent_runs.c.created_at.desc()).limit(min(max(limit, 1), 200))
            ).mappings().all()
        return AgentRunPage(items=tuple(AgentRunView(run_id=row["id"], status=row["status"],
            session_id=row["session_id"], model=row["model"],
            provider_configured=row["provider_configured"], latency_ms=row["latency_ms"],
            trace_id=row["trace_id"]) for row in rows))


def _insert_values(run: AgentRun, scope_id: UUID):
    from logistics_backend.persistence.agent_models import agent_runs

    return agent_runs.insert().values(
        id=run.id, scope_id=scope_id, status=run.status.value,
        created_at=run.created_at, updated_at=run.updated_at,
        created_by=run.created_by, row_version=0, schema_version="2.0.0",
        session_id=run.session_id, prompt=run.prompt, reply=run.reply,
        model=run.model, provider_configured=run.provider_configured,
        latency_ms=run.latency_ms, trace_id=run.trace_id)
