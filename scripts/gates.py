#!/usr/bin/env python
"""Phase Gate evidence executor (failure-closed).

Runs the commands the frozen task manifest requires, executes the phase-specific
acceptance assertions, verifies handoff/review records and hash freshness, and only
then writes ``artifacts/gates/GNN.json`` with ``status: passed``. Any failing check
produces ``status: failed``, keeps the previous record under ``runs``, and makes this
process exit non-zero.

Contract source: docs/plan/GATE_EXECUTION_CONTRACT.md and docs/plan/PHASE_GATES.md.

Rework 2026-10-01 (P01-02) tightened three judgements that were passing too much:

* the candidate revision is a deterministic manifest of *relevant* files, so writing
  evidence, logs, reports, review records or scratch files cannot change it;
* a ZCode pre-acceptance or Codex review record must bind a non-empty, well-formed,
  still-fresh input hash map that covers the inputs this runner consumes - an empty map is
  rejected;
* a preceding Gate record is validated against F2/F3/F4/F6 (fields, personally executed
  commands, exit codes, raw logs, frozen inputs and dependency hashes) instead of its
  ``status`` alone; the planner checker's ``log_hash`` and this runner's ``log_sha256`` are
  both accepted per concrete schema, but a record with neither is rejected.

Usage:
    uv run python scripts/gates.py --phase 01 --revision auto
    uv run python scripts/gates.py --phase 01 --revision auto --check-only
    uv run python scripts/gates.py --phase 01 --revision auto --assertion <id>

Exit codes: 0 = gate passed (or --check-only found everything fresh), 1 = gate failed
or stale evidence found, 2 = usage/configuration error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
MANIFEST_PATH = "docs/plan/TASK_MANIFEST.json"
GATES_DIR = "artifacts/gates"
DEFAULT_COMMAND_TIMEOUT_S = 1800

# --------------------------------------------------------------- candidate revision
# The candidate identity is a deterministic manifest of *relevant* files (implementation,
# configuration, contracts, tests and the generated business schema), never the whole tree:
# writing a log, report, review record or scratch file must not change it (rework-2026-10-01
# defect 2). The walk is a whitelist; everything not listed here is deliberately outside the
# candidate. Ordering is byte-wise by repository-relative POSIX path, so the digest is
# recomputable by hand from the same file set:
#
#   code_revision   = "content-sha256:" + sha256("\n".join(f"{path}\0{sha256(content)}"))
#   dirty_tree_hash = "content-sha256:" + sha256("\n".join(f"{path}\0{size}\0{sha256(content)}"))
#
# A file that does not exist is simply absent from the manifest (the walk never fails on a
# missing optional root); a directory that does not exist contributes nothing.
REVISION_INCLUDE_ROOTS = (
    "apps", "packages", "scripts", "tests", "tools", "contracts", "data", "deploy", ".github",
)
REVISION_INCLUDE_FILES = (
    "pyproject.toml", "uv.lock", "package.json", "package-lock.json",
    ".python-version", ".node-version", "OWNERSHIP.json",
    "PROJECT_MASTER_PLAN.md", "TASK_GRAPH.md",
)
REVISION_INCLUDE_CONTRACT_ROOTS = ("docs/architecture", "docs/api", "docs/algorithms")
REVISION_INCLUDE_PLAN_FILES = (
    "docs/plan/TASK_MANIFEST.json", "docs/plan/PHASE_GATES.md",
    "docs/plan/GATE_EXECUTION_CONTRACT.md", "docs/plan/TEST_FIXTURES.md",
)
# Outside the candidate on purpose (documented, not accidental): process/entry documents and
# every generated or authored record - AGENTS.md, README.md, AI-CODING-PLAN.md,
# docs/prompts/**, docs/agent-toolchain/**, docs/workflow/**, docs/implementation/**,
# docs/handoffs/**, docs/reviews/**, docs/plan/{USER_REQUIREMENTS,REQUIREMENTS_TRACEABILITY,
# PACKAGE_MANIFEST,VERIFICATION_REPORT}.*, artifacts/**, tmp/**, .mimosa/**. They describe how
# the work is dispatched or what it produced; editing them must not move the candidate.
# Excluded even inside an included root: scratch state, generated artefacts, vendored tools
# and legacy assets that are read-only baselines rather than inputs of the new workspace.
REVISION_EXCLUDE_PARTS = frozenset({
    ".venv", "node_modules", "__pycache__", ".git", ".mimosa", ".ruff_cache",
    ".pytest_cache", ".mypy_cache",
})
REVISION_EXCLUDE_PREFIXES = (
    "artifacts/", "tmp/", "tools/bin/", "demo/", "demos/", "platform/",
    "backend/", "frontend/", "benchmarks/",
)
REVISION_EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".log", ".zip", ".png", ".jpg", ".pdf")

# ------------------------------------------------------- previous-gate evidence schemas
# docs/plan/GATE_EXECUTION_CONTRACT.md section 2 fixes the field set. Two producers exist in
# this repository and both write real records, so the check is schema aware rather than
# lenient: the planner checker (G00) predates the runner and never wrote started_at /
# dirty_tree_hash / acceptance_artifacts, which is recorded here explicitly instead of being
# waved through. Every other element - commands, exit codes, logs, input and dependency
# hashes - is verified for both schemas.
PREVIOUS_GATE_COMMON_FIELDS = (
    "schema_version", "gate_id", "status", "finished_at", "code_revision",
    "input_artifact_hashes", "commands", "reviewer", "dependency_evidence_hashes",
)
PLANNER_SCHEMA_MARKERS = ("scope", "checker_counts")
RUNNER_SCHEMA_FIELDS = (
    "started_at", "dirty_tree_hash", "environment_fingerprint", "acceptance_artifacts", "limitations",
)
PLANNER_SCHEMA_FIELDS = ("environment_fingerprint", "limitations")
# The planner checker records `log_hash`; this runner records `log_sha256`. Both are accepted,
# but a record that carries neither is rejected: skipping log verification is not compatibility.
LOG_HASH_FIELDS = ("log_sha256", "log_hash")


# --------------------------------------------------------------------- command spec


@dataclass(frozen=True)
class CommandSpec:
    """A phase assertion that carries its own executable command."""

    command: str
    expectation: str
    required: bool = True


@dataclass(frozen=True)
class CheckSpec:
    """Phase-specific acceptance assertion."""

    id: str
    gate: str
    description: str
    command: CommandSpec | None = None


PHASE_ASSERTIONS: dict[int, tuple[CheckSpec, ...]] = {
    1: (
        CheckSpec(
            "clean-install-imports",
            "G01",
            "干净安装后六个包可导入（仓库外 cwd 亦可），且解析到各自 workspace src 目录",
            None,  # implemented by GateRunner.check_imports_from_outside_cwd (writes its own probe)
        ),
        CheckSpec(
            "layer-boundaries",
            "G01",
            "分层检查通过：层依赖方向正确、domain 无第三方导入",
            CommandSpec("uv run python scripts/check_architecture.py", "exit code 0 and no violations"),
        ),
        CheckSpec(
            "lock-reproducible",
            "G01",
            "依赖锁可复现：uv.lock 与各成员清单一致，且 npm 锁未漂移",
            CommandSpec("uv lock --check", "exit code 0"),
        ),
        CheckSpec(
            "runner-fails-closed",
            "G01",
            "Gate 执行器非零命令必失败：exit=1 的探查命令必须被判定为失败",
            None,  # implemented by GateRunner.check_runner_fails_closed
        ),
        CheckSpec(
            "legacy-demo-untouched",
            "G01",
            "旧 demo 未被覆盖：登记文件指纹与 demo.zip 哈希仍与 P01-01 基线证据一致",
            None,  # implemented by GateRunner.check_legacy_demo_untouched
        ),
    ),
}


# ------------------------------------------------------------------------- utilities


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repo_relative(path: Path, root: Path) -> str:
    """Path as recorded in evidence: relative to the repository root when possible.

    Log and artifact paths must never raise just because the caller redirected output with
    ``--out-dir`` outside the repository, so anything outside the root is recorded absolute.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def clean_env() -> dict[str, str]:
    """Environment for child commands: no inherited npm offline/cache-only switches."""
    env = dict(os.environ)
    for name in ("npm_config_offline", "npm_config_cache_mode", "npm_config_allow_scripts", "NPM_CONFIG_OFFLINE"):
        env.pop(name, None)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def split_command(command: str) -> list[str]:
    """Parse a manifest command string into argv without a shell."""
    return shlex.split(command, posix=False) if os.name == "nt" else shlex.split(command)


def normalize_argv(argv: list[str]) -> list[str]:
    """Strip Windows quoting artifacts left by a non-posix shlex split."""
    normalized = []
    for token in argv:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
            token = token[1:-1]
        normalized.append(token)
    return normalized


def resolve_tool(name: str, root: Path) -> str:
    """Resolve a command's executable, falling back to the repository bootstrap copy.

    The host that produced P01-01 has no system-wide uv, so the gate runner must find
    the same interpreter the rest of the workspace uses. Missing tools are returned
    as-is so the child process fails loudly with a FileNotFoundError report.
    """
    found = shutil.which(name)
    if found:
        return found
    for suffix in (".exe", ".cmd", ".bat", ""):
        candidate = root / "tools/bin" / f"{name}{suffix}"
        if candidate.is_file():
            return str(candidate)
    return name


def parse_pytest_counts(output: str) -> dict[str, int | str]:
    """Extract real test counts from a pytest summary line, if present."""
    counts: dict[str, int | str] = {}
    for label in ("passed", "failed", "skipped", "errors", "error", "xfailed", "xpassed", "deselected"):
        match = re.search(rf"(\d+) {label}\b", output)
        if match:
            key = "errors" if label == "error" else label
            counts[key] = int(match.group(1))
    return counts


def looks_like_pytest(argv: list[str]) -> bool:
    return any("pytest" in token for token in argv)


# ------------------------------------------------------------------------ result types


@dataclass
class CommandResult:
    check_id: str
    argv: list[str]
    cwd: str
    exit_code: int
    duration_ms: int
    log_path: str
    log_sha256: str
    stdout_tail: list[str] = field(default_factory=list)
    test_counts: dict[str, int | str] = field(default_factory=dict)
    required: bool = True

    def as_dict(self) -> dict:
        payload = {
            "check_id": self.check_id,
            "argv": self.argv,
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "log_path": self.log_path,
            "log_sha256": self.log_sha256,
            "required": self.required,
        }
        if self.test_counts:
            payload["test_counts"] = self.test_counts
        if self.stdout_tail:
            payload["stdout_tail"] = self.stdout_tail
        return payload


@dataclass
class CheckResult:
    id: str
    gate: str
    description: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "gate": self.gate,
            "description": self.description,
            "passed": self.passed,
            "detail": self.detail,
        }


# ------------------------------------------------------------------------- the runner


class GateRunner:
    def __init__(
        self,
        root: Path,
        phase: int,
        revision: str,
        only_checks: list[str] | None = None,
        skip_commands: bool = False,
        out_dir: Path | None = None,
    ) -> None:
        self.root = root
        self.phase = phase
        self.gate_id = f"G{phase:02d}"
        self.revision = revision
        self.only_checks = only_checks
        self.skip_commands = skip_commands
        self.gate_dir = root / GATES_DIR
        # `--out-dir` lets a sandboxed or self-test run record elsewhere instead of
        # overwriting the official gate record. When it differs from the default, the
        # evidence is explicitly marked as not being the phase's official record.
        self.out_dir = Path(out_dir).resolve() if out_dir else self.gate_dir
        self.records_official_gate = self.out_dir == self.gate_dir
        self.log_dir = self.out_dir / f"{self.gate_id}-logs"
        self.failures: list[str] = []
        self.limitations: list[str] = []

    # -- manifest / dependency resolution ------------------------------------------

    def manifest(self) -> dict:
        path = self.root / MANIFEST_PATH
        if not path.is_file():
            raise SystemExit(f"ARCH-CONFIG: task manifest not found: {MANIFEST_PATH}")
        return json.loads(path.read_text(encoding="utf-8"))

    def phase_tasks(self) -> list[dict]:
        return [task for task in self.manifest()["tasks"] if task["phase"] == self.phase]

    def gate_node(self) -> dict:
        for gate in self.manifest()["gates"]:
            if gate["id"] == self.gate_id:
                return gate
        raise SystemExit(f"ARCH-CONFIG: gate {self.gate_id} is not in the task manifest")

    def previous_gates(self) -> list[str]:
        return [f"G{index:02d}" for index in range(self.phase)]

    # -- records -------------------------------------------------------------------

    def dsh_evidence_paths(self) -> dict[str, Path]:
        return {
            task["id"]: self.root / "artifacts/handoffs" / task["id"] / "dsh" / "evidence.json"
            for task in self.phase_tasks()
        }

    def required_documentation_paths(self) -> list[Path]:
        paths: list[Path] = []
        for task in self.phase_tasks():
            paths.append(self.root / task["task_doc"])
            paths.append(self.root / task["report"])
        return paths

    def zcode_precheck_path(self, task_id: str) -> Path:
        """Conventional location for the ZCode pre-acceptance record.

        docs/workflow/HANDOFF_CONTRACT.md does not exist in this checkout, so the
        runner fixes the path convention itself and fails closed when it is missing.
        """
        return self.root / "artifacts/handoffs" / task_id / "zcode" / "precheck.json"

    def codex_review_path(self) -> Path:
        return self.root / "artifacts/gates" / f"{self.gate_id}-codex-review.json"

    def load_json(self, path: Path) -> dict | None:
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.failures.append(f"REVIEW-UNREADABLE: {path.relative_to(self.root).as_posix()}: {exc}")
            return None

    # -- revision ------------------------------------------------------------------

    def relevant_files(self) -> list[Path]:
        """Every file that is a relevant input of a candidate, in deterministic order.

        Whitelist walk (see the module constants): implementation, configuration, contracts,
        tests, the generated business schema and the frozen plan files. Logs, reports, review
        records, gate evidence, scratch directories and legacy assets are excluded, so writing
        them cannot change the candidate.
        """
        found: list[Path] = []
        for root_name in REVISION_INCLUDE_ROOTS:
            base = self.root / root_name
            if not base.is_dir():
                continue
            found.extend(path for path in base.rglob("*") if path.is_file())
        for directory in REVISION_INCLUDE_CONTRACT_ROOTS:
            base = self.root / directory
            if base.is_dir():
                found.extend(path for path in base.rglob("*") if path.is_file())
        for relative in (*REVISION_INCLUDE_FILES, *REVISION_INCLUDE_PLAN_FILES):
            path = self.root / relative
            if path.is_file():
                found.append(path)
        rows: dict[str, Path] = {}
        for path in found:
            relative = path.relative_to(self.root).as_posix()
            if relative.startswith(REVISION_EXCLUDE_PREFIXES):
                continue
            if any(part in REVISION_EXCLUDE_PARTS for part in path.relative_to(self.root).parts):
                continue
            if relative.endswith(REVISION_EXCLUDE_SUFFIXES):
                continue
            rows[relative] = path
        return [rows[key] for key in sorted(rows)]

    def relevant_manifest_rows(self) -> list[tuple[str, str, int]]:
        """(relative path, sha256, size) for the candidate file set, sorted by path."""
        rows = []
        for path in self.relevant_files():
            relative = path.relative_to(self.root).as_posix()
            rows.append((relative, sha256_file(path), path.stat().st_size))
        return rows

    def compute_revision(self) -> str:
        if self.revision and self.revision != "auto":
            return self.revision
        rows = [f"{relative}\0{digest}" for relative, digest, _ in self.relevant_manifest_rows()]
        return "content-sha256:" + sha256_text("\n".join(rows))

    # -- command execution ---------------------------------------------------------

    def run_command(self, check_id: str, spec: CommandSpec) -> CommandResult:
        argv = normalize_argv(split_command(spec.command))
        argv[0] = resolve_tool(argv[0], self.root)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"{check_id}.log"
        started = time.monotonic()
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(f"# check: {check_id}\n# argv: {json.dumps(argv, ensure_ascii=False)}\n")
            handle.write(f"# cwd: {self.root}\n# started_at: {utc_now()}\n# expectation: {spec.expectation}\n\n")
            handle.flush()
            try:
                completed = subprocess.run(
                    argv,
                    cwd=self.root,
                    env=clean_env(),
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_COMMAND_TIMEOUT_S,
                    check=False,
                )
                stdout, stderr, exit_code = completed.stdout, completed.stderr, completed.returncode
            except FileNotFoundError as exc:
                stdout, stderr, exit_code = "", f"command not found: {exc}", 127
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = (exc.stderr or "") + f"\ntimeout after {DEFAULT_COMMAND_TIMEOUT_S}s"
                exit_code = 124
            duration_ms = int((time.monotonic() - started) * 1000)
            handle.write("## stdout\n")
            handle.write(stdout)
            handle.write("\n## stderr\n")
            handle.write(stderr)
            handle.write(f"\n## exit_code: {exit_code}\n")
            handle.write(f"## duration_ms: {duration_ms}\n")
        combined = f"{stdout}\n{stderr}"
        test_counts = parse_pytest_counts(combined) if looks_like_pytest(argv) else {}
        return CommandResult(
            check_id=check_id,
            argv=argv,
            cwd=str(self.root),
            exit_code=exit_code,
            duration_ms=duration_ms,
            log_path=repo_relative(log_path, self.root),
            log_sha256=sha256_file(log_path),
            stdout_tail=[line for line in combined.strip().splitlines()[-4:] if line.strip()],
            test_counts=test_counts,
            required=spec.required,
        )

    def evaluate_command(
        self,
        check_id: str,
        result: CommandResult,
        spec: CommandSpec | None = None,
    ) -> CheckResult:
        """Turn a recorded command result into a pass/fail check.

        ``spec`` supplies the human-readable expectation; when it is omitted (for example
        when re-evaluating an already recorded result) the expectation is derived from the
        result itself so the judgement never depends on how the call site was written.
        """
        expectation = spec.expectation if spec is not None else "recorded command must have exited 0"
        problems: list[str] = []
        if result.exit_code != 0:
            problems.append(f"exit_code={result.exit_code} (expected 0)")
        log_file = self.root / result.log_path
        if log_file.is_file() and log_file.stat().st_size == 0:
            problems.append("empty log")
        if looks_like_pytest(result.argv):
            counts = result.test_counts
            if not counts:
                problems.append("no test summary found; a zero-case run is not acceptance evidence")
            else:
                if int(counts.get("passed", 0)) <= 0:
                    problems.append(f"no passing tests: {counts}")
                if int(counts.get("failed", 0)) or int(counts.get("errors", 0)):
                    problems.append(f"failing tests: {counts}")
                if int(counts.get("skipped", 0)) > 0:
                    problems.append(f"skipped tests present: {counts}")
        detail = expectation if not problems else "; ".join(problems)
        return CheckResult(check_id, self.gate_id, expectation, not problems, detail)

    # -- phase assertions ----------------------------------------------------------

    def check_imports_from_outside_cwd(self) -> CheckResult:
        """Test case 1: after a frozen install the six packages import from anywhere."""
        expectation = "六个包在仓库外 cwd 下仍可导入，且解析到各自 workspace src 目录"
        probe_path = self.root / f".gate-probe-{self.gate_id}.py"
        probe_path.write_text(
            "import importlib, json, pathlib\n"
            "MODULES = ['logistics_domain', 'logistics_contracts', 'logistics_optimization',\n"
            "           'logistics_simulation', 'logistics_agents', 'logistics_evaluation']\n"
            "resolved = {name: str(pathlib.Path(importlib.import_module(name).__file__).resolve()) for name in MODULES}\n"
            "print('IMPORT_PROBE=' + json.dumps(resolved))\n",
            encoding="utf-8",
        )
        try:
            result = self.run_command(
                "clean-install-imports",
                CommandSpec(f"uv run python {probe_path.name}", "six packages must import"),
            )
        finally:
            probe_path.unlink(missing_ok=True)
        problems: list[str] = []
        if result.exit_code != 0:
            problems.append(f"probe exit_code={result.exit_code}")
        log_text = (self.root / result.log_path).read_text(encoding="utf-8")
        marker = "IMPORT_PROBE="
        if marker not in log_text:
            problems.append("probe printed no resolution map")
        else:
            payload = json.loads(log_text.split(marker, 1)[1].splitlines()[0])
            expected = {
                "logistics_domain": "packages/domain/src",
                "logistics_contracts": "packages/contracts/src",
                "logistics_optimization": "packages/optimization/src",
                "logistics_simulation": "packages/simulation/src",
                "logistics_agents": "packages/agents/src",
                "logistics_evaluation": "packages/evaluation/src",
            }
            for module, fragment in expected.items():
                location = payload.get(module, "")
                if fragment.replace("/", os.sep) not in location.replace("/", os.sep):
                    problems.append(f"{module} resolved outside its workspace source: {location}")
        detail = expectation if not problems else "; ".join(problems)
        return CheckResult("clean-install-imports", self.gate_id, expectation, not problems, detail)

    def check_layer_boundaries(self) -> CheckResult:
        spec = next(item for item in PHASE_ASSERTIONS[1] if item.id == "layer-boundaries")
        result = self.run_command("layer-boundaries", spec.command)
        report = self.run_command("layer-boundaries-json", CommandSpec(
            "uv run python scripts/check_architecture.py --json",
            "structured layer report",
        ))
        problems = []
        if result.exit_code != 0:
            problems.append(f"checker exit_code={result.exit_code}")
        if report.exit_code != 0:
            problems.append(f"json checker exit_code={report.exit_code}")
        else:
            log_text = (self.root / report.log_path).read_text(encoding="utf-8")
            body = log_text.split("## stdout\n", 1)[-1].split("\n## stderr", 1)[0]
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as exc:
                payload = {}
                problems.append(f"layer report is not valid JSON: {exc}")
            violations = payload.get("violation_count")
            if violations != 0:
                problems.append(f"violation_count={violations}")
            if not payload.get("modules_scanned"):
                problems.append("no modules scanned; the layer check would be vacuous")
        detail = spec.description if not problems else "; ".join(problems)
        return CheckResult("layer-boundaries", self.gate_id, spec.description, not problems, detail)

    def check_lock_reproducible(self) -> CheckResult:
        spec = next(item for item in PHASE_ASSERTIONS[1] if item.id == "lock-reproducible")
        result = self.run_command("lock-reproducible", spec.command)
        problems = []
        if result.exit_code != 0:
            problems.append(f"uv lock --check exit_code={result.exit_code}")
        for name in ("uv.lock", "package-lock.json"):
            if not (self.root / name).is_file():
                problems.append(f"{name} missing")
        npm_lock = self.root / "package-lock.json"
        if npm_lock.is_file():
            payload = json.loads(npm_lock.read_text(encoding="utf-8"))
            if payload.get("lockfileVersion") != 3:
                problems.append(f"npm lockfileVersion={payload.get('lockfileVersion')}")
        detail = spec.description if not problems else "; ".join(problems)
        return CheckResult("lock-reproducible", self.gate_id, spec.description, not problems, detail)

    def check_legacy_demo_untouched(self) -> CheckResult:
        spec = next(item for item in PHASE_ASSERTIONS[1] if item.id == "legacy-demo-untouched")
        baseline = self.load_json(self.root / "docs/architecture/BASELINE_INVENTORY.json")
        evidence = self.load_json(self.root / "artifacts/handoffs/P01-01/dsh/evidence.json")
        problems: list[str] = []
        if not baseline:
            problems.append("BASELINE_INVENTORY.json missing or unreadable")
        if not evidence:
            problems.append("P01-01 evidence.json missing or unreadable")
        if problems:
            return CheckResult("legacy-demo-untouched", self.gate_id, spec.description, False, "; ".join(problems))
        entries = baseline.get("entries", [])
        mismatched = [
            entry["source_path"]
            for entry in entries
            if sha256_file(self.root / entry["source_path"]) != entry["sha256"]
        ]
        if mismatched:
            problems.append(f"{len(mismatched)} baseline file(s) changed, first: {mismatched[0]}")
        recorded = evidence.get("legacy_demo", {})
        demo_zip = self.root / "demo.zip"
        if demo_zip.is_file() and recorded.get("demo_zip", {}).get("sha256") != sha256_file(demo_zip):
            problems.append("demo.zip hash differs from the recorded baseline")
        if recorded.get("file_count") != len(entries):
            problems.append(f"recorded demo file_count={recorded.get('file_count')} but inventory has {len(entries)}")
        detail = spec.description if not problems else "; ".join(problems)
        return CheckResult("legacy-demo-untouched", self.gate_id, spec.description, not problems, detail)

    def check_runner_fails_closed(self) -> CheckResult:
        """G01 requires a non-zero command to make the gate fail: prove it, twice.

        1. a real probe command that exits 1 must be recorded as failing;
        2. the same gate command re-evaluated with an injected non-zero exit code must be
           rejected, which covers "a command reported by the manifest cannot lie its way
           into a passed gate".
        """
        check_id = "runner-fails-closed-probe"
        probe = CommandSpec("uv run python -c \"import sys; sys.exit(1)\"", "must fail")
        result = self.run_command(check_id, probe)
        verdict = self.evaluate_command(check_id, result, probe)
        real_probe_ok = result.exit_code == 1 and not verdict.passed
        injected = CommandResult(
            check_id=check_id,
            argv=["uv", "run", "pytest", "tests/unit/test_p01_01_workspace_bootstrap.py", "-q"],
            cwd=str(self.root),
            exit_code=1,
            duration_ms=result.duration_ms,
            log_path=result.log_path,
            log_sha256=result.log_sha256,
            stdout_tail=["1 failed, 55 passed in 1.00s"],
            test_counts={"passed": 55, "failed": 1},
            required=True,
        )
        injected_verdict = self.evaluate_command(check_id, injected)
        injected_ok = not injected_verdict.passed
        proven = real_probe_ok and injected_ok
        detail = (
            "probe exited 1 and was evaluated as failed; injected exit=1 with counts "
            f"{injected.test_counts} was also rejected"
            if proven
            else f"fail-closed not proven: real probe exit={result.exit_code}, verdict={verdict.detail}; "
                 f"injected verdict={injected_verdict.detail}"
        )
        return CheckResult("runner-fails-closed", self.gate_id,
                           "non-zero commands must fail the gate", proven, detail)

    # -- handoff / review records --------------------------------------------------

    def check_phase_handoffs(self) -> list[CheckResult]:
        results: list[CheckResult] = []
        for task_id, path in self.dsh_evidence_paths().items():
            payload = self.load_json(path)
            if not payload:
                results.append(CheckResult(
                    f"dsh-evidence:{task_id}", self.gate_id,
                    "每个阶段任务都提供 DSH 证据", False,
                    f"missing {path.relative_to(self.root).as_posix()}",
                ))
                continue
            status = payload.get("status")
            accepted = {"READY_FOR_ZCODE", "Z_PRECHECK_PASSED"}
            ok = status in accepted
            results.append(CheckResult(
                f"dsh-evidence:{task_id}", self.gate_id,
                "每个阶段任务都提供 DSH 证据", ok,
                f"status={status}" if ok else f"unexpected status={status!r}",
            ))
        for path in self.required_documentation_paths():
            ok = path.is_file()
            relative = path.relative_to(self.root).as_posix()
            results.append(CheckResult(
                f"docs:{relative}", self.gate_id, "任务文档与完成报告齐备", ok,
                "present" if ok else f"missing {relative}",
            ))
        results.extend(self.check_zcode_precheck())
        results.append(self.check_codex_review())
        return results

    def check_zcode_precheck(self) -> list[CheckResult]:
        results: list[CheckResult] = []
        tasks = {task["id"]: task for task in self.phase_tasks()}
        for task_id, task in tasks.items():
            path = self.zcode_precheck_path(task_id)
            relative = path.relative_to(self.root).as_posix()
            description = "ZCode 预验收记录存在、绑定本任务必需输入且其冻结输入未漂移"
            payload = self.load_json(path)
            if payload is None:
                results.append(CheckResult(
                    f"zcode-precheck:{task_id}", self.gate_id, description, False,
                    f"missing {relative}; the phase handoff contract requires a pre-acceptance record",
                ))
                continue
            problems: list[str] = []
            if payload.get("task_id") != task_id:
                problems.append(f"task_id={payload.get('task_id')!r} (expected {task_id!r})")
            if payload.get("phase_gate") != self.gate_id:
                problems.append(f"phase_gate={payload.get('phase_gate')!r} (expected {self.gate_id!r})")
            if payload.get("status") != "Z_PRECHECK_PASSED":
                problems.append(f"status={payload.get('status')!r} (expected 'Z_PRECHECK_PASSED')")
            if not payload.get("reviewer"):
                problems.append("no reviewer recorded")
            problems.extend(self.recorded_input_problems(
                relative, payload.get("verified_input_hashes"),
                require=self.required_precheck_inputs(task),
            ))
            detail = (
                f"{relative}: Z_PRECHECK_PASSED with "
                f"{len(payload.get('verified_input_hashes') or {})} fresh input hash(es)"
                if not problems else f"{relative}: " + "; ".join(problems)
            )
            results.append(CheckResult(f"zcode-precheck:{task_id}", self.gate_id, description, not problems, detail))
        return results

    def recorded_input_problems(
        self,
        label: str,
        recorded: object,
        *,
        require: tuple[str, ...] = (),
    ) -> list[str]:
        """Validate a reviewer's frozen input hash map.

        A record whose only content is "passed" is not evidence: the map must exist, be
        non-empty, carry a well-formed sha256 per entry, every entry must still match the file
        on disk, and the inputs this runner actually consumes must be covered.
        """
        if not isinstance(recorded, dict):
            return [f"{label}: verified_input_hashes is missing or not an object"]
        if not recorded:
            return [f"{label}: verified_input_hashes is empty; a record without verifiable inputs is not evidence"]
        problems: list[str] = []
        for relative, digest in sorted(recorded.items()):
            if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
                problems.append(f"{label}: invalid input path {relative!r}")
                continue
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                problems.append(f"{label}: {relative} has no sha256 digest")
                continue
            target = self.root / relative
            if not target.is_file():
                problems.append(f"{label}: {relative} is missing on disk")
            elif sha256_file(target) != digest:
                problems.append(f"{label}: {relative} has a stale input hash")
        missing = [item for item in require if item not in recorded]
        if missing:
            problems.append(f"{label}: required input(s) not covered: {', '.join(missing)}")
        return problems

    def required_precheck_inputs(self, task: dict) -> tuple[str, ...]:
        """Inputs a ZCode pre-acceptance record must bind for this task.

        Derived from the frozen manifest and the runner's own reading rules: the manifest the
        record is validated against, the gate protocol, the task prompt and the developer
        evidence this phase handoff check consumes.
        """
        required = [MANIFEST_PATH, "docs/plan/PHASE_GATES.md"]
        prompt = task.get("prompt")
        if isinstance(prompt, str) and prompt:
            required.append(prompt)
        required.append(f"artifacts/handoffs/{task['id']}/dsh/evidence.json")
        return tuple(dict.fromkeys(required))

    def stale_input_hashes(self, recorded: dict) -> list[str]:
        stale = []
        for relative, digest in sorted(recorded.items()):
            path = self.root / relative
            if not path.is_file() or sha256_file(path) != digest:
                stale.append(relative)
        return stale

    def check_codex_review(self) -> CheckResult:
        path = self.codex_review_path()
        relative = path.relative_to(self.root).as_posix()
        description = "Codex 阶段 review 存在、覆盖当前 revision、绑定可核验输入且输入哈希未漂移"
        payload = self.load_json(path)
        if payload is None:
            return CheckResult(
                "codex-review", self.gate_id, description, False,
                f"missing {relative}; a phase gate cannot be signed without the Codex review record",
            )
        problems = []
        if payload.get("gate_id") != self.gate_id:
            problems.append(f"gate_id={payload.get('gate_id')!r}")
        if payload.get("status") not in {"approved", "passed"}:
            problems.append(f"status={payload.get('status')!r}")
        recorded_revision = payload.get("code_revision")
        if not recorded_revision:
            problems.append("no code_revision recorded")
        elif self.revision not in {"auto", None} and recorded_revision != self.revision:
            problems.append(f"review covers revision {recorded_revision!r}, current revision is {self.revision!r}")
        if not payload.get("reviewer"):
            problems.append("no reviewer recorded")
        # A non-empty reviewer plus "approved" is not enough: the review must bind verifiable inputs.
        problems.extend(self.recorded_input_problems("codex-review", payload.get("verified_input_hashes")))
        detail = "codex review is valid for the current revision" if not problems else "; ".join(problems)
        return CheckResult("codex-review", self.gate_id, description, not problems, detail)

    def check_previous_gates(self) -> list[CheckResult]:
        """Validate every earlier Gate record against F2/F3/F4/F6 of the frozen contract.

        A record that merely says ``{"status": "passed"}`` is not evidence (rework-2026-10-01
        defect 4): the fields, the personally executed commands with their real exit codes and
        raw logs, the frozen input hashes and the dependency hashes must all still hold.
        """
        results = []
        records = self.load_previous_gate_records()
        cycles = self.gate_dependency_cycles(records)
        for gate_id in self.previous_gates():
            payload = records.get(gate_id)
            if payload is None:
                results.append(CheckResult(
                    f"previous-gate:{gate_id}", self.gate_id, "前序 Gate 证据有效", False,
                    f"missing artifacts/gates/{gate_id}.json",
                ))
                continue
            problems = self.previous_gate_record_problems(gate_id, payload)
            problems.extend(cycles.get(gate_id, []))
            results.append(CheckResult(
                f"previous-gate:{gate_id}", self.gate_id, "前序 Gate 证据有效", not problems,
                f"schema={self.gate_record_schema(payload)} status={payload.get('status')} "
                f"commands={len(payload.get('commands') or [])} inputs={len(payload.get('input_artifact_hashes') or {})}"
                if not problems else "; ".join(problems),
            ))
        return results

    def load_previous_gate_records(self) -> dict[str, dict]:
        """Every existing preceding Gate record, loaded once (unreadable files are kept as None)."""
        records: dict[str, dict] = {}
        for gate_id in self.previous_gates():
            path = self.gate_dir / f"{gate_id}.json"
            payload = self.load_json(path)
            if payload is not None:
                records[gate_id] = payload
        return records

    @staticmethod
    def gate_record_schema(payload: dict) -> str:
        """`planner` for the Phase00 checker record, `runner` for this executor's records."""
        return "planner" if any(marker in payload for marker in PLANNER_SCHEMA_MARKERS) else "runner"

    def previous_gate_record_problems(self, gate_id: str, payload: dict) -> list[str]:
        """Typed problems for one preceding Gate record; empty list means the evidence holds."""
        problems: list[str] = []
        if not isinstance(payload, dict):
            return ["evidence is not an object"]
        schema = self.gate_record_schema(payload)
        required = list(PREVIOUS_GATE_COMMON_FIELDS)
        required += list(PLANNER_SCHEMA_FIELDS if schema == "planner" else RUNNER_SCHEMA_FIELDS)
        non_empty = {
            "schema_version", "finished_at", "code_revision", "reviewer",
            "started_at", "dirty_tree_hash", "environment_fingerprint",
        }
        for field_name in required:
            if field_name not in payload:
                problems.append(f"missing required field {field_name}")
            elif field_name in non_empty and payload[field_name] in (None, "", [], {}):
                problems.append(f"empty required field {field_name}")
        if payload.get("gate_id") != gate_id:
            problems.append(f"gate_id={payload.get('gate_id')!r} (expected {gate_id!r})")
        if payload.get("status") != "passed":
            problems.append(f"status={payload.get('status')!r} (expected 'passed')")
        if not isinstance(payload.get("code_revision"), str) or not payload.get("code_revision"):
            problems.append("code_revision is missing or not a string")
        if not isinstance(payload.get("reviewer"), str) or not payload.get("reviewer"):
            problems.append("reviewer is missing or not a string")
        for stamp in ("finished_at", "started_at"):
            if stamp in payload and not isinstance(payload[stamp], str):
                problems.append(f"{stamp} must be an ISO-8601 string")

        commands = payload.get("commands")
        if not isinstance(commands, list) or not commands:
            problems.append("commands[] is missing or empty; the executor must record its own runs")
        else:
            for index, command in enumerate(commands):
                problems.extend(self.recorded_command_problems(index, command))

        inputs = payload.get("input_artifact_hashes")
        if not isinstance(inputs, dict) or not inputs:
            problems.append("input_artifact_hashes is missing or empty")
        else:
            for relative, digest in sorted(inputs.items()):
                if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
                    problems.append(f"input_artifact_hashes has an invalid path {relative!r}")
                    continue
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    problems.append(f"input_artifact_hashes[{relative}] has no sha256 digest")
                    continue
                target = self.root / relative
                if not target.is_file():
                    problems.append(f"frozen input {relative} is missing on disk")
                elif sha256_file(target) != digest:
                    problems.append(f"frozen input {relative} drifted after the gate was recorded")

        problems.extend(self.dependency_hash_problems(gate_id, payload.get("dependency_evidence_hashes")))
        return problems

    def recorded_command_problems(self, index: int, command: object) -> list[str]:
        """F3/F4/F6 for one recorded command: argv, cwd, integer exit code, raw log and its hash."""
        if not isinstance(command, dict):
            return [f"commands[{index}] is not an object"]
        problems: list[str] = []
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            problems.append(f"commands[{index}] has no usable argv")
        cwd = command.get("cwd")
        if not isinstance(cwd, str) or not cwd:
            problems.append(f"commands[{index}] has no cwd")
        elif Path(cwd).is_absolute() and Path(cwd).resolve() != self.root.resolve():
            problems.append(f"commands[{index}] cwd {cwd!r} is not this repository root")
        exit_code = command.get("exit_code")
        if type(exit_code) is not int:
            problems.append(
                f"commands[{index}] exit_code={exit_code!r} is not an integer "
                "(a missing or boolean exit code cannot be read as success)"
            )
        elif exit_code != 0:
            problems.append(f"commands[{index}] exit_code={exit_code} (expected 0)")
        log_path = command.get("log_path")
        if not isinstance(log_path, str) or not log_path:
            problems.append(f"commands[{index}] has no log_path")
            return problems
        field_names = [name for name in LOG_HASH_FIELDS if name in command]
        if not field_names:
            problems.append(
                f"commands[{index}] records neither {' nor '.join(LOG_HASH_FIELDS)}; "
                "a raw log hash is required and may not be skipped"
            )
            return problems
        recorded_digest = command[field_names[0]]
        if not isinstance(recorded_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", recorded_digest):
            problems.append(f"commands[{index}].{field_names[0]} is not a sha256 digest")
            return problems
        log_file = self.root / log_path
        if not log_file.is_file():
            problems.append(f"commands[{index}] log {log_path} is missing on disk")
        elif log_file.stat().st_size == 0:
            problems.append(f"commands[{index}] log {log_path} is empty")
        elif sha256_file(log_file) != recorded_digest:
            problems.append(f"commands[{index}] log {log_path} changed after the gate was recorded")
        return problems

    def dependency_hash_problems(self, gate_id: str, recorded: object) -> list[str]:
        """F2/F6 for the dependency hashes: earlier gates only, present and byte-identical."""
        if not isinstance(recorded, dict):
            return ["dependency_evidence_hashes is missing or not an object"]
        index_of = {name: position for position, name in enumerate(self.previous_gates())}
        current = index_of.get(gate_id, len(index_of))
        problems: list[str] = []
        for dependency, digest in sorted(recorded.items()):
            position = index_of.get(dependency)
            if position is None:
                problems.append(f"dependency_evidence_hashes names {dependency!r}, which is not a preceding gate")
                continue
            if position >= current:
                problems.append(f"dependency_evidence_hashes references {dependency!r} at or after {gate_id!r}")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                problems.append(f"dependency_evidence_hashes[{dependency}] has no sha256 digest")
                continue
            path = self.gate_dir / f"{dependency}.json"
            if not path.is_file():
                problems.append(f"dependency {dependency} record is missing on disk")
            elif sha256_file(path) != digest:
                problems.append(f"dependency {dependency} record changed after it was bound")
        return problems

    def gate_dependency_cycles(self, records: dict[str, dict]) -> dict[str, list[str]]:
        """Detect self-references and cycles in the recorded gate dependency graph."""
        order = {name: position for position, name in enumerate(self.previous_gates())}
        problems: dict[str, list[str]] = {}

        def walk(node: str, path: tuple[str, ...]) -> list[str]:
            payload = records.get(node)
            if payload is None:
                return []
            found: list[str] = []
            for dependency in sorted(payload.get("dependency_evidence_hashes") or {}):
                if dependency == node:
                    found.append(f"{node} lists itself as a dependency (cycle)")
                elif dependency in path:
                    found.append(f"dependency cycle: {' -> '.join((*path, dependency))}")
                elif dependency in records and order.get(dependency, 0) < order.get(node, 0):
                    found.extend(walk(dependency, (*path, dependency)))
            return found

        for gate_id in records:
            issues = walk(gate_id, (gate_id,))
            if issues:
                problems[gate_id] = sorted(set(issues))
        return problems

    # -- orchestration -------------------------------------------------------------

    def assertion_specs(self) -> list[CheckSpec]:
        specs = list(PHASE_ASSERTIONS.get(self.phase, ()))
        if self.only_checks:
            known = {spec.id for spec in specs}
            unknown = [item for item in self.only_checks if item not in known]
            if unknown:
                raise SystemExit(f"ARCH-CONFIG: unknown assertion id(s): {unknown}; known: {sorted(known)}")
            specs = [spec for spec in specs if spec.id in set(self.only_checks)]
        return specs

    def run(self, check_only: bool) -> int:
        started_at = utc_now()
        self.revision = self.compute_revision()
        self.gate_dir.mkdir(parents=True, exist_ok=True)
        if check_only:
            return self.run_check_only(started_at)

        task_commands: list[CommandResult] = []
        command_checks: list[CheckResult] = []
        for task in self.phase_tasks():
            for index, command in enumerate(task["commands"], start=1):
                check_id = f"{task['id']}-cmd{index}"
                if self.skip_commands:
                    command_checks.append(CheckResult(
                        check_id, self.gate_id, command, False,
                        "--skip-commands was requested: manifest commands were not executed",
                    ))
                    continue
                spec = CommandSpec(command, "manifest command must succeed")
                result = self.run_command(check_id, spec)
                task_commands.append(result)
                command_checks.append(self.evaluate_command(check_id, result, spec))

        assertion_checks: list[CheckResult] = []
        for spec in self.assertion_specs():
            if self.skip_commands and spec.id != "runner-fails-closed":
                # `--skip-commands` still lets the cheap failure-closure probe run, because
                # that probe is the assertion which proves non-zero commands are rejected.
                assertion_checks.append(CheckResult(
                    spec.id, self.gate_id, spec.description, False,
                    "--skip-commands was requested: the phase acceptance assertion was not evaluated",
                ))
                continue
            if spec.id == "clean-install-imports":
                assertion_checks.append(self.check_imports_from_outside_cwd())
            elif spec.id == "layer-boundaries":
                assertion_checks.append(self.check_layer_boundaries())
            elif spec.id == "lock-reproducible":
                assertion_checks.append(self.check_lock_reproducible())
            elif spec.id == "legacy-demo-untouched":
                assertion_checks.append(self.check_legacy_demo_untouched())
            elif spec.id == "runner-fails-closed":
                assertion_checks.append(self.check_runner_fails_closed())
            else:  # pragma: no cover - guard against an unregistered assertion id
                assertion_checks.append(CheckResult(spec.id, self.gate_id, spec.description, False,
                                                    "assertion id has no implementation"))

        record_checks = self.check_previous_gates() + self.check_phase_handoffs()
        all_checks = command_checks + assertion_checks + record_checks
        failed = [check for check in all_checks if not check.passed]
        self.limitations.extend([
            "This gate was executed by DSH scripts/gates.py; Codex still owns the final phase sign-off.",
            "No database, solver, simulation, LLM or browser acceptance is in scope for this phase.",
        ])

        evidence = {
            "schema_version": SCHEMA_VERSION,
            "gate_id": self.gate_id,
            "phase": self.phase,
            "status": "failed" if failed else "passed",
            "started_at": started_at,
            "finished_at": utc_now(),
            "code_revision": self.revision,
            "dirty_tree_hash": self.dirty_tree_hash(),
            "dependency_evidence_hashes": self.dependency_evidence_hashes(),
            "input_artifact_hashes": self.input_artifact_hashes(),
            "environment_fingerprint": self.environment_fingerprint(),
            "commands": [result.as_dict() for result in task_commands],
            "acceptance_assertions": [check.as_dict() for check in assertion_checks],
            "record_checks": [check.as_dict() for check in record_checks],
            "failed_checks": [check.id for check in failed],
            "acceptance_artifacts": self.acceptance_artifacts(),
            "limitations": self.limitations,
            "reviewer": "dsh-scripts/gates.py",
        }
        self.write_evidence(evidence)
        self.print_summary(all_checks, task_commands)
        return 0 if not failed else 1

    def run_check_only(self, started_at: str) -> int:
        """Verify freshness only: run nothing, sign nothing."""
        path = self.out_dir / f"{self.gate_id}.json"
        payload = self.load_json(path)
        print(f"check-only: gate {self.gate_id} revision {self.revision}")
        if payload is None:
            print(f"check-only: no existing evidence at {path} (nothing signed yet)")
            print("check-only: gate not signed (no evidence file written)")
            return 0
        problems: list[str] = []
        if not self.records_official_gate:
            problems.append(f"--out-dir {self.out_dir} was given, so this is not the official gate record")
        stale = self.stale_input_hashes(payload.get("input_artifact_hashes", {}))
        if stale:
            problems.append(f"{len(stale)} stale input artifact hash(es), first: {stale[0]}")
        if payload.get("code_revision") not in {None, self.revision}:
            problems.append(
                f"recorded revision {payload.get('code_revision')!r} differs from current {self.revision!r}"
            )
        for command in payload.get("commands", []):
            log_path = self.root / command["log_path"]
            if not log_path.is_file():
                problems.append(f"missing command log {command['log_path']}")
            elif sha256_file(log_path) != command.get("log_sha256"):
                problems.append(f"command log changed: {command['log_path']}")
        zcode = self.check_zcode_precheck()
        codex = self.check_codex_review()
        problems.extend(check.detail for check in zcode + [codex] if not check.passed)
        previous = self.check_previous_gates()
        problems.extend(check.detail for check in previous if not check.passed)
        status = payload.get("status")
        print(f"check-only: recorded status={status}, failed_checks={payload.get('failed_checks', [])}")
        for problem in problems:
            print(f"check-only: STALE {problem}")
        if not problems:
            print("check-only: all recorded inputs are fresh; gate state unchanged (no file written)")
        print("check-only: gate not signed (no evidence file written)")
        return 0 if status == "passed" and not problems else 1

    # -- evidence building ---------------------------------------------------------

    def dirty_tree_hash(self) -> str:
        """Working-tree fingerprint over the same relevant file set as the candidate.

        Recorded separately from ``code_revision`` (contract section 4) and computed with a
        documented, distinct formula (path + byte size + content) so that the two evidence
        fields are independent values while both stay recomputable from repository content and
        free of logs, reports, review records and scratch files.
        """
        rows = [f"{relative}\0{size}\0{digest}" for relative, digest, size in self.relevant_manifest_rows()]
        return "content-sha256:" + sha256_text("\n".join(rows))

    def dependency_evidence_hashes(self) -> dict[str, str]:
        hashes = {}
        for gate_id in self.previous_gates():
            path = self.gate_dir / f"{gate_id}.json"
            if path.is_file():
                hashes[gate_id] = sha256_file(path)
        return hashes

    def input_artifact_hashes(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for task in self.phase_tasks():
            for relative in [task["task_doc"], task["report"], *task["files"]]:
                path = self.root / relative
                if path.is_file():
                    hashes[relative] = sha256_file(path)
        for relative in (MANIFEST_PATH, "uv.lock", "package-lock.json", "docs/plan/PHASE_GATES.md"):
            path = self.root / relative
            if path.is_file():
                hashes[relative] = sha256_file(path)
        return hashes

    def environment_fingerprint(self) -> dict:
        fingerprint = {
            "python": platform.python_version(),
            "os": f"{platform.system()} {platform.release()}",
        }
        for tool in ("uv", "node", "npm"):
            executable = resolve_tool(tool, self.root)
            try:
                completed = subprocess.run([executable, "--version"], capture_output=True, text=True,
                                           timeout=120, check=False)
                fingerprint[tool] = completed.stdout.strip().splitlines()[0] if completed.returncode == 0 else None
            except (OSError, subprocess.SubprocessError, IndexError):
                fingerprint[tool] = None
        return fingerprint

    def acceptance_artifacts(self) -> list[dict]:
        artifacts = []
        for relative in ("uv.lock", "package-lock.json"):
            path = self.root / relative
            if path.is_file():
                artifacts.append({"path": relative, "sha256": sha256_file(path)})
        for gate_id, digest in self.dependency_evidence_hashes().items():
            artifacts.append({"path": f"{GATES_DIR}/{gate_id}.json", "sha256": digest})
        return artifacts

    def write_evidence(self, evidence: dict) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f"{self.gate_id}.json"
        if not self.records_official_gate:
            evidence["official_gate_record"] = False
            evidence["official_gate_record_note"] = (
                f"written to {self.out_dir} because --out-dir was given; the official record lives at "
                f"{GATES_DIR}/{self.gate_id}.json and was NOT modified by this run"
            )
            evidence["limitations"] = [
                *evidence.get("limitations", []),
                "This run used --out-dir and therefore does not represent the phase gate record.",
            ]
        if path.is_file():
            previous = json.loads(path.read_text(encoding="utf-8"))
            runs = previous.get("runs", [])
            runs.append({
                "status": previous.get("status"),
                "finished_at": previous.get("finished_at"),
                "code_revision": previous.get("code_revision"),
                "failed_checks": previous.get("failed_checks", []),
            })
            evidence["runs"] = runs[-20:]
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {repo_relative(path, self.root)} (status: {evidence['status']})")

    def print_summary(self, checks: list[CheckResult], commands: list[CommandResult] | None = None) -> None:
        passed = [check for check in checks if check.passed]
        print(f"{self.gate_id}: {len(passed)}/{len(checks)} checks passed")
        for check in checks:
            marker = "PASS" if check.passed else "FAIL"
            print(f"  [{marker}] {check.id}: {check.detail}")
        if commands:
            durations = [result.duration_ms for result in commands]
            print(f"  commands: {len(commands)}, median {int(statistics.median(durations))} ms, "
                  f"total {sum(durations)} ms")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="phase gate evidence executor")
    parser.add_argument("--phase", required=True, help="two-digit phase number, e.g. 01")
    parser.add_argument("--revision", default="auto", help="'auto' or an explicit revision label")
    parser.add_argument("--check-only", action="store_true",
                        help="verify freshness only: run nothing and sign nothing")
    parser.add_argument("--assertion", action="append", default=None,
                        help="run only the named phase assertion (repeatable)")
    parser.add_argument("--skip-commands", action="store_true",
                        help="do not execute manifest commands or phase assertions (evidence/record "
                             "verification only); the gate can never pass this way")
    parser.add_argument("--out-dir", default=None,
                        help="write gate evidence and logs here instead of artifacts/gates "
                             "(sandboxed/self-test runs; such a record is marked non-official and "
                             "never overwrites the phase record)")
    parser.add_argument("--root", default=None, help="repository root (defaults to this script's parent)")
    args = parser.parse_args(argv)

    phase_text = str(args.phase).strip()
    if not re.fullmatch(r"\d{1,2}", phase_text):
        print(f"ARCH-CONFIG: --phase must be a one/two digit number, got {args.phase!r}", file=sys.stderr)
        return 2
    phase = int(phase_text)
    if phase == 0:
        print("ARCH-CONFIG: G00 is recorded by tools/ai_coding_plan/validate_plan.py --record-g00", file=sys.stderr)
        return 2

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    runner = GateRunner(
        root=root,
        phase=phase,
        revision=args.revision,
        only_checks=args.assertion,
        skip_commands=args.skip_commands,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )
    return runner.run(check_only=args.check_only)


if __name__ == "__main__":
    sys.exit(main())
