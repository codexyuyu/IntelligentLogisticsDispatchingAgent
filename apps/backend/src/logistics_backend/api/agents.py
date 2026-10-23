"""Agent chat API (P23 subset); provider errors map to typed 503 responses."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from logistics_backend.api.dependencies import operator
from logistics_agents.service import AgentChatService
from logistics_contracts.agents import AgentChatRequest, AgentChatResponse
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["agents"])


def agent_service(request: Request) -> AgentChatService:
    return request.app.state.agents


@router.post("/agents/chat", response_model=AgentChatResponse, operation_id="agent_chat")
def agent_chat(request: Request, command: AgentChatRequest,
               current: ActorContext = Depends(operator),
               service: AgentChatService = Depends(agent_service)):
    reply = service.reply(command.message)
    return AgentChatResponse(reply=reply.content, model=reply.model,
        provider_configured=service.configured, trace_id=request.state.trace_id)
