#!/usr/bin/env python
"""Layered architecture check for the logistics dispatching monorepo.

Verifies the Architecture Contract (docs/architecture/ARCHITECTURE_OVERVIEW.md and
IMPLEMENTATION_CONVENTIONS.md) against the real source tree:

1. every module belongs to a known layer;
2. a layer may only import permitted sibling layers;
3. the pure domain layer imports no framework, ORM, model SDK, solver or simulation
   engine at all (not even declared dependencies);
4. other layers may only import third-party distributions they actually declare in
   their own ``pyproject.toml`` (declaration is necessary but never sufficient for
   domain);
5. no new package imports the legacy ``app.*`` namespace or the read-only teaching
   probes under ``demo/``;
6. workspace members never import each other through private ``src`` paths.

Exit codes: 0 = all checks passed, 1 = violations found, 2 = usage/configuration error.
No application code, database or network access is required.

Usage:
    uv run python scripts/check_architecture.py [--root PATH] [--json] [--verbose]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
CHECK_NAME = "architecture-layers"

# --------------------------------------------------------------------------- rules

# Layer name -> (source roots relative to the repository root, internal layers it may import)
LAYERS: dict[str, tuple[tuple[str, ...], frozenset[str]]] = {
    "domain": (("packages/domain/src",), frozenset({"domain"})),
    "contracts": (("packages/contracts/src",), frozenset({"domain", "contracts"})),
    "optimization": (("packages/optimization/src",), frozenset({"domain", "optimization"})),
    "simulation": (("packages/simulation/src",), frozenset({"domain", "simulation"})),
    "agents": (("packages/agents/src",), frozenset({"contracts", "domain", "agents"})),
    "evaluation": (("packages/evaluation/src",), frozenset({"contracts", "domain", "evaluation"})),
    "backend": (
        ("apps/backend/src",),
        frozenset({"domain", "contracts", "optimization", "simulation", "agents", "evaluation", "backend"}),
    ),
}

# Import root -> owning layer (used for the "no application -> adapters" style rules).
IMPORT_ROOT_LAYER: dict[str, str] = {
    "logistics_domain": "domain",
    "logistics_contracts": "contracts",
    "logistics_optimization": "optimization",
    "logistics_simulation": "simulation",
    "logistics_agents": "agents",
    "logistics_evaluation": "evaluation",
    "logistics_backend": "backend",
}

# Third-party import root -> (distribution name for declaration checks, forbidden layers)
THIRD_PARTY: dict[str, tuple[str, frozenset[str]]] = {
    "fastapi": ("fastapi", frozenset({"domain"})),
    "starlette": ("starlette", frozenset({"domain"})),
    "uvicorn": ("uvicorn", frozenset({"domain"})),
    "pydantic": ("pydantic", frozenset({"domain"})),
    "sqlalchemy": ("sqlalchemy", frozenset({"domain"})),
    "alembic": ("alembic", frozenset({"domain"})),
    "psycopg": ("psycopg", frozenset({"domain"})),
    "ortools": ("ortools", frozenset({"domain", "contracts", "agents", "evaluation"})),
    "simpy": ("simpy", frozenset({"domain", "contracts", "agents", "evaluation"})),
    "numpy": ("numpy", frozenset()),
    "pandas": ("pandas", frozenset()),
    "openai": ("openai", frozenset({"domain", "contracts", "optimization", "simulation", "evaluation"})),
    "anthropic": ("anthropic", frozenset({"domain", "contracts", "optimization", "simulation", "evaluation"})),
}

# Layers that must stay dependency-free in their own metadata as well as in imports.
PURE_LAYER = "domain"

LEGACY_IMPORT_ROOTS = ("app", "demo", "demos")
DESCRIPTION = "layer boundary and import direction check"


@dataclass(frozen=True)
class Violation:
    code: str
    rule: str
    path: str
    line: int
    detail: str

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "rule": self.rule,
            "path": self.path,
            "line": self.line,
            "detail": self.detail,
        }

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.code}] {self.detail} (rule: {self.rule})"


@dataclass(frozen=True)
class ImportRecord:
    module: str
    root: str
    line: int


def layer_source_roots(root: Path) -> list[tuple[str, Path]]:
    return [(name, root / relative) for name, (relatives, _) in LAYERS.items() for relative in relatives]


def layer_for_path(root: Path, path: Path) -> str | None:
    for name, source_root in layer_source_roots(root):
        if source_root.is_dir() and path.is_relative_to(source_root):
            return name
    return None


def iter_modules(root: Path) -> list[tuple[str, Path]]:
    """Every first-party .py file with the layer that owns it."""
    found: list[tuple[str, Path]] = []
    for name, source_root in layer_source_roots(root):
        if not source_root.is_dir():
            continue
        for path in sorted(source_root.rglob("*.py")):
            if any(part in {"__pycache__", ".venv"} for part in path.parts):
                continue
            found.append((name, path))
    return found


def imported_roots(tree: ast.AST) -> list[ImportRecord]:
    """Module-level import roots, including imports nested in try/if blocks."""
    records: list[ImportRecord] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                records.append(ImportRecord(module=alias.name, root=root, line=node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import stays inside the same layer
                continue
            module = node.module or ""
            root = module.split(".", 1)[0]
            records.append(ImportRecord(module=module, root=root, line=node.lineno))
    return records


def declared_distributions(root: Path, layer: str) -> set[str]:
    """Distributions declared by the workspace member that owns this layer."""
    relatives = LAYERS[layer][0]
    for relative in relatives:
        member_root = root / relative
        if member_root.name != "src":
            continue
        project_file = member_root.parent / "pyproject.toml"
        if not project_file.is_file():
            continue
        data = tomllib.loads(project_file.read_text(encoding="utf-8"))
        declared = data.get("project", {}).get("dependencies", [])
        names = set()
        for requirement in declared:
            name = requirement.split(";")[0]
            for separator in ("[", ">", "<", "=", "!", "~", " "):
                name = name.split(separator, 1)[0]
            names.add(name.strip().lower())
        return names
    return set()


def check_module(root: Path, layer: str, path: Path) -> list[Violation]:
    relative = path.relative_to(root).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [Violation("ARCH-SYNTAX", "all modules must parse", relative, exc.lineno or 0, str(exc))]
    violations: list[Violation] = []
    allowed_layers = LAYERS[layer][1]
    declared = declared_distributions(root, layer)
    for record in imported_roots(tree):
        if record.root in LEGACY_IMPORT_ROOTS:
            violations.append(
                Violation(
                    "ARCH-LEGACY",
                    "no new package may import the legacy app namespace or teaching demos",
                    relative,
                    record.line,
                    f"imports legacy root {record.root!r} (via {record.module!r})",
                )
            )
            continue
        if record.root in IMPORT_ROOT_LAYER:
            target = IMPORT_ROOT_LAYER[record.root]
            if target not in allowed_layers:
                violations.append(
                    Violation(
                        "ARCH-DIRECTION",
                        f"layer {layer} may only import {sorted(allowed_layers)}",
                        relative,
                        record.line,
                        f"layer {layer} imports layer {target} via {record.module!r}",
                    )
                )
            continue
        entry = THIRD_PARTY.get(record.root)
        if entry is None:
            continue  # standard library or an undeclared/unclassified import
        distribution, forbidden_layers = entry
        if layer in forbidden_layers:
            violations.append(
                Violation(
                    "ARCH-PURITY",
                    f"layer {layer} must not import {distribution}",
                    relative,
                    record.line,
                    f"pure/forbidden layer {layer} imports {record.root!r}",
                )
            )
            continue
        if layer == PURE_LAYER:
            violations.append(
                Violation(
                    "ARCH-PURITY",
                    "the domain layer imports only the standard library",
                    relative,
                    record.line,
                    f"domain imports third-party root {record.root!r}",
                )
            )
            continue
        if distribution and distribution.lower() not in declared:
            violations.append(
                Violation(
                    "ARCH-UNDECLARED",
                    "a module may only import distributions its own member declares",
                    relative,
                    record.line,
                    f"imports {record.root!r} but member {layer} does not declare {distribution!r}",
                )
            )
    return violations


def private_src_fragments(tree: ast.AST) -> list[int]:
    """Line numbers of string constants that name another member's private src path.

    Only string *literals* are inspected, so a comment or docstring that documents a path
    (this file included) is not a violation, while a real path manipulation is.
    """
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = node.value.replace("\\", "/")
        if "node_modules" in text:
            continue
        if re.search(r"(?:^|/)(?:packages|apps)/[^/]+/src(?:/|$)", text):
            lines.append(node.lineno)
    return lines


def check_private_src_imports(root: Path) -> list[Violation]:
    """No member may reach into another member's private src layout."""
    violations: list[Violation] = []
    for _layer, path in iter_modules(root):
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue  # reported by check_module
        for line in private_src_fragments(tree):
            violations.append(
                Violation(
                    "ARCH-PRIVATE-SRC",
                    "import workspace members by distribution name, never by src path",
                    relative,
                    line,
                    "references another member's private source path in a string literal",
                )
            )
    return violations


def check_pure_layer_metadata(root: Path) -> list[Violation]:
    """The pure domain member must not declare any dependency at all."""
    violations: list[Violation] = []
    for relative in LAYERS[PURE_LAYER][0]:
        member_root = root / relative
        project_file = member_root.parent / "pyproject.toml"
        if not project_file.is_file():
            continue
        data = tomllib.loads(project_file.read_text(encoding="utf-8"))
        declared = data.get("project", {}).get("dependencies", [])
        if declared:
            violations.append(
                Violation(
                    "ARCH-PURITY",
                    "the pure domain member declares no dependencies",
                    project_file.relative_to(root).as_posix(),
                    0,
                    f"declares {declared}",
                )
            )
    return violations


def run_checks(root: Path) -> dict:
    modules = iter_modules(root)
    violations: list[Violation] = []
    for layer, path in modules:
        violations.extend(check_module(root, layer, path))
    violations.extend(check_private_src_imports(root))
    violations.extend(check_pure_layer_metadata(root))
    per_layer: dict[str, int] = {name: 0 for name in LAYERS}
    for layer, _ in modules:
        per_layer[layer] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "check": CHECK_NAME,
        "description": DESCRIPTION,
        "root": str(root),
        "layers_checked": sorted(LAYERS),
        "modules_scanned": len(modules),
        "modules_per_layer": per_layer,
        "passed": not violations,
        "violation_count": len(violations),
        "violations": [violation.as_dict() for violation in violations],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--root", default=None, help="repository root (default: parent of this script's directory)")
    parser.add_argument("--json", action="store_true", help="emit the full report as JSON")
    parser.add_argument("--verbose", action="store_true", help="list every scanned layer and module count")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        print(f"ARCH-CONFIG: repository root not found: {root}", file=sys.stderr)
        return 2

    report = run_checks(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if args.verbose:
            for layer, count in sorted(report["modules_per_layer"].items()):
                print(f"  layer {layer}: {count} module(s)")
        print(
            f"{CHECK_NAME}: scanned {report['modules_scanned']} module(s) across "
            f"{len(report['layers_checked'])} layer(s); violations={report['violation_count']}"
        )
        for violation in report["violations"]:
            print("  " + violation["path"] + f":{violation['line']}: [{violation['code']}] {violation['detail']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
