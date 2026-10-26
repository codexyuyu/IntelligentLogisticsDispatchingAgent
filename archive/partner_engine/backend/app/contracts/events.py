"""SHARED: simulation is a branch; events never silently modify production facts."""
from pydantic import AwareDatetime, StrictStr
from app.contracts.common import ContractModel, Id, NonNegativeInt, PositiveInt, Source
from app.contracts.entities import PlanningSnapshot
from app.domain.states import EventType

class EventPayload(ContractModel):
    delay_s: NonNegativeInt | None = None
    unavailable_until_s: NonNegativeInt | None = None
    replacement_matrix_id: Id | None = None
    affected_order_ids: tuple[Id, ...] = ()
    note: StrictStr | None = None

class DispatchEvent(ContractModel):
    event_id: Id
    event_type: EventType
    snapshot_id: Id
    expected_snapshot_version: PositiveInt
    object_id: Id
    occurred_at_s: NonNegativeInt
    received_at: AwareDatetime
    source: Source
    payload: EventPayload

class SimulationRequest(ContractModel):
    snapshot: PlanningSnapshot
    events: tuple[DispatchEvent, ...]
    horizon_s: PositiveInt
    random_seed: NonNegativeInt = 17

class SimulationResult(ContractModel):
    simulation_id: Id
    base_snapshot_id: Id
    final_snapshot: PlanningSnapshot
    emitted_events: tuple[DispatchEvent, ...]
