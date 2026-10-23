"""Assemble the P02-02 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P02-02/zcode/build-evidence.py

The script only reads repository files and writes the two records next to itself; it
never signs a Gate, and it starts no process (toolchain versions are read from the
existing G01 evidence fingerprint plus the pinned version files). Every hash it records
is recomputed here so Codex can rebuild and diff the record.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()


def sha(rel: str) -> str | None:
    path = root / rel
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(rel: str) -> str | None:
    path = root / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace").strip()


def read_json(rel: str) -> dict:
    text = read_text(rel)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def collect_logs() -> dict:
    records = {}
    for path in sorted(pathlib.Path("artifacts/handoffs/P02-02/zcode/logs").glob("*.log")):
        rel = path.as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        exit_code = None
        for line in reversed(text.splitlines()):
            if line.startswith("EXIT_CODE="):
                exit_code = int(line.split("=", 1)[1])
                break
        records[rel] = {"sha256": sha(rel), "bytes": path.stat().st_size, "exit_code": exit_code}
    return records


def collect_sandbox() -> dict:
    records = {}
    for path in sorted(pathlib.Path("tmp/zcode-g02-dryrun").rglob("*")):
        if path.is_file():
            rel = path.as_posix()
            records[rel] = {"sha256": sha(rel), "bytes": path.stat().st_size}
    return records


VERIFIED_INPUTS = [
    "docs/prompts/02-domain/P02-02-master-entities.md",
    "docs/prompts/02-domain/P02-01-primitives-and-states.md",
    "TASK_GRAPH.md",
    "docs/plan/TASK_MANIFEST.json",
    "docs/plan/PHASE_GATES.md",
    "docs/plan/TEST_FIXTURES.md",
    "docs/architecture/DOMAIN_CATALOG.md",
    "docs/architecture/DATA_CONTRACTS.md",
    "docs/architecture/CONTRACT_FREEZE.md",
    "docs/architecture/IMPLEMENTATION_CONVENTIONS.md",
    "docs/architecture/issues/README.md",
    "docs/api/API_CONTRACT.md",
    "docs/algorithms/OPTIMIZATION_CONTRACT.md",
    "docs/algorithms/SIMULATION_CONTRACT.md",
    "docs/algorithms/METRICS_CONTRACT.md",
    "packages/domain/src/logistics_domain/__init__.py",
    "packages/contracts/src/logistics_contracts/__init__.py",
    "scripts/gates.py",
    "scripts/check_architecture.py",
    "scripts/check_ownership.py",
    "OWNERSHIP.json",
    "pyproject.toml",
    "uv.lock",
    "package-lock.json",
    ".github/workflows/ci.yml",
    "playwright.config.ts",
    "apps/frontend/package.json",
    "artifacts/gates/G01.json",
    "artifacts/handoffs/P01-03/dsh/evidence.json",
]

DELIVERABLES = [
    "docs/implementation/P02-02.md",
    "docs/implementation/reports/P02-02.md",
    "packages/contracts/src/logistics_contracts/entities.py",
    "packages/domain/src/logistics_domain/orders.py",
    "packages/domain/src/logistics_domain/resources.py",
    "tests/integration/test_p02_02_master_entities.py",
    "tests/unit/test_p02_02_master_entities.py",
]

PHASE_TASKS = ("P02-01", "P02-02", "P02-03", "P02-04")

COMMANDS = [
    {
        "check_id": "P02-02-cmd1",
        "argv": "uv run pytest tests/unit/test_p02_02_master_entities.py tests/integration/test_p02_02_master_entities.py -q",
        "cwd": str(root),
        "exit_code": 4,
        "result": "ERROR: file or directory not found: tests/unit/test_p02_02_master_entities.py; no tests ran in 0.00s",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/cmd1-pytest.log",
        "mandatory": True,
        "passed": False,
    },
    {
        "check_id": "P02-02-cmd2",
        "argv": "uv run python scripts/check_architecture.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/cmd2-architecture.log",
        "mandatory": True,
        "passed": True,
        "caveat": "vacuous pass: the 7 scanned modules are the untouched P01-01 stubs and P02-02 added no domain code; must not be cited as task acceptance evidence",
    },
    {
        "check_id": "regression",
        "argv": "uv run pytest -q",
        "cwd": str(root),
        "exit_code": 0,
        "result": "187 passed",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/regression-pytest.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "architecture-verbose",
        "argv": "uv run python scripts/check_architecture.py --verbose",
        "cwd": str(root),
        "exit_code": 0,
        "result": "7 layers / 7 modules, violations=0",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/cmd2-architecture-verbose.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "ownership",
        "argv": "uv run python scripts/check_ownership.py --json",
        "cwd": str(root),
        "exit_code": 0,
        "result": "passed=true, violations=[], default_owner_fallbacks=[], 865 files scanned",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/ownership.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "lock-check",
        "argv": "uv lock --check",
        "cwd": str(root),
        "exit_code": 0,
        "result": "Resolved 40 packages",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/lock-check.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "uv-sync-frozen",
        "argv": "uv sync --frozen",
        "cwd": str(root),
        "exit_code": 0,
        "result": "Checked 39 packages",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/uv-sync.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "gates-phase01-check-only",
        "argv": "uv run python scripts/gates.py --phase 01 --revision auto --check-only",
        "cwd": str(root),
        "exit_code": 1,
        "result": "status=failed; failed_checks=[zcode-precheck:P01-01, zcode-precheck:P01-02, zcode-precheck:P01-03, codex-review]; recorded revision is STALE",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/gates-phase01-check-only.log",
        "mandatory": False,
        "passed": False,
    },
    {
        "check_id": "gates-phase02-check-only",
        "argv": "uv run python scripts/gates.py --phase 02 --revision auto --check-only",
        "cwd": str(root),
        "exit_code": 0,
        "result": "no existing evidence at artifacts/gates/G02.json (nothing signed yet)",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/gates-phase02-check-only.log",
        "mandatory": False,
        "passed": True,
        "caveat": "NO-OP trap: on a never-signed gate --check-only runs nothing and exits 0; exit 0 here does NOT mean Phase 02 is ready",
    },
    {
        "check_id": "gates-phase02-sandbox",
        "argv": "uv run python scripts/gates.py --phase 02 --revision auto --out-dir tmp/zcode-g02-dryrun",
        "cwd": str(root),
        "exit_code": 1,
        "result": "G02: 5/27 checks passed; all four P02-0X-cmd1 exit 4; previous-gate:G01 status=failed; DSH evidence / task docs / reports / zcode prechecks missing for all four Phase 02 tasks; codex-review missing",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/gates-phase02-dryrun.log",
        "mandatory": False,
        "passed": False,
        "note": "deliberately written to a non-official out-dir so this review neither signs nor overwrites artifacts/gates/G02.json",
    },
    {
        "check_id": "lint-ruff-scoped",
        "argv": "uv run ruff check apps/backend/src packages/*/src tests scripts",
        "cwd": str(root),
        "exit_code": 1,
        "result": "39 errors (RUF022, RUF001/RUF002 fullwidth punctuation, UP017, UP031, SIM300, F401, F841, RUF005); none from P02-02 because P02-02 has no files",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/lint-ruff-scoped.log",
        "mandatory": False,
        "passed": False,
        "established": False,
        "note": "ruff is declared in pyproject [dependency-groups].dev but no CI step or script runs it, so it is not an enforced project check yet",
    },
    {
        "check_id": "lint-ruff-repo",
        "argv": "uv run ruff check .",
        "cwd": str(root),
        "exit_code": 1,
        "result": "thousands of findings, including the read-only demo/ baseline; output 1571029 bytes",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/lint-ruff.log",
        "mandatory": False,
        "passed": False,
        "established": False,
    },
    {
        "check_id": "frontend-workspace-test",
        "argv": "npm --workspace @logistics/frontend run test --if-present",
        "cwd": str(root),
        "exit_code": 1,
        "result": "'vitest' is not recognized; apps/frontend declares test=vitest run but installs no devDependencies",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/frontend-test.log",
        "mandatory": False,
        "passed": False,
        "scoped_to": "P01-01 / CI, not P02-02",
    },
    {
        "check_id": "frontend-e2e-list",
        "argv": "npm run test:e2e:list",
        "cwd": str(root),
        "exit_code": 1,
        "result": "Error: No tests found / Total: 0 tests in 0 files",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/frontend-e2e-list.log",
        "mandatory": False,
        "passed": False,
        "scoped_to": "P01-02 / CI, not P02-02",
    },
    {
        "check_id": "secret-hygiene",
        "argv": "find/grep equivalent of the ci.yml secret-hygiene job (no git in this checkout)",
        "cwd": str(root),
        "exit_code": 0,
        "result": "no .env/*.pem/*.p12/id_rsa files and no sk-/AKIA literals in the target tree",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/secret-hygiene.log",
        "mandatory": False,
        "passed": True,
        "substituted_for": "the ci.yml secret-hygiene job (git ls-files / git grep cannot run without .git)",
    },
    {
        "check_id": "injection-scan",
        "argv": "grep -rnE 'shell=True|os.system|subprocess shell|eval|exec|pickle.loads' apps packages scripts tests",
        "cwd": str(root),
        "exit_code": 0,
        "result": "0 hits; no SQL string-assembly entry points; no database layer yet",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/security-injection-scan.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "revision-volatility",
        "argv": "snapshot of GateRunner.compute_revision() rows across two consecutive tool calls",
        "cwd": str(root),
        "exit_code": 0,
        "result": "1167 rows; .mimosa/** 451 rows (~39%) and tmp/** 423 rows (~36%); the only difference between the two snapshots was .mimosa/hook-state/<session>.json (plus this role's own new evidence files)",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log",
        "mandatory": False,
        "passed": True,
        "note": "supports defect D6 with a reproduction using the runner's own enumeration",
    },
    {
        "check_id": "pytest-cache-attribution",
        "argv": "sha256 of .pytest_cache/v/cache/{nodeids,lastfailed} before and after a 62-test run inside one shell call",
        "cwd": str(root),
        "exit_code": 0,
        "result": "both hashes unchanged -> the hypothesis that pytest itself shifts the gate revision is REFUTED",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/pytest-cache-attribution.log",
        "mandatory": False,
        "passed": True,
        "note": "recorded so the refuted hypothesis is not re-derived later",
    },
    {
        "check_id": "gate-precheck-recognition",
        "argv": "uv run python scripts/gates.py --phase 02 --revision auto --out-dir tmp/zcode-g02-dryrun2",
        "cwd": str(root),
        "exit_code": 1,
        "result": "[FAIL] zcode-precheck:P02-02: artifacts/handoffs/P02-02/zcode/precheck.json: status='BLOCKED' (expected 'Z_PRECHECK_PASSED')",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/gates-phase02-precheck-recognized.log",
        "mandatory": False,
        "passed": True,
        "note": "proves the record path/fields are recognised and that a BLOCKED record fails closed instead of being mistaken for a pass",
    },
    {
        "check_id": "interface-probe",
        "argv": "uv run python -c 'import logistics_domain, logistics_contracts; getattr(...)'",
        "cwd": str(root),
        "exit_code": 0,
        "result": "logistics_domain.entities/states/units/ids and logistics_contracts.dto/mapping/export_schema all raise NotImplementedError with an explicit pending owner",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/probe-interfaces.log",
        "mandatory": False,
        "passed": True,
        "note": "reproducible proof that the P02-01/P02-02/P02-04 interfaces are absent; the fail-loudly stub design itself is correct",
    },
]

REVERIFY_COMMANDS = [
    {
        "check_id": "reverify-cmd1",
        "pass": 2,
        "argv": "uv run pytest tests/unit/test_p02_02_master_entities.py tests/integration/test_p02_02_master_entities.py -q",
        "cwd": str(root),
        "exit_code": 4,
        "result": "ERROR: file or directory not found: tests/unit/test_p02_02_master_entities.py; no tests ran in 0.00s",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/reverify-cmd1-pytest.log",
        "mandatory": True,
        "passed": False,
    },
    {
        "check_id": "reverify-cmd2",
        "pass": 2,
        "argv": "uv run python scripts/check_architecture.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/reverify-cmd2-architecture.log",
        "mandatory": True,
        "passed": True,
        "caveat": "vacuous pass, same as pass 1: the scan sees the untouched P01-01 stubs only",
    },
    {
        "check_id": "reverify-regression",
        "pass": 2,
        "argv": "uv run pytest -q",
        "cwd": str(root),
        "exit_code": 0,
        "result": "187 passed",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/reverify-regression.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "reverify-gates-phase02",
        "pass": 2,
        "argv": "uv run python scripts/gates.py --phase 02 --revision auto --out-dir tmp/zcode-g02-dryrun-p2",
        "cwd": str(root),
        "exit_code": 1,
        "result": "G02: 5/27 checks passed; zcode-precheck:P02-02 now reported as status='BLOCKED' (expected 'Z_PRECHECK_PASSED'); previous-gate:G01 still status=failed",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/reverify-gates-phase02.log",
        "mandatory": False,
        "passed": False,
        "note": "sandbox out-dir; the official artifacts/gates/G02.json was not written",
    },
    {
        "check_id": "reverify-baseline",
        "pass": 2,
        "argv": "check_ownership.py --json ; uv lock --check ; credential-file find ; secret-literal grep ; injection grep",
        "cwd": str(root),
        "exit_code": 0,
        "result": "ownership passed=True violations=0 fallbacks=[] (915 files scanned, up from 865 purely because of this role's own evidence files); uv lock --check exit 0; no credential files; no sk-/AKIA literals; no shell=True/os.system/eval/exec/pickle.loads",
        "log_path": "artifacts/handoffs/P02-02/zcode/logs/reverify-baseline-checks.log",
        "mandatory": False,
        "passed": True,
    },
]

DEFECTS = [
    {
        "id": "D1",
        "severity": "blocking",
        "task": "P02-02",
        "title": "P02-02 has no deliverable at all (0/7 Files paths)",
        "evidence": [
            "logs/cmd1-pytest.log exit 4",
            "logs/gates-phase02-dryrun.log: P02-02-cmd1 exit_code=4; dsh-evidence:P02-02 missing; docs missing",
        ],
        "status": "unfixed",
        "owner": "DSH / P02-02",
    },
    {
        "id": "D2",
        "severity": "blocking",
        "task": "P02-01 + G01",
        "title": "Prerequisite P02-01 is undelivered and previous gate G01 is status=failed",
        "evidence": [
            "artifacts/gates/G01.json status=failed",
            "logs/gates-phase01-check-only.log",
            "TASK_GRAPH.md:46-47",
            "docs/plan/PHASE_GATES.md G01 row",
        ],
        "status": "unfixed",
        "owner": "DSH / P02-01, P01-01..P01-03 + Codex review",
    },
    {
        "id": "D3",
        "severity": "non-blocking-for-P02-02",
        "task": "P01-01",
        "title": "apps/frontend declares test=vitest run without devDependencies, so vitest is missing and the CI frontend job step fails",
        "evidence": [
            "apps/frontend/package.json",
            "logs/frontend-test.log exit 1",
            ".github/workflows/ci.yml:95",
        ],
        "status": "unfixed",
        "owner": "P01-01 (or P24-01)",
    },
    {
        "id": "D4",
        "severity": "non-blocking-for-P02-02",
        "task": "P01-02",
        "title": "npm run test:e2e:list exits 1 with zero specs while CI treats it as a required step",
        "evidence": [
            "logs/frontend-e2e-list.log exit 1",
            ".github/workflows/ci.yml:98",
            "playwright.config.ts comment claims an empty listing is legitimate",
        ],
        "status": "unfixed",
        "owner": "P01-02",
    },
    {
        "id": "D5",
        "severity": "non-blocking",
        "task": "engineering config",
        "title": "ruff is configured but never executed in CI, and its RUF001/RUF002 rules conflict with the project-wide Chinese fullwidth punctuation convention",
        "evidence": [
            "pyproject.toml [tool.ruff]",
            ".github/workflows/ci.yml (no ruff step)",
            "logs/lint-ruff-scoped.log 39 errors",
        ],
        "status": "unfixed",
        "owner": "engineering config / P01-02",
    },
    {
        "id": "D6",
        "severity": "non-blocking",
        "task": "P01-02",
        "title": "Gate revision is built from volatile session/scratch files (.mimosa/**, tmp/**), so a recorded code_revision is unreproducible from the next agent action",
        "evidence": [
            "scripts/gates.py:43 EXCLUDED_FROM_REVISION excludes only artifacts/gates and artifacts/e2e",
            "scripts/gates.py:327-342 compute_revision enumerates the whole tree: 1167 rows, of which .mimosa/** is 451 rows (~39%) and tmp/** is 423 rows (~36%)",
            ".mimosa/hook-state/<session>.json is rewritten by the agent host on every tool call; two snapshots one tool call apart differ exactly in that file (logs/revision-volatility.log)",
            "the G02 revision label moved 13321610... -> 94eafe09... -> f9ba8e61... during this review while only this role's own evidence files were written",
            "logs/gates-phase01-check-only.log: STALE recorded revision (ab054daf... can no longer be reproduced)",
        ],
        "status": "unfixed",
        "confidence": "proven by reproduction with the runner's own compute_revision(); the earlier pytest-cache hypothesis was tested and REFUTED (logs/pytest-cache-attribution.log: nodeids/lastfailed hashes unchanged after a 62-test run)",
        "owner": "P01-02",
    },
    {
        "id": "D7",
        "severity": "non-blocking (blocks G01 sign-off)",
        "task": "project management + P01-03",
        "title": "Handoff contract documents are absent (ARCH-0004 still open), so the record format has no contract source",
        "evidence": [
            "docs/architecture/issues/README.md ARCH-0004",
            "scripts/gates.py:305-311 comment",
        ],
        "status": "unfixed",
        "owner": "project management + P01-03",
    },
    {
        "id": "D8",
        "severity": "observation",
        "task": "environment baseline",
        "title": "Node baseline drift: .node-version pins 22 (what CI installs) while the local runtime and the G01 fingerprint record v24.18.0",
        "evidence": [
            ".node-version = 22",
            "package.json engines: node >=22 <25",
            "artifacts/gates/G01.json environment_fingerprint.node = v24.18.0",
            ".github/workflows/ci.yml uses node-version-file: .node-version",
        ],
        "status": "unfixed",
        "owner": "P01-01 / CI",
    },
]

g01_fingerprint = read_json("artifacts/gates/G01.json").get("environment_fingerprint", {})

payload = {
    "schema_version": "1.0.0",
    "task_id": "P02-02",
    "scene": "master-entities",
    "phase": 2,
    "phase_gate": "G02",
    "reviewer": "ZCode",
    "review_role": "independent-pre-acceptance",
    "status": "BLOCKED",
    "verdict_reason": (
        "P02-02 has no candidate at all: 0/7 Files paths exist, no DSH handoff was submitted, "
        "prerequisite P02-01 is undelivered and previous gate G01 is status=failed. Nothing could be pre-accepted."
    ),
    "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
    "verification_passes": {
        "first_review_at_local": "2026-09-14T23:42:43.662877-07:00",
        "reverified_at_local": datetime.datetime.now().astimezone().isoformat(),
        "purpose": "P02-02 was requested again on 2026-09-15; the tree was re-checked instead of reusing the first verdict.",
        "frozen_input_drift": (
            "all 29 verified_input_hashes from the first pass were recomputed and are byte-identical, "
            "so the prompts, manifests, contracts, locks and gate records this verdict binds to have not changed"
        ),
        "deliverable_count_pass1": 0,
        "deliverable_count_pass2": sum(1 for rel in DELIVERABLES if (root / rel).is_file()),
        "mandatory_command_result_pass1": "cmd1 exit 4 / cmd2 exit 0 (vacuous)",
        "mandatory_command_result_pass2": "cmd1 exit 4 / cmd2 exit 0 (vacuous)",
        "regression_pass1": "187 passed",
        "regression_pass2": "187 passed",
        "gate_state_pass1": "G02 sandbox 5/27, previous-gate:G01 failed",
        "gate_state_pass2": "G02 sandbox 5/27, previous-gate:G01 failed (unchanged)",
        "conclusion": "verdict unchanged: BLOCKED - no candidate exists to pre-accept",
    },
    "candidate": {
        "root": str(root),
        "vcs": "no .git in this checkout; located by content hash (scripts/gates.py compute_revision)",
        "revision_label_at_review_start": "content-sha256:1332161037086ddec70e4766df94d137743db391d55c6cd68b6329a8f0bef73a",
        "revision_label_mid_review": "content-sha256:94eafe09d58ffb18a24217b4b86169b4e408f53c54fcd26cd88fa11138c61e23",
        "revision_label_late_review": "content-sha256:f9ba8e61d5d9bdf18a859631f020c19ba0a2451613148bd4d9c5f2249952fdf9",
        "revision_note": (
            "the label moved three times during this review because compute_revision() hashes .mimosa/** session state "
            "and tmp/** scratch (only artifacts/gates and artifacts/e2e are excluded); the only writes in between were "
            "this role's own evidence files (defect D6). The runner recomputes the label on every invocation, so the "
            "value recorded here is a point-in-time snapshot, not a reproducible fingerprint."
        ),
        "previous_gate_recorded_revision": "content-sha256:ab054daf9c6c1373c6503f603805756ef3ef9c5a60400d07d8e938d6987e532b",
    },
    "deliverable_presence": {rel: (root / rel).is_file() for rel in DELIVERABLES},
    "deliverable_present_count": sum(1 for rel in DELIVERABLES if (root / rel).is_file()),
    "deliverable_expected_count": len(DELIVERABLES),
    "dsh_handoff": {
        "docs/handoffs/P02-02/dsh.md": (root / "docs/handoffs/P02-02/dsh.md").is_file(),
        "artifacts/handoffs/P02-02/dsh/evidence.json": (root / "artifacts/handoffs/P02-02/dsh/evidence.json").is_file(),
        "preserved_dsh_report": "none existed for P02-02; this role created or rewrote nothing on the DSH side",
    },
    "prerequisites": {
        "G01": {
            "status": "failed",
            "failed_checks": [
                "zcode-precheck:P01-01",
                "zcode-precheck:P01-02",
                "zcode-precheck:P01-03",
                "codex-review",
            ],
            "source": "artifacts/gates/G01.json + logs/gates-phase01-check-only.log",
            "blocks": "Phase 02 and later per docs/plan/PHASE_GATES.md",
        },
        "P02-01": {
            "delivered": False,
            "evidence": (
                "packages/domain/src/logistics_domain/ contains only the P01-01 __init__.py stub; "
                "docs/implementation/P02-01.md, reports/P02-01.md and artifacts/handoffs/P02-01/dsh/evidence.json are missing"
            ),
            "required_by": "TASK_GRAPH.md lines 46-47",
        },
        "G02": {"status": "not_signed", "sandbox_result": "G02: 5/27 checks passed (logs/gates-phase02-dryrun.log)"},
    },
    "gate_phase02_required_records": {
        task: {"task_doc": None, "report": None, "dsh_evidence": None, "zcode_precheck": None} for task in PHASE_TASKS
    },
    "commands": COMMANDS + REVERIFY_COMMANDS,
    "test_cases": {
        "1": {
            "input": "requirement 1001g vs vehicle 1000g",
            "expected": "representable data, allocation rule reports a capacity violation",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation and no test files exist (exit_code=4, 0 tests ran)",
        },
        "2": {
            "input": "cargo.temperature=[80,20]",
            "expected": "invalid input rejected",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation and no test files exist (exit_code=4, 0 tests ran)",
        },
        "coverage": "0 of 2 required test cases",
    },
    "defects": DEFECTS,
    "fixed_by_zcode": [],
    "unfixed": [d["id"] for d in DEFECTS],
    "not_verified": [
        "Schema / OpenAPI / generated-client consistency: the generators do not exist yet (scripts/export_contracts.py is P02-04, apps/frontend/scripts/generate-contracts.mjs is P24-02) - recorded as tool-not-built, NOT as a pass",
        "Static type checking: no mypy/pyright configuration exists; check_architecture.py covers import direction only",
        "Real PostgreSQL, real OR-Tools, SimPy, browser E2E: phases not reached",
        "npm ci: not re-run (it would rebuild node_modules); relies on the G01 record of exit 0",
        "CI as written cannot run in this checkout (no .git), so its git ls-files / git grep / git diff steps were replaced by a git-free equivalent",
        "Real CI on Node 22 was not executed; only the local Node runtime was used (see D8)",
        "Domain semantics beyond representation (solver capacity, time windows, temperature chain, storage occupancy, inventory, handover): no object exists at this phase",
    ],
    "security_review": {
        "scope": "current change set (empty for P02-02) plus a minimal baseline check",
        "credential_files": "none found (.env / .env.* / *.pem / *.p12 / id_rsa*) in the target tree",
        "secret_literals": "0 hits for sk-[A-Za-z0-9]{20,} and AKIA[0-9A-Z]{16}",
        "gitignore_covers": [".env", ".env.*", "tools/bin/", "node_modules/", ".venv/", "artifacts/e2e/"],
        "command_injection": "no shell=True / os.system / eval / exec / pickle.loads in apps|packages|scripts|tests; the gate runner executes argv arrays without a shell",
        "sql_injection": "no database access code exists yet (P03+); parameter binding is NOT APPLICABLE to this change set rather than verified",
        "auth_scope_logging": "P02-02 is a pure domain model (no framework, no telemetry, no logging backend); the HTTP boundary and redaction belong to P05-01/P37, nothing testable here",
        "dependency_changes": "none in this change set; uv lock --check exit 0",
        "external_targets_scanned": "none - no external production target was scanned",
        "zcode_own_artifacts": "the evidence builder for this record starts no subprocess and contains no shell invocation",
    },
    "tool_versions": {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "python_pin": read_text(".python-version"),
        "node_pin": read_text(".node-version"),
        "node_local_and_g01_fingerprint": g01_fingerprint.get("node"),
        "npm_recorded_in_g01": g01_fingerprint.get("npm"),
        "uv_recorded_in_g01": g01_fingerprint.get("uv"),
        "g01_fingerprint_os": g01_fingerprint.get("os"),
        "os": f"{platform.system()} {platform.release()}",
        "note": "uv/node/npm are quoted from the G01 environment fingerprint because this evidence builder deliberately starts no process",
    },
    "verified_input_hashes": {rel: sha(rel) for rel in VERIFIED_INPUTS},
    "evidence_logs": collect_logs(),
    "sandbox_gate_evidence": collect_sandbox(),
    "files_added_by_zcode": [
        "docs/handoffs/P02-02/zcode.md",
        "artifacts/handoffs/P02-02/zcode/evidence.json",
        "artifacts/handoffs/P02-02/zcode/precheck.json",
        "artifacts/handoffs/P02-02/zcode/build-evidence.py",
        "artifacts/handoffs/P02-02/zcode/logs/ (raw command logs for both verification passes)",
        "tmp/zcode-g02-dryrun/ and tmp/zcode-g02-dryrun-p2/ (non-official G02 sandbox evidence, under the gitignored tmp/)",
    ],
    "files_modified_by_zcode": [],
    "signs_gate": False,
    "gate_signed": None,
    "limitations": [
        "This record is BLOCKED on purpose: scripts/gates.py compares status against 'Z_PRECHECK_PASSED' and fails closed. DSH must re-deliver and re-request pre-acceptance; this record must not be reused.",
        "The record covers two verification passes (2026-09-14 and 2026-09-15) over the same unchanged tree; pass 2 re-ran every mandatory and adjacent check rather than reusing pass 1 output.",
        "P02-02-cmd2 (check_architecture.py) exit 0 is vacuous and is not acceptance evidence.",
        "docs/workflow/README.md and HANDOFF_CONTRACT.md do not exist (ARCH-0004); this record follows the user instruction plus the path hardcoded in scripts/gates.py:305-311, and the record layout still needs a project-side contract decision.",
        "The G02 revision label is not stable across this review for the reason in D6.",
    ],
    "next_actions": [
        "Codex: decide the revision-staleness policy (D6) and record the G01 codex review; G01 also needs the three zcode precheck records for P01-01..P01-03 before it can be signed.",
        "DSH: deliver P02-01 first, then P02-02 (task doc, report, DSH evidence, unit + integration tests), then request pre-acceptance again.",
        "Fix or explicitly defer D3/D4 so the CI frontend job is not permanently red.",
        "Decide the ruff policy (D5) before Chinese-docstring domain files land.",
        "Align .node-version with the intended Node baseline or record why local Node 24 is acceptable (D8).",
    ],
}

out_dir = pathlib.Path("artifacts/handoffs/P02-02/zcode")
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
for name in ("evidence.json", "precheck.json"):
    (out_dir / name).write_text(text, encoding="utf-8")

print("status:", payload["status"])
print("deliverables present:", payload["deliverable_present_count"], "/", payload["deliverable_expected_count"])
print("logs recorded:", len(payload["evidence_logs"]))
missing = [rel for rel, digest in payload["verified_input_hashes"].items() if digest is None]
print("inputs hashed:", len(payload["verified_input_hashes"]), "missing:", missing)
print("written:", (out_dir / "evidence.json").as_posix(), (out_dir / "precheck.json").as_posix())
print("bytes:", (out_dir / "evidence.json").stat().st_size)
