"""SHARED: sole source of exchange types. No ORM, solver or model SDK objects."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, AwareDatetime, model_validator
from app.domain.states import SolveStatus

CONTRACT_VERSION = '0.2.0'
Id = Annotated[StrictStr, Field(pattern=r'^[a-z][a-z0-9]*_[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')]
NonNegativeInt = Annotated[StrictInt, Field(ge=0)]
PositiveInt = Annotated[StrictInt, Field(gt=0)]
Hash = Annotated[StrictStr, Field(pattern=r'^[a-f0-9]{64}$')]

class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)

class TimeWindow(ContractModel):
    start_s: NonNegativeInt
    end_s: NonNegativeInt

    @model_validator(mode='after')
    def ordered(self):
        if self.end_s < self.start_s:
            raise ValueError('end_s must be >= start_s')
        return self

class Source(ContractModel):
    source_kind: Literal['user', 'database', 'public', 'simulation', 'default']
    source_ref: StrictStr
    observed_at: AwareDatetime
    rule_version: StrictStr

class SolveBudget(ContractModel):
    remaining_ms: PositiveInt
    max_workers: PositiveInt = 1
    random_seed: NonNegativeInt = 17

class SolveMetadata(ContractModel):
    status: SolveStatus
    raw_status: StrictStr
    engine: StrictStr
    engine_version: StrictStr
    has_solution: bool
    proof_scope: StrictStr
    solve_ms: NonNegativeInt

    @model_validator(mode='after')
    def coherent(self):
        if self.has_solution != (self.status in ('optimal', 'feasible')):
            raise ValueError('has_solution must agree with solve status')
        return self

class RuleEvidence(ContractModel):
    """Structured R05 evidence attached to a violation.

    ``interval_*`` is the half-open window the rule examined; ``observed_value``
    and ``limit_value`` are in ``capacity_unit`` when the rule is a capacity
    rule.  Evidence never replaces the message: both are mandatory context for
    reproducing a failed cold-chain check.
    """

    rule_version: StrictStr
    capacity_unit: StrictStr | None = None
    observed_value: NonNegativeInt | None = None
    limit_value: NonNegativeInt | None = None
    interval_start_s: NonNegativeInt | None = None
    interval_end_s: NonNegativeInt | None = None
    detail: StrictStr | None = None

    @model_validator(mode='after')
    def coherent(self):
        if (self.interval_start_s is None) != (self.interval_end_s is None):
            raise ValueError('evidence interval needs both start and end')
        if self.interval_start_s is not None and self.interval_end_s < self.interval_start_s:
            raise ValueError('evidence interval end precedes start')
        if (self.observed_value is None) != (self.limit_value is None):
            raise ValueError('capacity evidence needs observed and limit together')
        if self.observed_value is not None and self.capacity_unit is None:
            raise ValueError('capacity evidence needs a capacity unit')
        return self

class Violation(ContractModel):
    rule_id: StrictStr
    object_ids: tuple[Id, ...]
    message: StrictStr
    source_refs: tuple[StrictStr, ...] = ()
    evidence: RuleEvidence | None = None

class ValidationReport(ContractModel):
    status: Literal['passed', 'failed', 'not_checked']
    validator_version: StrictStr
    checked_rule_ids: tuple[StrictStr, ...]
    violations: tuple[Violation, ...]
    not_checked_rule_ids: tuple[StrictStr, ...] = ()

    @model_validator(mode='after')
    def not_false_success(self):
        if self.status == 'passed' and (self.violations or not self.checked_rule_ids):
            raise ValueError('passed requires checked rules and zero violations')
        if self.status == 'passed' and self.not_checked_rule_ids:
            raise ValueError('passed cannot carry unchecked rules; missing data is not a pass')
        if self.status == 'failed' and not self.violations:
            raise ValueError('failed requires at least one violation')
        return self

class FieldError(ContractModel):
    field: StrictStr
    message: StrictStr

class ErrorResponse(ContractModel):
    code: StrictStr
    message: StrictStr
    field_errors: tuple[FieldError, ...] = ()
    trace_id: StrictStr
    retryable: bool = False
