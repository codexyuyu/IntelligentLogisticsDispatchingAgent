"""Repeatable master-data seed import (P04-02).

The importer validates every payload with the same boundary DTOs the API uses, inserts in FK
order inside one transaction and never overwrites an existing row. A rejected fixture reports
the row and leaves the database unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from pydantic import ValidationError

from logistics_backend.persistence.planning_models import travel_matrices
from logistics_backend.persistence.resource_models import TABLES
from logistics_backend.persistence.uow import UnitOfWork
from logistics_contracts import entities
from logistics_contracts.planning import TravelMatrixDTO

ROOT = Path(__file__).resolve().parents[5]
SCENARIOS = ROOT / "data/scenarios"
DTO = {
    "warehouses": ("warehouse", entities.WarehouseDTO),
    "zones": ("zone", entities.ZoneDTO),
    "locations": ("location", entities.StorageLocationDTO),
    "docks": ("dock", entities.DockDTO),
    "workers": ("worker", entities.WorkerDTO),
    "equipment": ("equipment", entities.EquipmentDTO),
    "drivers": ("driver", entities.DriverDTO),
    "vehicles": ("vehicle", entities.VehicleDTO),
    "orders": ("order", entities.OrderDTO),
    "cargo": ("cargo", entities.CargoDTO),
}
ORDER = ("warehouses", "drivers", "zones", "locations", "docks", "workers", "equipment",
         "vehicles", "orders", "cargo")


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _values(kind: str, item: dict, scope_id: UUID):
    table = TABLES[kind]
    payload = dict(item)
    values = {
        "id": UUID(item["id"]), "scope_id": scope_id, "status": item["status"],
        "created_at": _dt(item["created_at"]), "updated_at": _dt(item["updated_at"]),
        "created_by": UUID(item["created_by"]), "row_version": item["row_version"],
        "schema_version": item["schema_version"], "payload": payload,
    }
    for column in table.c:
        name = column.name
        if name in values:
            continue
        if name in payload:
            value = payload[name]
            if name.endswith("_id") or name in ("id", "driver_id"):
                value = UUID(value) if value is not None else None
            values[name] = value
    missing = [column.name for column in table.c if column.name not in values]
    if missing:
        raise ValueError(f"{kind} fixture is missing columns {missing}")
    return values


def seed(scenario: str, database_url: str) -> dict:
    path = SCENARIOS / f"{scenario}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scope_id = UUID(data["scope_id"])
    if data.get("schema_version") != "2.0.0":
        raise ValueError("scenario schema_version must be 2.0.0")
    for key, (_, dto) in DTO.items():
        for index, item in enumerate(data.get(key, ())):
            try:
                dto.model_validate(item).to_domain()
            except (ValidationError, ValueError) as exc:
                raise ValueError(f"{key}[{index}] is invalid: {exc}") from exc
    for matrix in data.get("matrices", ()):
        TravelMatrixDTO.model_validate(matrix["payload"]).to_domain()
    engine = create_engine(database_url, pool_pre_ping=True)
    counts = {}
    try:
        with UnitOfWork(engine) as uow:
            for key in ORDER:
                rows = data.get(key, ())
                kind = DTO[key][0]
                table = TABLES[kind]
                before = uow.connection.execute(select(func.count()).select_from(table)
                    .where(table.c.scope_id == scope_id)).scalar_one()
                for item in rows:
                    uow.connection.execute(
                        pg_insert(table).values(**_values(kind, item, scope_id))
                        .on_conflict_do_nothing())
                after = uow.connection.execute(select(func.count()).select_from(table)
                    .where(table.c.scope_id == scope_id)).scalar_one()
                counts[key] = {"input": len(rows), "inserted": after - before}
            matrix_rows = data.get("matrices", ())
            before = uow.connection.execute(select(func.count()).select_from(travel_matrices)
                .where(travel_matrices.c.scope_id == scope_id)).scalar_one()
            for matrix in matrix_rows:
                uow.connection.execute(pg_insert(travel_matrices).values(
                    id=UUID(matrix["id"]), version=matrix["version"], scope_id=scope_id,
                    hash=matrix["hash"], created_at=_dt(matrix["created_at"]),
                    payload=matrix["payload"]).on_conflict_do_nothing())
            after = uow.connection.execute(select(func.count()).select_from(travel_matrices)
                .where(travel_matrices.c.scope_id == scope_id)).scalar_one()
            counts["matrices"] = {"input": len(matrix_rows), "inserted": after - before}
        return {"scenario": scenario, "scope_id": str(scope_id), "counts": counts}
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a generated scenario into PostgreSQL")
    parser.add_argument("--scenario", default="tiny_master")
    parser.add_argument("--database-url-env", default="LOGISTICS_DATABASE_URL")
    args = parser.parse_args()
    url = os.environ.get(args.database_url_env)
    if not url:
        raise SystemExit(f"{args.database_url_env} is not set; refusing to guess a database")
    result = seed(args.scenario, url)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
