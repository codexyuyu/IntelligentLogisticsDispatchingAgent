"""SHARED contract, implementation owner B. Synchronous CPU work goes in workers."""
from typing import Protocol
from app.contracts.planning import RoutingRequest, RoutingResult

class RoutingSolver(Protocol):
    def solve(self, request: RoutingRequest) -> RoutingResult: ...
