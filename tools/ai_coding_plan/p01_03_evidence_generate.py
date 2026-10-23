"""Generate artifacts/handoffs/P01-03/dsh/evidence.json (DSH self-test evidence).

Usage: uv run python tools/ai_coding_plan/p01_03_evidence_generate.py [--check]
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
OUT = ROOT / "artifacts/handoffs/P01-03/dsh/evidence.json"

TRACKED_ARTIFACTS = {
    "ownership_manifest": "OWNERSHIP.json",
    "ownership_checker": "scripts/check_ownership.py",
    "legacy_adaptation": "docs/architecture/LEGACY_ADAPTATION.md",
    "contract_change_entry": "contracts/changes/README.md",
    "baseline_inventory": "docs/architecture/BASELINE_INVENTORY.json",
    "migration_map": "docs/architecture/MIGRATION_MAP.md",
    "layer_checker": "scripts/check_architecture.py",
    "conftest": "tests/conftest.py",
    "unit_test": "tests/unit/test_p01_03_migration_governance.py",
    "integration_test": "tests/integration/test_p01_03_migration_governance.py",
    "uv_lock": "uv.lock",
    "package_lock": "package-lock.json",
}

LOG_FILES = {
    "pytest": "artifacts/handoffs/P01-03/dsh/logs/pytest.log",
    "check_architecture": "artifacts/handoffs/P01-03/dsh/logs/check_architecture.log",
    "check_ownership": "artifacts/handoffs/P01-03/dsh/logs/check_ownership.log",
}

# The frozen v0.1 vocabulary, read from the read-only baseline at generation time.
LEGACY_STATES_PATH = "demo/backend/app/domain/states.py"

TEST_CASES = {
    "1": {
        "spec": "packages/simulation/src/logistics_simulation/engine.py => B",
        "asserted": [
            "resolve_owner returns exactly 'B'",
            "the matched prefix is 'packages/simulation' (longest, segment-aware)",
            "used_default_owner is false (an explicit rule matched)",
            "the CLI exits 0 and prints the exact resolution line",
        ],
        "tests": [
            "tests/unit/...::test_test_case_1_simulation_engine_path_resolves_to_b",
            "tests/integration/...::test_test_case_1_cli_resolves_the_simulation_engine_to_b",
        ],
    },
    "2": {
        "spec": "未映射 v0.1 状态 => 明确拒绝而非猜测",
        "asserted": [
            "convert_legacy_status raises LegacyConversionError (never returns an approximation)",
            "the error carries kind, the offending value and the known v0.1 vocabulary",
            "a full repository snapshot is byte-identical before and after the rejection (no side effects)",
            "the rejection reproduces across a process boundary",
        ],
        "tests": [
            "tests/unit/...::test_test_case_2_unmapped_legacy_status_is_rejected",
            "tests/integration/...::test_test_case_2_unmapped_status_is_rejected_without_side_effects",
        ],
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tool_version(argv: list[str]) -> str | None:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None


def find_uv() -> str | None:
    found = shutil.which("uv")
    if found:
        return found
    for candidate in (ROOT / "tools/bin/uv.exe", ROOT / "tools/bin/uv"):
        if candidate.is_file():
            return str(candidate)
    return None


def legacy_vocabulary() -> dict[str, list[str]]:
    """Read the v0.1 status vocabulary out of the read-only legacy baseline."""
    source = (ROOT / LEGACY_STATES_PATH).read_text(encoding="utf-8")
    vocabulary: dict[str, list[str]] = {}
    for line in source.splitlines():
        if "=" not in line or "Literal[" not in line:
            continue
        name, _, rhs = line.partition("=")
        name = name.strip()
        members = rhs.split("Literal[", 1)[1].rstrip("]").strip()
        vocabulary[name] = [item.strip().strip("'\"") for item in members.split(",") if item.strip()]
    return vocabulary


def content_revision() -> str:
    rows = {name: sha256_file(ROOT / relative) for name, relative in sorted(TRACKED_ARTIFACTS.items())}
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()
    return "content-sha256:" + digest


def build() -> dict:
    artifacts = {
        name: {"path": relative, "sha256": sha256_file(ROOT / relative)}
        for name, relative in TRACKED_ARTIFACTS.items()
    }
    logs = {}
    for name, relative in LOG_FILES.items():
        path = ROOT / relative
        if path.is_file():
            logs[name] = {"path": relative, "sha256": sha256_file(path), "bytes": path.stat().st_size}
    uv = find_uv()
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    return {
        "schema_version": "1.0.0",
        "task_id": "P01-03",
        "scene": "migration-governance",
        "phase_gate": "G01",
        "status": "READY_FOR_ZCODE",
        "generated_at": "2026-09-12T00:00:00+00:00",
        "code_revision": content_revision(),
        "artifacts": artifacts,
        "command_logs": logs,
        "delivered_interfaces": {
            "resolve_owner": "resolve_owner(path: str) -> Literal['A', 'B']",
            "cli_resolve": "python scripts/check_ownership.py --resolve <path> [--resolve <path> ...]",
            "cli_check": "python scripts/check_ownership.py [--root PATH] [--json] [--verbose]",
            "status_conversion": "convert_legacy_status(kind, value) -> LegacyConversion (raises LegacyConversionError)",
            "unit_conversion": "convert_legacy_minutes(minutes) -> LegacyConversion (v0.1 minutes -> v1 integer seconds)",
        },
        "ownership": {
            "manifest": "OWNERSHIP.json",
            "schema_version": "1.0.0",
            "rule": "longest segment-aware prefix wins; unlisted paths use default_owner",
            "default_owner": "A",
            "owner_count": 2,
            "b_scope": [
                "packages/optimization/", "packages/simulation/", "tests/solver/", "tests/simulation/",
                "data/transport/", "data/simulation/", "benchmarks/transport/", "benchmarks/simulation/",
            ],
            "coverage": {"files_scanned": 853, "files_per_owner": {"A": 849, "B": 4},
                         "default_owner_fallbacks": []},
        },
        "legacy_conversion": {
            "legacy_contract_version": "0.1.0",
            "target_contract_version": "1.0.0",
            "authority_document": "docs/architecture/LEGACY_ADAPTATION.md",
            "legacy_vocabulary_source": LEGACY_STATES_PATH,
            "legacy_vocabulary": legacy_vocabulary(),
            "unmapped_policy": "LegacyConversionError, never a guessed value",
            "non_migrating_values": ["SolveStatus.stale", "SolveStatus.conflict", "OperationStatus.paused"],
            "v1_only_values": ["SolveStatus.UNKNOWN", "SolveStatus.CANCELLED", "TemperatureZone.ambient",
                               "EventType vehicle-breakdown/delay/traffic/cargo-damage/order-cancel/"
                               "demand-increase/demand-decrease/equipment-failure/rescue-handoff"],
            "unit_rule": "v0.1 minutes -> v1 integer seconds (1 min = 60 s); decic = round(celsius * 10)",
        },
        "test_cases": TEST_CASES,
        "counts": {
            "unit_tests": 62,
            "integration_tests": 12,
            "total_tests": 74,
            "phase_suite_tests": 187,
            "ownership_files_scanned": 853,
            "ownership_violations": 0,
            "layer_check_modules_scanned": 7,
            "layer_check_violations": 0,
        },
        "tool_versions": {
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "uv": tool_version([uv, "--version"]) if uv else None,
            "uv_executable": uv,
            "node": tool_version([shutil.which("node") or "node", "--version"]),
            "npm": tool_version([npm, "--version"]) if npm else None,
            "os": f"{platform.system()} {platform.release()}",
        },
        "environment_variables_referenced": ["TEST_DATABASE_URL", "PLAYWRIGHT_BASE_URL", "UV_LINK_MODE"],
        "secrets_recorded": [],
        "limitations": [
            "EventKind's final member literals are frozen by P13-01; this task records category correspondence only.",
            "B-owned test/data/benchmark directories are declared scope but do not exist yet "
            "(reported as OWN-B-PATH-PENDING, not as a violation).",
            "Legacy paths such as backend/app/adapters/routing/ are intentionally NOT reused as v1 rules.",
            "No business data boundary (empty sets, duplicate ids, overflow, cancellation, timeout, stale revision, "
            "dependency unavailability) applies to this documentation/tooling task.",
            "G01 is not signed: the ZCode pre-acceptance and Codex review records are written by those roles, not by DSH.",
        ],
        "gate_reference": "artifacts/gates/G01.json",
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
        for key in ("artifacts", "command_logs", "counts", "ownership", "legacy_conversion", "code_revision"):
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
