from typing import Annotated, Literal, TypeAlias
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from logistics_domain.primitives import EntityRef
from logistics_domain.states import EntityKind, ErrorCode

class Detail(BaseModel):
    model_config = ConfigDict(extra="forbid")

class EntityRefDTO(Detail):
    kind: EntityKind
    id: UUID
    revision: int | None

    def to_domain(self) -> EntityRef:
        return EntityRef(kind=self.kind, id=self.id, revision=self.revision)

    @classmethod
    def from_domain(cls, value: EntityRef) -> "EntityRefDTO":
        return cls(kind=value.kind, id=value.id, revision=value.revision)

class FieldError(Detail):
    kind: Literal["field"] = "field"
    field_path: str
    rule: str
    expected: str
    actual: str

class ConflictDetail(Detail):
    kind: Literal["conflict"] = "conflict"
    entity_ref: EntityRefDTO
    expected_revision: int
    actual_revision: int

class UnsupportedDetail(Detail):
    kind: Literal["unsupported"] = "unsupported"
    capability: str

ErrorDetail: TypeAlias = Annotated[FieldError | ConflictDetail | UnsupportedDetail, Field(discriminator="kind")]

class ErrorEnvelope(Detail):
    schema_version: Literal["2.0.0"] = "2.0.0"
    code: ErrorCode
    message: str
    trace_id: UUID
    retryable: bool
    details: tuple[ErrorDetail, ...] = ()
