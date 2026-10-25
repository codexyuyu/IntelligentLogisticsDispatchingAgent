"""SHARED: transport-level dependencies, no business decisions."""
from typing import Annotated
from fastapi import Depends, Header
from app.bootstrap import Services, build_services

IdempotencyKey = Annotated[str, Header(alias='Idempotency-Key', min_length=1, max_length=128)]


def get_services() -> Services:
    """FastAPI dependency: the composition-root graph, built once per process."""
    return build_services()


ServicesDep = Annotated[Services, Depends(get_services)]
