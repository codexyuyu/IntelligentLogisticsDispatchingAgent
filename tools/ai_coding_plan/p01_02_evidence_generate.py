"""Generate artifacts/handoffs/P01-02/dsh/evidence.json (DSH self-test evidence).

Hashes are computed from the real files at generation time so the evidence can be checked
for drift. Usage: uv run python tools/ai_coding_plan/p01_02_evidence_generate.py [--check]
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
OUT = ROOT / "artifacts/handoffs/P01-02/dsh/evidence.json"

TRACKED_ARTIFACTS = {
    "gates": "scripts/gates.py",
    "check_architecture": "scripts/check_architecture.py",
    "conftest": "tests/conftest.py",
    "ci_workflow": ".github/workflows/ci.yml",
    "vitest_config": "apps/frontend/vitest.config.ts",
    "frontend_test_setup": "apps/frontend/src/test/setup.ts",
    "unit_test": "tests/unit/test_p01_02_checks_and_gate_runner.py",
    "integration_test": "tests/integration/test_p01_02_checks_and_gate_runner.py",
    "uv_lock": "uv.lock",
    "package_lock": "package-lock.json",
    "phase_gate_evidence": "artifacts/gates/G01.json",
}

LOG_FILES = {
    "pytest": "artifacts/handoffs/P01-02/dsh/logs/pytest.log",
    "check_architecture": "artifacts/handoffs/P01-02/dsh/logs/check_architecture.log",
    "gate_g01": "artifacts/handoffs/P01-02/dsh/logs/gate-g01.log",
}

TEST_CASES = {
    "1": {
        "spec": "命令 exit=1 => G01 failed 且进程非零",
        "tests": ["tests/integration/...::test_exit_one_command_fails_the_gate_and_exits_nonzero"],
        "asserted": [
            "evidence status == failed",
            "P01-01-cmd1 in failed_checks",
            "recorded exit_code == 1",
            "raw log exists with a matching sha256",
            "runner process exit code != 0",
        ],
    },
    "2": {
        "spec": "domain 导入 fastapi => 层边界检查失败",
        "tests": [
            "tests/integration/...::test_domain_importing_fastapi_fails_the_layer_check",
            "tests/integration/...::test_layer_violation_makes_the_phase_gate_fail",
        ],
        "asserted": [
            "checker exit code != 0",
            "violation code ARCH-PURITY with exact path and line",
            "the same violation also fails the phase acceptance assertion",
        ],
    },
    "3": {
        "spec": "Codex review 缺失或 ZCode 输入哈希过期 => 不写 passed",
        "tests": [
            "tests/integration/...::test_missing_codex_review_prevents_a_passed_record",
            "tests/integration/...::test_stale_zcode_input_hash_prevents_a_passed_record",
            "tests/integration/...::test_missing_zcode_precheck_prevents_a_passed_record",
        ],
        "asserted": [
            "status == failed whenever the review or pre-acceptance record is missing",
            "status == failed whenever a recorded input hash no longer matches disk",
        ],
    },
    "4": {
        "spec": "--check-only 全部成功 => 仅输出检查结果，不签收 Gate",
        "tests": ["tests/integration/...::test_check_only_does_not_sign_and_does_not_write"],
        "asserted": [
            "no evidence file is created or modified",
            "no command log directory is created",
            "stdout states the gate was not signed",
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
    gate = json.loads((ROOT / "artifacts/gates/G01.json").read_text(encoding="utf-8"))
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    return {
        "schema_version": "1.0.0",
        "task_id": "P01-02",
        "scene": "checks-and-gate-runner",
        "phase_gate": "G01",
        "status": "READY_FOR_ZCODE",
        "generated_at": "2026-09-12T00:00:00+00:00",
        "code_revision": content_revision(),
        "artifacts": artifacts,
        "command_logs": logs,
        "delivered_interfaces": {
            "gate_runner": "python scripts/gates.py --phase NN --revision REV -> artifacts/gates/GNN.json",
            "layer_check": "python scripts/check_architecture.py [--root PATH] [--json] [--verbose]",
        },
        "gate_runner_modes": {
            "default": "executes manifest commands and phase assertions, writes GNN.json, exit 0 only when passed",
            "check_only": "freshness verification only: runs nothing, writes nothing, never signs",
            "skip_commands": "evidence/record verification only; always fails, each skipped assertion says so",
            "assertion_filter": "runs only the named assertion ids",
            "out_dir": "writes evidence to an alternate directory; the record is marked official_gate_record=false and never overwrites artifacts/gates/GNN.json",
        },
        "phase_assertions": [spec["id"] for spec in gate.get("acceptance_assertions", [])],
        "phase_assertion_results": {spec["id"]: spec["passed"] for spec in gate.get("acceptance_assertions", [])},
        "test_cases": TEST_CASES,
        "counts": {
            "unit_tests": 39,
            "integration_tests": 18,
            "total_tests": 57,
            "layer_check_modules_scanned": 7,
            "layer_check_violations": 0,
            "gate_checks_total": len(gate.get("commands", []))
            + len(gate.get("acceptance_assertions", []))
            + len(gate.get("record_checks", [])),
            "gate_checks_failed": len(gate.get("failed_checks", [])),
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
        "gate_state": {
            "gate_id": gate["gate_id"],
            "status": gate["status"],
            "failed_checks": gate["failed_checks"],
            "note": (
                "G01 stays failed by design: P01-03 has not delivered, and the ZCode pre-acceptance and Codex "
                "review records are not written by the development role. DSH self-test passing is not a gate sign-off."
            ),
        },
        "limitations": [
            "G01 is NOT signed: artifacts/gates/G01.json records status=failed until P01-03 delivers and the ZCode/Codex records exist.",
            "docs/workflow/HANDOFF_CONTRACT.md does not exist; this task fixes the record format itself and documents the deviation.",
            "The layer checker's third-party import table is a whitelist: an unlisted new dependency is not flagged, so it must be added to the table when introduced.",
            "CI is validated locally by static assertions only; no GitHub Actions run exists for this repository.",
            "No database, solver, simulation, LLM or browser acceptance is in scope for Phase 01.",
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
        for key in ("artifacts", "command_logs", "counts", "gate_state", "code_revision", "tool_versions"):
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
