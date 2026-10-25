import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

try:
    from ortools.sat.python import cp_model
except ImportError:  # dependency is installed from requirements.txt in deployment
    cp_model = None

import pymysql
from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="智慧物流调度算法服务",
    description="面向县域农产品冷链场景的调度计算服务。提供数据读取、CP-SAT 冷间排程和异常重调度接口。",
    version="0.4.0",
    docs_url=None,
)


@app.get("/docs", include_in_schema=False)
def chinese_docs() -> HTMLResponse:
    """提供中文化的 Swagger 调试界面。"""
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="智慧物流调度算法服务 - 接口文档",
        swagger_ui_parameters={
            "docExpansion": "list",
            "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
        },
    )
    page = html.body.decode("utf-8")
    translate_js = """
(function () {
  const dict = {
    "Swagger UI": "接口文档",
    "Authorize": "授权",
    "Try it out": "测试",
    "Execute": "执行",
    "Cancel": "取消",
    "Clear": "清空",
    "Close": "关闭",
    "Filter": "筛选",
    "Explore": "浏览",
    "Schemas": "数据模型",
    "Models": "模型",
    "Responses": "响应",
    "Response headers": "响应头",
    "Request body": "请求体",
    "Request URL": "请求地址",
    "Server response": "服务器响应",
    "Curl": "Curl 请求",
    "Example Value": "示例值",
    "Example": "示例",
    "Copy": "复制",
    "Download": "下载",
    "No content": "无内容",
    "No operations defined in spec!": "接口文档暂无可用接口",
    "Response content": "响应内容",
    "Parameters": "参数",
    "Parameter": "参数",
    "Description": "描述",
    "Expand Operations": "展开接口",
    "Collapse Operations": "收起接口",
    "List operations": "接口列表",
    "Show Details": "显示详情",
    "Hide Details": "隐藏详情"
  };

  function translate(root) {
    const walker = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let node;
    while ((node = walker.nextNode())) nodes.push(node);
    for (const textNode of nodes) {
      const value = textNode.nodeValue.trim();
      if (dict[value]) textNode.nodeValue = textNode.nodeValue.replace(value, dict[value]);
    }
    document.title = "智慧物流调度算法服务 - 接口文档";
  }

  const start = () => {
    translate(document.body);
    const observer = new MutationObserver(() => translate(document.body));
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    setTimeout(() => observer.disconnect(), 20000);
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();

"""
    page = page.replace("</body>", "<script>" + translate_js + "</script></body>")
    return HTMLResponse(page)


def db_config() -> dict:
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "123456"),
        "database": os.getenv("MYSQL_DATABASE", "smart_warehouse"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
        "connect_timeout": 5,
        "read_timeout": 10,
        "write_timeout": 10,
    }


@contextmanager
def db_cursor():
    connection = pymysql.connect(**db_config())
    try:
        with connection.cursor() as cursor:
            yield cursor
    finally:
        connection.close()


def parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)


def key(row: dict, snake: str, camel: str, default=None):
    return row.get(snake, row.get(camel, default))


def bool_value(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "available", "normal"}


def load_batches() -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT
                b.id,
                b.batch_code AS batchCode,
                p.product_name AS product,
                COALESCE(p.category, '其他') AS category,
                COALESCE(b.quality_grade, 'A') AS grade,
                b.quantity_remaining AS quantity,
                b.receive_time AS expectedInbound,
                COALESCE(p.min_temperature, 0) AS minTemperature,
                COALESCE(p.max_temperature, 25) AS maxTemperature,
                COALESCE(p.base_shelf_life_days, 7) AS maxStorageDays,
                COALESCE(b.remaining_days, p.base_shelf_life_days, 7) AS remainingShelfDays,
                CASE WHEN p.perishable = 1 THEN 1 ELSE 0 END AS preCoolingRequired,
                b.status AS status,
                p.storage_type AS storageType
            FROM fresh_batch b
            JOIN products p ON p.id = b.product_id
            WHERE b.quantity_remaining > 0
              AND COALESCE(b.status, 'NORMAL') <> 'EXPIRED'
            ORDER BY b.receive_time, b.id
        """)
        rows = cursor.fetchall()
    for row in rows:
        row["preCoolingRequired"] = bool_value(row.get("preCoolingRequired"))
    return rows


def load_orders() -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT
                o.id,
                CONCAT('ORD-', LPAD(o.id, 4, '0')) AS orderCode,
                CONCAT('客户-', o.id) AS customer,
                p.product_name AS product,
                o.quantity AS quantity,
                'A' AS grade,
                DATE_ADD(COALESCE(o.created_at, NOW()), INTERVAL 2 DAY) AS latestDelivery,
                1 AS minShelfLifeDays,
                o.status AS status,
                p.storage_type AS storageType
            FROM outbound_order o
            JOIN products p ON p.id = o.product_id
            WHERE COALESCE(o.status, 'CREATED') IN ('CREATED', 'PENDING')
            ORDER BY o.created_at, o.id
        """)
        return list(cursor.fetchall())


def load_cold_rooms() -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT
                s.id,
                s.code AS roomCode,
                COALESCE(w.name, '智能仓库 Demo') AS warehouseName,
                COALESCE(s.capacity, 0) AS capacity,
                COALESCE(s.used, 0) AS usedCapacity,
                CASE WHEN s.storage_type = 'FROZEN' THEN -22
                     WHEN s.storage_type = 'CHILLED' THEN 0
                     ELSE 10 END AS minTemperature,
                CASE WHEN s.storage_type = 'FROZEN' THEN -18
                     WHEN s.storage_type = 'CHILLED' THEN 4
                     ELSE 30 END AS maxTemperature,
                COALESCE(s.category, '通用') AS supportedProducts,
                0 AS preCoolingSupported,
                2 AS cleaningHours,
                1 AS switchHours,
                CASE WHEN COALESCE(s.status, 'NORMAL') = 'NORMAL' THEN 'NORMAL'
                     ELSE s.status END AS deviceStatus,
                1.5 AS costPerTonHour,
                s.storage_type AS storageType,
                s.current_temperature AS currentTemperature,
                s.current_humidity AS currentHumidity
            FROM shelf s
            LEFT JOIN warehouse w ON w.id = s.warehouse_id
            WHERE s.storage_type IN ('CHILLED', 'FROZEN')
            ORDER BY s.id
        """)
        return list(cursor.fetchall())


def demo_vehicles() -> list[dict]:
    return [
        {"id": 1, "vehicleCode": "V01", "vehicleType": "冷藏车", "capacity": 1000, "volume": 18, "refrigerated": True,
         "minTemperature": 0, "maxTemperature": 8, "currentLocation": "智能仓库 Demo", "status": "AVAILABLE", "costPerKm": 2.50},
        {"id": 2, "vehicleCode": "V02", "vehicleType": "冷藏车", "capacity": 800, "volume": 15, "refrigerated": True,
         "minTemperature": 0, "maxTemperature": 6, "currentLocation": "智能仓库 Demo", "status": "AVAILABLE", "costPerKm": 2.30},
        {"id": 3, "vehicleCode": "V03", "vehicleType": "冷藏车", "capacity": 500, "volume": 10, "refrigerated": True,
         "minTemperature": 2, "maxTemperature": 8, "currentLocation": "智能仓库 Demo", "status": "AVAILABLE", "costPerKm": 2.00},
    ]


def demo_routes() -> list[dict]:
    return [
        {"id": 1, "routeCode": "R001", "startNode": "智能仓库 Demo", "endNode": "县城生鲜超市", "distanceKm": 18.5,
         "estimatedMinutes": 35, "roadStatus": "NORMAL", "roadFactor": 1.0, "tollCost": 0.0, "refrigeratedRequired": True, "status": "AVAILABLE"},
        {"id": 2, "routeCode": "R002", "startNode": "智能仓库 Demo", "endNode": "区域批发市场", "distanceKm": 35.0,
         "estimatedMinutes": 60, "roadStatus": "NORMAL", "roadFactor": 1.0, "tollCost": 8.0, "refrigeratedRequired": True, "status": "AVAILABLE"},
        {"id": 3, "routeCode": "R003", "startNode": "智能仓库 Demo", "endNode": "社区电商配送中心", "distanceKm": 15.0,
         "estimatedMinutes": 30, "roadStatus": "NORMAL", "roadFactor": 1.0, "tollCost": 0.0, "refrigeratedRequired": True, "status": "AVAILABLE"},
        {"id": 4, "routeCode": "R004", "startNode": "智能仓库 Demo", "endNode": "乡镇配送点", "distanceKm": 26.0,
         "estimatedMinutes": 50, "roadStatus": "CONGESTED", "roadFactor": 1.35, "tollCost": 5.0, "refrigeratedRequired": True, "status": "AVAILABLE"},
    ]


def load_dataset() -> dict:
    return {
        "batches": load_batches(),
        "orders": load_orders(),
        "coldRooms": load_cold_rooms(),
        "vehicles": demo_vehicles(),
        "routes": demo_routes(),
    }


def normalize_query_data(data: dict) -> dict:
    dataset = load_dataset()
    # The database is the source of truth. Optional arrays are accepted for compatibility,
    # but an empty/missing array is always replaced with current database data.
    for field in ("batches", "orders", "coldRooms"):
        if not data.get(field):
            data[field] = dataset[field]
    if not data.get("vehicles"):
        data["vehicles"] = dataset["vehicles"]
    if not data.get("routes"):
        data["routes"] = dataset["routes"]
    return data


def room_matches_batch(room: dict, batch: dict) -> bool:
    """Hard compatibility check for storage type, temperature and product/category.

    A room is considered compatible only when:
      1) storage type matches (e.g. CHILLED/FROZEN)
      2) room temperature range contains the batch requirement
      3) when the room declares supportedProducts, the batch product/category
         must match at least one declared keyword.
    """
    storage_type = str(room.get("storageType") or room.get("storage_type") or "").upper()
    batch_type = str(batch.get("storageType") or batch.get("storage_type") or "").upper()
    if batch_type and storage_type and batch_type != storage_type:
        return False

    bmin = float(key(batch, "min_temperature", "minTemperature", -99))
    bmax = float(key(batch, "max_temperature", "maxTemperature", 99))
    rmin = float(key(room, "min_temperature", "minTemperature", -99))
    rmax = float(key(room, "max_temperature", "maxTemperature", 99))
    if bmin < rmin or bmax > rmax:
        return False

    supported = str(key(room, "supported_products", "supportedProducts", "") or "").strip().lower()
    if supported:
        product = str(batch.get("product", "") or "").strip().lower()
        category = str(batch.get("category", "") or "").strip().lower()
        # Generic/comprehensive zones accept any product of the correct storage type.
        generic_tokens = ("综合", "通用", "all", "general")
        if not any(token in supported for token in generic_tokens):
            if not any(token and token in supported for token in (product, category)):
                return False
    return True


def choose_route(routes: list[dict], start: str, end_candidates: list[str], refrigerated_required: bool = True):
    candidates = []
    for route in routes:
        if str(key(route, "status", "status", "AVAILABLE")).upper() != "AVAILABLE":
            continue
        if key(route, "start_node", "startNode") != start:
            continue
        if key(route, "end_node", "endNode") not in end_candidates:
            continue
        if refrigerated_required and not bool_value(key(route, "refrigerated_required", "refrigeratedRequired", True), True):
            continue
        road_status = str(key(route, "road_status", "roadStatus", "NORMAL")).upper()
        if road_status == "BLOCKED":
            continue
        dist = float(key(route, "distance_km", "distanceKm", 999999))
        minutes = float(key(route, "estimated_minutes", "estimatedMinutes", 0))
        factor = float(key(route, "road_factor", "roadFactor", 1.0))
        candidates.append((dist * factor + minutes * 0.02, route))
    return sorted(candidates, key=lambda x: x[0])[0][1] if candidates else None


def choose_vehicle(vehicles: list[dict], quantity: float, refrigerated_required: bool = True):
    candidates = []
    for vehicle in vehicles:
        if str(key(vehicle, "status", "status", "AVAILABLE")).upper() != "AVAILABLE":
            continue
        if refrigerated_required and not bool_value(key(vehicle, "refrigerated", "refrigerated", True), True):
            continue
        capacity = float(key(vehicle, "capacity", "capacity", 0))
        if capacity < quantity:
            continue
        candidates.append((capacity, vehicle))
    return sorted(candidates, key=lambda x: x[0])[0][1] if candidates else None


def solve_greedy(data: dict) -> dict:
    start = parse_dt(data.get("planningStart", datetime.now().isoformat()))
    end = parse_dt(data.get("planningEnd", (start + timedelta(days=7)).isoformat()))
    rooms = data.get("coldRooms", [])
    batches = data.get("batches", [])
    orders = data.get("orders", [])
    vehicles = data.get("vehicles", [])
    routes = data.get("routes", [])

    order_remaining = {str(o.get("id")): float(o.get("quantity", 0)) for o in orders}
    room_cursor = {str(r.get("id")): start for r in rooms}
    room_used = {str(r.get("id")): float(key(r, "used_capacity", "usedCapacity", 0) or 0) for r in rooms}
    assignments = []
    unassigned = 0
    total_cost = 0.0
    total_transport_cost = 0.0

    for batch in sorted(batches, key=lambda x: parse_dt(key(x, "expected_inbound", "expectedInbound"))):
        qty = float(batch.get("quantity", 0) or 0)
        product = str(batch.get("product", ""))
        bmin = float(key(batch, "min_temperature", "minTemperature", -99))
        bmax = float(key(batch, "max_temperature", "maxTemperature", 99))
        expected = max(parse_dt(key(batch, "expected_inbound", "expectedInbound")), start)

        room_candidates = []
        for room in rooms:
            rid = str(room.get("id"))
            status = str(key(room, "device_status", "deviceStatus", "NORMAL")).upper()
            if status not in ("NORMAL", "正常"):
                continue
            if not room_matches_batch(room, batch):
                continue
            cap = float(key(room, "capacity", "capacity", 0) or 0)
            used = room_used[rid]
            if used + qty > cap:
                continue
            rmin = float(key(room, "min_temperature", "minTemperature", -99))
            rmax = float(key(room, "max_temperature", "maxTemperature", 99))
            if bmin < rmin or bmax > rmax:
                continue
            st = max(expected, room_cursor[rid], start)
            hourly_cost = float(key(room, "cost_per_ton_hour", "costPerTonHour", 1) or 1)
            room_candidates.append((st, hourly_cost, room))

        if not room_candidates:
            unassigned += 1
            continue

        _, hourly_cost, room = sorted(room_candidates, key=lambda x: (x[0], x[1]))[0]
        rid = str(room.get("id"))
        inbound = max(expected, room_cursor[rid])

        matching_order = next(
            (o for o in orders if o.get("product") == product and float(order_remaining.get(str(o.get("id")), 0)) > 0),
            None,
        )
        max_days = float(key(batch, "max_storage_days", "maxStorageDays", 7) or 7)
        min_shelf = float(key(matching_order, "min_shelf_life_days", "minShelfLifeDays", 1) if matching_order else 1)
        storage_days = min(max_days, max(1.0, min_shelf))
        latest_delivery = parse_dt(key(matching_order, "latest_delivery", "latestDelivery")) if matching_order else end
        outbound = min(inbound + timedelta(days=storage_days), latest_delivery, end)
        if outbound < inbound:
            outbound = inbound

        order_id = int(matching_order["id"]) if matching_order else None
        allocated_to_order = min(qty, order_remaining[str(order_id)]) if order_id else 0.0
        if order_id:
            order_remaining[str(order_id)] -= allocated_to_order

        customer = str(key(matching_order, "customer", "customer", "")) if matching_order else ""
        route = choose_route(routes, str(key(room, "warehouse_name", "warehouseName", "智能仓库 Demo")),
                             [customer, "县城生鲜超市", "区域批发市场", "社区电商配送中心", "乡镇配送点"], True)
        vehicle = choose_vehicle(vehicles, allocated_to_order or qty, True)

        route_id = int(route["id"]) if route else None
        vehicle_id = int(vehicle["id"]) if vehicle else None
        transport_cost = 0.0
        if route and vehicle:
            distance = float(key(route, "distance_km", "distanceKm", 0) or 0)
            factor = float(key(route, "road_factor", "roadFactor", 1.0) or 1)
            cost_per_km = float(key(vehicle, "cost_per_km", "costPerKm", 0) or 0)
            toll = float(key(route, "toll_cost", "tollCost", 0) or 0)
            transport_cost = distance * factor * cost_per_km + toll
            total_transport_cost += transport_cost

        risk = "LOW"
        remaining_shelf = float(key(batch, "remaining_shelf_days", "remainingShelfDays", 99) or 99)
        if remaining_shelf < 4 or (outbound - inbound).days >= 6:
            risk = "MEDIUM"

        hours = max(1, (outbound - inbound).total_seconds() / 3600)
        storage_cost = qty * hourly_cost * hours
        total_cost += storage_cost + transport_cost
        room_used[rid] += qty
        cleaning = float(key(room, "cleaning_hours", "cleaningHours", 2) or 2)
        switching = float(key(room, "switch_hours", "switchHours", 1) or 1)
        room_cursor[rid] = outbound + timedelta(hours=cleaning + switching)

        assignments.append({
            "batchId": int(batch["id"]),
            "coldRoomId": int(room["id"]),
            "orderId": order_id,
            "vehicleId": vehicle_id,
            "routeId": route_id,
            "plannedInbound": inbound.isoformat(timespec="minutes"),
            "plannedOutbound": outbound.isoformat(timespec="minutes"),
            "allocatedQuantity": qty,
            "storageCost": round(storage_cost, 2),
            "transportCost": round(transport_cost, 2),
            "qualityRisk": risk,
            "feasible": bool(vehicle_id is not None or order_id is None),
            "changeNote": "" if route and vehicle else "缺少满足条件的运输路线或车辆资源",
        })

    total_cap = sum(float(key(r, "capacity", "capacity", 0) or 0) for r in rooms) or 1
    used_cap = sum(max(0.0, room_used[str(r.get("id"))]) for r in rooms)
    fulfillment = 100.0 * sum(1 for o in orders if order_remaining.get(str(o.get("id")), 0) <= 0) / (len(orders) or 1)
    on_time = 100.0 if not unassigned else max(0.0, 100 - unassigned / max(1, len(batches)) * 100)

    return {
        "planningStart": start.isoformat(timespec="minutes"),
        "planningEnd": end.isoformat(timespec="minutes"),
        "objective": data.get("objective", "FULFILLMENT_RISK"),
        "assignments": assignments,
        "utilization": round(min(100.0, used_cap / total_cap * 100), 2),
        "fulfillment": round(fulfillment, 2),
        "onTimeInbound": round(on_time, 2),
        "totalCost": round(total_cost, 2),
        "transportCost": round(total_transport_cost, 2),
        "highRiskCount": sum(1 for x in assignments if x["qualityRisk"] == "HIGH"),
        "changedCount": 0,
        "unassignedBatchCount": unassigned,
    }


def eligible_rooms_for_batch(batch: dict, rooms: list[dict]) -> list[dict]:
    """Return only rooms that can legally host the batch under hard constraints."""
    eligible = []
    qty = float(batch.get("quantity", 0) or 0)
    for room in rooms:
        status = str(key(room, "device_status", "deviceStatus", "NORMAL") or "NORMAL").upper()
        capacity = float(key(room, "capacity", "capacity", 0) or 0)
        used = float(key(room, "used_capacity", "usedCapacity", 0) or 0)
        if status not in ("NORMAL", "正常"):
            continue
        if not room_matches_batch(room, batch):
            continue
        if capacity - used < qty:
            continue
        eligible.append(room)
    return eligible


def validate_schedule_solution(result: dict, data: dict) -> tuple[bool, dict[str, list[str]]]:
    """Independent post-solver validation for the B-01 plan.

    The validator intentionally does not trust CP-SAT variables. It re-checks the
    returned business result against the same hard rules so later Agent/DB layers
    can safely consume only a verified plan.
    """
    errors: dict[str, list[str]] = {}
    batches = {str(b.get("id")): b for b in data.get("batches", [])}
    orders = {str(o.get("id")): o for o in data.get("orders", [])}
    rooms = {str(r.get("id")): r for r in data.get("coldRooms", [])}

    room_items: dict[str, list[tuple[datetime, datetime, str]]] = {}
    order_totals: dict[str, float] = {oid: 0.0 for oid in orders}
    batch_totals: dict[str, float] = {bid: 0.0 for bid in batches}

    for item in result.get("assignments", []):
        bid = str(item.get("batchId"))
        rid = str(item.get("coldRoomId"))
        if bid not in batches:
            errors.setdefault(bid, []).append("结果引用了不存在的批次")
            continue
        if rid not in rooms:
            errors.setdefault(bid, []).append("结果引用了不存在的冷间")
            continue

        batch = batches[bid]
        room = rooms[rid]
        qty = float(item.get("allocatedQuantity", 0) or 0)
        inbound = parse_dt(item.get("plannedInbound"))
        outbound = parse_dt(item.get("plannedOutbound"))
        expected = parse_dt(key(batch, "expected_inbound", "expectedInbound"))

        if qty <= 0:
            errors.setdefault(bid, []).append("allocatedQuantity 必须大于0")
        if inbound < expected:
            errors.setdefault(bid, []).append("plannedInbound 早于真实到货时间")
        if outbound < inbound:
            errors.setdefault(bid, []).append("plannedOutbound 早于 plannedInbound")
        if not room_matches_batch(room, batch):
            errors.setdefault(bid, []).append("冷间温区/存储类型/品类不匹配")

        capacity = float(key(room, "capacity", "capacity", 0) or 0)
        used = float(key(room, "used_capacity", "usedCapacity", 0) or 0)
        if used + qty > capacity + 1e-9:
            errors.setdefault(bid, []).append("冷间容量超限")

        duration_minutes = max(1, int(round((outbound - inbound).total_seconds() / 60)))
        room_items.setdefault(rid, []).append((inbound, outbound, bid))

        allocations = item.get("orderAllocations") or []
        for alloc in allocations:
            oid = str(alloc.get("orderId"))
            aq = float(alloc.get("quantity", 0) or 0)
            if oid not in orders:
                errors.setdefault(bid, []).append(f"订单 {oid} 不存在")
                continue
            order_totals[oid] += aq
            batch_totals[bid] += aq
            latest = parse_dt(key(orders[oid], "latest_delivery", "latestDelivery"))
            if aq < 0:
                errors.setdefault(bid, []).append(f"订单 {oid} 分配量不能为负数")
            if aq > 0 and outbound > latest:
                errors.setdefault(bid, []).append(
                    f"订单 {orders[oid].get('orderCode', oid)} 的 plannedOutbound 超过 latestDelivery"
                )

        if not allocations and item.get("orderId") is not None:
            errors.setdefault(bid, []).append("存在 orderId 但缺少 orderAllocations 明细")

        # Keep the variable referenced so the validator remains explicit about time semantics.
        _ = duration_minutes

    for bid, total in batch_totals.items():
        qty = float(batches[bid].get("quantity", 0) or 0)
        if total > qty + 1e-9:
            errors.setdefault(bid, []).append("订单分配量超过批次供给量")

    for oid, total in order_totals.items():
        qty = float(orders[oid].get("quantity", 0) or 0)
        if total > qty + 1e-9:
            errors.setdefault(f"order:{oid}", []).append("订单分配量超过订单需求量")

    for rid, items in room_items.items():
        items.sort(key=lambda x: x[0])
        room = rooms[rid]
        gap = timedelta(hours=(
            float(key(room, "cleaning_hours", "cleaningHours", 2) or 2)
            + float(key(room, "switch_hours", "switchHours", 1) or 1)
        ))
        for i in range(1, len(items)):
            prev_end = items[i - 1][1]
            cur_start = items[i][0]
            if cur_start < prev_end + gap:
                errors.setdefault(items[i][2], []).append(
                    f"与批次 {items[i - 1][2]} 在冷间时间上冲突（含清洁/切换缓冲）"
                )

    return (not errors, errors)


def solve_with_ortools(data: dict) -> dict:
    """Cold-room scheduling V1.2 using OR-Tools CP-SAT.

    V1.2 tightens the model without changing the project's data architecture:
      1) batch-room assignment remains a CP-SAT decision
      2) batch->order allocation quantity becomes an integer decision variable
      3) expectedInbound is a hard lower bound for plannedInbound
      4) latestDelivery is a hard outbound proxy deadline for allocated order quantity
      5) same-room jobs require non-overlap plus cleaning/switching buffer
      6) the result is independently re-validated before being returned as executable

    In B-01, plannedOutbound means the cold-room release time. In B-02/B-03 it can
    be connected to transport duration so customer delivery is modelled end-to-end.
    """
    if cp_model is None:
        raise HTTPException(status_code=503, detail="OR-Tools 未安装，请执行 pip install -r requirements.txt")

    start_dt = parse_dt(data.get("planningStart", datetime.now().isoformat()))
    end_dt = parse_dt(data.get("planningEnd", (start_dt + timedelta(days=7)).isoformat()))
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="planningEnd 必须晚于 planningStart")

    batches = list(data.get("batches", []))
    rooms = list(data.get("coldRooms", []))
    orders = list(data.get("orders", []))

    if not batches:
        return {
            "status": "OPTIMAL", "solver": "OR-Tools CP-SAT", "solverStatus": "OPTIMAL",
            "assignments": [], "utilization": 0.0, "fulfillment": 100.0,
            "onTimeInbound": 100.0, "totalCost": 0.0, "transportCost": 0.0,
            "highRiskCount": 0, "changedCount": 0, "unassignedBatchCount": 0,
            "message": "没有待排程批次",
        }
    if not rooms:
        return {
            "status": "INFEASIBLE", "solver": "OR-Tools CP-SAT", "solverStatus": "INFEASIBLE",
            "assignments": [], "utilization": 0.0, "fulfillment": 0.0,
            "onTimeInbound": 0.0, "totalCost": 0.0, "transportCost": 0.0,
            "highRiskCount": 0, "changedCount": 0, "unassignedBatchCount": len(batches),
            "infeasibleReasons": {str(b.get("id")): ["没有冷间资源"] for b in batches},
            "message": "没有可用冷间资源",
        }

    horizon_minutes = int((end_dt - start_dt).total_seconds() // 60)
    if horizon_minutes <= 0:
        raise HTTPException(status_code=400, detail="排程时间窗无效")

    # Integer quantities are intentional for the current project data model.
    # If future business data requires decimal tons, scale quantities to the smallest unit.
    SCALE = 1
    model = cp_model.CpModel()
    batch_vars: dict[str, dict[str, Any]] = {}
    room_intervals: dict[str, list[Any]] = {str(r.get("id")): [] for r in rooms}
    room_demands: dict[str, list[int]] = {str(r.get("id")): [] for r in rooms}
    infeasible_reasons: dict[str, list[str]] = {}

    # Candidate orders are product-compatible and positive-demand only.
    candidate_orders: dict[str, list[dict]] = {}
    require_full_order_fulfillment = bool(data.get("requireFullOrderFulfillment", False))
    for batch in batches:
        bid = str(batch.get("id"))
        product = str(batch.get("product", ""))
        candidate_orders[bid] = [
            o for o in orders
            if str(o.get("product", "")) == product
            and float(o.get("quantity", 0) or 0) > 0
        ]
        candidate_orders[bid].sort(
            key=lambda o: parse_dt(key(o, "latest_delivery", "latestDelivery", end_dt))
        )

    for batch in batches:
        bid = str(batch.get("id"))
        qty = int(round(float(batch.get("quantity", 0) or 0) * SCALE))
        if qty <= 0:
            infeasible_reasons[bid] = ["批次数量必须大于0"]
            continue

        expected_dt = parse_dt(key(batch, "expected_inbound", "expectedInbound", start_dt))
        lower_dt = max(expected_dt, start_dt)
        lower = max(0, int((lower_dt - start_dt).total_seconds() // 60))

        # Occupancy is an explicit B-01 storage/processing window. It is deliberately
        # kept at the current 24h-capped semantics so this revision does not invent new
        # database fields. The interpretation is documented in the response below.
        remaining_days = float(key(batch, "remaining_shelf_days", "remainingShelfDays", 1) or 1)
        max_storage_days = float(key(batch, "max_storage_days", "maxStorageDays", remaining_days) or remaining_days)
        storage_hours = max(1.0, min(24.0, remaining_days * 24.0, max_storage_days * 24.0))
        duration = max(60, int(round(storage_hours * 60)))

        # Without an order allocation, the batch only needs to fit inside the planning
        # horizon. An order's latestDelivery becomes a hard upper bound only when the
        # batch actually allocates quantity to that order. This prevents unrelated
        # orders from unnecessarily shortening warehouse occupancy windows.
        latest_start = horizon_minutes - duration
        if latest_start < lower:
            infeasible_reasons[bid] = [
                "真实到货时间晚于排程窗口，批次无法在 planningEnd 前完成冷间作业"
            ]
            continue

        eligible_rooms = eligible_rooms_for_batch(batch, rooms)
        if not eligible_rooms:
            infeasible_reasons[bid] = [
                "没有满足设备状态、容量、温区、存储类型和商品/品类要求的冷间"
            ]
            continue

        start_var = model.NewIntVar(lower, latest_start, f"start_{bid}")
        end_var = model.NewIntVar(lower + duration, horizon_minutes, f"end_{bid}")
        model.Add(end_var == start_var + duration)

        room_assignments: dict[str, Any] = {}
        eligible_literals = []
        for room in eligible_rooms:
            rid = str(room.get("id"))
            present = model.NewBoolVar(f"assign_{bid}_{rid}")
            room_assignments[rid] = present
            eligible_literals.append(present)
            interval = model.NewOptionalIntervalVar(
                start_var, duration, end_var, present, f"interval_{bid}_{rid}"
            )
            room_intervals[rid].append(interval)
            room_demands[rid].append(qty)
        model.AddExactlyOne(eligible_literals)

        order_allocations: dict[str, Any] = {}
        order_used: dict[str, Any] = {}
        for order in candidate_orders[bid]:
            oid = str(order.get("id"))
            order_qty = int(round(float(order.get("quantity", 0) or 0) * SCALE))
            q = model.NewIntVar(0, min(qty, order_qty), f"alloc_{bid}_{oid}")
            used = model.NewBoolVar(f"order_used_{bid}_{oid}")
            order_allocations[oid] = q
            order_used[oid] = used
            model.Add(q > 0).OnlyEnforceIf(used)
            model.Add(q == 0).OnlyEnforceIf(used.Not())
            order_deadline = int((parse_dt(key(order, "latest_delivery", "latestDelivery", end_dt)) - start_dt).total_seconds() // 60)
            model.Add(end_var <= order_deadline).OnlyEnforceIf(used)

        if order_allocations:
            model.Add(sum(order_allocations.values()) <= qty)

        batch_vars[bid] = {
            "batch": batch,
            "start": start_var,
            "end": end_var,
            "duration": duration,
            "roomAssignments": room_assignments,
            "orderAllocations": order_allocations,
            "orderUsed": order_used,
            "orders": candidate_orders[bid],
        }

    if infeasible_reasons:
        return {
            "status": "INFEASIBLE", "solver": "OR-Tools CP-SAT", "solverStatus": "INFEASIBLE_PRECHECK",
            "assignments": [], "utilization": 0.0, "fulfillment": 0.0,
            "onTimeInbound": 0.0, "totalCost": 0.0, "transportCost": 0.0,
            "highRiskCount": 0, "changedCount": 0,
            "unassignedBatchCount": len(infeasible_reasons),
            "infeasibleReasons": infeasible_reasons,
            "message": "存在无法满足硬约束的批次，未生成可执行方案",
        }

    for room in rooms:
        rid = str(room.get("id"))
        cap = int(round(float(key(room, "capacity", "capacity", 0) or 0)))
        used = int(round(float(key(room, "used_capacity", "usedCapacity", 0) or 0)))
        available = max(0, cap - used)
        if room_intervals[rid]:
            model.AddCumulative(room_intervals[rid], room_demands[rid], available)

    # Pairwise room sequencing with cleaning/switching gap.
    for room in rooms:
        rid = str(room.get("id"))
        gap_minutes = int(round((
            float(key(room, "cleaning_hours", "cleaningHours", 2) or 2)
            + float(key(room, "switch_hours", "switchHours", 1) or 1)
        ) * 60))
        candidates = []
        for bid, vars_ in batch_vars.items():
            if rid in vars_["roomAssignments"]:
                candidates.append((bid, vars_["roomAssignments"][rid], vars_["start"], vars_["end"]))
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                bid_i, ai, si, ei = candidates[i]
                bid_j, aj, sj, ej = candidates[j]
                before = model.NewBoolVar(f"order_{rid}_{i}_{j}_before")
                after = model.NewBoolVar(f"order_{rid}_{i}_{j}_after")
                model.Add(before + after == 1).OnlyEnforceIf([ai, aj])
                model.Add(before == 0).OnlyEnforceIf(ai.Not())
                model.Add(before == 0).OnlyEnforceIf(aj.Not())
                model.Add(after == 0).OnlyEnforceIf(ai.Not())
                model.Add(after == 0).OnlyEnforceIf(aj.Not())
                model.Add(ei + gap_minutes <= sj).OnlyEnforceIf(before)
                model.Add(ej + gap_minutes <= si).OnlyEnforceIf(after)

    # Order demand constraints: a real order can be split across multiple batches,
    # but total allocation cannot exceed its demand.
    order_allocation_vars: dict[str, list[Any]] = {str(o.get("id")): [] for o in orders}
    for vars_ in batch_vars.values():
        for oid, var in vars_["orderAllocations"].items():
            order_allocation_vars.setdefault(oid, []).append(var)
    for order in orders:
        oid = str(order.get("id"))
        demand = int(round(float(order.get("quantity", 0) or 0) * SCALE))
        terms = order_allocation_vars.get(oid, [])
        if terms:
            total_alloc = sum(terms)
            if require_full_order_fulfillment:
                model.Add(total_alloc == demand)
            else:
                model.Add(total_alloc <= demand)
        elif require_full_order_fulfillment and demand > 0:
            infeasible_reasons.setdefault(f"order:{oid}", []).append("订单没有任何可匹配批次，无法满足全量需求")

    if infeasible_reasons:
        return {
            "status": "INFEASIBLE", "solver": "OR-Tools CP-SAT", "solverStatus": "INFEASIBLE_PRECHECK",
            "assignments": [], "utilization": 0.0, "fulfillment": 0.0,
            "onTimeInbound": 0.0, "totalCost": 0.0, "transportCost": 0.0,
            "highRiskCount": 0, "changedCount": 0,
            "unassignedBatchCount": len([k for k in infeasible_reasons if not k.startswith("order:")]),
            "infeasibleReasons": infeasible_reasons,
            "message": "存在无法满足硬约束的批次或订单，未生成可执行方案",
        }

    # Multi-objective as one weighted integer objective:
    # 1) maximize order fulfillment; 2) minimize shelf/quality risk exposure;
    # 3) minimize storage cost; 4) prefer earlier inbound.
    total_order_qty = int(round(sum(float(o.get("quantity", 0) or 0) for o in orders) * SCALE))
    fulfillment_terms = [var for vars_ in batch_vars.values() for var in vars_["orderAllocations"].values()]
    fulfilled_total = sum(fulfillment_terms) if fulfillment_terms else 0
    objective_terms = []
    if total_order_qty > 0 and fulfillment_terms:
        objective_terms.append(-1000000 * fulfilled_total)

    for bid, vars_ in batch_vars.items():
        batch = vars_["batch"]
        remaining_shelf = float(key(batch, "remaining_shelf_days", "remainingShelfDays", 99) or 99)
        risk_penalty = 3 if remaining_shelf < 2 else (1 if remaining_shelf < 4 else 0)
        if risk_penalty:
            objective_terms.append(risk_penalty * vars_["duration"])
        objective_terms.append(vars_["start"] * 10)
        for rid, present in vars_["roomAssignments"].items():
            room = next(r for r in rooms if str(r.get("id")) == rid)
            cost = int(round(float(key(room, "cost_per_ton_hour", "costPerTonHour", 1.0) or 1.0) * 100))
            qty = max(1, int(round(float(batch.get("quantity", 0) or 0))))
            objective_terms.append(present * cost * max(1, vars_["duration"] // 60) * qty)
    model.Minimize(sum(objective_terms) if objective_terms else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.num_search_workers = min(8, os.cpu_count() or 1)
    status = solver.Solve(model)
    status_name = solver.StatusName(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": "INFEASIBLE" if status == cp_model.INFEASIBLE else status_name,
            "solver": "OR-Tools CP-SAT", "solverStatus": status_name,
            "assignments": [], "utilization": 0.0, "fulfillment": 0.0,
            "onTimeInbound": 0.0, "totalCost": 0.0, "transportCost": 0.0,
            "highRiskCount": 0, "changedCount": 0, "unassignedBatchCount": len(batches),
            "message": "OR-Tools 未找到满足全部硬约束的方案",
        }

    assignments = []
    total_capacity = sum(float(key(r, "capacity", "capacity", 0) or 0) for r in rooms) or 1.0
    baseline_used = sum(float(key(r, "used_capacity", "usedCapacity", 0) or 0) for r in rooms)
    scheduled_qty = 0.0
    total_cost = 0.0
    high_risk = 0
    matched_order_qty = 0.0

    order_fulfilled: dict[str, float] = {str(o.get("id")): 0.0 for o in orders}
    order_demand: dict[str, float] = {str(o.get("id")): float(o.get("quantity", 0) or 0) for o in orders}

    for bid, vars_ in batch_vars.items():
        selected_rid = next(rid for rid, present in vars_["roomAssignments"].items() if solver.Value(present) == 1)
        room = next(r for r in rooms if str(r.get("id")) == selected_rid)
        batch = vars_["batch"]
        start_value = start_dt + timedelta(minutes=solver.Value(vars_["start"]))
        end_value = start_dt + timedelta(minutes=solver.Value(vars_["end"]))
        qty = float(batch.get("quantity", 0) or 0)
        scheduled_qty += qty
        duration_hours = vars_["duration"] / 60.0
        room_cost = float(key(room, "cost_per_ton_hour", "costPerTonHour", 1) or 1) * qty * duration_hours
        total_cost += room_cost

        allocations = []
        for order in vars_["orders"]:
            oid = str(order.get("id"))
            q = float(solver.Value(vars_["orderAllocations"][oid])) / SCALE
            if q <= 0:
                continue
            latest_dt = parse_dt(key(order, "latest_delivery", "latestDelivery", end_dt))
            allocations.append({
                "orderId": int(order["id"]),
                "orderCode": order.get("orderCode"),
                "quantity": q,
                "latestDelivery": latest_dt.isoformat(timespec="minutes"),
            })
            order_fulfilled[oid] += q
            matched_order_qty += q

        primary = allocations[0] if allocations else None
        remaining_shelf = float(key(batch, "remaining_shelf_days", "remainingShelfDays", 99) or 99)
        risk = "HIGH" if remaining_shelf < 2 else ("MEDIUM" if remaining_shelf < 4 else "LOW")
        if risk == "HIGH":
            high_risk += 1

        checks = {
            "capacity": float(key(room, "used_capacity", "usedCapacity", 0) or 0) + qty <= float(key(room, "capacity", "capacity", 0) or 0),
            "temperature": room_matches_batch(room, batch),
            "productCategory": room_matches_batch(room, batch),
            "inboundWindow": start_value >= parse_dt(key(batch, "expected_inbound", "expectedInbound", start_dt)),
            "orderQuantity": sum(a["quantity"] for a in allocations) <= qty + 1e-9,
            "deliveryWindow": all(
                end_value <= parse_dt(a["latestDelivery"]) for a in allocations
            ),
        }

        assignments.append({
            "batchId": int(batch["id"]),
            "batchCode": batch.get("batchCode"),
            "product": batch.get("product"),
            "category": batch.get("category"),
            "coldRoomId": int(room["id"]),
            "coldRoomCode": room.get("roomCode"),
            "orderId": primary["orderId"] if primary else None,
            "orderCode": primary["orderCode"] if primary else None,
            "orderAllocations": allocations,
            "vehicleId": None,
            "routeId": None,
            "plannedInbound": start_value.isoformat(timespec="minutes"),
            "plannedOutbound": end_value.isoformat(timespec="minutes"),
            "allocatedQuantity": qty,
            "allocatedToOrderQuantity": round(sum(a["quantity"] for a in allocations), 3),
            "storageCost": round(room_cost, 2),
            "transportCost": 0.0,
            "qualityRisk": risk,
            "feasible": all(checks.values()),
            "constraintChecks": checks,
            "changeNote": "OR-Tools CP-SAT 冷间排程 V1.2：批次-订单分配量进入求解，结果独立校验",
        })

    fulfillment = 100.0 if not order_demand else min(
        100.0,
        matched_order_qty / (sum(order_demand.values()) or 1.0) * 100.0,
    )
    utilization = min(100.0, ((baseline_used + scheduled_qty) / total_capacity) * 100.0)
    inbound_checks = [x["constraintChecks"]["inboundWindow"] for x in assignments]

    result = {
        "status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
        "solver": "OR-Tools CP-SAT",
        "solverStatus": status_name,
        "objectiveValue": float(solver.ObjectiveValue()),
        "wallTimeSeconds": round(solver.WallTime(), 4),
        "planningStart": start_dt.isoformat(timespec="minutes"),
        "planningEnd": end_dt.isoformat(timespec="minutes"),
        "objective": "MAX_FULFILLMENT_THEN_RISK_COST_TIME",
        "requireFullOrderFulfillment": require_full_order_fulfillment,
        "assignments": assignments,
        "orderSummary": [
            {
                "orderId": int(o["id"]),
                "orderCode": o.get("orderCode"),
                "demand": float(o.get("quantity", 0) or 0),
                "allocated": round(order_fulfilled.get(str(o.get("id")), 0.0), 3),
                "remaining": round(max(0.0, float(o.get("quantity", 0) or 0) - order_fulfilled.get(str(o.get("id")), 0.0)), 3),
                "fulfillmentRate": round(
                    100.0 * order_fulfilled.get(str(o.get("id")), 0.0) / (float(o.get("quantity", 0) or 0) or 1.0),
                    2,
                ),
            }
            for o in orders
        ],
        "utilization": round(utilization, 2),
        "fulfillment": round(fulfillment, 2),
        "onTimeInbound": round(100.0 * sum(bool(x) for x in inbound_checks) / (len(inbound_checks) or 1), 2),
        "totalCost": round(total_cost, 2),
        "transportCost": 0.0,
        "highRiskCount": high_risk,
        "changedCount": 0,
        "unassignedBatchCount": 0,
        "message": "已由 OR-Tools CP-SAT 生成，并通过独立校验：容量、温区、品类、真实到货时间、订单分配量、订单截止时间及冷间时序",
    }

    valid, validation_errors = validate_schedule_solution(result, data)
    result["validation"] = {
        "passed": valid,
        "errorCount": sum(len(v) for v in validation_errors.values()),
        "errors": validation_errors,
    }
    if not valid:
        result["status"] = "INVALID"
        result["solverStatus"] = f"{status_name}_VALIDATION_FAILED"
        result["message"] = "OR-Tools 给出了候选方案，但独立结果校验未通过，已拒绝作为可执行方案"

    return result


@app.get("/api/health", summary="健康检查", description="检查算法服务、MySQL smart_warehouse 数据库和 OR-Tools 是否可用。")
def health():
    try:
        with db_cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS db")
            db_name = cursor.fetchone()["db"]
        try:
            import ortools  # noqa: F401
            solver = "OR-Tools CP-SAT available"
        except Exception:
            solver = "OR-Tools CP-SAT unavailable"
        return {"status": "ok", "database": db_name, "solver": solver}
    except Exception as ex:
        raise HTTPException(status_code=503, detail=f"MySQL smart_warehouse 不可用: {ex}")


@app.get("/api/schedule/data", summary="读取调度数据", description="从现有 smart_warehouse 数据库读取批次、订单、冷间资源，以及演示车辆和路线。")
def schedule_data():
    try:
        return load_dataset()
    except Exception as ex:
        raise HTTPException(status_code=503, detail=f"读取 smart_warehouse 失败: {ex}")


@app.post("/api/schedule/solve", summary="执行智能冷间排程", description="使用 OR-Tools CP-SAT 根据容量、温区、品类、到货时间、订单截止时间和冷间时序约束生成调度方案。")
def solve(data: dict | None = None):
    try:
        normalized = normalize_query_data(dict(data or {}))
        if not normalized.get("batches") or not normalized.get("coldRooms"):
            raise HTTPException(status_code=400, detail="当前 smart_warehouse 中没有可调度批次或冷库资源")
        result = solve_with_ortools(normalized)
        # Return the resolved dataset as well so the existing Spring Boot adapter
        # can keep the current frontend response shape without any new DB tables.
        result["batches"] = normalized["batches"]
        result["orders"] = normalized["orders"]
        result["coldRooms"] = normalized["coldRooms"]
        result["vehicles"] = normalized["vehicles"]
        result["routes"] = normalized["routes"]
        return result
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(status_code=503, detail=f"调度读取/计算失败: {ex}")


@app.post("/api/schedule/reschedule", summary="执行异常重调度", description="根据受影响批次对当前调度方案重新求解。")
def reschedule(data: dict):
    try:
        normalized = normalize_query_data(dict(data or {}))
        affected = {str(x) for x in normalized.get("affectedBatchIds", [])}
        result = solve_with_ortools(normalized)
        fixed = [x for x in normalized.get("originalAssignments", []) if str(x.get("batchId")) not in affected]
        result["assignments"] = [x for x in result.get("assignments", []) if str(x.get("batchId")) in affected] + fixed
        result["changedCount"] = len(affected)
        return result
    except Exception as ex:
        raise HTTPException(status_code=503, detail=f"重调度失败: {ex}")
