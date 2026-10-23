"""Shared pytest fixtures for unit, integration, solver, simulation and e2e suites.

Discovered from the repository root for both ``tests/unit`` and ``tests/integration``.

Live-infrastructure policy (docs/architecture/IMPLEMENTATION_CONVENTIONS.md):

* a real test database is only used when ``TEST_DATABASE_URL`` is exported; the fixture
  never falls back to a personal database, and it refuses a non test-named database;
* database tests are wrapped in a transaction and rolled back, so no test leaves state;
* when the variable is absent the dependent test **fails** with an explicit reason
  instead of silently skipping, because a critical skip is not acceptance evidence for
  a Gate (docs/plan/PHASE_GATES.md).

No fixture in this file talks to a solver, the network or the file system outside the
repository root.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_UV_FALLBACK = REPO_ROOT / "tools/bin/uv.exe"  # bootstrap copy used on hosts without a global uv

# Phase 01 task ids whose DSH evidence files are part of the repository state.
DSH_EVIDENCE_TASKS = ("P01-01", "P01-02", "P01-03")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute repository root (all task-relative paths resolve from here)."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def scripts_dir(repo_root: Path) -> Path:
    directory = repo_root / "scripts"
    assert directory.is_dir(), "scripts/ must exist at the repository root"
    return directory


@pytest.fixture(scope="session")
def tool_resolver():
    """Resolve an executable the same way scripts/gates.py does (PATH, then tools/bin)."""

    def resolve(name: str) -> str:
        found = shutil.which(name)
        if found:
            return found
        for suffix in (".exe", ".cmd", ""):
            candidate = REPO_ROOT / "tools/bin" / f"{name}{suffix}"
            if candidate.is_file():
                return str(candidate)
        return name

    return resolve


@pytest.fixture(scope="session")
def clean_env():
    """Environment without inherited npm offline/cache-only switches."""

    def build(**overrides: str) -> dict[str, str]:
        env = dict(os.environ)
        for name in ("npm_config_offline", "npm_config_cache_mode", "npm_config_allow_scripts", "NPM_CONFIG_OFFLINE"):
            env.pop(name, None)
        env["PYTHONIOENCODING"] = "utf-8"
        env.update(overrides)
        return env

    return build


@pytest.fixture
def run_command(repo_root: Path, clean_env, tool_resolver):
    """Run a command with an argv list (never a shell) and return the completed process."""

    def run(argv: list[str], timeout: int = 900, cwd: Path | None = None):
        executable = list(argv)
        executable[0] = tool_resolver(executable[0])
        return subprocess.run(
            executable,
            cwd=cwd or repo_root,
            env=clean_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    return run


@pytest.fixture
def load_json():
    def load(path: Path) -> dict:
        assert path.is_file(), f"expected JSON artifact is missing: {path}"
        return json.loads(path.read_text(encoding="utf-8"))

    return load


@pytest.fixture
def sha256_of():
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    return digest


@pytest.fixture
def dsh_evidence(repo_root: Path, load_json):
    """DSH evidence for a Phase 01 task, or None when that task has not delivered yet."""

    def load(task_id: str) -> dict | None:
        assert task_id in DSH_EVIDENCE_TASKS, f"unexpected task id {task_id!r}"
        path = repo_root / "artifacts/handoffs" / task_id / "dsh" / "evidence.json"
        return load_json(path) if path.is_file() else None

    return load


@pytest.fixture(scope="session")
def python_executable() -> str:
    assert sys.version_info[:2] == (3, 12), "the workspace environment must run CPython 3.12"
    return sys.executable


# ------------------------------------------------------------------ test database


def _assert_test_database(url: str) -> None:
    lowered = url.lower()
    assert "test" in lowered, (
        f"TEST_DATABASE_URL must point at an isolated *test* database, got a URL without 'test': {url!r}"
    )
    for forbidden in ("postgres:postgres@localhost/", "postgres@localhost/logistics"):
        assert forbidden not in lowered, f"refusing an obvious production/default database: {url!r}"


@pytest.fixture(scope="session")
def database_url() -> str:
    """Session-scoped isolated PostgreSQL URL.

    Fails (never skips) when ``TEST_DATABASE_URL`` is absent: the environment manual for
    Phase 03 must define it, and a critical skip cannot be accepted as Gate evidence.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "TEST_DATABASE_URL is not set: start an isolated PostgreSQL (see the Phase 01 environment manual) "
            "and export TEST_DATABASE_URL=postgresql+psycopg://<user>:<pw>@127.0.0.1:5432/logistics_test",
            pytrace=False,
        )
    _assert_test_database(url)
    return url


@pytest.fixture
def db_connection(database_url: str):
    """PostgreSQL connection wrapped in a transaction that is always rolled back.

    The driver is imported lazily so that Phase 01 and Phase 02 suites do not require
    psycopg to be installed yet.
    """
    try:
        import psycopg  # type: ignore[import-not-found]
    except ModuleNotFoundError:  # pragma: no cover - depends on the lock file of a later phase
        pytest.fail(
            "psycopg is not installed in this environment; database tasks must add it to the workspace lock first",
            pytrace=False,
        )
    dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn) as connection:
        try:
            yield connection
        finally:
            connection.rollback()


@pytest.fixture
def db_cursor(db_connection):
    with db_connection.cursor() as cursor:
        yield cursor
        db_connection.rollback()


# ------------------------------------------------------------------ gate helpers


def _load_script_module(path: Path, unique_name: str):
    """Import a scripts/*.py file as an isolated module.

    The module must be registered in ``sys.modules`` before execution: dataclasses look
    their own module up by name while the class is being created.
    """
    import importlib.util

    assert path.is_file(), f"{path.name} must exist"
    spec = importlib.util.spec_from_file_location(unique_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(unique_name, None)
        raise
    return module


@pytest.fixture
def gate_runner_module(scripts_dir: Path):
    """Import scripts/gates.py as a module so unit tests can exercise its logic."""
    return _load_script_module(scripts_dir / "gates.py", "dsh_gates_under_test")


@pytest.fixture
def architecture_module(scripts_dir: Path):
    """Import scripts/check_architecture.py as a module."""
    return _load_script_module(scripts_dir / "check_architecture.py", "dsh_check_architecture_under_test")


@pytest.fixture
def ownership_module(scripts_dir: Path):
    """Import scripts/check_ownership.py as a module."""
    return _load_script_module(scripts_dir / "check_ownership.py", "dsh_check_ownership_under_test")
