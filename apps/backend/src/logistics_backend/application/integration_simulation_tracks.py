"""Deterministic schematic route tracks for an independently checked joint run.

Tracks contain node identifiers and timed route legs, never GPS coordinates.  A
client may draw the nodes with its existing deterministic schematic layout.
The baseline is immutable; an incident produces a separate, auditable projection.
"""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid5

from logistics_backend.application.timeline import PRIORITY

TRACK_NAMESPACE = UUID("45b5ea25-8373-48c2-a7c2-50f87c91d13a")


class SimulationTrackError(ValueError):
    pass


def _segment(origin: str, destination: str, start: int, end: int,
             kind: str, start_fraction: float = 0.0, end_fraction: float = 1.0) -> dict:
    if start < 0 or end < start:
        raise SimulationTrackError("invalid route segment interval")
    return {
        "from_node_id": origin, "to_node_id": destination,
        "start_s": start, "end_s": end, "kind": kind,
        "start_fraction": start_fraction, "end_fraction": end_fraction,
    }


def build_tracks(result: dict, timeline: dict) -> list[dict]:
    """Derive route motion from persisted solver stop times and matrix travel times."""
    if result.get("status") != "checked" or timeline.get("reconciliation", {}).get("passed") is not True:
        raise SimulationTrackError("unchecked joint run cannot be simulated")
    transport = result["transport_solution"]
    problem = result["transport_problem"]
    nodes = {node["id"]: node for node in problem["nodes"]}
    matrix = problem["matrix"]
    indices = {node_id: index for index, node_id in enumerate(matrix["node_ids"])}
    by_route: dict[str, list[dict]] = {}
    for stop in transport["stops"]:
        by_route.setdefault(stop["route_id"], []).append(stop)
    return_at = {event["vehicle_id"]: event["time_s"] for event in timeline["events"]
                 if event["kind"] == "vehicle_return"}
    tracks = []
    for route in sorted(transport["candidate"]["routes"], key=lambda item: item["vehicle_id"]):
        stops = sorted(by_route.get(route["id"], []), key=lambda item: item["sequence"])
        if not stops or stops[0]["sequence"] != 0 or any(
            stop["sequence"] != index for index, stop in enumerate(stops)
        ):
            raise SimulationTrackError("route stops are missing or not contiguous")
        first_node = nodes[stops[0]["node_id"]]["location_id"]
        try:
            first_travel = matrix["travel_s"][indices[route["start_node_id"]]][indices[first_node]]
        except (KeyError, IndexError) as exc:
            raise SimulationTrackError("initial matrix arc is missing") from exc
        if first_travel is None:
            raise SimulationTrackError("initial matrix arc is blocked")
        if first_travel > stops[0]["arrival_s"]:
            raise SimulationTrackError("route would depart before simulation epoch")
        origin = route["start_node_id"]
        first_departure = max(0, stops[0]["arrival_s"] - first_travel)
        previous_departure = first_departure
        legs = []
        for stop in stops:
            if stop["arrival_s"] < previous_departure or stop["departure_s"] < stop["arrival_s"]:
                raise SimulationTrackError("route stop times violate monotonicity")
            legs.append(_segment(origin, stop["node_id"], previous_departure,
                                 stop["arrival_s"], "travel"))
            legs.append(_segment(stop["node_id"], stop["node_id"], stop["arrival_s"],
                                 stop["departure_s"], "service", 0.0, 0.0))
            origin = stop["node_id"]
            previous_departure = stop["departure_s"]
        end = return_at.get(route["vehicle_id"])
        if end is None or end < previous_departure:
            raise SimulationTrackError("checked timeline is missing vehicle return")
        legs.append(_segment(origin, route["end_node_id"], previous_departure, end, "return"))
        tracks.append({
            "vehicle_id": route["vehicle_id"], "route_id": route["id"],
            "distance_m": route["total_distance_m"], "start_node_id": route["start_node_id"],
            "end_node_id": route["end_node_id"], "segments": legs,
            "stops": [{"node_id": stop["node_id"], "sequence": stop["sequence"],
                       "arrival_s": stop["arrival_s"], "departure_s": stop["departure_s"],
                       "task_ids": stop["task_ids"],
                       "kind": nodes[stop["node_id"]]["kind"],
                       "order_id": nodes[stop["node_id"]]["order_id"]} for stop in stops],
        })
    if len({track["vehicle_id"] for track in tracks}) != len(tracks):
        raise SimulationTrackError("duplicate vehicle route")
    return tracks


def sample_track(track: dict, at_s: int) -> dict:
    """A reversible (from_node, to_node, progress) schematic location."""
    segments = track["segments"]
    if not segments:
        raise SimulationTrackError("track has no segments")
    active = next((segment for segment in segments if segment["start_s"] <= at_s < segment["end_s"]), None)
    if active is None:
        active = segments[0] if at_s < segments[0]["start_s"] else segments[-1]
    start, end = active["start_s"], active["end_s"]
    fraction = 1.0 if at_s >= end else (0.0 if at_s <= start or end == start
                                       else (at_s - start) / (end - start))
    progress = active["start_fraction"] + fraction * (active["end_fraction"] - active["start_fraction"])
    return {"vehicle_id": track["vehicle_id"], "from_node_id": active["from_node_id"],
            "to_node_id": active["to_node_id"], "progress": round(progress, 9),
            "kind": active["kind"], "time_s": at_s}


def hold_and_shift(tracks: list[dict], vehicle_id: str, at_s: int, delay_s: int) -> list[dict]:
    """Freeze vehicle at its current point, then shift only its future route.

    This safe simulation policy does not claim that OR-Tools found a new path.
    """
    if delay_s <= 0 or at_s < 0:
        raise SimulationTrackError("delay must be positive and time nonnegative")
    output = deepcopy(tracks)
    affected = next((track for track in output if track["vehicle_id"] == vehicle_id), None)
    if affected is None:
        raise SimulationTrackError("vehicle is not part of the checked run")
    if not affected["segments"] or at_s < affected["segments"][0]["start_s"] or at_s >= affected["segments"][-1]["end_s"]:
        raise SimulationTrackError("incident must occur during vehicle route")
    current = sample_track(affected, at_s)
    prefix, suffix = [], []
    for leg in affected["segments"]:
        if leg["end_s"] <= at_s:
            prefix.append(leg)
        elif leg["start_s"] >= at_s:
            suffix.append({**leg, "start_s": leg["start_s"] + delay_s,
                           "end_s": leg["end_s"] + delay_s})
        else:
            progress = current["progress"]
            prefix.append({**leg, "end_s": at_s, "end_fraction": progress})
            suffix.append({**leg, "start_s": at_s + delay_s,
                           "end_s": leg["end_s"] + delay_s, "start_fraction": progress})
    hold = _segment(current["from_node_id"], current["to_node_id"], at_s,
                    at_s + delay_s, "hold", current["progress"], current["progress"])
    affected["segments"] = [*prefix, hold, *suffix]
    return output


def retime_events(events: list[dict], vehicle_id: str, at_s: int, delay_s: int,
                  incident_id: str) -> list[dict]:
    """Keep history fixed and add a simulated incident to the future projection."""
    values = deepcopy(events)
    for event in values:
        if event.get("vehicle_id") == vehicle_id and event["time_s"] > at_s:
            event["time_s"] += delay_s
            event["id"] = str(uuid5(TRACK_NAMESPACE, f"{incident_id}:{event['id']}"))
    values.append({"id": str(uuid5(TRACK_NAMESPACE, f"{incident_id}:occurred")),
                   "kind": "transport_delay", "time_s": at_s,
                   "object_id": vehicle_id, "vehicle_id": vehicle_id,
                   "order_id": None, "route_id": None, "node_id": None})
    values.sort(key=lambda item: (item["time_s"], PRIORITY.get(item["kind"], -1),
                                   item["object_id"], item["id"]))
    for index, event in enumerate(values):
        event["sequence"] = index
    return values


def delay_impact(result: dict, events: list[dict], vehicle_id: str, at_s: int,
                 delay_s: int) -> dict:
    """Only accept a hold projection that still respects hard delivery/vehicle bounds."""
    future = [event for event in events if event["kind"] == "order_delivered"
              and event["vehicle_id"] == vehicle_id and event["time_s"] > at_s]
    if not future:
        raise SimulationTrackError("vehicle has no remaining deliveries")
    problem = result["transport_problem"]
    nodes = {node["id"]: node for node in problem["nodes"]}
    route_ids = {route["id"] for route in result["transport_solution"]["candidate"]["routes"]
                 if route["vehicle_id"] == vehicle_id}
    violations = []
    for stop in result["transport_solution"]["stops"]:
        if stop["route_id"] not in route_ids or stop["service_start_s"] <= at_s:
            continue
        node = nodes[stop["node_id"]]
        if stop["service_start_s"] + delay_s > node["hard_window"]["latest_s"]:
            violations.append({"node_id": stop["node_id"], "reason": "hard_window_exceeded"})
    scope_horizon = result["warehouse_problem"]["snapshot"]["scope"]["horizon_s"]
    return_at = next((e["time_s"] for e in events if e["kind"] == "vehicle_return"
                      and e["vehicle_id"] == vehicle_id), None)
    if return_at is None or return_at + delay_s > scope_horizon:
        violations.append({"vehicle_id": vehicle_id, "reason": "simulation_horizon_exceeded"})
    state = next((item for item in problem["vehicles"] if item["vehicle_id"] == vehicle_id), None)
    if state is None or return_at is None or return_at + delay_s > state["available_window"]["latest_s"]:
        violations.append({"vehicle_id": vehicle_id, "reason": "vehicle_available_window_exceeded"})
    return {"affected_order_ids": [e["order_id"] for e in future],
            "before_eta_s": {e["order_id"]: e["time_s"] for e in future},
            "after_eta_s": {e["order_id"]: e["time_s"] + delay_s for e in future},
            "violations": violations, "valid": not violations}
