"""Assemble the P03-03 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P03-03/zcode/build-evidence.py

DSH submitted an honest BLOCKED handoff with no implementation. This record reviews that
submission independently, records this role's verdict, and adds two findings this round
produced itself: the architecture checker cannot see an ORM leaking out of the adapter,
and the G03 pass counter rises purely from blocked tasks writing reports. It only reads the
repository and writes the two records next to itself; it never signs a Gate.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()

BUILDER_LOG = "artifacts/handoffs/P03-03/zcode/logs/build-evidence.log"


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
    for path in sorted(pathlib.Path("artifacts/handoffs/P03-03/zcode/logs").glob("*.log")):
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
    for path in sorted(pathlib.Path("tmp/zcode-g03-dryrun-p3").rglob("*")):
        if path.is_file():
            rel = path.as_posix()
            out[rel] = {"sha256": sha(rel), "bytes": path.stat().st_size}
    return out


def presence(paths: list[str]) -> tuple[dict, int]:
    table = {rel: (root / rel).is_file() for rel in paths}
    return table, sum(1 for present in table.values() if present)


def dsh_review() -> dict:
    d = read_json("artifacts/handoffs/P03-03/dsh/evidence.json")
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
    z2 = read_json("artifacts/handoffs/P03-02/zcode/precheck.json")
    return {
        "present": (root / "docs/handoffs/P03-03/dsh.md").is_file()
        and (root / "artifacts/handoffs/P03-03/dsh/evidence.json").is_file(),
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
        "quotes_predecessor_verdict_correctly": z2.get("status") == "BLOCKED"
        and z2.get("code_and_test_present_count") == 0,
        "own_systemic_finding": d.get("systemic_finding"),
        "overclaim_check": (
            "the DSH report states explicitly that it claims no unrun test passed; and in section 4 it correctly warns "
            "that the rise from 7/28 to 9/28 came only from documentation rows while the passing task-command count stayed "
            "at 4/8 and was entirely vacuous architecture checks. No overclaim found; the warning is accurate"
        ),
        "verdict_on_submission": (
            "honest, accurate, and its section 7 inverts the framing correctly: the repair unit must be the barrier, not "
            "another task. Two of its open questions I was able to close this round (see architecture_checker_coverage "
            "and gate_pass_count_perversity): it asked whether check_architecture.py could detect ORM leakage and could "
            "only say 'unverifiable'; the answer is that it cannot, once the ORM is legitimately declared."
        ),
    }


DELIVERABLES = [
    "apps/backend/src/logistics_backend/persistence/snapshots.py",
    "apps/backend/src/logistics_backend/persistence/uow.py",
    "docs/implementation/P03-03.md",
    "docs/implementation/reports/P03-03.md",
    "packages/domain/src/logistics_domain/ports/storage.py",
    "tests/integration/test_p03_03_repositories_and_snapshot.py",
    "tests/unit/test_p03_03_repositories_and_snapshot.py",
]

CODE_AND_TEST_DELIVERABLES = [
    "apps/backend/src/logistics_backend/persistence/snapshots.py",
    "apps/backend/src/logistics_backend/persistence/uow.py",
    "packages/domain/src/logistics_domain/ports/storage.py",
    "tests/integration/test_p03_03_repositories_and_snapshot.py",
    "tests/unit/test_p03_03_repositories_and_snapshot.py",
]

DEPENDENCY_ARTIFACTS = [
    "artifacts/gates/G02.json",
    "artifacts/handoffs/P03-01/dsh/evidence.json",
    "artifacts/handoffs/P03-02/dsh/evidence.json",
    "alembic.ini",
    "apps/backend/migrations/env.py",
    "apps/backend/migrations/versions/0001_resources.py",
    "apps/backend/migrations/versions/0002_planning_runtime.py",
    "apps/backend/src/logistics_backend/persistence/resource_models.py",
    "apps/backend/src/logistics_backend/persistence/planning_models.py",
    "apps/backend/src/logistics_backend/persistence/runtime_models.py",
    "packages/domain/src/logistics_domain/entities.py",
    "packages/domain/src/logistics_domain/orders.py",
    "packages/domain/src/logistics_domain/resources.py",
    "packages/domain/src/logistics_domain/planning.py",
    "packages/domain/src/logistics_domain/ports/storage.py",
    "packages/domain/src/logistics_domain/ids.py",
    "packages/domain/src/logistics_domain/units.py",
    "packages/domain/src/logistics_domain/states.py",
    "packages/contracts/src/logistics_contracts/planning.py",
    "scripts/export_contracts.py",
    "contracts/schemas.json",
]

VERIFIED_INPUTS = [
    "docs/prompts/03-database/P03-03-repositories-and-snapshot.md",
    "docs/prompts/03-database/P03-02-planning-schema.md",
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
    "artifacts/handoffs/P03-01/zcode/precheck.json",
    "artifacts/handoffs/P03-02/zcode/precheck.json",
    "artifacts/handoffs/P03-03/dsh/evidence.json",
    "docs/handoffs/P03-03/dsh.md",
    "docs/implementation/P03-03.md",
    "docs/implementation/reports/P03-03.md",
]

PHASE_TASKS = ("P03-01", "P03-02", "P03-03", "P03-04")

COMMANDS = [
    {
        "check_id": "P03-03-cmd1",
        "argv": "uv run pytest tests/unit/test_p03_03_repositories_and_snapshot.py tests/integration/test_p03_03_repositories_and_snapshot.py -q",
        "cwd": str(root),
        "exit_code": 4,
        "result": "ERROR: file or directory not found: tests/unit/test_p03_03_repositories_and_snapshot.py; no tests ran in 0.00s",
        "log_path": "artifacts/handoffs/P03-03/zcode/logs/cmd1-pytest.log",
        "mandatory": True,
        "passed": False,
        "agrees_with_dsh": True,
    },
    {
        "check_id": "P03-03-cmd2",
        "argv": "uv run python scripts/check_architecture.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
        "log_path": "artifacts/handoffs/P03-03/zcode/logs/cmd2-architecture.log",
        "mandatory": True,
        "passed": True,
        "agrees_with_dsh": True,
        "caveat": "vacuous pass, and for THIS task specifically it cannot cover the task's own architectural obligation - see commands[architecture-coverage-probe]",
    },
    {
        "check_id": "regression",
        "argv": "uv run pytest -q",
        "cwd": str(root),
        "exit_code": 0,
        "result": "187 passed",
        "log_path": "artifacts/handoffs/P03-03/zcode/logs/regression-pytest.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "architecture-coverage-probe",
        "argv": "uv run python artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "scenario A (backend does not declare sqlalchemy): an sqlalchemy import in the backend API layer is caught "
            "by ARCH-UNDECLARED; scenario B (backend declares sqlalchemy, the state P03-01 must create): 0 violations, "
            "NOT DETECTED. The checker treats all of apps/backend/src as one layer and hard-forbids sqlalchemy/alembic/"
            "psycopg only inside domain, so nothing distinguishes adapter from application within the backend"
        ),
        "log_path": "artifacts/handoffs/P03-03/zcode/logs/architecture-coverage-probe.log",
        "mandatory": False,
        "passed": False,
        "note": "answers DSH's open question 'can check_architecture.py detect ORM leakage out of the adapter?' - it cannot; evidence for D5",
    },
    {
        "check_id": "gates-phase03-sandbox",
        "argv": "uv run python scripts/gates.py --phase 03 --revision auto --out-dir tmp/zcode-g03-dryrun-p3",
        "cwd": str(root),
        "exit_code": 1,
        "result": (
            "G03: 11/28 checks passed. Breakdown: 1 G00 row + 4 vacuous P03-0X-cmd2 architecture rows + 6 documentation "
            "rows; the 4 remaining cmd2 plus every other command row fails. dsh-evidence:P03-01/02/03 all 'unexpected "
            "status=BLOCKED'; zcode-precheck:P03-01/02 BLOCKED and P03-03/04 missing; previous-gate G01 failed and G02 missing"
        ),
        "log_path": "artifacts/handoffs/P03-03/zcode/logs/gates-phase03-sandbox.log",
        "mandatory": False,
        "passed": False,
        "note": "sandbox out-dir; artifacts/gates/G03.json was NOT written. Reconciles with DSH's 9/28: its two docs now exist (9 + 2 = 11)",
    },
    {
        "check_id": "dsh-evidence-integrity",
        "argv": "independent recomputation of the hashes recorded in artifacts/handoffs/P03-03/dsh/evidence.json",
        "cwd": str(root),
        "exit_code": 0,
        "result": "all 4 command-log hashes match; all 17 recorded input hashes match; no stale recorded input; quoted predecessor verdicts correct",
        "log_path": "artifacts/handoffs/P03-03/zcode/logs/dsh-evidence-integrity.log",
        "mandatory": False,
        "passed": True,
    },
    {
        "check_id": "environment-and-baseline",
        "argv": "which psql pg_ctl ; uv lock --check ; check_ownership.py --json ; credential find ; secret grep ; injection grep ; SQL-assembly grep",
        "cwd": str(root),
        "exit_code": 0,
        "result": (
            "psql/pg_ctl absent; TEST_DATABASE_URL unset; uv.lock 40 packages with NO alembic/sqlalchemy/psycopg; "
            "ownership passed=True violations=0 (1087 files); no credential files; no sk-/AKIA literals; no shell=True/"
            "os.system/eval/exec/pickle.loads; no SQL string assembly"
        ),
        "log_path": "artifacts/handoffs/P03-03/zcode/logs/baseline-checks.log",
        "mandatory": False,
        "passed": True,
    },
]

DEFECTS = [
    {
        "id": "D1",
        "severity": "blocking",
        "task": "P03-03",
        "title": "No implementation candidate exists: 0/5 code-and-test deliverables were written (only the two BLOCKED report documents exist, 2/7 paths present)",
        "evidence": [
            "logs/cmd1-pytest.log exit 4 (0 tests ran)",
            "logs/gates-phase03-sandbox.log: P03-03-cmd1 exit_code=4",
            "logs/dsh-evidence-integrity.log: DSH recorded 0/7 before writing its two docs; those two are present now",
            "PlanningSnapshotStore / UnitOfWork / PlanningSnapshot / PlanningScope have zero implementation hits in apps|packages|tests|scripts",
        ],
        "status": "unfixed",
        "owner": "DSH / P03-03 (deliberately not started; see D2)",
        "note": "writing ports/storage.py before the domain types exist would define the domain model from the port backwards, which Architecture Constraint 6 forbids - DSH's refusal is correct",
    },
    {
        "id": "D2",
        "severity": "blocking",
        "task": "G02 + P03-02 + G01",
        "title": "Both declared prerequisites are unmet: G02 has no record and P03-02 is BLOCKED with zero code deliverables",
        "evidence": [
            "artifacts/gates/G02.json does not exist; the phase-02 sandbox probe reports G02: 5/27",
            "artifacts/handoffs/P03-02/dsh/evidence.json and artifacts/handoffs/P03-02/zcode/precheck.json are both status=BLOCKED; P03-02 code+test 0/5",
            "artifacts/gates/G01.json status=failed (its 5 acceptance assertions all pass; only handoff records are missing)",
            "TASK_MANIFEST.json deps for P03-03 = [G02, P03-02]; TASK_GRAPH.md:60 agrees",
            "dependency artifacts present: 2/21, and both are the predecessors' own BLOCKED evidence records rather than delivered capabilities",
        ],
        "status": "unfixed",
        "owner": "Codex (G01 review) + ZCode (P01-01..P01-03 prechecks) + role A/DSH (P02-01..04, then P03-01, P03-02)",
    },
    {
        "id": "D3",
        "severity": "blocking-for-this-task-when-reissued",
        "task": "P03-03 scope / planning",
        "title": "The task's 7-file allow-list still omits the dependency manifests it needs; third task in a row with this gap",
        "evidence": [
            "allowed_files = [snapshots.py, uow.py, both docs, ports/storage.py, both tests] - apps/backend/pyproject.toml and uv.lock are absent",
            "uv.lock has 40 packages and none of them is alembic, sqlalchemy, psycopg or psycopg-binary",
            "the business rules require REPEATABLE READ and an ORM that stays inside the adapter, i.e. sqlalchemy plus a driver",
            "both test cases need two real concurrent PostgreSQL connections through conftest",
        ],
        "impact": "same as P03-01/P03-02: the task cannot succeed as scoped; this is now confirmed as a planning-level gap, not a task-level oversight",
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
        "severity": "blocking-for-acceptance-of-this-task's-core-obligation",
        "task": "P01-02 (checker coverage)",
        "title": "The architecture checker cannot detect an ORM leaking out of the adapter once the ORM is legitimately declared, so P03-03's central obligation has no automated enforcement",
        "evidence": [
            "scripts/check_architecture.py LAYERS['backend'] = (('apps/backend/src',), ...) - all of apps/backend/src is ONE layer, with no adapter-versus-application sub-rule",
            "THIRD_PARTY forbids sqlalchemy/alembic/psycopg only in {'domain'}",
            "probe scenario A (backend does not declare sqlalchemy): 1 violation, ARCH-UNDECLARED",
            "probe scenario B (backend declares sqlalchemy, the state P03-01 must create): 0 violations, NOT DETECTED",
            "logs/architecture-coverage-probe.log; probe script at artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py",
        ],
        "impact": (
            "P03-03's Business Rule 'ORM must not leave the adapter' and Architecture Constraint 4's 'application must not "
            "import adapters' cannot be verified by the only automated dependency check. Once the ORM is declared, a "
            "repository returning a SQLAlchemy Session or ORM model into application code still yields violations=0, so "
            "acceptance criterion 3 ('dependency boundary check passes') would be a vacuous pass for exactly that obligation"
        ),
        "recommendation": (
            "add a rule that treats apps/backend/src/logistics_backend/persistence as the only place where ORM/driver "
            "imports are allowed, or add an explicit forbidden-import rule per sub-package; and let the precheck require a "
            "dedicated probe rather than the generic layer check for this obligation"
        ),
        "status": "unfixed",
        "owner": "P01-02",
    },
    {
        "id": "D6",
        "severity": "non-blocking (contract gap)",
        "task": "P01-02 / ARCH-0004",
        "title": "The gate runner still has no accepted state for a prerequisite-blocked handoff; three tasks are now flagged for reporting honestly",
        "evidence": [
            "logs/gates-phase03-sandbox.log: dsh-evidence:P03-01, P03-02 and P03-03 all 'unexpected status=BLOCKED'",
            "scripts/gates.py accepts only READY_FOR_ZCODE and Z_PRECHECK_PASSED for DSH evidence",
            "every task book orders a BLOCKED report when prerequisites are missing",
        ],
        "status": "unfixed",
        "owner": "P01-02 + ARCH-0004 decision",
    },
    {
        "id": "D7",
        "severity": "non-blocking (metric perversity, please read before trusting any pass count)",
        "task": "P01-02 (gate runner)",
        "title": "The G03 pass count rises purely because blocked tasks write documentation: it equals 1 + 4 + 2N, where N is the number of Phase 03 tasks that produced only their BLOCKED docs",
        "evidence": [
            "measured across four rounds: 5/28 (P03-01 probe) -> 7/28 -> 9/28 -> 11/28 (this pass)",
            "composition at 11/28: 1 previous-gate G00 row + 4 vacuous P03-0X-cmd2 architecture rows + 6 documentation rows (2 per task with docs)",
            "every other row fails, including all four P03-0X-cmd1 command rows (exit 4) and all four dsh-evidence/zcode-precheck rows",
            "logs/gates-phase03-sandbox.log",
        ],
        "impact": (
            "a reader tracking only the pass count would conclude Phase 03 is progressing when nothing has been implemented; "
            "the count is anti-correlated with real progress because each blocked task adds two free rows. DSH reached the "
            "same conclusion independently in its section 4 and systemic_finding SYS-1"
        ),
        "recommendation": "report task-command rows separately from documentation rows, or weight the summary so documentation cannot mask zero implemented deliverables",
        "status": "unfixed",
        "owner": "P01-02",
    },
    {
        "id": "D8",
        "severity": "non-blocking-for-P03-03",
        "task": "P01-01",
        "title": "apps/frontend declares test=vitest run without devDependencies, so the CI frontend job step fails",
        "evidence": ["apps/frontend/package.json", ".github/workflows/ci.yml:95", "carried over from the 2026-09-14 P02-02 review"],
        "status": "unfixed",
        "owner": "P01-01 (or P24-01)",
        "reverified_this_pass": False,
    },
    {
        "id": "D9",
        "severity": "non-blocking-for-P03-03",
        "task": "P01-02",
        "title": "npm run test:e2e:list exits 1 with zero specs while CI treats it as a required step",
        "evidence": [".github/workflows/ci.yml:98", "playwright.config.ts comment", "carried over from the 2026-09-14 P02-02 review"],
        "status": "unfixed",
        "owner": "P01-02",
        "reverified_this_pass": False,
    },
    {
        "id": "D10",
        "severity": "non-blocking",
        "task": "engineering config",
        "title": "ruff is configured but never executed in CI, and its RUF001/RUF002 rules conflict with the Chinese fullwidth punctuation convention",
        "evidence": ["pyproject.toml [tool.ruff]", ".github/workflows/ci.yml (no ruff step)", "carried over from the 2026-09-14 P02-02 review"],
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
            "reproduced by ZCode and independently by DSH in all three Phase 03 handoffs",
        ],
        "status": "unfixed",
        "confidence": "proven by reproduction; three independent observations",
        "owner": "P01-02",
        "reverified_this_pass": True,
    },
    {
        "id": "D12",
        "severity": "observation (narrowed this round)",
        "task": "P01-01",
        "title": "The _PENDING_APIS registry covers P03-03's module correctly, but still omits the Phase 02 module names - the gap is narrower than previously reported",
        "evidence": [
            "logistics_domain._PENDING_APIS = ['entities','ids','ports','states','units'] - 'ports' IS registered and names P03-03 among its owners",
            "logistics_domain.ports raises NotImplementedError with the correct owner message; the packages/domain/src/logistics_domain/ports directory simply does not exist",
            "logistics_contracts._PENDING_APIS = ['dto','errors','export_schema','mapping'] - 'planning', 'execution', 'runtime' and 'common' are still absent",
        ],
        "impact": "cosmetic; P03-03 is the first task whose module name the registry anticipates, so the fail-loudly design works for this task",
        "status": "unfixed",
        "owner": "P01-01 (only the Phase 02 names remain unregistered)",
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
    "task_id": "P03-03",
    "scene": "repositories-and-snapshot",
    "phase": 3,
    "phase_gate": "G03",
    "reviewer": "ZCode",
    "review_role": "independent-pre-acceptance",
    "status": "BLOCKED",
    "verdict_reason": (
        "P03-03 has no implementation candidate: the five code-and-test deliverables do not exist and only the two "
        "BLOCKED-report documents were written. Both declared prerequisites are unmet (G02 has no record, P03-02 is "
        "BLOCKED with 0/5 code deliverables), the transitive prerequisite G01 is status=failed, and no PostgreSQL is "
        "reachable. DSH's BLOCKED verdict is independently confirmed; nothing could be pre-accepted. Re-issuing further "
        "Phase 03 tasks before the barriers are repaired would only reproduce this record."
    ),
    "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
    "candidate": {
        "root": str(root),
        "vcs": "no .git in this checkout; located by content hash (scripts/gates.py compute_revision)",
        "revision_label_during_this_review": current_revision(),
        "revision_label_is_self_perturbing": (
            "one step stale by construction: compute_revision() covers this record's own directory (defect D11)"
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
        "G02": {"status": "not_signed", "record_exists": (root / "artifacts/gates/G02.json").is_file()},
        "P03-02": {
            "status": "BLOCKED",
            "record": "artifacts/handoffs/P03-02/zcode/precheck.json",
            "code_and_test_present": "0/5",
        },
        "G03": {"status": "not_signed", "sandbox_result": "G03: 11/28 checks passed"},
    },
    "architecture_checker_coverage": {
        "question": "can scripts/check_architecture.py detect an ORM leaking out of the adapter layer?",
        "answer": "No, once the ORM is legitimately declared.",
        "structural_reason": [
            "LAYERS['backend'] covers all of apps/backend/src as a single layer, so there is no adapter-versus-application sub-rule",
            "THIRD_PARTY forbids sqlalchemy/alembic/psycopg only inside the domain layer",
        ],
        "experiment": [
            "scenario A, backend does not declare sqlalchemy: an sqlalchemy import in the backend API layer yields 1 violation (ARCH-UNDECLARED)",
            "scenario B, backend declares sqlalchemy (the state P03-01 must create): the same file yields 0 violations",
        ],
        "consequence": (
            "the enforcement observed in scenario A is an artefact of the dependency not being declared yet. P03-01 must "
            "declare it, which moves the repository into scenario B and leaves the obligation with no automated check"
        ),
        "evidence": "artifacts/handoffs/P03-03/zcode/logs/architecture-coverage-probe.log",
        "probe_script": "artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py",
    },
    "gate_pass_count_perversity": {
        "formula": "G03 pass count = 1 (previous-gate G00) + 4 (vacuous P03-0X-cmd2 architecture rows) + 2 x (Phase 03 tasks that wrote only their BLOCKED docs)",
        "measured": ["5/28", "7/28", "9/28", "11/28"],
        "consequence": "the counter is anti-correlated with real progress: each blocked task adds two free rows from documentation while the implemented-deliverable count stays at zero",
        "independently_observed_by_dsh": "its section 4 warns that the 7/28 -> 9/28 rise was entirely documentation, with the passing task-command count unchanged at 4/8; its systemic_finding SYS-1 records the same",
    },
    "frozen_interface": {
        "declared": "PlanningSnapshotStore.capture(scope: PlanningScope) -> PlanningSnapshot; UnitOfWork.commit() -> None",
        "types_required_and_absent": ["PlanningSnapshotStore", "UnitOfWork", "PlanningSnapshot", "PlanningScope", "ResourceRevision", "InventoryLedger"],
        "business_rules_expected": [
            "capture a consistent snapshot under REPEATABLE READ",
            "the snapshot includes matrix and calendar versions",
            "the ORM never leaves the adapter",
            "canonical serialization produces a stable hash",
            "DTOs map onto pure domain snapshots",
        ],
        "algorithm_expected": [
            "read the scoped entities and the version vector in one transaction",
            "canonicalize and hash",
        ],
    },
    "commands": COMMANDS,
    "test_cases": {
        "1": {
            "input": "a concurrent vehicle-capacity update while a snapshot is captured",
            "expected": "a single snapshot that does not mix old and new reads",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation, no tests, and no PostgreSQL; the case also needs two real concurrent connections, which SQLite cannot approximate",
        },
        "2": {
            "input": "an error raised inside the unit of work",
            "expected": "everything rolls back with no half state",
            "status": "NOT_VERIFIABLE",
            "reason": "no implementation, no tests, no database",
        },
        "coverage": "0 of 2 required test cases",
    },
    "acceptance_recheck_plan": {
        "purpose": "what to verify when P03-03 is re-issued after G02 is signed and P03-01/P03-02 land",
        "preconditions": [
            "P03-01 and P03-02 accepted first: snapshots.py must read the tables and ORM mappings they create",
            "an isolated PostgreSQL reachable with TEST_DATABASE_URL exported to a *test*-named database",
            "apps/backend/pyproject.toml + uv.lock permitted to gain sqlalchemy/psycopg/alembic (see D3)",
        ],
        "checks": [
            "test case 1 must be reproduced with TWO real concurrent connections: capture while another transaction commits a vehicle-capacity change, then assert the snapshot holds a single consistent revision vector (no mixed old/new reads). A single connection or SQLite must be rejected as evidence",
            "test case 2: raise inside the unit of work and assert full rollback - no partially written row, no leaked transaction, and the connection usable afterwards",
            "capture() must read entities and the version vector inside ONE transaction at REPEATABLE READ, not across multiple transactions",
            "the snapshot must include matrix and calendar versions, not only entity revisions",
            "the canonical serialization must be deterministic: capture twice from the same state and compare hashes byte for byte",
            "DTOs must map onto pure domain snapshots; a SQLAlchemy model, Session or Result must never appear in the returned type",
            "because D5 leaves this obligation unenforced, the precheck must hand-run the ORM-leak probe itself: grep the backend for ORM imports outside persistence/ and inspect the declared return types",
            "ports/storage.py may only declare Protocols over domain types frozen by P02; if it defines domain types instead, that is a second definition of the domain model (Architecture Constraint 6)",
            "the DSN used in the run must be postgresql, never sqlite",
        ],
    },
    "defects": DEFECTS,
    "fixed_by_zcode": [],
    "unfixed": [d["id"] for d in DEFECTS],
    "not_verified": [
        "Both P03-03 test cases, the capture/commit interfaces, the REPEATABLE READ obligation, the matrix/calendar version inclusion, the canonical hash stability and the ORM-containment rule are UNVERIFIED: nothing was implemented and no database exists",
        "G03 exit criteria (real migration/rollback/FK, consistent snapshot, exactly-one concurrent resource commit, no half version on transaction failure): the 'consistent snapshot' criterion belongs to this very task and currently has no evidence at all",
        "Static type checking: no mypy/pyright configuration exists",
        "npm ci, the frontend workspace test, the Playwright listing and ruff were NOT re-run in this pass; D8/D9/D10 rest on the 2026-09-14 evidence and are flagged reverified_this_pass=false",
        "CI as written cannot run in this checkout (no .git), so its git ls-files / git grep / git diff steps cannot execute as written",
    ],
    "security_review": {
        "scope": "the change set is documentation plus DSH evidence; the eventual deliverable is a snapshot reader and unit of work, so forward-looking controls are stated as requirements, not passes",
        "credential_files": "none found (.env / .env.* / *.pem / *.p12 / id_rsa*) in the target tree",
        "secret_literals": "0 hits for sk-[A-Za-z0-9]{20,} and AKIA[0-9A-Z]{16}",
        "test_database_url_handling": "presence checked only; never echoed, no connection attempted",
        "sql_injection": (
            "no database access code exists yet, so there is nothing to verify. P03-03 is the first task that will issue "
            "queries (snapshot capture) and its two test cases involve concurrent writes; every parameter must be bound, "
            "never interpolated or assembled with format/f-string - a forward-looking requirement, NOT a pass"
        ),
        "command_injection": "no shell=True / os.system / eval / exec / pickle.loads in apps|packages|scripts|tests; runner and conftest use argv arrays; the probe script added this round also starts no process",
        "transaction_safety": "the unit of work is where rollback correctness lives; test case 2 is the project's control for 'no half state', and it has never run",
        "auth_scope_logging": "no HTTP boundary or worker exists yet; belongs to P05-01/P37",
        "dependency_changes": "none in this change set; uv lock --check exit 0",
        "external_targets_scanned": "none - only local tool availability and environment variables were inspected",
        "zcode_own_artifacts": "neither the evidence builder nor the architecture probe starts a subprocess or invokes a shell",
    },
    "tool_versions": {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "python_pin": read_text(".python-version"),
        "node_pin": read_text(".node-version"),
        "node_local_and_g01_fingerprint": fingerprint.get("node"),
        "uv_recorded_in_g01": fingerprint.get("uv"),
        "os": f"{platform.system()} {platform.release()}",
        "note": "uv/node are quoted from the G01 environment fingerprint because these tools start no process",
    },
    "verified_input_hashes": {rel: sha(rel) for rel in VERIFIED_INPUTS},
    "evidence_logs": collect_logs(),
    "evidence_builder": {
        "path": "artifacts/handoffs/P03-03/zcode/build-evidence.py",
        "sha256": sha("artifacts/handoffs/P03-03/zcode/build-evidence.py"),
        "note": "this record's own generator; rerun it from the repository root to rebuild evidence.json and precheck.json",
    },
    "sandbox_gate_evidence": collect_sandbox(),
    "files_added_by_zcode": [
        "docs/handoffs/P03-03/zcode.md",
        "artifacts/handoffs/P03-03/zcode/evidence.json",
        "artifacts/handoffs/P03-03/zcode/precheck.json",
        "artifacts/handoffs/P03-03/zcode/build-evidence.py",
        "artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py",
        "artifacts/handoffs/P03-03/zcode/logs/ (raw command and probe logs)",
        "tmp/zcode-g03-dryrun-p3/ (non-official G03 sandbox evidence, under the gitignored tmp/)",
    ],
    "files_modified_by_zcode": [],
    "preserved_dsh_report": [
        "docs/handoffs/P03-03/dsh.md",
        "artifacts/handoffs/P03-03/dsh/evidence.json",
        "artifacts/handoffs/P03-03/dsh/logs/",
        "docs/implementation/P03-03.md",
        "docs/implementation/reports/P03-03.md",
        "note: none of these was created, rewritten or reformatted by this role; only read and hashed",
    ],
    "signs_gate": False,
    "gate_signed": None,
    "limitations": [
        "This record is BLOCKED on purpose: scripts/gates.py compares status against 'Z_PRECHECK_PASSED' and fails closed. It agrees with DSH's own BLOCKED verdict.",
        "P03-03-cmd2 (check_architecture.py) exit 0 is vacuous, and for this task it cannot cover the task's own architectural obligation (D5).",
        "docs/workflow/README.md and HANDOFF_CONTRACT.md do not exist (ARCH-0004); this record follows the user instruction plus the path hardcoded in scripts/gates.py:305-311.",
        "D8/D9/D10 were not re-executed in this pass because no frontend or lint artifact is in P03-03's scope.",
    ],
    "next_actions": [
        "STOP re-issuing Phase 03 tasks until the barrier is repaired: three tasks have now produced the same BLOCKED record, and each one only adds two documentation rows to the gate's pass count (D7).",
        "ZCode: write the three P01-01..P01-03 precheck records, which are the entire remaining cause of G01 failing (its five acceptance assertions already pass).",
        "Codex: record the G01 codex review, decide the revision-staleness policy (D11) and the ARCH-0004 record-format question; consider accepting BLOCKED as a known handoff status (D6).",
        "Project management: authorise the database dependencies into the workspace lock (D3) and write the Phase 01 environment manual (D4).",
        "Role A / DSH: deliver P02-01..P02-04, assemble G02, then P03-01, P03-02, P03-03 in order.",
        "P01-02: close the ORM-containment coverage gap (D5) before P03-03 is re-issued, otherwise its acceptance criterion 3 stays vacuous for the obligation that matters most.",
    ],
}

out_dir = pathlib.Path("artifacts/handoffs/P03-03/zcode")
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
