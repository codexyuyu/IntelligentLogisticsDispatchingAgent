"""Unit checks for the P01-01 workspace bootstrap (task: 建立目标 Monorepo 与可复现依赖环境).

These checks are pure configuration/structure assertions over the committed files:
workspace topology, src-layout, dependency direction, pinned baselines and the
"explicit failure instead of fake success" rule for not-yet-implemented packages.

Nothing here needs a network or a solver; the runtime half (frozen install, six
package imports, lock idempotency) lives in tests/integration.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PYTHON_WORKSPACE_MEMBERS = {
    "packages/domain": "logistics_domain",
    "packages/contracts": "logistics_contracts",
    "packages/optimization": "logistics_optimization",
    "packages/simulation": "logistics_simulation",
    "packages/agents": "logistics_agents",
    "packages/evaluation": "logistics_evaluation",
    "apps/backend": "logistics_backend",
}

# The six packages the task interface requires to be importable after a workspace install.
REQUIRED_IMPORT_PACKAGES = (
    "logistics_domain",
    "logistics_contracts",
    "logistics_optimization",
    "logistics_simulation",
    "logistics_agents",
    "logistics_evaluation",
)

# Architecture boundary: no package may pull these in through its own metadata.
FORBIDDEN_DEPENDENCY_PREFIXES = (
    "fastapi",
    "uvicorn",
    "starlette",
    "pydantic",
    "sqlalchemy",
    "alembic",
    "ortools",
    "simpy",
    "simpy",
    "numpy",
    "pandas",
)

ALLOWED_INTERNAL_PREFIX = "logistics-"


def read_toml(relative: str) -> dict:
    path = REPO_ROOT / relative
    assert path.is_file(), f"{relative} must exist"
    with path.open("rb") as handle:
        return tomllib.load(handle)


def read_text(relative: str) -> str:
    path = REPO_ROOT / relative
    assert path.is_file(), f"{relative} must exist"
    return path.read_text(encoding="utf-8")


def declared_dependencies(relative: str) -> list[str]:
    data = read_toml(relative)
    return [str(item) for item in data.get("project", {}).get("dependencies", [])]


def distribution_name(requirement: str) -> str:
    return re.split(r"[<>=!~\[; ]", requirement, maxsplit=1)[0].strip().lower()


# --------------------------------------------------------------------------- root


def test_root_is_uv_workspace_with_declared_members() -> None:
    data = read_toml("pyproject.toml")
    members = data["tool"]["uv"]["workspace"]["members"]
    assert members == ["packages/*", "apps/backend"], "workspace members must cover packages/* and apps/backend"
    assert data["tool"]["uv"]["package"] is False, "the aggregator root must not pretend to ship a package"
    package_dirs = sorted(p.parent.relative_to(REPO_ROOT).as_posix() for p in REPO_ROOT.glob("packages/*/pyproject.toml"))
    assert package_dirs == [
        "packages/agents",
        "packages/contracts",
        "packages/domain",
        "packages/evaluation",
        "packages/optimization",
        "packages/simulation",
    ]


def test_root_aggregates_every_workspace_member() -> None:
    declared = {distribution_name(dep) for dep in declared_dependencies("pyproject.toml")}
    members = {read_toml(f"{path}/pyproject.toml")["project"]["name"] for path in PYTHON_WORKSPACE_MEMBERS}
    missing = members - declared
    assert not missing, f"uv sync --frozen must install every member; root does not aggregate: {sorted(missing)}"
    sources = read_toml("pyproject.toml")["tool"]["uv"]["sources"]
    assert set(sources) == members, "every member must resolve to its workspace path"
    assert all(value == {"workspace": True} for value in sources.values())


def test_python_baseline_is_pinned_to_312() -> None:
    assert read_text(".python-version").strip() == "3.12"
    requires = read_toml("pyproject.toml")["project"]["requires-python"]
    assert requires == ">=3.12,<3.13", "the compatible baseline is 3.12, not 'latest'"


def test_node_baseline_is_pinned_to_22() -> None:
    assert read_text(".node-version").strip() == "22"
    root_manifest = json.loads(read_text("package.json"))
    assert root_manifest["engines"]["node"] == ">=22 <25"
    assert root_manifest["workspaces"] == ["apps/frontend"]
    assert root_manifest["private"] is True


def test_npm_workspace_manifest_declares_frontend_scripts() -> None:
    frontend = json.loads(read_text("apps/frontend/package.json"))
    assert frontend["name"] == "@logistics/frontend"
    assert frontend["private"] is True
    for script in ("dev", "build", "test", "contracts:generate", "contracts:check"):
        assert script in frontend["scripts"], f"frontend must expose the {script} script"
    assert frontend["scripts"]["build"].startswith("tsc"), "build must type-check before bundling"


def test_playwright_runner_is_configured_at_the_root() -> None:
    config = read_text("playwright.config.ts")
    assert "./apps/frontend/e2e" in config, "e2e specs live under apps/frontend/e2e"
    assert "defineConfig" in config


# --------------------------------------------------------------- per-member layout


@pytest.mark.parametrize(("relative_dir", "module"), sorted(PYTHON_WORKSPACE_MEMBERS.items()))
def test_member_uses_src_layout_with_public_init(relative_dir: str, module: str) -> None:
    data = read_toml(f"{relative_dir}/pyproject.toml")
    assert data["build-system"]["build-backend"] == "hatchling.build"
    assert data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [f"src/{module}"]
    init_file = REPO_ROOT / relative_dir / "src" / module / "__init__.py"
    assert init_file.is_file(), f"{module} must expose a public __init__.py"
    assert f'PACKAGE_NAME = "{module.replace("_", "-")}"' in init_file.read_text(encoding="utf-8")


@pytest.mark.parametrize(("relative_dir", "module"), sorted(PYTHON_WORKSPACE_MEMBERS.items()))
def test_member_python_floor_matches_root(relative_dir: str, module: str) -> None:
    assert module, "parametrised for a readable test id"
    assert read_toml(f"{relative_dir}/pyproject.toml")["project"]["requires-python"] == ">=3.12,<3.13"


def test_pure_domain_member_declares_no_dependencies() -> None:
    assert declared_dependencies("packages/domain/pyproject.toml") == [], (
        "domain must stay framework-free and depend on nothing"
    )


@pytest.mark.parametrize(
    ("relative_dir", "forbidden"),
    [
        ("packages/domain", FORBIDDEN_DEPENDENCY_PREFIXES),
        ("packages/contracts", ("fastapi", "uvicorn", "sqlalchemy", "ortools", "simpy")),
        ("packages/optimization", ("fastapi", "uvicorn", "sqlalchemy")),
        ("packages/simulation", ("fastapi", "uvicorn", "sqlalchemy")),
        ("packages/agents", ("fastapi", "uvicorn", "sqlalchemy", "ortools", "simpy")),
        ("packages/evaluation", ("fastapi", "uvicorn", "sqlalchemy", "ortools", "simpy")),
    ],
)
def test_dependency_boundaries_are_respected(relative_dir: str, forbidden: tuple[str, ...]) -> None:
    declared = [distribution_name(dep) for dep in declared_dependencies(f"{relative_dir}/pyproject.toml")]
    violations = sorted(name for name in declared if name.startswith(forbidden))
    assert not violations, f"{relative_dir} must not depend on {violations}"


def test_backend_is_the_only_member_declaring_a_web_framework() -> None:
    for relative_dir in PYTHON_WORKSPACE_MEMBERS:
        declared = [distribution_name(dep) for dep in declared_dependencies(f"{relative_dir}/pyproject.toml")]
        uses_web_framework = any(name.startswith(("fastapi", "uvicorn", "starlette")) for name in declared)
        assert uses_web_framework == (relative_dir == "apps/backend"), (
            f"only apps/backend may depend on a web framework, violated by {relative_dir}"
        )


def test_engine_dependencies_stay_in_their_adapter_package() -> None:
    optimization = [distribution_name(dep) for dep in declared_dependencies("packages/optimization/pyproject.toml")]
    simulation = [distribution_name(dep) for dep in declared_dependencies("packages/simulation/pyproject.toml")]
    assert any(name == "ortools" for name in optimization)
    assert any(name == "simpy" for name in simulation)
    for relative_dir in ("packages/domain", "packages/contracts", "packages/agents", "packages/evaluation"):
        declared = [distribution_name(dep) for dep in declared_dependencies(f"{relative_dir}/pyproject.toml")]
        assert not [name for name in declared if name in {"ortools", "simpy"}], (
            f"{relative_dir} must not depend on a solver or simulation engine"
        )


def test_no_workspace_dependency_cycles() -> None:
    graph = {
        path: {distribution_name(dep) for dep in declared_dependencies(f"{path}/pyproject.toml")}
        for path in PYTHON_WORKSPACE_MEMBERS
    }
    by_name = {read_toml(f"{path}/pyproject.toml")["project"]["name"]: path for path in graph}

    def visit(node: str, seen: tuple[str, ...]) -> None:
        assert node not in seen, f"dependency cycle: {' -> '.join((*seen, node))}"
        for dependency in sorted(graph[node]):
            if dependency in by_name:
                visit(by_name[dependency], (*seen, node))

    for member in graph:
        visit(member, ())


def test_dependency_graph_direction_matches_architecture() -> None:
    graph = {
        name: {distribution_name(dep) for dep in declared_dependencies(f"{path}/pyproject.toml")}
        for name, path in (
            (read_toml(f"{member}/pyproject.toml")["project"]["name"], member)
            for member in PYTHON_WORKSPACE_MEMBERS
        )
    }
    assert graph["logistics-domain"] == set()
    assert graph["logistics-contracts"] == {"logistics-domain", "pydantic"}
    assert graph["logistics-optimization"] == {"logistics-domain", "ortools"}
    assert graph["logistics-simulation"] == {"logistics-domain", "simpy"}
    assert graph["logistics-agents"] == {"logistics-contracts"}
    assert graph["logistics-evaluation"] == {"logistics-contracts"}


# ------------------------------------------------------------------ pin / lock rules


def test_lock_files_exist_and_are_not_hand_written_placeholders() -> None:
    uv_lock = read_text("uv.lock")
    first_line = uv_lock.splitlines()[0].strip()
    assert first_line == "version = 1", f"uv.lock must declare lock format version 1, found {first_line!r}"
    assert uv_lock.count("[[package]]") >= 7, "uv.lock must contain the resolved workspace members and dependencies"
    for module in REQUIRED_IMPORT_PACKAGES:
        assert f'name = "{module.replace("_", "-")}"' in uv_lock, f"uv.lock must pin {module}"
    npm_lock = read_text("package-lock.json")
    parsed = json.loads(npm_lock)
    assert parsed["lockfileVersion"] == 3
    assert "apps/frontend" in parsed["packages"], "package-lock must record the npm workspace"
    assert parsed["packages"]["node_modules/@playwright/test"]["integrity"].startswith("sha512-")


def test_uv_lock_records_the_runtime_engine_versions() -> None:
    uv_lock = read_text("uv.lock")
    assert 'name = "ortools"' in uv_lock
    assert 'name = "simpy"' in uv_lock
    assert 'name = "fastapi"' in uv_lock


def test_dev_tooling_is_pinned_in_the_root_project() -> None:
    data = read_toml("pyproject.toml")
    dev = {distribution_name(entry) for entry in data["dependency-groups"]["dev"]}
    assert {"pytest", "ruff", "pytest-timeout", "pytest-asyncio"} <= dev, "dev checks must be locked by the root"
    pytest_config = data["tool"]["pytest"]["ini_options"]
    assert pytest_config["testpaths"] == ["tests"]
    assert "--strict-markers" in pytest_config["addopts"]


# --------------------------------------------------- no fake implementation rule


@pytest.mark.parametrize("module", sorted(PYTHON_WORKSPACE_MEMBERS.values()))
def test_public_init_never_returns_a_placeholder_success(module: str) -> None:
    relative = next(path for path, name in PYTHON_WORKSPACE_MEMBERS.items() if name == module)
    source = read_text(f"{relative}/src/{module}/__init__.py")
    # Strip the module docstring: it may legitimately mention the rules it refuses to break.
    body = re.sub(r'^\s*""".*?"""\s*', "", source, count=1, flags=re.S)
    assert "raise NotImplementedError" in body, f"{module} must fail loudly for undelivered APIs"
    assert "__getattr__" in body, "undelivered names must be routed through an explicit __getattr__ failure"
    assert "return True" not in body and "return 200" not in body, f"{module} must not return a fixed success"
    for banned in ("todo:", "fixme", "notimplemented  #", "stub:", "hardcoded answer"):
        assert banned not in body.lower(), f"{module} must not carry a {banned} marker"


def test_contract_version_is_declared_once_per_layer() -> None:
    domain = read_text("packages/domain/src/logistics_domain/__init__.py")
    assert 'SCHEMA_VERSION = "1.0.0"' in domain
    assert 'LEGACY_CONTRACT_VERSION = "0.1.0"' in domain, "the legacy version must stay visible for migration"
    for relative, module in PYTHON_WORKSPACE_MEMBERS.items():
        source = read_text(f"{relative}/src/{module}/__init__.py")
        assert re.search(r'SCHEMA_VERSION = "1\.0\.0"', source), f"{module} must declare the frozen schema version"


def test_backend_declares_the_contract_api_prefix() -> None:
    assert 'API_PREFIX = "/api/v1"' in read_text("apps/backend/src/logistics_backend/__init__.py")


def test_demo_is_never_imported_by_the_new_workspace() -> None:
    for relative, module in PYTHON_WORKSPACE_MEMBERS.items():
        source = read_text(f"{relative}/src/{module}/__init__.py")
        assert "demo" not in source.replace("demonst", ""), f"{module} must not reference the read-only demo tree"
        assert "from app" not in source and "import app" not in source, f"{module} must not import the legacy app package"


def test_workspace_bootstrap_files_listed_by_the_task_all_exist() -> None:
    expected = [
        ".node-version",
        ".python-version",
        "apps/backend/pyproject.toml",
        "apps/backend/src/logistics_backend/__init__.py",
        "apps/frontend/package.json",
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
        "uv.lock",
    ]
    missing = [relative for relative in expected if not (REPO_ROOT / relative).is_file()]
    assert not missing, f"declared P01-01 deliverables missing: {missing}"
