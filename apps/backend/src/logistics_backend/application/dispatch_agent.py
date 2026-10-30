"""Run-scoped, read-only deterministic dispatch tools for the LLM coordinator.

No tool registers an incident, starts a simulation, approves a candidate, or modifies
an operational schedule. The selected checked run is bound by the server, not the model.
"""

from __future__ import annotations

from time import monotonic
from typing import Any, Mapping
from uuid import UUID

from logistics_agents.tools import ToolRegistry, ToolResult, ToolSpec
from logistics_backend.application.integration_simulation_tracks import (
    SimulationTrackError,
    delay_impact,
    hold_and_shift,
)
from logistics_backend.application.timeline import state_at_time
from logistics_backend.errors import ServiceError
from logistics_domain.states import ErrorCode


def _schema(properties: dict | None = None, required: tuple[str, ...] = ()) -> dict:
    return {"type": "object", "properties": properties or {},
            "required": list(required), "additionalProperties": False}


TIME = {"type": "integer", "minimum": 0, "maximum": 604800}
DELAY = {"type": "integer", "minimum": 1, "maximum": 3600}
VEHICLE = {"type": "string", "format": "uuid", "description": "Vehicle UUID from a read tool"}


class DispatchOrchestrator:
    def __init__(self, integration, simulation, agents):
        self.integration = integration
        self.simulation = simulation
        self.agents = agents

    @staticmethod
    def _checked(result: dict) -> None:
        if result.get("status") != "checked" or (result.get("joint_validation") or {}).get("valid") is not True:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "run is not checked and jointly validated")

    @staticmethod
    def _validate_args(spec: ToolSpec, args: Mapping[str, Any]) -> None:
        """Enforce the exposed JSON schema subset at the execution boundary, not just in prompts."""
        params = spec.parameters or _schema()
        properties = params.get("properties", {})
        if any(key not in properties for key in args):
            raise ValueError("unexpected tool argument")
        if any(name not in args for name in params.get("required", [])):
            raise ValueError("missing required tool argument")
        for name, value in args.items():
            constraint = properties[name]
            if constraint.get("type") == "integer":
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError("tool argument must be integer")
                if value < constraint.get("minimum", value) or value > constraint.get("maximum", value):
                    raise ValueError("tool integer out of range")
            elif constraint.get("type") == "string":
                if not isinstance(value, str):
                    raise ValueError("tool argument must be string")
                if constraint.get("format") == "uuid":
                    UUID(value)

    def _registry(self, run_id: UUID) -> ToolRegistry:
        registry = ToolRegistry()

        def register(name: str, description: str, parameters: dict, handler):
            spec = ToolSpec(name=name, description=description, allowed_roles=("operator",),
                            parameters=parameters)

            def bounded(current, arguments):
                self._validate_args(spec, arguments)
                return handler(current, arguments)

            registry.register(spec, bounded)

        def run_overview(current, _):
            result = self.integration.get(run_id, current)
            self._checked(result)
            return {"run_id": str(run_id), "status": result["status"],
                    "source_kind": result.get("source_kind"),
                    "joint_validation": result.get("joint_validation"),
                    "scenario_id": result.get("request", {}).get("scenario_id"),
                    "simulation_started": self._sim_or_none(run_id, current) is not None,
                    "data_source": "checked_postgresql_integration_run"}

        register("get_current_run", "Read the checked integration run, validation and simulation status",
                 _schema(), run_overview)

        def metrics(current, _):
            result = self.integration.get(run_id, current)
            self._checked(result)
            return {"run_id": str(run_id), "observations": result.get("observations"),
                    "data_source": "checked_solver_observations"}

        register("get_dispatch_metrics", "Read actual validated warehouse and transport observations",
                 _schema(), metrics)

        def warehouse(current, args):
            at_s = args["at_s"]
            state = self.simulation.state_at(run_id, at_s, "active", current)
            return {"run_id": str(run_id), "time_s": at_s,
                    "completed_operation_ids": state.get("completed_operation_ids", []),
                    "active_operation_ids": state.get("active_operation_ids", []),
                    "completed_order_ids": state.get("completed_order_ids", []),
                    "source_kind": state.get("source_kind"), "actual_inventory_mutated": False}

        register("get_warehouse_progress", "Read warehouse operation progress in the stored simulation at at_s",
                 _schema({"at_s": TIME}, ("at_s",)), warehouse)

        def vehicles(current, args):
            at_s = args["at_s"]
            state = self.simulation.state_at(run_id, at_s, "active", current)
            return {"run_id": str(run_id), "time_s": at_s,
                    "vehicle_positions": state.get("vehicle_positions", {}),
                    "in_transit_vehicle_ids": state.get("in_transit_vehicle_ids", []),
                    "active_version": state.get("active_version"),
                    "incident_status": state.get("incident_status"),
                    "source_kind": state.get("source_kind")}

        register("get_vehicle_states", "Read simulated truck positions and transit status at at_s",
                 _schema({"at_s": TIME}, ("at_s",)), vehicles)

        def preview(current, args):
            return self.preview_delay(run_id, current, UUID(args["vehicle_id"]),
                                      args["time_s"], args["delay_s"])

        register("preview_vehicle_delay", "Read-only validated impact of a future simulated vehicle delay; NEVER records or approves",
                 _schema({"vehicle_id": VEHICLE, "time_s": TIME, "delay_s": DELAY},
                         ("vehicle_id", "time_s", "delay_s")), preview)
        return registry

    def _sim_or_none(self, run_id, actor):
        try:
            return self.simulation.get(run_id, actor)
        except ServiceError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                return None
            raise

    def preview_delay(self, run_id: UUID, actor, vehicle_id: UUID, time_s: int, delay_s: int) -> dict:
        """Pure projection: never calls incident(), start(), events.ingest(), or writes to DB."""
        result = self.integration.get(run_id, actor)
        self._checked(result)
        sim = self.simulation.get(run_id, actor)  # Simulation must already exist.
        if sim.get("incident") is not None:
            raise ServiceError(ErrorCode.RESOURCE_CONFLICT, "simulation already has an incident")
        vehicle = str(vehicle_id)
        if not any(track.get("vehicle_id") == vehicle for track in sim["tracks"]):
            raise ServiceError(ErrorCode.INVALID_INPUT, "vehicle not in checked simulation")
        state = state_at_time({"events": sim["events"]}, result, time_s)
        if vehicle not in state.get("in_transit_vehicle_ids", []):
            raise ServiceError(ErrorCode.INVALID_INPUT, "vehicle not in transit at given time")
        try:
            projection = self.simulation.project_delay(result, sim, vehicle, time_s,
                delay_s, 2000, f'preview:{run_id}:{vehicle}:{time_s}:{delay_s}')
        except SimulationTrackError as exc:
            raise ServiceError(ErrorCode.INVALID_INPUT, str(exc)) from exc
        return {"run_id": str(run_id), "simulation_id": sim["simulation_id"],
                "vehicle_id": vehicle, "time_s": time_s, "delay_s": delay_s,
                "strategy": projection["strategy"], "impact": projection["impact"],
                "proposal_valid": projection["proposal_valid"], "committed": False,
                "approved": False, "requires_human_confirmation": True,
                "route_replanned": projection["route_changed"],
                "local_solver": projection["local_solver"],
                "actual_inventory_mutated": False}

    def execute(self, command, actor, trace_id):
        checked = self.integration.get(command.run_id, actor)
        self._checked(checked)
        registry = self._registry(command.run_id)
        descriptions = [spec.to_openai_tool() for spec in registry.specs()]
        # Model does not receive a run_id argument; the backend binds it to this request.
        message = (f"Checked run_id: {command.run_id}. Only use tools for factual results. "
                   "The simulation is not actual vehicle telemetry, and an analysis is NOT an approval. "
                   "You must invoke relevant tools before giving any concrete business facts. "
                   f"Operator question: {command.message}")
        started = monotonic()
        try:
            run = self.agents.chat.run_with_tools(message, tools=descriptions,
                executor=lambda name, args: registry.invoke(name, actor, args), max_turns=4)
        except Exception:
            self.agents.record_dispatch_failure(command, actor, trace_id,
                                                int((monotonic() - started) * 1000))
            raise
        grounded = any(turn.ok for turn in run.turns)
        if run.stopped_reason != "final_answer":
            content = "工具调用轮次已达到上限，未形成完整答复；请缩小问题范围后重新查询。"
            outcome = "max_turns"
        elif not grounded:
            content = "未取得有效的调度工具证据，不能据此报告订单、车辆或调度结论。"
            outcome = "no_tool_evidence"
        else:
            content = run.reply.content
            outcome = "final_answer"
        return self.agents.record_dispatch(command, actor, trace_id, run,
                                           content, outcome,
                                           latency_ms=int((monotonic() - started) * 1000))
