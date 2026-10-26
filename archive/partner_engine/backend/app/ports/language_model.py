"""SHARED: AC owns provider adapter. Never grant direct SQL/shell/commit access."""
from typing import Protocol
from app.contracts.http import ParseRequest, ParseResponse, EvidenceResponse

class LanguageModelGateway(Protocol):
    def parse(self, request: ParseRequest) -> ParseResponse: ...
    def explain(self, evidence: EvidenceResponse) -> str: ...
