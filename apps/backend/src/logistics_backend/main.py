"""Run with uvicorn logistics_backend.main:create_app --factory."""
from logistics_backend.bootstrap import create_app

__all__ = ["create_app"]
