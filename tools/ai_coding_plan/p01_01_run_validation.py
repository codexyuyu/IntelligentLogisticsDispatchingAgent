"""Run the three mandatory P01-01 validation commands and archive raw logs.

Writes stdout/stderr transcripts plus a machine-readable summary to
artifacts/handoffs/P01-01/dsh/logs/. Exits non-zero if any command fails, so the
script itself is a failure-closed gate.

Usage: python tools/ai_coding_plan/p01_01_run_validation.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "artifacts/handoffs/P01-01/dsh/logs"

COMMANDS: list[tuple[str, list[str]]] = [
    (
        "pytest",
        [
            "uv", "run", "pytest",
            "tests/unit/test_p01_01_workspace_bootstrap.py",
            "tests/integration/test_p01_01_workspace_bootstrap.py",
            "-q",
        ],
    ),
    ("uv_sync_frozen", ["uv", "sync", "--frozen"]),
    ("npm_ci", ["npm", "ci"]),
]


def resolve_uv() -> str:
    found = shutil.which("uv")
    if found:
        return found
    for candidate in (ROOT / "tools/bin/uv.exe", ROOT / "tools/bin/uv"):
        if candidate.is_file():
            return str(candidate)
    raise SystemExit("uv not found on PATH or in tools/bin")


def resolve_npm() -> str:
    for name in ("npm.cmd", "npm"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("npm not found on PATH")


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for name in ("npm_config_offline", "npm_config_cache_mode", "npm_config_allow_scripts", "NPM_CONFIG_OFFLINE"):
        env.pop(name, None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    uv = resolve_uv()
    npm = resolve_npm()
    summary = {"schema_version": "1.0.0", "task_id": "P01-01", "commands": []}
    ok = True
    for name, argv in COMMANDS:
        concrete = [uv if token == "uv" else npm if token == "npm" else token for token in argv]
        transcript = LOG_DIR / f"{name}.log"
        with transcript.open("w", encoding="utf-8") as handle:
            handle.write(f"# argv: {json.dumps(concrete, ensure_ascii=False)}\n")
            handle.write(f"# cwd: {ROOT}\n")
            handle.write(f"# started_at: {dt.datetime.now(dt.timezone.utc).isoformat()}\n\n")
            handle.flush()
            result = subprocess.run(
                concrete, cwd=ROOT, env=clean_env(), capture_output=True, text=True, check=False
            )
            handle.write("## stdout\n")
            handle.write(result.stdout)
            handle.write("\n## stderr\n")
            handle.write(result.stderr)
            handle.write(f"\n## exit_code: {result.returncode}\n")
        entry = {
            "id": name,
            "argv": concrete,
            "cwd": str(ROOT),
            "exit_code": result.returncode,
            "log_path": transcript.relative_to(ROOT).as_posix(),
            "log_sha256": hashlib.sha256(transcript.read_bytes()).hexdigest(),
            "stdout_tail": result.stdout.strip().splitlines()[-3:],
        }
        if name == "pytest":
            last = [line for line in result.stdout.splitlines() if " passed" in line or " failed" in line]
            entry["test_counts"] = last[-1].strip() if last else "unknown"
        summary["commands"].append(entry)
        ok = ok and result.returncode == 0
        print(f"{name}: exit={result.returncode} log={entry['log_path']}")
    summary["status"] = "passed" if ok else "failed"
    (LOG_DIR / "validation-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
