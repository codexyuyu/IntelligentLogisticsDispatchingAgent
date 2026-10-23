#!/usr/bin/env python
"""Ownership resolution and migration-governance check for the v1 monorepo.

Public entry point (task P01-03):

    resolve_owner(path: str) -> Literal["A", "B"]

Rules
-----
* Longest matching ``OWNERSHIP.json`` path prefix wins; the match is segment-aware, so
  ``packages/simulation`` matches ``packages/simulation/src/x.py`` but never
  ``packages/simulation_extra/x.py``.
* An unlisted relative path falls back to ``default_owner`` (A).
* ``packages/optimization`` and ``packages/simulation`` (plus the matching solver /
  simulation test, data and benchmark directories) belong to B; everything else to A.
* An absolute path, a Windows drive/UNC path, or any path escaping the repository root is
  rejected instead of being guessed.
* ``demo/`` and ``demos/`` are the read-only teaching baseline: uniformly A-owned, and no
  v1 package may import them.

Legacy conversion is deliberately strict:

* ``convert_legacy_status`` follows only the explicit table in
  ``docs/architecture/LEGACY_ADAPTATION.md`` and **rejects** anything unmapped
  (``LegacyConversionError``) instead of guessing a "close enough" v1 value;
* ``convert_legacy_minutes`` converts the v0.1 minute unit to v1 integer seconds and returns
  a ``LegacyConversion`` recording the legacy version, so the conversion is auditable.

Exit codes: 0 = all checks passed, 1 = violations found, 2 = usage/configuration error.

Usage:
    uv run python scripts/check_ownership.py [--root PATH] [--json] [--verbose]
    uv run python scripts/check_ownership.py --resolve packages/simulation/src/x.py
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = "1.0.0"
OWNER = Literal["A", "B"]
LEGACY_CONTRACT_VERSION = "0.1.0"
V1_CONTRACT_VERSION = "1.0.0"
CHECK_NAME = "ownership-and-migration"
MANIFEST_NAME = "OWNERSHIP.json"
LEGACY_OWNERSHIP_NAME = "demo/OWNERSHIP.json"
LEGACY_INVENTORY_NAME = "docs/architecture/BASELINE_INVENTORY.json"
LEGACY_ADAPTATION_NAME = "docs/architecture/LEGACY_ADAPTATION.md"

LEGACY_NAMESPACES = ("app", "demo", "demos")
# Directory names never scanned when auditing path coverage.
AUDIT_SKIP_DIRECTORIES = {
    ".venv", "node_modules", "__pycache__", ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    # harness/runtime scratch state, not project artifacts
    ".mimosa", ".uv-cache", ".workbuddy", ".workbuddy-ai", ".claude",
    # local independent clone of the R30-E baseline, not part of this workspace's code
    "merged",
}


@dataclass(frozen=True)
class LegacyConversion:
    """Result of an explicit v0.1 -> v1 conversion; carries the legacy version."""

    legacy_version: str
    target_version: str
    kind: str
    source_value: str
    target_value: str | None
    rule: str


class LegacyConversionError(ValueError):
    """Raised when a v0.1 value has no explicit v1 mapping (never guessed)."""

    def __init__(self, kind: str, value: str, known: tuple[str, ...]) -> None:
        self.kind = kind
        self.value = value
        self.known = known
        super().__init__(
            f"unmapped legacy {kind} status {value!r}: no explicit v0.1 -> v1 conversion is defined in "
            f"{LEGACY_ADAPTATION_NAME}; known v0.1 values are {list(known)}. "
            "Add a decided mapping instead of guessing."
        )


class OwnershipError(ValueError):
    """Raised when a path cannot be resolved to a repository-relative path."""


# ------------------------------------------------------------------- legacy statuses
#
# Vocabulary source: demo/backend/app/domain/states.py (v0.1, contract version 0.1.0).
# Target vocabulary source: docs/architecture/DATA_CONTRACTS.md (v1 SolveStatus / JobStatus),
# docs/architecture/DOMAIN_CATALOG.md (entity lifecycles) and PROJECT_MASTER_PLAN.md.
# A `None` target means the v0.1 value has no v1 equivalent and is intentionally dropped;
# it still requires an explicit entry so nothing disappears silently.

LEGACY_STATUS_TABLES: dict[str, dict[str, str | None]] = {
    "JobStatus": {
        "queued": "V1_JOB_STATUS:queued",
        "running": "V1_JOB_STATUS:running",
        "succeeded": "V1_JOB_STATUS:completed",
        "failed": "V1_JOB_STATUS:failed",
        "cancelled": "V1_JOB_STATUS:cancelled",
    },
    "SolveStatus": {
        "optimal": "V1_SOLVE_STATUS:OPTIMAL",
        "feasible": "V1_SOLVE_STATUS:FEASIBLE",
        "infeasible_proven": "V1_SOLVE_STATUS:INFEASIBLE",
        "no_solution_within_budget": "V1_SOLVE_STATUS:TIMEOUT",
        "invalid_input": "V1_SOLVE_STATUS:INVALID_INPUT",
        "model_invalid": "V1_SOLVE_STATUS:ERROR",
        "needs_clarification": "V1_SOLVE_STATUS:INVALID_INPUT",
        "unsupported": "V1_SOLVE_STATUS:INVALID_INPUT",
        "stale": None,
        "conflict": None,
    },
    "PlanStatus": {
        "draft": "V1_SCHEDULE_VERSION:validated-pending",
        "validated": "V1_SCHEDULE_VERSION:validated",
        "confirmed": "V1_SCHEDULE_VERSION:confirmed",
        "executing": "V1_SCHEDULE_VERSION:executing",
        "completed": "V1_SCHEDULE_VERSION:completed",
        "rejected": "V1_SCHEDULE_VERSION:rejected",
        "stale": "V1_SCHEDULE_VERSION:superseded",
        "superseded": "V1_SCHEDULE_VERSION:superseded",
    },
    "OperationStatus": {
        "pending": "V1_WAREHOUSE_TASK:pending",
        "running": "V1_WAREHOUSE_TASK:running",
        "interrupted": "V1_WAREHOUSE_TASK:interrupted",
        "completed": "V1_WAREHOUSE_TASK:completed",
        "cancelled": "V1_WAREHOUSE_TASK:cancelled",
        "paused": None,
    },
    "TemperatureZone": {
        "chilled": "V1_TEMPERATURE_ZONE:chilled",
        "frozen": "V1_TEMPERATURE_ZONE:frozen",
    },
    "EventType": {
        "departure_delayed": "V1_EVENT_KIND:departure-delay",
        "dock_unavailable": "V1_EVENT_KIND:warehouse-resource-unavailable",
        "cargo_quarantined": "V1_EVENT_KIND:cargo-incident",
        "weather_changed": "V1_EVENT_KIND:weather-change",
        "demand_changed": "V1_EVENT_KIND:demand-change",
    },
}

# v0.1 -> v1 value vocabulary that is NOT covered by the legacy table because it only
# exists in v1. Listed so the gap is explicit and testable rather than implied.
V1_ONLY_VALUES: dict[str, tuple[str, ...]] = {
    "SolveStatus": ("UNKNOWN", "CANCELLED"),
    "TemperatureZone": ("ambient",),
    "EventType": (
        "vehicle-breakdown",
        "delay",
        "traffic",
        "cargo-damage",
        "order-cancel",
        "demand-increase",
        "demand-decrease",
        "equipment-failure",
        "rescue-handoff",
    ),
}

LEGACY_ENUM_TABLE_VERSION_FIELD = "LEGACY_ENUM_TABLE_VERSION"


def _target_rule(kind: str, legacy_value: str, target: str | None) -> str:
    if target is None:
        return f"v0.1 {kind}.{legacy_value} 在 v1 没有对应值，按不迁移处理（不静默改写）"
    return f"v0.1 {kind}.{legacy_value} -> v1 {target.split(':', 1)[1]}"


def convert_legacy_status(kind: str, value: str) -> LegacyConversion:
    """Map one v0.1 status value to its v1 value, or reject it explicitly."""
    table = LEGACY_STATUS_TABLES.get(kind)
    if table is None:
        raise LegacyConversionError(kind, value, ())
    if value not in table:
        raise LegacyConversionError(kind, value, tuple(sorted(table)))
    target = table[value]
    return LegacyConversion(
        legacy_version=LEGACY_CONTRACT_VERSION,
        target_version=V1_CONTRACT_VERSION,
        kind=kind,
        source_value=value,
        target_value=target,
        rule=_target_rule(kind, value, target),
    )


def legacy_status_vocabulary(kind: str) -> tuple[str, ...]:
    table = LEGACY_STATUS_TABLES.get(kind)
    if table is None:
        raise LegacyConversionError(kind, "<vocabulary>", ())
    return tuple(table)


def convert_legacy_minutes(value: int, field: str = "duration") -> LegacyConversion:
    """Convert the v0.1 minute unit to v1 integer seconds (explicit, recorded)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer number of minutes, got {value!r}")
    if value < 0:
        raise ValueError(f"{field} must not be negative, got {value}")
    return LegacyConversion(
        legacy_version=LEGACY_CONTRACT_VERSION,
        target_version=V1_CONTRACT_VERSION,
        kind="Duration",
        source_value=str(value),
        target_value=str(value * 60),
        rule=f"v0.1 {field}={value} 分钟 -> v1 {value * 60} 秒（整数秒，向上不取整；记录旧版本 {LEGACY_CONTRACT_VERSION}）",
    )


# ------------------------------------------------------------------------ ownership


def normalize_repo_path(path: str) -> str:
    """Return a repository-relative posix path, or raise OwnershipError.

    Absolute paths, drive/UNC paths and paths that climb out of the repository are
    rejected: guessing an owner for a path outside the repository would silently widen an
    ownership rule.
    """
    if not isinstance(path, str) or not path.strip():
        raise OwnershipError(f"path must be a non-empty string, got {path!r}")
    raw = path.strip().replace("\\", "/")
    if raw.startswith("/") or raw.startswith("//"):
        raise OwnershipError(f"absolute path is not accepted: {path!r}")
    if len(raw) > 1 and raw[1] == ":":
        raise OwnershipError(f"drive-qualified path is not accepted: {path!r}")
    parts: list[str] = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise OwnershipError(f"path escapes the repository root: {path!r}")
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        raise OwnershipError(f"path does not identify a repository entry: {path!r}")
    return "/".join(parts)


def _prefix_matches(relative_path: str, prefix: str) -> bool:
    """Segment-aware prefix match: 'a/b' matches 'a/b' and 'a/b/c', never 'a/bc'."""
    if relative_path == prefix:
        return True
    return relative_path.startswith(prefix + "/")


def load_manifest(root: Path) -> dict:
    path = root / MANIFEST_NAME
    if not path.is_file():
        raise OwnershipError(f"{MANIFEST_NAME} not found under {root}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for key in ("rule", "default_owner", "owners", "paths"):
        if key not in manifest:
            raise OwnershipError(f"{MANIFEST_NAME} is missing required key {key!r}")
    unknown = {prefix: owner for prefix, owner in manifest["paths"].items() if owner not in manifest["owners"]}
    if unknown:
        raise OwnershipError(f"{MANIFEST_NAME} declares undefined owners: {unknown}")
    if manifest["default_owner"] not in manifest["owners"]:
        raise OwnershipError(f"{MANIFEST_NAME} default_owner {manifest['default_owner']!r} is not in owners")
    return manifest


def resolve_owner(path: str, root: Path | None = None) -> OWNER:
    """Resolve the owner of a repository path by longest matching prefix."""
    manifest = load_manifest(root or Path(__file__).resolve().parents[1])
    relative = normalize_repo_path(path)
    best_prefix = ""
    best_owner = manifest["default_owner"]
    for prefix, owner in manifest["paths"].items():
        candidate = prefix.rstrip("/")
        if _prefix_matches(relative, candidate) and len(candidate) > len(best_prefix):
            best_prefix = candidate
            best_owner = owner
    return best_owner


def resolve_owner_detail(path: str, root: Path | None = None) -> dict:
    """Structured form of :func:`resolve_owner` for evidence and CLI output."""
    manifest = load_manifest(root or Path(__file__).resolve().parents[1])
    relative = normalize_repo_path(path)
    best = ""
    owner = manifest["default_owner"]
    for prefix, candidate_owner in manifest["paths"].items():
        candidate = prefix.rstrip("/")
        if _prefix_matches(relative, candidate) and len(candidate) > len(best):
            best, owner = candidate, candidate_owner
    return {
        "path": relative,
        "owner": owner,
        "matched_prefix": best or None,
        "used_default_owner": best == "",
        "default_owner": manifest["default_owner"],
        "rule": manifest["rule"],
    }


# ---------------------------------------------------------------------------- checks


def audit_path_coverage(root: Path, manifest: dict) -> dict:
    """Every tracked real file must resolve deterministically; report default fallbacks."""
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if AUDIT_SKIP_DIRECTORIES & set(path.parts):
            continue
        files.append(relative)
    fallbacks = []
    owners: dict[str, int] = {owner: 0 for owner in manifest["owners"]}
    for relative in files:
        detail = resolve_owner_detail(relative, root)
        owners[detail["owner"]] = owners.get(detail["owner"], 0) + 1
        if detail["used_default_owner"]:
            fallbacks.append(relative)
    return {
        "files_scanned": len(files),
        "files_per_owner": owners,
        "default_owner_fallbacks": sorted(fallbacks),
    }


def check_legacy_imports(root: Path) -> list[dict]:
    """No v1 package may import the v0.1 ``app.*`` namespace or the teaching demos."""
    offenders: list[dict] = []
    for source_root in sorted(root.glob("packages/*/src")) + sorted(root.glob("apps/*/src")):
        for path in sorted(source_root.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                offenders.append({
                    "path": path.relative_to(root).as_posix(),
                    "line": exc.lineno or 0,
                    "imported": "<syntax error>",
                })
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    if name.split(".", 1)[0] in LEGACY_NAMESPACES:
                        offenders.append({
                            "path": path.relative_to(root).as_posix(),
                            "line": node.lineno,
                            "imported": name,
                        })
    return offenders


def check_legacy_mapping_coverage(root: Path) -> list[str]:
    """Every B-owned legacy asset registered for B must appear in the adaptation document."""
    problems: list[str] = []
    inventory_path = root / LEGACY_INVENTORY_NAME
    doc_path = root / LEGACY_ADAPTATION_NAME
    if not inventory_path.is_file():
        return [f"{LEGACY_INVENTORY_NAME} is missing; legacy coverage cannot be checked"]
    if not doc_path.is_file():
        return [f"{LEGACY_ADAPTATION_NAME} is missing; the legacy conversion table is required"]
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    document = doc_path.read_text(encoding="utf-8")
    for entry in inventory.get("entries", []):
        source = entry["source_path"]
        owner = resolve_owner(source, root)
        if owner == "B" and source not in document:
            problems.append(f"B-owned legacy asset {source} is not mentioned in {LEGACY_ADAPTATION_NAME}")
    return problems


def check_contract_change_entry(root: Path) -> list[str]:
    """A contract change must state inputs/outputs and the migration order before coding."""
    problems: list[str] = []
    path = root / "contracts/changes/README.md"
    if not path.is_file():
        return ["contracts/changes/README.md is missing; contract changes have no acceptance entry"]
    text = path.read_text(encoding="utf-8")
    required = ("输入影响", "输出影响", "迁移顺序", "生成物", "version_id", "schema_version")
    for token in required:
        if token not in text:
            problems.append(f"contracts/changes/README.md does not document {token!r} as a required field")
    return problems


def run_checks(root: Path) -> dict:
    try:
        manifest = load_manifest(root)
    except (OwnershipError, json.JSONDecodeError) as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "check": CHECK_NAME,
            "root": str(root),
            "passed": False,
            "violation_count": 1,
            "violations": [{"code": "OWN-CONFIG", "detail": str(exc)}],
        }
    violations: list[dict] = []
    pending: list[dict] = []
    coverage = audit_path_coverage(root, manifest)
    for offender in check_legacy_imports(root):
        violations.append({
            "code": "OWN-LEGACY-IMPORT",
            "detail": f"{offender['path']}:{offender['line']} imports legacy namespace {offender['imported']!r}",
        })
    for problem in check_legacy_mapping_coverage(root):
        violations.append({"code": "OWN-LEGACY-COVERAGE", "detail": problem})
    for problem in check_contract_change_entry(root):
        violations.append({"code": "OWN-CONTRACT-CHANGE", "detail": problem})
    # Declaring an owner for a path that does not exist yet is legitimate scope
    # documentation (B's transport/simulation surface lands in later phases); it is
    # reported as pending work, not as a failure. A *declared* B prefix that appears only
    # as a leftover empty shell would still be visible in the coverage report.
    for prefix, owner in manifest["paths"].items():
        if owner != "B":
            continue
        candidate = prefix.rstrip("/")
        if candidate.split("/")[0] not in {"packages", "tests", "data", "benchmarks"}:
            continue
        if not (root / candidate).exists():
            pending.append({
                "code": "OWN-B-PATH-PENDING",
                "detail": f"B-owned prefix {prefix!r} is declared but not created yet (later phase delivers it)",
            })
    return {
        "schema_version": SCHEMA_VERSION,
        "check": CHECK_NAME,
        "root": str(root),
        "manifest": MANIFEST_NAME,
        "manifest_schema_version": manifest.get("schema_version"),
        "owner_count": len(manifest["owners"]),
        "path_rule_count": len(manifest["paths"]),
        "legacy_status_tables": {kind: len(table) for kind, table in sorted(LEGACY_STATUS_TABLES.items())},
        "coverage": coverage,
        "pending_owner_paths": pending,
        "passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ownership and legacy migration check")
    parser.add_argument("--root", default=None, help="repository root (default: parent of scripts/)")
    parser.add_argument("--json", action="store_true", help="emit the full report as JSON")
    parser.add_argument("--verbose", action="store_true", help="list owner counts and default fallbacks")
    parser.add_argument("--resolve", action="append", default=None,
                        help="resolve the owner of a path (repeatable) and exit")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        print(f"OWN-CONFIG: repository root not found: {root}", file=sys.stderr)
        return 2

    if args.resolve:
        failed = False
        for path in args.resolve:
            try:
                detail = resolve_owner_detail(path, root)
            except OwnershipError as exc:
                print(f"{path} -> REJECTED ({exc})")
                failed = True
                continue
            origin = detail["matched_prefix"] or f"default_owner={detail['default_owner']}"
            print(f"{detail['path']} -> {detail['owner']} (prefix: {origin})")
        return 1 if failed else 0

    report = run_checks(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if args.verbose:
            for owner, count in sorted(report["coverage"]["files_per_owner"].items()):
                print(f"  owner {owner}: {count} file(s)")
            for relative in report["coverage"]["default_owner_fallbacks"]:
                print(f"  default-owner fallback: {relative}")
        print(
            f"{CHECK_NAME}: files={report['coverage']['files_scanned']} "
            f"rules={report['path_rule_count']} violations={report['violation_count']}"
        )
        for violation in report["violations"]:
            print(f"  [{violation['code']}] {violation['detail']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
