"""Unified demo API. B-01/B-02 planning path is wired; remaining business routes stay explicit 501."""
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse
from app.common.errors import FeatureNotImplemented
from app.contracts.common import CONTRACT_VERSION, ErrorResponse, FieldError
from app.contracts.http import HealthResponse
from app.api.routes import scenarios, requests, planning, jobs, plans, events, simulations, evidence, postgres_demo, agent_demo

app = FastAPI(title='Logistics Demo', version=CONTRACT_VERSION,
              description='Unified logistics demo; B-01 warehouse scheduling and B-02 routing are wired into planning-jobs.',
              responses={501: {'model': ErrorResponse}, 422: {'model': ErrorResponse, 'description': 'Unprocessable Content'},
                         409: {'model': ErrorResponse}, 500: {'model': ErrorResponse}})

@app.middleware('http')
async def trace_request(request: Request, call_next):
    request.state.trace_id = uuid4().hex
    response = await call_next(request)
    response.headers['X-Trace-Id'] = request.state.trace_id
    return response

def error_response(request: Request, status: int, code: str, message: str, fields=()):
    body = ErrorResponse(code=code, message=message, field_errors=fields,
                         trace_id=getattr(request.state, 'trace_id', uuid4().hex))
    return JSONResponse(status_code=status, content=body.model_dump(mode='json'))

@app.exception_handler(FeatureNotImplemented)
async def not_implemented(request: Request, exc: FeatureNotImplemented):
    return error_response(request, 501, 'not_implemented', str(exc))

@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    fields = tuple(FieldError(field='.'.join(map(str, e['loc'])), message=e['msg']) for e in exc.errors())
    return error_response(request, 422, 'invalid_input', 'Request validation failed', fields)

@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return error_response(request, exc.status_code, 'http_error', str(exc.detail))

@app.exception_handler(ValueError)
async def value_error(request: Request, exc: ValueError):
    return error_response(request, 400, 'invalid_business_input', str(exc))

@app.exception_handler(KeyError)
async def key_error(request: Request, exc: KeyError):
    return error_response(request, 404, 'not_found', str(exc).strip("'"))

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    return error_response(request, 500, 'internal_error', 'Unexpected server error')

@app.get('/api/v1/health', response_model=HealthResponse, operation_id='get_health')
def health() -> HealthResponse:
    return HealthResponse()

for module in (scenarios, requests, planning, jobs, plans, events, simulations, evidence):
    app.include_router(module.router, prefix='/api/v1')

# Isolated local sub-application: existing shared /api/v1 OpenAPI and generated frontend stay unchanged.
# Only for developer use; PG_DEMO_ENABLED + localhost checks are enforced by its handlers.
pg_local_app = FastAPI(title='PostgreSQL → R20 Routing (local simulation preview + optional archive)',
                       description='Local simulation. Optional archival saves ONLY to separate demo table; NOT an executable dispatch.')
pg_local_app.include_router(postgres_demo.router)
pg_local_app.include_router(agent_demo.router)
app.mount('/local-pg', pg_local_app)
