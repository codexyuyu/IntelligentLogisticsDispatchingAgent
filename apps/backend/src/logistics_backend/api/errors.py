from uuid import uuid4
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError
from logistics_contracts.common import ErrorEnvelope, FieldError, UnsupportedDetail
from logistics_domain.errors import DomainError
from logistics_domain.states import ErrorCode, HTTP_STATUS_BY_ERROR_CODE


def response(request, code, message, status=None, details=()):
    trace = getattr(request.state, "trace_id", uuid4())
    body = ErrorEnvelope(code=code, message=message, trace_id=trace,
        retryable=code in (ErrorCode.DEPENDENCY_UNAVAILABLE, ErrorCode.PROVIDER_UNAVAILABLE), details=details)
    return JSONResponse(body.model_dump(mode="json"), status_code=status or HTTP_STATUS_BY_ERROR_CODE[code],
        headers={"X-Request-ID": str(trace)})


def install_handlers(app):
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        status = getattr(exc, "status", None)
        details = (UnsupportedDetail(capability="requested capability"),) if status == 501 else ()
        return response(request, exc.code, exc.message, status, details)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        details = tuple(FieldError(field_path=".".join(map(str, e["loc"])), rule=e["type"],
            expected="contract value", actual="redacted") for e in exc.errors())
        return response(request, ErrorCode.INVALID_INPUT, "request does not match schema", details=details)

    @app.exception_handler(IntegrityError)
    async def conflict(request: Request, exc: IntegrityError):
        return response(request, ErrorCode.RESOURCE_CONFLICT, "database relationship or uniqueness conflict")

    @app.exception_handler(OperationalError)
    async def unavailable(request: Request, exc: OperationalError):
        return response(request, ErrorCode.DEPENDENCY_UNAVAILABLE, "database unavailable")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        return response(request, ErrorCode.INTERNAL_ERROR, "internal operation failed")
