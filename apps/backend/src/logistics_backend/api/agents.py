"""Agent chat and run-history API (P23 subset)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.agent import AgentRunService
from logistics_contracts.agents import (
    AgentChatRequest,
    DispatchRequest,
    DispatchResponse,
    AgentChatResponse,
    AgentRunPage,
    AgentToolCallPage,
    AgentToolCallRequest,
    AgentToolPage,
    AgentToolResultView,
    AgentToolSpecView,
)
from logistics_contracts.decision import DecisionCreate, DecisionPage, DecisionView
from logistics_domain.runtime import ActorContext
from logistics_backend.application.decision import DecisionService
from logistics_backend.application.tools import ToolService
from logistics_contracts.dispatch_tasks import DispatchTaskCreate, DispatchTaskRevision, DispatchTaskView

router = APIRouter(tags=["agents"])


def agent_service(request: Request) -> AgentRunService:
    return request.app.state.agents


def tool_service(request: Request) -> ToolService:
    return request.app.state.tools


def decision_service(request: Request) -> DecisionService:
    return request.app.state.decisions


@router.post("/agents/chat", response_model=AgentChatResponse, operation_id="agent_chat")
def agent_chat(request: Request, command: AgentChatRequest,
               current: ActorContext = Depends(operator),
               service: AgentRunService = Depends(agent_service)):
    return service.chat_once(command, current, request.state.trace_id)


def dispatch_service(request: Request):
    return request.app.state.dispatch_agent


@router.post("/agents/dispatch", response_model=DispatchResponse,
             operation_id="agent_dispatch_analysis")
def dispatch(command: DispatchRequest, request: Request,
             current: ActorContext = Depends(operator),
             service=Depends(dispatch_service)):
    return service.execute(command, current, request.state.trace_id)


@router.get("/agents/dispatch/{agent_run_id}", response_model=DispatchResponse,
            operation_id="get_agent_dispatch_analysis")
def get_dispatch(agent_run_id: UUID, current: ActorContext = Depends(actor),
                 service: AgentRunService = Depends(agent_service)):
    return service.get_dispatch(agent_run_id, current)


@router.get("/agents/runs", response_model=AgentRunPage, operation_id="list_agent_runs")
def list_agent_runs(current: ActorContext = Depends(actor),
                    service: AgentRunService = Depends(agent_service),
                    limit: int = Query(default=50, ge=1, le=200)):
    return service.list(current, limit)


@router.get("/agents/tools", response_model=AgentToolPage, operation_id="list_agent_tools")
def list_agent_tools(service: ToolService = Depends(tool_service)):
    return AgentToolPage(items=tuple(AgentToolSpecView(name=spec.name,
        description=spec.description, allowed_roles=spec.allowed_roles)
        for spec in service.specs()))


@router.get("/agents/tools/calls", response_model=AgentToolCallPage,
            operation_id="list_agent_tool_calls")
def list_agent_tool_calls(current: ActorContext = Depends(actor),
                          service: ToolService = Depends(tool_service),
                          limit: int = Query(default=50, ge=1, le=200)):
    return service.calls(current, limit)


@router.post("/agents/tools/{name}", response_model=AgentToolResultView,
             operation_id="invoke_agent_tool")
def invoke_agent_tool(name: str, command: AgentToolCallRequest, request: Request,
                      current: ActorContext = Depends(operator),
                      service: ToolService = Depends(tool_service)):
    result = service.invoke(name, current, command.arguments, request.state.trace_id)
    return AgentToolResultView(name=result.name, ok=result.ok, content=result.content,
        error_code=result.error_code)


@router.post("/agents/decisions", response_model=DecisionView, status_code=201,
             operation_id="record_agent_decision")
def record_agent_decision(command: DecisionCreate, current: ActorContext = Depends(operator),
                          service: DecisionService = Depends(decision_service)):
    return service.record(command, current)


@router.get("/agents/decisions", response_model=DecisionPage,
            operation_id="list_agent_decisions")
def list_agent_decisions(current: ActorContext = Depends(actor),
                         service: DecisionService = Depends(decision_service),
                         limit: int = Query(default=50, ge=1, le=200)):
    return service.list(current, limit)


@router.post("/agents/decisions/{decision_id}/accept", response_model=DecisionView,
             operation_id="accept_agent_decision")
def accept_agent_decision(decision_id: UUID, current: ActorContext = Depends(operator),
                          service: DecisionService = Depends(decision_service)):
    from logistics_domain.states import EntityState

    return service.transition(decision_id, EntityState.ACCEPTED, current)


@router.post("/agents/decisions/{decision_id}/reject", response_model=DecisionView,
             operation_id="reject_agent_decision")
def reject_agent_decision(decision_id: UUID, current: ActorContext = Depends(operator),
                          service: DecisionService = Depends(decision_service)):
    from logistics_domain.states import EntityState

    return service.transition(decision_id, EntityState.REJECTED, current)


# Controlled natural-language scheduling, separate from the read-only analysis API.
def natural_dispatch_service(request: Request):
    return request.app.state.natural_dispatch


@router.post("/agents/dispatch-tasks", response_model=DispatchTaskView,
             operation_id="create_natural_dispatch_task")
def create_dispatch_task(command: DispatchTaskCreate,
                         current: ActorContext = Depends(operator),
                         service=Depends(natural_dispatch_service)):
    return service.create(command, current)


@router.get("/agents/dispatch-tasks", operation_id="list_natural_dispatch_tasks")
def list_dispatch_tasks(current: ActorContext = Depends(actor),
                        service=Depends(natural_dispatch_service)):
    return service.list(current)


@router.get("/agents/dispatch-tasks/{task_id}", response_model=DispatchTaskView,
            operation_id="get_natural_dispatch_task")
def get_dispatch_task(task_id: UUID, current: ActorContext = Depends(actor),
                      service=Depends(natural_dispatch_service)):
    return service.get(task_id, current)


@router.post("/agents/dispatch-tasks/{task_id}/preview", response_model=DispatchTaskView,
             operation_id="preview_natural_dispatch_task")
def preview_dispatch_task(task_id: UUID, command: DispatchTaskRevision,
                          current: ActorContext = Depends(operator),
                          service=Depends(natural_dispatch_service)):
    return service.preview(task_id, current, command.expected_row_version)


@router.post("/agents/dispatch-tasks/{task_id}/approve", response_model=DispatchTaskView,
             operation_id="approve_natural_dispatch_task")
def approve_dispatch_task(task_id: UUID, command: DispatchTaskRevision, request: Request,
                          current: ActorContext = Depends(operator),
                          service=Depends(natural_dispatch_service)):
    return service.decide(task_id, current, command.expected_row_version, True, request.state.trace_id)


@router.post("/agents/dispatch-tasks/{task_id}/reject", response_model=DispatchTaskView,
             operation_id="reject_natural_dispatch_task")
def reject_dispatch_task(task_id: UUID, command: DispatchTaskRevision, request: Request,
                         current: ActorContext = Depends(operator),
                         service=Depends(natural_dispatch_service)):
    return service.decide(task_id, current, command.expected_row_version, False, request.state.trace_id)


# A bounded, read-only evidence review. Does NOT invoke approve/reject/incident writes.
from logistics_contracts.decision_analysis import DecisionAnalysisRequest, DecisionAnalysisView


def decision_analysis_service(request: Request):
    return request.app.state.decision_analysis


@router.get('/agents/dispatch-tasks/{task_id}/ai-analysis',
            response_model=DecisionAnalysisView | None,
            operation_id='get_dispatch_task_ai_analysis')
def get_task_ai_analysis(task_id: UUID, current: ActorContext = Depends(actor),
                         service=Depends(decision_analysis_service)):
    return service.latest('dispatch_task', task_id, current)


@router.post('/agents/dispatch-tasks/{task_id}/ai-analysis',
             response_model=DecisionAnalysisView,
             operation_id='analyze_dispatch_task_candidate')
def analyze_task_candidate(task_id: UUID, command: DecisionAnalysisRequest,
                           current: ActorContext = Depends(operator),
                           service=Depends(decision_analysis_service)):
    return service.analyze('dispatch_task', task_id, current, command.question)


@router.get('/agents/runs/{run_id}/incidents/{incident_id}/ai-analysis',
            response_model=DecisionAnalysisView | None,
            operation_id='get_incident_ai_analysis')
def get_incident_ai_analysis(run_id: UUID, incident_id: UUID,
                             current: ActorContext = Depends(actor),
                             service=Depends(decision_analysis_service)):
    return service.latest_incident(run_id, incident_id, current)


@router.post('/agents/runs/{run_id}/incidents/{incident_id}/ai-analysis',
             response_model=DecisionAnalysisView,
             operation_id='analyze_incident_candidate')
def analyze_incident_candidate(run_id: UUID, incident_id: UUID,
                               command: DecisionAnalysisRequest,
                               current: ActorContext = Depends(operator),
                               service=Depends(decision_analysis_service)):
    return service.analyze('incident', incident_id, current, command.question, run_id=run_id)
