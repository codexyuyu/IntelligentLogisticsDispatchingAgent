"""Assemble the P05-03 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P05-03/zcode/build-evidence.py

Reads repository files only; writes evidence.json, an identical precheck.json and a build
log next to itself. Never signs a Gate. Every hash is recomputed here so Codex can rebuild
and diff the record; the gate revision label is asked of the runner itself.

Verdict: BLOCKED. 0 of the 9 code/openapi/test deliverables exist. Both declared
dependencies are unmet (G04 has no gate record; P05-02 is BLOCKED with 0/8, so the router
and composition root do not exist). Two further blockers hold independently: the third
mandatory command cannot pass because scripts/export_contracts.py does not exist, and both
Test Cases are PostgreSQL concurrency semantics with no database, no driver and no HTTP
client available. The job boundary types are also homeless: DATA_CONTRACTS.md:57 assigns
JobRequest/JobRef to this task, but its allow-list contains no contracts module, and
JobKind/LeaseToken/Deadline/WorkOutcome have no frozen definition at all.

Unlike the sibling P05-01/P05-02 records, this DSH record is internally consistent and
accurate about its own documents; that is credited here and is not a defect.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()
TASK, SLUG, PHASE, GATE = "P05-03", "durable-jobs", 5, "G05"
ZDIR = f"artifacts/handoffs/{TASK}/zcode"

# The 11 allow-listed paths (6 modules + openapi.json + 2 documents + 2 tests).
DELIVERABLES = [
    "apps/backend/src/logistics_backend/api/jobs.py",
    "apps/backend/src/logistics_backend/api/router.py",
    "apps/backend/src/logistics_backend/application/jobs.py",
    "apps/backend/src/logistics_backend/bootstrap.py",
    "apps/backend/src/logistics_backend/persistence/jobs.py",
    "apps/backend/src/logistics_backend/worker.py",
    "contracts/openapi.json",
    "tests/unit/test_p05_03_durable_jobs.py",
    "tests/integration/test_p05_03_durable_jobs.py",
    "docs/implementation/P05-03.md",
    "docs/implementation/reports/P05-03.md",
]
VERIFIED_INPUTS = [
    "docs/prompts/04-api/P05-03-durable-jobs.md",
    "docs/api/API_CONTRACT.md",
    "docs/architecture/DATA_CONTRACTS.md",
    "docs/architecture/DOMAIN_CATALOG.md",
    "docs/plan/PHASE_GATES.md",
    "docs/plan/TASK_MANIFEST.json",
    "pyproject.toml",
    "uv.lock",
    "apps/backend/pyproject.toml",
    "tests/conftest.py",
    "artifacts/gates/G00.json",
    "artifacts/gates/G01.json",
    "artifacts/handoffs/P05-01/dsh/evidence.json",
    "artifacts/handoffs/P05-02/dsh/evidence.json",
    "artifacts/handoffs/P05-03/dsh/evidence.json",
    "docs/handoffs/P05-03/dsh.md",
]
MY_LOGS = [
    "cmd1-pytest.log",
    "cmd2-architecture.log",
    "cmd3-export-contracts.log",
    "gates-probe-phase05.log",
    "regression-full-pytest.log",
    "env-probe.log",
]


def sha(rel: str):
    p = root / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def exists(rel: str) -> bool:
    return (root / rel).is_file()


def current_revision() -> str:
    scripts = str(root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import gates

    return gates.GateRunner(root=root, phase=PHASE, revision="auto").compute_revision()


def log_fact(name: str) -> dict:
    rel = f"{ZDIR}/logs/{name}"
    return {"path": rel, "sha256": sha(rel), "bytes": (root / rel).stat().st_size if exists(rel) else None}


def main() -> int:
    (root / ZDIR / "logs").mkdir(parents=True, exist_ok=True)
    presence = {rel: exists(rel) for rel in DELIVERABLES}
    present = sum(presence.values())
    docs = [r for r in DELIVERABLES if r.startswith("docs/")]
    code = [r for r in DELIVERABLES if r not in docs]
    code_present = sum(1 for r in code if presence[r])
    g01 = json.loads((root / "artifacts/gates/G01.json").read_text(encoding="utf-8"))
    dsh = json.loads((root / "artifacts/handoffs/P05-03/dsh/evidence.json").read_text(encoding="utf-8"))
    dsh_rows = len(dsh.get("deliverable_presence") or {})

    record = {
        "schema_version": "1.0.0",
        "task_id": TASK,
        "scene": SLUG,
        "phase": PHASE,
        "phase_gate": GATE,
        "reviewer": "ZCode",
        "review_role": "independent-pre-acceptance",
        "status": "BLOCKED",
        "verdict_reason": (
            "P05-03 has no implementation candidate. All 9 code/openapi/test deliverables are absent: no job API "
            "routes, no JobService application layer, no persistence adapter, no worker, no generated "
            "contracts/openapi.json and no tests. Both declared dependencies are unmet: G04 has no gate record, and "
            "P05-02 is BLOCKED with 0/8 so the api/router.py and bootstrap.py this task must extend do not exist. Two "
            "further blockers hold independently: the third mandatory command 'export_contracts.py --check' cannot "
            "pass because that generator (owned by P02-04) does not exist - this is the third consecutive Phase 05 "
            "round with the same exit-2 root cause - and both Test Cases are PostgreSQL concurrency semantics "
            "(lease expiry after a worker crash, stale-lease write rejection) with no database, no driver in the lock "
            "and no HTTP client available. The job boundary types are also homeless: DATA_CONTRACTS.md:57 assigns "
            "JobRequest/JobRef to this task but the allow-list contains no contracts module, and JobKind, LeaseToken, "
            "Deadline and WorkOutcome have no frozen definition at all (each appears 0 times in the three frozen "
            "contracts). DSH's BLOCKED verdict is independently confirmed; no Gate is signed."
        ),
        "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
        "candidate": {
            "root": str(root),
            "vcs": "no .git in this checkout; located by content hash (scripts/gates.py GateRunner.compute_revision)",
            "revision_label_during_this_review": current_revision(),
            "revision_label_is_self_perturbing": "compute_revision() covers artifacts/handoffs/**, .mimosa/** and tmp/**, "
                                                "including this record's own directory",
            "previous_gate_recorded_revision": g01.get("code_revision"),
            "measured_g05_probe_revision": "content-sha256:c627d42667bf8ee79be6870a067f03d11f9d2420b269561d838d1b0db4f40526",
            "same_root_as_dsh": True,
            "same_candidate_checked": "yes: same working root, same commands, same absent deliverables",
        },
        "deliverable_presence": presence,
        "deliverable_present_count": present,
        "deliverable_expected_count": len(DELIVERABLES),
        "deliverable_present_count_explanation": (
            f"{present} of {len(DELIVERABLES)} allow-listed paths exist and both are documents "
            "(docs/implementation/P05-03.md, docs/implementation/reports/P05-03.md) recording the BLOCKED state. All 9 "
            "code/openapi/test deliverables are absent. The DSH record used a 10-row basis (its own dsh.md and "
            "evidence.json plus these two documents plus the 6 code/test files) and reported 4/10; on its own basis "
            "that is ACCURATE and internally consistent, and this review credits it - in contrast to the sibling "
            "P05-01 and P05-02 records, whose document rows are stale. This review reports on the 11-path allow-list "
            "basis for comparability across the phase."
        ),
        "code_and_test_presence": {r: presence[r] for r in code},
        "code_and_test_present_count": code_present,
        "code_and_test_expected_count": len(code),
        "dsh_record_consistency": {
            "dsh_expected_count": dsh.get("deliverable_expected_count"),
            "dsh_rows": dsh_rows,
            "dsh_present_count": dsh.get("deliverable_present_count"),
            "verdict": "consistent: 10 rows, denominator 10, 4 present, and 4 of those rows exist on disk. The record "
                       "also correctly names the 6 absent files and states why each was deliberately not created.",
            "one_note": "the record asserts presence of its own two documents and of the dsh.md/evidence.json pair at "
                        "write time (00:54:11) before three of them existed (00:54:34/00:54:47/00:54:59); the "
                        "assertion is correct now, so no correction is needed, but the same records are never "
                        "recomputed after the documents are written - the shared process gap behind the P05-01/P05-02 "
                        "staleness",
        },
        "dsh_submission": {
            "record": "artifacts/handoffs/P05-03/dsh/evidence.json",
            "record_sha256": sha("artifacts/handoffs/P05-03/dsh/evidence.json"),
            "handoff": "docs/handoffs/P05-03/dsh.md",
            "handoff_sha256": sha("docs/handoffs/P05-03/dsh.md"),
            "dsh_status": dsh.get("status"),
            "reviewer_agrees_with_status": True,
            "dsh_summary_not_relied_on": "the verdict was re-derived from the filesystem, gate records and re-run "
                                         "commands before the DSH narrative was read",
            "input_hashes_reverified": "28/28 of DSH's input_hashes recomputed byte-identical",
            "output_hashes_reverified": "5/5 of DSH's recorded log hashes recomputed byte-identical",
            "claims_independently_reproduced": [
                "logistics_backend.api/.application/.persistence/.worker/.bootstrap and logistics_domain.jobs / "
                "logistics_contracts.jobs/.dto all ModuleNotFoundError",
                "httpx, psycopg, psycopg2, sqlalchemy, alembic, asyncpg all absent; fastapi 0.141.1, starlette 1.6.0, "
                "pydantic 2.13.5, pytest 9.1.1 present",
                "export_contracts.py --check -> exit 2; contracts/openapi.json and contracts/schemas.json absent",
                "WorkOutcome, JobKind, LeaseToken and Deadline each appear 0 times in DATA_CONTRACTS.md, "
                "DOMAIN_CATALOG.md and API_CONTRACT.md; DATA_CONTRACTS.md:57 does assign JobRequest/JobRef to P05-03",
                "psql/pg_ctl absent, docker daemon unreachable, TEST_DATABASE_URL unset",
                "G05 probe: previous-gate:G04 missing",
            ],
        },
        "dependency_presence": {
            "artifacts/gates/G04.json": exists("artifacts/gates/G04.json"),
            "artifacts/handoffs/P05-02/zcode/precheck.json": exists("artifacts/handoffs/P05-02/zcode/precheck.json"),
            "apps/backend/src/logistics_backend/api/router.py": exists("apps/backend/src/logistics_backend/api/router.py"),
            "apps/backend/src/logistics_backend/bootstrap.py": exists("apps/backend/src/logistics_backend/bootstrap.py"),
            "apps/backend/src/logistics_backend/persistence/__init__.py": exists(
                "apps/backend/src/logistics_backend/persistence/__init__.py"),
        },
        "dependency_present_count": 1,
        "dependency_expected_count": 5,
        "dependency_expected_count_note": (
            "0 of 5 are usable: artifacts/handoffs/P05-02/zcode/precheck.json exists only because this review wrote "
            "it with status=BLOCKED, so it is not a Z_PRECHECK_PASSED; G04.json, api/router.py and bootstrap.py do not "
            "exist, and there is no persistence package at all (the UoW and idempotency store belong to the BLOCKED "
            "P03-03/P03-04)."
        ),
        "prerequisites": {
            "G00": {"recorded_status": "passed", "sha256": sha("artifacts/gates/G00.json"), "verdict": "valid"},
            "G01": {"recorded_status": g01.get("status"), "sha256": sha("artifacts/gates/G01.json"),
                    "failed_checks": g01.get("failed_checks"), "verdict": "invalid (blocking)"},
            "G02": {"record": None, "verdict": "invalid (blocking)"},
            "G03": {"record": None, "verdict": "invalid (blocking): no persistence, no UoW, no migration"},
            "G04": {"record": None, "verdict": "invalid (blocking, declared dependency 1)"},
            "P05-01": {"dsh_status": "BLOCKED", "verdict": "invalid (blocking): router.py and bootstrap.py absent"},
            "P05-02": {"dsh_status": "BLOCKED", "deliverables": "0/8 code/contracts/test",
                       "verdict": "invalid (blocking, declared dependency 2)"},
            "P03-03/P03-04": {"precheck": "BLOCKED", "verdict": "invalid (blocking): SKIP LOCKED claim, heartbeat "
                                                                "renewal and lease expiry all need the missing UoW "
                                                                "and tables"},
            "P02-02/P02-03/P02-04": {"precheck": "BLOCKED", "verdict": "invalid (blocking): the Job entity and its "
                                                                       "status enum"},
        },
        "frozen_interface": {
            "signature": "JobService.submit(request: JobRequest, key: str) -> JobRef; Worker.run_once() -> WorkOutcome",
            "source": "docs/prompts/04-api/P05-03-durable-jobs.md (Interfaces)",
            "assignment_conflict": (
                "DATA_CONTRACTS.md:57 assigns JobRequest / JobRef to P05-03, yet the P05-03 allow-list contains no "
                "packages/contracts or packages/domain module - the only boundary carrier it may touch is "
                "contracts/openapi.json, which the prompt forbids hand-editing"
            ),
            "unfrozen_types": ["JobKind", "LeaseToken", "Deadline", "WorkOutcome"],
            "unfrozen_evidence": "each appears 0 times across DATA_CONTRACTS.md, DOMAIN_CATALOG.md and API_CONTRACT.md; "
                                 "WorkOutcome is a name invented by the task prompt's Interfaces line, not a frozen "
                                 "contract type",
            "contracts_package_hint": "logistics_contracts._PENDING_APIS registers dto/mapping/export_schema (P02-04) "
                                      "and errors (P05-01) only - there is not even a placeholder slot for job DTOs",
            "whitelist_gap": "duplicating the boundary layer here would violate Constraint 6; returning an undefined "
                             "dict would violate Constraint 1",
        },
        "commands": [
            {"id": "cmd1", "mandatory": True,
             "argv": "uv run pytest tests/unit/test_p05_03_durable_jobs.py tests/integration/test_p05_03_durable_jobs.py -q",
             "workdir": str(root), "exit_code": 4,
             "result": "ERROR: file or directory not found; no tests ran in 0.00s (0/0/0/0)",
             "zero_case_run": True, "counts_as_evidence": False, "log": log_fact("cmd1-pytest.log")},
            {"id": "cmd2", "mandatory": True, "argv": "uv run python scripts/check_architecture.py",
             "workdir": str(root), "exit_code": 0,
             "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
             "counts_as_evidence": False, "hollow_pass": True,
             "hollow_pass_reason": "the 7 scanned modules are the unmodified P01-01 placeholder packages; "
                                   "logistics_backend.api, .application, .persistence and .worker do not exist, so the "
                                   "checker cannot evaluate this task's rules (application does not import adapters, "
                                   "the DTO->application->UoW->domain->adapter chain, no long solve inside a request). "
                                   "Byte-identical to the P05-01 and P05-02 runs of the same command.",
             "log": log_fact("cmd2-architecture.log")},
            {"id": "cmd3", "mandatory": True, "argv": "uv run python scripts/export_contracts.py --check",
             "workdir": str(root), "exit_code": 2,
             "result": "can't open file 'scripts/export_contracts.py': [Errno 2] No such file or directory",
             "counts_as_evidence": False,
             "structural": "third consecutive Phase 05 round with this identical root cause; it stays red until "
                           "P02-04 delivers the generator, and hand-writing contracts/openapi.json is forbidden",
             "log": log_fact("cmd3-export-contracts.log")},
            {"id": "cmd4", "mandatory": False,
             "argv": "uv run python scripts/gates.py --phase 05 --revision auto --out-dir tmp/zcode-p05/probe-g05",
             "workdir": str(root), "exit_code": 1,
             "result": "G05: 10/27 checks passed; G04 missing; all three cmd1 checks exit 4; all three cmd3 checks "
                       "exit 2; all three dsh-evidence statuses unexpected; all three zcode-prechecks missing",
             "wrote_official_gate_record": False,
             "count_reconciliation": "DSH recorded 4/27 (P05-01 round), 6/27 (P05-02 round) and 8/27 (P05-03 round); "
                                     "this review measures 10/27. Each +2 increment is exactly the two documents of "
                                     "the previous task becoming present, and the +2 from 8 to 10 is P05-03's own two "
                                     "documents (written at 00:54:47/00:54:59, after its 00:52:46 probe). All the DSH "
                                     "numbers are honest time-point snapshots.",
             "log": log_fact("gates-probe-phase05.log")},
            {"id": "cmd5", "mandatory": False, "argv": "uv run pytest tests/unit tests/integration -q",
             "workdir": str(root), "exit_code": 0,
             "result": "187 passed -- adjacent-module regression baseline, containing no P05-03 test",
             "log": log_fact("regression-full-pytest.log")},
            {"id": "cmd6", "mandatory": False,
             "argv": "environment probe: httpx / DB drivers / missing modules",
             "workdir": str(root), "exit_code": None,
             "result": "no httpx and no DB driver; logistics_backend.api/.application/.persistence/.worker and "
                       "logistics_domain.jobs / logistics_contracts.jobs all ModuleNotFoundError",
             "log": log_fact("env-probe.log")},
        ],
        "phase_appropriate_checks": {
            "uv lock --check": {"exit_code": 0, "result": "Resolved 40 packages"},
            "scripts/check_ownership.py": {"exit_code": 0, "result": "files=1360 rules=60 violations=0"},
            "scripts/gates.py --phase 01 --check-only": {"exit_code": 0,
                                                         "result": "recorded status=failed; 4 records missing; "
                                                                   "gate not signed"},
            "uv run ruff check apps/backend/src packages/*/src tests scripts": {
                "exit_code": 1, "result": "39 errors, all pre-existing in P01 files",
                "attribution": "pre-existing lint debt; ruff is not a mandatory command here"},
            "schema/openapi/generated-client consistency": {
                "status": "NOT RUN - structurally impossible",
                "reason": "no generator and no contracts/openapi.json; no substitute comparison was invented",
            },
        },
        "test_cases": {
            "1: a worker crashes after claiming a job => the lease expires and a second process can re-claim it": {
                "status": "NOT RUN / UNVERIFIED",
                "reason": "no worker, no lease table, no database and no second process",
                "recheck_plan": "on an isolated real PostgreSQL, kill a real worker process mid-claim and have a "
                                "SECOND process re-claim after expiry; a sleep followed by a status flip is not "
                                "evidence",
            },
            "2: a write carrying an old lease => rejected, and the new result is not overwritten": {
                "status": "NOT RUN / UNVERIFIED",
                "reason": "no lease-epoch CAS and no persisted row",
                "recheck_plan": "write with a stale lease epoch and assert rejection AND that the stored row still "
                                "holds the newer result with the newer epoch - inspect the row, not just the return "
                                "code",
            },
        },
        "defects": [
            {"id": "Z-D1", "severity": "blocking (inherited)",
             "title": "Declared dependency G04 has no record and cannot be assembled",
             "evidence": ["artifacts/gates/ holds only G00-checks.log, G00.json, G01.json",
                          "Phase 05 probe: [FAIL] previous-gate:G04: missing",
                          "G01 failed with its 4 records absent; G02/G03 missing; all P03/P04 tasks BLOCKED"],
             "owner": "project management side + P01-03", "fixed_by_zcode": False,
             "reason_not_fixed": "outside this task's whitelist and this reviewer's role"},
            {"id": "Z-D2", "severity": "blocking (dependency)",
             "title": "P05-02 delivered nothing, and the P05-01 files this task must extend do not exist either",
             "evidence": ["P05-02 evidence status=BLOCKED with 0/8 code/contracts/test deliverables",
                          "api/router.py and bootstrap.py absent, so there is no route table to register "
                          "GET /jobs/{id} and POST /jobs/{id}/cancel and no composition root to wire JobService",
                          "creating them here would implement another owner's deliverables and mask integration "
                          "errors - exactly what Out of Scope forbids"],
             "owner": "P05-01 then P05-02 (after the barrier repair)", "fixed_by_zcode": False,
             "reason_not_fixed": "Out of Scope forbids changing another owner's implementation surface"},
            {"id": "Z-D3", "severity": "blocking (contract gap)",
             "title": "JobRequest/JobRef are assigned to this task but have no carrier, and JobKind/LeaseToken/"
                      "Deadline/WorkOutcome are not frozen at all",
             "evidence": ["DATA_CONTRACTS.md:57 assigns JobRequest/JobRef to P05-03",
                          "the P05-03 allow-list contains no packages/contracts or packages/domain module",
                          "JobKind, LeaseToken, Deadline and WorkOutcome each appear 0 times in the three frozen "
                          "contracts; WorkOutcome is coined by the prompt's Interfaces line",
                          "_PENDING_APIS has no slot for job DTOs"],
             "owner": "contract owner (fold into the same decision as ARCH-0006 and the P05-01/P05-02 gaps)",
             "fixed_by_zcode": False,
             "reason_not_fixed": "duplicating the boundary layer violates Constraint 6; a bare dict violates "
                                 "Constraint 1; hand-writing the generated artifact is forbidden"},
            {"id": "Z-D4", "severity": "blocking (dependency)",
             "title": "The third mandatory command has been structurally impossible for three consecutive Phase 05 "
                      "rounds",
             "evidence": ["exit 2, file not found, identical for P05-01 and P05-02",
                          "the manifest lists scripts/export_contracts.py under P02-04 (its owner) and also under "
                          "P05-01, so its ownership is ambiguous in the manifest itself",
                          "contracts/openapi.json does not exist and must not be hand-written"],
             "owner": "P02-04 + plan owner (manifest ambiguity)", "fixed_by_zcode": False,
             "reason_not_fixed": "creating it here would implement another owner's deliverable"},
            {"id": "Z-D5", "severity": "blocking (environment)",
             "title": "No PostgreSQL, no driver and no HTTP client, so both Test Cases are unexecutable",
             "evidence": ["psql/pg_ctl absent, docker daemon unreachable, TEST_DATABASE_URL unset, no psycopg/"
                          "sqlalchemy/alembic/asyncpg in uv.lock",
                          "httpx absent and fastapi.testclient requires httpx2",
                          "tests/conftest.py fails (never skips) without TEST_DATABASE_URL"],
             "owner": "project management side (before G01 is finally signed)", "fixed_by_zcode": False,
             "reason_not_fixed": "uv.lock is a G01 input; adding dependencies would invalidate an existing gate record"},
        ],
        "fixed_by_zcode": [],
        "unfixed": ["Z-D1 (gate barrier)", "Z-D2 (P05-01/P05-02 deliverables)", "Z-D3 (job boundary types)",
                    "Z-D4 (export_contracts.py + manifest ambiguity)", "Z-D5 (PostgreSQL + drivers + httpx)"],
        "not_verified": [
            "Test Case 1 (lease re-claim after a real worker crash) and Test Case 2 (stale-lease write rejected, new "
            "result intact) - not run",
            "the interface JobService.submit(...) / Worker.run_once() - no implementation",
            "HTTP endpoints GET /api/v1/jobs/{id} and POST /api/v1/jobs/{id}/cancel (API_CONTRACT.md:33) - no app, "
            "no router, no client",
            "Business Rules: jobs persisted in PostgreSQL, process concurrency default 1, no heavy solve on FastAPI "
            "BackgroundTasks, lease epoch prevents stale worker write-back",
            "Algorithm: SKIP LOCKED claim, heartbeat renewal, independent-process deadline, cancel flag and terminal "
            "CAS, expired-lease reclamation, retry ceiling",
            "the G05 exit assertions of PHASE_GATES.md:27 - no Phase 05 evidence exists at all",
            "the whole Edge Case table; the cancellation/timeout and stale-lease rows ARE the two Test Cases",
            "Error-code mappings (422/409/503/401/403, INVALID_TRANSITION, UNSUPPORTED) and the typed "
            "TIMEOUT/UNKNOWN/INFEASIBLE semantics for job payloads",
            "Logging events p05_03.started/completed/rejected - never emitted (no code path ran)",
            "Observability: no metrics emitted (honestly 0). DSH also flags that the prompt's metric list is "
            "cross-task (commit_conflicts_total{reason} belongs to P16-03, http_requests_total to P05-01's HTTP "
            "boundary); this review confirms the overlap for the third consecutive Phase 05 task and defers the "
            "wording decision to the prompt owner.",
            "Not applicable: candidate/validated/confirmed states and version_id/parent_version_id/snapshot_hash - "
            "this task produces no schedule plan",
        ],
        "security_review": {
            "credentials_scan": "no credential-looking literal in the P05 documents, DSH records or repository "
                                "sources; no TEST_DATABASE_URL value appears anywhere",
            "authz_surface": "the job endpoints are operator-only per API_CONTRACT.md, but nothing is implemented, so "
                             "there is no authorization code to audit - recorded as not applicable rather than passed",
            "injection_surface": "not applicable yet: no SQL, no shell interpolation, no subprocess and no route "
                                 "exist. The re-issue checklist requires parameter binding for every statement "
                                 "(SKIP LOCKED claim, heartbeat, terminal CAS) with no concatenated/format/f-string "
                                 "SQL, and no unbounded retry loop",
            "log_redaction": "this review's logs contain command output only; no secret, personal data or model "
                             "reasoning was printed or stored",
            "dependency_changes": "uv.lock and apps/backend/pyproject.toml are byte-identical to the state DSH "
                                  "reviewed; uv lock --check exits 0; no dependency was added by this review",
            "known_dependency_vulnerabilities": "no scanner is established in this repository, so no scan is claimed "
                                                "and none was run",
            "unverified_advisories_vs_reproducible": "no reproducible vulnerability found or reproduced; no scanner "
                                                     "output exists to classify",
        },
        "tool_versions": {"python": platform.python_version(),
                          "uv": "0.12.13 (tools/bin/uv.exe; not on PATH)",
                          "os": f"{platform.system()} {platform.release()}",
                          "host_notes": "no httpx, no DB driver, no psql/pg_ctl, docker daemon unreachable, "
                                        "TEST_DATABASE_URL unset; fastapi 0.141.1 / starlette 1.6.0 / pytest 9.1.1 "
                                        "present"},
        "verified_input_hashes": {r: sha(r) for r in VERIFIED_INPUTS},
        "verified_input_hashes_note": "recomputed during this review; every shared key matches DSH's recorded value",
        "evidence_logs": {n: log_fact(n) for n in MY_LOGS},
        "evidence_builder": {"path": f"{ZDIR}/build-evidence.py", "argv": f"python {ZDIR}/build-evidence.py",
                             "rebuildable": "yes: every hash is recomputed from the working tree"},
        "sandbox_gate_evidence": {
            "official_gate_records_written": [],
            "statement": "no Gate was signed and no artifacts/gates file was created or modified; probe output went "
                         "to tmp/zcode-p05",
            "artifacts_gates_listing_after_review": ["G00-checks.log", "G00.json", "G01.json"],
        },
        "files_added_by_zcode": [f"{ZDIR}/build-evidence.py", f"{ZDIR}/evidence.json", f"{ZDIR}/precheck.json",
                                 *[f"{ZDIR}/logs/{n}" for n in MY_LOGS]],
        "files_modified_by_zcode": [],
        "files_modified_by_zcode_note": "no file outside this record's own directory was created or modified; the DSH "
                                        "report and evidence were preserved unmodified and nothing under apps/, "
                                        "contracts/, scripts/, tests/ or artifacts/gates/ was touched",
        "preserved_dsh_report": ["docs/handoffs/P05-03/dsh.md (unmodified)",
                                 "artifacts/handoffs/P05-03/dsh/evidence.json (unmodified; its counts were found "
                                 "consistent)", "artifacts/handoffs/P05-03/dsh/logs/* (5 files, hashes verified)"],
        "signs_gate": False,
        "gate_signed": None,
        "limitations": ["the revision label is a self-perturbing content hash because there is no .git",
                        "no PostgreSQL and no HTTP client are available, so both concurrency Test Cases are blocked "
                        "on this host",
                        "the architecture checker scans 7 placeholder modules; its exit 0 is not acceptance evidence"],
        "next_actions": [
            "repair the barrier first: the 4 Phase 01 records, then the project-level lock/environment decisions "
            "(DB driver, migration tool, HTTP test client, isolated PostgreSQL, TEST_DATABASE_URL, environment manual) "
            "before G01 is finally signed, then P02-01..P02-04 and G02, then G03, then P04-01/P04-02 and G04",
            "deliver and pre-accept P05-01, then P05-02, before re-issuing P05-03",
            "decide the job boundary-type ownership (JobRequest/JobRef carrier plus JobKind/LeaseToken/Deadline/"
            "WorkOutcome definitions) together with ARCH-0006 and the P05-01/P05-02 gap; four tasks have now hit the "
            "same 'named as owner but no legal carrier' pattern, which argues for one architectural decision "
            "instead of per-task records",
            "adjudicate the cross-task Observability metric lists carried by three consecutive Phase 05 prompts",
            "at pre-acceptance, kill a real worker process and prove a second process re-claims the lease, then "
            "prove a stale lease epoch cannot overwrite the newer result by inspecting the persisted row",
        ],
        "reviewer_verdict_line": "ZCode: BLOCKED -- 0/9 code/openapi/test deliverables, G04 and P05-02 unmet, job "
                                 "boundary types homeless, cmd3 impossible for a third round, no PostgreSQL; DSH "
                                 "verdict confirmed and its record found consistent; no Gate signed",
    }

    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    (root / ZDIR / "evidence.json").write_text(payload, encoding="utf-8")
    (root / ZDIR / "precheck.json").write_text(payload, encoding="utf-8")
    print(f"wrote {ZDIR}/evidence.json and precheck.json (status={record['status']})")
    print(f"deliverables present {present}/{len(DELIVERABLES)}; code/openapi/test {code_present}/{len(code)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
