"""Deterministic evidence builder for the ZCode independent pre-acceptance of P01-01.

Re-running this script recomputes every hash from the current disk and rewrites
evidence.json / precheck.json, so the record can always be rebuilt and compared
field by field. It starts no subprocess and writes only its own two JSON files.

The frozen input set follows docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md section
Z1 (14 recommended paths) plus the two P01-01 test files. It deliberately excludes
self-referencing outputs (this script, the two JSONs, the logs directory),
artifacts/gates/**, tmp/** and the files the remediation warns will drift before
G01 is finally signed (uv.lock, apps/backend/pyproject.toml).
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = ROOT / "artifacts/handoffs/P01-01/zcode"
LOGS = HERE / "logs"

FROZEN_INPUTS = [
    "TASK_GRAPH.md",
    "docs/plan/TASK_MANIFEST.json",
    "docs/plan/PHASE_GATES.md",
    "docs/architecture/DOMAIN_CATALOG.md",
    "docs/architecture/DATA_CONTRACTS.md",
    "docs/architecture/IMPLEMENTATION_CONVENTIONS.md",
    "docs/prompts/01-foundation/P01-01-workspace-bootstrap.md",
    "docs/implementation/P01-01.md",
    "docs/implementation/reports/P01-01.md",
    "docs/handoffs/P01-01/dsh.md",
    "artifacts/handoffs/P01-01/dsh/evidence.json",
    "scripts/gates.py",
    "scripts/check_architecture.py",
    "tests/conftest.py",
    "tests/unit/test_p01_01_workspace_bootstrap.py",
    "tests/integration/test_p01_01_workspace_bootstrap.py",
]

DELIVERABLES = [
    ".node-version",
    ".python-version",
    "apps/backend/pyproject.toml",
    "apps/backend/src/logistics_backend/__init__.py",
    "apps/frontend/package.json",
    "docs/implementation/P01-01.md",
    "docs/implementation/reports/P01-01.md",
    "package-lock.json",
    "package.json",
    "packages/agents/pyproject.toml",
    "packages/agents/src/logistics_agents/__init__.py",
    "packages/contracts/pyproject.toml",
    "packages/contracts/src/logistics_contracts/__init__.py",
    "packages/domain/pyproject.toml",
    "packages/domain/src/logistics_domain/__init__.py",
    "packages/evaluation/pyproject.toml",
    "packages/evaluation/src/logistics_evaluation/__init__.py",
    "packages/optimization/pyproject.toml",
    "packages/optimization/src/logistics_optimization/__init__.py",
    "packages/simulation/pyproject.toml",
    "packages/simulation/src/logistics_simulation/__init__.py",
    "playwright.config.ts",
    "pyproject.toml",
    "tests/integration/test_p01_01_workspace_bootstrap.py",
    "tests/unit/test_p01_01_workspace_bootstrap.py",
    "uv.lock",
]

LOG_FILES = [
    "r2-cmd1-pytest.log",
    "r2-cmd2-uv-sync-frozen.log",
    "r2-cmd3-npm-ci.log",
    "r2-architecture.log",
    "r2-demo-and-hash-drift.log",
    "r2-fail-closed.log",
    "r2-frontend-test.log",
    "r2-gates-probe-g01.log",
    "r2-gates-probe-g01-after.log",
    "r2-import-isolation.log",
    "r2-lock-check.log",
    "r2-ownership.log",
    "r2-regression.log",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    verified = {rel: sha256_file(ROOT / rel) for rel in FROZEN_INPUTS}
    evidence_logs = {
        f"artifacts/handoffs/P01-01/zcode/logs/{name}": {
            "sha256": sha256_file(LOGS / name),
            "bytes": (LOGS / name).stat().st_size,
        }
        for name in LOG_FILES
    }
    presence = {rel: (ROOT / rel).is_file() for rel in DELIVERABLES}

    commands = [
        {
            "check_id": "P01-01-cmd1",
            "argv": "uv run pytest tests/unit/test_p01_01_workspace_bootstrap.py tests/integration/test_p01_01_workspace_bootstrap.py -q",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "56 passed in 5.94s (0 skipped, 0 failed)",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-cmd1-pytest.log",
            "mandatory": True,
            "passed": True,
        },
        {
            "check_id": "P01-01-cmd2",
            "argv": "uv sync --frozen",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "Checked 39 packages in 3ms",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-cmd2-uv-sync-frozen.log",
            "mandatory": True,
            "passed": True,
        },
        {
            "check_id": "P01-01-cmd3",
            "argv": "npm ci",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "added 4 packages, audited 6 packages; 0 vulnerabilities",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-cmd3-npm-ci.log",
            "mandatory": True,
            "passed": True,
        },
        {
            "check_id": "regression",
            "argv": "uv run pytest tests/unit tests/integration -q",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "187 passed in 43.14s",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-regression.log",
            "mandatory": False,
            "passed": True,
        },
        {
            "check_id": "lock-check",
            "argv": "uv lock --check",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "Resolved 40 packages",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-lock-check.log",
            "mandatory": False,
            "passed": True,
        },
        {
            "check_id": "ownership",
            "argv": "uv run python scripts/check_ownership.py --json",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "files=1425 rules=60 violations=0",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-ownership.log",
            "mandatory": False,
            "passed": True,
        },
        {
            "check_id": "architecture",
            "argv": "uv run python scripts/check_architecture.py --verbose",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "7 layers / 7 modules, violations=0",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-architecture.log",
            "mandatory": False,
            "passed": True,
        },
        {
            "check_id": "fail-closed",
            "argv": ".venv/Scripts/python.exe -I -c 'import logistics_domain, logistics_contracts; getattr(...)'",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "logistics_domain.entities/units/states and logistics_contracts.dto/mapping all raise NotImplementedError with an explicit pending owner",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-fail-closed.log",
            "mandatory": False,
            "passed": True,
        },
        {
            "check_id": "import-isolation",
            "argv": ".venv/Scripts/python.exe -I -c (from a neutral cwd, user site disabled, cwd removed from sys.path) 'import six packages'",
            "cwd": "/tmp",
            "exit_code": 0,
            "result": "six packages resolve to their workspace src directories, proving installed (not cwd) resolution",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-import-isolation.log",
            "mandatory": False,
            "passed": True,
        },
        {
            "check_id": "demo-fingerprint",
            "argv": "independent recompute of the BASELINE_INVENTORY demo/ fingerprint",
            "cwd": str(ROOT),
            "exit_code": 0,
            "result": "173/173 entries present; tree sha256 == DSH evidence value; demo.zip + demo.zip.sha256 self-consistent; 14/14 DSH artifact/log hashes fresh on disk",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-demo-and-hash-drift.log",
            "mandatory": False,
            "passed": True,
        },
        {
            "check_id": "gates-probe-g01",
            "argv": "uv run python scripts/gates.py --phase 01 --revision auto --out-dir tmp/zcode-p0101/probe-g01-full",
            "cwd": str(ROOT),
            "exit_code": 1,
            "result": "G01: 22/26 checks passed; the 4 failures are exactly the 3 missing zcode precheck records plus the codex review (expected before this record existed)",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-gates-probe-g01.log",
            "mandatory": False,
            "passed": False,
            "note": "deliberately written to a non-official out-dir under gitignored tmp/; artifacts/gates/G01.json was neither signed nor overwritten; this probe predates precheck.json",
        },
        {
            "check_id": "gates-probe-g01-after",
            "argv": "uv run python scripts/gates.py --phase 01 --revision auto --out-dir tmp/zcode-p0101/probe-g01-after2",
            "cwd": str(ROOT),
            "exit_code": 1,
            "result": "G01: 22/26; zcode-precheck:P01-01 now PASSes with 16 fresh hash(es); P01-02-cmd1 now FAILS (56 passed, 1 failed) because tests/integration/test_p01_02_checks_and_gate_runner.py:555 hardcodes 'zcode-precheck:P01-01' in G01 failed_checks (defect Z-D1); remaining failures: P01-02-cmd1, zcode-precheck:P01-02, zcode-precheck:P01-03, codex-review",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-gates-probe-g01-after.log",
            "mandatory": False,
            "passed": False,
            "note": "sandbox out-dir under gitignored tmp/; artifacts/gates/G01.json neither signed nor overwritten; failure set merely swapped, gate score unchanged at 22/26",
        },
        {
            "check_id": "repro-p0102-fail-closed-test",
            "argv": "uv run pytest tests/integration/test_p01_02_checks_and_gate_runner.py::test_repository_phase_one_gate_is_fail_closed -q",
            "cwd": str(ROOT),
            "exit_code": 1,
            "result": "1 failed in 4.08s; AssertionError at tests/integration/test_p01_02_checks_and_gate_runner.py:555: 'zcode-precheck:P01-01' not in failed_checks",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-gates-probe-g01-after.log",
            "mandatory": False,
            "passed": False,
            "note": "isolated reproduction of defect Z-D1; the trigger is the existence of artifacts/handoffs/P01-01/zcode/precheck.json",
        },
        {
            "check_id": "frontend-test-script",
            "argv": "npm run test --workspace @logistics/frontend --if-present",
            "cwd": str(ROOT),
            "exit_code": 1,
            "result": "'vitest' is not recognized; apps/frontend declares test=vitest run but installs no devDependencies",
            "log_path": "artifacts/handoffs/P01-01/zcode/logs/r2-frontend-test.log",
            "mandatory": False,
            "passed": False,
            "scoped_to": "P01-01 deliverable apps/frontend/package.json; frontend tests do not exist until P24-01",
        },
    ]

    defects = [
        {
            "id": "Z-D1",
            "severity": "blocking-for-G01-sign-off (P01-02 scope; discovered during the P01-01 round)",
            "task": "P01-02",
            "title": "tests/integration/test_p01_02_checks_and_gate_runner.py:555 hardcodes 'zcode-precheck:P01-01' inside G01 failed_checks; once the P01-01 precheck record exists, P01-02-cmd1 fails (56 passed, 1 failed) and G01 cannot reach 26/26 even after the other records are written",
            "evidence": ["tests/integration/test_p01_02_checks_and_gate_runner.py:555", "logs/r2-gates-probe-g01-after.log: G01 22/26 with [FAIL] P01-02-cmd1 exit_code=1", "isolated repro: 1 failed in 4.08s"],
            "trigger": "artifacts/handoffs/P01-01/zcode/precheck.json exists with status=Z_PRECHECK_PASSED (this review wrote it per the scripts/gates.py contract and BARRIER_REMEDIATION Z1)",
            "impact": "the G01 unlock sequence in BARRIER_REMEDIATION section Z2 is incomplete: writing the three precheck records breaks P01-02-cmd1 before the gate can be signed; the gate score stays 22/26 with a swapped failure set",
            "repro": "1) write the P01-01 precheck record; 2) run 'uv run pytest tests/unit/test_p01_02_checks_and_gate_runner.py tests/integration/test_p01_02_checks_and_gate_runner.py -q' -> AssertionError at line 555",
            "fix_suggestion": "assert the durable fail-closed invariant (status=failed, codex-review in failed_checks, official record untouched) instead of a specific missing-record id; this change belongs to the P01-02 rework round, not to this review (role boundary: report only, no fix-and-sign)",
            "status": "unfixed",
            "owner": "P01-02 (DSH rework) + P01-02 ZCode precheck must re-verify",
        },
        {
            "id": "Z-N1",
            "severity": "non-blocking",
            "task": "P01-01",
            "title": "apps/frontend declares test=vitest run without devDependencies, so the script fails until P24-01 installs the frontend test stack",
            "evidence": ["apps/frontend/package.json", "logs/r2-frontend-test.log exit 1"],
            "status": "unfixed",
            "owner": "P01-01 (declared) / P24-01 (runtime)",
            "impact": "no frontend tests exist yet; the script is inert scaffolding, not an acceptance surface of P01-01",
        },
        {
            "id": "Z-N2",
            "severity": "non-blocking (disclosed limitation)",
            "task": "P01-01",
            "title": "Node 22 runtime behaviour is unverified on this host (Node 24.18.0); the pinned baseline and CI use Node 22",
            "evidence": [".node-version = 22", "package.json engines node >=22 <25", "npm 11.16.0 / node v24.18.0 on this host"],
            "status": "unfixed",
            "owner": "P01-01 / CI",
            "impact": "npm ci repeatability verified on Node 24 only; CI on Node 22 has never run (no .git in this checkout)",
        },
        {
            "id": "Z-N3",
            "severity": "non-blocking (cross-cutting)",
            "task": "P01-02/P01-03 + project management",
            "title": "docs/workflow/02-ZCODE-PRECHECK.md and HANDOFF_CONTRACT.md referenced by the task prompt do not exist (ARCH-0004); this record follows the path convention hardcoded in scripts/gates.py:305-311",
            "evidence": ["scripts/gates.py:305-311 comment", "docs/architecture/issues/README.md ARCH-0004"],
            "status": "unfixed",
            "owner": "project management + P01-03",
        },
        {
            "id": "Z-N4",
            "severity": "non-blocking (cross-cutting, previously recorded)",
            "task": "P01-02",
            "title": "Gate revision is built from volatile session/scratch state (.mimosa/**, tmp/**), so code_revision labels are point-in-time snapshots (previously recorded as D6 in the P02-02 review)",
            "evidence": ["scripts/gates.py EXCLUDED_FROM_REVISION", "artifacts/handoffs/P02-02/zcode/precheck.json defect D6"],
            "status": "unfixed",
            "owner": "P01-02",
        },
        {
            "id": "Z-N5",
            "severity": "observation (prerequisite repair, sanctioned)",
            "task": "P01-01",
            "title": "The P01-01 round first repaired the missing Phase 00 deliverables and recorded G00 (status=passed); this is the 'fix the prerequisite, never skip a gate' path the task prompt itself mandates, not an out-of-scope change",
            "evidence": ["docs/prompts/01-foundation/P01-01-workspace-bootstrap.md Current State", "artifacts/gates/G00.json status=passed", "artifacts/handoffs/P01-01/dsh.md section 2"],
            "status": "accepted",
            "owner": "scheduler visibility only",
        },
    ]

    test_cases = {
        "1": {
            "input": "clean environment: uv sync --frozen, then import the six packages",
            "expected": "all six packages import successfully from the installed workspace",
            "status": "PASSED",
            "evidence": "cmd2 exit 0; integration test test_frozen_workspace_install_is_importable (python -I, neutral cwd, resolved to member src dirs) and test_every_member_is_installed_as_an_editable_workspace_distribution (direct_url.json present); r2-import-isolation.log",
            "caveat": "the review used the existing locked .venv (uv sync --frozen exit 0 proves lock compliance); a from-zero fresh venv was created by DSH at delivery time and is covered by their pytest log",
        },
        "2": {
            "input": "npm ci executed twice in a row",
            "expected": "package-lock.json byte-identical before and after both runs",
            "status": "PASSED",
            "evidence": "integration test test_npm_ci_is_repeatable_and_lock_file_is_unchanged asserts observed == [before, before]; cmd3 exit 0 in this review; DSH evidence package_lock sha256 still fresh (14/14 no drift)",
        },
        "coverage": "2 of 2 required test cases",
    }

    not_verified = [
        "Node 22 runtime: only Node 24.18.0 exists on this host (Z-N2); the CI job has never run because the checkout has no .git",
        "Fresh-venv-from-zero install: not re-created in this review; uv sync --frozen (exit 0), uv lock --check (exit 0) and the isolated import probes cover the frozen-install contract",
        "scripts/gates.py fail-closed behaviour for non-zero commands: verified indirectly by G01's runner-fails-closed assertion (passes) but the runner itself is a P01-02 deliverable reviewed under P01-02",
        "Layer-boundary scanner (scripts/check_architecture.py): P01-02 deliverable; only its current vacuous scan over the 7 placeholder modules is observed here",
        "Anything HTTP/database/solver/simulation/LLM/browser: phases not reached",
    ]

    security_review = {
        "scope": "P01-01 workspace bootstrap change set plus baseline hygiene",
        "credential_files": "none found in the target tree (checked in earlier rounds; no credential-shaped files under the P01-01 change set)",
        "secret_literals": "0 hits for sk-[A-Za-z0-9]{20,} / AKIA patterns in P01-01 files",
        "command_injection": "no shell=True / os.system / eval / exec / pickle.loads in apps|packages|scripts|tests; gate runner executes argv arrays",
        "sql_injection": "NOT APPLICABLE: no database code exists at this phase",
        "dependency_changes": "uv lock --check exit 0; npm ci exit 0; both locks match the recorded evidence hashes",
        "external_targets_scanned": "none",
        "zcode_own_artifacts": "build-evidence.py starts no subprocess and contains no shell invocation",
    }

    tool_versions = {
        "python": "3.12.10",
        "python_executable": "D:\\Agent\\DeepSeekHarness\\IntelligentLogisticsDispatchingAgent\\.venv\\Scripts\\python.exe",
        "uv": "tools/bin/uv.exe (bootstrap copy recorded in DSH evidence as uv 0.12.13)",
        "node": "v24.18.0",
        "npm": "11.16.0",
        "os": "Windows 11",
        "zcode": "desktop 3.14.3 (this review's host app; not a project dependency)",
    }

    return {
        "schema_version": "1.0.0",
        "task_id": "P01-01",
        "scene": "workspace-bootstrap",
        "phase": 1,
        "phase_gate": "G01",
        "reviewer": "ZCode",
        "review_role": "independent-pre-acceptance",
        "status": "Z_PRECHECK_PASSED",
        "verdict_reason": "All 26 whitelist deliverables exist; the 3 mandatory validation commands exit 0 with 56 tests collected and 0 skipped; both required test cases pass; DSH's 14 recorded hashes are all fresh on disk; the read-only demo/ baseline fingerprint recomputes identically; no out-of-scope or interface drift found. Non-blocking observations Z-N1..Z-N5 are recorded and do not falsify the acceptance surface.",
        "reviewed_at_local": now,
        "candidate": {
            "root": str(ROOT),
            "vcs": "no .git in this checkout; the candidate is identified by content hashes (scripts/gates.py compute_revision) plus the DSH evidence artifact hashes",
            "dsh_evidence": "artifacts/handoffs/P01-01/dsh/evidence.json (status=READY_FOR_ZCODE, 14/14 recorded hashes re-verified fresh on 2026-09-28)",
            "same_candidate_check": "same workspace root, same file set and same mandatory commands as the DSH round; no divergence found",
        },
        "deliverable_presence": presence,
        "deliverable_present_count": sum(presence.values()),
        "deliverable_expected_count": len(DELIVERABLES),
        "prerequisites": {
            "G00": {"status": "passed", "source": "artifacts/gates/G00.json"},
            "G01": {
                "status": "failed (record snapshot at review time)",
                "failed_checks": [
                    "zcode-precheck:P01-01",
                    "zcode-precheck:P01-02",
                    "zcode-precheck:P01-03",
                    "codex-review",
                ],
                "note": "this record resolves the first of the four failures; the gate is not signed by this review",
            },
        },
        "commands": commands,
        "test_cases": test_cases,
        "defects": defects,
        "fixed_by_zcode": [],
        "unfixed": ["Z-D1", "Z-N1", "Z-N2", "Z-N3", "Z-N4"],
        "not_verified": not_verified,
        "security_review": security_review,
        "tool_versions": tool_versions,
        "verified_input_hashes": verified,
        "evidence_logs": evidence_logs,
        "files_added_by_zcode": [
            "docs/handoffs/P01-01/zcode.md",
            "artifacts/handoffs/P01-01/zcode/evidence.json",
            "artifacts/handoffs/P01-01/zcode/precheck.json",
            "artifacts/handoffs/P01-01/zcode/build-evidence.py",
            "artifacts/handoffs/P01-01/zcode/logs/ (12 r2-* logs, this review)",
            "tmp/zcode-p0101/ (non-official G01 probe evidence, gitignored)",
        ],
        "files_modified_by_zcode": [
            "none outside this review's own artifacts; DSH reports, DSH evidence, artifacts/gates/** and all business/config files were not touched",
        ],
        "signs_gate": False,
        "gate_signed": None,
        "limitations": [
            "G01 remains failed until P01-02 and P01-03 precheck records and the Codex review exist; this record alone must not be read as a gate signature",
            "Writing this record changes the G01 failure set: P01-02-cmd1 now fails because of the stale assertion at tests/integration/test_p01_02_checks_and_gate_runner.py:555 (Z-D1); the gate score is unchanged at 22/26 and the P01-02 rework must fix that test before the final gate run",
            "The G01 revision label is volatile (Z-N4); the frozen input hashes above are the durable binding",
            "docs/workflow/HANDOFF_CONTRACT.md does not exist (Z-N3); record layout follows scripts/gates.py:305-311 and the established zcode precheck schema",
            "Node 22 runtime unverified (Z-N2)",
        ],
        "next_actions": [
            "Codex / scheduler: the P01-01 pre-acceptance is PASSED and this candidate is fixed for hand-off; before G01 can be signed, P01-02's fail-closed test must be corrected (Z-D1) as part of the P01-02 rework, then the P01-02 and P01-03 ZCode prechecks can be written, and finally the Codex G01 review - in the order fixed by docs/plan/BARRIER_REMEDIATION_G01_G02_G03.md section Z2, amended by Z-D1",
            "P01-02 owner (DSH): replace the hardcoded 'zcode-precheck:P01-01 in failed_checks' assertion at tests/integration/test_p01_02_checks_and_gate_runner.py:555 with the durable invariant (status=failed + codex-review missing + official record untouched); the synthetic-repo tests at lines 415-460 are unaffected",
            "Project management: decide P1-a (database drivers into the workspace lock) and P1-b (Phase 01 environment manual) BEFORE the G01 final sign-off",
            "P01-01 owner: either pin vitest as a devDependency or move the test script to P24-01 (Z-N1)",
        ],
    }


def main() -> None:
    evidence = build()
    (HERE / "evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # precheck.json is a contract-shaped subset of evidence.json; it must stay
    # out of its own verified_input_hashes (self-reference rule).
    precheck = {
        key: evidence[key]
        for key in (
            "schema_version",
            "task_id",
            "scene",
            "phase",
            "phase_gate",
            "reviewer",
            "review_role",
            "status",
            "verdict_reason",
            "reviewed_at_local",
            "candidate",
            "deliverable_present_count",
            "deliverable_expected_count",
            "test_cases",
            "defects",
            "fixed_by_zcode",
            "unfixed",
            "not_verified",
            "security_review",
            "tool_versions",
            "verified_input_hashes",
            "evidence_logs",
            "files_added_by_zcode",
            "files_modified_by_zcode",
            "signs_gate",
            "gate_signed",
            "limitations",
            "next_actions",
        )
    }
    (HERE / "precheck.json").write_text(
        json.dumps(precheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {HERE / 'evidence.json'} and {HERE / 'precheck.json'}")
    print(
        f"status={precheck['status']} "
        f"deliverables={precheck['deliverable_present_count']}/{precheck['deliverable_expected_count']} "
        f"frozen_inputs={len(precheck['verified_input_hashes'])}"
    )


if __name__ == "__main__":
    main()
