"""SHARED ports for R05 cold-chain scheduling and independent checking.

Implementations live outside this package and are owned as follows:

* ``OccupancyTimelineBuilder`` and ``ColdChainValidator`` adapters: PARTNER
  (乙方) under ``backend/app/adapters/warehouse/``.
* The stdlib-only domain rules behind them: DSH (甲方) under
  ``backend/app/domain/coldchain_capacity.py`` and ``domain/joint_validation.py``.

The domain layer must not import Pydantic or a solver.  Mapping contract models
to plain dictionaries — and back — is the adapter's job, which is why the frozen
domain entry points below take and return mappings only.
"""
from typing import Any, Mapping, Protocol

from app.contracts.common import ValidationReport
from app.contracts.planning import (
    ColdChainValidationRequest,
    WarehouseScheduleRequest,
    WarehouseScheduleResult,
)
from app.contracts.coldchain import ScheduledOccupancy


class OccupancyTimelineBuilder(Protocol):
    """Resolve declared occupancies into planned ``[start_s, end_s)`` intervals."""

    def build(
        self,
        request: WarehouseScheduleRequest,
        result: WarehouseScheduleResult,
    ) -> tuple[ScheduledOccupancy, ...]: ...


class ColdChainValidator(Protocol):
    """Independent R05 validator port.

    ``validator_version`` is part of the evidence: a plan validated by one
    version cannot inherit another version's pass.
    """

    validator_version: str

    def validate(self, request: ColdChainValidationRequest) -> ValidationReport: ...


class JointValidationDomainFunction(Protocol):
    """Stdlib-only domain entry point (甲方 implements, 乙方 adapts).

    ``payload`` keys are frozen by contracts/changes/20261023-partner-r05-freeze.md
    and mirror :class:`ColdChainValidationRequest` with plain JSON values:
    ``snapshot``, ``operations``, ``handoffs``, ``coldchain``, ``rule_version``,
    ``source`` and ``horizon_s``.

    Returns a mapping with ``status``, ``checked_rule_ids``, ``violations`` (each
    ``rule_id``, ``object_ids``, ``message``, optional ``evidence``) and
    ``not_checked_rule_ids``.  The adapter converts that mapping into a
    :class:`ValidationReport` without adding or dropping rules.
    """

    def __call__(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...


__all__ = [
    'ColdChainValidator',
    'JointValidationDomainFunction',
    'OccupancyTimelineBuilder',
]
