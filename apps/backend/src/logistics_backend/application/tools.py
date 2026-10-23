"""Backend binding of the agent tool registry (P17-01 subset)."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import UUID

from logistics_agents.tools import ToolRegistry, ToolResult, ToolSpec
from logistics_domain.runtime import ActorContext


class ToolService:
    def __init__(self, jobs, agents):
        self.jobs = jobs
        self.agents = agents
        self.registry = ToolRegistry()
        self.registry.register(ToolSpec(name="job_status",
            description="Read a job's status and result reference by job_id",
            allowed_roles=("operator", "viewer")), self._job_status)
        self.registry.register(ToolSpec(name="agent_runs",
            description="List recent agent chat runs for the current scope",
            allowed_roles=("operator", "viewer")), self._agent_runs)

    def specs(self):
        return self.registry.specs()

    def invoke(self, name: str, actor: ActorContext,
               arguments: Mapping[str, Any]) -> ToolResult:
        return self.registry.invoke(name, actor, arguments)

    def _job_status(self, actor: ActorContext, arguments: Mapping[str, Any]):
        job_id = UUID(str(arguments["job_id"]))
        job = self.jobs.get(job_id, actor)
        return job.model_dump(mode="json")

    def _agent_runs(self, actor: ActorContext, arguments: Mapping[str, Any]):
        limit = int(arguments.get("limit", 20))
        return self.agents.list(actor, limit).model_dump(mode="json")
