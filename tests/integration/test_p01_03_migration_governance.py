"""Integration checks for P01-03 ownership and legacy-migration governance.

The scripts are executed as real processes against the real repository and against a
sandbox repository, and the observable results are process exit codes plus the written
JSON report. The two task Test Cases are asserted here end-to-end:

1. ``packages/simulation/src/logistics_simulation/engine.py`` => ``B`` (via the frozen CLI
   entry point, not just an in-process function call);
2. an unmapped v0.1 status => explicit rejection with the offending value and the known
   vocabulary, and no side effect on the source tree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = "scripts/check_ownership.py"

# Sandbox asset owned by B, used by the legacy-coverage check.
B_OWNED_LEGACY_ASSET = "demo/data/transport/matrix.json"


def write_sandbox_repo(root: Path) -> None:
    """A minimal repository whose ownership rules can genuinely be verified."""
    (root / "OWNERSHIP.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "plan_version": "1.0.0",
                "rule": (
                    "Longest matching path prefix wins; an unlisted path falls back to default_owner. "
                    "The prefix match is segment-aware."
                ),
                "default_owner": "A",
                "owners": {"A": "everything else", "B": "transport, matrix and simulation"},
                "paths": {
                    "packages/simulation/": "B",
                    "packages/optimization/": "B",
                    "data/transport/": "B",
                    "apps/": "A",
                    "packages/domain/": "A",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "docs/architecture").mkdir(parents=True, exist_ok=True)
    (root / "docs/architecture/LEGACY_ADAPTATION.md").write_text(
        f"# sandbox legacy adaptation\n{B_OWNED_LEGACY_ASSET}\n", encoding="utf-8"
    )
    (root / "docs/architecture/BASELINE_INVENTORY.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "entries": [
                    {
                        "source_path": B_OWNED_LEGACY_ASSET,
                        "sha256": "0" * 64,
                        "owner": "B",
                        "disposition": "reuse",
                        "target_path": None,
                        "capability_evidence": "sandbox",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "contracts/changes").mkdir(parents=True, exist_ok=True)
    (root / "contracts/changes/README.md").write_text(
        "# contract changes\n输入影响 输出影响 迁移顺序 生成物 version_id schema_version\n", encoding="utf-8"
    )
    (root / "packages/simulation/src/logistics_simulation").mkdir(parents=True, exist_ok=True)
    (root / "packages/simulation/src/logistics_simulation/__init__.py").write_text(
        'PACKAGE_NAME = "logistics-simulation"\n', encoding="utf-8"
    )
    (root / "apps/backend/src/logistics_backend").mkdir(parents=True, exist_ok=True)
    (root / "apps/backend/src/logistics_backend/__init__.py").write_text(
        'API_PREFIX = "/api/v1"\n', encoding="utf-8"
    )


# ------------------------------------------------------- Test Case 1 (CLI, real process)


def test_test_case_1_cli_resolves_the_simulation_engine_to_b(run_command, repo_root: Path) -> None:
    """Test Case 1 through the published entry point: exit 0 and the owner is B."""
    result = run_command([
        "python", CHECKER, "--root", str(repo_root),
        "--resolve", "packages/simulation/src/logistics_simulation/engine.py",
    ])
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == (
        "packages/simulation/src/logistics_simulation/engine.py -> B (prefix: packages/simulation)"
    )


def test_cli_resolves_a_batch_and_reports_each_owner(run_command, repo_root: Path) -> None:
    result = run_command([
        "python", CHECKER,
        "--resolve", "packages/simulation/src/logistics_simulation/engine.py",
        "--resolve", "packages/optimization/src/logistics_optimization/matrix.py",
        "--resolve", "apps/backend/src/logistics_backend/bootstrap.py",
        "--resolve", "tests/simulation/test_kernel.py",
        "--resolve", "tests/unit/test_p01_03_migration_governance.py",
    ])
    assert result.returncode == 0, result.stdout + result.stderr
    lines = [line for line in result.stdout.splitlines() if "->" in line]
    owners = {line.split(" -> ")[1].split(" ")[0] for line in lines}
    assert owners == {"A", "B"}
    assert "packages/simulation/src/logistics_simulation/engine.py -> B" in result.stdout
    assert "apps/backend/src/logistics_backend/bootstrap.py -> A" in result.stdout
    assert "tests/unit/test_p01_03_migration_governance.py -> A" in result.stdout


def test_cli_rejects_a_path_outside_the_repository(run_command) -> None:
    result = run_command(["python", CHECKER, "--resolve", "../secrets.env"])
    assert result.returncode == 1, "an escaping path must be rejected, not guessed"
    assert "REJECTED" in result.stdout
    assert "escapes the repository root" in result.stdout


# --------------------------------------------------- Test Case 2 (rejection, no writes)


def test_test_case_2_unmapped_status_is_rejected_without_side_effects(run_command, ownership_module) -> None:
    """Test Case 2: 未映射 v0.1 状态 => 明确拒绝而非猜测."""
    snapshot = {
        path.relative_to(REPO_ROOT).as_posix(): path.read_bytes()
        for path in sorted(REPO_ROOT.rglob("*"))
        if path.is_file() and not ({"__pycache__", ".pytest_cache", ".ruff_cache"} & set(path.parts))
        and ".venv" not in path.parts and "node_modules" not in path.parts
    }

    with pytest.raises(ownership_module.LegacyConversionError) as error:
        ownership_module.convert_legacy_status("SolveStatus", "partially_solved")

    assert error.value.kind == "SolveStatus"
    assert error.value.value == "partially_solved"
    assert "no explicit v0.1 -> v1 conversion" in str(error.value)
    # The known v0.1 vocabulary must be reported so the decision can be made deliberately.
    assert error.value.known == tuple(sorted([
        "optimal", "feasible", "infeasible_proven", "no_solution_within_budget",
        "invalid_input", "model_invalid", "needs_clarification", "unsupported", "stale", "conflict",
    ]))

    after = {
        path.relative_to(REPO_ROOT).as_posix(): path.read_bytes()
        for path in sorted(REPO_ROOT.rglob("*"))
        if path.is_file() and not ({"__pycache__", ".pytest_cache", ".ruff_cache"} & set(path.parts))
        and ".venv" not in path.parts and "node_modules" not in path.parts
    }
    assert after == snapshot, "a rejected conversion must not modify the repository"

    # Rejection is reproducible through a separate process as well.
    probe = run_command([
        "python", "-c",
        "import sys; sys.path.insert(0, 'scripts'); import check_ownership as m;"
        " m.convert_legacy_status('SolveStatus', 'partially_solved')",
    ])
    assert probe.returncode != 0
    assert "LegacyConversionError" in probe.stderr
    assert "partially_solved" in probe.stderr


def test_legacy_minutes_convert_across_a_process_boundary(run_command) -> None:
    probe = run_command([
        "python", "-c",
        "import sys; sys.path.insert(0, 'scripts'); import check_ownership as m;"
        "c = m.convert_legacy_minutes(2); print('CONV', c.target_value, c.legacy_version, c.target_version)",
    ])
    assert probe.returncode == 0, probe.stderr
    assert "CONV 120 0.1.0 1.0.0" in probe.stdout


# --------------------------------------------------------------- real repository checks


def test_real_repository_ownership_check_passes(run_command, repo_root: Path) -> None:
    result = run_command(["python", CHECKER, "--root", str(repo_root), "--json"])
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["passed"] is True
    assert report["violation_count"] == 0
    assert report["coverage"]["files_scanned"] > 100
    assert report["coverage"]["default_owner_fallbacks"] == []
    assert report["owner_count"] == 2
    assert report["schema_version"] == "1.0.0"


def test_every_b_owned_prefix_is_declared_for_a_real_or_pending_path(run_command, repo_root: Path) -> None:
    report = json.loads(run_command(["python", CHECKER, "--root", str(repo_root), "--json"]).stdout)
    existing = {prefix for prefix in json.loads((repo_root / "OWNERSHIP.json").read_text(encoding="utf-8"))["paths"]}
    for item in report["pending_owner_paths"]:
        assert item["code"] == "OWN-B-PATH-PENDING"
        assert any(prefix in item["detail"] for prefix in existing)
    assert report["passed"] is True, "pending paths must not be reported as violations"


def test_sandbox_repository_passes_and_reports_pending_paths(run_command, tmp_path: Path) -> None:
    sandbox = tmp_path / "repo"
    sandbox.mkdir()
    write_sandbox_repo(sandbox)
    result = run_command(["python", str(REPO_ROOT / CHECKER), "--root", str(sandbox), "--json"])
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["passed"] is True
    assert report["coverage"]["files_scanned"] >= 4


def test_sandbox_with_a_legacy_import_fails_the_check(run_command, tmp_path: Path) -> None:
    sandbox = tmp_path / "repo"
    sandbox.mkdir()
    write_sandbox_repo(sandbox)
    (sandbox / "apps/backend/src/logistics_backend/bootstrap.py").write_text(
        "from app.adapters.routing.ortools_solver import OrToolsRoutingSolver\n", encoding="utf-8"
    )
    result = run_command(["python", str(REPO_ROOT / CHECKER), "--root", str(sandbox), "--json"])
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["passed"] is False
    codes = {violation["code"] for violation in report["violations"]}
    assert "OWN-LEGACY-IMPORT" in codes
    detail = next(v["detail"] for v in report["violations"] if v["code"] == "OWN-LEGACY-IMPORT")
    assert "app.adapters.routing.ortools_solver" in detail


def test_sandbox_missing_governance_documents_fail_closed(run_command, tmp_path: Path) -> None:
    sandbox = tmp_path / "repo"
    sandbox.mkdir()
    write_sandbox_repo(sandbox)
    (sandbox / "contracts/changes/README.md").unlink()
    result = run_command(["python", str(REPO_ROOT / CHECKER), "--root", str(sandbox), "--json"])
    assert result.returncode == 1
    codes = {violation["code"] for violation in json.loads(result.stdout)["violations"]}
    assert "OWN-CONTRACT-CHANGE" in codes


def test_legacy_adaptation_document_is_not_a_second_contract(run_command, repo_root: Path) -> None:
    """It must present itself as the conversion authority, not a competing contract."""
    text = (repo_root / "docs/architecture/LEGACY_ADAPTATION.md").read_text(encoding="utf-8")
    assert "唯一权威" in text
    assert "只读" in text
    assert "不迁移" in text
    # The v1 target vocabulary is referenced, never redefined.
    assert "DATA_CONTRACTS.md" in text and "DOMAIN_CATALOG.md" in text


def test_ownership_check_agrees_with_the_layer_check_about_legacy_imports(run_command, repo_root: Path) -> None:
    """Both governance checks must be able to run together without contradictory verdicts."""
    ownership = run_command(["python", CHECKER, "--root", str(repo_root)])
    architecture = run_command(["python", "scripts/check_architecture.py", "--root", str(repo_root)])
    assert ownership.returncode == 0, ownership.stdout
    assert architecture.returncode == 0, architecture.stdout
    assert "violations=0" in ownership.stdout
    assert "violations=0" in architecture.stdout
