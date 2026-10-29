"""把已提交版本的运输路由与停靠点落库，并能原样读回。

背景：`routes` / `route_stops` 两张表从 0002 迁移就有，但应用层从未写入，
导致「已提交方案」无法还原出停靠点时间线（局部重解因此拿不到基础方案）。
这里补的正是这条缺口：只写既有表，不改任何数据库结构。

约定：
* 落库时重建路由与停靠点的 id，避免同一候选提交成多个版本时主键冲突；
* payload 存完整 DTO，读回时不靠列拼装，保证时间字段与任务引用不丢。
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from logistics_backend.persistence.planning_models import route_stops, routes
from logistics_contracts.planning import RouteDTO, RouteStopDTO
from logistics_domain.planning import Route, RouteStop


def persist_version_routes(
    uow,
    *,
    scope_id: UUID,
    version_id: UUID,
    actor_id: UUID,
    now: datetime,
    plan_routes: tuple[Route, ...],
    plan_stops: tuple[RouteStop, ...],
) -> tuple[int, int]:
    """把一次提交涉及的路由与停靠点写入既有表，返回 (路由数, 停靠点数)。"""

    stops_by_route: dict[UUID, list[RouteStop]] = {}
    for stop in plan_stops:
        stops_by_route.setdefault(stop.route_id, []).append(stop)

    written_routes = 0
    written_stops = 0
    for route in plan_routes:
        new_route_id = uuid4()
        stored = _with_entity(route, id=new_route_id, version_id=version_id,
                              created_at=now, updated_at=now, row_version=0, created_by=actor_id)
        dto = RouteDTO.model_validate(_fields(stored))
        uow.connection.execute(routes.insert().values(
            id=stored.id, scope_id=scope_id, status=stored.status.value,
            created_at=now, updated_at=now, created_by=actor_id, row_version=0,
            schema_version="2.0.0", payload=json.loads(dto.model_dump_json()),
            version_id=version_id, vehicle_id=stored.vehicle_id, driver_id=stored.driver_id,
            start_node_id=stored.start_node_id, end_node_id=stored.end_node_id,
            total_distance_m=stored.total_distance_m,
            matrix_id=stored.matrix_ref.matrix_id, matrix_version=stored.matrix_ref.version))
        written_routes += 1

        for stop in sorted(stops_by_route.get(route.id, ()), key=lambda s: s.sequence):
            new_stop = _with_entity(stop, id=uuid4(), route_id=new_route_id,
                                    created_at=now, updated_at=now, row_version=0,
                                    created_by=actor_id)
            stop_dto = RouteStopDTO.model_validate(_fields(new_stop))
            uow.connection.execute(route_stops.insert().values(
                id=new_stop.id, scope_id=scope_id, status=new_stop.status.value,
                created_at=now, updated_at=now, created_by=actor_id, row_version=0,
                schema_version="2.0.0", payload=json.loads(stop_dto.model_dump_json()),
                route_id=new_route_id, sequence=new_stop.sequence, node_id=new_stop.node_id,
                arrival_s=new_stop.arrival_s, service_start_s=new_stop.service_start_s,
                departure_s=new_stop.departure_s))
            written_stops += 1

    return written_routes, written_stops


def load_version_routes(uow, *, scope_id: UUID, version_id: UUID
                        ) -> tuple[tuple[Route, ...], tuple[RouteStop, ...]]:
    """读回某版本的路由与停靠点；没有落库记录时返回空元组，由调用方显式失败。"""

    route_rows = uow.connection.execute(select(routes).where(
        routes.c.version_id == version_id, routes.c.scope_id == scope_id)
        .order_by(routes.c.created_at)).mappings().all()
    loaded_routes = tuple(RouteDTO.model_validate_json(json.dumps(row["payload"])).to_domain()
                          for row in route_rows)
    if not loaded_routes:
        return (), ()

    route_ids = [route.id for route in loaded_routes]
    stop_rows = uow.connection.execute(select(route_stops).where(
        route_stops.c.route_id.in_(route_ids), route_stops.c.scope_id == scope_id)
        .order_by(route_stops.c.route_id, route_stops.c.sequence)).mappings().all()
    loaded_stops = tuple(RouteStopDTO.model_validate_json(json.dumps(row["payload"])).to_domain()
                         for row in stop_rows)
    return loaded_routes, loaded_stops


def _fields(entity) -> dict:
    from dataclasses import fields

    return {item.name: getattr(entity, item.name) for item in fields(entity)}


def _with_entity(entity, **changes):
    from dataclasses import replace

    return replace(entity, **changes)
