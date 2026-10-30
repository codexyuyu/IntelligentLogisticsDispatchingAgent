"""Durable, simulation-only warehouse/vehicle/exception approval workflow.

The checked integration run and its S4 timeline remain immutable.  Even an
approved simulation projection does NOT commit an operational schedule, alter
S3 inventory, or claim to be observed GPS/vehicle telemetry.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid5

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert

from logistics_backend.application.integration_simulation_tracks import (
    SimulationTrackError,
    build_tracks,
    delay_impact,
    hold_and_shift,
    retime_events,
    sample_track,
)
from logistics_backend.application.timeline import state_at_time
from logistics_backend.errors import ServiceError
from logistics_backend.persistence.integration_models import (
    integration_simulation_incidents,
    integration_simulations,
)
from logistics_contracts.events import EventEnvelopeDTO
from logistics_domain.states import ErrorCode

NAMESPACE = UUID('c2384e28-1342-4be2-bad8-c091beff40d1')


class IntegrationSimulationService:
    def __init__(self, *, uow_factory, scope_id: UUID, integration, events):
        self.uow_factory = uow_factory
        self.scope_id = scope_id
        self.integration = integration
        self.events = events

    def _scope(self, actor):
        if actor.scope_id != self.scope_id:
            raise ServiceError(ErrorCode.FORBIDDEN, 'scope mismatch')

    def _run(self, run_id, actor):
        self._scope(actor)
        return self.integration.get(run_id, actor)

    def _simulation(self, run_id, actor):
        self._scope(actor)
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(integration_simulations).where(
                integration_simulations.c.run_id == run_id,
                integration_simulations.c.scope_id == actor.scope_id)).mappings().first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, 'simulation for run not found')
        return row

    def _incident(self, simulation_id, actor):
        with self.uow_factory() as uow:
            return uow.connection.execute(select(integration_simulation_incidents).where(
                integration_simulation_incidents.c.simulation_id == simulation_id,
                integration_simulation_incidents.c.scope_id == actor.scope_id)).mappings().first()

    def start(self, run_id: UUID, actor) -> dict:
        """Idempotently materialize the checked-run routes in PostgreSQL."""
        result = self._run(run_id, actor)
        timeline = self.integration.timeline(run_id, actor)  # seven S4 gates
        try:
            tracks = build_tracks(result, timeline)
        except (KeyError, ValueError, TypeError) as exc:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, str(exc)) from exc
        identity = uuid5(NAMESPACE, f'{actor.scope_id}:{run_id}')
        events = timeline['events']
        payload = {
            'id': str(identity), 'run_id': str(run_id),
            'schema_version': '2.0.0', 'source_kind': 'simulated_from_planned',
            'baseline_version': 0,
            'input_source_kind': result.get('source_kind'),
            'scenario_id': result.get('request', {}).get('scenario_id'),
            'tracks': tracks, 'events': events,
            'reconciliation': timeline['reconciliation'],
            'horizon_s': max((event['time_s'] for event in events), default=0),
        }
        with self.uow_factory() as uow:
            uow.connection.execute(insert(integration_simulations).values(
                id=identity, scope_id=actor.scope_id, run_id=run_id,
                created_at=datetime.now(UTC).replace(microsecond=0),
                created_by=actor.actor_id, payload=payload).on_conflict_do_nothing())
            persisted = uow.connection.execute(select(integration_simulations.c.payload).where(
                integration_simulations.c.id == identity,
                integration_simulations.c.scope_id == actor.scope_id)).scalar_one()
            if persisted != payload:
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT,
                                   'simulation baseline differs from immutable checked run')
        return self.get(run_id, actor)

    def get(self, run_id: UUID, actor) -> dict:
        row = self._simulation(run_id, actor)
        incident = self._incident(row['id'], actor)
        return {
            **row['payload'],
            'simulation_id': str(row['id']),
            'status': 'ready' if incident is None else incident['status'],
            'incident': None if incident is None else self._incident_view(incident),
            'active_view': 'approved' if incident is not None and incident['status'] == 'approved' else 'baseline',
            'active_version': 1 if incident is not None and incident['status'] == 'approved' else 0,
            'operational_schedule_mutated': False,
            'inventory_mutated': False,
        }

    @staticmethod
    def _incident_view(row):
        return {**row['payload'], 'status': row['status'],
                'row_version': row['row_version'], 'event_id': str(row['event_id'])}

    @staticmethod
    def _s1_advice(result, vehicle_id, at_s, delay_s, budget_ms):
        """Run the S1 local solver, but do not splice its depot-origin plan mid-road.

        S1's current local problem starts at the vehicle's depot; using that as a
        mid-road continuation would teleport a truck.  The approved P0 policy is
        the separately checked hold-and-resume projection instead.
        """
        from logistics_backend.application.vehicle_delay_reschedule import (
            VehicleDelayRequest,
            resolve_vehicle_delay,
        )
        from logistics_contracts.transport import TransportProblemDTO, TransportSolutionDTO

        problem = TransportProblemDTO.model_validate(result['transport_problem']).to_domain()
        solution = TransportSolutionDTO.model_validate(result['transport_solution']).to_domain()
        if solution.candidate is None:
            return {'status': 'not_resolved', 'reason': 'baseline_candidate_missing'}
        outcome = resolve_vehicle_delay(problem, solution.candidate, solution.stops,
            VehicleDelayRequest(UUID(vehicle_id), delay_s, at_s, budget_ms))
        return {'status': outcome.status, 'reason': outcome.reason,
                'affected_order_ids': [str(item) for item in outcome.affected_order_ids],
                'applied_to_simulation': False,
                'note': 'S1 depot-origin local route is advisory; mid-road continuation uses safe hold/resume'}

    def incident(self, run_id: UUID, command, actor, trace_id: UUID) -> dict:
        simulation = self._simulation(run_id, actor)
        original = simulation['payload']
        existing = self._incident(simulation['id'], actor)
        identity = uuid5(NAMESPACE, f'{simulation["id"]}:{command.source_event_id}')
        if existing:
            if existing['id'] != identity:
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT,
                                   'only one incident per simulation in this release')
            prior = existing['payload']
            if (prior['vehicle_id'], prior['time_s'], prior['delay_s'], prior['reason']) != (
                    str(command.vehicle_id), command.time_s, command.delay_s, command.reason):
                raise ServiceError(ErrorCode.IDEMPOTENCY_CONFLICT, 'incident input changed')
            return self._incident_view(existing)

        vehicle_id = str(command.vehicle_id)
        tracks = original['tracks']
        if not any(track['vehicle_id'] == vehicle_id for track in tracks):
            raise ServiceError(ErrorCode.INVALID_INPUT, 'vehicle not in checked transport plan')
        baseline_state = state_at_time({'events': original['events']}, self._run(run_id, actor), command.time_s)
        if vehicle_id not in baseline_state['in_transit_vehicle_ids']:
            raise ServiceError(ErrorCode.INVALID_INPUT, 'vehicle not in transit at incident time')
        try:
            candidate_tracks = hold_and_shift(tracks, vehicle_id, command.time_s, command.delay_s)
            result = self._run(run_id, actor)
            impact = delay_impact(result, original['events'], vehicle_id,
                                  command.time_s, command.delay_s)
            candidate_events = retime_events(original['events'], vehicle_id, command.time_s,
                                             command.delay_s, str(identity))
        except SimulationTrackError as exc:
            raise ServiceError(ErrorCode.INVALID_INPUT, str(exc)) from exc

        route = next(track for track in tracks if track['vehicle_id'] == vehicle_id)
        task_id = next((task for stop in route['stops'] if stop['departure_s'] >= command.time_s
                        for task in stop['task_ids']), None)
        if task_id is None:
            raise ServiceError(ErrorCode.INVALID_INPUT, 'no remaining transport task for event')

        # S1's persisted event contract remains legal: kind=transport_delay,
        # entity=transport_task.  The stable source ID makes retries idempotent.
        s1 = self._s1_advice(result, vehicle_id, command.time_s, command.delay_s, command.budget_ms)
        envelope = EventEnvelopeDTO.model_validate({
            'schema_version': '2.0.0', 'source': 'integration-simulation',
            'source_event_id': f'{simulation["id"]}:{command.source_event_id}',
            'kind': 'transport_delay', 'occurred_at_utc': datetime.now(UTC).replace(microsecond=0),
            'simulation_id': simulation['id'], 'expected_revision': None,
            'payload': {'kind': 'transport_delay',
                        'entity_ref': {'kind': 'transport_task', 'id': task_id, 'revision': None},
                        'transport_task_id': task_id, 'effective_at_s': command.time_s,
                        'additional_seconds': command.delay_s, 'reason': command.reason},
        })
        payload = {
            'id': str(identity), 'simulation_id': str(simulation['id']),
            'vehicle_id': vehicle_id, 'time_s': command.time_s,
            'delay_s': command.delay_s, 'reason': command.reason,
            'source_event_id': command.source_event_id,
            'strategy': 'simulated_hold_resume', 'candidate_version': 1, 'impact': impact,
            's1_local_solver': s1, 'candidate_tracks': candidate_tracks,
            'candidate_events': candidate_events,
            'proposal_valid': impact['valid'],
        }
        now = datetime.now(UTC).replace(microsecond=0)
        with self.uow_factory() as uow:
            # Different browser requests must not register two events for one
            # simulation before the UNIQUE(simulation_id) insert is visible.
            lock_id = int.from_bytes(simulation['id'].bytes[:8], 'big', signed=True)
            uow.connection.execute(text('SELECT pg_advisory_xact_lock(:lock_id)'), {'lock_id': lock_id})
            previous = uow.connection.execute(select(integration_simulation_incidents).where(
                integration_simulation_incidents.c.simulation_id == simulation['id'],
                integration_simulation_incidents.c.scope_id == actor.scope_id)).mappings().first()
            if previous:
                if previous['id'] == identity and (
                    previous['payload']['vehicle_id'], previous['payload']['time_s'],
                    previous['payload']['delay_s'], previous['payload']['reason']) == (
                        vehicle_id, command.time_s, command.delay_s, command.reason):
                    return self._incident_view(previous)
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, 'concurrent different incident')
            receipt = self.events.ingest(envelope, actor, trace_id)
            uow.connection.execute(insert(integration_simulation_incidents).values(
                id=identity, simulation_id=simulation['id'], scope_id=actor.scope_id,
                event_id=receipt.event_id, status='pending', row_version=0,
                created_at=now, updated_at=now, created_by=actor.actor_id,
                payload=payload).on_conflict_do_nothing())
            persisted = uow.connection.execute(select(integration_simulation_incidents).where(
                integration_simulation_incidents.c.simulation_id == simulation['id'],
                integration_simulation_incidents.c.scope_id == actor.scope_id)).mappings().one()
            if (persisted['id'] != identity or
                (persisted['payload']['vehicle_id'], persisted['payload']['time_s'],
                 persisted['payload']['delay_s'], persisted['payload']['reason']) !=
                (vehicle_id, command.time_s, command.delay_s, command.reason)):
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, 'concurrent different incident')
        return self._incident_view(persisted)

    def decide(self, run_id: UUID, incident_id: UUID, decision: str, actor,
               expected_row_version: int) -> dict:
        if decision not in ('approved', 'rejected'):
            raise ServiceError(ErrorCode.INVALID_INPUT, 'invalid simulation decision')
        simulation = self._simulation(run_id, actor)
        with self.uow_factory() as uow:
            current = uow.connection.execute(select(integration_simulation_incidents).where(
                integration_simulation_incidents.c.id == incident_id,
                integration_simulation_incidents.c.simulation_id == simulation['id'],
                integration_simulation_incidents.c.scope_id == actor.scope_id).with_for_update()).mappings().first()
            if not current:
                raise ServiceError(ErrorCode.NOT_FOUND, 'incident not found')
            if current['status'] == decision:
                return {**self._incident_view(current), 'idempotent': True}
            if current['status'] != 'pending':
                raise ServiceError(ErrorCode.INVALID_TRANSITION, 'incident already decided')
            if current['row_version'] != expected_row_version:
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, 'stale incident version')
            if decision == 'approved' and not current['payload']['proposal_valid']:
                raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT,
                                   'simulation projection violates a hard constraint')
            updated = uow.connection.execute(update(integration_simulation_incidents).where(
                integration_simulation_incidents.c.id == incident_id,
                integration_simulation_incidents.c.status == 'pending',
                integration_simulation_incidents.c.row_version == expected_row_version).values(
                    status=decision, row_version=expected_row_version + 1,
                    updated_at=datetime.now(UTC).replace(microsecond=0))
                .returning(integration_simulation_incidents.c.id)).first()
            if updated is None:
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, 'concurrent incident decision')
        return {**self._incident_view({**current, 'status': decision,
                                       'row_version': expected_row_version + 1}), 'idempotent': False}

    def state_at(self, run_id: UUID, at_s: int, view: str, actor) -> dict:
        if view not in ('active', 'baseline', 'candidate'):
            raise ServiceError(ErrorCode.INVALID_INPUT, 'view must be active, baseline or candidate')
        simulation = self._simulation(run_id, actor)
        incident = self._incident(simulation['id'], actor)
        selected = view
        if view == 'active':
            selected = 'candidate' if incident is not None and incident['status'] == 'approved' else 'baseline'
        if selected == 'candidate' and incident is None:
            raise ServiceError(ErrorCode.NOT_FOUND, 'no incident candidate')
        payload = simulation['payload']
        tracks = payload['tracks'] if selected == 'baseline' else incident['payload']['candidate_tracks']
        events = payload['events'] if selected == 'baseline' else incident['payload']['candidate_events']
        source = 'simulated_from_planned' if selected == 'baseline' else 'simulated_delay_projection'
        state = state_at_time({'events': events}, self._run(run_id, actor), at_s)
        positions = {track['vehicle_id']: sample_track(track, at_s) for track in tracks}
        # The S4 position set was derived from unshifted planned stops.  In a
        # simulated suffix use the actual segment projection for consistency.
        state['halted_vehicle_positions'] = {
            vehicle_id: positions[vehicle_id]['from_node_id']
            if positions[vehicle_id]['progress'] < 1 else positions[vehicle_id]['to_node_id']
            for vehicle_id in state['in_transit_vehicle_ids'] if vehicle_id in positions
        }
        return {
            **state, 'run_id': str(run_id), 'simulation_id': str(simulation['id']),
            'source_kind': source, 'view': selected, 'time_s': at_s,
            'incident_status': None if incident is None else incident['status'],
            'active_version': 1 if selected == 'candidate' else 0,
            'vehicle_positions': positions,
            'events': [event for event in events if event['time_s'] <= at_s],
            'event_count': len(events),
            'operational_schedule_mutated': False, 'inventory_mutated': False,
        }
