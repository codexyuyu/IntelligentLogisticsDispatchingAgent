"""Simulation engine protocol (P11-01)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from logistics_domain.simulation import SimulationRequest, SimulationResult

__all__ = ["SimulationEngine"]


@runtime_checkable
class SimulationEngine(Protocol):
    def run(self, request: SimulationRequest) -> SimulationResult:
        ...
