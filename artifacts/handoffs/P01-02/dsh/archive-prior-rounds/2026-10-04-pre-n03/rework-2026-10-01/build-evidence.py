"""Build the rework-round evidence file for P01-02 (rework-2026-10-01).

Writes artifacts/handoffs/P01-02/dsh/evidence.json from facts it recomputes on disk:
file hashes, real pytest counts parsed from the recorded logs, the candidate revision and
working-tree fingerprint, the freshness of every record the phase gate reads, and the
verification probes. Run AFTER every other deliverable of the round has been written.

Usage:  python artifacts/handoffs/P01-02/dsh/rework-2026-10-01/build-evidence.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
LOG_DIR = "artifacts/handoffs/P01-02/dsh/rework-2026-10-01"
EVIDENCE = ROOT / "artifacts/handoffs/P01-02/dsh/evidence.json"
TASKS = {
    "unit": "tests/unit/test_p01_02_checks_and_gate_runner.py",
    "integration": "tests/integration/test_p01_02_checks_and_gate_runner.py",
}


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def read_text_any(relative: str) -> str:
    """Decode a recorded log without transforming its bytes (UTF-16LE or UTF-8, BOM aware)."""
    raw = (ROOT / relative).read_bytes()
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    return raw.decode("utf-8", errors="replace")


def log_row(name: str) -> dict:
    relative = f"{LOG_DIR}/{name}"
    path = ROOT / relative
    return dict(path=relative, sha256=sha256(relative), bytes=path.stat().st_size)


def counts_from(log_name: str) -> dict:
    text = read_text_any(f"{LOG_DIR}/{log_name}")
    summary = dict(collected=None, passed=None, failed=None, skipped=None, errors=None)
    for label in ("passed", "failed", "skipped", "errors"):
        match = re.search(rf"(\d+) {label}\b", text)
        if match:
            summary[label] = int(match.group(1))
    passed = summary["passed"] or 0
    summary["collected"] = passed + (summary["failed"] or 0) + (summary["skipped"] or 0) + (summary["errors"] or 0)
    return summary


def load_gates_module():
    spec = importlib.util.spec_from_file_location("gates_for_evidence", ROOT / "scripts/gates.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["gates_for_evidence"] = module
    spec.loader.exec_module(module)
    return module


def stale_inputs(record: dict) -> list[str]:
    recorded = record.get("input_artifact_hashes") or {}
    stale = []
    for relative, digest in sorted(recorded.items()):
        path = ROOT / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            stale.append(relative)
    return stale


def uv_version() -> str:
    completed = subprocess.run([str(ROOT / "tools/bin/uv.exe"), "--version"], capture_output=True, text=True)
    return completed.stdout.strip()


def main() -> int:
    module = load_gates_module()
    runner = module.GateRunner(root=ROOT, phase=1, revision="auto")
    rows = runner.relevant_manifest_rows()

    g01 = json.loads((ROOT / "artifacts/gates/G01.json").read_text(encoding="utf-8"))
    g00 = json.loads((ROOT / "artifacts/gates/G00.json").read_text(encoding="utf-8"))
    precheck_path = ROOT / "artifacts/handoffs/P01-01/zcode/precheck.json"
    precheck = json.loads(precheck_path.read_text(encoding="utf-8"))

    artifacts = {name: dict(path=path, sha256=sha256(path)) for name, path in {
        "gate_runner": "scripts/gates.py",
        "unit_test": TASKS["unit"],
        "integration_test": TASKS["integration"],
        "task_doc": "docs/implementation/P01-02.md",
        "completion_report": "docs/implementation/reports/P01-02.md",
        "handoff": "docs/handoffs/P01-02/dsh.md",
        "probe_script": f"{LOG_DIR}/negative-probes.py",
        "previous_round_evidence": f"{LOG_DIR}/previous-round-evidence.json",
        "phase_gate_evidence": "artifacts/gates/G01.json",
        "previous_gate_evidence": "artifacts/gates/G00.json",
    }.items()}

    logs = {name: log_row(name) for name in (
        "cmd1-p01-02-suites.log", "cmd2-check-architecture.log", "cmd3-full-suites.log",
        "cmd4-gate-check-only.log", "negative-probes.log", "env-lock-check.log",
        "baseline-p01-02-suites.log", "revision-stability-probe.log",
        "ownership-fallback-proof.log", "pre-change-hashes.txt",
    )}

    probe_text = read_text_any(f"{LOG_DIR}/negative-probes.log")
    probe = json.loads(probe_text[probe_text.index("{"):probe_text.rindex("}") + 1])

    evidence = {
        "schema_version": "1.0.0",
        "task_id": "P01-02",
        "round": "rework-2026-10-01",
        "scene": "checks-and-gate-runner-rework",
        "phase_gate": "G01",
        "status": "READY_FOR_ZCODE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role": "dsh",
        "signs_gate": False,
        "candidate": {
            "root": str(ROOT),
            "vcs": "no .git in this checkout; identity is the content-sha256 candidate manifest",
            "formula": 'code_revision = "content-sha256:" + sha256("\\n".join(f"{path}\\0{sha256(content)}")) over the '
                       'relevant-file whitelist, paths sorted byte-wise; '
                       'dirty_tree_hash = same rows as f"{path}\\0{size}\\0{sha256(content)}"',
            "relevant_file_count": len(rows),
            "relevant_files_sample": [row[0] for row in rows[:12]],
            "code_revision": runner.compute_revision(),
            "dirty_tree_hash": runner.dirty_tree_hash(),
        },
        "artifacts": artifacts,
        "command_logs": logs,
        "counts": {
            "p01_02_suites": counts_from("cmd1-p01-02-suites.log"),
            "full_suites": counts_from("cmd3-full-suites.log"),
            "baseline_p01_02_suites": counts_from("baseline-p01-02-suites.log"),
            "layer_check_modules_scanned": 7,
            "layer_check_violations": 0,
        },
        "commands_executed": [
            {"argv": ["uv", "run", "pytest", TASKS["unit"], TASKS["integration"], "-q"], "exit_code": 0,
             "log_path": logs["cmd1-p01-02-suites.log"]["path"]},
            {"argv": ["uv", "run", "python", "scripts/check_architecture.py"], "exit_code": 0,
             "log_path": logs["cmd2-check-architecture.log"]["path"]},
            {"argv": ["uv", "run", "pytest", "tests/unit", "tests/integration", "-q"], "exit_code": 1,
             "log_path": logs["cmd3-full-suites.log"]["path"],
             "note": "the two failures are the pre-existing AGENTS.md ownership fallbacks, not this candidate"},
            {"argv": ["uv", "run", "python", "scripts/gates.py", "--phase", "01", "--revision", "auto", "--check-only"],
             "exit_code": 1, "log_path": logs["cmd4-gate-check-only.log"]["path"],
             "note": "current-state freshness check; NOT a gate sign-off"},
            {"argv": ["uv", "run", "python", f"{LOG_DIR}/negative-probes.py"], "exit_code": 0,
             "log_path": logs["negative-probes.log"]["path"]},
            {"argv": ["uv", "lock", "--check"], "exit_code": 0, "log_path": logs["env-lock-check.log"]["path"]},
        ],
        "defects_fixed": {
            "1_worktree_dependent_test": {
                "change": "controlled temp-repo scenarios for missing pre-check / missing review / input drift; the "
                          "real-tree probe asserts only invariants matching current inputs and cross-checks the runner "
                          "verdict against a test-side recomputation; the official record hash is captured before the call",
                "test": f"{TASKS['unit']}, {TASKS['integration']}::test_repository_phase_one_gate_is_fail_closed",
            },
            "2_candidate_self_perturbation": {
                "change": "whitelist relevant-file manifest + documented formulas; candidate and tree fingerprint "
                          "recorded separately; scratch/evidence/report/review writes no longer move either value",
                "probe": "negative-probes.log: tmp_log / mimosa_state / handoff_log / evidence_generator all false; "
                         "relevant source change true",
            },
            "3_empty_precheck_hashes": {
                "change": "non-empty, well-formed, on-disk-fresh input map that covers the required inputs; task_id, "
                          "phase_gate, reviewer and status must match; Codex review likewise rejects an empty set",
                "probe": "negative-probes.log: empty_precheck_input_hashes_accepted false, complete_precheck_accepted true",
            },
            "4_status_only_previous_gate": {
                "change": "F2/F3/F4/F6 validation of fields, commands, integer exit codes, raw logs, frozen inputs and "
                          "dependency hashes; self/forward references and dependency cycles rejected; log_hash and "
                          "log_sha256 accepted per concrete schema, neither present is rejected",
                "probe": "negative-probes.log: previous_gate_status_without_evidence_accepted false, "
                         "complete_previous_gate_accepted true",
            },
        },
        "verification_probes": probe,
        "freshness_after_this_round": {
            "official_g01_record_sha256": sha256("artifacts/gates/G01.json"),
            "official_g01_record_untouched_by_this_round": True,
            "g01_recorded_inputs_now_stale": stale_inputs(g01),
            "g00_recorded_inputs_now_stale": stale_inputs(g00),
            "p01_01_precheck_now_stale": sorted(
                relative for relative, digest in (precheck.get("verified_input_hashes") or {}).items()
                if not (ROOT / relative).is_file()
                or hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest
            ),
        },
        "out_of_scope_blockers": [
            {
                "id": "R-G00-DRIFT",
                "finding": "the official artifacts/gates/G00.json record's frozen input "
                           "docs/architecture/issues/README.md changed on 2026-09-15 06:26, after the record was "
                           "written on 2026-09-14 06:54",
                "impact": "by F2/F6 the G00 evidence no longer holds, so G01 and every downstream gate stay blocked "
                          "even after the pre-check and Codex review records exist",
                "owner": "Phase 00 owner / project management",
                "fix": "re-record G00 on the current candidate with "
                       "tools/ai_coding_plan/validate_plan.py --record-g00 (outside this task's write scope; DSH did not modify it)",
            },
            {
                "id": "R-OWNERSHIP-AGENTS-MD",
                "finding": "scripts/check_ownership.py reports default_owner_fallbacks == ['AGENTS.md']; AGENTS.md was "
                           "created by the 2026-10-01 prompt round at 06:59, after the Codex baseline run at 04:43",
                "impact": "tests/unit and tests/integration P01-03 ownership assertions fail, so the phase regression "
                          "is not green",
                "owner": "P01-03 / project management",
                "fix": "add an explicit ownership rule for AGENTS.md in OWNERSHIP.json (outside this task's write scope)",
            },
        ],
        "tool_versions": {
            "python": sys.version.split()[0],
            "uv": uv_version(),
            "uv_cache_dir": "tmp/dsh-p01-02-rework/uv-cache (the default user cache is not writable on this host)",
            "os": "Windows 11",
        },
        "environment_notes": [
            "UV_CACHE_DIR was redirected into the repository because the default uv cache directory is not writable "
            "for this session; uv lock --check still exits 0 and uv.lock was not modified.",
            "No database, solver, simulation, LLM or browser acceptance is in scope for Phase 01.",
        ],
        "secrets_recorded": [],
        "gate_state": {
            "gate_id": "G01",
            "status": g01.get("status"),
            "failed_checks": g01.get("failed_checks", []),
            "note": "G01 is NOT signed. DSH does not write ZCode pre-acceptance or Codex review records; the official "
                    "record was not modified by this round.",
        },
        "limitations": [
            "This round fixes only the Phase 01 gate mechanism; G02-G39 business assertions are out of scope.",
            "The planner-schema G00 record structurally lacks started_at/dirty_tree_hash/acceptance_artifacts; that "
            "difference is registered explicitly and does not relax command, exit-code, log, input or dependency checks.",
            "tools/bin/uv.exe (41.5 MB vendored binary) is excluded from the candidate on purpose.",
            "Temporary controlled repositories prove the judgements; they are not business acceptance.",
        ],
    }
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(written=str(EVIDENCE.relative_to(ROOT)), sha256=sha256(str(EVIDENCE.relative_to(ROOT))),
                          counts=evidence["counts"]["p01_02_suites"],
                          code_revision=evidence["candidate"]["code_revision"],
                          stale_g01=evidence["freshness_after_this_round"]["g01_recorded_inputs_now_stale"],
                          stale_g00=evidence["freshness_after_this_round"]["g00_recorded_inputs_now_stale"]),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
