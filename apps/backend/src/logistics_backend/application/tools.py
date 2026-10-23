"""Backend binding of the agent tool registry and its audit trail (P17/P19)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Mapping
from uuid import UUID, uuid4

from sqlalchemy import select

from logistics_agents.tools import ToolRegistry, ToolResult, ToolSpec
from logistics_contracts.agents import AgentToolCallPage, AgentToolCallView
from logistics_domain.runtime import ActorContext
from logistics_domain.states import EntityState
from logistics_domain.tool import ToolCall


class ToolService:
    def __init__(self, jobs, agents, uow_factory=None, workspace_id: UUID | None = None):
        self.jobs = jobs
        self.agents = agents
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id
        self.registry = ToolRegistry()
        self.registry.register(ToolSpec(name="job_status",
            description="Read a job's status and result reference by job_id",
            allowed_roles=("operator", "viewer")), self._job_status)
        self.registry.register(ToolSpec(name="agent_runs",
            description="List recent agent chat runs for the current scope",
            allowed_roles=("operator", "viewer")), self._agent_runs)

    def specs(self):
        return self.registry.specs()

    def invoke(self, name: str, actor: ActorContext, arguments: Mapping[str, Any],
               trace_id: UUID | None = None) -> ToolResult:
        started = monotonic()
        result = self.registry.invoke(name, actor, arguments)
        duration_ms = int((monotonic() - started) * 1000)
        if self.uow_factory is not None and trace_id is not None:
            self._record(actor, name, arguments, result, duration_ms, trace_id)
        return result

    def calls(self, actor: ActorContext, limit: int = 50) -> AgentToolCallPage:
        from logistics_backend.persistence.tool_models import tool_calls

        if self.uow_factory is None:
            return AgentToolCallPage(items=())
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(tool_calls).where(
                tool_calls.c.scope_id == actor.scope_id)
                .order_by(tool_calls.c.created_at.desc()).limit(min(max(limit, 1), 200))
            ).mappings().all()
        return AgentToolCallPage(items=tuple(AgentToolCallView(call_id=row["id"],
            tool_name=row["tool_name"], status=row["status"],
            error_code=row["error_code"], duration_ms=row["duration_ms"],
            trace_id=row["trace_id"]) for row in rows))

    def _record(self, actor, name, arguments, result: ToolResult, duration_ms, trace_id):
        from logistics_backend.persistence.tool_models import tool_calls

        now = datetime.now(timezone.utc).replace(microsecond=0)
        status = (EntityState.SUCCEEDED if result.ok else
                  EntityState.DENIED if result.error_code == "tool_forbidden" else
                  EntityState.FAILED)
        call = ToolCall(id=uuid4(), status=status, created_at=now, updated_at=now,
            row_version=0, schema_version="2.0.0", created_by=actor.actor_id,
            run_id=None, tool_name=name,
            arguments_json=json.dumps(arguments, default=str, sort_keys=True),
            result_json=json.dumps(result.content, default=str, sort_keys=True),
            error_code=result.error_code, duration_ms=duration_ms, trace_id=trace_id)
        with self.uow_factory() as uow:
            uow.connection.execute(tool_calls.insert().values(
                id=call.id, scope_id=actor.scope_id, status=call.status.value,
                created_at=now, updated_at=now, created_by=actor.actor_id, row_version=0,
                schema_version="2.0.0", run_id=None, tool_name=call.tool_name,
                arguments=json.loads(call.arguments_json), result=json.loads(call.result_json),
                error_code=call.error_code, duration_ms=call.duration_ms,
                trace_id=call.trace_id))

    def _job_status(self, actor: ActorContext, arguments: Mapping[str, Any]):
        job_id = UUID(str(arguments["job_id"]))
        job = self.jobs.get(job_id, actor)
        return job.model_dump(mode="json")

    def _agent_runs(self, actor: ActorContext, arguments: Mapping[str, Any]):
        limit = int(arguments.get("limit", 20))
        return self.agents.list(actor, limit).model_dump(mode="json")
