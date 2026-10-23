"""Assemble the P03-02 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P03-02/zcode/build-evidence.py

DSH submitted an honest BLOCKED handoff with no implementation, so this record reviews
that submission independently and then states this role's own verdict. It only reads the
repository and writes the two records next to itself; it never signs a Gate and starts no
process. The gate revision label is asked of the runner itself, never transcribed.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()

BUILDER_LOG = "artifacts/handoffs/P03-02/zcode/logs/build-evidence.log"


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
    """Inventory the raw command logs (this script's own console log is excluded)."""
    records = {}
    for path in sorted(pathlib.Path("artifacts/handoffs/P03-02/zcode/logs").glob("*.log")):
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
    for path in sorted(pathlib.Path("tmp/zcode-g03-dryrun-p2").rglob("*")):
        if path.is_file():
            out[path.as_posix()] = {"sha256": sha(path.as_posix()), "bytes": path.stat().st_size}
    return out


def presence(paths: list[str]) -> tuple[dict, int]:
    table = {rel: (root / rel).is_file() for rel in paths}
    return table, sum(1 for present in table.values() if present)


def dsh_review() -> dict:
    """Recompute everything the DSH handoff asserts about itself."""
    d = read_json("artifacts/handoffs/P03-02/dsh/evidence.json")
    log_rows, logs_ok = [], True
    for command in d.get("commands", []):
        rel = command.get("log_path")
        if not rel:
            continue
        actual, recorded = sha(rel), command.get("log_sha256")
        match = actual is not None and actual == recorded
        logs_ok = logs_ok and match
        log_rows.append(
            {
                "check_id": command.get("check_id"),
                "exit_code": command.get("exit_code"),
                "recorded_log_sha256": recorded,
                "actual_log_sha256": actual,
                "match": match,
            }
        )
    recorded_inputs = d.get("input_hashes") or {}
    stale = [rel for rel, digest in recorded_inputs.items() if sha(rel) != digest]
    recorded_presence = d.get("deliverable_presence") or {}
    drifted = {
        rel: {"recorded": was, "now": (root / rel).is_file()}
        for rel, was in recorded_presence.items()
        if was != (root / rel).is_file()
    }
    zcode_p0301 = read_json("artifacts/handoffs/P03-01/zcode/precheck.json")
    return {
        "present": (root / "docs/handoffs/P03-02/dsh.md").is_file()
        and (root / "artifacts/handoffs/P03-02/dsh/evidence.json").is_file(),
        "claimed_status": d.get("status"),
        "signs_gate": d.get("signs_gate"),
        "gate_signed": d.get("gate_signed"),
        "log_rows": log_rows,
        "all_command_log_hashes_match": logs_ok,
        "recorded_input_count": len(recorded_inputs),
        "stale_recorded_inputs": stale,
        "deliverable_presence_snapshot_drift": drifted,
        "snapshot_corrections": [
            f"{rel}: recorded {was} but now {now} - the record's presence check ran before DSH wrote its own report documents"
            for rel, (was, now) in ((r, (v["recorded"], v["now"])) for r, v in drifted.items())
        ],
        "quotes_previous_zcode_verdict_correctly": (
            zcode_p0301.get("status") == "BLOCKED" and zcode_p0301.get("code_and_test_present_count") == 0
        ),
        "environment_claims_reproduced": "no psql/pg_ctl, TEST_DATABASE_URL unset, uv.lock holds no alembic/sqlalchemy/psycopg - verified in this pass",
        "dependency_claims_reproduced": "G02 record absent, G01 status=failed, P03-01 BLOCKED with 0/6 code deliverables, Phase 02 files 0/15 - verified in this pass",
        "overclaim_check": (
            "the DSH report states explicitly that it claims no unrun test passed and that P03-02 is not implemented; "
            "no overclaim found"
        ),
        "verdict_on_submission": (
            "honest and accurate. Its strongest argument is structural and I confirmed it: 0002_planning_runtime.py is the "
            "second link of one Alembic chain whose 0001_resources.py, env.py and alembic.ini do not exist, so writing 0002 "
            "alone would leave down_revision dangling; and Test Case 2's FK target (the orders table) is created by 0001. "
            "P03-02 therefore cannot be implemented or accepted independently of P03-01."
        ),
    }


DELIVERABLES = [
    "apps/backend/migrations/versions/0002_planning_runtime.py",
    "apps/backend/src/logistics_backend/persistence/planning_models.py",
    "apps/backend/src/logistics_backend/persistence/runtime_models.py",
    "docs/implementation/P03-02.md",
    "docs/implementation/reports/P03-02.md",
    "tests/integration/test_p03_02_planning_schema.py",
    "tests/unit/test_p03_02_planning_schema.py",
]

CODE_AND_TEST_DELIVERABLES = [
    "apps/backend/migrations/versions/0002_planning_runtime.py",
    "apps/backend/src/logistics_backend/persistence/planning_models.py",
    "apps/backend/src/logistics_backend/persistence/runtime_models.py",
    "tests/integration/test_p03_02_planning_schema.py",
    "tests/unit/test_p03_02_planning_schema.py",
]

DEPENDENCY_ARTIFACTS = [
    "artifacts/gates/G02.json",
    "artifacts/handoffs/P03-01/dsh/evidence.json",
    "alembic.ini",
    "apps/backend/migrations/env.py",
    "apps/backend/migrations/versions/0001_resources.py",
    "apps/backend/src/logistics_backend/persistence/resource_models.py",
    "tests/unit/test_p03_01_resource_schema.py",
    "packages/domain/src/logistics_domain/planning.py",
    "packages/domain/src/logistics_domain/runtime.py",
    "packages/domain/src/logistics_domain/entities.py",
    "packages/domain/src/logistics_domain/orders.py",
    "packages/domain/src/logistics_domain/resources.py",
    "packages/domain/src/logistics_domain/ids.py",
    "packages/domain/src/logistics_domain/units.py",
    "packages/domain/src/logistics_domain/states.py",
    "packages/contracts/src/logistics_contracts/planning.py",
    "packages/contracts/src/logistics_contracts/runtime.py",
    "scripts/export_contracts.py",
    "contracts/schemas.json",
]

VERIFIED_INPUTS = [
    "docs/prompts/03-database/P03-02-planning-schema.md",
    "docs/prompts/03-database/P03-01-resource-schema.md",
    "TASK_GRAPH.md",
    "docs/plan/TASK_MANIFEST.json",
    "docs/plan/PHASE_GATES.md",
    "docs/architecture/DOMAIN_CATALOG.md",
    "docs/architecture/DATA_CONTRACTS.md",
    "docs/architecture/IMPLEMENTATION_CONVENTIONS.md",
    "docs/architecture/issues/README.md",
    "docs/api/API_CONTRACT.md",
    "packages/domain/src/logistics_domain/__init__.py",
    "packages/contracts/src/logistics_contracts/__init__.py",
    "apps/backend/pyproject.toml",
    "tests/conftest.py",
    "scripts/gates.py",
    "scripts/check_architecture.py",
    "pyproject.toml",
    "uv.lock",
    ".github/workflows/ci.yml",
    "artifacts/gates/G00.json",
    "artifacts/gates/G01.json",
    "artifacts/handoffs/P03-01/dsh/evidence.json",
    "artifacts/handoffs/P03-01/zcode/precheck.json",
    "artifacts/handoffs/P03-02/dsh/evidence.json",
    "docs/handoffs/P03-02/dsh.md",
    "docs/implementation/P03-02.md",
    "docs/implementation/reports/P03-02.md",
]

PHASE_TASKS = ("P03-01", "P03-02", "P03-03", "P03-04")

COMMANDS = [
    {
        "check_id": "P03-02-cmd1",
        "argv": "uv run pytest tests/unit/test_p03_02_planning_schema.py tests/integration/test_p03_02_planning_schema.py -q",
        "cwd": str(root),
        "exit_code": 4,
        "result": "ERROR: file or directory not found: tests/unit/test_p03_02_planning_schema.py; no tests ran in 0.00s",
        "log_path": "artifacts/handoffs/P03-02/zcode/logs/cmd1-pytest.log",
        "mandatory": True,
        "passed": False,
        "agrees_with_dsh": True,
    },
    {
        "check_id": "P03-02-cmd2",
        "argv": "uv run python scripts/check_architecture.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
        "log_path": "artifacts/handoffs/P03-02/zcode/logs/cmd2-architecture.log",
        "mandatory": True,
        "passed": True,
        "agrees_with_dsh": True,
        "caveat": "vacuous pass: the 7 scanned modules are the untouched P01-01 stubs and P03-02 added no code; not acceptance evidence",
    },
    {
        "check_id": "regression",
        "argv": "uv run pytest -q",
        "cwd": str(root),
        "exit_code": 0,
        "result": "187 passed",
        "log_path": "artifacts/handoffs/P03-02/zcode/logs/regression-pytest.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "gates-phase03-sandbox",
        "argv": "uv run python scripts/gates.py --phase 03 --revision auto --out-dir tmp/zcode-g03-dryrun-p2",
        "cwd": str(root),
        "exit_code": 1,
        "result": (
            "G03: 9/28 checks passed; previous-gate:G01 status=failed; previous-gate:G02 missing; "
            "dsh-evidence:P03-01 and P03-02 both 'unexpected status=BLOCKED'; zcode-precheck:P03-01 BLOCKED and "
            "P03-02 missing; all four P03-0X-cmd1 exit_code=4; codex-review missing"
        ),
        "log_path": "artifacts/handoffs/P03-02/zcode/logs/gates-phase03-sandbox.log",
        "mandatory": False,
        "passed": False,
        "note": (
            "sandbox out-dir; artifacts/gates/G03.json was NOT written. Reconciles with DSH's reported 7/28: DSH probed "
            "before writing its two docs, and those two doc checks now pass (7 + 2 = 9)."
        ),
    },
    {
        "check_id": "dsh-evidence-integrity",
        "argv": "independent recomputation of the hashes recorded in artifacts/handoffs/P03-02/dsh/evidence.json",
        "cwd": str(root),
        "exit_code": 0,
        "result": "all 4 command-log hashes match; all 15 recorded input hashes match; no stale recorded input",
        "log_path": "artifacts/handoffs/P03-02/zcode/logs/dsh-evidence-integrity.log",
        "mandatory": False,
        "passed": True,
        "note": "DSH's blocker report is internally consistent and binds to the current tree; it also quotes the P03-01 ZCode verdict correctly",
    },
    {
        "check_id": "alembic-chain-integrity",
        "argv": "presence check for alembic.ini, migrations/env.py and migrations/versions/0001_resources.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "alembic.ini, env.py and 0001_resources.py all MISSING; the apps/backend/migrations directory does not exist at all",
        "log_path": "artifacts/handoffs/P03-02/zcode/logs/dsh-evidence-integrity.log",
        "mandatory": False,
        "passed": False,
        "note": "confirms DSH's structural argument: 0002 would be a dangling second link, and Test Case 2's FK target (orders) is created by 0001",
    },
    {
        "check_id": "environment-and-baseline",
        "argv": "which psql pg_ctl ; uv lock --check ; check_ownership.py --json ; credential find ; secret grep ; injection grep ; SQL-assembly grep",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "psql/pg_ctl absent; TEST_DATABASE_URL unset; uv.lock 40 packages with NO alembic/sqlalchemy/psycopg; "
            "ownership passed=True violations=0 (1040 files); no credential files; no sk-/AKIA literals; no shell=True/"
            "os.system/eval/exec/pickle.loads; no SQL string assembly"
        ),
        "log_path": "artifacts/handoffs/P03-02/zcode/logs/baseline-checks.log",
        "mandatory": False,
        "passed": True,
    },
]

DEFECTS = [
    {
        "id": "D1",
        "severity": "blocking",
        "task": "P03-02",
        "title": "No implementation candidate exists: 0/5 code-and-test deliverables were written (only the two BLOCKED report documents exist, 2/7 paths present)",
        "evidence": [
            "logs/cmd1-pytest.log exit 4 (0 tests ran)",
            "logs/gates-phase03-sandbox.log: P03-02-cmd1 exit_code=4; docs present but no code",
            "logs/dsh-evidence-integrity.log: DSH recorded 0/7 before writing its two docs; those two are present now, the other five are not",
        ],
        "status": "unfixed",
        "owner": "DSH / P03-02 (deliberately not started; see D2)",
        "note": "refusing to write 0002 without 0001 avoids both a dangling down_revision and a second definition of the domain model",
    },
    {
        "id": "D2",
        "severity": "blocking",
        "task": "G02 + P03-01 + G01",
        "title": "Both declared prerequisites are unmet: G02 has no record and P03-01 is BLOCKED with zero code deliverables",
        "evidence": [
            "artifacts/gates/G02.json does not exist; the phase-02 sandbox probe reports G02: 5/27",
            "artifacts/handoffs/P03-01/dsh/evidence.json and artifacts/handoffs/P03-01/zcode/precheck.json are both status=BLOCKED; P03-01 code+test deliverables 0/6",
            "artifacts/gates/G01.json status=failed (its 5 acceptance assertions all pass; only handoff records are missing)",
            "TASK_MANIFEST.json deps for P03-02 = [G02, P03-01]; TASK_GRAPH.md:59 agrees",
            "dependency artifacts present: 0/19",
        ],
        "status": "unfixed",
        "owner": "Codex (G01 review) + ZCode (P01-01..P01-03 prechecks) + role A/DSH (P02-01..04, then P03-01)",
    },
    {
        "id": "D3",
        "severity": "blocking-for-this-task-when-reissued",
        "task": "P03-02 scope / planning",
        "title": "The task's 7-file allow-list omits the dependency manifests it needs, so alembic and psycopg still cannot be added",
        "evidence": [
            "allowed_files = [0002_planning_runtime.py, planning_models.py, runtime_models.py, both docs, both tests] - apps/backend/pyproject.toml and uv.lock are absent",
            "uv.lock has 40 packages and none of them is alembic, sqlalchemy, psycopg or psycopg-binary",
            "the interface is persist_version(ScheduleVersionDTO) -> VersionRef and the two test cases are database-level assertions",
            "both P03-02 test cases need a live PostgreSQL through conftest's db_connection, which fails when psycopg is missing",
        ],
        "impact": "identical to the P03-01 finding: a re-issued task cannot succeed as scoped",
        "status": "unfixed",
        "owner": "project management / planning: extend the allow-list or authorise a dependency task",
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
        "severity": "non-blocking (contract gap)",
        "task": "P01-02 / ARCH-0004",
        "title": "The gate runner still has no accepted state for a prerequisite-blocked handoff; it now flags two tasks for reporting honestly",
        "evidence": [
            "logs/gates-phase03-sandbox.log: dsh-evidence:P03-01 and dsh-evidence:P03-02 both 'unexpected status=BLOCKED'",
            "scripts/gates.py accepts only READY_FOR_ZCODE and Z_PRECHECK_PASSED for DSH evidence",
            "every task book orders a BLOCKED report when prerequisites are missing",
        ],
        "status": "unfixed",
        "owner": "P01-02 + ARCH-0004 decision",
    },
    {
        "id": "D6",
        "severity": "non-blocking-for-P03-02",
        "task": "P01-01",
        "title": "apps/frontend declares test=vitest run without devDependencies, so the CI frontend job step fails",
        "evidence": ["apps/frontend/package.json", ".github/workflows/ci.yml:95", "carried over from the 2026-09-14 P02-02 review"],
        "status": "unfixed",
        "owner": "P01-01 (or P24-01)",
        "reverified_this_pass": False,
    },
    {
        "id": "D7",
        "severity": "non-blocking-for-P03-02",
        "task": "P01-02",
        "title": "npm run test:e2e:list exits 1 with zero specs while CI treats it as a required step",
        "evidence": [".github/workflows/ci.yml:98", "playwright.config.ts comment", "carried over from the 2026-09-14 P02-02 review"],
        "status": "unfixed",
        "owner": "P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D8",
        "severity": "non-blocking",
        "task": "engineering config",
        "title": "ruff is configured but never executed in CI, and its RUF001/RUF002 rules conflict with the Chinese fullwidth punctuation convention",
        "evidence": ["pyproject.toml [tool.ruff]", ".github/workflows/ci.yml (no ruff step)", "carried over from the 2026-09-14 P02-02 review"],
        "status": "unfixed",
        "owner": "engineering config / P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D9",
        "severity": "non-blocking",
        "task": "P01-02",
        "title": "Gate revision is built from volatile session/scratch files (.mimosa/**, tmp/**), so a recorded code_revision is unreproducible",
        "evidence": [
            "scripts/gates.py:43 EXCLUDED_FROM_REVISION excludes only artifacts/gates and artifacts/e2e",
            "measured 1167 rows of which .mimosa/** is 451 and tmp/** is 423",
            ".mimosa/hook-state/<session>.json is rewritten on every tool call",
            "reproduced independently by ZCode (artifacts/handoffs/P02-02/zcode/logs/revision-volatility.log) and by DSH in both Phase 03 handoffs",
        ],
        "status": "unfixed",
        "confidence": "proven by reproduction; corroborated independently by DSH",
        "owner": "P01-02",
        "reverified_this_pass": True,
    },
    {
        "id": "D10",
        "severity": "observation",
        "task": "P01-01",
        "title": "The _PENDING_APIS registries name capabilities but not the modules Phase 02/03 create, so probing those surfaces yields a bare AttributeError",
        "evidence": [
            "logistics_domain._PENDING_APIS = ['entities','ids','ports','states','units']",
            "logistics_contracts._PENDING_APIS = ['dto','errors','export_schema','mapping']",
            "no 'planning'/'execution'/'runtime'/'common' entry in either",
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
    "task_id": "P03-02",
    "scene": "planning-schema",
    "phase": 3,
    "phase_gate": "G03",
    "reviewer": "ZCode",
    "review_role": "independent-pre-acceptance",
    "status": "BLOCKED",
    "verdict_reason": (
        "P03-02 has no implementation candidate: the five code-and-test deliverables do not exist and only the two "
        "BLOCKED-report documents were written. Both declared prerequisites are unmet (G02 has no record, P03-01 is "
        "BLOCKED with 0/6 code deliverables), the transitive prerequisite G01 is status=failed, and no PostgreSQL is "
        "reachable. DSH's BLOCKED verdict is independently confirmed; nothing could be pre-accepted."
    ),
    "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
    "candidate": {
        "root": str(root),
        "vcs": "no .git in this checkout; located by content hash (scripts/gates.py compute_revision)",
        "revision_label_during_this_review": current_revision(),
        "revision_label_is_self_perturbing": (
            "by construction this label is one step stale: compute_revision() covers this record's own directory, so "
            "writing evidence.json and precheck.json moves the label again (defect D9)"
        ),
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
        "G02": {"status": "not_signed", "record_exists": (root / "artifacts/gates/G02.json").is_file(), "sandbox_result": "G02: 5/27"},
        "P03-01": {
            "status": "BLOCKED",
            "record": "artifacts/handoffs/P03-01/zcode/precheck.json",
            "code_and_test_present": "0/6",
            "declared_by": "TASK_MANIFEST.json deps [G02, P03-01]; TASK_GRAPH.md:59",
        },
        "G03": {"status": "not_signed", "sandbox_result": "G03: 9/28 checks passed"},
    },
    "chain_coupling": {
        "finding": (
            "P03-02 is not independently deliverable: 0002_planning_runtime.py is the second link of one Alembic chain "
            "whose 0001_resources.py, migrations/env.py and alembic.ini do not exist, and Test Case 2's FK target (the "
            "orders table) is created by 0001."
        ),
        "evidence": [
            "alembic.ini, apps/backend/migrations/env.py and apps/backend/migrations/versions/0001_resources.py are all absent; apps/backend/migrations does not exist",
            "TASK_MANIFEST.json allowed_files for P03-01 include 0001_resources.py and env.py; without them a 0002 file would have a dangling down_revision",
            "DOMAIN_CATALOG.md:60 'FK deletes default to RESTRICT' - so deleting an Order referenced by V1 must be refused by the database, which requires both the orders table (0001) and the referencing table (0002) to exist",
            "uv.lock contains no alembic, so no round-trip check can run at all",
        ],
        "consequence": "P03-01 and P03-02 must be accepted as one chain, and neither can be verified alone",
    },
    "environment": {
        "postgresql_client": "psql not found on PATH",
        "postgresql_server": "pg_ctl not found on PATH",
        "test_database_url_set": False,
        "conftest_behaviour_when_url_absent": "pytest.fail, never skip (tests/conftest.py)",
        "isolated_postgres_reachable": False,
        "environment_manual_present": False,
        "note": "TEST_DATABASE_URL was only checked for presence, never echoed; no connection was attempted",
    },
    "frozen_interface": {
        "declared": "persist_version(version: ScheduleVersionDTO) -> VersionRef",
        "types_required_and_absent": ["ScheduleVersionDTO", "VersionRef", "ScheduleVersion", "Job", "Outbox", "AuditEntry"],
        "business_rules_expected": [
            "ScheduleVersion content and audit appends are not overwritable",
            "active_version_id is stored separately",
            "unique(schedule_id, version_no)",
            "JSONB content carries schema_version",
            "money columns are bigint",
        ],
        "algorithm_expected": [
            "plan tasks linked by (version_id, task_id)",
            "indexes covering job status, event cursor and parent_version_id",
            "migration round-trip check",
        ],
    },
    "commands": COMMANDS,
    "test_cases": {
        "1": {
            "input": "two rows with version_no=2 under the same schedule",
            "expected": "rejected by the unique constraint on (schedule_id, version_no)",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation and no test files exist (exit_code=4, 0 tests ran); no PostgreSQL is reachable either",
        },
        "2": {
            "input": "deleting an Order that V1 references",
            "expected": "rejected (RESTRICT), not cascaded",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation, no tests, no database; also requires the orders table that P03-01 was to create",
        },
        "coverage": "0 of 2 required test cases",
    },
    "acceptance_recheck_plan": {
        "purpose": "what to verify when P03-02 is re-issued after G02 is signed and P03-01 lands",
        "preconditions": [
            "P03-01 accepted first, because 0002 chains from 0001 and Test Case 2's FK target lives in 0001",
            "an isolated PostgreSQL reachable with TEST_DATABASE_URL exported to a *test*-named database",
            "apps/backend/pyproject.toml + uv.lock permitted to gain psycopg/SQLAlchemy/Alembic (see D3), with uv lock --check still passing",
        ],
        "checks": [
            "alembic upgrade head applies 0001 then 0002, and downgrade unwinds 0002 then 0001, both without residue and without breaking the revision chain",
            "test case 1: a second version_no=2 under one schedule is rejected by the unique constraint, naming the violated constraint, with no partial row written",
            "test case 2: deleting an Order referenced by V1 is refused by the database (RESTRICT), and no child rows disappear",
            "immutability: updating a ScheduleVersion row or an audit row must be impossible or must append rather than overwrite; active_version_id must live on Schedule, not on the version",
            "JSONB columns carry schema_version, and money columns are bigint (not float, not numeric-with-scale drift)",
            "indexes exist for job status, event cursor (events(scope,sequence)) and parent_version_id, matching DOMAIN_CATALOG.md:62",
            "plan tasks are keyed by (version_id, task_id), not by a synthetic surrogate alone",
            "the DSN used in the test run must be postgresql, never sqlite",
            "table/column definitions must map 1:1 from the real packages/domain types once P02-03/P02-04 exist, not be reverse-engineered from DDL",
        ],
    },
    "defects": DEFECTS,
    "fixed_by_zcode": [],
    "unfixed": [d["id"] for d in DEFECTS],
    "not_verified": [
        "Both P03-02 test cases, the persist_version interface, the immutability/active_version_id/JSONB/bigint business rules and the migration round-trip are UNVERIFIED: nothing was implemented and no database exists",
        "G03 exit criteria (real PostgreSQL migration/rollback/FK, consistent snapshot, exactly-one concurrent resource commit, no half version on transaction failure) belong to Phase 03 as a whole and mostly depend on P03-03/P03-04",
        "Static type checking: no mypy/pyright configuration exists",
        "npm ci, the frontend workspace test and the Playwright listing were NOT re-run in this pass; D6/D7/D8 rest on the 2026-09-14 evidence and are flagged reverified_this_pass=false",
        "CI as written cannot run in this checkout (no .git), so its git ls-files / git grep / git diff steps cannot execute as written",
    ],
    "security_review": {
        "scope": "the change set is documentation plus DSH evidence; the eventual deliverable is a database migration, so forward-looking controls are stated as requirements, not passes",
        "credential_files": "none found (.env / .env.* / *.pem / *.p12 / id_rsa*) in the target tree",
        "secret_literals": "0 hits for sk-[A-Za-z0-9]{20,} and AKIA[0-9A-Z]{16}",
        "test_database_url_handling": "presence checked only; never printed, no connection attempted",
        "sql_injection": (
            "no database access code exists yet, so there is nothing to verify. Every parameter P03-02/P03-03/P03-04 uses "
            "must be bound, never interpolated or assembled with format/f-string - a forward-looking requirement, NOT a pass"
        ),
        "command_injection": "no shell=True / os.system / eval / exec / pickle.loads in apps|packages|scripts|tests; runner and conftest use argv arrays",
        "auth_scope_logging": "no HTTP boundary or worker exists yet; belongs to P05-01/P37",
        "dependency_changes": "none in this change set; uv lock --check exit 0",
        "external_targets_scanned": "none - only local tool availability and localhost environment variables were inspected",
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
        "path": "artifacts/handoffs/P03-02/zcode/build-evidence.py",
        "sha256": sha("artifacts/handoffs/P03-02/zcode/build-evidence.py"),
        "note": "this record's own generator; rerun it from the repository root to rebuild evidence.json and precheck.json",
    },
    "sandbox_gate_evidence": collect_sandbox(),
    "files_added_by_zcode": [
        "docs/handoffs/P03-02/zcode.md",
        "artifacts/handoffs/P03-02/zcode/evidence.json",
        "artifacts/handoffs/P03-02/zcode/precheck.json",
        "artifacts/handoffs/P03-02/zcode/build-evidence.py",
        "artifacts/handoffs/P03-02/zcode/logs/ (raw command logs)",
        "tmp/zcode-g03-dryrun-p2/ (non-official G03 sandbox evidence, under the gitignored tmp/)",
    ],
    "files_modified_by_zcode": [],
    "preserved_dsh_report": [
        "docs/handoffs/P03-02/dsh.md",
        "artifacts/handoffs/P03-02/dsh/evidence.json",
        "artifacts/handoffs/P03-02/dsh/logs/",
        "docs/implementation/P03-02.md",
        "docs/implementation/reports/P03-02.md",
        "note: none of these was created, rewritten or reformatted by this role; only read and hashed",
    ],
    "signs_gate": False,
    "gate_signed": None,
    "limitations": [
        "This record is BLOCKED on purpose: scripts/gates.py compares status against 'Z_PRECHECK_PASSED' and fails closed. It agrees with DSH's own BLOCKED verdict; the task must be re-issued after G02 is signed and P03-01 lands.",
        "P03-02-cmd2 (check_architecture.py) exit 0 is vacuous and is not acceptance evidence.",
        "docs/workflow/README.md and HANDOFF_CONTRACT.md do not exist (ARCH-0004); this record follows the user instruction plus the path hardcoded in scripts/gates.py:305-311.",
        "D6/D7/D8 were not re-executed in this pass because no frontend or lint artifact is in P03-02's scope; they carry the 2026-09-14 evidence and are flagged reverified_this_pass=false.",
    ],
    "next_actions": [
        "Codex: record the G01 codex review and decide the revision-staleness policy (D9); G01 needs the three P01-01..P01-03 zcode precheck records before it can be re-run and signed.",
        "ZCode: those three P01 records are this role's own gap and are the entire remaining cause of G01 failing.",
        "Role A / DSH: deliver P02-01..P02-04, assemble G02, then deliver P03-01 and P03-02 as one chain.",
        "Project management: resolve D3 (allow psycopg/SQLAlchemy/Alembic into the workspace lock) and D4 (write the Phase 01 environment manual) before re-issuing any Phase 03 task.",
    ],
}

out_dir = pathlib.Path("artifacts/handoffs/P03-02/zcode")
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
for name in ("evidence.json", "precheck.json"):
    (out_dir / name).write_text(text, encoding="utf-8")

print("status:", payload["status"])
print("deliverables present:", deliverable_count, "/", len(DELIVERABLES))
print("code+test present   :", code_count, "/", len(CODE_AND_TEST_DELIVERABLES))
print("dependency present  :", dep_count, "/", len(DEPENDENCY_ARTIFACTS))
print("dsh logs match      :", dsh["all_command_log_hashes_match"], "| inputs stale:", dsh["stale_recorded_inputs"] or "none")
print("logs recorded:", len(payload["evidence_logs"]))
print("inputs hashed:", len(payload["verified_input_hashes"]), "missing:", [r for r, v in payload["verified_input_hashes"].items() if v is None])
print("bytes:", (out_dir / "evidence.json").stat().st_size)
