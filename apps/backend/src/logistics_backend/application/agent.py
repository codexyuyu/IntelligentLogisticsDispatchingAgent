"""Durable agent-run audit around the provider chat adapter (P19/P23 subset)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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

    def record_dispatch(self, command, actor, trace_id, run, content, stopped_reason, latency_ms=0):
        """Persist a completed/failed analysis and all its calls in one scoped transaction."""
        import json
        from logistics_backend.persistence.tool_models import tool_calls
        from logistics_contracts.agents import DispatchResponse, DispatchToolTrace

        now = datetime.now(timezone.utc).replace(microsecond=0)
        identity = uuid4()
        status = (EntityState.COMPLETED if stopped_reason == "final_answer"
                  else EntityState.FAILED)
        # Reuse the v2 audit table without a migration; the run binding is explicitly
        # encoded in prompt JSON for backwards-compatible replay of this new endpoint.
        prompt = json.dumps({"kind": "dispatch", "run_id": str(command.run_id),
                             "message": command.message,
                             "stopped_reason": stopped_reason}, ensure_ascii=False)
        record = AgentRun(id=identity, status=status, created_at=now, updated_at=now,
            row_version=0, schema_version="2.0.0", created_by=actor.actor_id,
            session_id=command.session_id, prompt=prompt, reply=content,
            model=run.reply.model, provider_configured=self.configured,
            latency_ms=latency_ms, trace_id=trace_id)
        with self.uow_factory() as uow:
            uow.connection.execute(_insert_values(record, actor.scope_id))
            for index, turn in enumerate(run.turns):
                # Preserve tool execution order for replay, even with identical wall-clock seconds.
                call_time = now + timedelta(microseconds=index + 1)
                uow.connection.execute(tool_calls.insert().values(
                    id=uuid4(), scope_id=actor.scope_id,
                    status="succeeded" if turn.ok else "failed",
                    created_at=call_time, updated_at=call_time, created_by=actor.actor_id,
                    row_version=0, schema_version="2.0.0", run_id=identity,
                    tool_name=turn.name[:64], arguments=dict(turn.arguments or {}),
                    result=json.loads(json.dumps(dict(turn.content), default=str)),
                    error_code=turn.error_code, duration_ms=0, trace_id=trace_id))
        return DispatchResponse(agent_run_id=identity, run_id=command.run_id,
            session_id=command.session_id, reply=content, model=run.reply.model,
            provider_configured=self.configured, trace_id=trace_id,
            stopped_reason=stopped_reason,
            tools=tuple(DispatchToolTrace(name=turn.name, ok=turn.ok,
                arguments=dict(turn.arguments) if turn.arguments is not None else None,
                content=dict(turn.content), error_code=turn.error_code)
                for turn in run.turns))

    def record_dispatch_failure(self, command, actor, trace_id, latency_ms):
        """Keep a scoped failure audit when the external provider is unavailable."""
        import json

        now = datetime.now(timezone.utc).replace(microsecond=0)
        prompt = json.dumps({"kind": "dispatch", "run_id": str(command.run_id),
                             "message": command.message, "stopped_reason": "no_tool_evidence"},
                            ensure_ascii=False)
        record = AgentRun(id=uuid4(), status=EntityState.FAILED,
            created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
            created_by=actor.actor_id, session_id=command.session_id, prompt=prompt,
            reply="模型或工具运行失败，未形成可核验结论。", model=None,
            provider_configured=self.configured, latency_ms=latency_ms, trace_id=trace_id)
        with self.uow_factory() as uow:
            uow.connection.execute(_insert_values(record, actor.scope_id))

    def get_dispatch(self, agent_run_id, actor):
        """Restore completed analysis and tool evidence after a browser refresh."""
        import json
        from logistics_backend.persistence.agent_models import agent_runs
        from logistics_backend.persistence.tool_models import tool_calls
        from logistics_backend.errors import ServiceError
        from logistics_contracts.agents import DispatchResponse, DispatchToolTrace
        from logistics_domain.states import ErrorCode

        with self.uow_factory() as uow:
            row = uow.connection.execute(select(agent_runs).where(
                agent_runs.c.id == agent_run_id, agent_runs.c.scope_id == actor.scope_id)).mappings().first()
            if row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "agent run not found")
            calls = uow.connection.execute(select(tool_calls).where(
                tool_calls.c.run_id == agent_run_id,
                tool_calls.c.scope_id == actor.scope_id)
                .order_by(tool_calls.c.created_at, tool_calls.c.id)).mappings().all()
        try:
            prompt = json.loads(row["prompt"])
            if not isinstance(prompt, dict) or prompt.get("kind") != "dispatch":
                raise ValueError("not a dispatch run")
            run_id = UUID(prompt["run_id"])
        except (ValueError, TypeError, KeyError) as exc:
            raise ServiceError(ErrorCode.NOT_FOUND, "dispatch run not found") from exc
        # A failed analysis can also mean the turn cap was reached.
        stopped_reason = prompt.get("stopped_reason", "final_answer" if row["status"] == "completed"
                                     else "no_tool_evidence")
        return DispatchResponse(agent_run_id=row["id"], run_id=run_id,
            session_id=row["session_id"], reply=row["reply"] or "",
            model=row["model"] or "", provider_configured=row["provider_configured"],
            trace_id=row["trace_id"], stopped_reason=stopped_reason,
            tools=tuple(DispatchToolTrace(name=call["tool_name"],
                ok=call["status"] == "succeeded", arguments=call["arguments"],
                content=call["result"] or {}, error_code=call["error_code"])
                for call in calls))

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
