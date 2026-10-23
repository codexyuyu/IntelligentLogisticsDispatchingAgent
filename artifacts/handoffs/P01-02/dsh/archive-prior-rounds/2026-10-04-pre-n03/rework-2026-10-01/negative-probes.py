"""Rework 2026-10-01 evidence probe for the four confirmed P01-02 defects.

Mirrors the isolated Codex probes in
``artifacts/reviews/2026-10-01/codex/snapshot-and-evidence-probes.json`` and re-runs them
against the reworked ``scripts/gates.py``. Everything happens in a temporary tree, so no
official Gate record, review record or repository file is touched.

Usage:  python artifacts/handoffs/P01-02/dsh/rework-2026-10-01/negative-probes.py
Exit 0 = every superseded finding is now False and every fixed judgement still holds.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
GATES = ROOT / "scripts/gates.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("gates_under_probe", GATES)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gates_under_probe"] = module
    spec.loader.exec_module(module)
    return module


def write(root: Path, relative: str, body: str = "x\n") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def complete_gate_record(module, root: Path, gate_id: str = "G00") -> dict:
    log_relative = f"artifacts/gates/{gate_id}-logs/probe.log"
    log = write(root, log_relative, "# argv: python -c pass\n## exit_code: 0\n")
    manifest = root / "docs/plan/TASK_MANIFEST.json"
    return {
        "schema_version": "1.0.0", "gate_id": gate_id, "status": "passed",
        "started_at": "2026-09-12T00:00:00+00:00", "finished_at": "2026-09-12T00:00:10+00:00",
        "code_revision": "content-sha256:probe", "dirty_tree_hash": "content-sha256:probe",
        "dependency_evidence_hashes": {},
        "input_artifact_hashes": {"docs/plan/TASK_MANIFEST.json": hashlib.sha256(manifest.read_bytes()).hexdigest()},
        "environment_fingerprint": {"python": "3.12.10"},
        "commands": [{"argv": ["python", "-c", "pass"], "cwd": str(root), "exit_code": 0,
                      "log_path": log_relative, "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()}],
        "acceptance_artifacts": [], "limitations": [], "reviewer": "probe",
    }


def main() -> int:
    module = load_runner_module()
    findings: dict[str, object] = {}
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        write(root, "docs/plan/TASK_MANIFEST.json", '{"tasks": []}')
        write(root, "docs/plan/PHASE_GATES.md", "# gates\n")
        write(root, "scripts/gates.py", "x = 1\n")
        write(root, "artifacts/handoffs/P01-01/dsh/evidence.json", '{"status": "READY_FOR_ZCODE"}')
        task = {"id": "P01-01", "task_doc": "a.md", "report": "b.md", "commands": [], "files": []}
        runner = module.GateRunner(root=root, phase=1, revision="auto")
        runner.phase_tasks = lambda: [task]

        # Defect 3: an empty pre-check input set used to be accepted.
        precheck = write(root, "artifacts/handoffs/P01-01/zcode/precheck.json", json.dumps({
            "schema_version": "1.0.0", "task_id": "P01-01", "phase_gate": "G01", "reviewer": "zcode",
            "status": "Z_PRECHECK_PASSED", "verified_input_hashes": {},
        }))
        findings["empty_precheck_input_hashes_accepted"] = runner.check_zcode_precheck()[0].passed

        # ... and a pre-check that covers everything must still be accepted.
        verified = {
            relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in ("docs/plan/TASK_MANIFEST.json", "docs/plan/PHASE_GATES.md",
                             "artifacts/handoffs/P01-01/dsh/evidence.json")
        }
        precheck.write_text(json.dumps({
            "schema_version": "1.0.0", "task_id": "P01-01", "phase_gate": "G01", "reviewer": "zcode",
            "status": "Z_PRECHECK_PASSED", "verified_input_hashes": verified,
        }), encoding="utf-8")
        findings["complete_precheck_accepted"] = runner.check_zcode_precheck()[0].passed

        # Defect 4: a status-only previous Gate record used to be accepted.
        write(root, "artifacts/gates/G00.json", json.dumps({"gate_id": "G00", "status": "passed"}))
        findings["previous_gate_status_without_evidence_accepted"] = runner.check_previous_gates()[0].passed

        # ... and a complete controlled record must still be accepted.
        write(root, "artifacts/gates/G00.json", json.dumps(complete_gate_record(module, root)))
        findings["complete_previous_gate_accepted"] = runner.check_previous_gates()[0].passed

        # Defect 2: scratch, evidence and forensics writes used to move the candidate.
        before_revision = runner.compute_revision()
        before_tree = runner.dirty_tree_hash()
        for relative in ("tmp/probe.log", ".mimosa/probe.json",
                         "artifacts/handoffs/P01-02/dsh/logs/probe.log",
                         "artifacts/handoffs/P01-02/dsh/probe.py",
                         "artifacts/reviews/2026-10-01/codex/probe.py",
                         "docs/implementation/reports/P01-02.md"):
            write(root, relative, "probe\n")
        findings["tmp_log_changes_revision"] = runner.compute_revision() != before_revision
        findings["mimosa_state_changes_revision"] = runner.compute_revision() != before_revision
        findings["handoff_log_changes_revision"] = runner.compute_revision() != before_revision
        findings["evidence_generator_changes_dirty_tree_hash"] = runner.dirty_tree_hash() != before_tree

        # A relevant input must still move both identity values.
        write(root, "scripts/gates.py", "x = 2\n")
        findings["relevant_source_change_moves_revision"] = runner.compute_revision() != before_revision
        findings["relevant_source_change_moves_dirty_tree"] = runner.dirty_tree_hash() != before_tree

    expected = {
        "empty_precheck_input_hashes_accepted": False,
        "complete_precheck_accepted": True,
        "previous_gate_status_without_evidence_accepted": False,
        "complete_previous_gate_accepted": True,
        "tmp_log_changes_revision": False,
        "mimosa_state_changes_revision": False,
        "handoff_log_changes_revision": False,
        "evidence_generator_changes_dirty_tree_hash": False,
        "relevant_source_change_moves_revision": True,
        "relevant_source_change_moves_dirty_tree": True,
    }
    verdict = {name: findings.get(name) == want for name, want in expected.items()}
    print(json.dumps(dict(observed=findings, expected=expected, matches=verdict,
                          all_match=all(verdict.values())), indent=2))
    return 0 if all(verdict.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
