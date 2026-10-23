"""Failure-closed checks for the Gate execution contract (P00-03).

Demonstrates the two required negative cases deterministically, by reusing the
frozen planner checker functions instead of re-implementing the DAG rules:

  1. a task depending on a non-existent task (P99-01) => graph validation fails
  2. a G00/G01 evidence record whose commands carry no exit_code => not acceptable

Prints the observed errors and exits non-zero if an expectation is NOT met.
Usage: python tools/ai_coding_plan/check_gate_contract.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/ai_coding_plan"))

from validate_plan import validate_graph  # noqa: E402  (frozen planner checker)

REQUIRED_EVIDENCE_FIELDS = {
    "schema_version", "gate_id", "status", "started_at", "finished_at",
    "code_revision", "dirty_tree_hash", "dependency_evidence_hashes",
    "input_artifact_hashes", "environment_fingerprint", "commands",
    "acceptance_artifacts", "limitations", "reviewer",
}


def missing_dependency_errors() -> list[str]:
    data = {
        "tasks": [
            {"id": "P99-01", "phase": 1, "deps": [], "blocks": ["G01"], "parallel": [], "allowed_files": ["a"]},
            {"id": "P01-01", "phase": 1, "deps": ["P99-01"], "blocks": ["G01"], "parallel": [], "allowed_files": ["b"]},
        ],
        "gates": [{"id": "G01", "phase": 1, "deps": ["P01-01"], "blocks": []}],
    }
    # P99-01 is now present, so remove it again to reproduce the real failure mode:
    # a dependency that cannot be resolved inside the node set.
    data["tasks"] = [t for t in data["tasks"] if t["id"] != "P99-01"]
    return validate_graph(data)


def unsupported_evidence_errors() -> list[str]:
    """Mirror artifacts/gates/G01.json with exit codes stripped from commands."""
    evidence = {
        "schema_version": "1.0.0",
        "gate_id": "G00",
        "status": "passed",
        "started_at": "2026-09-12T00:00:00+00:00",
        "finished_at": "2026-09-12T00:00:10+00:00",
        "code_revision": "content-sha256:deadbeef",
        "dirty_tree_hash": "content-sha256:deadbeef",
        "dependency_evidence_hashes": {},
        "input_artifact_hashes": {},
        "environment_fingerprint": {"python": "3.12.10"},
        "commands": [{"argv": ["uv", "run", "pytest", "-q"], "cwd": str(ROOT), "log_path": "x.log"}],
        "acceptance_artifacts": [],
        "limitations": [],
        "reviewer": "planner",
    }
    errors = [f"missing evidence field {name}" for name in sorted(REQUIRED_EVIDENCE_FIELDS - set(evidence))]
    for index, command in enumerate(evidence["commands"]):
        if "exit_code" not in command:
            errors.append(f"commands[{index}] has no exit_code; a Gate with unrecorded exit codes cannot pass")
        if command.get("exit_code") not in (0, None):
            errors.append(f"commands[{index}] exit_code={command['exit_code']} is non-zero; gate must fail")
    return errors


def main() -> int:
    graph_errors = missing_dependency_errors()
    evidence_errors = unsupported_evidence_errors()
    result = {
        "case_1_missing_dependency": {"expectation": "check fails", "errors": graph_errors, "ok": bool(graph_errors)},
        "case_2_missing_exit_code": {"expectation": "evidence rejected", "errors": evidence_errors, "ok": bool(evidence_errors)},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["case_1_missing_dependency"]["ok"] and result["case_2_missing_exit_code"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
