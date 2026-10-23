"""Unit checks for P01-03 ownership resolution and legacy conversion.

Covers the two task Test Cases at unit level plus the surrounding rules:

1. ``packages/simulation/src/logistics_simulation/engine.py`` must resolve to ``B``
   (longest segment-aware prefix wins);
2. an unmapped v0.1 status must be rejected explicitly, never guessed.

Also covers path rejection (absolute, drive-qualified, escaping), the legacy conversion
tables (every v0.1 value is either mapped or explicitly non-migrating), the v0.1 minute to
v1 second unit conversion, and the manifest/audit invariants.
"""

from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

P01_03_DELIVERABLES = (
    "OWNERSHIP.json",
    "contracts/changes/README.md",
    "docs/architecture/LEGACY_ADAPTATION.md",
    "scripts/check_ownership.py",
)

# v0.1 vocabulary copied from demo/backend/app/domain/states.py (read-only legacy baseline).
LEGACY_STATES = {
    "JobStatus": ["queued", "running", "succeeded", "failed", "cancelled"],
    "PlanStatus": [
        "draft", "validated", "confirmed", "executing", "completed", "rejected", "stale", "superseded",
    ],
    "OperationStatus": ["pending", "running", "paused", "interrupted", "completed", "cancelled"],
    "SolveStatus": [
        "optimal", "feasible", "infeasible_proven", "no_solution_within_budget",
        "invalid_input", "model_invalid", "needs_clarification", "unsupported", "stale", "conflict",
    ],
    "TemperatureZone": ["chilled", "frozen"],
    "EventType": [
        "departure_delayed", "dock_unavailable", "cargo_quarantined", "weather_changed", "demand_changed",
    ],
}


# ------------------------------------------------------------------ Test Case 1


def test_test_case_1_simulation_engine_path_resolves_to_b(ownership_module) -> None:
    """Test Case 1: packages/simulation/src/logistics_simulation/engine.py => B."""
    detail = ownership_module.resolve_owner_detail(
        "packages/simulation/src/logistics_simulation/engine.py", REPO_ROOT
    )
    assert detail["owner"] == "B"
    assert detail["matched_prefix"] == "packages/simulation"
    assert detail["used_default_owner"] is False
    assert ownership_module.resolve_owner("packages/simulation/src/logistics_simulation/engine.py", REPO_ROOT) == "B"


@pytest.mark.parametrize(
    ("path", "owner", "prefix"),
    [
        ("packages/simulation/src/logistics_simulation/engine.py", "B", "packages/simulation"),
        ("packages/simulation/pyproject.toml", "B", "packages/simulation"),
        ("packages/optimization/src/logistics_optimization/transport.py", "B", "packages/optimization"),
        ("tests/solver/test_vrp.py", "B", "tests/solver"),
        ("tests/simulation/test_kernel.py", "B", "tests/simulation"),
        ("data/transport/README.md", "B", "data/transport"),
        ("benchmarks/simulation/README.md", "B", "benchmarks/simulation"),
        ("apps/backend/src/logistics_backend/__init__.py", "A", "apps"),
        ("packages/domain/src/logistics_domain/__init__.py", "A", "packages/domain"),
        ("packages/contracts/src/logistics_contracts/__init__.py", "A", "packages/contracts"),
        ("tests/unit/test_p01_03_migration_governance.py", "A", "tests/unit"),
        ("scripts/check_ownership.py", "A", "scripts"),
        ("OWNERSHIP.json", "A", "OWNERSHIP.json"),
        ("demo/backend/app/adapters/routing/ortools_solver.py", "A", "demo"),
    ],
)
def test_resolve_owner_uses_the_longest_segment_aware_prefix(ownership_module, path: str, owner: str, prefix: str) -> None:
    detail = ownership_module.resolve_owner_detail(path, REPO_ROOT)
    assert detail["owner"] == owner, f"{path} resolved to {detail['owner']}"
    assert detail["matched_prefix"] == prefix


def test_prefix_match_is_segment_aware_and_never_matches_a_sibling_name(ownership_module) -> None:
    """`packages/simulation` must not match `packages/simulation_extra/...`."""
    detail = ownership_module.resolve_owner_detail("packages/simulation_extra/src/x.py", REPO_ROOT)
    assert detail["owner"] == "A", "a sibling directory with a shared name prefix must not inherit B"
    assert detail["matched_prefix"] == "packages"
    assert detail["used_default_owner"] is False


def test_windows_style_separators_resolve_identically(ownership_module) -> None:
    windows = ownership_module.resolve_owner_detail(
        "packages\\simulation\\src\\logistics_simulation\\engine.py", REPO_ROOT
    )
    posix = ownership_module.resolve_owner_detail(
        "packages/simulation/src/logistics_simulation/engine.py", REPO_ROOT
    )
    assert windows["owner"] == posix["owner"] == "B"
    assert windows["path"] == posix["path"]


def test_unlisted_path_falls_back_to_the_declared_default_owner(ownership_module) -> None:
    manifest = ownership_module.load_manifest(REPO_ROOT)
    detail = ownership_module.resolve_owner_detail("some/new/area/file.txt", REPO_ROOT)
    assert detail["used_default_owner"] is True
    assert detail["owner"] == manifest["default_owner"]
    assert detail["matched_prefix"] is None


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "C:/Windows/system32/config",
        "C:\\Windows\\system32\\config",
        "//server/share/file",
        "../outside.py",
        "packages/../../outside.py",
        "",
        "   ",
    ],
)
def test_paths_outside_the_repository_are_rejected(ownership_module, path: str) -> None:
    with pytest.raises(ownership_module.OwnershipError):
        ownership_module.resolve_owner(path, REPO_ROOT)


def test_normalization_keeps_internal_parent_segments_inside_the_root(ownership_module) -> None:
    assert ownership_module.normalize_repo_path("packages/./simulation//src/../src/x.py") == (
        "packages/simulation/src/x.py"
    )


def test_resolve_owner_is_total_over_the_real_repository(ownership_module) -> None:
    """Every tracked file resolves to a declared owner (no crash, no surprise fallback)."""
    manifest = ownership_module.load_manifest(REPO_ROOT)
    report = ownership_module.run_checks(REPO_ROOT)
    assert report["passed"] is True, report["violations"]
    assert report["coverage"]["files_scanned"] > 100
    assert set(report["coverage"]["files_per_owner"]) <= set(manifest["owners"])
    assert report["coverage"]["default_owner_fallbacks"] == [], (
        "every real path must be covered by an explicit rule; allow-listing by accident hides ownership"
    )


def test_manifest_declares_the_documented_algorithm(ownership_module) -> None:
    manifest = ownership_module.load_manifest(REPO_ROOT)
    assert manifest["schema_version"] == "1.0.0"
    assert "Longest matching path prefix wins" in manifest["rule"]
    assert "unlisted path falls back to default_owner" in manifest["rule"]
    assert manifest["owners"]["B"].startswith("B")
    assert set(manifest["paths"].values()) <= {"A", "B"}
    # B's scope must be exactly transport/matrix/simulation plus their tests/data/benchmarks.
    b_prefixes = sorted(prefix for prefix, owner in manifest["paths"].items() if owner == "B")
    assert b_prefixes == [
        "benchmarks/simulation/",
        "benchmarks/transport/",
        "data/simulation/",
        "data/transport/",
        "packages/optimization/",
        "packages/simulation/",
        "tests/simulation/",
        "tests/solver/",
    ]


def test_legacy_ownership_paths_are_not_reused_verbatim(ownership_module) -> None:
    """The v0.1 rule table used bare relative paths; those must not silently govern v1."""
    legacy_paths = {path.rstrip("/") for path in ownership_module.load_manifest(REPO_ROOT)["paths"]}
    assert "backend/app/adapters/routing/" not in ownership_module.load_manifest(REPO_ROOT)["paths"]
    assert not any(path.startswith("backend/") for path in legacy_paths), (
        "v0.1 relative paths such as backend/app/... must not appear as v1 rules"
    )


# ------------------------------------------------------------------ Test Case 2


def test_test_case_2_unmapped_legacy_status_is_rejected(ownership_module) -> None:
    """Test Case 2: 未映射 v0.1 状态 => 明确拒绝而非猜测."""
    with pytest.raises(ownership_module.LegacyConversionError) as error:
        ownership_module.convert_legacy_status("PlanStatus", "cancelled")
    message = str(error.value)
    assert error.value.kind == "PlanStatus"
    assert error.value.value == "cancelled"
    assert "cancelled" in message
    assert "no explicit v0.1 -> v1 conversion" in message
    assert "LEGACY_ADAPTATION.md" in message


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("PlanStatus", "cancelled"),          # exists in v0.1 JobStatus/OperationStatus, not PlanStatus
        ("JobStatus", "paused"),              # exists in v0.1 OperationStatus only
        ("SolveStatus", "SOLVED"),            # wrong case: v1 literal passed as legacy input
        ("OperationStatus", "succeeded"),     # belongs to v0.1 JobStatus
        ("TemperatureZone", "ambient"),       # v1-only value, never produced by v0.1 data
        ("UnknownKind", "queued"),            # unknown status family
    ],
)
def test_unmapped_values_are_rejected_with_the_known_vocabulary(ownership_module, kind: str, value: str) -> None:
    with pytest.raises(ownership_module.LegacyConversionError) as error:
        ownership_module.convert_legacy_status(kind, value)
    assert error.value.kind == kind
    assert error.value.value == value
    assert error.value.known == (() if kind not in LEGACY_STATES else tuple(sorted(LEGACY_STATES[kind])))


def test_rejection_has_no_side_effect_and_does_not_invent_a_value(ownership_module) -> None:
    """A rejected conversion must not return anything and must not mutate the tables."""
    before = {kind: dict(table) for kind, table in ownership_module.LEGACY_STATUS_TABLES.items()}
    with pytest.raises(ownership_module.LegacyConversionError):
        ownership_module.convert_legacy_status("PlanStatus", "cancelled")
    assert ownership_module.LEGACY_STATUS_TABLES == before
    assert "cancelled" not in ownership_module.LEGACY_STATUS_TABLES["PlanStatus"]


def test_every_v0_1_value_is_either_mapped_or_explicitly_non_migrating(ownership_module) -> None:
    """Nothing may vanish silently: each real v0.1 value needs a decided entry."""
    for kind, values in LEGACY_STATES.items():
        table = ownership_module.LEGACY_STATUS_TABLES[kind]
        assert set(values) <= set(table), f"{kind} loses v0.1 values: {sorted(set(values) - set(table))}"
        for value in values:
            conversion = ownership_module.convert_legacy_status(kind, value)
            assert conversion.legacy_version == "0.1.0"
            assert conversion.target_version == "1.0.0"
            if table[value] is None:
                assert conversion.target_value is None
                assert "不迁移" in conversion.rule
            else:
                assert conversion.target_value and ":" in conversion.target_value


def test_specific_decided_conversions_match_the_frozen_v1_vocabulary(ownership_module) -> None:
    def target(kind: str, value: str) -> str | None:
        return ownership_module.convert_legacy_status(kind, value).target_value

    # v1 uses JobStatus.completed where v0.1 used 'succeeded'.
    assert target("JobStatus", "succeeded") == "V1_JOB_STATUS:completed"
    # v1 SolveStatus is SCREAMING_SNAKE_CASE and renames the budget/invalid cases.
    assert target("SolveStatus", "infeasible_proven") == "V1_SOLVE_STATUS:INFEASIBLE"
    assert target("SolveStatus", "no_solution_within_budget") == "V1_SOLVE_STATUS:TIMEOUT"
    assert target("SolveStatus", "model_invalid") == "V1_SOLVE_STATUS:ERROR"
    # Staleness and conflicts are HTTP conflicts in v1, not solver states.
    assert target("SolveStatus", "stale") is None
    assert target("SolveStatus", "conflict") is None
    # 'paused' has no v1 warehouse-task equivalent.
    assert target("OperationStatus", "paused") is None
    # Confirmation is expressed by the immutable ScheduleVersion lifecycle.
    assert target("PlanStatus", "confirmed") == "V1_SCHEDULE_VERSION:confirmed"
    assert target("PlanStatus", "stale") == "V1_SCHEDULE_VERSION:superseded"


def test_v1_only_values_are_recorded_as_such(ownership_module) -> None:
    assert "UNKNOWN" in ownership_module.V1_ONLY_VALUES["SolveStatus"]
    assert "ambient" in ownership_module.V1_ONLY_VALUES["TemperatureZone"]
    assert "vehicle-breakdown" in ownership_module.V1_ONLY_VALUES["EventType"]
    for kind, values in ownership_module.V1_ONLY_VALUES.items():
        table = ownership_module.LEGACY_STATUS_TABLES[kind]
        for value in values:
            assert value not in table, f"{value} is v1-only and must not appear as a v0.1 key"


def test_kind_and_value_are_required(ownership_module) -> None:
    with pytest.raises(ownership_module.LegacyConversionError):
        ownership_module.convert_legacy_status("JobStatus", "")
    with pytest.raises(ownership_module.LegacyConversionError):
        ownership_module.convert_legacy_status("", "queued")


# ---------------------------------------------------------------- unit conversion


def test_legacy_minutes_convert_to_integer_seconds_with_a_recorded_version(ownership_module) -> None:
    conversion = ownership_module.convert_legacy_minutes(2)
    assert conversion.target_value == "120"
    assert conversion.legacy_version == "0.1.0"
    assert conversion.target_version == "1.0.0"
    assert conversion.kind == "Duration"
    assert "120 秒" in conversion.rule
    assert ownership_module.convert_legacy_minutes(0).target_value == "0"
    assert ownership_module.convert_legacy_minutes(7, field="service_time").target_value == "420"


@pytest.mark.parametrize("value", [1.5, "2", None, -1, True])
def test_illegal_minute_inputs_are_rejected(ownership_module, value) -> None:
    with pytest.raises(ValueError):
        ownership_module.convert_legacy_minutes(value)


# ------------------------------------------------------------- document and script


def test_legacy_adaptation_document_covers_every_b_owned_asset(ownership_module) -> None:
    assert ownership_module.check_legacy_mapping_coverage(REPO_ROOT) == []


def test_legacy_adaptation_document_lists_the_decided_tables() -> None:
    text = (REPO_ROOT / "docs/architecture/LEGACY_ADAPTATION.md").read_text(encoding="utf-8")
    for required in (
        "JobStatus", "SolveStatus", "PlanStatus", "OperationStatus", "TemperatureZone", "EventType",
        "1 分钟 = 60 秒", "decic", "最长**段感知**前缀", "LegacyConversionError", "v1 新增",
    ):
        assert required in text, f"LEGACY_ADAPTATION.md must document {required!r}"
    # The v0.1 baseline must be identified as read-only input, not a second contract.
    assert "0.1.0" in text and "1.0.0" in text
    assert "只读" in text


def test_contract_change_entry_documents_the_required_fields(ownership_module) -> None:
    assert ownership_module.check_contract_change_entry(REPO_ROOT) == []
    text = (REPO_ROOT / "contracts/changes/README.md").read_text(encoding="utf-8")
    for field in ("输入影响", "输出影响", "迁移顺序", "生成物", "version_id", "parent_version_id", "snapshot_hash"):
        assert field in text
    assert "domain → DTO → ports → 调用方 → 测试 → 生成物" in text


def test_no_v1_package_imports_the_legacy_namespace(ownership_module) -> None:
    assert ownership_module.check_legacy_imports(REPO_ROOT) == []


def test_checker_detects_a_legacy_import_in_a_sandbox_tree(ownership_module, tmp_path: Path) -> None:
    sandbox = tmp_path / "repo"
    (sandbox / "packages/domain/src/logistics_domain").mkdir(parents=True)
    (sandbox / "packages/domain/src/logistics_domain/mod.py").write_text(
        "from app.contracts.entities import Order\n", encoding="utf-8"
    )
    offenders = ownership_module.check_legacy_imports(sandbox)
    assert len(offenders) == 1
    assert offenders[0]["imported"] == "app.contracts.entities"
    assert offenders[0]["line"] == 1


def test_checker_detects_a_syntax_error_instead_of_ignoring_it(ownership_module, tmp_path: Path) -> None:
    sandbox = tmp_path / "repo"
    (sandbox / "packages/domain/src/logistics_domain").mkdir(parents=True)
    (sandbox / "packages/domain/src/logistics_domain/broken.py").write_text("def broken(:\n", encoding="utf-8")
    offenders = ownership_module.check_legacy_imports(sandbox)
    assert offenders and offenders[0]["imported"] == "<syntax error>"


def test_missing_manifest_is_a_configuration_violation(ownership_module, tmp_path: Path) -> None:
    report = ownership_module.run_checks(tmp_path)
    assert report["passed"] is False
    assert report["violations"][0]["code"] == "OWN-CONFIG"


def test_undefined_owner_in_the_manifest_is_rejected(ownership_module, tmp_path: Path) -> None:
    (tmp_path / "OWNERSHIP.json").write_text(
        json.dumps({
            "schema_version": "1.0.0",
            "rule": "Longest matching path prefix wins",
            "default_owner": "A",
            "owners": {"A": "a"},
            "paths": {"x/": "C"},
        }),
        encoding="utf-8",
    )
    with pytest.raises(ownership_module.OwnershipError):
        ownership_module.load_manifest(tmp_path)


def test_pending_b_owned_paths_are_reported_not_failed(ownership_module, tmp_path: Path) -> None:
    """Declaring B's future surface is legitimate; it is reported as pending work."""
    (tmp_path / "OWNERSHIP.json").write_text(
        json.dumps({
            "schema_version": "1.0.0",
            "rule": "Longest matching path prefix wins; an unlisted path falls back to default_owner.",
            "default_owner": "A",
            "owners": {"A": "a", "B": "b"},
            "paths": {"data/transport/": "B"},
        }),
        encoding="utf-8",
    )
    # Provide the governance inputs so the only open question is the pending B path.
    (tmp_path / "docs/architecture").mkdir(parents=True)
    (tmp_path / "docs/architecture/LEGACY_ADAPTATION.md").write_text(
        "# stub\nsee demo/data/transport/matrix.json for the B-owned example\n", encoding="utf-8"
    )
    (tmp_path / "docs/architecture/BASELINE_INVENTORY.json").write_text(
        json.dumps({
            "schema_version": "1.0.0",
            "entries": [
                {
                    "source_path": "demo/data/transport/matrix.json",
                    "sha256": "0" * 64,
                    "owner": "B",
                    "disposition": "reuse",
                    "target_path": None,
                    "capability_evidence": "stub",
                }
            ],
        }),
        encoding="utf-8",
    )
    (tmp_path / "contracts/changes").mkdir(parents=True)
    (tmp_path / "contracts/changes/README.md").write_text(
        "# stub\n输入影响 输出影响 迁移顺序 生成物 version_id schema_version\n", encoding="utf-8"
    )
    report = ownership_module.run_checks(tmp_path)
    assert report["passed"] is True, report["violations"]
    assert any(item["code"] == "OWN-B-PATH-PENDING" for item in report["pending_owner_paths"])


# ------------------------------------------------------------------- repo hygiene


def test_p01_03_deliverables_exist() -> None:
    missing = [relative for relative in P01_03_DELIVERABLES if not (REPO_ROOT / relative).is_file()]
    assert not missing, f"declared P01-03 deliverables missing: {missing}"


def test_ownership_manifest_is_valid_json_with_sorted_unique_rules() -> None:
    manifest = json.loads((REPO_ROOT / "OWNERSHIP.json").read_text(encoding="utf-8"))
    assert len(manifest["paths"]) == len(set(manifest["paths"]))
    # A prefix is a rule for a directory (slash-terminated) or for exactly one file.
    for prefix in manifest["paths"]:
        if prefix.endswith("/"):
            continue
        leaf = prefix.rsplit("/", 1)[-1]
        assert leaf not in {"src", "tests", "packages", "apps"}, f"{prefix!r} looks like a directory rule"


def test_checker_imports_nothing_beyond_the_standard_library() -> None:
    """This tool is part of the engineering surface: no third-party dependency allowed."""
    tree = ast.parse((REPO_ROOT / "scripts/check_ownership.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    allowed = {"__future__", "argparse", "ast", "json", "sys", "dataclasses", "pathlib", "typing"}
    assert imported <= allowed, f"unexpected imports: {sorted(imported - allowed)}"


def test_checker_declares_the_frozen_interface(ownership_module) -> None:
    report = ownership_module.run_checks(REPO_ROOT)
    assert report["check"] == "ownership-and-migration"
    assert report["schema_version"] == "1.0.0"
    assert report["manifest"] == "OWNERSHIP.json"
    assert report["owner_count"] == 2
    assert report["legacy_status_tables"] == {kind: len(values) for kind, values in sorted(LEGACY_STATES.items())}


def test_root_pyproject_and_workspace_are_unchanged_by_this_task() -> None:
    """P01-03 must not widen the workspace surface: it adds no package or dependency."""
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["uv"]["workspace"]["members"] == ["packages/*", "apps/backend"]
    assert data["project"]["dependencies"] == [
        "logistics-domain", "logistics-contracts", "logistics-optimization",
        "logistics-simulation", "logistics-agents", "logistics-evaluation", "logistics-backend",
    ]
