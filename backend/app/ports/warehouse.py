"""SHARED contract, implementation owner AC. Synchronous CPU work goes in workers."""
from typing import Protocol
from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult

class WarehouseScheduler(Protocol):
    def schedule(self, request: WarehouseScheduleRequest) -> WarehouseScheduleResult: ...
