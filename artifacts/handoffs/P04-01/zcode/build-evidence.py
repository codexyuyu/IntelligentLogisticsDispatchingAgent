"""Assemble the P04-01 ZCode pre-acceptance evidence record.

Run from the repository root:  python artifacts/handoffs/P04-01/zcode/build-evidence.py

The script only reads repository files and writes the two records next to itself plus a
build log under logs/; it never signs a Gate and never writes into the task's own
implementation paths. Every hash it records is recomputed here so Codex can rebuild and
diff the record. The gate revision label is asked of the runner itself, never
transcribed by hand.

Verdict: BLOCKED. P04-01 has no implementation candidate: 7 of the 9 allow-listed
deliverables (1 generator, 4 fixture JSON files, 2 test files) do not exist, its only
declared dependency G03 has no gate record, and the frozen interface's input type
ScenarioSpec is owned by the undelivered P02-04 while the return type ScenarioBundle has
no frozen owner (ARCH-0006, open).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(".").resolve()

TASK = "P04-01"
SLUG = "canonical-fixtures"
PHASE = 4
GATE = "G04"
ZDIR = f"artifacts/handoffs/{TASK}/zcode"
LOG_DIR = root / ZDIR / "logs"

# The manifest `files` list plus `allowed_files`: 5 file deliverables, 2 test files, and
# the 2 documents. 2 of the 9 exist; all 7 code/data/test deliverables are absent.
DELIVERABLES = [
    "scripts/generate_scenarios.py",
    "data/scenarios/tiny_transport.json",
    "data/scenarios/tiny_warehouse.json",
    "data/scenarios/invalid_cases.json",
    "data/scenarios/manifest.json",
    "tests/unit/test_p04_01_canonical_fixtures.py",
    "tests/integration/test_p04_01_canonical_fixtures.py",
    "docs/implementation/P04-01.md",
    "docs/implementation/reports/P04-01.md",
]

# Frozen inputs whose bytes this review verified. Recomputed, never copied from DSH.
VERIFIED_INPUTS = [
    "docs/prompts/01-foundation/P04-01-canonical-fixtures.md",
    "docs/plan/TEST_FIXTURES.md",
    "docs/plan/TASK_MANIFEST.json",
    "docs/plan/PHASE_GATES.md",
    "docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md",
    "TASK_GRAPH.md",
    "docs/architecture/DATA_CONTRACTS.md",
    "docs/architecture/DOMAIN_CATALOG.md",
    "docs/architecture/issues/README.md",
    "docs/architecture/issues/ARCH-0006-scenario-bundle-ownership.md",
    "data/scenarios/README.md",
    "pyproject.toml",
    "uv.lock",
    "tests/conftest.py",
    "artifacts/gates/G00.json",
    "artifacts/gates/G01.json",
    "artifacts/handoffs/P04-01/dsh/evidence.json",
    "docs/handoffs/P04-01/dsh.md",
]

MY_LOGS = [
    "cmd1-pytest.log",
    "cmd2-architecture.log",
    "gates-probe-phase04.log",
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
    dsh = json.loads((root / "artifacts/handoffs/P04-01/dsh/evidence.json").read_text(encoding="utf-8"))

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
            "P04-01 has no implementation candidate. All 7 code/data/test deliverables are absent (1 generator, "
            "4 fixture JSON files, 2 test files); the 2 documents present record the blocking state only. The single "
            "declared dependency G03 has no gate record (artifacts/gates/G03.json is missing) and cannot be assembled "
            "because P03-01..P03-04 are BLOCKED with zero delivered files, so the mandatory pytest command exits 4 "
            "with 0 cases collected. Independently of the gate chain, the frozen interface "
            "generate_scenario(spec: ScenarioSpec, seed: int) -> ScenarioBundle is unimplementable: the input type "
            "ScenarioSpec is owned by P02-04 (DATA_CONTRACTS.md:81) which has no DSH evidence and a BLOCKED precheck, "
            "and the return type ScenarioBundle has no frozen owner at all (ARCH-0006, still open). DSH's BLOCKED "
            "verdict is independently confirmed on all of these points; no Gate is signed."
        ),
        "reviewed_at_local": datetime.datetime.now().astimezone().isoformat(),
        "candidate": {
            "root": str(root),
            "vcs": "no .git in this checkout; located by content hash (scripts/gates.py GateRunner.compute_revision)",
            "revision_label_during_this_review": current_revision(),
            "revision_label_is_self_perturbing": (
                "by construction this label is one step stale: compute_revision() covers artifacts/handoffs/**, "
                ".mimosa/** and tmp/**, including this record's own directory, so the label moves when the record is "
                "written. It is a content fingerprint for the file set, not a VCS commit."
            ),
            "previous_gate_recorded_revision": g01.get("code_revision"),
            "measured_g04_probe_revision": "content-sha256:c627d42667bf8ee79be6870a067f03d11f9d2420b269561d838d1b0db4f40526",
            "same_root_as_dsh": True,
            "same_candidate_checked": (
                "yes: this review re-ran every mandatory command against the same working root and found the same "
                "file state DSH recorded; no implementation candidate exists for either agent to review"
            ),
        },
        "deliverable_presence": presence,
        "deliverable_present_count": present,
        "deliverable_expected_count": len(DELIVERABLES),
        "deliverable_present_count_explanation": (
            f"{present} of {len(DELIVERABLES)} exist, and both are documentation-only: docs/implementation/P04-01.md "
            "and docs/implementation/reports/P04-01.md record the BLOCKED state. The 7 implementation/data/test "
            "deliverables (1 generator, 4 fixture JSON files, 2 test files) are all absent. This matches DSH's record; "
            "unlike the sibling P04-02 record, this one is internally consistent and factually correct."
        ),
        "code_and_test_presence": {rel: presence[rel] for rel in DELIVERABLES},
        "code_and_test_present_count": code_present,
        "code_and_test_expected_count": len(code_paths),
        "dsh_submission": {
            "record": "artifacts/handoffs/P04-01/dsh/evidence.json",
            "record_sha256": sha("artifacts/handoffs/P04-01/dsh/evidence.json"),
            "handoff": "docs/handoffs/P04-01/dsh.md",
            "handoff_sha256": sha("docs/handoffs/P04-01/dsh.md"),
            "dsh_status": dsh.get("status"),
            "dsh_record_round": dsh.get("record_round"),
            "reviewer_agrees_with_status": True,
            "dsh_summary_not_relied_on": (
                "the verdict was re-derived from the file system, the gate records and re-run commands before the "
                "DSH narrative was read for reconciliation; every load-bearing DSH claim was re-checked"
            ),
            "input_hashes_reverified": (
                "20/20 of DSH's input_hashes recomputed byte-identical during this review, so the frozen inputs DSH "
                "reviewed are the ones this review reviewed"
            ),
            "output_hashes_reverified": "7/7 of DSH's recorded log hashes recomputed byte-identical",
        },
        "dependency_presence": {
            "artifacts/gates/G00.json": exists("artifacts/gates/G00.json"),
            "artifacts/gates/G01.json": exists("artifacts/gates/G01.json"),
            "artifacts/gates/G02.json": exists("artifacts/gates/G02.json"),
            "artifacts/gates/G03.json": exists("artifacts/gates/G03.json"),
            "artifacts/gates/G04.json": exists("artifacts/gates/G04.json"),
            "artifacts/handoffs/P02-04/zcode/precheck.json": exists("artifacts/handoffs/P02-04/zcode/precheck.json"),
            "data/scenarios/README.md": exists("data/scenarios/README.md"),
        },
        "dependency_present_count": 4,
        "dependency_expected_count": 7,
        "prerequisites": {
            "G00": {"recorded_status": "passed", "sha256": sha("artifacts/gates/G00.json"), "verdict": "valid"},
            "G01": {
                "recorded_status": g01.get("status"),
                "sha256": sha("artifacts/gates/G01.json"),
                "failed_checks": g01.get("failed_checks"),
                "verdict": "invalid (blocking): the failed set is exactly the 3 Phase 01 precheck records plus the "
                           "Codex review record; this review confirmed all 4 are still absent",
            },
            "G02": {"record": None, "verdict": "invalid (blocking): no artifacts/gates/G02.json exists"},
            "G03": {
                "record": None,
                "verdict": "invalid (blocking, the only declared dependency): no artifacts/gates/G03.json exists",
                "probe_evidence": (
                    "my re-run of the Phase 04 probe reports [FAIL] previous-gate:G03: missing "
                    "artifacts/gates/G03.json"
                ),
            },
            "P03-01..P03-04": {
                "dsh_status": "BLOCKED",
                "zcode_precheck": "BLOCKED",
                "verdict": "invalid (blocking): all four tasks blocked, zero declared deliverables exist, so G03 "
                           "cannot be assembled",
            },
            "P02-04": {
                "dsh_evidence": "absent (no artifacts/handoffs/P02-04/dsh/ directory)",
                "zcode_precheck_status": "BLOCKED",
                "verdict": "invalid (blocking): owns the interface input type ScenarioSpec per DATA_CONTRACTS.md:81, "
                           "so the signature cannot even be typed",
            },
        },
        "frozen_interface": {
            "signature": "generate_scenario(spec: ScenarioSpec, seed: int) -> ScenarioBundle",
            "source": "docs/prompts/01-foundation/P04-01-canonical-fixtures.md:90",
            "input_type_owner": "P02-04 (DATA_CONTRACTS.md:81: 'ScenarioSpec 的纯数据形状也在P02-04定义，P04负责生成')",
            "input_type_importable": (
                "no: logistics_domain.planning and logistics_domain.runtime both raise ModuleNotFoundError; "
                "packages/domain/src/logistics_domain/__init__.py exports layer constants only and documents "
                "'Nothing is implemented yet'"
            ),
            "return_type_owner": "none: ARCH-0006 remains open; the named Schema table has no ScenarioBundle row",
            "whitelist_gap": (
                "the task whitelist contains no domain-type module, so an implementer can only duplicate the domain "
                "model (Constraint 6) or return an undefined dict (Constraint 1)"
            ),
        },
        "commands": [
            {
                "id": "cmd1",
                "mandatory": True,
                "argv": "uv run pytest tests/unit/test_p04_01_canonical_fixtures.py tests/integration/test_p04_01_canonical_fixtures.py -q",
                "workdir": str(root),
                "exit_code": 4,
                "result": "ERROR: file or directory not found: tests/unit/test_p04_01_canonical_fixtures.py | no tests "
                          "ran in 0.00s (0 passed / 0 failed / 0 skipped)",
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
                    "the 7 scanned modules are the unmodified P01-01 placeholder packages (one __init__.py per "
                    "layer, confirmed with --verbose --json: modules_per_layer = 1 for each of the 7 layers); this "
                    "task added no code, and the checker cannot see the failure mode the task exists to prevent "
                    "(an undefined dict crossing a boundary) because neither a generator nor a Schema exists"
                ),
                "log": log_fact("cmd2-architecture.log"),
            },
            {
                "id": "cmd3",
                "mandatory": False,
                "argv": "uv run python scripts/gates.py --phase 04 --revision auto --out-dir tmp/zcode-p04/probe-g04",
                "workdir": str(root),
                "exit_code": 1,
                "result": "G04: 7/17 checks passed; previous-gate:G03 missing; both cmd1 checks fail; both dsh-evidence "
                          "statuses unexpected; both zcode-prechecks missing; codex-review missing",
                "wrote_official_gate_record": False,
                "official_record_untouched": "artifacts/gates/ still holds only G00-checks.log, G00.json, G01.json",
                "log": log_fact("gates-probe-phase04.log"),
            },
            {
                "id": "cmd4",
                "mandatory": False,
                "argv": "uv run pytest tests/unit tests/integration -q",
                "workdir": str(root),
                "exit_code": 0,
                "result": "187 passed in 40.34s -- adjacent-module regression baseline",
                "purpose": "because this task delivered no code, the regression that can be run is the whole existing "
                           "suite; it passes and contains no P04-01 test, which independently confirms the absence of "
                           "the deliverable tests",
                "log": log_fact("regression-full-pytest.log"),
            },
        ],
        "phase_appropriate_checks": {
            "uv lock --check": {"exit_code": 0, "result": "Resolved 40 packages in 2ms"},
            "scripts/check_ownership.py": {"exit_code": 0, "result": "ownership-and-migration: files=1250 rules=60 violations=0"},
            "scripts/gates.py --phase 01 --check-only": {
                "exit_code": 0,
                "result": "check-only: recorded status=failed, failed_checks=['zcode-precheck:P01-01', "
                          "'zcode-precheck:P01-02', 'zcode-precheck:P01-03', 'codex-review']; gate not signed",
            },
            "uv run ruff check apps/backend/src packages/*/src tests scripts": {
                "exit_code": 1,
                "result": "39 errors, all in pre-existing P01-01/P01-02/P01-03 files (scripts/gates.py 11, "
                          "scripts/check_ownership.py 7, tests 14, one per package __init__.py 7)",
                "attribution": "pre-existing lint debt, not introduced by P04-01 (which wrote no code); ruff is not in "
                               "this task's mandatory command set nor in .github/workflows/ci.yml",
            },
            "schema/openapi/generated-client consistency": {
                "status": "not applicable this round",
                "reason": "the task produces fixture files only; it exposes no HTTP route and no Schema export. The "
                          "generator export step belongs to P02/P05. No drift check was invented.",
            },
        },
        "test_cases": {
            "1: tiny_transport => shortest distance 9000 m": {
                "status": "NOT RUN / UNVERIFIED",
                "reason": "the fixture and its test file do not exist",
            },
            "2: same seed=42 + same generator version => identical file hash": {
                "status": "NOT RUN / UNVERIFIED",
                "reason": "no generator and no version stamp exist",
            },
            "oracle_self_consistency": {
                "status": "independently verified by ZCode",
                "method": (
                    "recomputed TEST_FIXTURES.md T1/W1/S1 arithmetic from the frozen matrices; no fixture was "
                    "created and no expected plan was written into any implementation"
                ),
                "log": "tmp/zcode-p04/oracle-arithmetic-check.txt",
                "findings": [
                    "D-A-B-D = 3000+2000+4000 = 9000 m and the reverse D-B-A-D = 7000+6000+5000 = 18000 m, both as stated",
                    "travel 300+200+400 = 900 s; A arrival/depart 300/360; B arrival/depart 560/620; back at depot 1020 s; drive+service = 1020 s",
                    "per-leg load 800000 -> 400000 -> 0 g; cost 9 km x 100 + 500 = 1400 fen",
                    "A-window [350,350] variant gives A 350/410, B 610/670, return 1070 s; B latest_start=600 is then infeasible (arrival 610)",
                    "W1 makespan 20 s without setup and 25 s with setup (A[0,10), setup[10,15), B[15,25))",
                    "S1: +3 units at t10 peaks at 11 > capacity 10 (over-capacity); +3 units at t20 stays at 8 <= 10 (feasible)",
                ],
                "conclusion": (
                    "the frozen oracle is self-consistent and independently reproducible, so the two Test Cases are "
                    "genuinely testable once P04-01 is re-issued on a satisfied dependency chain"
                ),
            },
        },
        "defects": [
            {
                "id": "Z-D1",
                "severity": "blocking (inherited, not caused by DSH)",
                "title": "The declared dependency G03 has no record and cannot be assembled",
                "evidence": [
                    "artifacts/gates/ contains only G00-checks.log, G00.json, G01.json",
                    "Phase 04 probe: [FAIL] previous-gate:G03: missing artifacts/gates/G03.json",
                    "Phase 03 probe: G03: 13/28 checks passed with every P03-01..P03-04 acceptance row failing",
                    "G01 status=failed with failed_checks = 3 Phase 01 prechecks + codex-review, all still missing",
                ],
                "owner": "project management side + P01-03 (see docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md)",
                "fixed_by_zcode": False,
                "reason_not_fixed": (
                    "the remedy is writing three Phase 01 precheck records and a Codex review, which is outside this "
                    "task's whitelist and this reviewer's role; the remediation plan already specifies the exact "
                    "paths and write order"
                ),
            },
            {
                "id": "Z-D2",
                "severity": "blocking (contract gap)",
                "title": "The frozen interface cannot be implemented as written: input type undelivered, return type unowned",
                "evidence": [
                    "DATA_CONTRACTS.md:81 assigns ScenarioSpec to P02-04; no artifacts/handoffs/P02-04/dsh/ exists and "
                    "its zcode precheck is BLOCKED",
                    "logistics_domain.planning / logistics_domain.runtime -> ModuleNotFoundError",
                    "ARCH-0006 is open: the named Schema table has no ScenarioBundle row; it appears in DATA_CONTRACTS.md:94, "
                    "API_CONTRACT.md:47 and this task's prompt line 90 only as a signature",
                    "the P04-01 whitelist contains no domain-type module",
                ],
                "owner": "contract owner (ARCH-0006 decision) + Phase 02 delivery",
                "fixed_by_zcode": False,
                "reason_not_fixed": (
                    "defining ScenarioBundle or ScenarioSpec here would be a unilateral contract change and would "
                    "duplicate the domain model (Constraint 6); the issue file already lists the three candidate "
                    "resolutions and explicitly refuses to pick one"
                ),
            },
            {
                "id": "Z-D3",
                "severity": "low (evidence hygiene, does not change the verdict)",
                "title": "3 of the 7 DSH raw logs are UTF-16 with BOM and unreadable with standard UTF-8 tooling",
                "evidence": [
                    "artifacts/handoffs/P04-01/dsh/logs/r2-gates-probe-phase03.log (UTF-16-BOM, 4582 B)",
                    "artifacts/handoffs/P04-01/dsh/logs/r2-gates-probe-phase04.log (UTF-16-BOM, 3082 B)",
                    "artifacts/handoffs/P04-02/dsh/logs/gates-probe-phase04.log (UTF-16-BOM, 3078 B)",
                    "DSH's report disclosed the encoding problem only for round 1's cmd1-pytest.log and "
                    "cmd2-architecture.log, which were then re-saved as UTF-8; the three files above were not disclosed",
                    "content is intact: decoding as UTF-16 yields 'G03: 13/28 checks passed' and 'G04: 5/17 checks passed', "
                    "and the byte sizes and sha256 values match DSH's recorded output_hashes exactly",
                ],
                "impact": "authenticity is unaffected; only machine readability of the evidence is degraded",
                "owner": "DSH",
                "fixed_by_zcode": False,
                "reason_not_fixed": (
                    "rewriting another agent's evidence logs would tamper with the audit trail; this review instead "
                    "re-ran the same commands and stored its own UTF-8 logs under artifacts/handoffs/P04-01/zcode/logs/"
                ),
            },
            {
                "id": "Z-D4",
                "severity": "low (report accuracy, does not change the verdict)",
                "title": "DSH's recorded G04 count (5/17) does not match a re-run (7/17); the difference is a file-write ordering effect",
                "evidence": [
                    "DSH P04-01 probe log (21:27:57) and P04-02 probe log (21:34:15) both read 'G04: 5/17'",
                    "docs/implementation/P04-02.md (21:36:27) and reports/P04-02.md (21:36:46) were written after both probes",
                    "my re-run reads 'G04: 7/17': the two additional passes are exactly the two P04-02 document checks",
                    "both DSH probes are internally consistent with the file state at their timestamps, so this is not "
                    "a misstatement; the reports simply do not mark the count as time-sensitive",
                ],
                "impact": "a later reader diffing the numbers could wrongly suspect the probe was misreported",
                "owner": "DSH",
                "fixed_by_zcode": False,
                "reason_not_fixed": "both numbers are honest snapshots; this record reconciles them instead",
            },
        ],
        "fixed_by_zcode": [],
        "unfixed": [
            "Z-D1 (G01/G02/G03 barrier): needs the 4 Phase 01 records and the Phase 02/03 deliveries listed in "
            "docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md",
            "Z-D2 (contract gap): needs the ARCH-0006 decision plus P02-04 delivery",
            "Z-D3 (UTF-16 logs): DSH-side re-save",
            "Z-D4 (probe count drift): DSH-side annotation",
        ],
        "not_verified": [
            "Test Case 1 (tiny_transport shortest distance 9000 m) - fixture absent, case not run",
            "Test Case 2 (same seed=42 + same generator version => identical file hash) - generator absent, case not run",
            "the interface generate_scenario(...) itself - no implementation exists",
            "Business Rules: exact TEST_FIXTURES data usage, explicit 'synthetic' marking, stable uuid5 identifiers, "
            "and the prohibition on embedding the expected plan in the implementation - all UNVERIFIED",
            "the G04 exit assertion 'T1/W1/I1/M1 data hash reproducible' - no data and no hash",
            "the G04 exit assertion 'every counter-example has a reason' - invalid_cases.json absent",
            "normalised serialisation independent of dict iteration order - no generator to inspect",
            "the generator version stamp - does not exist",
            "the whole Edge Case table (empty collections, duplicate ids, illegal enums/units, negatives/integer "
            "overflow, missing references, equal boundary times, stale revision, cancellation/timeout, dependency "
            "unavailable) - UNVERIFIED",
            "the Observability requirement (pass/fail counts, durations, files processed) - no generator run exists, "
            "so it is honestly 0; the G04 probe measured 4 commands, total 1078 ms in my re-run",
            "error-code mapping (422/409/503) and If-Match/Idempotency-Key - not applicable: this task exposes no "
            "HTTP boundary and produces no candidate plan states; recorded as not applicable rather than passed",
        ],
        "security_review": {
            "scope": "the paths touched or referenced by P04-01 plus the repository sources",
            "credentials_scan": (
                "no credential-looking literal found in the task documents, DSH records or repository sources; no "
                ".env, .pem, .p12 or id_rsa exists outside third-party vendored directories under demo/demos and "
                "tmp/package-verification"
            ),
            "env_var_handling": (
                "the task touches no credential; Phase 04 references only the variable name TEST_DATABASE_URL (in "
                "P04-02), and no value appears anywhere in the P04 documents or records"
            ),
            "injection_surface": (
                "not applicable for P04-01: no SQL, no shell interpolation, no subprocess and no HTTP boundary exist "
                "in the deliverable, because the deliverable does not exist. The parameter-binding rule is nonetheless "
                "carried into the re-issue checklist for any future fixture loader."
            ),
            "log_redaction": (
                "my logs contain command output only; no secret, no personal data and no model-internal reasoning "
                "was printed or stored"
            ),
            "dependency_changes": (
                "uv.lock is byte-identical to the state DSH reviewed (sha256 89f78a20...86c5) and uv lock --check "
                "reports exit 0; no dependency was added by this review"
            ),
            "known_dependency_vulnerabilities": (
                "no vulnerability scanner is established in this repository yet (no pip-audit/npm audit gate in "
                ".github/workflows/ci.yml), so no scan result is claimed; this is recorded as not-run rather than clean. "
                "The nearest existing check, the CI secret-hygiene job, has no local equivalent to run without git."
            ),
            "unverified_advisories_vs_reproducible": (
                "no reproducible vulnerability was found or reproduced; nothing is listed as an unverified advisory "
                "either, because no scanner output exists to classify"
            ),
        },
        "tool_versions": {
            "python": platform.python_version(),
            "uv": "0.12.13 (tools/bin/uv.exe; uv is not on PATH on this host)",
            "os": f"{platform.system()} {platform.release()}",
            "host_notes": "no psql/pg_ctl on PATH; docker client present but the daemon pipe is unavailable; "
                          "TEST_DATABASE_URL unset (recorded for P04-02; P04-01 needs no database)",
        },
        "verified_input_hashes": {rel: sha(rel) for rel in VERIFIED_INPUTS},
        "verified_input_hashes_note": (
            "recomputed during this review; every shared key matches DSH's recorded value byte-for-byte, so the "
            "frozen inputs did not drift between DSH's pass and this one"
        ),
        "evidence_logs": {name: log_fact(name) for name in MY_LOGS},
        "logs_note": (
            "all ZCode logs are UTF-8 by construction; the DSH UTF-16 files (Z-D3) were decoded for content "
            "verification only and were left unmodified"
        ),
        "evidence_builder": {
            "path": f"{ZDIR}/build-evidence.py",
            "argv": f"python {ZDIR}/build-evidence.py",
            "rebuildable": "yes: every hash is recomputed from the working tree; Codex can rebuild and diff",
        },
        "sandbox_gate_evidence": {
            "official_gate_records_written": [],
            "statement": "no Gate was signed, no artifacts/gates file was created or modified, and the probe output "
                         "went to tmp/zcode-p04/probe-g04 (gitignored scratch)",
            "artifacts_gates_listing_after_review": ["G00-checks.log", "G00.json", "G01.json"],
        },
        "files_added_by_zcode": [
            f"{ZDIR}/build-evidence.py",
            f"{ZDIR}/evidence.json",
            f"{ZDIR}/precheck.json",
            *[f"{ZDIR}/logs/{n}" for n in MY_LOGS],
            "tmp/zcode-p04/oracle-arithmetic-check.txt",
            "tmp/zcode-p04/architecture-verbose.json",
            "tmp/zcode-p04/probe-g04/",
        ],
        "files_modified_by_zcode": [],
        "files_modified_by_zcode_note": (
            "no file outside this record's own directory was created or modified; in particular no file under "
            "scripts/, data/, tests/, artifacts/gates/ or another task's handoff directory was touched, and the DSH "
            "report and evidence were preserved unmodified"
        ),
        "preserved_dsh_report": [
            "docs/handoffs/P04-01/dsh.md (sha256 above, unmodified)",
            "artifacts/handoffs/P04-01/dsh/evidence.json (sha256 above, unmodified)",
            "artifacts/handoffs/P04-01/dsh/logs/* (7 files, all unmodified, hashes verified)",
        ],
        "signs_gate": False,
        "gate_signed": None,
        "limitations": [
            "the revision label is a self-perturbing content hash because there is no .git; it cannot be used as a "
            "stable commit identifier",
            "no PostgreSQL, no Docker daemon and no psql/pg_ctl are available on this host, so any future Phase 04 "
            "database assertion remains blocked until the environment manual is delivered",
            "the architecture checker scans 7 placeholder modules and therefore cannot express the failure mode this "
            "task is meant to prevent; its exit 0 is not acceptance evidence",
        ],
        "next_actions": [
            "repair the barrier before re-issuing any Phase 03/04 task: write the 4 Phase 01 records in the order "
            "docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md specifies, then deliver P02-01..P02-04 and sign G02, then "
            "re-issue and sign G03",
            "obtain the ARCH-0006 decision (ScenarioBundle ownership) -- pair it with the ImportReceipt gap recorded "
            "by P04-02, since both are the same outstanding decision",
            "only then re-issue P04-01; at pre-acceptance, re-verify the 9000 m value, stable uuid5 ids, normalised "
            "serialisation, the generator version stamp, per-counter-example rule attribution, and absence of "
            "hand-written fixtures",
            "reproduce Test Case 2 independently by running the generator twice with seed=42 and comparing bytes, "
            "rather than trusting a single recorded hash",
        ],
        "reviewer_verdict_line": (
            "ZCode: BLOCKED -- 0/7 code-data-test deliverables, G03 missing, interface untyped; DSH verdict "
            "independently confirmed; no Gate signed"
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
