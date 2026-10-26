"""SimPy-backed discrete-event simulator for B-05."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import simpy

from app.adapters.simulation.event_sources import build_events
from app.application.coordinator import coordinate
from app.application.handle_event import handle_event
from app.application.impact_analysis import SUPPORTED_EVENTS
from app.application.runtime import runtime
from app.contracts.common import Id
from app.contracts.entities import PlanningSnapshot
from app.contracts.events import DispatchEvent, SimulationRequest, SimulationResult


def baseline_order_ids(snapshot: PlanningSnapshot,
                       events: tuple[DispatchEvent, ...]) -> tuple[str, ...]:
    """Baseline planning scope for a simulation run.

    Only a departure delay names orders that all sit on one vehicle's route, so that is the
    single event type whose ``affected_order_ids`` is a genuine scope hint. A dock outage
    names a warehouse and a quarantine names blocked orders -- narrowing the baseline to
    those would simulate a plan that never contained the orders the event is about.
    """
    required = {order.order_id for order in snapshot.orders if order.required}
    hinted = {order_id for event in events if event.event_type == "departure_delayed"
              for order_id in event.payload.affected_order_ids if order_id in required}
    return tuple(sorted(hinted or required))


class SimPySimulator:
    """Run a deterministic event stream and bridge events into B-04.

    Simulation runs get a larger planning budget than the interactive planning
    API.  The simulation must first build a complete baseline plan and then
    replan on injected events; the previous 10-second cap could be consumed by
    the warehouse stage alone on multi-order scenarios.

    Every event type B-04 supports is replayed here: departure_delayed,
    dock_unavailable and cargo_quarantined. An unsupported or undeliverable event aborts
    the run rather than being skipped, so a failed replay is never silently omitted from
    ``emitted_events`` (the HTTP layer records the failure as a failed job).
    """

    BASELINE_BUDGET_MS = 20_000
    REPLAN_BUDGET_MS = 20_000

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        unsupported = sorted({event.event_type for event in request.events}
                             - set(SUPPORTED_EVENTS))
        if unsupported:
            # Fail before spending the baseline budget on a stream B-04 cannot handle.
            raise ValueError("simulation_unsupported_event_types:" + ",".join(unsupported))

        simulation_id: Id = f"sim_{uuid4().hex[:20]}"
        sim_snapshot_id = f"sim_{simulation_id}_{request.snapshot.snapshot_id}"
        base_snapshot = request.snapshot.model_copy(
            update={"snapshot_id": sim_snapshot_id, "version": 1, "simulation_time_s": 0}
        )

        # Keep simulation state isolated from the live planning snapshot.
        runtime.put_snapshot(base_snapshot)
        order_ids = baseline_order_ids(base_snapshot, request.events)
        if not order_ids:
            raise ValueError("simulation_requires_at_least_one_required_order")

        # Generate the baseline plan that the simulation will perturb.
        baseline = coordinate(
            snapshot=base_snapshot,
            order_ids=order_ids,
            budget_ms=self.BASELINE_BUDGET_MS,
            max_coordination_rounds=3,
        )
        runtime.put_plan(baseline)

        env = simpy.Environment(initial_time=0)
        events = build_events(request)
        emitted: list[DispatchEvent] = []
        state = {"snapshot": base_snapshot, "plan": baseline}

        def process_events():
            for event in events:
                delay = max(0, event.occurred_at_s - int(env.now))
                if delay:
                    yield env.timeout(delay)
                current = state["snapshot"]
                projected = current.model_copy(update={"simulation_time_s": int(env.now)})
                runtime.put_snapshot(projected)
                sim_event = event.model_copy(
                    update={
                        "snapshot_id": current.snapshot_id,
                        "expected_snapshot_version": state["plan"].snapshot_version,
                        "received_at": datetime.now(timezone.utc),
                    }
                )
                result = handle_event(
                    event=sim_event,
                    previous_plan=state["plan"],
                    budget_ms=self.REPLAN_BUDGET_MS,
                )
                # B-04 already advances the snapshot version and stores the derived snapshot.
                new_snapshot = runtime.get_snapshot(result.replanned_plan.snapshot_id, result.replanned_plan.snapshot_version)
                new_snapshot = new_snapshot.model_copy(update={"simulation_time_s": int(env.now)})
                runtime.put_snapshot(new_snapshot)
                runtime.put_plan(result.replanned_plan)
                state["snapshot"] = new_snapshot
                state["plan"] = result.replanned_plan
                emitted.append(sim_event)

        env.process(process_events())
        env.run(until=request.horizon_s)
        if len(emitted) != len(events):
            # A horizon shorter than the last event used to drop the tail of the stream
            # silently, leaving a plausible-looking result that never replayed them.
            pending = ",".join(event.event_id for event in events[len(emitted):])
            raise ValueError(f"simulation_horizon_cut_event_stream:{pending}")
        final_snapshot = state["snapshot"].model_copy(update={"simulation_time_s": int(env.now)})
        return SimulationResult(
            simulation_id=simulation_id,
            base_snapshot_id=request.snapshot.snapshot_id,
            final_snapshot=final_snapshot,
            emitted_events=tuple(emitted),
        )
