"""SHARED: authoritative status values; changing these changes the contract."""
from typing import Literal

JobStatus = Literal['queued', 'running', 'succeeded', 'failed', 'cancelled']
PlanStatus = Literal['draft', 'validated', 'confirmed', 'executing', 'completed', 'rejected', 'stale', 'superseded']
OperationStatus = Literal['pending', 'running', 'paused', 'interrupted', 'completed', 'cancelled']
SolveStatus = Literal['optimal', 'feasible', 'infeasible_proven', 'no_solution_within_budget', 'invalid_input', 'model_invalid', 'needs_clarification', 'unsupported', 'stale', 'conflict']
TemperatureZone = Literal['chilled', 'frozen']
EventType = Literal['departure_delayed', 'dock_unavailable', 'cargo_quarantined', 'weather_changed', 'demand_changed']
