"""Assemble the P05-01 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P05-01/zcode/build-evidence.py

Reads repository files only; writes evidence.json, an identical precheck.json and a build
log next to itself. Never signs a Gate, never writes into the task's implementation paths.
Every hash is recomputed here so Codex can rebuild and diff the record. The gate revision
label is asked of the runner itself, never transcribed by hand.

Verdict: BLOCKED. 0 of the 9 code/openapi/test deliverables exist; the only declared
dependency G04 has no gate record; the boundary types the composition root must expose
have no frozen owner and no whitelisted carrier; and the third mandatory command cannot
pass because scripts/export_contracts.py (owned by P02-04) does not exist.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()
TASK, SLUG, PHASE, GATE = "P05-01", "api-composition", 5, "G05"
ZDIR = f"artifacts/handoffs/{TASK}/zcode"

# allow_files: 7 created files + 2 documents + 2 tests.
DELIVERABLES = [
    "apps/backend/src/logistics_backend/api/dependencies.py",
    "apps/backend/src/logistics_backend/api/errors.py",
    "apps/backend/src/logistics_backend/api/router.py",
    "apps/backend/src/logistics_backend/bootstrap.py",
    "apps/backend/src/logistics_backend/main.py",
    "contracts/openapi.json",
    "scripts/export_contracts.py",
    "tests/unit/test_p05_01_api_composition.py",
    "tests/integration/test_p05_01_api_composition.py",
    "docs/implementation/P05-01.md",
    "docs/implementation/reports/P05-01.md",
]
VERIFIED_INPUTS = [
    "docs/prompts/04-api/P05-01-api-composition.md",
    "docs/api/API_CONTRACT.md",
    "docs/architecture/DATA_CONTRACTS.md",
    "docs/architecture/DOMAIN_CATALOG.md",
    "docs/plan/PHASE_GATES.md",
    "docs/plan/TASK_MANIFEST.json",
    "docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md",
    "contracts/README.md",
    "contracts/changes/README.md",
    "pyproject.toml",
    "uv.lock",
    "apps/backend/pyproject.toml",
    "tests/conftest.py",
    "artifacts/gates/G00.json",
    "artifacts/gates/G01.json",
    "artifacts/handoffs/P04-01/dsh/evidence.json",
    "artifacts/handoffs/P04-02/dsh/evidence.json",
    "artifacts/handoffs/P04-01/zcode/precheck.json",
    "artifacts/handoffs/P04-02/zcode/precheck.json",
    "artifacts/handoffs/P05-01/dsh/evidence.json",
    "docs/handoffs/P05-01/dsh.md",
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
    dsh = json.loads((root / "artifacts/handoffs/P05-01/dsh/evidence.json").read_text(encoding="utf-8"))

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
            "P05-01 has no implementation candidate. All 9 code/openapi/test deliverables are absent: no app "
            "factory, no composition root, no router, no error protocol, no auth dependency, no contracts/openapi.json "
            "and no tests. The only declared dependency G04 has no gate record and cannot be assembled (G01 failed, "
            "G02/G03 missing, both P04 tasks BLOCKED). Three independent structural blockers hold even if G04 were "
            "signed: (1) the boundary types the composition root must expose - Settings, ActorContext, ErrorEnvelope, "
            "HealthResponse - have no frozen owner and no whitelisted carrier module, while logistics_contracts raises "
            "NotImplementedError for dto/errors/export_schema; (2) the third mandatory command "
            "'export_contracts.py --check' cannot pass because that script does not exist (it is owned by P02-04, and "
            "hand-writing contracts/openapi.json is forbidden); (3) there is no HTTP test client - httpx is absent and "
            "starlette.testclient aborts with a RuntimeError asking for httpx2 - so neither Test Case can be asserted "
            "on a real ASGI boundary. DSH's BLOCKED verdict is independently confirmed; no Gate is signed."
        ),
        "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
        "candidate": {
            "root": str(root),
            "vcs": "no .git in this checkout; located by content hash (scripts/gates.py GateRunner.compute_revision)",
            "revision_label_during_this_review": current_revision(),
            "revision_label_is_self_perturbing": "compute_revision() covers artifacts/handoffs/**, .mimosa/** and tmp/**, "
                                                "including this record's own directory, so the label moves when the "
                                                "record is written",
            "previous_gate_recorded_revision": g01.get("code_revision"),
            "measured_g05_probe_revision": "content-sha256:c627d42667bf8ee79be6870a067f03d11f9d2420b269561d838d1b0db4f40526",
            "same_root_as_dsh": True,
            "same_candidate_checked": "yes: same working root, same commands, same absent deliverables; there is no "
                                      "implementation candidate for either agent to review",
        },
        "deliverable_presence": presence,
        "deliverable_present_count": present,
        "deliverable_expected_count": len(DELIVERABLES),
        "deliverable_present_count_explanation": (
            f"{present} of {len(DELIVERABLES)} exist and both are documents (docs/implementation/P05-01.md, "
            "docs/implementation/reports/P05-01.md) that record the BLOCKED state. All 9 code/openapi/test deliverables "
            "are absent. This CORRECTS the DSH record, which reports 0/11 with both documents marked absent: at its "
            "write time (21:56:15) the two documents did not yet exist (they were written at 21:56:36 and 21:56:57), so "
            "the rows were true then and are stale now. The substantive figure is unchanged: 0 of 9 real deliverables."
        ),
        "code_and_test_presence": {r: presence[r] for r in code},
        "code_and_test_present_count": code_present,
        "code_and_test_expected_count": len(code),
        "dsh_submission": {
            "record": "artifacts/handoffs/P05-01/dsh/evidence.json",
            "record_sha256": sha("artifacts/handoffs/P05-01/dsh/evidence.json"),
            "handoff": "docs/handoffs/P05-01/dsh.md",
            "handoff_sha256": sha("docs/handoffs/P05-01/dsh.md"),
            "dsh_status": dsh.get("status"),
            "reviewer_agrees_with_status": True,
            "dsh_summary_not_relied_on": "the verdict was re-derived from the filesystem, gate records and re-run "
                                         "commands before the DSH narrative was read for reconciliation",
            "input_hashes_reverified": "25/25 of DSH's input_hashes recomputed byte-identical",
            "output_hashes_reverified": "4/4 of DSH's recorded log hashes recomputed byte-identical",
            "claims_independently_reproduced": [
                "artifacts/gates/ holds only G00-checks.log, G00.json, G01.json (no G02/G03/G04)",
                "contracts/ contains only README.md and changes/README.md",
                "scripts/ contains only check_architecture.py, check_ownership.py, gates.py (no export_contracts.py)",
                "httpx import fails; fastapi.testclient raises RuntimeError requiring httpx2, while fastapi 0.141.1 and "
                "starlette 1.6.0 are installed",
                "logistics_contracts exposes _PENDING_APIS = {dto, mapping, export_schema, errors}; dto/errors/"
                "export_schema raise NotImplementedError and an unknown name raises AttributeError",
                "only the 7 P01-01 placeholder __init__.py files exist under apps/ and packages/",
            ],
        },
        "dependency_presence": {
            "artifacts/gates/G04.json": exists("artifacts/gates/G04.json"),
            "artifacts/handoffs/P04-01/zcode/precheck.json": exists("artifacts/handoffs/P04-01/zcode/precheck.json"),
            "artifacts/handoffs/P04-02/zcode/precheck.json": exists("artifacts/handoffs/P04-02/zcode/precheck.json"),
            "apps/backend/src/logistics_backend/bootstrap.py": exists("apps/backend/src/logistics_backend/bootstrap.py"),
        },
        "dependency_present_count": 2,
        "dependency_expected_count": 4,
        "dependency_expected_count_note": (
            "0 of 4 are usable. The two P04 precheck records now exist because the P04 review wrote them, but both "
            "carry status=BLOCKED, so neither is a Z_PRECHECK_PASSED and neither satisfies the dependency; "
            "artifacts/gates/G04.json and bootstrap.py do not exist."
        ),
        "prerequisites": {
            "G00": {"recorded_status": "passed", "sha256": sha("artifacts/gates/G00.json"), "verdict": "valid"},
            "G01": {"recorded_status": g01.get("status"), "sha256": sha("artifacts/gates/G01.json"),
                    "failed_checks": g01.get("failed_checks"),
                    "verdict": "invalid (blocking): the failed set is the 3 Phase 01 prechecks plus the Codex review"},
            "G02": {"record": None, "verdict": "invalid (blocking)"},
            "G03": {"record": None, "verdict": "invalid (blocking)"},
            "G04": {"record": None, "verdict": "invalid (blocking, the only declared dependency): no "
                                               "artifacts/gates/G04.json exists; my Phase 05 probe reports "
                                               "[FAIL] previous-gate:G04 missing"},
            "P04-01": {"dsh_status": "BLOCKED", "fixtures": "0/4", "verdict": "invalid (blocking)"},
            "P04-02": {"dsh_status": "BLOCKED", "verdict": "invalid (blocking)"},
            "P02-04": {"precheck": "BLOCKED", "verdict": "invalid (blocking): owns the DTO layer and "
                                                         "scripts/export_contracts.py"},
            "P03-03/P03-04": {"precheck": "BLOCKED", "verdict": "invalid (blocking): the persistence stack Test "
                                                                "Case 2's ready probe needs"},
        },
        "frozen_interface": {
            "signature": "create_app(settings: Settings) -> FastAPI; GET /api/v1/health -> HealthResponse",
            "source": "docs/prompts/04-api/P05-01-api-composition.md (Interfaces)",
            "unowned_types": ["Settings", "ActorContext", "ErrorEnvelope", "HealthResponse"],
            "ownership_evidence": (
                "DATA_CONTRACTS.md's named Schema table has no row for any of the four; logistics_contracts raises "
                "NotImplementedError for dto/errors/export_schema and its _PENDING_APIS maps 'errors' to P05-01 but "
                "offers no carrier module inside this task's whitelist. Defining them here would duplicate the "
                "boundary layer (Constraint 6); returning an undefined dict would violate Constraint 1."
            ),
            "whitelist_gap": "the allow-list contains no packages/contracts or packages/domain module",
        },
        "commands": [
            {"id": "cmd1", "mandatory": True,
             "argv": "uv run pytest tests/unit/test_p05_01_api_composition.py tests/integration/test_p05_01_api_composition.py -q",
             "workdir": str(root), "exit_code": 4,
             "result": "ERROR: file or directory not found; no tests ran in 0.00s (0/0/0/0)",
             "zero_case_run": True, "counts_as_evidence": False, "log": log_fact("cmd1-pytest.log")},
            {"id": "cmd2", "mandatory": True, "argv": "uv run python scripts/check_architecture.py",
             "workdir": str(root), "exit_code": 0,
             "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
             "counts_as_evidence": False, "hollow_pass": True,
             "hollow_pass_reason": "the 7 scanned modules are the unmodified P01-01 placeholder packages; "
                                   "logistics_backend.api and bootstrap.py do not exist, so the checker cannot "
                                   "evaluate this task's rules ('only bootstrap assembles adapters', 'api does not "
                                   "import OR-Tools')",
             "log": log_fact("cmd2-architecture.log")},
            {"id": "cmd3", "mandatory": True, "argv": "uv run python scripts/export_contracts.py --check",
             "workdir": str(root), "exit_code": 2,
             "result": "can't open file 'scripts/export_contracts.py': [Errno 2] No such file or directory",
             "counts_as_evidence": False,
             "structural": "cannot pass until P02-04 delivers the generator; contracts/openapi.json must be produced "
                           "by that generator and must not be hand-written",
             "log": log_fact("cmd3-export-contracts.log")},
            {"id": "cmd4", "mandatory": False,
             "argv": "uv run python scripts/gates.py --phase 05 --revision auto --out-dir tmp/zcode-p05/probe-g05",
             "workdir": str(root), "exit_code": 1,
             "result": "G05: 10/27 checks passed; G04 missing; all three cmd1 checks exit 4; all three cmd3 checks "
                       "exit 2; all three dsh-evidence statuses unexpected; all three zcode-prechecks missing; "
                       "codex-review missing",
             "wrote_official_gate_record": False,
             "log": log_fact("gates-probe-phase05.log")},
            {"id": "cmd5", "mandatory": False, "argv": "uv run pytest tests/unit tests/integration -q",
             "workdir": str(root), "exit_code": 0,
             "result": "187 passed -- adjacent-module regression baseline, containing no P05-01 test",
             "log": log_fact("regression-full-pytest.log")},
            {"id": "cmd6", "mandatory": False,
             "argv": "environment probe: httpx/psycopg/sqlalchemy/alembic and fastapi.testclient",
             "workdir": str(root), "exit_code": None,
             "result": "httpx, psycopg, psycopg2, sqlalchemy, alembic, asyncpg all ModuleNotFoundError; "
                       "fastapi 0.141.1 / starlette 1.6.0 / pydantic 2.13.5 / pytest 9.1.1 present; "
                       "TestClient raises RuntimeError requiring httpx2",
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
                "attribution": "pre-existing lint debt, unchanged by Phase 05; ruff is not a mandatory command here "
                               "and is not part of ci.yml"},
            "schema/openapi/generated-client consistency": {
                "status": "NOT RUN - structurally impossible",
                "reason": "contracts/openapi.json and its generator scripts/export_contracts.py do not exist; the "
                          "generated-client drift check cannot be performed and no substitute was invented",
            },
        },
        "test_cases": {
            "1: unauthenticated request to a protected write endpoint => 401": {
                "status": "NOT RUN / UNVERIFIED",
                "reason": "no app, no protected route, no HTTP test client",
                "recheck_plan": "drive a real ASGI request with genuinely absent credentials and assert the 401 plus "
                                "the ErrorEnvelope code/trace_id/retryable fields - never a hard-coded status",
            },
            "2: database unavailable => ready=503 and live=200": {
                "status": "NOT RUN / UNVERIFIED",
                "reason": "no app and no health endpoints; no persistence layer",
                "recheck_plan": "the 503 branch can be proven with an unreachable DSN, but proving that ready returns "
                                "200 when the database IS reachable needs a real isolated PostgreSQL; assert BOTH "
                                "directions so the split is real rather than a constant",
                "refinement": "DSH's handoff states this case needs a real PostgreSQL outright; strictly, only the "
                              "positive direction does - the negative direction needs an unreachable DSN. Recorded "
                              "as a precision note, not a defect against DSH.",
            },
        },
        "defects": [
            {"id": "Z-D1", "severity": "blocking (inherited)",
             "title": "The only declared dependency G04 has no record and cannot be assembled",
             "evidence": ["artifacts/gates/ holds only G00-checks.log, G00.json, G01.json",
                          "Phase 05 probe: [FAIL] previous-gate:G04: missing artifacts/gates/G04.json",
                          "G01 status=failed with failed_checks = 3 Phase 01 prechecks + codex-review, all still absent",
                          "G02/G03 have no record; P03-01..P03-04 and P04-01/P04-02 are all BLOCKED"],
             "owner": "project management side + P01-03 (docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md)",
             "fixed_by_zcode": False,
             "reason_not_fixed": "outside this task's whitelist and this reviewer's role"},
            {"id": "Z-D2", "severity": "blocking (contract gap)",
             "title": "Settings / ActorContext / ErrorEnvelope / HealthResponse have no frozen owner and no carrier",
             "evidence": ["DATA_CONTRACTS.md's named Schema table has no row for any of the four",
                          "logistics_contracts._PENDING_APIS = {dto, mapping, export_schema, errors}; the first three "
                          "raise NotImplementedError and are assigned to the BLOCKED P02-04",
                          "the P05-01 allow-list contains no contracts/domain module",
                          "the task prompt's Interfaces line requires Settings and HealthResponse by name"],
             "owner": "contract owner (fold into the same decision as ARCH-0006 and the P05-02/P05-03 gaps)",
             "fixed_by_zcode": False,
             "reason_not_fixed": "defining them here would duplicate the boundary layer (Constraint 6)"},
            {"id": "Z-D3", "severity": "blocking (dependency)",
             "title": "The third mandatory command cannot pass because scripts/export_contracts.py does not exist",
             "evidence": ["uv run python scripts/export_contracts.py --check -> exit 2, file not found",
                          "TASK_MANIFEST.json lists scripts/export_contracts.py in BOTH P02-04's files and P05-01's "
                          "files, while P02-04 is the task that owns the generator; contracts/openapi.json does not "
                          "exist either",
                          "the prompt forbids hand-editing contracts/*.json"],
             "owner": "P02-04 (delivers the generator); manifest ambiguity to be resolved by the plan owner",
             "fixed_by_zcode": False,
             "reason_not_fixed": "creating it here would implement another owner's deliverable and would conflict "
                                 "with P02-04; hand-writing the JSON is explicitly forbidden",
             "new_finding": "the same script appears in two tasks' `files` lists, so its ownership is ambiguous in "
                            "the manifest itself - a plan-level defect worth fixing before re-issue"},
            {"id": "Z-D4", "severity": "blocking (test infrastructure)",
             "title": "No HTTP test client is installed, so neither Test Case can be asserted on a real ASGI boundary",
             "evidence": ["import httpx -> ModuleNotFoundError",
                          "fastapi.testclient -> RuntimeError: The starlette.testclient module requires the httpx2 "
                          "package to be installed",
                          "fastapi 0.141.1 and starlette 1.6.0 themselves are present"],
             "owner": "project management side (must be added to the lock before G01 is finally signed)",
             "fixed_by_zcode": False,
             "reason_not_fixed": "uv.lock is a G01 input; adding a dependency would invalidate an existing gate record"},
            {"id": "Z-D5", "severity": "medium (evidence accuracy; does not change the verdict)",
             "title": "The DSH record reports its two existing documents as absent",
             "evidence": ["deliverable_presence marks docs/implementation/P05-01.md and "
                          "docs/implementation/reports/P05-01.md as false, and the note says 'None exist'",
                          "both files exist (9861 B and 14921 B) and my G05 probe passes both docs checks",
                          "their mtimes (21:56:36 and 21:56:57) are LATER than the record's mtime (21:56:15), so the "
                          "rows were true when written and are stale now - the record was never recomputed after the "
                          "documents were written",
                          "the note additionally describes the implementation doc and report as 'its own handoff "
                          "documentation ... deliberately NOT counted', although it lists them as two of the 11 "
                          "counted rows - an internal inconsistency"],
             "correction": "the current truth is 2/11 allow-listed paths present (both documentation) and 0/9 "
                           "code/openapi/test deliverables",
             "owner": "DSH", "fixed_by_zcode": False,
             "reason_not_fixed": "another agent's evidence record is part of the audit trail and is preserved "
                                 "unmodified; the correction is recorded here for Codex"},
        ],
        "fixed_by_zcode": [],
        "unfixed": ["Z-D1 (gate barrier)", "Z-D2 (boundary-type ownership)", "Z-D3 (export_contracts.py + manifest "
                    "ambiguity)", "Z-D4 (httpx test client)", "Z-D5 (DSH record staleness)"],
        "not_verified": [
            "Test Case 1 (unauthenticated write => 401) and Test Case 2 (DB down => ready=503 / live=200) - not run",
            "the interface create_app(settings: Settings) -> FastAPI and GET /api/v1/health - no implementation",
            "the ErrorEnvelope protocol and its 422/409/503/401/403/INVALID_TRANSITION/UNSUPPORTED mapping",
            "auth (viewer/operator), the body-size limit middleware, trace_id propagation, lifespan connection "
            "management and the ready/live split",
            "Business Rules: only bootstrap assembles adapters; the API layer does not import OR-Tools; dev mode "
            "binds to localhost only",
            "the G05 exit assertions of PHASE_GATES.md:27 - no evidence at all for Phase 05",
            "the whole Edge Case table",
            "Observability: no metrics are emitted (honestly 0). DSH also flags that the prompt's metric list is "
            "cross-task (job_queue_wait_seconds / job_lease_expirations_total belong to P05-03, "
            "commit_conflicts_total{reason} to P16-03); this review confirms the overlap and defers the wording "
            "decision to the prompt owner rather than inventing metrics.",
            "Not applicable: candidate/validated/confirmed states, version_id/parent_version_id/snapshot_hash and the "
            "solver TIMEOUT/UNKNOWN/INFEASIBLE semantics - this task produces no schedule plan",
        ],
        "security_review": {
            "credentials_scan": "no credential-looking literal in the P05 documents, DSH records or repository "
                                "sources; no TEST_DATABASE_URL value appears anywhere (the variable name only, and it "
                                "is unset in this environment)",
            "authn_surface": "the task's central acceptance item is authentication (401 without credentials), but "
                             "nothing is implemented, so there is no authn code to audit - recorded as not "
                             "applicable rather than passed",
            "injection_surface": "not applicable: no SQL, no shell interpolation, no subprocess, no route exists",
            "log_redaction": "this review's logs contain command output only; no secret, personal data or model "
                             "reasoning was printed or stored",
            "dependency_changes": "uv.lock and apps/backend/pyproject.toml are byte-identical to the state DSH "
                                  "reviewed; uv lock --check exits 0; no dependency was added by this review",
            "known_dependency_vulnerabilities": "no scanner is established in this repository (ci.yml has no "
                                                "pip-audit/npm audit step), so no scan is claimed; recorded as "
                                                "not-run rather than clean",
            "unverified_advisories_vs_reproducible": "no reproducible vulnerability found or reproduced; no scanner "
                                                     "output exists to classify as an unverified advisory",
        },
        "tool_versions": {
            "python": platform.python_version(),
            "uv": "0.12.13 (tools/bin/uv.exe; uv is not on PATH on this host)",
            "os": f"{platform.system()} {platform.release()}",
            "host_notes": "httpx/psycopg/sqlalchemy/alembic/asyncpg absent; fastapi 0.141.1, starlette 1.6.0, "
                          "pydantic 2.13.5, pytest 9.1.1 present; no psql/pg_ctl; docker daemon unreachable; "
                          "TEST_DATABASE_URL unset",
        },
        "verified_input_hashes": {r: sha(r) for r in VERIFIED_INPUTS},
        "verified_input_hashes_note": "recomputed during this review; every shared key matches DSH's recorded value "
                                      "byte-for-byte",
        "evidence_logs": {n: log_fact(n) for n in MY_LOGS},
        "evidence_builder": {"path": f"{ZDIR}/build-evidence.py", "argv": f"python {ZDIR}/build-evidence.py",
                             "rebuildable": "yes: every hash is recomputed from the working tree"},
        "sandbox_gate_evidence": {
            "official_gate_records_written": [],
            "statement": "no Gate was signed, no artifacts/gates file was created or modified; probe output went to "
                         "tmp/zcode-p05 (gitignored scratch)",
            "artifacts_gates_listing_after_review": ["G00-checks.log", "G00.json", "G01.json"],
        },
        "files_added_by_zcode": [f"{ZDIR}/build-evidence.py", f"{ZDIR}/evidence.json", f"{ZDIR}/precheck.json",
                                 *[f"{ZDIR}/logs/{n}" for n in MY_LOGS], "tmp/zcode-p05/"],
        "files_modified_by_zcode": [],
        "files_modified_by_zcode_note": "no file outside this record's own directory was created or modified; the DSH "
                                        "report and evidence were preserved unmodified and nothing under apps/, "
                                        "contracts/, scripts/, tests/ or artifacts/gates/ was touched",
        "preserved_dsh_report": ["docs/handoffs/P05-01/dsh.md (unmodified)",
                                 "artifacts/handoffs/P05-01/dsh/evidence.json (unmodified, including the stale rows "
                                 "of Z-D5)", "artifacts/handoffs/P05-01/dsh/logs/* (4 files, hashes verified)"],
        "signs_gate": False,
        "gate_signed": None,
        "limitations": ["the revision label is a self-perturbing content hash because there is no .git",
                        "no HTTP test client and no PostgreSQL are available, so the two Test Cases cannot be "
                        "executed on this host at all",
                        "the architecture checker scans 7 placeholder modules; its exit 0 is not acceptance evidence"],
        "next_actions": [
            "repair the barrier before re-issuing any Phase 05 task: the 4 Phase 01 records, then the project-level "
            "lock/environment decisions (DB driver, migration tool, HTTP test client, isolated PostgreSQL, "
            "TEST_DATABASE_URL, environment manual) all before G01 is finally signed",
            "deliver P02-01..P02-04 (P02-04 also supplies scripts/export_contracts.py and the DTO layer), then sign "
            "G02, then G03, then re-issue the P04 tasks and sign G04",
            "resolve the manifest ambiguity where scripts/export_contracts.py appears in both P02-04's and P05-01's "
            "files lists",
            "decide the boundary-type ownership for Settings/ActorContext/ErrorEnvelope/HealthResponse together with "
            "ARCH-0006 and the P05-02/P05-03 gaps",
            "re-issue P05-01 only after that; at pre-acceptance, drive real ASGI requests for the 401 and assert both "
            "directions of the ready/live split, and require contracts/openapi.json to be generator-produced and "
            "byte-stable",
        ],
        "reviewer_verdict_line": "ZCode: BLOCKED -- 0/9 code/openapi/test deliverables, G04 missing, boundary types "
                                 "unowned, cmd3 structurally impossible; DSH verdict confirmed and its record "
                                 "corrected to 2/11; no Gate signed",
    }

    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    (root / ZDIR / "evidence.json").write_text(payload, encoding="utf-8")
    (root / ZDIR / "precheck.json").write_text(payload, encoding="utf-8")
    print(f"wrote {ZDIR}/evidence.json and precheck.json (status={record['status']})")
    print(f"deliverables present {present}/{len(DELIVERABLES)}; code/openapi/test {code_present}/{len(code)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
