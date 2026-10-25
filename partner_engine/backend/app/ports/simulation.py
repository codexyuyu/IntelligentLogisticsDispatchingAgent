"""SHARED contract, implementation owner B. Synchronous CPU work goes in workers."""
from typing import Protocol
from app.contracts.events import SimulationRequest, SimulationResult

class Simulator(Protocol):
    def simulate(self, request: SimulationRequest) -> SimulationResult: ...
