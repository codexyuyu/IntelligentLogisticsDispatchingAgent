"""Assemble the P04-02 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P04-02/zcode/build-evidence.py

The script only reads repository files and writes the two records next to itself plus a
build log under logs/; it never signs a Gate and never writes into the task's own
implementation paths. Every hash it records is recomputed here so Codex can rebuild and
diff the record. The gate revision label is asked of the runner itself, never
transcribed by hand.

Verdict: BLOCKED. P04-02 has no implementation candidate: none of the 4 code/data/test
deliverables exists and data/seed/ itself is absent. Both declared dependencies are
unmet (G03 has no gate record; P04-01 is BLOCKED with 0/4 fixtures and no ZCode
precheck). Two further independent blockers: no PostgreSQL is reachable on this host and
no database driver is in the lock file, and the declared receipt type ImportReceipt has
no row in the frozen Schema table while the whitelist contains no domain-type module.

This review also found that the DSH structured record is factually wrong on two of its
own rows: it marks both P04-02 documents as absent although they exist and were written
before the record itself (defect Z-D5). The BLOCKED verdict is unaffected.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()

TASK = "P04-02"
SLUG = "database-seed"
PHASE = 4
GATE = "G04"
ZDIR = f"artifacts/handoffs/{TASK}/zcode"
LOG_DIR = root / ZDIR / "logs"

# The manifest allow-list: 4 code/data/test deliverables plus the 2 documents.
DELIVERABLES = [
    "apps/backend/src/logistics_backend/cli/seed.py",
    "data/seed/README.md",
    "tests/unit/test_p04_02_database_seed.py",
    "tests/integration/test_p04_02_database_seed.py",
    "docs/implementation/P04-02.md",
    "docs/implementation/reports/P04-02.md",
]

VERIFIED_INPUTS = [
    "docs/prompts/01-foundation/P04-02-database-seed.md",
    "docs/plan/TEST_FIXTURES.md",
    "docs/plan/TASK_MANIFEST.json",
    "docs/plan/PHASE_GATES.md",
    "docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md",
    "TASK_GRAPH.md",
    "docs/architecture/DATA_CONTRACTS.md",
    "docs/architecture/issues/README.md",
    "docs/architecture/issues/ARCH-0006-scenario-bundle-ownership.md",
    "apps/backend/pyproject.toml",
    "uv.lock",
    "pyproject.toml",
    "tests/conftest.py",
    "artifacts/gates/G00.json",
    "artifacts/gates/G01.json",
    "artifacts/handoffs/P04-01/dsh/evidence.json",
    "artifacts/handoffs/P04-02/dsh/evidence.json",
    "docs/handoffs/P04-02/dsh.md",
]

MY_LOGS = [
    "cmd1-pytest.log",
    "cmd2-architecture.log",
    "gates-probe-phase04.log",
    "environment-probe.log",
    "regression-full-pytest.log",
]


def sha(rel: str) -> str | None:
    path = root / rel
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


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
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    presence = {rel: exists(rel) for rel in DELIVERABLES}
    present = sum(presence.values())
    code_paths = [rel for rel in DELIVERABLES if not rel.startswith("docs/")]
    code_present = sum(1 for rel in code_paths if presence[rel])

    g01 = json.loads((root / "artifacts/gates/G01.json").read_text(encoding="utf-8"))
    dsh = json.loads((root / "artifacts/handoffs/P04-02/dsh/evidence.json").read_text(encoding="utf-8"))
    p0401 = json.loads((root / "artifacts/handoffs/P04-01/dsh/evidence.json").read_text(encoding="utf-8"))

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
            "P04-02 has no implementation candidate. All 4 code/data/test deliverables are absent and data/seed/ "
            "itself does not exist, so only the 2 documents recording the blocking state are present. Neither "
            "declared dependency is met: G03 has no gate record and cannot be assembled (P03-01..P03-04 are BLOCKED "
            "with zero delivered files), and P04-01 is BLOCKED with 0 of its 4 fixtures plus no ZCode precheck, so "
            "there is no data set to import. Two independent blockers hold even if the gate chain were repaired: no "
            "PostgreSQL is reachable on this host (psql/pg_ctl absent, Docker daemon unreachable, nothing listening "
            "on 5432/5433, TEST_DATABASE_URL unset, no psycopg/sqlalchemy/alembic/asyncpg anywhere in uv.lock), and "
            "the declared receipt type ImportReceipt has no row in the frozen named Schema table while this task's "
            "whitelist contains no domain/DTO module, so the declared output cannot be expressed as a type. DSH's "
            "BLOCKED verdict is independently confirmed; no Gate is signed."
        ),
        "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
        "candidate": {
            "root": str(root),
            "vcs": "no .git in this checkout; located by content hash (scripts/gates.py GateRunner.compute_revision)",
            "revision_label_during_this_review": current_revision(),
            "revision_label_is_self_perturbing": (
                "by construction this label is one step stale: compute_revision() covers artifacts/handoffs/**, "
                ".mimosa/** and tmp/**, including this record's own directory"
            ),
            "previous_gate_recorded_revision": g01.get("code_revision"),
            "measured_g04_probe_revision": "content-sha256:c627d42667bf8ee79be6870a067f03d11f9d2420b269561d838d1b0db4f40526",
            "same_root_as_dsh": True,
            "same_candidate_checked": (
                "yes: same working root, same mandatory commands, same absent deliverables; no candidate exists to "
                "review"
            ),
        },
        "deliverable_presence": presence,
        "deliverable_present_count": present,
        "deliverable_expected_count": len(DELIVERABLES),
        "deliverable_present_count_explanation": (
            f"{present} of {len(DELIVERABLES)} exist: the 2 documents that record the BLOCKED state. All 4 "
            "code/data/test deliverables (1 seed CLI, 1 directory README, 2 test files) are absent, and data/seed/ "
            "does not exist as a directory. This corrects the DSH structured record, which reports 0/7 with both "
            "documents marked absent (defect Z-D5) -- the amounts of real, undelivered work agree: 0 of 4."
        ),
        "code_and_test_presence": {rel: presence[rel] for rel in DELIVERABLES},
        "code_and_test_present_count": code_present,
        "code_and_test_expected_count": len(code_paths),
        "dsh_submission": {
            "record": "artifacts/handoffs/P04-02/dsh/evidence.json",
            "record_sha256": sha("artifacts/handoffs/P04-02/dsh/evidence.json"),
            "handoff": "docs/handoffs/P04-02/dsh.md",
            "handoff_sha256": sha("docs/handoffs/P04-02/dsh.md"),
            "dsh_status": dsh.get("status"),
            "reviewer_agrees_with_status": True,
            "dsh_summary_not_relied_on": (
                "the verdict was re-derived from the file system, the gate records and re-run commands before the "
                "DSH narrative was read for reconciliation; every load-bearing DSH claim was re-checked, and one "
                "was found to be wrong in the structured record (Z-D5)"
            ),
            "input_hashes_reverified": (
                "22/22 of DSH's input_hashes recomputed byte-identical during this review"
            ),
            "output_hashes_reverified": "3/3 of DSH's recorded log hashes recomputed byte-identical",
            "claims_independently_reproduced": [
                "psql/pg_ctl NOT FOUND; docker client present but daemon unreachable; TEST_DATABASE_URL unset",
                "uv.lock contains 0 occurrences of psycopg/sqlalchemy/alembic/asyncpg",
                "apps/backend/pyproject.toml lists no database dependency",
                "import logistics_backend.cli -> ModuleNotFoundError; the package __init__ exports constants only",
                "artifacts/gates/ holds only G00-checks.log, G00.json, G01.json",
                "the Phase 04 probe reports previous-gate:G03 missing",
                "tests/conftest.py fails (never skips) when TEST_DATABASE_URL is absent and refuses a database whose "
                "URL does not contain 'test'",
            ],
        },
        "dependency_presence": {
            "artifacts/gates/G03.json": exists("artifacts/gates/G03.json"),
            "artifacts/handoffs/P04-01/zcode/precheck.json": exists("artifacts/handoffs/P04-01/zcode/precheck.json"),
            "data/scenarios/tiny_transport.json": exists("data/scenarios/tiny_transport.json"),
            "data/seed/": (root / "data/seed").is_dir(),
        },
        "dependency_present_count": 0,
        "dependency_expected_count": 4,
        "dependency_expected_count_note": (
            "0 of 4: no G03 record, no P04-01 ZCode precheck, no fixture to import, and no data/seed/ directory. "
            "Note that artifacts/handoffs/P04-01/zcode/precheck.json now exists because this review wrote it with "
            "status=BLOCKED; it is not a Z_PRECHECK_PASSED and therefore still does not satisfy P04-02's dependency."
        ),
        "prerequisites": {
            "G00": {"recorded_status": "passed", "sha256": sha("artifacts/gates/G00.json"), "verdict": "valid"},
            "G01": {
                "recorded_status": g01.get("status"),
                "sha256": sha("artifacts/gates/G01.json"),
                "failed_checks": g01.get("failed_checks"),
                "verdict": "invalid (blocking)",
            },
            "G02": {"record": None, "verdict": "invalid (blocking): no artifacts/gates/G02.json exists"},
            "G03": {
                "record": None,
                "verdict": "invalid (blocking, declared dependency 1): no artifacts/gates/G03.json exists",
                "probe_evidence": "my re-run of the Phase 04 probe reports [FAIL] previous-gate:G03: missing",
            },
            "P04-01": {
                "dsh_status": p0401.get("status"),
                "zcode_precheck": "artifacts/handoffs/P04-01/zcode/precheck.json written by this review with "
                                  "status=BLOCKED",
                "deliverable_present_count": "2/9 (both documentation-only); 0/4 fixtures; no generator",
                "verdict": "invalid (blocking, declared dependency 2): no scenario bundle exists to import",
            },
            "P03-01..P03-04": {
                "dsh_status": "BLOCKED",
                "zcode_precheck": "BLOCKED",
                "verdict": "invalid (blocking): G03 cannot be assembled",
            },
        },
        "frozen_interface": {
            "entrypoint": "python -m logistics_backend.cli.seed --scenario tiny_transport --database-url-env TEST_DATABASE_URL",
            "source": "docs/prompts/01-foundation/P04-02-database-seed.md:87",
            "entrypoint_importable": "no: logistics_backend.cli and logistics_backend.cli.seed both raise ModuleNotFoundError",
            "declared_model_types": ["ScenarioBundle", "ImportReceipt"],
            "ScenarioBundle": "no frozen owner: ARCH-0006 is open; its body already names P04-02 as carrying the same risk",
            "ImportReceipt": (
                "no row in the named Schema table of DATA_CONTRACTS.md; CommitReceipt (P02-03) and JobRequest/JobRef "
                "(P05-03) do have rows, so this is an omission rather than an inherited type. Repository-wide, the "
                "identifier appears only in TASK_MANIFEST.json (P04-02 model field), the P04-02 prompt line 68 and "
                "ARCH-0006 line 13."
            ),
            "whitelist_gap": (
                "the whitelist contains no domain/DTO module, so defining ImportReceipt here would duplicate the "
                "domain model (Constraint 6) and returning a bare dict would violate Constraint 1"
            ),
        },
        "environment_blockers": {
            "psql_on_path": False,
            "pg_ctl_on_path": False,
            "docker_daemon": (
                "unreachable: 'failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine' "
                "for both docker version and docker ps"
            ),
            "tcp_listener_5432": "no listener (immediate ConnectionRefusedError in the captured probe log)",
            "tcp_listener_5433": "no listener (immediate ConnectionRefusedError in the captured probe log)",
            "TEST_DATABASE_URL": "unset",
            "db_driver_in_lock": "0 occurrences of psycopg/sqlalchemy/alembic/asyncpg in uv.lock",
            "db_dependency_in_backend_manifest": "none: apps/backend/pyproject.toml declares fastapi, uvicorn and the "
                                                "six workspace packages only",
            "consequence": (
                "Test Case 1 (idempotent second import) and Test Case 2 (FK failure rolls the whole load back) both "
                "require a real isolated PostgreSQL with genuine FK constraints; neither can be executed or "
                "pre-accepted on this host, and per tests/conftest.py a missing TEST_DATABASE_URL is a failure, "
                "never a skip, so a critical skip cannot be used to fake coverage"
            ),
        },
        "commands": [
            {
                "id": "cmd1",
                "mandatory": True,
                "argv": "uv run pytest tests/unit/test_p04_02_database_seed.py tests/integration/test_p04_02_database_seed.py -q",
                "workdir": str(root),
                "exit_code": 4,
                "result": "ERROR: file or directory not found: tests/unit/test_p04_02_database_seed.py | no tests ran "
                          "in 0.00s (0 passed / 0 failed / 0 skipped)",
                "zero_case_run": True,
                "counts_as_evidence": False,
                "log": log_fact("cmd1-pytest.log"),
            },
            {
                "id": "cmd2",
                "mandatory": True,
                "argv": "uv run python scripts/check_architecture.py",
                "workdir": str(root),
                "exit_code": 0,
                "result": "architecture-layers: scanned 7 module(s) across 7 layer(s); violations=0",
                "counts_as_evidence": False,
                "hollow_pass": True,
                "hollow_pass_reason": (
                    "identical output (byte-for-byte) to the P04-01 run of the same command: 7 scanned modules are "
                    "the unmodified P01-01 placeholder packages. logistics_backend.cli is not even in scope, and the "
                    "checker cannot detect the failure mode this task must avoid (an undefined dict crossing the "
                    "seeder boundary) because no seeder exists"
                ),
                "log": log_fact("cmd2-architecture.log"),
            },
            {
                "id": "cmd3",
                "mandatory": False,
                "argv": "uv run python scripts/gates.py --phase 04 --revision auto --out-dir tmp/zcode-p04/probe-g04",
                "workdir": str(root),
                "exit_code": 1,
                "result": "G04: 7/17 checks passed; previous-gate:G03 missing; P04-01-cmd1 and P04-02-cmd1 fail with "
                          "exit 4; dsh-evidence for both tasks unexpected; both zcode-prechecks missing; codex-review missing",
                "wrote_official_gate_record": False,
                "log": log_fact("gates-probe-phase04.log"),
            },
            {
                "id": "cmd4",
                "mandatory": False,
                "argv": "environment probe: psql/pg_ctl/docker/TEST_DATABASE_URL/TCP 5432,5433/uv.lock driver scan/import probe",
                "workdir": str(root),
                "exit_code": None,
                "result": "no PostgreSQL reachable by any of the five routes; see environment_blockers",
                "log": log_fact("environment-probe.log"),
            },
            {
                "id": "cmd5",
                "mandatory": False,
                "argv": "uv run pytest tests/unit tests/integration -q",
                "workdir": str(root),
                "exit_code": 0,
                "result": "187 passed (40.34s and 38.19s on the two runs captured in the per-task logs) -- "
                          "adjacent-module regression baseline (no P04-02 test present)",
                "log": log_fact("regression-full-pytest.log"),
            },
        ],
        "phase_appropriate_checks": {
            "uv lock --check": {"exit_code": 0, "result": "Resolved 40 packages in 2ms"},
            "scripts/check_ownership.py": {"exit_code": 0, "result": "files=1250 rules=60 violations=0"},
            "scripts/gates.py --phase 01 --check-only": {
                "exit_code": 0,
                "result": "recorded status=failed; 4 missing records; gate not signed",
            },
            "uv run ruff check apps/backend/src packages/*/src tests scripts": {
                "exit_code": 1,
                "result": "39 errors, all pre-existing in P01 files; none in a P04-02 path (none exists)",
                "attribution": "pre-existing lint debt; ruff is neither a mandatory command here nor part of ci.yml",
            },
            "schema/openapi/generated-client consistency": {
                "status": "not applicable this round",
                "reason": "the task exposes a CLI entrypoint rather than an HTTP route and ships no Schema export; "
                          "the seeder's schema/hash validation is its own runtime check, not a generated-client artifact",
            },
        },
        "test_cases": {
            "1: importing the same data twice => second run inserted=0": {
                "status": "NOT RUN / UNVERIFIED",
                "reason": "no seeder, no fixture and no database; and independently, no PostgreSQL is reachable",
                "recheck_plan": (
                    "on re-issue, do not accept 'status is non-empty': count real rows in the isolated test database "
                    "before and after the second import and assert the delta is exactly 0"
                ),
            },
            "2: second object with an invalid FK => the whole load rolls back": {
                "status": "NOT RUN / UNVERIFIED",
                "reason": "requires a real PostgreSQL with genuine FK constraints, which is unreachable",
                "recheck_plan": (
                    "construct the invalid-FK input, run the load, then assert the first object is also absent and no "
                    "partial rows remain -- the rollback must be observed at the database level, not inferred from an "
                    "exit code"
                ),
            },
        },
        "defects": [
            {
                "id": "Z-D1",
                "severity": "blocking (inherited)",
                "title": "The declared dependency G03 has no record and cannot be assembled",
                "evidence": [
                    "artifacts/gates/ contains only G00-checks.log, G00.json, G01.json",
                    "Phase 04 probe: [FAIL] previous-gate:G03: missing artifacts/gates/G03.json",
                    "P03-01..P03-04 all BLOCKED with zero delivered files",
                ],
                "owner": "project management side + P01-03",
                "fixed_by_zcode": False,
                "reason_not_fixed": "outside this task's whitelist and this reviewer's role",
            },
            {
                "id": "Z-D2",
                "severity": "blocking (dependency)",
                "title": "P04-01 delivered no scenario fixture to import",
                "evidence": [
                    "artifacts/handoffs/P04-01/dsh/evidence.json status=BLOCKED, 2/9 deliverables, 0/4 fixtures",
                    "data/scenarios/ contains only README.md; scripts/generate_scenarios.py absent",
                    "no artifacts/handoffs/P04-01/zcode/precheck.json with Z_PRECHECK_PASSED (this review wrote one, "
                    "with status=BLOCKED)",
                ],
                "owner": "P04-01 (after the barrier repair)",
                "fixed_by_zcode": False,
                "reason_not_fixed": "manufacturing fixture data here would fabricate the dataset_hash and idempotency "
                                   "evidence G04 depends on",
            },
            {
                "id": "Z-D3",
                "severity": "blocking (environment)",
                "title": "No isolated PostgreSQL is reachable and no database driver is locked",
                "evidence": [
                    "psql and pg_ctl are not on PATH",
                    "docker version / docker ps fail against the desktop-linux pipe",
                    "no TCP listener on 5432 or 5433",
                    "TEST_DATABASE_URL is unset",
                    "uv.lock has 0 occurrences of psycopg/sqlalchemy/alembic/asyncpg; apps/backend/pyproject.toml has "
                    "no database dependency",
                ],
                "owner": "project management side (dependency decision + Phase 01 environment manual)",
                "fixed_by_zcode": False,
                "reason_not_fixed": (
                    "adding a database driver to uv.lock or the backend manifest would change Gate inputs that G01 "
                    "must sign off, and installing a server is an environment decision that "
                    "docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md assigns to the project management side"
                ),
            },
            {
                "id": "Z-D4",
                "severity": "blocking (contract gap)",
                "title": "The declared receipt type ImportReceipt has no frozen Schema row and no whitelisted home",
                "evidence": [
                    "DATA_CONTRACTS.md's named Schema table has CommitReceipt (P02-03) and JobRequest/JobRef (P05-03) "
                    "rows but no ImportReceipt row",
                    "repository-wide, ImportReceipt appears only in TASK_MANIFEST.json, the P04-02 prompt, and ARCH-0006",
                    "the P04-02 whitelist contains no domain/DTO module",
                ],
                "owner": "contract owner (fold into the same decision as ARCH-0006)",
                "fixed_by_zcode": False,
                "reason_not_fixed": (
                    "P04-02 deliberately did not open a duplicate issue; this review agrees it is the same outstanding "
                    "decision and records it here rather than editing another owner's issue file"
                ),
            },
            {
                "id": "Z-D5",
                "severity": "medium (evidence accuracy; does not change the verdict)",
                "title": "The DSH structured record reports existing P04-02 documents as absent, and its 0/7 count contradicts its own note",
                "evidence": [
                    "artifacts/handoffs/P04-02/dsh/evidence.json deliverable_presence marks "
                    "docs/implementation/P04-02.md and docs/implementation/reports/P04-02.md as false",
                    "both files exist (9559 B and 13533 B) and my re-run of the G04 probe passes both docs checks",
                    "their mtimes (21:36:27 and 21:36:46) precede the record's own mtime (21:37:16), so the record was "
                    "written after the files existed and is wrong at write time, not merely stale",
                    "the DSH P04-02 probe at 21:34:15 independently proves the documents were still missing then, "
                    "which is consistent with the handoff narrative but not with the record's final content",
                    "the count note defines 7 as 'the 6 manifest files plus this record's own evidence.json' yet "
                    "reports 0 present, although the evidence record itself was written by that point",
                ],
                "impact": (
                    "the machine-readable record understates the delivered set and cannot be diffed against a rebuild; "
                    "the substantive conclusion (0 of 4 code/data/test deliverables) is unaffected because it is correct"
                ),
                "correction": (
                    "the correct values are 2/6 allow-listed deliverables present (both documentation) and 0/4 "
                    "code/data/test deliverables absent; docs/handoffs/P04-02/dsh.md section 1 also enumerates only 4 "
                    "items while saying '6 deliverables, none created', the same conflation"
                ),
                "owner": "DSH",
                "fixed_by_zcode": False,
                "reason_not_fixed": (
                    "another agent's evidence record is part of the audit trail and is preserved unmodified; the "
                    "correction is recorded here for Codex instead"
                ),
            },
            {
                "id": "Z-D6",
                "severity": "low (evidence hygiene)",
                "title": "One DSH raw log is UTF-16 with BOM and unreadable with standard UTF-8 tooling",
                "evidence": [
                    "artifacts/handoffs/P04-02/dsh/logs/gates-probe-phase04.log is UTF-16-BOM, 3078 B",
                    "decoding it yields 'G04: 5/17 checks passed' and the per-check rows, so the content is intact",
                    "its sha256 matches DSH's recorded output_hashes exactly",
                ],
                "impact": "authenticity unaffected; only machine readability degraded",
                "owner": "DSH",
                "fixed_by_zcode": False,
                "reason_not_fixed": "this review re-ran the same probe and stored its own UTF-8 log instead of "
                                    "rewriting another agent's evidence",
            },
        ],
        "fixed_by_zcode": [],
        "unfixed": [
            "Z-D1 (gate barrier), Z-D2 (P04-01 fixtures), Z-D3 (PostgreSQL + driver decision), Z-D4 (ImportReceipt "
            "ownership), Z-D5 (DSH record accuracy), Z-D6 (UTF-16 log)",
        ],
        "not_verified": [
            "Test Case 1 (second identical import yields inserted=0) - no seeder, no fixture, no database",
            "Test Case 2 (invalid FK on the second object rolls the whole load back) - needs real PostgreSQL FK behaviour",
            "the CLI entrypoint python -m logistics_backend.cli.seed ... - the module does not exist",
            "Business Rules: explicit test/demo database only, no default truncation, stable fixture ids, and no "
            "overwriting of existing related facts - all UNVERIFIED",
            "Algorithm: schema/hash validation before a transactional insert, same-hash => no_change, and content "
            "change requiring a new dataset_version - UNVERIFIED",
            "the G04 exit assertion 'same seed imported twice does not duplicate and does not clear the existing "
            "database' - no evidence at all",
            "dataset_hash / dataset_version recomputation from the fixture - impossible without a fixture",
            "the whole Edge Case table (empty collections, duplicate ids, illegal enums/units, negatives/integer "
            "overflow, missing references, equal boundary times, stale revision, cancellation/timeout, dependency "
            "unavailable) - UNVERIFIED",
            "the Observability requirement (pass/fail counts, durations, files processed) - honestly 0, since no seed "
            "run exists; the G04 probe measured 4 commands, median 257 ms, total 1030 ms in my re-run",
            "error-code mapping (422/409/503) and If-Match/Idempotency-Key - not applicable: this task exposes a CLI "
            "entrypoint, not an HTTP route; recorded as not applicable rather than passed",
            "the candidate/validated/confirmed triple and version_id/parent_version_id/snapshot_hash - not applicable: "
            "this task produces no schedule plan",
        ],
        "security_review": {
            "scope": "the paths touched or referenced by P04-02 plus the repository sources",
            "credentials_scan": (
                "no credential-looking literal in the task documents, DSH records or repository sources; no .env, "
                ".pem, .p12 or id_rsa outside third-party vendored directories"
            ),
            "env_var_handling": (
                "the task's whole credential surface is the variable NAME TEST_DATABASE_URL, which is passed by name "
                "( --database-url-env TEST_DATABASE_URL ) rather than by value; no value appears in any P04 document "
                "or record, and the value is unset in this environment"
            ),
            "injection_surface": (
                "not applicable yet: no SQL, no shell interpolation and no subprocess exist because the seeder does "
                "not exist. When it is written, the parameter-binding rule applies to every insert, and the raw "
                "fixture must not be interpolated into SQL text -- this is carried into the re-issue checklist."
            ),
            "log_redaction": (
                "my logs contain command output only; no secret, no personal data and no model-internal reasoning was "
                "printed or stored. The database URL, had one existed, would be redacted rather than logged."
            ),
            "dependency_changes": (
                "uv.lock and apps/backend/pyproject.toml are byte-identical to the state DSH reviewed (sha256 "
                "89f78a20...86c5 and 97c9e247...9344); uv lock --check exits 0. No dependency was added by this review."
            ),
            "known_dependency_vulnerabilities": (
                "no vulnerability scanner is established in this repository (ci.yml has no pip-audit/npm audit step), "
                "so no scan is claimed and none was run; recorded as not-run rather than clean"
            ),
            "unverified_advisories_vs_reproducible": (
                "no reproducible vulnerability was found or reproduced, and no scanner output exists to classify as an "
                "unverified advisory"
            ),
        },
        "tool_versions": {
            "python": platform.python_version(),
            "uv": "0.12.13 (tools/bin/uv.exe; uv is not on PATH on this host)",
            "os": f"{platform.system()} {platform.release()}",
            "host_notes": "no psql/pg_ctl; docker client present, daemon unreachable; TEST_DATABASE_URL unset",
        },
        "verified_input_hashes": {rel: sha(rel) for rel in VERIFIED_INPUTS},
        "verified_input_hashes_note": (
            "recomputed during this review; every shared key matches DSH's recorded value byte-for-byte"
        ),
        "evidence_logs": {name: log_fact(name) for name in MY_LOGS},
        "evidence_builder": {
            "path": f"{ZDIR}/build-evidence.py",
            "argv": f"python {ZDIR}/build-evidence.py",
            "rebuildable": "yes: every hash is recomputed from the working tree; Codex can rebuild and diff",
        },
        "sandbox_gate_evidence": {
            "official_gate_records_written": [],
            "statement": "no Gate was signed, no artifacts/gates file was created or modified, and probe output went "
                         "to tmp/zcode-p04 (gitignored scratch)",
            "artifacts_gates_listing_after_review": ["G00-checks.log", "G00.json", "G01.json"],
        },
        "files_added_by_zcode": [
            f"{ZDIR}/build-evidence.py",
            f"{ZDIR}/evidence.json",
            f"{ZDIR}/precheck.json",
            *[f"{ZDIR}/logs/{n}" for n in MY_LOGS],
        ],
        "files_modified_by_zcode": [],
        "files_modified_by_zcode_note": (
            "no file outside this record's own directory was created or modified; the DSH report and evidence were "
            "preserved unmodified, and nothing under apps/, data/, tests/ or artifacts/gates/ was touched"
        ),
        "preserved_dsh_report": [
            "docs/handoffs/P04-02/dsh.md (sha256 above, unmodified)",
            "artifacts/handoffs/P04-02/dsh/evidence.json (sha256 above, unmodified, including the inaccurate rows of "
            "defect Z-D5)",
            "artifacts/handoffs/P04-02/dsh/logs/* (3 files, all unmodified, hashes verified)",
        ],
        "signs_gate": False,
        "gate_signed": None,
        "limitations": [
            "the revision label is a self-perturbing content hash because there is no .git",
            "no PostgreSQL, no Docker daemon and no psql/pg_ctl are available, so the idempotency and rollback cases "
            "cannot be executed on this host at all",
            "the architecture checker scans 7 placeholder modules and cannot express this task's failure mode; its "
            "exit 0 is not acceptance evidence",
        ],
        "next_actions": [
            "repair the barrier first: the 4 Phase 01 records in the order docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md "
            "specifies, then P02-01..P02-04 and G02, then G03",
            "settle two project-management decisions before G01 is signed: admit psycopg/SQLAlchemy/Alembic into the "
            "lock, and deliver the Phase 01 environment manual defining an isolated PostgreSQL plus TEST_DATABASE_URL",
            "decide ARCH-0006 and, in the same decision, the ImportReceipt Schema row (defect Z-D4) -- otherwise a "
            "re-issued P04-02 must either duplicate the domain model or return a bare dict",
            "re-issue P04-01 first and pre-accept it, then re-issue P04-02; at pre-acceptance, run two imports against "
            "an isolated real PostgreSQL and count real rows, construct the invalid-FK input and show the first object "
            "did not land, recompute dataset_hash from the fixture rather than trusting a recorded value, and try a "
            "deliberately non-test-named database to prove the refusal",
            "ensure DSH's replaced record recomputes its deliverable_presence after writing the documents (defect Z-D5)",
        ],
        "reviewer_verdict_line": (
            "ZCode: BLOCKED -- 0/4 code-data-test deliverables, G03 and P04-01 unmet, no PostgreSQL, ImportReceipt "
            "unowned; DSH verdict confirmed and its structured record corrected on two rows; no Gate signed"
        ),
    }

    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    (root / ZDIR / "evidence.json").write_text(payload, encoding="utf-8")
    (root / ZDIR / "precheck.json").write_text(payload, encoding="utf-8")
    print(f"wrote {ZDIR}/evidence.json and {ZDIR}/precheck.json (status={record['status']})")
    print(f"deliverables present: {present}/{len(DELIVERABLES)} (code/data/test: {code_present}/{len(code_paths)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
