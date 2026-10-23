"""Minimal no-build workbench shell served by the backend.

This is a development shell, not the final React application: it exercises the real HTTP
contract with plain `fetch` so the backend can be inspected without an npm install.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["workbench"])
WORKBENCH = Path(__file__).resolve().parents[4] / "frontend" / "workbench.html"


@router.get("/workbench", response_class=HTMLResponse, include_in_schema=False)
def workbench() -> str:
    if not WORKBENCH.is_file():
        return "<h1>Workbench unavailable</h1><p>apps/frontend/workbench.html is missing.</p>"
    return WORKBENCH.read_text(encoding="utf-8")
