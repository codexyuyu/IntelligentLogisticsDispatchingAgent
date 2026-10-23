import hashlib
import hmac
from uuid import UUID
from fastapi import Depends, Header, Request
from logistics_backend.application.master_data import ServiceError
from logistics_domain.runtime import ActorContext
from logistics_domain.states import ActorRole, ErrorCode


def actor(request: Request, authorization: str | None = Header(default=None)) -> ActorContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise ServiceError(ErrorCode.UNAUTHENTICATED, "bearer credential required")
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    settings = request.app.state.settings
    for grant in settings.credentials:
        if hmac.compare_digest(digest, grant.token_sha256):
            return ActorContext(actor_id=grant.actor_id, role=grant.role, scope_id=settings.scope_id)
    raise ServiceError(ErrorCode.UNAUTHENTICATED, "invalid credential")


def operator(current: ActorContext = Depends(actor)) -> ActorContext:
    if current.role != ActorRole.OPERATOR:
        raise ServiceError(ErrorCode.FORBIDDEN, "operator role required")
    return current


def revision(if_match: str = Header(alias="If-Match")) -> int:
    value = if_match.strip('"')
    if not value.isdecimal():
        raise ServiceError(ErrorCode.INVALID_INPUT, "If-Match must be a nonnegative revision")
    return int(value)


def master_service(request: Request):
    return request.app.state.master_data


def job_service(request: Request):
    return request.app.state.jobs
