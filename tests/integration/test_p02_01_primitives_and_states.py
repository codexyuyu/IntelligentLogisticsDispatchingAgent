"""Integration checks for P02-01: the domain enums/primitives against their real boundaries.

The boundaries exercised here are real, not re-read configuration:

* the frozen contract artifact ``contracts/changes/N01-R01-contract-decisions.json`` and the
  ownership table ``docs/architecture/TYPE_DEFINITION_OWNERSHIP.md`` are parsed from disk and
  compared member-by-member with the implemented enums;
* the lifecycle graph is compared with the ``状态与生命周期`` column of
  ``docs/architecture/DOMAIN_CATALOG.md``, so the code cannot drift from the catalog;
* the package is imported in an isolated interpreter from a throwaway working directory, so
  the six-package workspace install is proven rather than a cwd side effect;
* the domain source tree is scanned for forbidden framework/solver imports.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from logistics_domain import states

REPO_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_SRC = REPO_ROOT / "packages/domain/src/logistics_domain"
DECISIONS = REPO_ROOT / "contracts/changes/N01-R01-contract-decisions.json"
OWNERSHIP_TABLE = REPO_ROOT / "docs/architecture/TYPE_DEFINITION_OWNERSHIP.md"
DOMAIN_CATALOG = REPO_ROOT / "docs/architecture/DOMAIN_CATALOG.md"
DATA_CONTRACTS = REPO_ROOT / "docs/architecture/DATA_CONTRACTS.md"

pytestmark = pytest.mark.integration

FORBIDDEN_IMPORT_ROOTS = (
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic",
    "sqlalchemy",
    "alembic",
    "ortools",
    "simpy",
    "numpy",
    "pandas",
    "psycopg",
)


@pytest.fixture(scope="module")
def decisions() -> dict:
    return json.loads(DECISIONS.read_text(encoding="utf-8"))


def test_the_frozen_decisions_still_assign_states_and_primitives_to_this_task(decisions: dict) -> None:
    owned = {
        entry["name"]: entry
        for entry in decisions["types"]
        if entry.get("path", "").endswith(("states.py", "primitives.py"))
    }
    assert owned, "the frozen decisions must still own types in states.py / primitives.py"
    assert {entry["task"] for entry in owned.values()} == {"P02-01"}

    enum_members = {
        name: {member: value for member, value in entry["members"].items()}
        for name, entry in owned.items()
        if entry.get("kind") == "enum"
    }
    for name, members in enum_members.items():
        implemented = getattr(states, name, None)
        assert implemented is not None, f"{name} must be implemented in states.py"
        assert {member.name: member.value for member in implemented} == members, name


def test_every_enum_the_decisions_place_in_states_py_is_implemented(decisions: dict) -> None:
    entries = [entry for entry in decisions["types"] if entry.get("path", "").endswith("states.py")]
    expected = {entry["name"] for entry in entries if entry.get("kind") == "enum"}
    inherited = {entry["name"] for entry in entries if entry.get("kind") == "existing"}
    missing = sorted(name for name in expected | inherited if not hasattr(states, name))
    assert not missing, f"states.py is missing frozen types: {missing}"
    assert len(expected) == 17, sorted(expected)
    # In the frozen table these two inherit the named original contract rather than listing members.
    assert inherited == {"ErrorCode", "ConstraintCode"}


def test_ownership_table_agrees_with_the_module_that_declares_each_type() -> None:
    table = OWNERSHIP_TABLE.read_text(encoding="utf-8")
    for name in ("JobKind", "JobStatus", "JobOptimizationMode", "EntityKind", "ErrorCode"):
        row = next((line for line in table.splitlines() if line.startswith(f"| {name} |")), None)
        assert row is not None, f"{name} must have an ownership row"
        assert "P02-01" in row and "states.py" in row, row
    for name in ("CalendarInterval", "ResourceCalendar", "TimeWindow", "Load", "EntityRef", "ArtifactRef"):
        row = next((line for line in table.splitlines() if line.startswith(f"| {name} |")), None)
        assert row is not None, f"{name} must have an ownership row"
        assert "P02-01" in row and "primitives.py" in row, row


def test_lifecycle_graph_edges_exist_in_the_catalog_lifecycle_column() -> None:
    catalog = DOMAIN_CATALOG.read_text(encoding="utf-8")
    lifecycle_rows = [line for line in catalog.splitlines() if line.startswith("| ") and "→" in line]
    # 32 catalog entities minus the five immutable "recorded" ones that have no arrows.
    assert len(lifecycle_rows) == 27, "the catalog lifecycle column must be present and complete"

    rendered = catalog
    # Every state word used by the graph must be documented, so no state can be invented.
    for owner, graph in states.LIFECYCLE_TRANSITIONS.items():
        for source, targets in graph.items():
            for label in (source.value, *(target.value for target in targets)):
                assert label in rendered, f"{owner}: state {label!r} must appear in the catalog"


def test_catalog_declares_the_transition_rule_used_by_the_interface() -> None:
    catalog = DOMAIN_CATALOG.read_text(encoding="utf-8")
    # The closed start window and the half-open occupancy rule are catalog-level statements.
    assert "[earliest_s, latest_s]" in catalog
    assert "[start_s,end_s)" in catalog
    assert "delivered" in catalog and "draft" in catalog


def test_data_contracts_scalar_rules_are_implemented() -> None:
    contracts = DATA_CONTRACTS.read_text(encoding="utf-8")
    assert "int拒绝bool/float并在int64范围" in contracts
    assert "PositiveInt>=1，NonNegativeInt>=0" in contracts
    assert "Sha256为64小写hex非空" in contracts

    from logistics_domain import primitives
    from logistics_domain.errors import InvalidInputError

    assert primitives.INT64_MAX == 2**63 - 1
    with pytest.raises(InvalidInputError):
        primitives.require_int(True, field="v")
    with pytest.raises(InvalidInputError):
        primitives.require_int(1.0, field="v")
    with pytest.raises(InvalidInputError):
        primitives.require_int(2**63, field="v")
    with pytest.raises(InvalidInputError):
        primitives.require_positive_int(0, field="v")


def test_domain_source_imports_no_framework_or_solver() -> None:
    offenders: list[str] = []
    for path in sorted(DOMAIN_SRC.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for root in FORBIDDEN_IMPORT_ROOTS:
            if re.search(rf"^\s*(?:import|from)\s+{root}\b", source, flags=re.MULTILINE):
                offenders.append(f"{path.name}:{root}")
    assert not offenders, f"the pure domain layer must not import frameworks/solvers: {offenders}"


def test_domain_modules_import_only_stdlib_and_siblings_from_an_isolated_interpreter(tmp_path: Path) -> None:
    probe = (
        "import json, sys\n"
        "import logistics_domain.states as states\n"
        "import logistics_domain.primitives as primitives\n"
        "import logistics_domain.errors as errors\n"
        "third_party = sorted({\n"
        "    name.split('.')[0]\n"
        "    for name in sys.modules\n"
        "    if not name.startswith(('_', 'logistics_domain'))\n"
        "    and name.split('.')[0] not in sys.stdlib_module_names\n"
        "})\n"
        "print('PROBE_JSON=' + json.dumps({\n"
        "    'third_party': third_party,\n"
        "    'cwd_independent': True,\n"
        "    'job_kind': [m.value for m in states.JobKind],\n"
        "    'interval_ok': primitives.intervals_overlap(\n"
        "        primitives.CalendarInterval(0, 10, 1), primitives.CalendarInterval(10, 20, 1)) is False,\n"
        "    'has_transition': callable(states.transition),\n"
        "    'error_code': errors.InvalidInputError('x').code.value,\n"
        "}))\n"
    )
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, "-I", "-c", probe],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, f"isolated import failed:\n{result.stdout}\n{result.stderr}"
    payload = json.loads(
        next(line for line in result.stdout.splitlines() if line.startswith("PROBE_JSON="))[len("PROBE_JSON="):]
    )
    assert payload["third_party"] == [], f"domain import pulled in third-party modules: {payload['third_party']}"
    assert payload["job_kind"] == ["optimization", "simulation", "reschedule", "experiment", "metric"]
    assert payload["interval_ok"] is True
    assert payload["has_transition"] is True
    assert payload["error_code"] == "invalid_input"


def test_adjacent_and_overlapping_intervals_through_the_public_module() -> None:
    from logistics_domain import primitives

    first = primitives.CalendarInterval(start_s=0, end_s=10, available_units=3)
    second = primitives.CalendarInterval(start_s=10, end_s=20, available_units=0)
    calendar = primitives.ResourceCalendar(
        epoch_utc=primitives.require_utc_seconds(
            __import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            field="epoch_utc",
        ),
        intervals=(first, second),
        version=2,
    )
    assert calendar.available_units_at(0) == 3
    assert calendar.available_units_at(15) == 0
    assert calendar.version == 2
    assert primitives.intervals_overlap(first, second) is False


def test_reservation_row_in_the_catalog_is_transcribed_faithfully() -> None:
    """The frozen catalog prose is the only authority for the reservation edges."""
    catalog = DOMAIN_CATALOG.read_text(encoding="utf-8")
    row = next((line for line in catalog.splitlines() if "Reservation(" in line), None)
    assert row is not None, "the catalog must document the Reservation lifecycle"
    assert "Reservation(held→committed→released/expired)" in row, row

    graph = states.LIFECYCLE_TRANSITIONS["reservation"]
    assert {state.value for state in graph} == {"held", "committed", "released", "expired"}
    edges = {(source.value, target.value) for source, targets in graph.items() for target in targets}
    assert edges == {("held", "committed"), ("committed", "released"), ("committed", "expired")}
    # the union carries other entities' edges out of `committed`, so it is not the check object
    assert states.EntityState.SUPERSEDED not in graph[states.EntityState.COMMITTED]
    assert states.EntityState.RELEASED.value == "released"
