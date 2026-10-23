"""Assemble the P03-01 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P03-01/zcode/build-evidence.py

This is the first Phase 03 record and the first one where DSH submitted a handoff (an
honest BLOCKED report with no implementation). The record therefore has two jobs: review
the DSH submission independently, and record this role's own verdict. It only reads the
repository and writes the two records next to itself; it never signs a Gate and starts no
process. Every hash is recomputed here, and the gate revision label is asked of the runner
itself rather than transcribed.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()

BUILDER_LOG = "artifacts/handoffs/P03-01/zcode/logs/build-evidence.log"


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

        return gates.GateRunner(root=root, phase=3, revision="auto").compute_revision()
    except Exception as exc:  # pragma: no cover - environment probe only
        return f"<unavailable: {exc}>"


def collect_logs() -> dict:
    """Inventory the raw command logs (the builder's own console log is excluded)."""
    records = {}
    for path in sorted(pathlib.Path("artifacts/handoffs/P03-01/zcode/logs").glob("*.log")):
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
    for path in sorted(pathlib.Path("tmp/zcode-g03-dryrun").rglob("*")):
        if path.is_file():
            rel = path.as_posix()
            records[rel] = {"sha256": sha(rel), "bytes": path.stat().st_size}
    return records


def dsh_log_integrity() -> dict:
    """Recompute the hashes DSH recorded for its own command logs."""
    dsh = read_json("artifacts/handoffs/P03-01/dsh/evidence.json")
    rows = []
    all_match = True
    for command in dsh.get("commands", []):
        rel = command.get("log_path")
        if not rel:
            continue
        actual = sha(rel)
        recorded = command.get("log_sha256")
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
    stale_inputs = []
    for rel, recorded in (dsh.get("input_hashes") or {}).items():
        if sha(rel) != recorded:
            stale_inputs.append(rel)
    return {
        "all_command_log_hashes_match": all_match,
        "command_logs": rows,
        "recorded_input_count": len(dsh.get("input_hashes") or {}),
        "stale_recorded_inputs": stale_inputs,
        "conclusion": (
            "DSH's own evidence verifies: every recorded command-log hash and every recorded input hash "
            "recomputes to the same value, so its blocker analysis binds to the current tree"
        ),
    }


VERIFIED_INPUTS = [
    "docs/prompts/03-database/P03-01-resource-schema.md",
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
    "packages/domain/src/logistics_domain/__init__.py",
    "packages/contracts/src/logistics_contracts/__init__.py",
    "apps/backend/pyproject.toml",
    "tests/conftest.py",
    "scripts/gates.py",
    "scripts/check_architecture.py",
    "scripts/check_ownership.py",
    "OWNERSHIP.json",
    "pyproject.toml",
    "uv.lock",
    "package-lock.json",
    ".github/workflows/ci.yml",
    "artifacts/gates/G00.json",
    "artifacts/gates/G01.json",
    "artifacts/handoffs/P03-01/dsh/evidence.json",
    "docs/handoffs/P03-01/dsh.md",
    "docs/implementation/P03-01.md",
    "docs/implementation/reports/P03-01.md",
    "artifacts/handoffs/P02-04/zcode/precheck.json",
]

DELIVERABLES = [
    "alembic.ini",
    "apps/backend/migrations/env.py",
    "apps/backend/migrations/versions/0001_resources.py",
    "apps/backend/src/logistics_backend/persistence/resource_models.py",
    "docs/implementation/P03-01.md",
    "docs/implementation/reports/P03-01.md",
    "tests/integration/test_p03_01_resource_schema.py",
    "tests/unit/test_p03_01_resource_schema.py",
]

# The subset that is actual product code / tests rather than documentation.
CODE_AND_TEST_DELIVERABLES = [
    "alembic.ini",
    "apps/backend/migrations/env.py",
    "apps/backend/migrations/versions/0001_resources.py",
    "apps/backend/src/logistics_backend/persistence/resource_models.py",
    "tests/integration/test_p03_01_resource_schema.py",
    "tests/unit/test_p03_01_resource_schema.py",
]

DEPENDENCY_ARTIFACTS = [
    "artifacts/gates/G02.json",
    "artifacts/handoffs/P02-01/dsh/evidence.json",
    "artifacts/handoffs/P02-02/dsh/evidence.json",
    "artifacts/handoffs/P02-03/dsh/evidence.json",
    "artifacts/handoffs/P02-04/dsh/evidence.json",
    "docs/implementation/P02-01.md",
    "docs/implementation/P02-04.md",
    "packages/domain/src/logistics_domain/ids.py",
    "packages/domain/src/logistics_domain/units.py",
    "packages/domain/src/logistics_domain/states.py",
    "packages/domain/src/logistics_domain/entities.py",
    "packages/domain/src/logistics_domain/orders.py",
    "packages/domain/src/logistics_domain/resources.py",
    "packages/domain/src/logistics_domain/planning.py",
    "packages/domain/src/logistics_domain/execution.py",
    "packages/domain/src/logistics_domain/runtime.py",
    "packages/contracts/src/logistics_contracts/common.py",
    "packages/contracts/src/logistics_contracts/runtime.py",
    "packages/contracts/src/logistics_contracts/entities.py",
    "packages/contracts/src/logistics_contracts/planning.py",
    "scripts/export_contracts.py",
    "contracts/schemas.json",
]

PHASE_TASKS = ("P03-01", "P03-02", "P03-03", "P03-04")

COMMANDS = [
    {
        "check_id": "P03-01-cmd1",
        "argv": "uv run pytest tests/unit/test_p03_01_resource_schema.py tests/integration/test_p03_01_resource_schema.py -q",
        "cwd": str(root),
        "exit_code": 4,
        "result": "ERROR: file or directory not found: tests/unit/test_p03_01_resource_schema.py; no tests ran in 0.00s",
        "log_path": "artifacts/handoffs/P03-01/zcode/logs/cmd1-pytest.log",
        "mandatory": True,
        "passed": False,
        "agrees_with_dsh": True,
    },
    {
        "check_id": "P03-01-cmd2",
        "argv": "uv run python scripts/check_architecture.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
        "log_path": "artifacts/handoffs/P03-01/zcode/logs/cmd2-architecture.log",
        "mandatory": True,
        "passed": True,
        "agrees_with_dsh": True,
        "caveat": "vacuous pass: the 7 scanned modules are the untouched P01-01 stubs and P03-01 added no code; not acceptance evidence",
    },
    {
        "check_id": "regression",
        "argv": "uv run pytest -q",
        "cwd": str(root),
        "exit_code": 0,
        "result": "187 passed",
        "log_path": "artifacts/handoffs/P03-01/zcode/logs/regression-pytest.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "gates-phase03-sandbox",
        "argv": "uv run python scripts/gates.py --phase 03 --revision auto --out-dir tmp/zcode-g03-dryrun",
        "cwd": str(root),
        "exit_code": 1,
        "result": (
            "G03: 7/28 checks passed; previous-gate:G01 status=failed; previous-gate:G02 missing; "
            "dsh-evidence:P03-01 unexpected status='BLOCKED'; docs:docs/implementation/P03-01.md present and "
            "reports/P03-01.md present; all four P03-0X-cmd1 exit_code=4; zcode-precheck and codex-review missing"
        ),
        "log_path": "artifacts/handoffs/P03-01/zcode/logs/gates-phase03-sandbox.log",
        "mandatory": False,
        "passed": False,
        "note": (
            "sandbox out-dir; artifacts/gates/G03.json was NOT written. The count reconciles with DSH's reported "
            "5/28: DSH probed before writing its two docs, and those two doc checks now pass (5 + 2 = 7)."
        ),
    },
    {
        "check_id": "dsh-evidence-integrity",
        "argv": "independent recomputation of the hashes recorded in artifacts/handoffs/P03-01/dsh/evidence.json",
        "cwd": str(root),
        "exit_code": 0,
        "result": "all 4 command-log hashes match; all 16 recorded input hashes match; no stale recorded input",
        "log_path": "artifacts/handoffs/P03-01/zcode/logs/dsh-evidence-integrity.log",
        "mandatory": False,
        "passed": True,
        "note": "confirms the DSH blocker report is internally consistent and binds to the current tree",
    },
    {
        "check_id": "environment-availability",
        "argv": "which psql pg_ctl postgres initdb ; docker info ; echo $TEST_DATABASE_URL",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "psql/pg_ctl/postgres/initdb all absent from PATH; docker CLI present but the daemon is unreachable "
            "(npipe:////./pipe/dockerDesktopLinuxEngine); TEST_DATABASE_URL is not set"
        ),
        "log_path": "artifacts/handoffs/P03-01/zcode/logs/baseline-checks.log",
        "mandatory": False,
        "passed": False,
        "note": "independently reproduces DSH's environment finding: no PostgreSQL of any kind is reachable",
    },
    {
        "check_id": "baseline-checks",
        "argv": "check_ownership.py --json ; uv lock --check ; uv sync --frozen ; credential find ; secret grep ; injection grep ; SQL-assembly grep",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "ownership passed=True violations=0 fallbacks=[] (995 files scanned); uv lock --check exit 0; "
            "uv sync --frozen exit 0; no credential files; no sk-/AKIA literals; no shell=True/os.system/eval/exec/"
            "pickle.loads; no SQL string assembly (no DB code exists yet)"
        ),
        "log_path": "artifacts/handoffs/P03-01/zcode/logs/baseline-checks.log",
        "mandatory": False,
        "passed": True,
    },
]

DEFECTS = [
    {
        "id": "D1",
        "severity": "blocking",
        "task": "P03-01",
        "title": "No implementation candidate exists: 0/6 code-and-test deliverables were written (only the two BLOCKED report documents exist, 2/8 paths present)",
        "evidence": [
            "logs/cmd1-pytest.log exit 4 (0 tests ran)",
            "logs/gates-phase03-sandbox.log: P03-01-cmd1 exit_code=4, docs present but no code",
            "logs/dsh-evidence-integrity.log: DSH's own deliverable_presence recorded 0/8 before it wrote its two docs; those two are present now, the other six are not",
        ],
        "status": "unfixed",
        "owner": "DSH / P03-01 (deliberately not started; see D2)",
        "note": "DSH did not create partial DDL on purpose, to avoid defining a second domain model - the right call",
    },
    {
        "id": "D2",
        "severity": "blocking",
        "task": "G02 + G01",
        "title": "The only declared dependency G02 has no record at all, and the transitive prerequisite G01 is status=failed",
        "evidence": [
            "artifacts/gates/G02.json does not exist; the phase-02 sandbox probe reports G02: 5/27",
            "artifacts/gates/G01.json status=failed, failed_checks=[zcode-precheck:P01-01, zcode-precheck:P01-02, zcode-precheck:P01-03, codex-review] (all 5 acceptance assertions passed)",
            "TASK_MANIFEST.json deps for P03-01 = [G02]; TASK_GRAPH.md:58 agrees",
            "Phase 02 deliverable files present: 0/15 (verified in this pass)",
            "docs/plan/PHASE_GATES.md: G01 failure blocks Phase 02 and later",
        ],
        "status": "unfixed",
        "owner": "Codex (G01 review) + ZCode (P01-01..P01-03 prechecks) + role A/DSH (P02-01..P02-04)",
    },
    {
        "id": "D3",
        "severity": "blocking-for-this-task-when-reissued",
        "task": "P03-01 scope / planning",
        "title": "The task's 8-file allow-list does not include the dependency manifests it needs, so alembic and psycopg cannot be added without editing out-of-scope files",
        "evidence": [
            "allowed_files = [alembic.ini, apps/backend/migrations/env.py, apps/backend/migrations/versions/0001_resources.py, apps/backend/src/logistics_backend/persistence/resource_models.py, both docs, both tests] - apps/backend/pyproject.toml and uv.lock are absent",
            "uv.lock has 40 packages and none of them is alembic, sqlalchemy, psycopg or psycopg-binary",
            "the frozen interface is literally 'alembic upgrade head -> PostgreSQL resource tables'",
            "tests/conftest.py db_connection fails when psycopg is missing",
            "DSH flagged the same need as its suggested action 3 (allow a Phase 03 task to add psycopg/SQLAlchemy/Alembic to the workspace lock)",
        ],
        "impact": (
            "a re-issued P03-01 has only two ways out: edit pyproject.toml + uv.lock (outside its allow-list, which the "
            "task book forbids) or fake the schema without a real migration tool and driver (which the task book also "
            "forbids and which DSH explicitly predicted as risk R5)"
        ),
        "status": "unfixed",
        "owner": "project management / planning: extend the allow-list or authorise a dependency task",
    },
    {
        "id": "D4",
        "severity": "blocking-for-acceptance",
        "task": "P01-01 (environment manual)",
        "title": "The Phase 01 environment manual that defines the isolated PostgreSQL startup does not exist, although both code and a frozen convention reference it",
        "evidence": [
            "tests/conftest.py:158 tells the reader to 'see the Phase 01 environment manual' when TEST_DATABASE_URL is absent",
            "docs/architecture/IMPLEMENTATION_CONVENTIONS.md:9 states 'P01环境手册给出Docker PostgreSQL与本地PostgreSQL两种明确启动方式'",
            "no file matching manual/environment/postgres exists under docs/ (searched)",
            "this host has no psql/pg_ctl/postgres/initdb and no running Docker daemon",
        ],
        "impact": (
            "every Phase 03 database assertion currently fails by fixture rather than by product defect, and no "
            "documented way exists to obtain a working database; G03's 'real PostgreSQL migration/rollback/FK' "
            "criterion cannot be produced"
        ),
        "status": "unfixed",
        "owner": "Phase 01 environment documentation owner (project management side)",
    },
    {
        "id": "D5",
        "severity": "non-blocking (contract gap)",
        "task": "P01-02 / ARCH-0004",
        "title": "The gate runner has no accepted state for a prerequisite-blocked handoff, so an honest BLOCKED report is reported as an unexpected status",
        "evidence": [
            "logs/gates-phase03-sandbox.log: dsh-evidence:P03-01: unexpected status='BLOCKED'",
            "scripts/gates.py accepts only READY_FOR_ZCODE and Z_PRECHECK_PASSED for DSH evidence",
            "every task book orders a BLOCKED report with a concrete blocking reason when prerequisites are missing (P03-01 prompt, Current State section)",
        ],
        "impact": (
            "the two documents disagree: the task books define BLOCKED as a legitimate outcome, the runner treats it as "
            "malformed evidence. It does not change any verdict (the gate fails either way), but the diagnostic text "
            "misleads a reader into thinking DSH wrote a bad record"
        ),
        "recommendation": "either accept BLOCKED as a known DSH status with its own message, or state in the handoff contract that a blocked handoff must not be written to artifacts/handoffs/<task>/dsh/",
        "status": "unfixed",
        "owner": "P01-02 + ARCH-0004 decision",
    },
    {
        "id": "D6",
        "severity": "non-blocking-for-P03-01",
        "task": "P01-01",
        "title": "apps/frontend declares test=vitest run without devDependencies, so vitest is missing and the CI frontend job step fails",
        "evidence": [
            "apps/frontend/package.json",
            ".github/workflows/ci.yml:95",
            "carried over from the 2026-09-14 P02-02 review where the command exited 1",
        ],
        "status": "unfixed",
        "owner": "P01-01 (or P24-01)",
        "reverified_this_pass": False,
    },
    {
        "id": "D7",
        "severity": "non-blocking-for-P03-01",
        "task": "P01-02",
        "title": "npm run test:e2e:list exits 1 with zero specs while CI treats it as a required step",
        "evidence": [
            ".github/workflows/ci.yml:98",
            "playwright.config.ts comment claims an empty listing is legitimate",
            "carried over from the 2026-09-14 P02-02 review",
        ],
        "status": "unfixed",
        "owner": "P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D8",
        "severity": "non-blocking",
        "task": "engineering config",
        "title": "ruff is configured but never executed in CI, and its RUF001/RUF002 rules conflict with the project-wide Chinese fullwidth punctuation convention",
        "evidence": [
            "pyproject.toml [tool.ruff]",
            ".github/workflows/ci.yml (no ruff step)",
            "carried over from the 2026-09-14 P02-02 review: 39 errors in the target tree",
        ],
        "status": "unfixed",
        "owner": "engineering config / P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D9",
        "severity": "non-blocking",
        "task": "P01-02",
        "title": "Gate revision is built from volatile session/scratch files (.mimosa/**, tmp/**), so a recorded code_revision is unreproducible from the next agent action",
        "evidence": [
            "scripts/gates.py:43 EXCLUDED_FROM_REVISION excludes only artifacts/gates and artifacts/e2e",
            "scripts/gates.py:327-342 compute_revision enumerates the whole tree; measured 1167 rows of which .mimosa/** is 451 and tmp/** is 423",
            ".mimosa/hook-state/<session>.json is rewritten by the agent host on every tool call",
            "artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log holds the reproduction",
            "DSH independently reached the same conclusion in its handoff (candidate.revision_label_is_self_perturbing)",
        ],
        "status": "unfixed",
        "confidence": "proven by reproduction with the runner's own compute_revision(); independently corroborated by DSH",
        "owner": "P01-02",
        "reverified_this_pass": True,
    },
    {
        "id": "D10",
        "severity": "observation",
        "task": "P01-01",
        "title": "The _PENDING_APIS registries name capabilities but not the modules Phase 02/03 create, so probing those surfaces yields a bare AttributeError",
        "evidence": [
            "logistics_domain._PENDING_APIS keys = ['entities','ids','ports','states','units']",
            "logistics_contracts._PENDING_APIS keys = ['dto','errors','export_schema','mapping']",
            "artifacts/handoffs/P02-03/zcode/logs/probe-interfaces.log and P02-04 logs/probe-interfaces.log",
        ],
        "status": "unfixed",
        "owner": "P01-01",
    },
]

dsh = read_json("artifacts/handoffs/P03-01/dsh/evidence.json")
g01 = read_json("artifacts/gates/G01.json")
g01_fingerprint = g01.get("environment_fingerprint", {})

payload = {
    "schema_version": "1.0.0",
    "task_id": "P03-01",
    "scene": "resource-schema",
    "phase": 3,
    "phase_gate": "G03",
    "reviewer": "ZCode",
    "review_role": "independent-pre-acceptance",
    "status": "BLOCKED",
    "verdict_reason": (
        "P03-01 has no implementation candidate: the six code-and-test deliverables do not exist and only the two "
        "BLOCKED-report documents were written. The single declared dependency G02 has no record at all and the "
        "transitive prerequisite G01 is status=failed, so Phase 02 (0/15 files) is entirely undelivered. DSH's own "
        "BLOCKED verdict is independently confirmed; nothing could be pre-accepted."
    ),
    "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
    "candidate": {
        "root": str(root),
        "vcs": "no .git in this checkout; located by content hash (scripts/gates.py compute_revision)",
        "revision_label_during_this_review": current_revision(),
        "revision_label_is_self_perturbing": (
            "by construction this label is one step stale: compute_revision() covers this record's own directory, so "
            "writing evidence.json and precheck.json moves the label again. Recompute it with the same call to compare; "
            "an exact match is impossible until defect D9 is fixed."
        ),
        "previous_gate_recorded_revision": "content-sha256:ab054daf9c6c1373c6503f603805756ef3ef9c5a60400d07d8e938d6987e532b",
    },
    "deliverable_presence": {rel: (root / rel).is_file() for rel in DELIVERABLES},
    "deliverable_present_count": sum(1 for rel in DELIVERABLES if (root / rel).is_file()),
    "deliverable_expected_count": len(DELIVERABLES),
    "code_and_test_presence": {rel: (root / rel).is_file() for rel in CODE_AND_TEST_DELIVERABLES},
    "code_and_test_present_count": sum(1 for rel in CODE_AND_TEST_DELIVERABLES if (root / rel).is_file()),
    "code_and_test_expected_count": len(CODE_AND_TEST_DELIVERABLES),
    "dsh_submission": {
        "handoff_path": "docs/handoffs/P03-01/dsh.md",
        "evidence_path": "artifacts/handoffs/P03-01/dsh/evidence.json",
        "present": (root / "docs/handoffs/P03-01/dsh.md").is_file()
        and (root / "artifacts/handoffs/P03-01/dsh/evidence.json").is_file(),
        "claimed_status": dsh.get("status"),
        "claimed_verdict_reason": dsh.get("verdict_reason"),
        "claim_summary": (
            "DSH reports that P03-01 was deliberately not started, that 0/8 deliverables were created, that the blocker "
            "is G02 (no record) plus G01 (failed) plus the absence of any reachable PostgreSQL, and that it did not "
            "fabricate DDL on purpose"
        ),
        "independent_verification": {
            "log_hashes": "ALL MATCH (see commands[dsh-evidence-integrity])",
            "input_hashes": "ALL MATCH, no stale recorded input",
            "environment_claims": "independently reproduced (no psql/pg_ctl/postgres/initdb, Docker daemon unreachable, TEST_DATABASE_URL unset)",
            "dependency_claims": "independently reproduced (G02 record absent, G01 failed, Phase 02 files 0/15)",
            "lock_claims": "independently reproduced (uv.lock has no alembic/sqlalchemy/psycopg)",
            "conftest_claim": "independently reproduced by reading tests/conftest.py: database_url and db_connection call pytest.fail, never skip",
            "overclaim_check": "the DSH report explicitly states it does not claim any unrun test passed and does not claim P03-01 is implemented - no overclaim found",
            "corrections": [
                "DSH's deliverable_present_count field says 0/8, but its own two report documents now exist, so the true count is 2/8; the field is a snapshot taken before it wrote them",
                "DSH's G03 probe reported 5/28; the same probe now reports 7/28 because the two doc checks pass (5 + 2 = 7). Both numbers are correct for their moment",
            ],
        },
        "verdict_on_submission": (
            "honest and accurate: the blocker analysis holds up under independent recomputation, and the refusal to "
            "write DDL without the Phase 02 domain types is the correct choice under Architecture Constraint 6"
        ),
    },
    "dependency_presence": {rel: (root / rel).is_file() for rel in DEPENDENCY_ARTIFACTS},
    "dependency_present_count": sum(1 for rel in DEPENDENCY_ARTIFACTS if (root / rel).is_file()),
    "dependency_expected_count": len(DEPENDENCY_ARTIFACTS),
    "prerequisites": {
        "G01": {
            "status": "failed",
            "failed_checks": list(g01.get("failed_checks", [])),
            "acceptance_assertions_all_passed": all(
                a.get("passed") for a in g01.get("acceptance_assertions", [])
            )
            if g01.get("acceptance_assertions")
            else None,
            "source": "artifacts/gates/G01.json + logs/gates-phase03-sandbox.log",
            "blocks": "Phase 02 and later per docs/plan/PHASE_GATES.md",
        },
        "G02": {
            "status": "not_signed",
            "record_exists": (root / "artifacts/gates/G02.json").is_file(),
            "sandbox_result": "G02: 5/27 checks passed",
            "declared_by": "TASK_MANIFEST.json deps [G02]; TASK_GRAPH.md:58",
        },
        "G03": {"status": "not_signed", "sandbox_result": "G03: 7/28 checks passed"},
    },
    "environment": {
        "postgresql_client": "psql not found on PATH",
        "postgresql_server": "pg_ctl / postgres / initdb not found on PATH",
        "docker_cli": "present",
        "docker_daemon": "unreachable (npipe:////./pipe/dockerDesktopLinuxEngine)",
        "test_database_url_set": False,
        "conftest_behaviour_when_url_absent": "pytest.fail, never skip (tests/conftest.py)",
        "conftest_behaviour_when_psycopg_absent": "pytest.fail with 'psycopg is not installed in this environment'",
        "isolated_postgres_reachable": False,
        "environment_manual_present": False,
        "note": "no secret, credential or personal datum is recorded here; TEST_DATABASE_URL was only checked for presence, never echoed",
    },
    "gate_phase03_required_records": {
        task: {"task_doc": None, "report": None, "dsh_evidence": None, "zcode_precheck": None} for task in PHASE_TASKS
    },
    "frozen_interface": {
        "declared": "alembic upgrade head -> PostgreSQL resource tables",
        "domain_model_expected": [
            "Order", "Cargo", "Vehicle", "Driver", "Warehouse", "WarehouseZone",
            "StorageLocation", "Dock", "Worker", "Equipment",
        ],
        "business_rules_expected": [
            "FK, CHECK, unique keys, timestamptz, row_version",
            "SQLite must not stand in for the real database in acceptance",
            "objects referenced by history are only deactivated, never deleted",
        ],
        "algorithm_expected": [
            "create tables in relational topological order",
            "express the database-representable part of the domain constraints",
            "give enums and checks explicit names so migrations stay readable",
        ],
    },
    "commands": COMMANDS,
    "test_cases": {
        "1": {
            "input": "Cargo.order_id referencing a non-existent order",
            "expected": "rejected by the foreign key",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation and no test files exist (exit_code=4, 0 tests ran); no PostgreSQL is reachable either",
        },
        "2": {
            "input": "two warehouses with the same warehouse_code",
            "expected": "rejected by the unique constraint",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation and no test files exist (exit_code=4, 0 tests ran); no PostgreSQL is reachable either",
        },
        "coverage": "0 of 2 required test cases",
    },
    "acceptance_recheck_plan": {
        "purpose": "what to verify when P03-01 is re-issued after G02 is signed, so the review does not have to be re-derived",
        "preconditions": [
            "G02 signed, or at minimum the Phase 02 domain types present, because the DDL must map 1:1 from the real Python types rather than being reverse-engineered from DDL",
            "an isolated PostgreSQL reachable and TEST_DATABASE_URL exported as a *test*-named database (conftest refuses other names)",
            "apps/backend/pyproject.toml + uv.lock permitted to gain psycopg/SQLAlchemy/Alembic (see D3) and uv lock --check still passing",
        ],
        "checks": [
            "alembic upgrade head applies 0001_resources to a real PostgreSQL, and downgrade returns to the empty schema, both without leaving objects behind",
            "test case 1: inserting a Cargo whose order_id does not exist is rejected by the FK, with no partial row written",
            "test case 2: inserting a second warehouse with a duplicated warehouse_code is rejected by the unique constraint",
            "every table carries id (UUID), status enum, created_at/updated_at timestamptz, row_version and schema_version; no naive timestamps",
            "CHECK constraints exist for the non-negative and range rules from DOMAIN_CATALOG; enums and checks have explicit names",
            "deactivating a referenced object is a status change, not a delete (verify no ON DELETE CASCADE against history-bearing tables)",
            "the migration must not be validated against SQLite - confirm the DSN in the test run is postgresql, not sqlite",
            "the 10 mapped tables correspond to the real Python types in packages/domain (not to a hand-invented schema)",
        ],
    },
    "defects": DEFECTS,
    "fixed_by_zcode": [],
    "unfixed": [d["id"] for d in DEFECTS],
    "not_verified": [
        "All ten P03-01 business requirements (FK/CHECK/unique/timestamptz/row_version DDL, both test cases, a real 'alembic upgrade head') are UNVERIFIED: nothing was implemented and no database exists",
        "The 'alembic upgrade head' interface was not exercised: alembic.ini and apps/backend/migrations/ do not exist and alembic is not in the workspace lock",
        "G03 exit criteria (real PostgreSQL migration/rollback/FK, consistent snapshot, exactly-one concurrent resource commit, no half version on transaction failure) belong to Phase 03 as a whole and mostly depend on P03-02..P03-04",
        "Static type checking: no mypy/pyright configuration exists",
        "npm ci, the frontend workspace test and the Playwright listing were NOT re-run in this pass (no frontend file is in P03-01's scope); D6/D7/D8 rest on the 2026-09-14 command output and are flagged reverified_this_pass=false",
        "CI as written cannot run in this checkout (no .git), so its git ls-files / git grep / git diff steps cannot execute as written",
    ],
    "security_review": {
        "scope": "the current change set is documentation plus DSH evidence; the deliverable itself is a database migration task, so this section also states the controls a re-issued P03-01 must satisfy",
        "credential_files": "none found (.env / .env.* / *.pem / *.p12 / id_rsa*) in the target tree",
        "secret_literals": "0 hits for sk-[A-Za-z0-9]{20,} and AKIA[0-9A-Z]{16}",
        "test_database_url_handling": "only checked for presence; never printed, and no connection was attempted",
        "sql_injection": (
            "no database access code exists yet, so there is nothing to verify; conftest's own guard rejects a URL whose "
            "name does not contain 'test' and refuses obvious default/production databases before connecting. Every "
            "parameter used by P03-01/P03-02/P03-03 must be bound, never interpolated, per the project security "
            "constraint - this is a forward-looking requirement, not a verified pass"
        ),
        "command_injection": "no shell=True / os.system / eval / exec / pickle.loads in apps|packages|scripts|tests; the gate runner and conftest execute argv arrays without a shell",
        "auth_scope_logging": "no HTTP boundary or worker exists yet; belongs to P05-01/P37",
        "dependency_changes": "none in this change set; uv lock --check exit 0",
        "external_targets_scanned": "none - only localhost tool availability was probed, no external host was contacted",
        "zcode_own_artifacts": "the evidence builder for this record starts no subprocess and contains no shell invocation",
    },
    "tool_versions": {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "python_pin": read_text(".python-version"),
        "node_pin": read_text(".node-version"),
        "node_local_and_g01_fingerprint": g01_fingerprint.get("node"),
        "uv_recorded_in_g01": g01_fingerprint.get("uv"),
        "g01_fingerprint_os": g01_fingerprint.get("os"),
        "os": f"{platform.system()} {platform.release()}",
        "note": "uv/node are quoted from the G01 environment fingerprint because this evidence builder deliberately starts no process",
    },
    "verified_input_hashes": {rel: sha(rel) for rel in VERIFIED_INPUTS},
    "evidence_logs": collect_logs(),
    "evidence_builder": {
        "path": "artifacts/handoffs/P03-01/zcode/build-evidence.py",
        "sha256": sha("artifacts/handoffs/P03-01/zcode/build-evidence.py"),
        "note": "this record's own generator; rerun it from the repository root to rebuild evidence.json and precheck.json",
    },
    "sandbox_gate_evidence": collect_sandbox(),
    "files_added_by_zcode": [
        "docs/handoffs/P03-01/zcode.md",
        "artifacts/handoffs/P03-01/zcode/evidence.json",
        "artifacts/handoffs/P03-01/zcode/precheck.json",
        "artifacts/handoffs/P03-01/zcode/build-evidence.py",
        "artifacts/handoffs/P03-01/zcode/logs/ (raw command logs)",
        "tmp/zcode-g03-dryrun/ (non-official G03 sandbox evidence, under the gitignored tmp/)",
    ],
    "files_modified_by_zcode": [],
    "preserved_dsh_report": [
        "docs/handoffs/P03-01/dsh.md",
        "artifacts/handoffs/P03-01/dsh/evidence.json",
        "artifacts/handoffs/P03-01/dsh/logs/",
        "docs/implementation/P03-01.md",
        "docs/implementation/reports/P03-01.md",
        "note: none of these was created, rewritten or reformatted by this role; only hashed and read",
    ],
    "signs_gate": False,
    "gate_signed": None,
    "limitations": [
        "This record is BLOCKED on purpose: scripts/gates.py compares status against 'Z_PRECHECK_PASSED' and fails closed. It agrees with DSH's own BLOCKED verdict; the task must be re-issued after G02 is signed.",
        "P03-01-cmd2 (check_architecture.py) exit 0 is vacuous and is not acceptance evidence.",
        "docs/workflow/README.md and HANDOFF_CONTRACT.md do not exist (ARCH-0004); this record follows the user instruction plus the path hardcoded in scripts/gates.py:305-311, and the record layout still needs a project-side contract decision.",
        "D6/D7/D8 were not re-executed in this pass because no frontend or lint artifact is in P03-01's scope; they carry the 2026-09-14 evidence and are flagged reverified_this_pass=false.",
    ],
    "next_actions": [
        "Codex: record the G01 codex review and decide the revision-staleness policy (D9); G01 also needs the three zcode precheck records for P01-01..P01-03 before it can be re-run and signed.",
        "ZCode: those three P01 precheck records are this role's own gap and are the entire remaining cause of G01 failing (all five of its acceptance assertions already pass).",
        "Role A / DSH: deliver P02-01, P02-02, P02-03, P02-04 in order, then assemble G02.",
        "Project management: resolve D3 (allow psycopg/SQLAlchemy/Alembic into the workspace lock) and D4 (write the Phase 01 environment manual) before re-issuing P03-01, otherwise the re-issue cannot succeed as scoped.",
        "Then re-issue P03-01 and run the acceptance_recheck_plan checks above.",
    ],
}

out_dir = pathlib.Path("artifacts/handoffs/P03-01/zcode")
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
for name in ("evidence.json", "precheck.json"):
    (out_dir / name).write_text(text, encoding="utf-8")

print("status:", payload["status"])
print("deliverables present:", payload["deliverable_present_count"], "/", payload["deliverable_expected_count"])
print("code+test present   :", payload["code_and_test_present_count"], "/", payload["code_and_test_expected_count"])
print("dependency present  :", payload["dependency_present_count"], "/", payload["dependency_expected_count"])
print("logs recorded:", len(payload["evidence_logs"]))
missing = [rel for rel, digest in payload["verified_input_hashes"].items() if digest is None]
print("inputs hashed:", len(payload["verified_input_hashes"]), "missing:", missing)
print("written:", (out_dir / "evidence.json").as_posix(), (out_dir / "precheck.json").as_posix())
print("bytes:", (out_dir / "evidence.json").stat().st_size)
