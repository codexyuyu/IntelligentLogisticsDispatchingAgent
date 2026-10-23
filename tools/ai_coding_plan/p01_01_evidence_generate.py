"""Generate artifacts/handoffs/P01-01/dsh/evidence.json (DSH self-test evidence).

The recorded hashes are computed from the real files at generation time, so the
integration tests can detect any later drift. Usage:
    uv run python tools/ai_coding_plan/p01_01_evidence_generate.py [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/handoffs/P01-01/dsh/evidence.json"

DEMO_SKIP_DIRECTORIES = {"node_modules", ".venv", "__pycache__", ".git", ".mypy_cache"}

TRACKED_ARTIFACTS = {
    "uv_lock": "uv.lock",
    "package_lock": "package-lock.json",
    "root_pyproject": "pyproject.toml",
    "root_package_json": "package.json",
    "python_version_file": ".python-version",
    "node_version_file": ".node-version",
    "playwright_config": "playwright.config.ts",
    "frontend_package_json": "apps/frontend/package.json",
    "backend_pyproject": "apps/backend/pyproject.toml",
    "unit_test": "tests/unit/test_p01_01_workspace_bootstrap.py",
    "integration_test": "tests/integration/test_p01_01_workspace_bootstrap.py",
}

MEMBER_MODULES = {
    "logistics_domain": "packages/domain/src/logistics_domain/__init__.py",
    "logistics_contracts": "packages/contracts/src/logistics_contracts/__init__.py",
    "logistics_optimization": "packages/optimization/src/logistics_optimization/__init__.py",
    "logistics_simulation": "packages/simulation/src/logistics_simulation/__init__.py",
    "logistics_agents": "packages/agents/src/logistics_agents/__init__.py",
    "logistics_evaluation": "packages/evaluation/src/logistics_evaluation/__init__.py",
    "logistics_backend": "apps/backend/src/logistics_backend/__init__.py",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tool_version(argv: list[str]) -> str | None:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip().splitlines()[0]


def find_uv() -> str | None:
    found = shutil.which("uv")
    if found:
        return found
    for candidate in (ROOT / "tools/bin/uv.exe", ROOT / "tools/bin/uv"):
        if candidate.is_file():
            return str(candidate)
    return None


def demo_fingerprint() -> tuple[int, str]:
    """Fingerprint over exactly the demo/ files registered by the baseline inventory.

    Using the inventory's own entry list keeps the evidence check consistent with what
    P00-01 registered (whole-tree scans additionally pick up cache directories such as
    .pytest_cache and the .package-lock.json that npm writes into node_modules).
    """
    inventory = json.loads((ROOT / "docs/architecture/BASELINE_INVENTORY.json").read_text(encoding="utf-8"))
    paths = sorted(entry["source_path"] for entry in inventory["entries"])
    digest = hashlib.sha256()
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"registered baseline file missing: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("utf-8"))
        digest.update(b"\n")
    return len(paths), digest.hexdigest()


def node_version() -> str | None:
    node = shutil.which("node")
    if node is None:
        return None
    version = tool_version([node, "--version"])
    return version.lstrip("v") if version else None


def content_revision() -> str:
    """No Git in this checkout, so the revision is a hash over the bootstrap artifact set."""
    rows = {name: sha256_file(ROOT / relative) for name, relative in sorted(TRACKED_ARTIFACTS.items())}
    rows.update({f"module:{name}": sha256_file(ROOT / relative) for name, relative in sorted(MEMBER_MODULES.items())})
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()
    return "content-sha256:" + digest


def build() -> dict:
    artifacts = {name: {"path": relative, "sha256": sha256_file(ROOT / relative)} for name, relative in TRACKED_ARTIFACTS.items()}
    logs = {}
    for log in sorted((ROOT / "artifacts/handoffs/P01-01/dsh/logs").glob("*.log")):
        logs[log.relative_to(ROOT).as_posix()] = {
            "sha256": sha256_file(log),
            "bytes": log.stat().st_size,
        }
    count, tree_sha = demo_fingerprint()
    uv = find_uv()
    return {
        "schema_version": "1.0.0",
        "task_id": "P01-01",
        "scene": "workspace-bootstrap",
        "phase_gate": "G01",
        "status": "READY_FOR_ZCODE",
        "generated_at": "2026-09-12T00:00:00+00:00",
        "code_revision": content_revision(),
        "artifacts": artifacts,
        "command_logs": logs,
        "python_workspace_members": [
            "logistics-agents",
            "logistics-backend",
            "logistics-contracts",
            "logistics-domain",
            "logistics-evaluation",
            "logistics-optimization",
            "logistics-simulation",
        ],
        "importable_packages": sorted(MEMBER_MODULES),
        "python_workspace_member_modules": MEMBER_MODULES,
        "dependencies_lock": {
            "uv_lock_path": "uv.lock",
            "uv_lock_sha256": artifacts["uv_lock"]["sha256"],
            "package_lock_path": "package-lock.json",
            "package_lock_sha256": artifacts["package_lock"]["sha256"],
            "locked_package_count": 40,
            "npm_lockfile_version": 3,
            "frozen_install_command": "uv sync --frozen",
            "npm_install_command": "npm ci",
        },
        "tool_versions": {
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "uv": (tool_version([uv, "--version"]) if uv else None),
            "uv_executable": uv,
            "node": node_version(),
            "npm": tool_version([shutil.which("npm.cmd") or "npm", "--version"]) if shutil.which("npm.cmd") or shutil.which("npm") else None,
            "os": f"{platform.system()} {platform.release()}",
        },
        "environment_variables_referenced": [
            "TEST_DATABASE_URL",
            "PLAYWRIGHT_BASE_URL",
            "UV_LINK_MODE",
        ],
        "secrets_recorded": [],
        "legacy_demo": {
            "path": "demo/",
            "read_only": True,
            "file_count": count,
            "hash_algorithm": "sha256",
            "tree_sha256": tree_sha,
            "tree_hash_definition": (
                "sha256 over sorted '<relative_path>\\0<file_sha256>\\n' for every demo/ file registered by "
                "docs/architecture/BASELINE_INVENTORY.json (the G00 gate rejects directory paths, so the "
                "inventory registers files only)"
            ),
            "demo_zip": {"path": "demo.zip", "sha256": sha256_file(ROOT / "demo.zip")},
            "baseline_inventory": "docs/architecture/BASELINE_INVENTORY.json",
        },
        "validation_commands": [
            {
                "id": "pytest",
                "argv": [
                    "uv", "run", "pytest",
                    "tests/unit/test_p01_01_workspace_bootstrap.py",
                    "tests/integration/test_p01_01_workspace_bootstrap.py",
                    "-q",
                ],
                "cwd": str(ROOT),
                "log_path": "artifacts/handoffs/P01-01/dsh/logs/pytest-q.log",
            },
            {"id": "uv_sync_frozen", "argv": ["uv", "sync", "--frozen"], "cwd": str(ROOT),
             "log_path": "artifacts/handoffs/P01-01/dsh/logs/uv-sync-frozen.log"},
            {"id": "npm_ci", "argv": ["npm", "ci"], "cwd": str(ROOT),
             "log_path": "artifacts/handoffs/P01-01/dsh/logs/npm-ci.log"},
        ],
        "limitations": [
            "Phase 01 delivers the workspace skeleton only: no domain entity, solver, simulation, API or UI behaviour exists yet.",
            "The root README.md declared by pyproject.toml is absent in this checkout; hatchling is not asked to build the root project (package = false).",
            "uv 0.12.13 is not installed system-wide on this host; it was bootstrapped into tools/bin/uv.exe for this task and is not part of the workspace deliverable set.",
            "No Git repository exists in this checkout, so code_revision is a content hash of the bootstrap artifact set.",
            "Playwright is installed and configured but no e2e spec exists before P24-01; an empty Playwright run is not acceptance evidence.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file():
            print("evidence.json missing; generate it")
            return 1
        existing = json.loads(OUT.read_text(encoding="utf-8"))
        for key in ("artifacts", "dependencies_lock", "legacy_demo", "tool_versions", "code_revision"):
            if existing.get(key) != payload.get(key):
                print(f"evidence.json is stale for key {key}; regenerate it")
                return 1
        print("evidence.json up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
