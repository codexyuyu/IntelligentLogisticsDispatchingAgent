"""Integration checks for the P01-01 workspace bootstrap.

These checks cross real boundaries instead of re-reading configuration:

* test case 1 — a frozen workspace install is importable: the six packages are
  resolved and imported from their installed locations with user-site-packages
  disabled, and `uv lock --check` confirms the lock file matches the manifests.
* test case 2 — `npm ci` is repeatable: running it twice leaves package-lock.json
  byte-identical.
* repository integrity — the read-only `demo/` baseline is unchanged, verified
  against the hash recorded by the task evidence file.

Every external tool that is genuinely unavailable is reported with an explicit
reason. A required tool that is present but fails will fail the test.
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

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = REPO_ROOT / "artifacts/handoffs/P01-01/dsh/evidence.json"

REQUIRED_IMPORT_PACKAGES = (
    "logistics_domain",
    "logistics_contracts",
    "logistics_optimization",
    "logistics_simulation",
    "logistics_agents",
    "logistics_evaluation",
)

WORKSPACE_MEMBER_MODULES = {
    "logistics_domain": "packages/domain/src/logistics_domain",
    "logistics_contracts": "packages/contracts/src/logistics_contracts",
    "logistics_optimization": "packages/optimization/src/logistics_optimization",
    "logistics_simulation": "packages/simulation/src/logistics_simulation",
    "logistics_agents": "packages/agents/src/logistics_agents",
    "logistics_evaluation": "packages/evaluation/src/logistics_evaluation",
    "logistics_backend": "apps/backend/src/logistics_backend",
}

pytestmark = pytest.mark.integration


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subprocess_env() -> dict[str, str]:
    env = dict(os.environ)
    # The harness host may export offline/cache-only npm settings; the bootstrap
    # check must run with a normal registry configuration.
    for name in ("npm_config_offline", "npm_config_cache_mode", "npm_config_allow_scripts", "NPM_CONFIG_OFFLINE"):
        env.pop(name, None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run(argv: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env=subprocess_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def find_uv() -> str | None:
    """Locate uv: PATH first, then the bootstrap copy recorded in the task report."""
    found = shutil.which("uv")
    if found:
        return found
    for candidate in (REPO_ROOT / "tools/bin/uv.exe", REPO_ROOT / "tools/bin/uv"):
        if candidate.is_file():
            return str(candidate)
    return None


def find_npm() -> str | None:
    for name in ("npm.cmd", "npm"):
        found = shutil.which(name)
        if found:
            return found
    return None


def demo_tree_fingerprint() -> tuple[int, str]:
    """Fingerprint over exactly the demo/ files registered by the baseline inventory.

    The inventory is the P00-01 evidence base for the legacy tree, so it is also the right
    input here: it is file-only (the G00 recorder rejects directory paths) and therefore
    deterministic, unlike a whole-tree scan that would pick up .pytest_cache and the
    .package-lock.json npm writes into node_modules.
    """
    inventory = json.loads(
        (REPO_ROOT / "docs/architecture/BASELINE_INVENTORY.json").read_text(encoding="utf-8")
    )
    paths = sorted(entry["source_path"] for entry in inventory["entries"])
    if not paths:
        pytest.fail("the baseline inventory registers no demo/ file; the integrity check would be vacuous")
    digest = hashlib.sha256()
    for relative in paths:
        path = REPO_ROOT / relative
        assert path.is_file(), f"registered baseline file disappeared: {relative}"
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("utf-8"))
        digest.update(b"\n")
    return len(paths), digest.hexdigest()


@pytest.fixture(scope="module")
def evidence() -> dict:
    if not EVIDENCE_PATH.is_file():
        pytest.fail(f"task evidence file is required for the integrity checks: {EVIDENCE_PATH}")
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


# ------------------------------------------------------- test case 1: frozen sync


def test_frozen_workspace_install_is_importable() -> None:
    """干净环境 uv sync --frozen => 成功导入六包.

    The probe runs with isolation (-I) from a throwaway working directory, so the source
    tree is not on sys.path and the six packages can only resolve through the installed
    environment. A uv workspace installs members as editable distributions whose .pth
    files point at each member's real src-layout directory, so the assertion is that every
    module resolves to its own workspace source directory (or, for a non-editable install,
    inside the .venv) and NOT to an unrelated location.
    """
    probe = (
        "import importlib, json, pathlib, sys\n"
        f"names = {list(REQUIRED_IMPORT_PACKAGES)!r}\n"
        "resolved = {}\n"
        "for name in names:\n"
        "    module = importlib.import_module(name)\n"
        "    resolved[name] = str(pathlib.Path(module.__file__).resolve())\n"
        "print('PROBE_JSON=' + json.dumps({'executable': sys.executable, 'resolved': resolved}))\n"
    )
    result = run([sys.executable, "-I", "-c", probe])
    assert result.returncode == 0, f"six-package import failed:\n{result.stdout}\n{result.stderr}"
    payload = json.loads(
        next(line for line in result.stdout.splitlines() if line.startswith("PROBE_JSON="))[len("PROBE_JSON="):]
    )
    resolved: dict[str, str] = payload["resolved"]
    assert sorted(resolved) == sorted(REQUIRED_IMPORT_PACKAGES)
    venv_root = Path(payload["executable"]).resolve().parents[1]
    assert venv_root.name == ".venv", f"the probe must run inside the workspace .venv, got {venv_root}"
    for module, location in sorted(resolved.items()):
        actual = Path(location).resolve()
        expected = (REPO_ROOT / WORKSPACE_MEMBER_MODULES[module]).resolve() / "__init__.py"
        assert actual == expected or actual.is_relative_to(venv_root), (
            f"{module} resolved to an unexpected location: {actual} (expected {expected} or an install under {venv_root})"
        )


def test_every_member_is_installed_as_an_editable_workspace_distribution() -> None:
    """The six packages must be importable because they are installed, not because of cwd."""
    probe = (
        "import json\n"
        "from importlib.metadata import distribution, PackageNotFoundError\n"
        f"names = {sorted(WORKSPACE_MEMBER_MODULES)!r}\n"
        "out = {}\n"
        "for name in names:\n"
        "    try:\n"
        "        dist = distribution(name)\n"
        "        direct = dist.read_text('direct_url.json')\n"
        "        out[name] = {'has_direct_url': bool(direct), 'editable_marker': bool(direct and 'dir_info' in direct)}\n"
        "    except PackageNotFoundError:\n"
        "        out[name] = None\n"
        "print('EDITABLE_JSON=' + json.dumps(out))\n"
    )
    result = run([sys.executable, "-c", probe])
    assert result.returncode == 0, result.stderr
    installed = json.loads(
        next(line for line in result.stdout.splitlines() if line.startswith("EDITABLE_JSON="))[len("EDITABLE_JSON="):]
    )
    for module, details in sorted(installed.items()):
        assert details is not None, f"{module} is not installed in the workspace environment"
        assert details["has_direct_url"], f"{module} was not installed from a local workspace path"


def test_frozen_lock_matches_the_manifests() -> None:
    """`uv lock --check` proves uv.lock is in sync with the member manifests."""
    uv = find_uv()
    if uv is None:
        pytest.fail("uv is required to verify a frozen workspace install and is neither on PATH nor in tools/bin")
    result = run([uv, "lock", "--check"], timeout=600)
    assert result.returncode == 0, f"uv.lock is out of date with the workspace manifests:\n{result.stderr}"


def test_installed_distributions_cover_every_member(evidence: dict) -> None:
    expected = {
        "logistics-domain": "0.1.0",
        "logistics-contracts": "0.1.0",
        "logistics-optimization": "0.1.0",
        "logistics-simulation": "0.1.0",
        "logistics-agents": "0.1.0",
        "logistics-evaluation": "0.1.0",
        "logistics-backend": "0.1.0",
    }
    probe = (
        "import json\n"
        "from importlib.metadata import version, PackageNotFoundError\n"
        f"names = {sorted(expected)!r}\n"
        "out = {}\n"
        "for name in names:\n"
        "    try:\n"
        "        out[name] = version(name)\n"
        "    except PackageNotFoundError:\n"
        "        out[name] = None\n"
        "print('DIST_JSON=' + json.dumps(out))\n"
    )
    result = run([sys.executable, "-c", probe])
    assert result.returncode == 0, result.stderr
    installed = json.loads(
        next(line for line in result.stdout.splitlines() if line.startswith("DIST_JSON="))[len("DIST_JSON="):]
    )
    assert installed == expected, f"every workspace member must be installed with its pinned version: {installed}"
    assert evidence["python_workspace_members"] == sorted(expected)


def test_uv_lock_hash_matches_recorded_evidence(evidence: dict) -> None:
    recorded = evidence["artifacts"]["uv_lock"]
    assert sha256_file(REPO_ROOT / "uv.lock") == recorded["sha256"], "uv.lock changed after the task evidence was written"
    assert recorded["sha256"] == evidence["dependencies_lock"]["uv_lock_sha256"]


# ------------------------------------------------------- test case 2: npm ci twice


def test_npm_ci_is_repeatable_and_lock_file_is_unchanged() -> None:
    """npm ci 重复执行 => 锁文件无变化."""
    npm = find_npm()
    if npm is None:
        pytest.fail("npm is required for the workspace bootstrap check and was not found on PATH")
    lock_path = REPO_ROOT / "package-lock.json"
    before = sha256_file(lock_path)
    observed: list[str] = []
    for attempt in range(2):
        result = run([npm, "ci", "--no-audit", "--no-fund"], timeout=900)
        assert result.returncode == 0, f"npm ci attempt {attempt + 1} failed:\n{result.stdout}\n{result.stderr}"
        observed.append(sha256_file(lock_path))
    assert observed == [before, before], f"package-lock.json changed across npm ci runs: {[before, *observed]}"
    assert (REPO_ROOT / "node_modules/@playwright/test/package.json").is_file(), (
        "npm ci must install the declared playwright runtime"
    )


def test_npm_lock_hash_matches_recorded_evidence(evidence: dict) -> None:
    recorded = evidence["artifacts"]["package_lock"]
    assert sha256_file(REPO_ROOT / "package-lock.json") == recorded["sha256"], (
        "package-lock.json changed after the task evidence was written"
    )
    assert recorded["sha256"] == evidence["dependencies_lock"]["package_lock_sha256"]


def test_node_runtime_satisfies_the_pinned_baseline(evidence: dict) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to verify the Node baseline and was not found on PATH")
    result = run([node, "--version"])
    assert result.returncode == 0, result.stderr
    reported = result.stdout.strip().lstrip("v")
    major = int(reported.split(".")[0])
    pinned = (REPO_ROOT / ".node-version").read_text(encoding="utf-8").strip()
    assert pinned == "22"
    assert 22 <= major < 25, f"node {reported} is outside the supported baseline 22..24"
    assert evidence["tool_versions"]["node"] == reported


def test_python_runtime_satisfies_the_pinned_baseline(evidence: dict) -> None:
    reported = "%d.%d.%d" % sys.version_info[:3]
    assert (REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"
    assert sys.version_info[:2] == (3, 12), f"the workspace environment must run CPython 3.12, got {reported}"
    assert evidence["tool_versions"]["python"] == reported


# ------------------------------------------------------- read-only demo integrity


def test_legacy_demo_tree_is_untouched(evidence: dict) -> None:
    if not (REPO_ROOT / "demo").is_dir():
        pytest.skip("legacy demo/ is a gitignored machine-local asset; absent in this checkout")
    recorded = evidence["legacy_demo"]
    count, digest = demo_tree_fingerprint()
    assert digest == recorded["tree_sha256"], (
        "the read-only demo/ baseline changed; P01-01 must not move, edit or delete legacy assets"
    )
    assert count == recorded["file_count"], f"demo file count changed: {count} != {recorded['file_count']}"
    assert recorded["hash_algorithm"] == "sha256"


def test_workspace_bootstrap_did_not_touch_demo_zip(evidence: dict) -> None:
    if not (REPO_ROOT / "demo.zip").is_file():
        pytest.skip("demo.zip is a gitignored machine-local asset; absent in this checkout")
    recorded = evidence["legacy_demo"]["demo_zip"]
    assert sha256_file(REPO_ROOT / "demo.zip") == recorded["sha256"]
    declared = (REPO_ROOT / "demo.zip.sha256").read_text(encoding="utf-8").split()[0]
    assert declared == recorded["sha256"], "the shipped demo.zip checksum no longer matches the archive"
