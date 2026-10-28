"""Export deterministic schemas from implemented DTOs and actual API routes."""
import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from logistics_contracts import (
    agents,
    coldchain,
    common,
    decision,
    entities,
    events,
    experiment,
    http,
    impact,
    integration,
    metrics,
    planning,
    reschedule,
    runtime,
    schedules,
    simulation,
    transport,
    validation,
    warehouse,
)

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_BASES = {"Body", "Patch", "Record", "Detail", "EntityDTO", "PlanningEntityDTO", "Boundary"}

def export_contracts():
    models = {}
    for module in (coldchain, agents, common, decision, entities, events, experiment, http, impact, integration, metrics, planning, reschedule, runtime, schedules, simulation, transport, validation, warehouse):
        for name, value in vars(module).items():
            if (isinstance(value, type) and issubclass(value, BaseModel)
                    and value.__module__ == module.__name__ and name not in EXCLUDED_BASES):
                models[f"{module.__name__}.{name}"] = value.model_json_schema()
    return {"schema_version": "2.0.0", "schemas": models}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    from logistics_backend.bootstrap import schema_app
    artifacts = {"contracts/schemas.json": export_contracts(), "contracts/openapi.json": schema_app().openapi()}
    for name, value in artifacts.items():
        output = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_bytes() != output:
                raise SystemExit(f"schema differs: {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(output)

if __name__ == "__main__":
    main()
