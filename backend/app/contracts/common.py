"""SHARED: sole source of exchange types. No ORM, solver or model SDK objects."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, AwareDatetime, model_validator
from app.domain.states import SolveStatus

CONTRACT_VERSION = '0.1.0'
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

class Violation(ContractModel):
    rule_id: StrictStr
    object_ids: tuple[Id, ...]
    message: StrictStr
    source_refs: tuple[StrictStr, ...] = ()

class ValidationReport(ContractModel):
    status: Literal['passed', 'failed', 'not_checked']
    validator_version: StrictStr
    checked_rule_ids: tuple[StrictStr, ...]
    violations: tuple[Violation, ...]

    @model_validator(mode='after')
    def not_false_success(self):
        if self.status == 'passed' and (self.violations or not self.checked_rule_ids):
            raise ValueError('passed requires checked rules and zero violations')
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
