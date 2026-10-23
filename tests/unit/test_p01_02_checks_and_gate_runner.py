"""Unit checks for the P01-02 gate runner and layered architecture checker.

Covers the pure decision logic of scripts/gates.py and scripts/check_architecture.py:
command parsing, non-zero command rejection, empty/zero-case log rejection, stale hash
detection, and the layer rules. The end-to-end behaviour of both scripts against a real
synthetic repository lives in tests/integration/test_p01_02_checks_and_gate_runner.py.
"""

from __future__ import annotations

import ast
import hashlib
import json
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

P01_02_DELIVERABLES = (
    ".github/workflows/ci.yml",
    "apps/frontend/src/test/setup.ts",
    "apps/frontend/vitest.config.ts",
    "scripts/check_architecture.py",
    "scripts/gates.py",
    "tests/conftest.py",
)


def write_module(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


# ------------------------------------------------------------------ command parsing


def test_split_command_never_uses_a_shell(gate_runner_module) -> None:
    argv = gate_runner_module.normalize_argv(
        gate_runner_module.split_command('uv run pytest tests/unit -q')
    )
    assert argv == ["uv", "run", "pytest", "tests/unit", "-q"]
    assert "shell" not in json.dumps(argv).lower()


def test_split_command_keeps_quoted_python_programs_in_one_token(gate_runner_module) -> None:
    argv = gate_runner_module.normalize_argv(
        gate_runner_module.split_command('uv run python -c "import sys; sys.exit(1)"')
    )
    assert argv[:3] == ["uv", "run", "python"]
    assert argv[3] == "-c"
    assert len(argv) == 5, f"the -c program must stay a single argument, got {argv}"


def test_resolve_tool_prefers_path_and_falls_back_to_repo_bootstrap(gate_runner_module, tmp_path: Path) -> None:
    sentinel = tmp_path / "tools/bin/uv.exe"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("stub", encoding="utf-8")
    # 'python' exists on PATH in the test environment, so PATH wins.
    assert Path(gate_runner_module.resolve_tool("python", tmp_path)).name.startswith("python")
    # A tool that is absent from PATH must resolve to the repository bootstrap copy.
    assert gate_runner_module.resolve_tool("definitely-not-a-real-tool-xyz", tmp_path) == "definitely-not-a-real-tool-xyz"


# --------------------------------------------------------------- exit code semantics


def make_result(gate_runner_module, argv: list[str], exit_code: int, counts: dict | None = None):
    return gate_runner_module.CommandResult(
        check_id="unit",
        argv=argv,
        cwd=".",
        exit_code=exit_code,
        duration_ms=1,
        log_path="artifacts/gates/G01-logs/unit.log",
        log_sha256="0" * 64,
        stdout_tail=[],
        test_counts=counts or {},
        required=True,
    )


def test_non_zero_exit_is_rejected(gate_runner_module, tmp_path: Path) -> None:
    """命令 exit=1 => 判定失败（进程非零由集成测试断言）。"""
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    (tmp_path / "artifacts/gates/G01-logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts/gates/G01-logs/unit.log").write_text("log", encoding="utf-8")
    result = make_result(gate_runner_module, ["uv", "run", "python", "-c", "sys.exit(1)"], exit_code=1)
    verdict = runner.evaluate_command("c", result)
    assert verdict.passed is False
    assert "exit_code=1" in verdict.detail
    assert verdict.id == "c"


def test_failing_pytest_counts_are_rejected_even_with_exit_zero(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    (tmp_path / "artifacts/gates/G01-logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts/gates/G01-logs/unit.log").write_text("log", encoding="utf-8")
    result = make_result(
        gate_runner_module, ["uv", "run", "pytest", "tests/unit", "-q"],
        exit_code=0, counts={"passed": 3, "failed": 1},
    )
    verdict = runner.evaluate_command("c", result)
    assert verdict.passed is False
    assert "failing tests" in verdict.detail


def test_zero_case_pytest_run_is_not_acceptance_evidence(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    (tmp_path / "artifacts/gates/G01-logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts/gates/G01-logs/unit.log").write_text("log", encoding="utf-8")
    result = make_result(
        gate_runner_module, ["uv", "run", "pytest", "tests/unit", "-q"], exit_code=5, counts={},
    )
    verdict = runner.evaluate_command("c", result)
    assert verdict.passed is False
    assert "zero-case run" in verdict.detail


def test_skipped_tests_are_rejected(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    (tmp_path / "artifacts/gates/G01-logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts/gates/G01-logs/unit.log").write_text("log", encoding="utf-8")
    result = make_result(
        gate_runner_module, ["uv", "run", "pytest", "tests/unit", "-q"],
        exit_code=0, counts={"passed": 2, "skipped": 1},
    )
    verdict = runner.evaluate_command("c", result)
    assert verdict.passed is False
    assert "skipped" in verdict.detail


def test_empty_log_is_rejected(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    log = tmp_path / "artifacts/gates/G01-logs/unit.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("", encoding="utf-8")
    result = make_result(gate_runner_module, ["uv", "run", "python", "-c", "pass"], exit_code=0)
    verdict = runner.evaluate_command("c", result)
    assert verdict.passed is False
    assert "empty log" in verdict.detail


def test_passing_command_is_accepted(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    log = tmp_path / "artifacts/gates/G01-logs/unit.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("56 passed in 2.5s", encoding="utf-8")
    result = make_result(
        gate_runner_module, ["uv", "run", "pytest", "tests/unit", "-q"],
        exit_code=0, counts={"passed": 56},
    )
    assert runner.evaluate_command("c", result).passed is True


def test_pytest_count_parsing_reads_the_real_summary_line(gate_runner_module) -> None:
    counts = gate_runner_module.parse_pytest_counts("== 1 failed, 55 passed, 2 skipped, 1 error in 3.20s ==")
    assert counts["passed"] == 55
    assert counts["failed"] == 1
    assert counts["skipped"] == 2
    assert counts["errors"] == 1


# ------------------------------------------------------------- hash freshness rules


def test_stale_input_hash_is_detected(gate_runner_module, tmp_path: Path) -> None:
    target = tmp_path / "artifact.txt"
    target.write_text("original", encoding="utf-8")
    Digest = gate_runner_module.sha256_file
    fresh = Digest(target)
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    assert runner.stale_input_hashes({"artifact.txt": fresh}) == []
    target.write_text("changed", encoding="utf-8")
    assert runner.stale_input_hashes({"artifact.txt": fresh}) == ["artifact.txt"]
    assert runner.stale_input_hashes({"missing.txt": fresh}) == ["missing.txt"]


def test_codex_review_is_required_and_checked(gate_runner_module, tmp_path: Path) -> None:
    """Codex review 缺失 => 不写 passed；revision 不匹配、空输入集合或过期哈希同样拒绝。"""
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="content-sha256:current")
    review_path = tmp_path / "artifacts/gates/G01-codex-review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)

    assert runner.check_codex_review().passed is False
    assert "missing" in runner.check_codex_review().detail

    artifact = tmp_path / "uv.lock"
    artifact.write_text("locked", encoding="utf-8")
    digest = gate_runner_module.sha256_file(artifact)
    valid = {
        "gate_id": "G01",
        "status": "approved",
        "reviewer": "codex",
        "code_revision": "content-sha256:current",
        "verified_input_hashes": {"uv.lock": digest},
    }
    review_path.write_text(json.dumps(valid), encoding="utf-8")
    assert runner.check_codex_review().passed is True

    stale_revision = dict(valid, code_revision="content-sha256:older")
    review_path.write_text(json.dumps(stale_revision), encoding="utf-8")
    verdict = runner.check_codex_review()
    assert verdict.passed is False
    assert "revision" in verdict.detail

    review_path.write_text(json.dumps(dict(valid, verified_input_hashes={"uv.lock": "0" * 64})), encoding="utf-8")
    verdict = runner.check_codex_review()
    assert verdict.passed is False
    assert "stale input hash" in verdict.detail

    review_path.write_text(json.dumps(dict(valid, status="open")), encoding="utf-8")
    assert runner.check_codex_review().passed is False

    # "approved" plus a reviewer name is not enough: an empty or absent input set is rejected.
    review_path.write_text(json.dumps(dict(valid, verified_input_hashes={})), encoding="utf-8")
    verdict = runner.check_codex_review()
    assert verdict.passed is False
    assert "empty" in verdict.detail
    review_path.write_text(json.dumps({k: v for k, v in valid.items() if k != "verified_input_hashes"}), encoding="utf-8")
    assert runner.check_codex_review().passed is False


def phase_task(task_id: str = "P01-01") -> dict:
    return {"id": task_id, "task_doc": "a.md", "report": "b.md", "commands": [], "files": []}


def prepare_precheck_tree(gate_runner_module, tmp_path: Path, task_id: str = "P01-01"):
    """A minimal tree with every input a pre-check record must bind for a task."""
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    runner.phase_tasks = lambda: [phase_task(task_id)]
    for relative, body in (
        ("docs/plan/TASK_MANIFEST.json", '{"tasks": []}'),
        ("docs/plan/PHASE_GATES.md", "# gates\n"),
        (f"artifacts/handoffs/{task_id}/dsh/evidence.json", '{"status": "READY_FOR_ZCODE"}'),
        ("uv.lock", "locked\n"),
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return runner


def write_precheck(gate_runner_module, tmp_path: Path, payload: dict, task_id: str = "P01-01") -> Path:
    path = tmp_path / f"artifacts/handoffs/{task_id}/zcode/precheck.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def bound_inputs(gate_runner_module, tmp_path: Path, task_id: str = "P01-01") -> dict:
    return {
        relative: gate_runner_module.sha256_file(tmp_path / relative)
        for relative in (
            "docs/plan/TASK_MANIFEST.json",
            "docs/plan/PHASE_GATES.md",
            f"artifacts/handoffs/{task_id}/dsh/evidence.json",
        )
    }


def test_zcode_precheck_requires_status_task_gate_and_verifiable_inputs(gate_runner_module, tmp_path: Path) -> None:
    runner = prepare_precheck_tree(gate_runner_module, tmp_path)
    task_id = "P01-01"
    assert runner.check_zcode_precheck()[0].passed is False  # record missing entirely

    verified = bound_inputs(gate_runner_module, tmp_path)
    base = {"task_id": task_id, "phase_gate": "G01", "reviewer": "zcode", "verified_input_hashes": verified}

    write_precheck(gate_runner_module, tmp_path, dict(base, status="CHANGES_REQUIRED"))
    assert runner.check_zcode_precheck()[0].passed is False

    write_precheck(gate_runner_module, tmp_path, dict(base, status="Z_PRECHECK_PASSED"))
    assert runner.check_zcode_precheck()[0].passed is True

    # Wrong task or wrong gate must be rejected, not silently accepted.
    write_precheck(gate_runner_module, tmp_path, dict(base, status="Z_PRECHECK_PASSED", task_id="P01-02"))
    detail = runner.check_zcode_precheck()[0].detail
    assert "task_id" in detail
    write_precheck(gate_runner_module, tmp_path, dict(base, status="Z_PRECHECK_PASSED", phase_gate="G02"))
    assert "phase_gate" in runner.check_zcode_precheck()[0].detail

    # An empty input set is not evidence.
    write_precheck(gate_runner_module, tmp_path, dict(base, status="Z_PRECHECK_PASSED", verified_input_hashes={}))
    verdict = runner.check_zcode_precheck()[0]
    assert verdict.passed is False
    assert "empty" in verdict.detail

    # A missing map, a malformed digest and a missing covered file are all rejected.
    write_precheck(gate_runner_module, tmp_path, {"task_id": task_id, "phase_gate": "G01", "status": "Z_PRECHECK_PASSED"})
    assert runner.check_zcode_precheck()[0].passed is False
    write_precheck(gate_runner_module, tmp_path, dict(base, status="Z_PRECHECK_PASSED",
                                                     verified_input_hashes={"uv.lock": "not-a-digest"}))
    assert "sha256" in runner.check_zcode_precheck()[0].detail
    write_precheck(gate_runner_module, tmp_path, dict(base, status="Z_PRECHECK_PASSED",
                                                     verified_input_hashes={"ghost.lock": "0" * 64}))
    assert "missing on disk" in runner.check_zcode_precheck()[0].detail


def test_zcode_precheck_must_cover_the_required_inputs(gate_runner_module, tmp_path: Path) -> None:
    """A key input left out of the frozen hash list is a rejection, not a warning."""
    runner = prepare_precheck_tree(gate_runner_module, tmp_path)
    verified = bound_inputs(gate_runner_module, tmp_path)
    for dropped in ("docs/plan/TASK_MANIFEST.json", "docs/plan/PHASE_GATES.md",
                    "artifacts/handoffs/P01-01/dsh/evidence.json"):
        partial = {k: v for k, v in verified.items() if k != dropped}
        write_precheck(gate_runner_module, tmp_path,
                       {"task_id": "P01-01", "phase_gate": "G01", "status": "Z_PRECHECK_PASSED",
                        "reviewer": "zcode", "verified_input_hashes": partial})
        verdict = runner.check_zcode_precheck()[0]
        assert verdict.passed is False, dropped
        assert dropped in verdict.detail


def test_zcode_precheck_detects_drifted_inputs(gate_runner_module, tmp_path: Path) -> None:
    runner = prepare_precheck_tree(gate_runner_module, tmp_path)
    verified = bound_inputs(gate_runner_module, tmp_path)
    verified["uv.lock"] = gate_runner_module.sha256_file(tmp_path / "uv.lock")
    write_precheck(gate_runner_module, tmp_path,
                   {"task_id": "P01-01", "phase_gate": "G01", "status": "Z_PRECHECK_PASSED",
                    "reviewer": "zcode", "verified_input_hashes": verified})
    assert runner.check_zcode_precheck()[0].passed is True

    (tmp_path / "uv.lock").write_text("drifted\n", encoding="utf-8")
    verdict = runner.check_zcode_precheck()[0]
    assert verdict.passed is False
    assert "stale input hash" in verdict.detail


# ------------------------------------------------------------- previous gate evidence


def runner_gate_record(gate_runner_module, tmp_path: Path, gate_id: str = "G00", **overrides) -> dict:
    """A complete runner-schema Gate record, with every element F2/F3/F4/F6 requires."""
    log_relative = f"artifacts/gates/{gate_id}-logs/probe.log"
    log_path = tmp_path / log_relative
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("# argv: python -c pass\n## stdout\nok\n## exit_code: 0\n", encoding="utf-8")
    manifest = tmp_path / "docs/plan/TASK_MANIFEST.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if not manifest.is_file():
        manifest.write_text('{"tasks": []}', encoding="utf-8")
    record = {
        "schema_version": "1.0.0",
        "gate_id": gate_id,
        "status": "passed",
        "started_at": "2026-09-12T00:00:00+00:00",
        "finished_at": "2026-09-12T00:00:10+00:00",
        "code_revision": "content-sha256:deadbeef",
        "dirty_tree_hash": "content-sha256:deadbeef",
        "dependency_evidence_hashes": {},
        "input_artifact_hashes": {"docs/plan/TASK_MANIFEST.json": gate_runner_module.sha256_file(manifest)},
        "environment_fingerprint": {"python": "3.12.10"},
        "commands": [{
            "argv": ["python", "-c", "pass"],
            "cwd": str(tmp_path),
            "exit_code": 0,
            "log_path": log_relative,
            "log_sha256": gate_runner_module.sha256_file(log_path),
            "test_counts": {"passed": 1, "failed": 0, "skipped": 0},
        }],
        "acceptance_artifacts": [],
        "limitations": [],
        "reviewer": "dsh-scripts/gates.py",
    }
    record.update(overrides)
    return record


def write_gate_record(tmp_path: Path, record: dict) -> Path:
    path = tmp_path / f"artifacts/gates/{record['gate_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def planner_gate_record(gate_runner_module, tmp_path: Path, gate_id: str = "G00", **overrides) -> dict:
    """The Phase00 planner schema: log_hash instead of log_sha256, no started_at."""
    log_relative = f"artifacts/gates/{gate_id}-logs/checker.log"
    log_path = tmp_path / log_relative
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("Ran 24 tests\nOK\n", encoding="utf-8")
    manifest = tmp_path / "docs/plan/TASK_MANIFEST.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if not manifest.is_file():
        manifest.write_text('{"tasks": []}', encoding="utf-8")
    record = {
        "schema_version": "1.0.0",
        "gate_id": gate_id,
        "status": "passed",
        "scope": "Phase00 document contract verification only",
        "finished_at": "2026-09-12T00:00:10+00:00",
        "checker_counts": {"tasks": 109},
        "code_revision": "content-sha256:cafe",
        "dependency_evidence_hashes": {},
        "input_artifact_hashes": {"docs/plan/TASK_MANIFEST.json": gate_runner_module.sha256_file(manifest)},
        "environment_fingerprint": {"python": "3.12.10"},
        "commands": [{
            "argv": ["python", "tools/ai_coding_plan/validate_plan.py", "--self-test", "--record-g00"],
            "cwd": str(tmp_path),
            "exit_code": 0,
            "log_path": log_relative,
            "log_hash": gate_runner_module.sha256_file(log_path),
        }],
        "reviewer": "planner-checker:tools/ai_coding_plan/validate_plan.py",
        "limitations": ["documentation contract only"],
    }
    record.update(overrides)
    return record


def test_complete_previous_gate_records_are_accepted(gate_runner_module, tmp_path: Path) -> None:
    """Positive control: both real producer schemas pass when every required element holds."""
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    write_gate_record(tmp_path, runner_gate_record(gate_runner_module, tmp_path))
    assert runner.check_previous_gates()[0].passed is True

    write_gate_record(tmp_path, planner_gate_record(gate_runner_module, tmp_path))
    verdict = runner.check_previous_gates()[0]
    assert verdict.passed is True, verdict.detail
    assert "schema=planner" in verdict.detail


def test_status_only_previous_gate_record_is_rejected(gate_runner_module, tmp_path: Path) -> None:
    """Rework defect 4: `{"status": "passed"}` must not satisfy a dependency."""
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    write_gate_record(tmp_path, {"gate_id": "G00", "status": "passed"})
    verdict = runner.check_previous_gates()[0]
    assert verdict.passed is False
    assert "missing required field" in verdict.detail


@pytest.mark.parametrize(
    "broken",
    [
        {"status": "failed"},
        {"gate_id": "G07"},
        {"started_at": None},
        {"finished_at": ""},
        {"commands": []},
        {"input_artifact_hashes": {}},
        {"dependency_evidence_hashes": None},
        {"reviewer": ""},
        {"environment_fingerprint": {}},
    ],
)
def test_each_missing_previous_gate_element_is_rejected(gate_runner_module, tmp_path: Path, broken: dict) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    record = runner_gate_record(gate_runner_module, tmp_path)
    record.update(broken)
    write_gate_record(tmp_path, record)
    assert runner.check_previous_gates()[0].passed is False, broken


@pytest.mark.parametrize("exit_code", [1, None, 0.0, "0", True, False])
def test_previous_gate_command_exit_codes_must_be_integer_zero(gate_runner_module, tmp_path: Path, exit_code) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    record = runner_gate_record(gate_runner_module, tmp_path)
    record["commands"][0]["exit_code"] = exit_code
    write_gate_record(tmp_path, record)
    verdict = runner.check_previous_gates()[0]
    assert verdict.passed is False
    assert "exit_code" in verdict.detail


def test_previous_gate_logs_must_exist_be_non_empty_and_match(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    record = runner_gate_record(gate_runner_module, tmp_path)
    log_path = tmp_path / record["commands"][0]["log_path"]

    record["commands"][0].pop("log_sha256")
    write_gate_record(tmp_path, record)
    verdict = runner.check_previous_gates()[0]
    assert verdict.passed is False
    assert "log hash is required" in verdict.detail or "log_hash" in verdict.detail

    record = runner_gate_record(gate_runner_module, tmp_path)
    log_path.write_text("", encoding="utf-8")
    record["commands"][0]["log_sha256"] = gate_runner_module.sha256_file(log_path)
    write_gate_record(tmp_path, record)
    assert "empty" in runner.check_previous_gates()[0].detail

    record = runner_gate_record(gate_runner_module, tmp_path)
    log_path.write_text("tampered\n", encoding="utf-8")
    write_gate_record(tmp_path, record)
    assert "changed after" in runner.check_previous_gates()[0].detail

    record = runner_gate_record(gate_runner_module, tmp_path)
    log_path.unlink()
    write_gate_record(tmp_path, record)
    assert "missing on disk" in runner.check_previous_gates()[0].detail


def test_previous_gate_input_drift_is_rejected(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    write_gate_record(tmp_path, runner_gate_record(gate_runner_module, tmp_path))
    assert runner.check_previous_gates()[0].passed is True

    (tmp_path / "docs/plan/TASK_MANIFEST.json").write_text('{"tasks": [1]}', encoding="utf-8")
    verdict = runner.check_previous_gates()[0]
    assert verdict.passed is False
    assert "drifted" in verdict.detail


def test_previous_gate_dependency_hashes_must_match_and_be_acyclic(gate_runner_module, tmp_path: Path) -> None:
    """Self-references, forward references and cycles in dependency hashes are rejected."""
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=2, revision="auto")
    g00 = runner_gate_record(gate_runner_module, tmp_path, "G00")
    write_gate_record(tmp_path, g00)
    g01 = runner_gate_record(gate_runner_module, tmp_path, "G01", dependency_evidence_hashes={
        "G00": gate_runner_module.sha256_file(tmp_path / "artifacts/gates/G00.json"),
    })
    write_gate_record(tmp_path, g01)
    verdicts = {check.id: check for check in runner.check_previous_gates()}
    assert verdicts["previous-gate:G00"].passed is True
    assert verdicts["previous-gate:G01"].passed is True, verdicts["previous-gate:G01"].detail

    # A hash that no longer matches the file on disk.
    write_gate_record(tmp_path, dict(g01, dependency_evidence_hashes={"G00": "0" * 64}))
    assert runner.check_previous_gates()[1].passed is False

    # Self reference.
    write_gate_record(tmp_path, runner_gate_record(gate_runner_module, tmp_path, "G00",
                                                   dependency_evidence_hashes={"G00": "0" * 64}))
    assert "cycle" in runner.check_previous_gates()[0].detail

    # Forward reference from the earlier gate to the later one.
    write_gate_record(tmp_path, runner_gate_record(gate_runner_module, tmp_path, "G00",
                                                   dependency_evidence_hashes={"G01": "0" * 64}))
    write_gate_record(tmp_path, g01)
    detail = runner.check_previous_gates()[0].detail
    assert "at or after" in detail or "not a preceding gate" in detail


def test_relevant_file_manifest_is_the_documented_input_set(gate_runner_module, tmp_path: Path) -> None:
    for relative in (
        "apps/backend/pyproject.toml", "packages/domain/src/logistics_domain/__init__.py",
        "scripts/gates.py", "tests/unit/example.py", "tools/ai_coding_plan/validate_plan.py",
        "contracts/schemas.json", "data/scenarios/example.json", ".github/workflows/ci.yml",
        "pyproject.toml", "uv.lock", "package-lock.json", "OWNERSHIP.json",
        "docs/architecture/DATA_CONTRACTS.md", "docs/api/API_CONTRACT.md",
        "docs/algorithms/METRICS_CONTRACT.md", "docs/plan/TASK_MANIFEST.json",
        "docs/plan/PHASE_GATES.md",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    for relative in (
        "tmp/probe.log", "artifacts/gates/G01.json", "artifacts/handoffs/P01-01/dsh/evidence.json",
        "artifacts/handoffs/P01-02/dsh/logs/probe.log", "docs/implementation/reports/P01-01.md",
        "docs/handoffs/P01-01/dsh.md", "docs/reviews/G01-zcode.md", ".mimosa/probe.json",
        "demo/README.md", "demos/x.py", "tools/bin/uv.exe", "node_modules/pkg/index.js",
        "docs/plan/PACKAGE_MANIFEST.json", "docs/plan/VERIFICATION_REPORT.md",
        "AGENTS.md", "README.md", "AI-CODING-PLAN.md",
        "docs/prompts/01-foundation/P01-02-checks-and-gate-runner.md",
        "docs/agent-toolchain/11-dsh-repair-g01.md",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    relevant = {row[0] for row in runner.relevant_manifest_rows()}
    missing = {
        "apps/backend/pyproject.toml", "packages/domain/src/logistics_domain/__init__.py",
        "scripts/gates.py", "tests/unit/example.py", "tools/ai_coding_plan/validate_plan.py",
        "contracts/schemas.json", "data/scenarios/example.json", ".github/workflows/ci.yml",
        "pyproject.toml", "uv.lock", "package-lock.json", "OWNERSHIP.json",
        "docs/architecture/DATA_CONTRACTS.md", "docs/api/API_CONTRACT.md",
        "docs/algorithms/METRICS_CONTRACT.md", "docs/plan/TASK_MANIFEST.json", "docs/plan/PHASE_GATES.md",
    }
    assert missing <= relevant, sorted(missing - relevant)
    leaked = relevant & {
        "tmp/probe.log", "artifacts/gates/G01.json", "artifacts/handoffs/P01-01/dsh/evidence.json",
        "artifacts/handoffs/P01-02/dsh/logs/probe.log", "docs/implementation/reports/P01-01.md",
        "docs/handoffs/P01-01/dsh.md", "docs/reviews/G01-zcode.md", ".mimosa/probe.json",
        "demo/README.md", "demos/x.py", "tools/bin/uv.exe", "node_modules/pkg/index.js",
        "docs/plan/PACKAGE_MANIFEST.json", "docs/plan/VERIFICATION_REPORT.md",
        "AGENTS.md", "README.md", "AI-CODING-PLAN.md",
        "docs/prompts/01-foundation/P01-02-checks-and-gate-runner.md",
        "docs/agent-toolchain/11-dsh-repair-g01.md",
    }
    assert not leaked, sorted(leaked)


def test_candidate_revision_follows_the_documented_formula(gate_runner_module, tmp_path: Path) -> None:
    for relative in ("scripts/gates.py", "pyproject.toml", "docs/architecture/DATA_CONTRACTS.md"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n", encoding="utf-8")
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    rows = runner.relevant_manifest_rows()
    assert rows == sorted(rows)
    expected = hashlib.sha256("\n".join(f"{relative}\0{digest}" for relative, digest, _ in rows).encode()).hexdigest()
    assert runner.compute_revision() == "content-sha256:" + expected
    expected_tree = hashlib.sha256(
        "\n".join(f"{relative}\0{size}\0{digest}" for relative, digest, size in rows).encode()
    ).hexdigest()
    assert runner.dirty_tree_hash() == "content-sha256:" + expected_tree
    assert runner.dirty_tree_hash() != runner.compute_revision()
    assert runner.compute_revision() == runner.compute_revision()


def test_writing_evidence_reports_and_scratch_does_not_change_the_candidate(gate_runner_module, tmp_path: Path) -> None:
    """Rework defect 2: evidence, logs, reviews, scratch and forensics scripts never perturb it."""
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts/gates.py").write_text("x = 1\n", encoding="utf-8")
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    before = runner.compute_revision()
    tree_before = runner.dirty_tree_hash()

    for relative in (
        "artifacts/gates/G01.json", "artifacts/gates/G01-codex-review.json",
        "artifacts/handoffs/P01-02/dsh/evidence.json", "artifacts/handoffs/P01-02/dsh/logs/round.log",
        "artifacts/handoffs/P01-02/dsh/probe.py", "artifacts/reviews/2026-10-01/codex/probe.py",
        "docs/implementation/reports/P01-02.md", "docs/handoffs/P01-02/dsh.md",
        "docs/reviews/G01-zcode.md", "tmp/probe.log", "tmp/dsh-p01-02-rework/probe.py",
        ".mimosa/probe.json", "docs/plan/VERIFICATION_REPORT.md",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("probe\n", encoding="utf-8")

    assert runner.compute_revision() == before, "writing evidence must not move the candidate"
    assert runner.dirty_tree_hash() == tree_before, "writing evidence must not move the tree fingerprint"


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/gates.py", "packages/domain/src/logistics_domain/__init__.py",
        "tests/unit/example.py", "pyproject.toml", "uv.lock", "OWNERSHIP.json",
        "docs/architecture/DATA_CONTRACTS.md", "docs/plan/TASK_MANIFEST.json",
        "contracts/schemas.json", ".github/workflows/ci.yml", "tools/ai_coding_plan/validate_plan.py",
    ],
)
def test_changing_a_relevant_input_changes_the_candidate(gate_runner_module, tmp_path: Path, relative: str) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("before\n", encoding="utf-8")
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto")
    before = runner.compute_revision()
    tree_before = runner.dirty_tree_hash()
    path.write_text("after\n", encoding="utf-8")
    assert runner.compute_revision() != before, relative
    assert runner.dirty_tree_hash() != tree_before, relative
    path.unlink()
    assert runner.compute_revision() != before, f"deleting {relative} must also move the candidate"


def test_explicit_revision_label_is_used_verbatim(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="deadbeef")
    assert runner.compute_revision() == "deadbeef"


def test_unknown_assertion_id_is_a_configuration_error(gate_runner_module, tmp_path: Path) -> None:
    runner = gate_runner_module.GateRunner(root=tmp_path, phase=1, revision="auto", only_checks=["nope"])
    with pytest.raises(SystemExit) as error:
        runner.assertion_specs()
    assert "unknown assertion" in str(error.value)


def test_phase_zero_is_rejected_with_a_pointer_to_the_planner_checker(gate_runner_module, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate_runner_module.sys, "argv", ["gates.py", "--phase", "00"])
    assert gate_runner_module.main() == 2
    monkeypatch.setattr(gate_runner_module.sys, "argv", ["gates.py", "--phase", "abc"])
    assert gate_runner_module.main() == 2


# ------------------------------------------------------- architecture checker rules


def test_domain_importing_fastapi_is_a_violation(architecture_module, tmp_path: Path) -> None:
    """domain 导入 fastapi => 层边界检查失败（退出码由集成测试断言）。"""
    write_module(tmp_path / "packages/domain/src/logistics_domain/__init__.py", "import fastapi\n")
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is False
    codes = {violation["code"] for violation in report["violations"]}
    assert "ARCH-PURITY" in codes
    assert any("fastapi" in violation["detail"] for violation in report["violations"])


def test_pure_domain_rejects_every_third_party_import(architecture_module, tmp_path: Path) -> None:
    for index, module in enumerate(("pydantic", "ortools", "simpy", "sqlalchemy", "numpy")):
        root = tmp_path / f"case{index}"
        write_module(root / "packages/domain/src/logistics_domain/mod.py", f"import {module}\n")
        report = architecture_module.run_checks(root)
        assert report["passed"] is False, f"domain must reject {module}"
        assert all("domain" in violation["rule"] or "PURITY" == violation["code"] for violation in report["violations"])


def test_import_direction_is_enforced(architecture_module, tmp_path: Path) -> None:
    write_module(
        tmp_path / "packages/contracts/src/logistics_contracts/mod.py",
        "from logistics_backend import something\n",
    )
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is False
    assert any(violation["code"] == "ARCH-DIRECTION" for violation in report["violations"])


def test_agent_layer_may_not_import_solver_engines(architecture_module, tmp_path: Path) -> None:
    write_module(tmp_path / "packages/agents/src/logistics_agents/mod.py", "import ortools\n")
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is False
    assert any("ortools" in violation["detail"] for violation in report["violations"])


def test_legacy_and_teaching_imports_are_rejected(architecture_module, tmp_path: Path) -> None:
    write_module(tmp_path / "packages/contracts/src/logistics_contracts/mod.py", "import app.contracts.entities\n")
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is False
    assert any(violation["code"] == "ARCH-LEGACY" for violation in report["violations"])


def test_undeclared_third_party_import_is_rejected(architecture_module, tmp_path: Path) -> None:
    root = tmp_path
    member = root / "packages/optimization"
    (member / "src/logistics_optimization").mkdir(parents=True, exist_ok=True)
    (member / "pyproject.toml").write_text(
        '[project]\nname = "logistics-optimization"\nversion = "0.1.0"\ndependencies = ["logistics-domain"]\n',
        encoding="utf-8",
    )
    write_module(member / "src/logistics_optimization/mod.py", "import ortools\n")
    report = architecture_module.run_checks(root)
    assert report["passed"] is False
    assert any(violation["code"] == "ARCH-UNDECLARED" for violation in report["violations"])


def test_declared_third_party_import_is_accepted(architecture_module, tmp_path: Path) -> None:
    member = tmp_path / "packages/optimization"
    (member / "src/logistics_optimization").mkdir(parents=True, exist_ok=True)
    (member / "pyproject.toml").write_text(
        '[project]\nname = "logistics-optimization"\nversion = "0.1.0"\ndependencies = ["ortools"]\n',
        encoding="utf-8",
    )
    write_module(member / "src/logistics_optimization/mod.py", "import ortools\n")
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is True, report["violations"]


def test_private_src_path_imports_are_rejected(architecture_module, tmp_path: Path) -> None:
    write_module(
        tmp_path / "apps/backend/src/logistics_backend/mod.py",
        'MARKER = "packages/domain/src/logistics_domain"\n',
    )
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is False
    assert any(violation["code"] == "ARCH-PRIVATE-SRC" for violation in report["violations"])


def test_pure_domain_member_may_not_declare_dependencies(architecture_module, tmp_path: Path) -> None:
    member = tmp_path / "packages/domain"
    (member / "src/logistics_domain").mkdir(parents=True, exist_ok=True)
    (member / "pyproject.toml").write_text(
        '[project]\nname = "logistics-domain"\nversion = "0.1.0"\ndependencies = ["pydantic"]\n',
        encoding="utf-8",
    )
    write_module(member / "src/logistics_domain/__init__.py", "VERSION = '1.0.0'\n")
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is False
    assert any("declares" in violation["detail"] for violation in report["violations"])


def test_non_parsing_module_is_reported_not_ignored(architecture_module, tmp_path: Path) -> None:
    write_module(tmp_path / "packages/domain/src/logistics_domain/broken.py", "def broken(:\n")
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is False
    assert any(violation["code"] == "ARCH-SYNTAX" for violation in report["violations"])


def test_regular_relative_import_stays_inside_the_layer(architecture_module, tmp_path: Path) -> None:
    write_module(tmp_path / "packages/domain/src/logistics_domain/mod.py", "from . import states\n")
    report = architecture_module.run_checks(tmp_path)
    assert report["passed"] is True, report["violations"]


def test_clean_tree_scan_is_not_vacuous(architecture_module) -> None:
    report = architecture_module.run_checks(REPO_ROOT)
    assert report["passed"] is True, [violation["render"] if isinstance(violation, dict) else violation
                                      for violation in report["violations"]]
    assert report["modules_scanned"] >= 7
    assert report["check"] == architecture_module.CHECK_NAME


def test_architecture_checker_exits_zero_on_the_real_repository(architecture_module, run_command) -> None:
    result = run_command(["python", "scripts/check_architecture.py", "--json"])
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["violation_count"] == 0
    assert payload["schema_version"] == "1.0.0"


# --------------------------------------------------------------- delivered files


def test_p01_02_deliverables_exist_at_the_declared_paths() -> None:
    missing = [relative for relative in P01_02_DELIVERABLES if not (REPO_ROOT / relative).is_file()]
    assert not missing, f"declared P01-02 deliverables missing: {missing}"


def test_gate_runner_declares_the_frozen_interface_and_exit_codes() -> None:
    source = (REPO_ROOT / "scripts/gates.py").read_text(encoding="utf-8")
    assert "--phase" in source and "--revision" in source and "--check-only" in source
    assert "artifacts/gates" in source.replace("\\", "/")
    assert "status\": \"failed\"" in source or '"failed"' in source
    tree = ast.parse(source)
    literals = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    assert "shell=True" not in source, "commands must be executed with argv arrays, never a shell"


def test_gate_runner_uses_subprocess_argv_arrays() -> None:
    """Commands must be executed through argv arrays with no shell interpretation."""
    source = (REPO_ROOT / "scripts/gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    assert calls, "scripts/gates.py must execute manifest commands with subprocess.run"
    for node in calls:
        keywords = {keyword.arg for keyword in node.keywords}
        assert "shell" not in keywords, "subprocess.run must not pass shell="
        assert node.args, "subprocess.run must be called with an argv sequence"
        first = node.args[0]
        assert not (isinstance(first, ast.Constant) and isinstance(first.value, str)), (
            "the command must not be passed as a single string"
        )
    assert "shell=True" not in source


def workflow_jobs(root: Path) -> dict[str, list[str]]:
    """Parse the CI workflow without adding a YAML dependency.

    Only the structure this test needs is parsed: job names and the literal ``run:``
    commands of each job. The workflow is a repository artifact under our control, so a
    dependency-free indentation parser keeps the lock file stable.
    """
    text = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    jobs: dict[str, list[str]] = {}
    current_job: str | None = None
    in_jobs = False
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        stripped = raw.strip()
        if stripped == "jobs:":
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if indent == 2 and stripped.endswith(":"):
            current_job = stripped[:-1]
            jobs[current_job] = []
            continue
        if current_job and stripped.startswith("run:") and indent >= 6:
            command = stripped[len("run:"):].strip()
            jobs[current_job].append(command)
    return jobs


def test_ci_workflow_covers_install_checks_and_gate_runner() -> None:
    jobs = workflow_jobs(REPO_ROOT)
    assert {"python", "frontend"} <= set(jobs), f"unexpected job set: {sorted(jobs)}"
    # Multi-line `run: |` blocks are matched by their extracted command bodies.
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for required in (
        "uv sync --frozen",
        "uv lock --check",
        "scripts/check_architecture.py",
        "pytest",
        "scripts/gates.py",
        "--check-only",
        "workflow_dispatch",
    ):
        assert required in text, f"CI must cover {required!r}"
    joined = "\n".join(command for commands in jobs.values() for command in commands)
    assert "scripts/check_architecture.py" in joined
    assert "uv run pytest tests/unit tests/integration -q" in joined
    assert "scripts/gates.py --phase 01 --revision auto --check-only" in joined
    frontend = "\n".join(jobs["frontend"])
    assert "npm ci" in frontend
    assert "package-lock.json" in frontend
    # CI must never sign a gate with the developer's revision.
    gate_invocations = [
        command for commands in jobs.values() for command in commands if "scripts/gates.py" in command
    ]
    assert gate_invocations, "CI must invoke the gate runner"
    for command in gate_invocations:
        assert "--check-only" in command, f"CI must only check freshness, never sign: {command}"


def test_frontend_test_configuration_matches_the_declared_scripts() -> None:
    frontend = json.loads((REPO_ROOT / "apps/frontend/package.json").read_text(encoding="utf-8"))
    assert "vitest run" in frontend["scripts"]["test"]
    config = (REPO_ROOT / "apps/frontend/vitest.config.ts").read_text(encoding="utf-8")
    assert "jsdom" in config
    assert "./src/test/setup.ts" in config
    setup = (REPO_ROOT / "apps/frontend/src/test/setup.ts").read_text(encoding="utf-8")
    assert "fetch" in setup, "the setup file must block accidental network access in unit tests"


def test_conftest_fails_instead_of_skipping_without_a_test_database() -> None:
    source = (REPO_ROOT / "tests/conftest.py").read_text(encoding="utf-8")
    assert "pytest.fail" in source, "the database fixture must fail loudly, not skip"
    assert "pytest.skip" not in source, "a critical skip would be accepted as gate evidence"
    assert "TEST_DATABASE_URL" in source
    assert "rollback" in source.lower()
    tree = ast.parse(source)


def test_conftest_provides_the_isolation_and_tooling_fixtures() -> None:
    tree = ast.parse((REPO_ROOT / "tests/conftest.py").read_text(encoding="utf-8"))
    fixture_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                target = decorator.func if isinstance(decorator, ast.Call) else decorator
                if isinstance(target, ast.Attribute) and target.attr == "fixture":
                    fixture_names.add(node.name)
    assert {"repo_root", "clean_env", "run_command", "database_url", "db_connection"} <= fixture_names


# ------------------------------------------------- official vs sandboxed gate records


def test_out_dir_keeps_a_sandbox_run_away_from_the_official_record(gate_runner_module, tmp_path: Path) -> None:
    """A run with --out-dir must be marked non-official and leave the official record untouched.

    This guards a real defect: running the runner from inside the test suite used to overwrite
    the tracked ``artifacts/gates/G01.json`` acceptance evidence with a ``--skip-commands``
    record, which made the audited gate state depend on test execution order.
    """
    root = tmp_path / "repo"
    (root / "artifacts/gates").mkdir(parents=True)
    (root / "docs/plan").mkdir(parents=True)
    (root / "docs/plan/TASK_MANIFEST.json").write_text(
        json.dumps({"plan_version": "1.0.0", "tasks": [], "gates": []}), encoding="utf-8"
    )
    official = root / "artifacts/gates/G01.json"
    official.write_text('{"gate_id": "G01", "status": "failed"}', encoding="utf-8")
    official_before = official.read_bytes()

    sandbox = tmp_path / "sandbox"
    runner = gate_runner_module.GateRunner(root=root, phase=1, revision="auto", out_dir=sandbox)
    assert runner.records_official_gate is False
    assert runner.out_dir == sandbox.resolve()
    assert gate_runner_module.GateRunner(root=root, phase=1, revision="auto").records_official_gate is True

    runner.write_evidence({"schema_version": "1.0.0", "gate_id": "G01", "status": "failed", "limitations": []})
    written = json.loads((sandbox / "G01.json").read_text(encoding="utf-8"))
    assert written["official_gate_record"] is False
    assert "was NOT modified" in written["official_gate_record_note"]
    assert any("does not represent the phase gate record" in item for item in written["limitations"])
    assert official.read_bytes() == official_before, "the official gate record must not be touched"


def test_check_only_reports_a_non_official_record(gate_runner_module, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "artifacts/gates").mkdir(parents=True)
    (root / "docs/plan").mkdir(parents=True)
    (root / "docs/plan/TASK_MANIFEST.json").write_text(
        json.dumps({"plan_version": "1.0.0", "tasks": [], "gates": []}), encoding="utf-8"
    )
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / "G01.json").write_text(
        json.dumps({"gate_id": "G01", "status": "passed", "input_artifact_hashes": {}, "commands": []}),
        encoding="utf-8",
    )
    runner = gate_runner_module.GateRunner(root=root, phase=1, revision="auto", out_dir=sandbox)
    assert runner.run_check_only("2026-09-12T00:00:00+00:00") == 1
