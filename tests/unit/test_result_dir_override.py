"""The result artifact directory must be overridable so that every process of
one deployment resolves the same location.

Regression context: ``RESULT_DIR`` used to be a bare cwd-relative path. When the
API and the worker were started from different working copies, a completed job
reported ``result_not_ready: job result artifact is unavailable`` even though the
artifact existed in the other directory.

The resolver is a pure function on purpose: reloading the module inside a test
creates a second ``ResultArtifactStore`` class object, which breaks the worker
subprocess tests that pickle their handler arguments.
"""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from logistics_backend.application.artifacts import (
    RESULT_DIR,
    ResultArtifactStore,
    resolve_result_dir,
)


def test_default_result_dir_stays_cwd_relative():
    assert resolve_result_dir({}) == Path("artifacts/results")
    # The module constant keeps the same default unless the whole process sets it.
    if not os.environ.get("LOGISTICS_RESULTS_DIR"):
        assert RESULT_DIR == Path("artifacts/results")


def test_result_dir_can_be_pinned_with_environment_variable(tmp_path):
    resolved = resolve_result_dir({"LOGISTICS_RESULTS_DIR": str(tmp_path)})
    assert resolved == tmp_path
    assert resolved.is_absolute()

    store = ResultArtifactStore(directory=resolved)
    result_id = uuid4()
    digest = store.write(result_id, {"ok": True})
    assert (tmp_path / f"{result_id}.json").exists()
    assert store.read(result_id, digest) == b'{"ok":true}'


def test_artifact_written_once_is_readable_by_a_fresh_store(tmp_path):
    result_id = uuid4()
    digest = ResultArtifactStore(directory=tmp_path).write(result_id, {"kind": "optimization"})

    # A new store instance resolving the same directory must see the artifact,
    # which is exactly what the API process does after the worker completed a job.
    assert ResultArtifactStore(directory=tmp_path).read(result_id, digest) == b'{"kind":"optimization"}'
