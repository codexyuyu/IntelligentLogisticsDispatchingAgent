"""Transport solver protocol (P06-01); implementations live in the optimization layer."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from logistics_domain.planning import SolveBudget
from logistics_domain.transport import TransportProblem, TransportSolution

__all__ = ["TransportSolver"]


@runtime_checkable
class TransportSolver(Protocol):
    def solve(self, request: TransportProblem, budget: SolveBudget) -> TransportSolution:
        ...
