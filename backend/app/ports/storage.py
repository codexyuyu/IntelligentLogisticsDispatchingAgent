"""SHARED: AC-owned storage. Commit operation is one atomic transaction."""
from typing import Protocol
from app.contracts.entities import PlanningSnapshot
from app.contracts.planning import CandidatePlan
from app.contracts.http import ConfirmPlanRequest, ConfirmPlanResponse

class PlanningSnapshotStore(Protocol):
    def get_snapshot(self, snapshot_id: str, expected_version: int) -> PlanningSnapshot: ...

class PlanCommitStore(Protocol):
    def confirm(self, plan: CandidatePlan, request: ConfirmPlanRequest, idempotency_key: str) -> ConfirmPlanResponse: ...
