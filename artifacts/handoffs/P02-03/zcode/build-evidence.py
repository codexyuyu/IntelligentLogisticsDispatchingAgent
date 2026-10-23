"""Assemble the P02-03 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P02-03/zcode/build-evidence.py

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


def current_revision() -> str:
    """Ask the gate runner itself for the label, so it is never transcribed by hand."""
    scripts = str(root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        import gates

        return gates.GateRunner(root=root, phase=2, revision="auto").compute_revision()
    except Exception as exc:  # pragma: no cover - environment probe only
        return f"<unavailable: {exc}>"


BUILDER_LOG = "artifacts/handoffs/P02-03/zcode/logs/build-evidence.log"


def collect_logs() -> dict:
    """Inventory the raw command logs.

    The builder's own console log is deliberately excluded: this script is invoked with
    its stdout redirected into that very file, so reading it from inside the same run
    sees a truncated (often empty) file and would record a meaningless hash. The script
    itself is hashed separately in ``evidence_builder`` instead.
    """
    records = {}
    for path in sorted(pathlib.Path("artifacts/handoffs/P02-03/zcode/logs").glob("*.log")):
        rel = path.as_posix()
        if rel == BUILDER_LOG:
            continue
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
    for path in sorted(pathlib.Path("tmp/zcode-g02-dryrun-p3").rglob("*")):
        if path.is_file():
            rel = path.as_posix()
            records[rel] = {"sha256": sha(rel), "bytes": path.stat().st_size}
    return records


VERIFIED_INPUTS = [
    "docs/prompts/02-domain/P02-03-planning-entities.md",
    "docs/prompts/02-domain/P02-02-master-entities.md",
    "docs/prompts/02-domain/P02-04-runtime-contract-export.md",
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
    "artifacts/handoffs/P02-02/zcode/precheck.json",
]

DELIVERABLES = [
    "docs/implementation/P02-03.md",
    "docs/implementation/reports/P02-03.md",
    "packages/contracts/src/logistics_contracts/planning.py",
    "packages/domain/src/logistics_domain/planning.py",
    "tests/integration/test_p02_03_planning_entities.py",
    "tests/unit/test_p02_03_planning_entities.py",
]

DEPENDENCY_ARTIFACTS = [
    "docs/handoffs/P02-02/dsh.md",
    "artifacts/handoffs/P02-02/dsh/evidence.json",
    "docs/implementation/P02-02.md",
    "docs/implementation/reports/P02-02.md",
    "packages/domain/src/logistics_domain/orders.py",
    "packages/domain/src/logistics_domain/resources.py",
    "packages/contracts/src/logistics_contracts/entities.py",
    "packages/domain/src/logistics_domain/ids.py",
    "packages/domain/src/logistics_domain/units.py",
    "packages/domain/src/logistics_domain/states.py",
]

PHASE_TASKS = ("P02-01", "P02-02", "P02-03", "P02-04")

COMMANDS = [
    {
        "check_id": "P02-03-cmd1",
        "argv": "uv run pytest tests/unit/test_p02_03_planning_entities.py tests/integration/test_p02_03_planning_entities.py -q",
        "cwd": str(root),
        "exit_code": 4,
        "result": "ERROR: file or directory not found: tests/unit/test_p02_03_planning_entities.py; no tests ran in 0.00s",
        "log_path": "artifacts/handoffs/P02-03/zcode/logs/cmd1-pytest.log",
        "mandatory": True,
        "passed": False,
    },
    {
        "check_id": "P02-03-cmd2",
        "argv": "uv run python scripts/check_architecture.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
        "log_path": "artifacts/handoffs/P02-03/zcode/logs/cmd2-architecture.log",
        "mandatory": True,
        "passed": True,
        "caveat": "vacuous pass: the 7 scanned modules are the untouched P01-01 stubs and P02-03 added no domain code; must not be cited as task acceptance evidence",
    },
    {
        "check_id": "regression",
        "argv": "uv run pytest -q",
        "cwd": str(root),
        "exit_code": 0,
        "result": "187 passed",
        "log_path": "artifacts/handoffs/P02-03/zcode/logs/regression-pytest.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "gates-phase02-sandbox",
        "argv": "uv run python scripts/gates.py --phase 02 --revision auto --out-dir tmp/zcode-g02-dryrun-p3",
        "cwd": str(root),
        "exit_code": 1,
        "result": "G02: 5/27 checks passed; P02-03-cmd1 exit_code=4; dsh-evidence:P02-03 missing; docs:docs/implementation/P02-03.md missing; zcode-precheck:P02-03 missing; previous-gate:G01 status=failed",
        "log_path": "artifacts/handoffs/P02-03/zcode/logs/gates-phase02-sandbox.log",
        "mandatory": False,
        "passed": False,
        "note": "deliberately written to a non-official out-dir so this review neither signs nor overwrites artifacts/gates/G02.json",
    },
    {
        "check_id": "interface-probe",
        "argv": "uv run python -c 'import logistics_domain, logistics_contracts; probe planning'",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "logistics_domain.planning and logistics_contracts.planning both raise ModuleNotFoundError on import and "
            "AttributeError on attribute access; 'planning' is absent from both _PENDING_APIS registries, so the probe "
            "gets a bare AttributeError instead of the P01-01 fail-loudly message naming the owning task"
        ),
        "log_path": "artifacts/handoffs/P02-03/zcode/logs/probe-interfaces.log",
        "mandatory": False,
        "passed": True,
        "note": "reproducible proof that P02-03's frozen module surfaces do not exist; also the evidence for D9",
    },
    {
        "check_id": "baseline-checks",
        "argv": "check_ownership.py --json ; uv lock --check ; uv sync --frozen ; credential find ; secret grep ; injection grep",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "ownership passed=True violations=0 fallbacks=[] (930 files scanned); uv lock --check exit 0; "
            "uv sync --frozen exit 0; no credential files; no sk-/AKIA literals; no shell=True/os.system/eval/exec/pickle.loads"
        ),
        "log_path": "artifacts/handoffs/P02-03/zcode/logs/baseline-checks.log",
        "mandatory": False,
        "passed": True,
    },
]

DEFECTS = [
    {
        "id": "D1",
        "severity": "blocking",
        "task": "P02-03",
        "title": "P02-03 has no deliverable at all (0/6 Files paths)",
        "evidence": [
            "logs/cmd1-pytest.log exit 4 (0 tests ran)",
            "logs/gates-phase02-sandbox.log: P02-03-cmd1 exit_code=4; dsh-evidence:P02-03 missing; docs:docs/implementation/P02-03.md missing; docs:docs/implementation/reports/P02-03.md missing",
            "logs/probe-interfaces.log: neither logistics_domain.planning nor logistics_contracts.planning exists",
        ],
        "status": "unfixed",
        "owner": "DSH / P02-03",
    },
    {
        "id": "D2",
        "severity": "blocking",
        "task": "G01 + P02-02",
        "title": "Both declared prerequisites are unmet: G01 is status=failed and P02-02 was never delivered",
        "evidence": [
            "artifacts/gates/G01.json status=failed, failed_checks=[zcode-precheck:P01-01, zcode-precheck:P01-02, zcode-precheck:P01-03, codex-review]",
            "artifacts/handoffs/P02-02/dsh/evidence.json, docs/handoffs/P02-02/dsh.md, docs/implementation/P02-02.md, packages/domain/src/logistics_domain/orders.py and resources.py are all missing",
            "artifacts/handoffs/P02-02/zcode/precheck.json records BLOCKED for P02-02",
            "TASK_GRAPH.md:48 declares P02-03 dependencies as G01, P02-02",
            "docs/plan/PHASE_GATES.md: G01 failure blocks Phase 02 and later",
        ],
        "status": "unfixed",
        "owner": "DSH / P02-02, P01-01..P01-03 + Codex review",
    },
    {
        "id": "D3",
        "severity": "non-blocking-for-P02-03",
        "task": "P01-01",
        "title": "apps/frontend declares test=vitest run without devDependencies, so vitest is missing and the CI frontend job step fails",
        "evidence": [
            "apps/frontend/package.json",
            ".github/workflows/ci.yml:95",
            "carried over from the 2026-09-14 P02-02 review where the command exited 1 ('vitest' is not recognized)",
        ],
        "status": "unfixed",
        "owner": "P01-01 (or P24-01)",
        "reverified_this_pass": False,
    },
    {
        "id": "D4",
        "severity": "non-blocking-for-P02-03",
        "task": "P01-02",
        "title": "npm run test:e2e:list exits 1 with zero specs while CI treats it as a required step",
        "evidence": [
            ".github/workflows/ci.yml:98",
            "playwright.config.ts comment claims an empty listing is legitimate",
            "carried over from the 2026-09-14 P02-02 review (exit 1, 'No tests found')",
        ],
        "status": "unfixed",
        "owner": "P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D5",
        "severity": "non-blocking",
        "task": "engineering config",
        "title": "ruff is configured but never executed in CI, and its RUF001/RUF002 rules conflict with the project-wide Chinese fullwidth punctuation convention",
        "evidence": [
            "pyproject.toml [tool.ruff]",
            ".github/workflows/ci.yml (no ruff step)",
            "carried over from the 2026-09-14 P02-02 review: 39 errors in the target tree, none from P02-02",
        ],
        "status": "unfixed",
        "owner": "engineering config / P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D6",
        "severity": "non-blocking",
        "task": "P01-02",
        "title": "Gate revision is built from volatile session/scratch files (.mimosa/**, tmp/**), so a recorded code_revision is unreproducible from the next agent action",
        "evidence": [
            "scripts/gates.py:43 EXCLUDED_FROM_REVISION excludes only artifacts/gates and artifacts/e2e",
            "scripts/gates.py:327-342 compute_revision enumerates the whole tree; measured 1167 rows of which .mimosa/** is 451 and tmp/** is 423",
            ".mimosa/hook-state/<session>.json is rewritten by the agent host on every tool call",
            "the G02 label was content-sha256:336a208e... during this pass, versus ab054daf... recorded in G01 and 13321610.../94eafe09.../f9ba8e61... earlier the same day",
            "artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log and pytest-cache-attribution.log hold the reproduction and the refuted pytest-cache hypothesis",
        ],
        "status": "unfixed",
        "confidence": "proven by reproduction with the runner's own compute_revision() during the 2026-09-14 pass",
        "owner": "P01-02",
        "reverified_this_pass": True,
    },
    {
        "id": "D7",
        "severity": "non-blocking (blocks G01 sign-off)",
        "task": "project management + P01-03",
        "title": "Handoff contract documents are absent (ARCH-0004 still open), so the record format has no contract source",
        "evidence": [
            "docs/architecture/issues/README.md ARCH-0004 (open, blocking: yes)",
            "scripts/gates.py:305-311 comment",
            "docs/workflow/README.md and HANDOFF_CONTRACT.md do not exist in this checkout",
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
    {
        "id": "D9",
        "severity": "observation",
        "task": "P01-01",
        "title": "The P01-01 fail-loudly stub registry does not list the 'planning' module, so probing P02-03's frozen surface yields a bare AttributeError/ModuleNotFoundError instead of the message naming the owning task",
        "evidence": [
            "packages/domain/src/logistics_domain/__init__.py _PENDING_APIS keys = ['entities','ids','ports','states','units'] (no 'planning')",
            "packages/contracts/src/logistics_contracts/__init__.py _PENDING_APIS keys = ['dto','errors','export_schema','mapping'] (no 'planning')",
            "logs/probe-interfaces.log",
        ],
        "impact": (
            "cosmetic/consistency only: no caller can silently get a wrong result, since the module is simply absent. "
            "But the registry was clearly meant to cover every future module, and P02-02's 'entities' is listed while P02-03's "
            "'planning' is not, which makes the ownership hint inconsistent for whoever lands P02-03 and P02-04."
        ),
        "status": "unfixed",
        "owner": "P01-01 (registry owner); whoever lands P02-03 may extend it when the module is added",
    },
]

g01_fingerprint = read_json("artifacts/gates/G01.json").get("environment_fingerprint", {})

payload = {
    "schema_version": "1.0.0",
    "task_id": "P02-03",
    "scene": "planning-entities",
    "phase": 2,
    "phase_gate": "G02",
    "reviewer": "ZCode",
    "review_role": "independent-pre-acceptance",
    "status": "BLOCKED",
    "verdict_reason": (
        "P02-03 has no candidate at all: 0/6 Files paths exist, no DSH handoff was submitted, and both declared "
        "prerequisites are unmet (G01 status=failed, P02-02 never delivered). Nothing could be pre-accepted."
    ),
    "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
    "candidate": {
        "root": str(root),
        "vcs": "no .git in this checkout; located by content hash (scripts/gates.py compute_revision)",
        "revision_label_during_this_review": current_revision(),
        "revision_label_is_self_perturbing": (
            "by construction this label is one step stale: compute_revision() covers this record's own directory, so "
            "writing evidence.json and precheck.json moves the label again. Recompute it with the same call to compare; "
            "an exact match is impossible until defect D6 is fixed."
        ),
        "revision_note": (
            "the label is a point-in-time snapshot, not a reproducible fingerprint: compute_revision() hashes "
            ".mimosa/** session state and tmp/** scratch (only artifacts/gates and artifacts/e2e are excluded), and "
            ".mimosa/hook-state/<session>.json is rewritten on every tool call (defect D6)"
        ),
        "previous_gate_recorded_revision": "content-sha256:ab054daf9c6c1373c6503f603805756ef3ef9c5a60400d07d8e938d6987e532b",
    },
    "deliverable_presence": {rel: (root / rel).is_file() for rel in DELIVERABLES},
    "deliverable_present_count": sum(1 for rel in DELIVERABLES if (root / rel).is_file()),
    "deliverable_expected_count": len(DELIVERABLES),
    "dsh_handoff": {
        "docs/handoffs/P02-03/dsh.md": (root / "docs/handoffs/P02-03/dsh.md").is_file(),
        "artifacts/handoffs/P02-03/dsh/evidence.json": (root / "artifacts/handoffs/P02-03/dsh/evidence.json").is_file(),
        "preserved_dsh_report": "none existed for P02-03; this role created or rewrote nothing on the DSH side",
    },
    "dependency_presence": {rel: (root / rel).is_file() for rel in DEPENDENCY_ARTIFACTS},
    "prerequisites": {
        "G01": {
            "status": "failed",
            "failed_checks": [
                "zcode-precheck:P01-01",
                "zcode-precheck:P01-02",
                "zcode-precheck:P01-03",
                "codex-review",
            ],
            "source": "artifacts/gates/G01.json + logs/gates-phase02-sandbox.log",
            "blocks": "Phase 02 and later per docs/plan/PHASE_GATES.md",
        },
        "P02-02": {
            "delivered": False,
            "precheck_record": "artifacts/handoffs/P02-02/zcode/precheck.json (status BLOCKED, verified fresh 2026-09-14)",
            "evidence": "all P02-02 deliverable paths and its DSH handoff are missing; packages/domain/src/logistics_domain/ still holds only the P01-01 __init__.py stub",
            "required_by": "TASK_GRAPH.md:48 (P02-03 depends on G01, P02-02)",
        },
        "G02": {"status": "not_signed", "sandbox_result": "G02: 5/27 checks passed (logs/gates-phase02-sandbox.log)"},
    },
    "gate_phase02_required_records": {
        task: {"task_doc": None, "report": None, "dsh_evidence": None, "zcode_precheck": None} for task in PHASE_TASKS
    },
    "frozen_interface": {
        "declared": "ScheduleVersion(parent_version_id: UUID | None, snapshot_id: UUID, tasks: tuple[ScheduleTask, ...])",
        "domain_model_expected": [
            "TransportTask", "WarehouseTask", "Route", "RouteStop", "Schedule", "ScheduleTask",
            "ScheduleVersion", "Constraint", "OptimizationRequest", "OptimizationResult",
            "RescheduleRequest", "RescheduleResult",
        ],
        "business_rules_expected": [
            "stable task_id and version_id are separate",
            "version content is immutable; re-planning appends a new ScheduleVersion instead of overwriting history",
            "feasible status and validation status are expressed separately; an optimization result is never a confirmation",
            "version lineage has no cycle; without an incumbent the candidate must be empty",
        ],
    },
    "commands": COMMANDS,
    "test_cases": {
        "1": {
            "input": "status=TIMEOUT with candidate=null",
            "expected": "a legal failure result",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation and no test files exist (exit_code=4, 0 tests ran)",
        },
        "2": {
            "input": "parent_version_id pointing at the version itself",
            "expected": "rejected",
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
        "npm ci, the frontend workspace test and the Playwright listing were NOT re-run in this pass (no frontend file is in scope for P02-03); D3/D4 rest on the 2026-09-14 command output and are marked reverified_this_pass=false",
        "CI as written cannot run in this checkout (no .git), so its git ls-files / git grep / git diff steps cannot execute as written",
        "Real CI on Node 22 was not executed; only the local runtime was used (see D8)",
        "Immutability, lineage acyclicity and TIMEOUT/INFEASIBLE/UNKNOWN semantics cannot be exercised without the P02-01 primitives and the P02-03 planning module",
    ],
    "security_review": {
        "scope": "current change set (empty for P02-03) plus a minimal baseline check",
        "credential_files": "none found (.env / .env.* / *.pem / *.p12 / id_rsa*) in the target tree",
        "secret_literals": "0 hits for sk-[A-Za-z0-9]{20,} and AKIA[0-9A-Z]{16}",
        "gitignore_covers": [".env", ".env.*", "tools/bin/", "node_modules/", ".venv/", "artifacts/e2e/"],
        "command_injection": "no shell=True / os.system / eval / exec / pickle.loads in apps|packages|scripts|tests; the gate runner executes argv arrays without a shell",
        "sql_injection": "no database access code exists yet (P03+); parameter binding is NOT APPLICABLE to this change set rather than verified",
        "auth_scope_logging": "P02-03 is a pure domain model (no framework, no telemetry, no logging backend); the HTTP boundary and redaction belong to P05-01/P37, nothing testable here",
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
    "evidence_builder": {
        "path": "artifacts/handoffs/P02-03/zcode/build-evidence.py",
        "sha256": sha("artifacts/handoffs/P02-03/zcode/build-evidence.py"),
        "note": "this record's own generator; rerun it from the repository root to rebuild evidence.json and precheck.json",
    },
    "sandbox_gate_evidence": collect_sandbox(),
    "files_added_by_zcode": [
        "docs/handoffs/P02-03/zcode.md",
        "artifacts/handoffs/P02-03/zcode/evidence.json",
        "artifacts/handoffs/P02-03/zcode/precheck.json",
        "artifacts/handoffs/P02-03/zcode/build-evidence.py",
        "artifacts/handoffs/P02-03/zcode/logs/ (raw command logs)",
        "tmp/zcode-g02-dryrun-p3/ (non-official G02 sandbox evidence, under the gitignored tmp/)",
    ],
    "files_modified_by_zcode": [],
    "signs_gate": False,
    "gate_signed": None,
    "limitations": [
        "This record is BLOCKED on purpose: scripts/gates.py compares status against 'Z_PRECHECK_PASSED' and fails closed. DSH must re-deliver and re-request pre-acceptance; this record must not be reused.",
        "P02-03-cmd2 (check_architecture.py) exit 0 is vacuous and is not acceptance evidence.",
        "docs/workflow/README.md and HANDOFF_CONTRACT.md do not exist (ARCH-0004); this record follows the user instruction plus the path hardcoded in scripts/gates.py:305-311, and the record layout still needs a project-side contract decision.",
        "D3/D4/D5 were not re-executed in this pass because no frontend or lint artifact is in P02-03's scope; they carry the 2026-09-14 evidence and are flagged reverified_this_pass=false.",
    ],
    "next_actions": [
        "Codex: decide the revision-staleness policy (D6) and record the G01 codex review; G01 also needs the three zcode precheck records for P01-01..P01-03 before it can be signed.",
        "DSH: deliver P02-01, then P02-02, then P02-03 (task doc, report, DSH evidence, unit + integration tests), and only then request pre-acceptance.",
        "When P02-03 lands, add 'planning' to the _PENDING_APIS registries or the fail-loudly ownership hint stays inconsistent (D9).",
        "Fix or explicitly defer D3/D4 so the CI frontend job is not permanently red; decide the ruff policy (D5) before Chinese-docstring domain files land.",
    ],
}

out_dir = pathlib.Path("artifacts/handoffs/P02-03/zcode")
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
for name in ("evidence.json", "precheck.json"):
    (out_dir / name).write_text(text, encoding="utf-8")

print("status:", payload["status"])
print("deliverables present:", payload["deliverable_present_count"], "/", payload["deliverable_expected_count"])
print("dependency artifacts present:", sum(1 for v in payload["dependency_presence"].values() if v), "/", len(DEPENDENCY_ARTIFACTS))
print("logs recorded:", len(payload["evidence_logs"]))
missing = [rel for rel, digest in payload["verified_input_hashes"].items() if digest is None]
print("inputs hashed:", len(payload["verified_input_hashes"]), "missing:", missing)
print("written:", (out_dir / "evidence.json").as_posix(), (out_dir / "precheck.json").as_posix())
print("bytes:", (out_dir / "evidence.json").stat().st_size)
