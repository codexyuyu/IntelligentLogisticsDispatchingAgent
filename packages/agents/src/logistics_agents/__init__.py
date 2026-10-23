"""Agent layer: four bounded roles, the whitelisted tool protocol and LLM providers.

Layer rules: an LLM only extracts intent, decomposes work, calls tools and explains
results. It never freely generates the final schedule, never writes the database and
never bypasses a service. Agents reach business capability exclusively through
``ToolContext``-scoped tools; SQL and storage handles are forbidden in this layer.

Nothing is implemented yet: P17-01 onwards delivers the tool protocol, P18 the model
provider abstraction and P19-P23 the four roles, orchestration and session API.
"""

from __future__ import annotations

from . import llm, service

SCHEMA_VERSION = "1.0.0"
PACKAGE_NAME = "logistics-agents"
LAYER = "agents"

AGENT_ROLES = ("coordinator", "transport", "warehouse", "exception")
LLM_DECISION_SCOPE = "extract|decompose|call_tools|explain"

__all__ = ["SCHEMA_VERSION", "PACKAGE_NAME", "LAYER", "AGENT_ROLES", "LLM_DECISION_SCOPE",
           "llm", "service"]

_PENDING_APIS: dict[str, str] = {
    "tools": "P17-01/P17-02: whitelisted typed tools bound to application services",
    "provider": "P18-01/P18-02: provider abstraction, budget, retry, redaction, degradation",
    "coordinator": "P19-01/P19-02: intent extraction and bounded decomposition state machine",
    "transport_agent": "P20-01/P20-02: solve via tools only, evidence-backed explanation",
    "warehouse_agent": "P21-01/P21-02: scheduling and non-reserving window quotes",
    "exception_agent": "P22-01/P22-02: nine-step exception handling with manual_required",
    "orchestration": "P23-01/P23-02: routing, cancellation propagation and session API",
}


def __getattr__(name: str):
    if name in _PENDING_APIS:
        raise NotImplementedError(
            f"logistics_agents.{name} is not implemented yet ({_PENDING_APIS[name]}); "
            "see docs/implementation/P01-01.md for the delivered scope of the workspace bootstrap"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
