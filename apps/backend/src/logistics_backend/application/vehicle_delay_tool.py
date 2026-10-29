"""车辆延误重调度的智能体工具绑定。

职责边界：
* 工具只做「读事件 → 局部重解 → 独立校验 → 产出待审方案」，**不提交**、不写版本；
* 事件事实一律来自持久化事件载荷，不由模型在对话里提供，避免模型编造延误对象；
* 求解与校验失败时返回 ok=True 但 status=not_resolved，让模型据实解释，而不是抛异常掩盖。
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol
from uuid import UUID

from logistics_agents.tools import ToolSpec
from logistics_backend.application.vehicle_delay_reschedule import (
    VehicleDelayRequest,
    resolve_vehicle_delay,
    vehicle_for_transport_task,
)
from logistics_domain.execution import EventKind
from logistics_domain.planning import RouteStop, TransportPlan
from logistics_domain.runtime import ActorContext
from logistics_domain.transport import TransportProblem

TOOL_NAME = "prepare_vehicle_delay_reschedule"
TOOL_DESCRIPTION = (
    "读取车辆延误事件，对受影响车辆做局部重解并通过独立校验，返回待人工确认的候选方案"
)
# 关键：模型只能指定「哪条事件」。车辆、延误时长、发生时刻全部由事件载荷决定，
# 否则模型可以在对话里编造一个不存在的延误对象。
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "event_id": {
            "type": "string",
            "description": "已持久化的车辆延误事件 ID（UUID）。延误对象与时长由该事件载荷决定。",
        },
        "budget_ms": {
            "type": "integer",
            "minimum": 500,
            "maximum": 30000,
            "description": "局部重解的求解预算（毫秒），默认 4000。",
        },
    },
    "required": ["event_id"],
    "additionalProperties": False,
}


class BasePlan(Protocol):
    """基础方案的读取端口；由持久化层实现，测试中可注入内存实现。"""

    def __call__(self, actor: ActorContext) -> tuple[TransportProblem, TransportPlan, tuple[RouteStop, ...]]: ...


class EventPayloadReader(Protocol):
    def __call__(self, event_id: UUID, actor: ActorContext) -> dict: ...


def _as_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _as_uuid(value: Any, field: str) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise ValueError(f"{field} must be a UUID")


class VehicleDelayPlanner:
    """把「事件 → 局部重解 → 候选」串成一次可复现的编排。"""

    def __init__(self, read_event: EventPayloadReader, base_plan: BasePlan):
        self.read_event = read_event
        self.base_plan = base_plan

    def prepare(self, actor: ActorContext, event_id: UUID, budget_ms: int = 4000) -> dict:
        event = self.read_event(event_id, actor)
        kind = str(event.get("kind", ""))
        payload = event.get("payload") or {}
        if not isinstance(payload, Mapping):
            return {"status": "not_resolved", "reason": "event_payload_not_an_object",
                    "event_id": str(event_id), "event_kind": kind}
        if kind != EventKind.TRANSPORT_DELAY.value:
            return {"status": "not_resolved", "reason": "unsupported_event_kind",
                    "event_id": str(event_id), "event_kind": kind,
                    "supported_kind": EventKind.TRANSPORT_DELAY.value}

        # 合法载荷：TransportDelayPayload —— 实体是运输任务，延误时长是 additional_seconds。
        try:
            transport_task_id = _as_uuid(payload.get("transport_task_id"), "transport_task_id")
            delay_s = _as_int(payload.get("additional_seconds"), "additional_seconds")
            event_time_s = _as_int(payload.get("effective_at_s"), "effective_at_s")
            if delay_s <= 0:
                raise ValueError("additional_seconds must be a positive integer")
            if event_time_s < 0:
                raise ValueError("effective_at_s must be non-negative")
        except (TypeError, ValueError) as exc:
            return {"status": "not_resolved", "reason": "invalid_event_payload",
                    "event_id": str(event_id), "event_kind": kind, "detail": str(exc)}

        problem, plan, stops = self.base_plan(actor)
        # 车辆不由载荷指定：从基础方案按运输任务反查，避免把延误挂到别的车上。
        vehicle_id = vehicle_for_transport_task(plan, stops, transport_task_id)
        if vehicle_id is None:
            return {"status": "not_resolved", "reason": "transport_task_not_in_base_plan",
                    "event_id": str(event_id), "event_kind": kind,
                    "transport_task_id": str(transport_task_id)}

        request = VehicleDelayRequest(vehicle_id=vehicle_id, delay_s=delay_s,
                                      event_time_s=event_time_s, budget_ms=budget_ms)
        outcome = resolve_vehicle_delay(problem, plan, stops, request)
        return {
            "status": outcome.status,
            "reason": outcome.reason,
            "event_id": str(event_id),
            "event_kind": kind,
            "transport_task_id": str(transport_task_id),
            "vehicle_id": str(vehicle_id),
            "delay_s": delay_s,
            "event_time_s": event_time_s,
            "affected_order_ids": [str(o) for o in outcome.affected_order_ids],
            "committed": False,
            "requires_human_approval": outcome.resolved,
            "validation": (None if outcome.validation is None else {
                "valid": outcome.validation.valid,
                "checked_codes": list(outcome.validation.checked_codes),
                "violations": [
                    {"code": v.code, "severity": v.severity.value} for v in outcome.validation.violations[:10]
                ],
            }),
            "detail": outcome.detail,
        }


def register_vehicle_delay_tool(tool_service, planner: VehicleDelayPlanner) -> None:
    """把车辆延误工具挂到统一白名单，复用既有 tool_calls 审计。"""

    def handler(actor: ActorContext, arguments: Mapping[str, Any]) -> dict:
        event_id = _as_uuid(arguments.get("event_id"), "event_id")
        budget_ms = arguments.get("budget_ms", 4000)
        return planner.prepare(actor, event_id, _as_int(budget_ms, "budget_ms"))

    tool_service.register(
        ToolSpec(name=TOOL_NAME, description=TOOL_DESCRIPTION,
                 allowed_roles=("operator",), parameters=TOOL_PARAMETERS),
        handler,
    )
