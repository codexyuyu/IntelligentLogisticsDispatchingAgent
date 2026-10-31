"""Single entry point for the OR-Tools routing bindings used by the showcase.

The backend application layer must not import ``ortools`` directly: the backend
distribution does not declare it, and the architecture check rejects undeclared
imports. Keeping the binding behind this module keeps the dependency inside the
optimization package, which does declare OR-Tools.
"""
from __future__ import annotations


def routing_bindings():
    """Return (pywrapcp, routing_enums_pb2) from the pinned OR-Tools build."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    return pywrapcp, routing_enums_pb2


__all__ = ["routing_bindings"]