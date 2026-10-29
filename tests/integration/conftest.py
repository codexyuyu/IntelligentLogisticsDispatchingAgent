"""Shared integration fixtures.

`warehouse_api` was originally defined inside ``test_warehouse_job_pipeline.py``.
Module-level fixtures are not visible to other modules, so any new integration
test that needs the real HTTP server + PostgreSQL + spawned worker could not see
it. Re-exporting it here makes it available to the whole ``tests/integration``
directory without duplicating its definition or touching the original file.
"""

from __future__ import annotations

from tests.integration.test_warehouse_job_pipeline import warehouse_api  # noqa: F401

__all__ = ["warehouse_api"]
