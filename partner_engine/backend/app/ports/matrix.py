"""SHARED: B owns implementations; matrix access stays out of solver callbacks."""
from typing import Protocol
from app.contracts.entities import TravelMatrix

class TravelMatrixProvider(Protocol):
    def get_matrix(self, matrix_id: str, expected_version: int) -> TravelMatrix: ...
