"""Agent chat and run-history API (P23 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.agent import AgentRunService
from logistics_contracts.agents import AgentChatRequest, AgentChatResponse, AgentRunPage
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["agents"])


def agent_service(request: Request) -> AgentRunService:
    return request.app.state.agents


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
