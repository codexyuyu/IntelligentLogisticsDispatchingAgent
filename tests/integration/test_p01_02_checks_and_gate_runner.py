"""Integration checks for the P01-02 gate runner and layered architecture checker.

Every test here crosses a real process boundary: the scripts are executed with
``subprocess`` against a real (synthetic or repository) tree, and the observable result is
the process exit code plus the written evidence file. That is what makes the four task
Test Cases meaningful:

1. ``命令 exit=1 => G01 failed 且进程非零``
2. ``domain 导入 fastapi => 层边界检查失败``
3. ``Codex review 缺失或 ZCode 输入哈希过期 => 不写 passed``
4. ``--check-only 全部成功 => 仅输出检查结果，不签收 Gate``
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

TASK_DOC = "docs/implementation/{task}.md"
TASK_REPORT = "docs/implementation/reports/{task}.md"
TASK_PROMPT = "docs/prompts/01-foundation/{task}-synthetic.md"


# ------------------------------------------------------------------ synthetic repo


class SyntheticRepo:
    """A throwaway gate repository with a controllable manifest and handoff records.

    The layer check runs the REAL scripts/check_architecture.py copied into the synthetic
    tree, and the baseline check reads a REAL docs/architecture/BASELINE_INVENTORY.json, so
    the positive control exercises the same code paths as the repository itself.
    """

    def __init__(self, root: Path, scripts_source: Path) -> None:
        self.root = root
        self.scripts_source = scripts_source

    def write(self, relative: str, content: str = "x\n", *, newline: str | None = "\n") -> Path:
        """Write a file with deterministic bytes (LF, never CRLF-translated)."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline=newline) as handle:
            handle.write(content)
        return path

    def write_json(self, relative: str, payload: dict) -> Path:
        return self.write(relative, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    # -- structure ---------------------------------------------------------------

    def install_scripts(self) -> None:
        for name in ("gates.py", "check_architecture.py"):
            self.write(f"scripts/{name}", (self.scripts_source / name).read_text(encoding="utf-8"))

    def install_uv_shim(self, python_executable: str, workspace_root: Path) -> None:
        """Give the sandbox the same `uv` the runner resolves on this host.

        The gate runner resolves ``uv`` from PATH and then from ``<root>/tools/bin``. The
        sandbox is not a uv project, so this shim understands exactly the two verbs the
        manifest uses: ``uv run python <args...>`` executes the workspace interpreter, and
        ``uv lock --check`` delegates to the real uv against the workspace lock file. The
        assertion logic under test is therefore unchanged.
        """
        shim = (
            "import pathlib, subprocess, sys\n"
            f"PYTHON = r'{python_executable}'\n"
            f"WORKSPACE = pathlib.Path(r'{workspace_root}')\n"
            "args = sys.argv[1:]\n"
            "if args[:2] == ['run', 'python']:\n"
            "    sys.exit(subprocess.run([PYTHON, *args[2:]]).returncode)\n"
            "if args[:1] == ['lock']:\n"
            "    real = WORKSPACE / 'tools/bin/uv.exe'\n"
            "    sys.exit(subprocess.run([str(real), *args], cwd=WORKSPACE).returncode)\n"
            "print('unsupported shim invocation: ' + ' '.join(args), file=sys.stderr)\n"
            "sys.exit(2)\n"
        )
        self.write("tools/bin/uv_shim.py", shim)
        if os.name == "nt":
            self.write("tools/bin/uv.cmd", f'@echo off\r\n"{python_executable}" "%~dp0uv_shim.py" %*\r\n', newline="")
        else:
            path = self.write("tools/bin/uv", f'#!/bin/sh\nexec "{python_executable}" "$(dirname "$0")/uv_shim.py" "$@"\n')
            path.chmod(0o755)

    def write_workspace_members(self) -> None:
        """A minimal but valid workspace: pure domain plus one declared dependency."""
        entries = {
            "packages/domain": ("logistics-domain", []),
            "packages/contracts": ("logistics-contracts", ["logistics-domain"]),
            "packages/optimization": ("logistics-optimization", ["logistics-domain", "ortools"]),
            "packages/simulation": ("logistics-simulation", ["logistics-domain", "simpy"]),
            "packages/agents": ("logistics-agents", ["logistics-contracts"]),
            "packages/evaluation": ("logistics-evaluation", ["logistics-contracts"]),
        }
        for relative, (name, dependencies) in entries.items():
            module = name.replace("-", "_")
            declared = ", ".join(f'"{item}"' for item in dependencies)
            self.write(
                f"{relative}/pyproject.toml",
                f'[project]\nname = "{name}"\nversion = "0.1.0"\ndependencies = [{declared}]\n',
            )
            self.write(f"{relative}/src/{module}/__init__.py", f'PACKAGE_NAME = "{name}"\n')
        self.write(
            "apps/backend/pyproject.toml",
            '[project]\nname = "logistics-backend"\nversion = "0.1.0"\ndependencies = ["fastapi"]\n',
        )
        self.write("apps/backend/src/logistics_backend/__init__.py", 'API_PREFIX = "/api/v1"\n')

    def write_locks(self) -> None:
        self.write("uv.lock", "version = 1\nrevision = 3\n")
        self.write_json("package-lock.json", {"name": "synthetic", "lockfileVersion": 3, "packages": {}})

    def write_baseline(self) -> dict:
        """A real baseline inventory with one registered demo file."""
        content = "# synthetic legacy baseline\n"
        self.write("demo/README.md", content)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.write("demo.zip", "synthetic-archive")
        inventory = {
            "schema_version": "1.0.0",
            "entries": [
                {
                    "source_path": "demo/README.md",
                    "sha256": digest,
                    "owner": "A",
                    "disposition": "reference",
                    "target_path": None,
                    "capability_evidence": "scaffold only",
                }
            ],
        }
        self.write_json("docs/architecture/BASELINE_INVENTORY.json", inventory)
        self.write_json(
            "artifacts/handoffs/P01-01/dsh/evidence.json",
            {
                "schema_version": "1.0.0",
                "task_id": "P01-01",
                "status": "READY_FOR_ZCODE",
                "legacy_demo": {
                    "path": "demo/",
                    "file_count": len(inventory["entries"]),
                    "tree_sha256": digest,
                    "demo_zip": {
                        "path": "demo.zip",
                        "sha256": hashlib.sha256((self.root / "demo.zip").read_bytes()).hexdigest(),
                    },
                },
            },
        )
        return inventory

    # -- manifest and records ----------------------------------------------------

    def manifest(self, phase: int, task_id: str, commands: list[str], previous_gate_status: str = "passed") -> dict:
        """Build a manifest whose only phase is ``phase`` and whose previous gates are stubbed.

        Previous gates are written as *complete* controlled evidence records (commands, real
        logs, frozen inputs and dependency hashes), because the runner now validates them the
        way F2/F3/F4/F6 require instead of reading their status field alone.
        """
        assert phase >= 1
        gates = [
            {"id": f"G{index:02d}", "phase": index, "deps": [], "status": "not_run", "blocks": []}
            for index in range(phase)
        ]
        gates[phase - 1] = {
            "id": f"G{phase:02d}",
            "phase": phase,
            "deps": [task_id],
            "status": "not_run",
            "blocks": ["G%02d" % (phase + 1)],
        }
        tasks = [
            {
                "id": task_id,
                "phase": phase,
                "commands": commands,
                "task_doc": TASK_DOC.format(task=task_id),
                "report": TASK_REPORT.format(task=task_id),
                "prompt": TASK_PROMPT.format(task=task_id),
                "files": [],
                "status": "planned",
                "owner": "A",
            }
        ]
        payload = {"plan_version": "1.0.0", "tasks": tasks, "gates": gates}
        self.gate_id = f"G{phase:02d}"
        self.write_json("docs/plan/TASK_MANIFEST.json", payload)
        self.write("docs/plan/PHASE_GATES.md", "# synthetic gate protocol\n")
        self.write(TASK_DOC.format(task=task_id), "# task doc\n")
        self.write(TASK_REPORT.format(task=task_id), "# report\n")
        self.write(TASK_PROMPT.format(task=task_id), "# synthetic task prompt\n")
        for index in range(phase):
            gate_id = f"G{index:02d}"
            dependencies = {}
            if index:
                previous = f"G{index - 1:02d}"
                dependencies[previous] = self.digest(f"artifacts/gates/{previous}.json")
            self.gate_record(gate_id, status=previous_gate_status, dependencies=dependencies)
        return payload

    # -- evidence helpers --------------------------------------------------------

    def digest(self, relative: str) -> str:
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def gate_record(
        self,
        gate_id: str,
        *,
        status: str = "passed",
        dependencies: dict | None = None,
        **overrides,
    ) -> dict:
        """A complete, controlled Gate evidence record for a previous phase.

        Every element the frozen contract requires is present and real: a raw command log on
        disk with its hash, argv/cwd/integer exit_code, frozen input hashes and dependency
        hashes. Calls overwrite the record so a negative case can break exactly one element.
        """
        log_relative = f"artifacts/gates/{gate_id}-logs/probe.log"
        log_path = self.write(
            log_relative,
            f"# check: {gate_id}-cmd1\n# argv: [\"python\", \"-c\", \"pass\"]\n"
            f"# cwd: {self.root}\n\n## stdout\nok\n\n## stderr\n\n## exit_code: 0\n",
        )
        record = {
            "schema_version": "1.0.0",
            "gate_id": gate_id,
            "phase": int(gate_id[1:]),
            "status": status,
            "started_at": "2026-09-12T00:00:00+00:00",
            "finished_at": "2026-09-12T00:00:10+00:00",
            "code_revision": "content-sha256:synthetic",
            "dirty_tree_hash": "content-sha256:synthetic",
            "dependency_evidence_hashes": dict(dependencies or {}),
            "input_artifact_hashes": {
                "docs/plan/TASK_MANIFEST.json": self.digest("docs/plan/TASK_MANIFEST.json"),
            },
            "environment_fingerprint": {"python": "3.12.10", "os": "synthetic"},
            "commands": [
                {
                    "check_id": f"{gate_id}-cmd1",
                    "argv": ["python", "-c", "pass"],
                    "cwd": str(self.root),
                    "exit_code": 0,
                    "duration_ms": 1,
                    "log_path": log_relative,
                    "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
                }
            ],
            "acceptance_artifacts": [],
            "limitations": ["synthetic controlled record"],
            "reviewer": "dsh-scripts/gates.py",
        }
        record.update(overrides)
        self.write_json(f"artifacts/gates/{gate_id}.json", record)
        return record

    def precheck_inputs(self, task_id: str, extras: dict | None = None) -> dict:
        """The input hash map a ZCode pre-check record must bind for this task."""
        verified = {
            "docs/plan/TASK_MANIFEST.json": self.digest("docs/plan/TASK_MANIFEST.json"),
            "docs/plan/PHASE_GATES.md": self.digest("docs/plan/PHASE_GATES.md"),
            TASK_PROMPT.format(task=task_id): self.digest(TASK_PROMPT.format(task=task_id)),
            f"artifacts/handoffs/{task_id}/dsh/evidence.json": self.digest(
                f"artifacts/handoffs/{task_id}/dsh/evidence.json"
            ),
        }
        verified.update(extras or {})
        return verified

    def content_revision(self) -> str:
        """The revision the runner will compute for this tree at this moment."""
        sys.path.insert(0, str(self.scripts_source))
        try:
            import importlib

            module = importlib.import_module("gates")
        finally:
            sys.path.pop(0)
        return module.GateRunner(root=self.root, phase=1, revision="auto").compute_revision()

    def write_dsh_evidence(self, task_id: str, status: str = "READY_FOR_ZCODE") -> Path:
        return self.write_json(
            f"artifacts/handoffs/{task_id}/dsh/evidence.json",
            {"schema_version": "1.0.0", "task_id": task_id, "status": status},
        )

    def write_zcode_precheck(self, task_id: str, status: str, verified: dict | None = None) -> Path:
        return self.write_json(
            f"artifacts/handoffs/{task_id}/zcode/precheck.json",
            {
                "schema_version": "1.0.0",
                "task_id": task_id,
                "phase_gate": getattr(self, "gate_id", "G01"),
                "status": status,
                "reviewer": "zcode",
                "verified_input_hashes": verified if verified is not None else self.precheck_inputs(task_id),
            },
        )

    def write_codex_review(self, gate_id: str, status: str, revision: str, verified: dict | None = None) -> Path:
        return self.write_json(
            f"artifacts/gates/{gate_id}-codex-review.json",
            {
                "schema_version": "1.0.0",
                "gate_id": gate_id,
                "status": status,
                "reviewer": "codex",
                "code_revision": revision,
                "verified_input_hashes": verified
                if verified is not None
                else {"docs/plan/TASK_MANIFEST.json": self.digest("docs/plan/TASK_MANIFEST.json")},
            },
        )

    def gate(self, gate_id: str) -> dict | None:
        path = self.root / f"artifacts/gates/{gate_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def run_gate(self, run_command, *extra: str, phase: int = 1, revision: str = "auto"):
        argv = [
            "python", "scripts/gates.py",
            "--phase", f"{phase:02d}",
            "--revision", revision,
            "--root", str(self.root),
            *extra,
        ]
        return run_command(argv)

    def run_gate_subset(self, run_command, assertions: list[str], *, revision: str = "auto"):
        """Run only the named assertions, exactly as `--assertion` documents.

        The synthetic sandbox has no uv-managed environment, so the two assertions that
        need one (six-package import probe, `uv lock --check`) are excluded here and are
        covered against the real repository instead.
        """
        extra: list[str] = []
        for name in assertions:
            extra += ["--assertion", name]
        return self.run_gate(run_command, *extra, revision=revision)


# Assertions that a sandbox without a uv environment can genuinely satisfy.
SANDBOX_ASSERTIONS = ["layer-boundaries", "runner-fails-closed", "legacy-demo-untouched"]


def gate_runner_specs() -> list:
    """The phase assertion specs declared by the runner under test (all five for phase 1)."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import importlib

        module = importlib.import_module("gates")
    finally:
        sys.path.pop(0)
    return list(module.PHASE_ASSERTIONS[1])


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> SyntheticRepo:
    repo = SyntheticRepo(tmp_path, REPO_ROOT / "scripts")
    repo.install_scripts()
    return repo


def satisfiable_phase(
    repo: SyntheticRepo,
    *,
    command: str | None = None,
    with_review: bool = True,
    python_executable: str | None = None,
) -> str:
    """Build a phase whose acceptance assertions can genuinely all pass.

    Returns the exact content revision the runner will compute, so a review record can be
    bound to it (the runner rejects a review that covers a different revision).

    Order matters: ``write_baseline()`` owns the DSH evidence file, so it runs BEFORE the
    ZCode pre-check binds that file's hash, and nothing rewrites it afterwards.
    """
    repo.manifest(1, "P01-01", [command or passing_command()])
    repo.write_workspace_members()
    repo.write_locks()
    if python_executable:
        repo.install_uv_shim(python_executable, REPO_ROOT)
    repo.write_baseline()
    lock_digest = hashlib.sha256((repo.root / "uv.lock").read_bytes()).hexdigest()
    repo.write_zcode_precheck("P01-01", "Z_PRECHECK_PASSED", repo.precheck_inputs("P01-01", {"uv.lock": lock_digest}))
    revision = repo.content_revision()
    if with_review:
        repo.write_codex_review("G01", "approved", revision=revision)
    return revision


def passing_command() -> str:
    return 'python -c "print(\'ok\')"'


def failing_command() -> str:
    return 'python -c "import sys; sys.exit(1)"'


# ------------------------------------------------------ Test Case 1: exit=1 => failed


def test_exit_one_command_fails_the_gate_and_exits_nonzero(synthetic_repo: SyntheticRepo, run_command, python_executable) -> None:
    """Test Case 1: 命令 exit=1 => G01 failed 且进程非零."""
    revision = satisfiable_phase(synthetic_repo, command=failing_command(), python_executable=python_executable)

    result = synthetic_repo.run_gate(run_command, revision=revision)
    assert result.returncode != 0, f"a failing command must make the runner exit non-zero\n{result.stdout}"

    evidence = synthetic_repo.gate("G01")
    assert evidence is not None, "the runner must still record the failed attempt"
    assert evidence["status"] == "failed"
    assert "P01-01-cmd1" in evidence["failed_checks"]
    command = next(item for item in evidence["commands"] if item["check_id"] == "P01-01-cmd1")
    assert command["exit_code"] == 1
    log = synthetic_repo.root / command["log_path"]
    assert log.is_file() and log.stat().st_size > 0, "original logs must be preserved"
    assert command["log_sha256"] == hashlib.sha256(log.read_bytes()).hexdigest()


def test_passing_phase_writes_a_complete_passed_record(synthetic_repo: SyntheticRepo, run_command, python_executable) -> None:
    """The positive control: a fully satisfied phase must sign, with every evidence field."""
    revision = satisfiable_phase(synthetic_repo, python_executable=python_executable)

    first = synthetic_repo.run_gate_subset(run_command, SANDBOX_ASSERTIONS, revision=revision)
    assert first.returncode == 0, first.stdout
    evidence = synthetic_repo.gate("G01")
    assert evidence["status"] == "passed", evidence["failed_checks"]
    for field in (
        "schema_version", "gate_id", "status", "started_at", "finished_at", "code_revision",
        "dirty_tree_hash", "dependency_evidence_hashes", "input_artifact_hashes",
        "environment_fingerprint", "commands", "acceptance_artifacts", "limitations", "reviewer",
    ):
        assert field in evidence, f"evidence must record {field}"
    assert evidence["dependency_evidence_hashes"].get("G00")
    assert evidence["code_revision"] == revision
    assert evidence["commands"][0]["exit_code"] == 0
    assert evidence["reviewer"] == "dsh-scripts/gates.py"
    assert not evidence["failed_checks"], evidence["failed_checks"]
    assert {check["id"] for check in evidence["acceptance_assertions"]} == set(SANDBOX_ASSERTIONS)
    # The assertions a sandbox cannot satisfy are still declared by the phase itself.
    assert {spec.id for spec in gate_runner_specs()} >= set(SANDBOX_ASSERTIONS)

    # A second run must not erase the previous attempt.
    second = synthetic_repo.run_gate_subset(run_command, SANDBOX_ASSERTIONS, revision=revision)
    assert second.returncode == 0, second.stdout
    assert synthetic_repo.gate("G01")["runs"], "the previous attempt must stay recorded"


# ------------------------------------------- Test Case 2: domain importing fastapi


def test_domain_importing_fastapi_fails_the_layer_check(synthetic_repo: SyntheticRepo, run_command, python_executable) -> None:
    """Test Case 2: domain 导入 fastapi => 层边界检查失败."""
    synthetic_repo.write("packages/domain/src/logistics_domain/__init__.py", "import fastapi\n")
    result = run_command(
        ["python", "scripts/check_architecture.py", "--root", str(synthetic_repo.root), "--json"],
        cwd=synthetic_repo.root,
    )
    assert result.returncode != 0, "the layer check must exit non-zero on a violation"
    report = json.loads(result.stdout)
    assert report["passed"] is False
    assert report["violation_count"] >= 1
    violation = report["violations"][0]
    assert violation["code"] == "ARCH-PURITY"
    assert violation["path"] == "packages/domain/src/logistics_domain/__init__.py"
    assert violation["line"] == 1
    assert "fastapi" in violation["detail"]


def test_layer_violation_makes_the_phase_gate_fail(synthetic_repo: SyntheticRepo, run_command, python_executable) -> None:
    """The layer check is wired into the phase acceptance assertions, not only standalone."""
    revision = satisfiable_phase(synthetic_repo, python_executable=python_executable)
    synthetic_repo.write("packages/domain/src/logistics_domain/__init__.py", "import fastapi\n")

    result = synthetic_repo.run_gate_subset(run_command, ["layer-boundaries"], revision=revision)
    assert result.returncode != 0
    evidence = synthetic_repo.gate("G01")
    assert evidence["status"] == "failed"
    assert "layer-boundaries" in evidence["failed_checks"]
    layer_check = next(item for item in evidence["acceptance_assertions"] if item["id"] == "layer-boundaries")
    assert layer_check["passed"] is False
    assert "exit_code" in layer_check["detail"]


# ---------------------------------- Test Case 3: missing review / stale precheck hash


def test_missing_codex_review_prevents_a_passed_record(
    synthetic_repo: SyntheticRepo, run_command, python_executable
) -> None:
    """Test Case 3a: Codex review 缺失 => 不写 passed."""
    satisfiable_phase(synthetic_repo, with_review=False, python_executable=python_executable)

    result = synthetic_repo.run_gate(run_command)
    assert result.returncode != 0
    evidence = synthetic_repo.gate("G01")
    assert evidence["status"] == "failed"
    assert "codex-review" in evidence["failed_checks"]
    review_check = next(item for item in evidence["record_checks"] if item["id"] == "codex-review")
    assert "missing" in review_check["detail"]


# ------------------------------------- previous Gate evidence (controlled temp repository)


def gate_evidence_only(
    repo: SyntheticRepo,
    run_command,
    out_dir: Path,
    *,
    phase: int = 1,
    revision: str = "auto",
):
    """Run the runner without executing phase commands, writing evidence into ``out_dir``."""
    result = repo.run_gate(run_command, "--skip-commands", "--out-dir", str(out_dir),
                           phase=phase, revision=revision)
    evidence = json.loads((out_dir / f"G{phase:02d}.json").read_text(encoding="utf-8"))
    return result, evidence


def previous_gate_detail(evidence: dict, gate_id: str = "G00") -> str:
    return next(item["detail"] for item in evidence["record_checks"] if item["id"] == f"previous-gate:{gate_id}")


def test_complete_previous_gate_evidence_is_accepted(synthetic_repo: SyntheticRepo, run_command, tmp_path: Path) -> None:
    """Positive control: a fully controlled G00 record must not be reported as a blocker."""
    synthetic_repo.manifest(1, "P01-01", [passing_command()])
    result, evidence = gate_evidence_only(synthetic_repo, run_command, tmp_path / "out")
    assert result.returncode != 0, "the phase is still missing its own review records"
    assert "previous-gate:G00" not in evidence["failed_checks"], previous_gate_detail(evidence)
    assert "status=passed" in previous_gate_detail(evidence)


def test_status_only_previous_gate_record_is_rejected(synthetic_repo: SyntheticRepo, run_command, tmp_path: Path) -> None:
    """Rework defect 4, end to end: {"status": "passed"} cannot satisfy a dependency."""
    synthetic_repo.manifest(1, "P01-01", [passing_command()])
    synthetic_repo.write_json("artifacts/gates/G00.json", {"gate_id": "G00", "status": "passed"})

    result, evidence = gate_evidence_only(synthetic_repo, run_command, tmp_path / "out")
    assert result.returncode != 0
    assert "previous-gate:G00" in evidence["failed_checks"]
    assert "missing required field" in previous_gate_detail(evidence)


def test_previous_gate_input_drift_is_rejected(synthetic_repo: SyntheticRepo, run_command, tmp_path: Path) -> None:
    """A frozen input that changed after the earlier gate was recorded invalidates it (F6)."""
    payload = synthetic_repo.manifest(1, "P01-01", [passing_command()])
    synthetic_repo.write_json("docs/plan/TASK_MANIFEST.json", dict(payload, comment="edited after G00"))

    result, evidence = gate_evidence_only(synthetic_repo, run_command, tmp_path / "out")
    assert result.returncode != 0
    assert "previous-gate:G00" in evidence["failed_checks"]
    assert "drifted" in previous_gate_detail(evidence)


def test_previous_gate_nonzero_command_and_missing_log_are_rejected(
    synthetic_repo: SyntheticRepo, run_command, tmp_path: Path
) -> None:
    """F3/F4: a recorded command that failed, or whose raw log is gone, invalidates the gate."""
    synthetic_repo.manifest(1, "P01-01", [passing_command()])
    record = json.loads((synthetic_repo.root / "artifacts/gates/G00.json").read_text(encoding="utf-8"))
    record["commands"][0]["exit_code"] = 1
    synthetic_repo.write_json("artifacts/gates/G00.json", record)
    _, evidence = gate_evidence_only(synthetic_repo, run_command, tmp_path / "out-nonzero")
    assert "exit_code=1" in previous_gate_detail(evidence)

    synthetic_repo.manifest(1, "P01-01", [passing_command()])
    record = json.loads((synthetic_repo.root / "artifacts/gates/G00.json").read_text(encoding="utf-8"))
    (synthetic_repo.root / record["commands"][0]["log_path"]).unlink()
    _, evidence = gate_evidence_only(synthetic_repo, run_command, tmp_path / "out-nolog")
    assert "missing on disk" in previous_gate_detail(evidence)


def test_stale_zcode_input_hash_prevents_a_passed_record(
    synthetic_repo: SyntheticRepo, run_command, python_executable
) -> None:
    """Test Case 3b: ZCode 输入哈希过期 => 不写 passed."""
    satisfiable_phase(synthetic_repo, python_executable=python_executable)
    lock = synthetic_repo.root / "uv.lock"

    lock.write_text("version = 1\n# drifted after the pre-check\n", encoding="utf-8")

    result = synthetic_repo.run_gate(run_command)
    assert result.returncode != 0
    evidence = synthetic_repo.gate("G01")
    assert evidence["status"] == "failed"
    assert "zcode-precheck:P01-01" in evidence["failed_checks"]
    detail = next(item for item in evidence["record_checks"] if item["id"] == "zcode-precheck:P01-01")["detail"]
    assert "stale input hash" in detail


def test_missing_zcode_precheck_prevents_a_passed_record(
    synthetic_repo: SyntheticRepo, run_command, python_executable
) -> None:
    satisfiable_phase(synthetic_repo, python_executable=python_executable)
    (synthetic_repo.root / "artifacts/handoffs/P01-01/zcode/precheck.json").unlink()

    result = synthetic_repo.run_gate(run_command)
    assert result.returncode != 0
    assert "zcode-precheck:P01-01" in synthetic_repo.gate("G01")["failed_checks"]


def test_unfinished_task_evidence_prevents_a_passed_record(
    synthetic_repo: SyntheticRepo, run_command, python_executable
) -> None:
    task_id = "P01-01"
    satisfiable_phase(synthetic_repo, python_executable=python_executable)
    synthetic_repo.write_dsh_evidence(task_id, status="BLOCKED")

    result = synthetic_repo.run_gate(run_command)
    assert result.returncode != 0
    assert f"dsh-evidence:{task_id}" in synthetic_repo.gate("G01")["failed_checks"]


def test_failed_dependency_gate_prevents_a_passed_record(
    synthetic_repo: SyntheticRepo, run_command
) -> None:
    task_id = "P01-01"
    synthetic_repo.manifest(2, task_id, [passing_command()], previous_gate_status="failed")
    synthetic_repo.write_dsh_evidence(task_id)
    synthetic_repo.write_zcode_precheck(task_id, "Z_PRECHECK_PASSED")
    revision = synthetic_repo.content_revision()
    synthetic_repo.write_codex_review("G02", "approved", revision=revision)

    result = synthetic_repo.run_gate(run_command, phase=2, revision=revision)
    assert result.returncode != 0
    assert "previous-gate:G01" in synthetic_repo.gate("G02")["failed_checks"]


# ------------------------------------------- Test Case 4: --check-only never signs


def test_check_only_does_not_sign_and_does_not_write(
    synthetic_repo: SyntheticRepo, run_command, python_executable
) -> None:
    """Test Case 4: --check-only 全部成功 => 仅输出检查结果，不签收 Gate."""
    revision = satisfiable_phase(synthetic_repo, python_executable=python_executable)

    before = synthetic_repo.gate("G01")
    assert before is None or before["status"] != "passed"

    result = synthetic_repo.run_gate(run_command, "--check-only", revision=revision)
    assert "check-only" in result.stdout
    assert "gate not signed" in result.stdout
    after = synthetic_repo.gate("G01")
    if before is None:
        assert after is None, "check-only must not create an evidence file"
    else:
        assert after == before, "check-only must not modify an existing evidence file"
    assert not (synthetic_repo.root / "artifacts/gates/G01-logs").exists(), (
        "check-only must not execute phase commands"
    )


def test_check_only_reports_stale_inputs_without_signing(
    synthetic_repo: SyntheticRepo, run_command, python_executable
) -> None:
    revision = satisfiable_phase(synthetic_repo, python_executable=python_executable)
    lock = synthetic_repo.root / "uv.lock"
    signed = synthetic_repo.run_gate_subset(run_command, SANDBOX_ASSERTIONS, revision=revision)
    assert signed.returncode == 0, signed.stdout
    assert synthetic_repo.gate("G01")["status"] == "passed"

    # Drift a recorded input: the freshness check must notice and refuse to claim success.
    lock.write_text("version = 1\n# drift\n", encoding="utf-8")
    result = synthetic_repo.run_gate(run_command, "--check-only", revision=revision)
    assert result.returncode != 0
    assert "STALE" in result.stdout
    assert "gate not signed" in result.stdout


# ------------------------------------------------------- the real repository state


def test_repository_phase_one_gate_is_fail_closed(run_command, load_json, repo_root: Path, tmp_path: Path) -> None:
    """Live failure-closure probe against the real repository, restricted to true invariants.

    The gate must stay failed here, but the *reason set* depends on the live repository state
    (which is exactly why the old hardcoded missing-record assertion broke as soon as the
    P01-01 pre-check appeared). So this test asserts only invariants that hold for the current
    inputs and cross-checks each review verdict against an independent recomputation of the
    same facts, computed in this test rather than imported from the runner.

    It runs with ``--skip-commands`` (executing the phase commands here would re-enter this
    suite) and with ``--out-dir`` pointing at a temporary directory, so it NEVER overwrites the
    official ``artifacts/gates/G01.json`` record produced by the acceptance run. The official
    record's hash is captured BEFORE the call and compared AFTER it.
    """
    official = repo_root / "artifacts/gates/G01.json"
    official_before = hashlib.sha256(official.read_bytes()).hexdigest() if official.is_file() else None

    out_dir = tmp_path / "sandbox-gates"
    result = run_command([
        "python", "scripts/gates.py", "--phase", "01", "--revision", "auto",
        "--skip-commands", "--out-dir", str(out_dir),
    ], timeout=1800)
    assert result.returncode != 0, "the gate must not pass while phase records are missing"

    evidence_path = out_dir / "G01.json"
    assert evidence_path.is_file(), "the sandbox run must write its own record"
    evidence = load_json(evidence_path)
    assert evidence["gate_id"] == "G01"
    assert evidence["status"] == "failed"
    assert evidence["official_gate_record"] is False, "a --out-dir record must be marked non-official"
    assert evidence["code_revision"].startswith("content-sha256:")
    assert evidence["dependency_evidence_hashes"].get("G00")
    # The escape hatch must be visible in the record, never silent.
    skipped = [check for check in evidence["acceptance_assertions"] if check["id"] != "runner-fails-closed"]
    assert skipped and all("skip-commands" in check["detail"] for check in skipped)

    failed = set(evidence["failed_checks"])

    # 1. The Codex phase review genuinely does not exist yet, so the gate cannot be signed.
    if not (repo_root / "artifacts/gates/G01-codex-review.json").is_file():
        assert "codex-review" in failed

    # 2. The P01-01 pre-check verdict must agree with an independent freshness recomputation.
    precheck = repo_root / "artifacts/handoffs/P01-01/zcode/precheck.json"
    if precheck.is_file():
        payload = json.loads(precheck.read_text(encoding="utf-8"))
        recorded = payload.get("verified_input_hashes") or {}
        drifted = sorted(
            relative for relative, digest in recorded.items()
            if not (repo_root / relative).is_file()
            or hashlib.sha256((repo_root / relative).read_bytes()).hexdigest() != digest
        )
        prompt = repo_root / "docs/prompts/01-foundation/P01-01-workspace-bootstrap.md"
        required_covered = all(
            item in recorded for item in ("docs/plan/TASK_MANIFEST.json", "docs/plan/PHASE_GATES.md")
        )
        expected_ok = bool(recorded) and not drifted and required_covered and prompt.is_file()
        assert ("zcode-precheck:P01-01" not in failed) == expected_ok, (
            f"runner verdict disagrees with the recomputed pre-check state: drifted={drifted}, "
            f"covered={required_covered}"
        )
    else:
        assert "zcode-precheck:P01-01" in failed

    # 3. The same cross-check for the previous gate record's frozen inputs.
    g00 = repo_root / "artifacts/gates/G00.json"
    if g00.is_file():
        record = json.loads(g00.read_text(encoding="utf-8"))
        drifted = sorted(
            relative for relative, digest in (record.get("input_artifact_hashes") or {}).items()
            if not (repo_root / relative).is_file()
            or hashlib.sha256((repo_root / relative).read_bytes()).hexdigest() != digest
        )
        assert ("previous-gate:G00" in failed) == bool(drifted), (
            f"runner verdict disagrees with the recomputed G00 input state: drifted={drifted}"
        )
    else:
        assert "previous-gate:G00" in failed

    # The official record must not have been touched by this test.
    assert official.is_file(), "the acceptance run must have produced the official G01 record"
    assert hashlib.sha256(official.read_bytes()).hexdigest() == official_before, (
        "a sandboxed run must not modify the official gate record"
    )


def test_real_gate_runner_executes_a_real_probe_command(run_command, repo_root: Path, tmp_path: Path) -> None:
    """The probe assertion must really spawn a process and preserve its raw log.

    The run is limited to the failure-closure assertion (``--skip-commands``) and writes to a
    temporary ``--out-dir`` so the official gate record stays untouched.
    """
    out_dir = tmp_path / "probe-gates"
    official = repo_root / "artifacts/gates/G01.json"
    before = hashlib.sha256(official.read_bytes()).hexdigest() if official.is_file() else None

    result = run_command([
        "python", "scripts/gates.py", "--phase", "01", "--revision", "auto",
        "--skip-commands", "--assertion", "runner-fails-closed", "--out-dir", str(out_dir),
    ], timeout=1800)
    assert result.returncode != 0, "the phase still cannot pass without its review records"
    evidence = json.loads((out_dir / "G01.json").read_text(encoding="utf-8"))
    probe_check = next(item for item in evidence["acceptance_assertions"] if item["id"] == "runner-fails-closed")
    assert probe_check["passed"] is True, probe_check["detail"]
    probe_log = out_dir / "G01-logs/runner-fails-closed-probe.log"
    assert probe_log.is_file() and probe_log.stat().st_size > 0, "the probe must leave a raw log"
    text = probe_log.read_text(encoding="utf-8")
    assert "exit_code: 1" in text, "the probe is deliberately non-zero and must be recorded as such"
    for required in ("# argv:", "# cwd:", "## stdout", "## stderr"):
        assert required in text, f"the probe log must record {required!r}"
    after = hashlib.sha256(official.read_bytes()).hexdigest() if official.is_file() else None
    assert after == before, "a sandboxed run must not modify the official gate record"


def test_real_repository_layer_check_passes(run_command) -> None:
    result = run_command(["python", "scripts/check_architecture.py"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "violations=0" in result.stdout


def test_real_repository_check_only_never_signed_a_gate(run_command) -> None:
    result = run_command(["python", "scripts/gates.py", "--phase", "01", "--revision", "auto", "--check-only"])
    assert "check-only" in result.stdout
    assert "gate not signed" in result.stdout


@pytest.mark.parametrize("phase", ["00", "abc", "1.0"])
def test_invalid_phase_arguments_are_rejected(phase: str, run_command) -> None:
    result = run_command(["python", "scripts/gates.py", "--phase", phase])
    assert result.returncode == 2
    assert "ARCH-CONFIG" in (result.stdout + result.stderr)