"""Imported evidence and R05/R08/R09 integration commands; schema 2.0.0."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from logistics_contracts.coldchain import ColdChainSnapshotDTO
from logistics_contracts.planning import PlanningSnapshotDTO, WarehouseTaskDTO
from logistics_contracts.warehouse import SetupPolicyDTO


class Boundary(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: Literal['2.0.0'] = '2.0.0'


class ScenarioImport(Boundary):
    name: str = Field(min_length=1, max_length=128)
    source_kind: Literal['synthetic', 'enterprise']
    source_ref: str = Field(min_length=1, max_length=512)
    snapshot: PlanningSnapshotDTO
    warehouse_tasks: tuple[WarehouseTaskDTO, ...]
    coldchain_fields: ColdChainSnapshotDTO | None = None
    setup_policy: SetupPolicyDTO = SetupPolicyDTO()
    available_at_s: dict[UUID, StrictInt]


class RecoveryInput(Boundary):
    task_id: UUID
    resource_id: UUID
    disruption_at_s: StrictInt = Field(ge=0)
    recovery_s: StrictInt = Field(gt=0)


class IntegrationRun(Boundary):
    scenario_id: UUID
    seed: StrictInt = Field(default=0, ge=0, le=2**31-1)
    budget_ms: StrictInt = Field(default=4000, ge=100, le=12000)
    recoveries: tuple[RecoveryInput, ...] = ()


class RevokeInput(Boundary):
    task_id: UUID
    now_s: StrictInt = Field(ge=0)
    expected_digest: str = Field(pattern=r'^[a-f0-9]{64}$')


class ExperimentInput(Boundary):
    scenario_id: UUID
    budget_ms: StrictInt = Field(default=1000, ge=100, le=4000)
    seeds: tuple[StrictInt, ...] = tuple(range(10))
