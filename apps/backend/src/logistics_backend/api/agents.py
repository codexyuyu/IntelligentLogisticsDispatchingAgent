"""Agent chat and run-history API (P23 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.agent import AgentRunService
from logistics_contracts.agents import (
    AgentChatRequest,
    AgentChatResponse,
    AgentRunPage,
    AgentToolCallRequest,
    AgentToolPage,
    AgentToolResultView,
    AgentToolSpecView,
)
from logistics_domain.runtime import ActorContext
from logistics_backend.application.tools import ToolService

router = APIRouter(tags=["agents"])


def agent_service(request: Request) -> AgentRunService:
    return request.app.state.agents


def tool_service(request: Request) -> ToolService:
    return request.app.state.tools


@router.post("/agents/chat", response_model=AgentChatResponse, operation_id="agent_chat")
def agent_chat(request: Request, command: AgentChatRequest,
               current: ActorContext = Depends(operator),
               service: AgentRunService = Depends(agent_service)):
    return service.chat_once(command, current, request.state.trace_id)


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


@router.post("/agents/tools/{name}", response_model=AgentToolResultView,
             operation_id="invoke_agent_tool")
def invoke_agent_tool(name: str, command: AgentToolCallRequest,
                      current: ActorContext = Depends(operator),
                      service: ToolService = Depends(tool_service)):
    result = service.invoke(name, current, command.arguments)
    return AgentToolResultView(name=result.name, ok=result.ok, content=result.content,
        error_code=result.error_code)
