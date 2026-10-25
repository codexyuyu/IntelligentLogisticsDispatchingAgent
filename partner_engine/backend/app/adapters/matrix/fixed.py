"""Owner: B | Fixed snapshot-backed travel matrix provider.

The adapter is storage-agnostic. A higher layer loads an immutable TravelMatrix
from a snapshot store and injects it here. The adapter never turns unreachable
edges into zero-cost edges.
"""
from __future__ import annotations

from collections.abc import Mapping

from app.contracts.entities import PlanningSnapshot, TravelMatrix


class FixedTravelMatrixProvider:
    """Serve immutable, versioned matrices from an in-memory catalog."""

    def __init__(self, matrices: Mapping[str, TravelMatrix] | None = None) -> None:
        self._matrices = dict(matrices or {})

    @classmethod
    def from_snapshot(cls, snapshot: PlanningSnapshot) -> "FixedTravelMatrixProvider":
        return cls({snapshot.matrix.matrix_id: snapshot.matrix})

    def register(self, matrix: TravelMatrix) -> None:
        self._matrices[matrix.matrix_id] = matrix

    def get_matrix(self, matrix_id: str, expected_version: int) -> TravelMatrix:
        matrix = self._matrices.get(matrix_id)
        if matrix is None:
            raise ValueError(f"matrix_not_found:{matrix_id}")
        if matrix.version != expected_version:
            raise ValueError(
                f"matrix_version_conflict:{matrix_id}:expected={expected_version}:actual={matrix.version}"
            )
        self._validate(matrix)
        return matrix

    @staticmethod
    def _validate(matrix: TravelMatrix) -> None:
        node_ids = matrix.node_ids
        if not node_ids or len(node_ids) != len(set(node_ids)):
            raise ValueError("matrix_node_ids_invalid")
        n = len(node_ids)
        for name, values in (("duration_s", matrix.duration_s), ("distance_m", matrix.distance_m)):
            if len(values) != n or any(len(row) != n for row in values):
                raise ValueError(f"matrix_shape_invalid:{name}")
            for i in range(n):
                if values[i][i] != 0:
                    raise ValueError(f"matrix_diagonal_must_be_zero:{name}:{i}")

    @staticmethod
    def lookup(matrix: TravelMatrix, from_node_id: str, to_node_id: str) -> tuple[int, int]:
        try:
            a = matrix.node_ids.index(from_node_id)
            b = matrix.node_ids.index(to_node_id)
        except ValueError as exc:
            raise ValueError(f"matrix_unknown_node:{from_node_id}->{to_node_id}") from exc
        duration = matrix.duration_s[a][b]
        distance = matrix.distance_m[a][b]
        if duration is None or distance is None:
            raise ValueError(f"matrix_unreachable:{from_node_id}->{to_node_id}")
        return int(duration), int(distance)
