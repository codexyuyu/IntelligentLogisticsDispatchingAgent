"""SHARED contract, implementation owner PARTNER. Synchronous CPU work goes in workers."""
from typing import Protocol
from app.contracts.common import ValidationReport
from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult

class WarehouseScheduler(Protocol):
    def schedule(self, request: WarehouseScheduleRequest) -> WarehouseScheduleResult: ...

class WarehouseValidator(Protocol):
    """Independent post-solve check; a schedule without a report is not delivered."""

    validator_version: str

    def validate(
        self,
        request: WarehouseScheduleRequest,
        result: WarehouseScheduleResult,
    ) -> ValidationReport: ...
