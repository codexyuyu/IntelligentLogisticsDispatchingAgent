"""Assemble the P03-04 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P03-04/zcode/build-evidence.py

P03-04 is the last task of Phase 03, and with it all four Phase 03 tasks have submitted
honest BLOCKED handoffs. This record reviews the P03-04 submission, verifies the contract
citations DSH used to justify its verdict, and closes the phase-level picture. It only reads
the repository and writes the two records next to itself; it never signs a Gate.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()

BUILDER_LOG = "artifacts/handoffs/P03-04/zcode/logs/build-evidence.log"


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
    return path.read_text(encoding="utf-8", errors="replace").strip() if path.is_file() else None


def read_json(rel: str) -> dict:
    text = read_text(rel)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def contract_line(number: int) -> str:
    lines = (read_text("docs/architecture/DATA_CONTRACTS.md") or "").splitlines()
    return lines[number - 1] if len(lines) >= number else "<line unavailable>"


def current_revision() -> str:
    scripts = str(root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        import gates

        return gates.GateRunner(root=root, phase=3, revision="auto").compute_revision()
    except Exception as exc:  # pragma: no cover - environment probe only
        return f"<unavailable: {exc}>"


def collect_logs() -> dict:
    records = {}
    for path in sorted(pathlib.Path("artifacts/handoffs/P03-04/zcode/logs").glob("*.log")):
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
    out = {}
    for path in sorted(pathlib.Path("tmp/zcode-g03-dryrun-p4").rglob("*")):
        if path.is_file():
            rel = path.as_posix()
            out[rel] = {"sha256": sha(rel), "bytes": path.stat().st_size}
    return out


def presence(paths: list[str]) -> tuple[dict, int]:
    table = {rel: (root / rel).is_file() for rel in paths}
    return table, sum(1 for present in table.values() if present)


def dsh_review() -> dict:
    d = read_json("artifacts/handoffs/P03-04/dsh/evidence.json")
    rows, all_match = [], True
    for command in d.get("commands", []):
        rel = command.get("log_path")
        if not rel:
            continue
        actual, recorded = sha(rel), command.get("log_sha256")
        match = actual is not None and actual == recorded
        all_match = all_match and match
        rows.append(
            {
                "check_id": command.get("check_id"),
                "exit_code": command.get("exit_code"),
                "recorded_log_sha256": recorded,
                "actual_log_sha256": actual,
                "match": match,
            }
        )
    recorded_inputs = d.get("input_hashes") or {}
    recorded_presence = d.get("deliverable_presence") or {}
    drifted = {
        rel: {"recorded": was, "now": (root / rel).is_file()}
        for rel, was in recorded_presence.items()
        if was != (root / rel).is_file()
    }
    z3 = read_json("artifacts/handoffs/P03-03/zcode/precheck.json")
    return {
        "present": (root / "docs/handoffs/P03-04/dsh.md").is_file()
        and (root / "artifacts/handoffs/P03-04/dsh/evidence.json").is_file(),
        "claimed_status": d.get("status"),
        "signs_gate": d.get("signs_gate"),
        "gate_signed": d.get("gate_signed"),
        "log_rows": rows,
        "all_command_log_hashes_match": all_match,
        "recorded_input_count": len(recorded_inputs),
        "stale_recorded_inputs": [rel for rel, digest in recorded_inputs.items() if sha(rel) != digest],
        "deliverable_presence_snapshot_drift": drifted,
        "snapshot_corrections": [
            f"{rel}: recorded False but now True - the presence check ran before DSH wrote its own report documents"
            for rel in drifted
        ],
        "quotes_predecessor_verdict_correctly": z3.get("status") == "BLOCKED"
        and z3.get("code_and_test_present_count") == 0,
        "arch_issue_deliberately_not_registered": (
            "DSH decided not to open a new ARCH entry for the P02-03 type dependency, on the grounds that the contract "
            "already adjudicates it and registering would misattribute a delivery gap as a contract defect. I verified the "
            "underlying citations and agree with the reasoning"
        ),
        "overclaim_check": (
            "the report explicitly disclaims any unrun test; and its treatment of the 11/28 counter matches what I measure. "
            "No overclaim found"
        ),
        "verdict_on_submission": (
            "honest and accurate, and it adds a contract-level argument I verified line by line: the frozen interface needs "
            "CommitCommand, ValidationReport and CommitReceipt, which DATA_CONTRACTS.md assigns to P02-03 and which the "
            "stage-intertype rule requires P02-03 to define BEFORE P03 may reference them. So P03-04 is blocked at the type "
            "level even if G02 were signed, until P02-03 lands"
        ),
    }


DELIVERABLES = [
    "apps/backend/src/logistics_backend/persistence/idempotency.py",
    "apps/backend/src/logistics_backend/persistence/reservations.py",
    "apps/backend/src/logistics_backend/persistence/version_store.py",
    "docs/implementation/P03-04.md",
    "docs/implementation/reports/P03-04.md",
    "tests/integration/test_p03_04_atomic_version_store.py",
    "tests/unit/test_p03_04_atomic_version_store.py",
]

CODE_AND_TEST_DELIVERABLES = [
    "apps/backend/src/logistics_backend/persistence/idempotency.py",
    "apps/backend/src/logistics_backend/persistence/reservations.py",
    "apps/backend/src/logistics_backend/persistence/version_store.py",
    "tests/integration/test_p03_04_atomic_version_store.py",
    "tests/unit/test_p03_04_atomic_version_store.py",
]

DEPENDENCY_ARTIFACTS = [
    "artifacts/gates/G02.json",
    "artifacts/handoffs/P03-01/dsh/evidence.json",
    "artifacts/handoffs/P03-02/dsh/evidence.json",
    "artifacts/handoffs/P03-03/dsh/evidence.json",
    "apps/backend/src/logistics_backend/persistence/snapshots.py",
    "apps/backend/src/logistics_backend/persistence/uow.py",
    "packages/domain/src/logistics_domain/ports/storage.py",
    "packages/domain/src/logistics_domain/planning.py",
    "packages/domain/src/logistics_domain/entities.py",
    "packages/domain/src/logistics_domain/orders.py",
    "packages/domain/src/logistics_domain/resources.py",
    "packages/domain/src/logistics_domain/ids.py",
    "packages/domain/src/logistics_domain/units.py",
    "packages/domain/src/logistics_domain/states.py",
    "packages/domain/src/logistics_domain/execution.py",
    "packages/domain/src/logistics_domain/runtime.py",
    "packages/contracts/src/logistics_contracts/planning.py",
    "packages/contracts/src/logistics_contracts/runtime.py",
    "apps/backend/migrations/versions/0001_resources.py",
    "apps/backend/migrations/versions/0002_planning_runtime.py",
    "apps/backend/src/logistics_backend/persistence/resource_models.py",
    "apps/backend/src/logistics_backend/persistence/planning_models.py",
    "apps/backend/src/logistics_backend/persistence/runtime_models.py",
]

VERIFIED_INPUTS = [
    "docs/prompts/03-database/P03-04-atomic-version-store.md",
    "docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md",
    "TASK_GRAPH.md",
    "docs/plan/TASK_MANIFEST.json",
    "docs/plan/PHASE_GATES.md",
    "docs/architecture/DOMAIN_CATALOG.md",
    "docs/architecture/DATA_CONTRACTS.md",
    "docs/architecture/IMPLEMENTATION_CONVENTIONS.md",
    "docs/architecture/issues/README.md",
    "docs/api/API_CONTRACT.md",
    "packages/domain/src/logistics_domain/__init__.py",
    "apps/backend/pyproject.toml",
    "tests/conftest.py",
    "scripts/gates.py",
    "scripts/check_architecture.py",
    "pyproject.toml",
    "uv.lock",
    ".github/workflows/ci.yml",
    "artifacts/gates/G00.json",
    "artifacts/gates/G01.json",
    "artifacts/handoffs/P03-01/zcode/precheck.json",
    "artifacts/handoffs/P03-02/zcode/precheck.json",
    "artifacts/handoffs/P03-03/zcode/precheck.json",
    "artifacts/handoffs/P03-04/dsh/evidence.json",
    "docs/handoffs/P03-04/dsh.md",
    "docs/implementation/P03-04.md",
    "docs/implementation/reports/P03-04.md",
]

PHASE_TASKS = ("P03-01", "P03-02", "P03-03", "P03-04")

COMMANDS = [
    {
        "check_id": "P03-04-cmd1",
        "argv": "uv run pytest tests/unit/test_p03_04_atomic_version_store.py tests/integration/test_p03_04_atomic_version_store.py -q",
        "cwd": str(root),
        "exit_code": 4,
        "result": "ERROR: file or directory not found: tests/unit/test_p03_04_atomic_version_store.py; no tests ran in 0.00s",
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/cmd1-pytest.log",
        "mandatory": True,
        "passed": False,
        "agrees_with_dsh": True,
    },
    {
        "check_id": "P03-04-cmd2",
        "argv": "uv run python scripts/check_architecture.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/cmd2-architecture.log",
        "mandatory": True,
        "passed": True,
        "agrees_with_dsh": True,
        "caveat": "vacuous: the seven scanned modules are the untouched P01-01 stubs, and the checker cannot even cover this task's adapter-containment obligation (see D5)",
    },
    {
        "check_id": "regression",
        "argv": "uv run pytest -q",
        "cwd": str(root),
        "exit_code": 0,
        "result": "187 passed",
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/regression-pytest.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "gates-phase03-sandbox",
        "argv": "uv run python scripts/gates.py --phase 03 --revision auto --out-dir tmp/zcode-g03-dryrun-p4",
        "cwd": str(root),
        "exit_code": 1,
        "result": (
            "G03: 13/28. Composition: 1 previous-gate G00 row + 4 vacuous P03-0X-cmd2 rows + 8 documentation rows "
            "(2 per task x 4 tasks). Every other row fails: all four P03-0X-cmd1 are exit 4, all four dsh-evidence rows "
            "are 'unexpected status=BLOCKED', zcode-precheck shows BLOCKED x3 and missing x1, and previous-gate G01 failed "
            "with G02 missing"
        ),
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/gates-phase03-sandbox.log",
        "mandatory": False,
        "passed": False,
        "note": "sandbox out-dir; artifacts/gates/G03.json was NOT written. Reconciles with DSH's 11/28 (its two docs now exist: 11 + 2 = 13)",
    },
    {
        "check_id": "contract-citation-check",
        "argv": "read DATA_CONTRACTS.md lines 24, 55, 56, 79, 96, 97 and the frozen error table",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "DSH's citations are exact: ValidationReport is '纯类型P02-03'; CommitCommand is P02-03/P16-03; CommitReceipt is "
            "P02-03; line 79 requires P02-03 to define these pure value types before P03 may reference them and forbids a "
            "second same-named definition; line 96 freezes PlanCommitStore.commit as 单事务, called by ScheduleService; line "
            "97 makes ScheduleService the only official plan-commit use case. The error table DOES freeze IDEMPOTENCY_CONFLICT "
            "in the 409 group"
        ),
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/contract-citation-check.log",
        "mandatory": False,
        "passed": True,
        "note": "verifies the paper dependency on P02-03 and closes a question nobody asked: this task's error code has a contract source, unlike UNSUPPORTED (ARCH-0003)",
    },
    {
        "check_id": "architecture-coverage-reverify",
        "argv": "uv run python artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "re-verified: scenario A detects an ORM import in the backend API layer, scenario B (backend declares sqlalchemy) does not",
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/architecture-coverage-reverify.log",
        "mandatory": False,
        "passed": False,
        "note": "keeps the D5 finding current for this pass rather than carrying it forward unchecked",
    },
    {
        "check_id": "dsh-evidence-integrity",
        "argv": "independent recomputation of the hashes recorded in artifacts/handoffs/P03-04/dsh/evidence.json",
        "cwd": str(root),
        "exit_code": 0,
        "result": "all 4 command-log hashes match; all 15 recorded input hashes match; no stale recorded input; quoted predecessor verdicts correct",
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/dsh-evidence-integrity.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "g01-shortfall-diagnostic",
        "argv": "uv run python scripts/gates.py --phase 01 --revision auto --out-dir tmp/zcode-g01-diagnostic",
        "cwd": str(root),
        "exit_code": 1,
        "result": (
            "G01: 22/26. Passing: all 7 task commands, all 5 acceptance assertions, previous-gate G00, all 3 DSH evidence "
            "rows (READY_FOR_ZCODE), all 6 task document rows. Failing: exactly the 3 zcode precheck records plus the codex "
            "review, i.e. 4 missing JSON files and no code work"
        ),
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/g01-diagnostic.log",
        "mandatory": False,
        "passed": False,
        "note": "sandbox out-dir; artifacts/gates/G01.json was NOT written or re-signed by this role",
    },
    {
        "check_id": "barrier-diagnostic-claim-verification",
        "argv": "independent recomputation of the claims in docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md",
        "cwd": str(root),
        "exit_code": 0,
        "result": "all six load-bearing claims confirmed: 22/26 composition, 40/40 inputs undrifted, uv.lock+pyproject are G01 inputs, the stale conftest hash trap is real, the 4 records are absent, the 3 DSH evidences are accepted",
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/g01-claim-verification.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "environment-and-baseline",
        "argv": "which psql pg_ctl ; uv lock --check ; check_ownership.py --json ; credential find ; secret grep ; injection grep ; SQL-assembly grep",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "psql/pg_ctl absent; TEST_DATABASE_URL unset; uv.lock 40 packages with NO alembic/sqlalchemy/psycopg; ownership "
            "passed=True violations=0 (1165 files); no credential files; no sk-/AKIA literals; no shell=True/os.system/eval/"
            "exec/pickle.loads; no SQL string assembly"
        ),
        "log_path": "artifacts/handoffs/P03-04/zcode/logs/baseline-checks.log",
        "mandatory": False,
        "passed": True,
    },
]

DEFECTS = [
    {
        "id": "D1",
        "severity": "blocking",
        "task": "P03-04",
        "title": "No implementation candidate exists: 0/5 code-and-test deliverables were written (only the two BLOCKED report documents exist, 2/7 paths present)",
        "evidence": [
            "logs/cmd1-pytest.log exit 4 (0 tests ran)",
            "logs/gates-phase03-sandbox.log: P03-04-cmd1 exit_code=4",
            "logs/dsh-evidence-integrity.log: DSH recorded 0/7 before writing its two docs; those two are present now",
            "the persistence package does not exist at all, so idempotency.py, reservations.py and version_store.py have no parent",
        ],
        "status": "unfixed",
        "owner": "DSH / P03-04",
    },
    {
        "id": "D2",
        "severity": "blocking",
        "task": "G02 + P03-03 + G01",
        "title": "Both declared prerequisites are unmet, and the interface's types are owned by an undelivered Phase 02 task",
        "evidence": [
            "artifacts/gates/G02.json does not exist; the phase-02 probe has read G02: 5/27 identically in all five rounds",
            "artifacts/handoffs/P03-03/dsh/evidence.json and .../P03-03/zcode/precheck.json are both BLOCKED; P03-03 code+test 0/5",
            "artifacts/gates/G01.json status=failed (its 5 acceptance assertions all pass; only handoff records are missing)",
            "DATA_CONTRACTS.md line 55/56/24 assign CommitCommand, CommitReceipt and ValidationReport to P02-03",
            "DATA_CONTRACTS.md line 79 requires P02-03 to define those pure value types before P03 references them, and forbids a second same-named definition",
            "dependency artifacts present: 3/23, and all three are the predecessors' own BLOCKED evidence records",
        ],
        "status": "unfixed",
        "owner": "Codex (G01 review) + ZCode (P01-01..P01-03 prechecks) + role A/DSH (P02-01..04 first)",
    },
    {
        "id": "D3",
        "severity": "blocking-for-this-task-when-reissued",
        "task": "P03-04 scope / planning",
        "title": "The task's 7-file allow-list omits the dependency manifests it needs; fourth task in a row with this gap",
        "evidence": [
            "allowed_files = [idempotency.py, reservations.py, version_store.py, both docs, both tests] - apps/backend/pyproject.toml and uv.lock are absent",
            "uv.lock has 40 packages and none of them is alembic, sqlalchemy, psycopg or psycopg-binary",
            "test case 1 needs two real concurrent transactions competing for one dock row, i.e. a real PostgreSQL and an ORM/driver",
        ],
        "impact": "confirmed across all four Phase 03 tasks: this is a planning-level gap to fix once, not a per-task oversight",
        "status": "unfixed",
        "owner": "project management / planning",
    },
    {
        "id": "D4",
        "severity": "blocking-for-acceptance",
        "task": "P01-01 (environment manual)",
        "title": "The Phase 01 environment manual that defines the isolated PostgreSQL startup still does not exist",
        "evidence": [
            "tests/conftest.py:158 points the reader to 'the Phase 01 environment manual'",
            "docs/architecture/IMPLEMENTATION_CONVENTIONS.md:9 states the manual defines both Docker and local PostgreSQL startup",
            "no such document exists under docs/; this host has no psql/pg_ctl and no running Docker daemon",
        ],
        "status": "unfixed",
        "owner": "Phase 01 environment documentation owner",
    },
    {
        "id": "D5",
        "severity": "blocking-for-acceptance-of-the-core-obligation",
        "task": "P01-02 (checker coverage)",
        "title": "The architecture checker cannot detect an ORM leaking out of the adapter once the ORM is legitimately declared, so the containment obligation G03 cares about has no automated enforcement",
        "evidence": [
            "re-verified this pass: logs/architecture-coverage-reverify.log (scenario A detects, scenario B does not)",
            "scripts/check_architecture.py LAYERS['backend'] covers all of apps/backend/src as one layer; THIRD_PARTY forbids sqlalchemy/alembic/psycopg only in the domain layer",
            "original experiment: artifacts/handoffs/P03-03/zcode/logs/architecture-coverage-probe.log",
        ],
        "impact": (
            "for P03-04 this matters more than for P03-03: the task's whole point is that reservation and version writes stay "
            "inside one transaction and that ORM objects do not escape into application code. Acceptance criterion 3 "
            "('dependency boundary check passes') cannot speak to any of it"
        ),
        "status": "unfixed",
        "owner": "P01-02",
        "reverified_this_pass": True,
    },
    {
        "id": "D6",
        "severity": "non-blocking (contract gap)",
        "task": "P01-02 / ARCH-0004",
        "title": "The gate runner has no accepted state for a prerequisite-blocked handoff; all four Phase 03 tasks are now flagged for reporting honestly",
        "evidence": [
            "logs/gates-phase03-sandbox.log: dsh-evidence:P03-01, P03-02, P03-03 and P03-04 all 'unexpected status=BLOCKED'",
            "scripts/gates.py accepts only READY_FOR_ZCODE and Z_PRECHECK_PASSED for DSH evidence",
            "every task book orders a BLOCKED report when prerequisites are missing",
        ],
        "status": "unfixed",
        "owner": "P01-02 + ARCH-0004 decision",
    },
    {
        "id": "D7",
        "severity": "non-blocking (misleading metric)",
        "task": "P01-02 (gate runner)",
        "title": "The G03 pass count rose again purely from documentation: 13/28 = 1 + 4 + 2x4, confirming the formula at the fifth measurement",
        "evidence": [
            "five measurements across the four tasks: 5/28, 7/28, 9/28, 11/28, 13/28",
            "composition at 13/28: 1 G00 row + 4 vacuous cmd2 rows + 8 documentation rows (2 per task)",
            "all four P03-0X-cmd1 rows are exit 4; the implemented-deliverable count across the whole phase is zero",
        ],
        "impact": "the counter is anti-correlated with real progress; DSH independently reached the same conclusion in its P03-03 section 4 and P03-04 section 3",
        "status": "unfixed",
        "owner": "P01-02",
    },
    {
        "id": "D8",
        "severity": "non-blocking-for-P03-04",
        "task": "P01-01",
        "title": "apps/frontend declares test=vitest run without devDependencies, so the CI frontend job step fails",
        "evidence": ["apps/frontend/package.json", ".github/workflows/ci.yml:95", "carried over from the 2026-09-14 review"],
        "status": "unfixed",
        "owner": "P01-01 (or P24-01)",
        "reverified_this_pass": False,
    },
    {
        "id": "D9",
        "severity": "non-blocking-for-P03-04",
        "task": "P01-02",
        "title": "npm run test:e2e:list exits 1 with zero specs while CI treats it as a required step",
        "evidence": [".github/workflows/ci.yml:98", "playwright.config.ts comment", "carried over from the 2026-09-14 review"],
        "status": "unfixed",
        "owner": "P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D10",
        "severity": "non-blocking",
        "task": "engineering config",
        "title": "ruff is configured but never executed in CI, and its RUF001/RUF002 rules conflict with the Chinese fullwidth punctuation convention",
        "evidence": ["pyproject.toml [tool.ruff]", ".github/workflows/ci.yml (no ruff step)", "carried over from the 2026-09-14 review"],
        "status": "unfixed",
        "owner": "engineering config / P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D11",
        "severity": "non-blocking",
        "task": "P01-02",
        "title": "Gate revision is built from volatile session/scratch files (.mimosa/**, tmp/**), so a recorded code_revision is unreproducible",
        "evidence": [
            "scripts/gates.py:43 EXCLUDED_FROM_REVISION excludes only artifacts/gates and artifacts/e2e",
            "measured 1167 rows of which .mimosa/** is 451 and tmp/** is 423",
            ".mimosa/hook-state/<session>.json is rewritten on every tool call",
            "reproduced by ZCode and independently by DSH in all four Phase 03 handoffs",
        ],
        "status": "unfixed",
        "confidence": "proven by reproduction; four independent DSH observations",
        "owner": "P01-02",
        "reverified_this_pass": True,
    },
    {
        "id": "D12",
        "severity": "observation",
        "task": "P01-01",
        "title": "The _PENDING_APIS registry still omits the Phase 02 module names (planning, execution, runtime, common); P03-03's 'ports' is correctly registered",
        "evidence": [
            "logistics_domain._PENDING_APIS = ['entities','ids','ports','states','units']",
            "logistics_contracts._PENDING_APIS = ['dto','errors','export_schema','mapping']",
        ],
        "status": "unfixed",
        "owner": "P01-01",
    },
]

dsh = dsh_review()
g01 = read_json("artifacts/gates/G01.json")
fingerprint = g01.get("environment_fingerprint", {})
deliverable_table, deliverable_count = presence(DELIVERABLES)
code_table, code_count = presence(CODE_AND_TEST_DELIVERABLES)
dep_table, dep_count = presence(DEPENDENCY_ARTIFACTS)

payload = {
    "schema_version": "1.0.0",
    "task_id": "P03-04",
    "scene": "atomic-version-store",
    "phase": 3,
    "phase_gate": "G03",
    "reviewer": "ZCode",
    "review_role": "independent-pre-acceptance",
    "status": "BLOCKED",
    "verdict_reason": (
        "P03-04 has no implementation candidate: the five code-and-test deliverables do not exist and only the two "
        "BLOCKED-report documents were written. Its declared prerequisites are unmet (G02 has no record, P03-03 is BLOCKED "
        "with 0/5 code deliverables), the transitive prerequisite G01 is status=failed, the interface's value types are "
        "owned by the undelivered P02-03 per the frozen contract, and no PostgreSQL is reachable. DSH's BLOCKED verdict is "
        "independently confirmed; nothing could be pre-accepted."
    ),
    "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
    "candidate": {
        "root": str(root),
        "vcs": "no .git in this checkout; located by content hash (scripts/gates.py compute_revision)",
        "revision_label_during_this_review": current_revision(),
        "revision_label_is_self_perturbing": "one step stale by construction: compute_revision() covers this record's own directory (D11)",
        "previous_gate_recorded_revision": "content-sha256:ab054daf9c6c1373c6503f603805756ef3ef9c5a60400d07d8e938d6987e532b",
    },
    "deliverable_presence": deliverable_table,
    "deliverable_present_count": deliverable_count,
    "deliverable_expected_count": len(DELIVERABLES),
    "code_and_test_presence": code_table,
    "code_and_test_present_count": code_count,
    "code_and_test_expected_count": len(CODE_AND_TEST_DELIVERABLES),
    "dsh_submission": dsh,
    "dependency_presence": dep_table,
    "dependency_present_count": dep_count,
    "dependency_expected_count": len(DEPENDENCY_ARTIFACTS),
    "prerequisites": {
        "G01": {
            "status": "failed",
            "failed_checks": list(g01.get("failed_checks", [])),
            "acceptance_assertions_all_passed": all(a.get("passed") for a in g01.get("acceptance_assertions", []))
            if g01.get("acceptance_assertions")
            else None,
            "blocks": "Phase 02 and later per docs/plan/PHASE_GATES.md",
        },
        "G02": {"status": "not_signed", "record_exists": (root / "artifacts/gates/G02.json").is_file()},
        "P03-03": {"status": "BLOCKED", "record": "artifacts/handoffs/P03-03/zcode/precheck.json", "code_and_test_present": "0/5"},
        "G03": {"status": "not_signed", "sandbox_result": "G03: 13/28 checks passed"},
    },
    "type_chain_coupling": {
        "finding": (
            "P03-04 is blocked at the type level by contract text, independently of the Gates: its frozen interface needs "
            "CommitCommand, ValidationReport and CommitReceipt, and DATA_CONTRACTS.md assigns all three to P02-03 while "
            "requiring P02-03 to define them before P03 may reference them."
        ),
        "verified_citations": {
            "line 24": contract_line(24),
            "line 55": contract_line(55),
            "line 56": contract_line(56),
            "line 79": contract_line(79)[:400],
            "line 96": contract_line(96),
            "line 97": contract_line(97),
        },
        "consequence": (
            "even with G02 signed, P03-04 cannot be implemented until P02-03 lands; and a second same-named definition is "
            "forbidden, so the storage layer cannot declare its own CommitCommand to work around it. Order matters: P02 before P03."
        ),
        "positive_note": (
            "this task's error code is properly frozen: IDEMPOTENCY_CONFLICT appears in the 409 group of the error table, so "
            "test case 2 has a contract source. (UNSUPPORTED is absent from that table, which ARCH-0003 already records - not "
            "a new gap and not P03-04's concern.)"
        ),
    },
    "phase_03_closure": {
        "state": "all four Phase 03 tasks have now submitted handoffs, and all four are BLOCKED with zero code deliverables",
        "per_task": {
            "P03-01": {"dsh": "BLOCKED", "zcode": "BLOCKED", "code_and_test_present": "0/6"},
            "P03-02": {"dsh": "BLOCKED", "zcode": "BLOCKED", "code_and_test_present": "0/5"},
            "P03-03": {"dsh": "BLOCKED", "zcode": "BLOCKED", "code_and_test_present": "0/5"},
            "P03-04": {"dsh": "BLOCKED", "zcode": "BLOCKED (this record)", "code_and_test_present": "0/5"},
        },
        "implemented_deliverables_in_phase_03": 0,
        "phase_03_code_and_test_expected": 21,
        "g03_assertions_ever_executed": False,
        "g03_assertions": [
            "real PostgreSQL migration, rollback and FK pass",
            "consistent snapshot",
            "the last resource's concurrent commit succeeds exactly once",
            "no half version on transaction failure",
        ],
        "consequence": (
            "G03 cannot be assembled from any direction, and Phase 04 and later remain blocked behind it. A phase summary for "
            "Phase 03 would have nothing to aggregate except four blocked reports; the repair work is entirely upstream."
        ),
    },
    "mid_review_artifact": {
        "path": "docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md",
        "created_during_this_review": True,
        "author": "DSH, produced under an explicit user authorisation for a read-only barrier diagnostic",
        "nature": "not a task deliverable, not gate evidence, signs nothing - it says so itself",
        "why_it_matters": (
            "it is the first artifact that quantifies the unblocking cost precisely, and its numbers survived my independent "
            "recomputation. It also warns about an ordering trap that would otherwise cost a second G01 sign-off"
        ),
        "claims_i_verified": [
            "G01 is 22/26, and the only 4 failures are the 3 zcode precheck records plus the codex review - measured independently by me in a sandbox run that signs nothing",
            "G01.json records 40 input_artifact_hashes and 0 of them have drifted, so the old G01 evidence is not stale; only the records are missing",
            "uv.lock and all seven pyproject.toml files ARE registered as G01 input artifacts, so adding the database dependencies drifts G01's inputs and forces a re-sign - the lock change should therefore happen before G01's final sign-off, otherwise it is paid for twice",
            "the stale-hash trap is real: artifacts/handoffs/P01-02/dsh/evidence.json records tests/conftest.py as 95ad3430... while the file on disk is b4c985aa..., because P01-03 later extended that file for the database fixtures. Copying historical hashes would fail with 'N stale input hash(es)'",
            "the 3 P01 DSH evidences are READY_FOR_ZCODE, which gates.py accepts, so they are not part of the shortfall",
            "the 3 P01 precheck records and the codex review file are genuinely absent",
        ],
        "what_i_did_not_do_and_why": (
            "I did NOT write the three P01-01..P01-03 precheck records, even though three of the four missing files are this "
            "role's own debt and it is the single highest-leverage action in the project. This round's assigned task is P03-04, "
            "and a Z_PRECHECK_PASSED record is only honest if it follows a real independent verification pass per task: its own "
            "mandatory commands, its own boundary checks and its own logs. Issuing three pass verdicts without that work would "
            "be exactly the kind of paperwork shortcut this role exists to prevent. It is a separate, self-contained piece of "
            "work and should be requested as such."
        ),
    },
    "g01_shortfall": {
        "measured_by_this_role": "22/26, sandbox out-dir, nothing signed",
        "passing": [
            "7/7 task commands",
            "5/5 acceptance assertions (clean-install-imports, layer-boundaries, lock-reproducible, runner-fails-closed, legacy-demo-untouched)",
            "previous-gate:G00",
            "3/3 DSH evidences as READY_FOR_ZCODE",
            "6/6 task document and report rows",
        ],
        "failing": [
            "zcode-precheck:P01-01",
            "zcode-precheck:P01-02",
            "zcode-precheck:P01-03",
            "codex-review",
        ],
        "code_changes_required_to_reach_26_of_26": 0,
        "missing_files": 4,
        "owned_by_zcode": 3,
        "owned_by_codex": 1,
        "input_drift": "40 recorded input_artifact_hashes, 0 drifted",
        "ordering_trap": "uv.lock and the seven pyproject.toml files are G01 inputs, so the database dependency change must land before G01's final sign-off",
        "hash_trap": "do not copy tests/conftest.py hashes out of artifacts/handoffs/P01-02/dsh/evidence.json (95ad3430... there vs b4c985aa... on disk)",
    },
    "architecture_checker_coverage": {
        "question": "can scripts/check_architecture.py detect an ORM leaking out of the adapter layer?",
        "answer": "No, once the ORM is legitimately declared.",
        "reverified_this_pass": True,
        "evidence": "artifacts/handoffs/P03-04/zcode/logs/architecture-coverage-reverify.log",
    },
    "gate_pass_count_perversity": {
        "formula": "G03 pass count = 1 (previous-gate G00) + 4 (vacuous P03-0X-cmd2 architecture rows) + 2 x (Phase 03 tasks that wrote only their BLOCKED docs)",
        "measured": ["5/28", "7/28", "9/28", "11/28", "13/28"],
        "checked_at_n_equals_4": True,
        "consequence": "with all four tasks blocked the counter sits at its maximum while the implemented-deliverable count is zero",
    },
    "frozen_interface": {
        "declared": "PlanCommitStore.commit(cmd: CommitCommand, report: ValidationReport) -> CommitReceipt",
        "frozen_contract_note": "DATA_CONTRACTS.md line 96 freezes it as single-transaction and called by ScheduleService; line 97 makes ScheduleService the only official plan-commit use case",
        "types_required_and_absent": ["CommitCommand", "ValidationReport", "CommitReceipt", "ScheduleVersion", "PlanCommitStore"],
        "business_rules_expected": [
            "this phase tests storage transactions only; no public commit route may be exposed yet",
            "the validation report must match the candidate and snapshot hashes",
            "lock resource rows in a fixed order, re-check version and slot capacity, CAS active_version_id, then atomically write the new version, reservation, audit and outbox",
            "the same idempotency key with the same body returns the original receipt",
        ],
    },
    "commands": COMMANDS,
    "test_cases": {
        "1": {
            "input": "two transactions competing for the last free dock",
            "expected": "exactly one succeeds",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation, no tests, no PostgreSQL; needs two real concurrent transactions",
        },
        "2": {
            "input": "the same idempotency key with a different body",
            "expected": "IDEMPOTENCY_CONFLICT",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation, no tests, no database; the error code itself is frozen in the contract, so the expectation is well defined once the code exists",
        },
        "coverage": "0 of 2 required test cases",
    },
    "acceptance_recheck_plan": {
        "purpose": "what to verify when P03-04 is re-issued after P02-03 lands and G02 is signed",
        "preconditions": [
            "P02-03 must land first: it owns CommitCommand, ValidationReport, CommitReceipt and CandidatePlan per the contract, and a second same-named definition is forbidden",
            "P03-01, P03-02 and P03-03 accepted first, because the store writes the tables and ORM mappings they create",
            "an isolated PostgreSQL reachable with TEST_DATABASE_URL exported to a *test*-named database",
            "apps/backend/pyproject.toml + uv.lock permitted to gain sqlalchemy/psycopg/alembic (D3)",
        ],
        "checks": [
            "test case 1 with two REAL concurrent transactions: both try to reserve the last dock; assert exactly one commits and the other fails with RESOURCE_CONFLICT (409), and that the loser left no reservation, no version and no audit row behind",
            "test case 2: reuse an idempotency key with a different body and assert IDEMPOTENCY_CONFLICT; then reuse it with the identical body and assert the ORIGINAL receipt is returned unchanged (not a second write)",
            "atomicity: make the commit fail after the version insert and assert no half state survives - no orphan reservation, no schedule version, no outbox row, and active_version_id unchanged",
            "the validation report must be checked against the candidate and snapshot hashes before anything is written; a mismatched report must abort with no side effects",
            "resource rows must be locked in a fixed, documented order: run two commits that touch the same pair in opposite orders and assert no deadlock",
            "active_version_id must be changed by compare-and-set against expected_active_version_id, so a stale expectation yields STALE_SNAPSHOT rather than an overwrite",
            "no HTTP route may be added in this task: the contract makes ScheduleService the only official commit use case and says PlanCommitStore is called by it",
            "the version, reservation, audit and outbox writes must be in ONE transaction, not sequential commits",
            "the DSN used in the run must be postgresql, never sqlite; SQLite cannot demonstrate concurrent-commit semantics",
            "because D5 leaves ORM containment unenforced, hand-check that persistence types do not appear in any application-layer signature",
        ],
    },
    "defects": DEFECTS,
    "fixed_by_zcode": [],
    "unfixed": [d["id"] for d in DEFECTS],
    "not_verified": [
        "Both P03-04 test cases, the PlanCommitStore.commit interface, the CAS/idempotency/atomicity rules and the fixed lock order are UNVERIFIED: nothing was implemented and no database exists",
        "The G03 exit assertions - real migration/rollback/FK, consistent snapshot, exactly-one concurrent commit, no half version - have never been executed by any task in Phase 03",
        "Static type checking: no mypy/pyright configuration exists",
        "npm ci, the frontend workspace test, the Playwright listing and ruff were NOT re-run in this pass; D8/D9/D10 rest on the 2026-09-14 evidence and are flagged reverified_this_pass=false",
        "CI as written cannot run in this checkout (no .git), so its git ls-files / git grep / git diff steps cannot execute as written",
    ],
    "security_review": {
        "scope": "the change set is documentation plus DSH evidence; the eventual deliverable is the highest-stakes storage layer in Phase 03, so forward-looking controls are stated as requirements, not passes",
        "credential_files": "none found (.env / .env.* / *.pem / *.p12 / id_rsa*) in the target tree",
        "secret_literals": "0 hits for sk-[A-Za-z0-9]{20,} and AKIA[0-9A-Z]{16}",
        "test_database_url_handling": "presence checked only; never echoed, no connection attempted",
        "sql_injection": (
            "no database access code exists yet, so there is nothing to verify. This is the task that will write idempotency "
            "records and reservations, so every parameter must be bound, never interpolated or assembled with format/f-string "
            "- a forward-looking requirement, NOT a pass"
        ),
        "idempotency_and_replay": (
            "P03-04 is the project's first anti-replay control: the same idempotency key with the same body must return the "
            "original receipt and must not perform a second write, while a different body must be rejected. That behaviour has "
            "never been executed and is a security-relevant invariant, not just a business rule"
        ),
        "concurrency_safety": (
            "the fixed lock order requirement exists to prevent deadlocks between concurrent commits; nothing has verified it, "
            "and a deadlock-prone implementation would surface only under real concurrency"
        ),
        "command_injection": "no shell=True / os.system / eval / exec / pickle.loads in apps|packages|scripts|tests; runner, conftest and this role's scripts use argv arrays or nothing at all",
        "auth_scope_logging": "no HTTP boundary or worker exists yet; belongs to P05-01/P16-03/P37",
        "dependency_changes": "none in this change set; uv lock --check exit 0",
        "external_targets_scanned": "none - only local tool availability and environment variables were inspected",
        "zcode_own_artifacts": "the evidence builder for this record starts no subprocess and contains no shell invocation",
    },
    "tool_versions": {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "python_pin": read_text(".python-version"),
        "node_pin": read_text(".node-version"),
        "node_local_and_g01_fingerprint": fingerprint.get("node"),
        "uv_recorded_in_g01": fingerprint.get("uv"),
        "os": f"{platform.system()} {platform.release()}",
        "note": "uv/node are quoted from the G01 environment fingerprint because this evidence builder starts no process",
    },
    "verified_input_hashes": {rel: sha(rel) for rel in VERIFIED_INPUTS},
    "evidence_logs": collect_logs(),
    "evidence_builder": {
        "path": "artifacts/handoffs/P03-04/zcode/build-evidence.py",
        "sha256": sha("artifacts/handoffs/P03-04/zcode/build-evidence.py"),
        "note": "this record's own generator; rerun it from the repository root to rebuild evidence.json and precheck.json",
    },
    "sandbox_gate_evidence": collect_sandbox(),
    "files_added_by_zcode": [
        "docs/handoffs/P03-04/zcode.md",
        "artifacts/handoffs/P03-04/zcode/evidence.json",
        "artifacts/handoffs/P03-04/zcode/precheck.json",
        "artifacts/handoffs/P03-04/zcode/build-evidence.py",
        "artifacts/handoffs/P03-04/zcode/logs/ (raw command, contract-check and probe logs)",
        "tmp/zcode-g03-dryrun-p4/ (non-official G03 sandbox evidence, under the gitignored tmp/)",
    ],
    "files_modified_by_zcode": [],
    "preserved_dsh_report": [
        "docs/handoffs/P03-04/dsh.md",
        "artifacts/handoffs/P03-04/dsh/evidence.json",
        "artifacts/handoffs/P03-04/dsh/logs/",
        "docs/implementation/P03-04.md",
        "docs/implementation/reports/P03-04.md",
        "note: none of these was created, rewritten or reformatted by this role; only read and hashed",
    ],
    "signs_gate": False,
    "gate_signed": None,
    "limitations": [
        "This record is BLOCKED on purpose: scripts/gates.py compares status against 'Z_PRECHECK_PASSED' and fails closed. It agrees with DSH's own BLOCKED verdict.",
        "P03-04-cmd2 (check_architecture.py) exit 0 is vacuous and cannot cover this task's containment obligation (D5).",
        "docs/workflow/README.md and HANDOFF_CONTRACT.md do not exist (ARCH-0004); this record follows the user instruction plus the path hardcoded in scripts/gates.py:305-311.",
        "D8/D9/D10 were not re-executed in this pass because no frontend or lint artifact is in P03-04's scope.",
    ],
    "next_actions": [
        "Treat Phase 03 as closed with zero implementation: all four tasks reported BLOCKED and G03 has no path to assembly. Do not re-issue P03-01..P03-04 individually.",
        "ZCode: write the three P01-01..P01-03 precheck records - the entire remaining cause of G01 failing, whose five acceptance assertions already pass.",
        "Codex: record the G01 codex review; decide ARCH-0004 (record format) and D11 (revision policy); consider accepting BLOCKED as a known handoff status (D6).",
        "Project management: authorise the database dependencies into the workspace lock (D3, now confirmed across all four Phase 03 tasks) and write the Phase 01 environment manual (D4).",
        "Role A / DSH: deliver P02-01..P02-04 in order (P02-03 first for the type surface P03 needs), assemble G02, then re-issue P03-01..P03-04 as one chain.",
        "P01-02: close the ORM-containment coverage gap (D5) before any Phase 03 storage task is re-issued.",
    ],
}

out_dir = pathlib.Path("artifacts/handoffs/P03-04/zcode")
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
for name in ("evidence.json", "precheck.json"):
    (out_dir / name).write_text(text, encoding="utf-8")

print("status:", payload["status"])
print("deliverables present:", deliverable_count, "/", len(DELIVERABLES))
print("code+test present   :", code_count, "/", len(CODE_AND_TEST_DELIVERABLES))
print("dependency present  :", dep_count, "/", len(DEPENDENCY_ARTIFACTS))
print("dsh logs match      :", dsh["all_command_log_hashes_match"], "| inputs stale:", dsh["stale_recorded_inputs"] or "none")
print("phase 03 implemented deliverables:", payload["phase_03_closure"]["implemented_deliverables_in_phase_03"],
      "/", payload["phase_03_closure"]["phase_03_code_and_test_expected"])
print("logs recorded:", len(payload["evidence_logs"]))
print("inputs hashed:", len(payload["verified_input_hashes"]), "missing:", [r for r, v in payload["verified_input_hashes"].items() if v is None])
print("bytes:", (out_dir / "evidence.json").stat().st_size)
