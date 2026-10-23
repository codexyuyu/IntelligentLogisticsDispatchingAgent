"""Minimal coordinator-facing chat service (P19/P23 subset)."""

from __future__ import annotations

from logistics_agents.llm import ChatMessage, LLMProvider, LLMReply

SYSTEM_PROMPT = (
    "You are the logistics dispatching assistant. You may explain and summarize data, but "
    "you must never invent a schedule, delivery result or inventory fact. If a requested "
    "capability is not enabled, say so explicitly and ask the operator to run the "
    "deterministic solver/validator first."
)


class AgentChatService:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    @property
    def configured(self) -> bool:
        return self.provider.configured

    def reply(self, message: str) -> LLMReply:
        return self.provider.complete((
            ChatMessage("system", SYSTEM_PROMPT),
            ChatMessage("user", message),
        ))
