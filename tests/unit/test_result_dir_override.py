"""The result artifact directory must be overridable so that every process of
one deployment resolves the same location.

Regression context: ``RESULT_DIR`` used to be a bare cwd-relative path. When the
API and the worker were started from different working copies, a completed job
reported ``result_not_ready: job result artifact is unavailable`` even though the
artifact existed in the other directory.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from uuid import uuid4

from logistics_backend.application import artifacts


def _reload():
    return importlib.reload(artifacts)


def test_default_result_dir_stays_cwd_relative(monkeypatch):
    monkeypatch.delenv("LOGISTICS_RESULTS_DIR", raising=False)
    module = _reload()
    assert module.RESULT_DIR == Path("artifacts/results")


def test_result_dir_can_be_pinned_with_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGISTICS_RESULTS_DIR", str(tmp_path))
    module = _reload()
    assert module.RESULT_DIR == tmp_path
    assert module.RESULT_DIR.is_absolute()

    store = module.ResultArtifactStore()
    result_id = uuid4()
    digest = store.write(result_id, {"ok": True})
    assert (tmp_path / f"{result_id}.json").exists()
    assert store.read(result_id, digest) == b'{"ok":true}'


def test_artifact_written_once_is_readable_by_a_fresh_store(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGISTICS_RESULTS_DIR", str(tmp_path))
    module = _reload()
    result_id = uuid4()
    digest = module.ResultArtifactStore().write(result_id, {"kind": "optimization"})

    # A new store instance resolving the same directory must see the artifact,
    # which is exactly what the API process does after the worker completed a job.
    assert module.ResultArtifactStore().read(result_id, digest) == b'{"kind":"optimization"}'
