"""R05 post-solve timeline: storage occupancies, exposure segments, changeovers.

Pure derivation from a solved schedule.  This module never builds or reads a
CP-SAT model: it is the *result* side of the R05 contract, and the independent
validator re-derives the same numbers from the snapshot to cross-check them.
"""
from __future__ import annotations

import hashlib

from app.contracts.coldchain import (
    ColdChainPlan,
    ColdChainSnapshot,
    ExposureSegment,
    ScheduledChangeover,
    ScheduledOccupancy,
    SetupPolicy,
)
from app.contracts.entities import ScheduledOperation
from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult


def _short_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1('\x1f'.join(parts).encode('utf-8')).hexdigest()[:12]
    return f'{prefix}_{digest}'


def _by_operation(result: WarehouseScheduleResult) -> dict[str, ScheduledOperation]:
    return {item.operation_id: item for item in result.operations}


class ColdChainTimelineBuilder:
    """Resolve declared R05 occupancies into planned half-open intervals."""

    def build(self, request: WarehouseScheduleRequest,
              result: WarehouseScheduleResult) -> tuple[ScheduledOccupancy, ...]:
        coldchain = request.snapshot.coldchain
        if coldchain is None:
            return ()
        scheduled = _by_operation(result)
        resolved: list[ScheduledOccupancy] = []
        for declared in coldchain.occupancies:
            start = self._occupancy_start(declared, scheduled)
            end = self._occupancy_end(declared, scheduled, coldchain)
            if end <= start:
                # Inbound and outbound at the same instant: nothing is stored, so
                # there is no interval to declare (and no capacity consumed).
                continue
            resolved.append(ScheduledOccupancy(
                occupancy_id=declared.occupancy_id,
                batch_id=declared.batch_id,
                location_id=declared.location_id,
                capacity_use=declared.capacity_use,
                start_s=start,
                end_s=end,
            ))
        resolved.sort(key=lambda item: (item.start_s, item.end_s, item.occupancy_id))
        return tuple(resolved)

    @staticmethod
    def _occupancy_start(declared, scheduled) -> int:
        if declared.origin == 'initial_stock':
            return 0
        if declared.inbound_operation_id is not None:
            item = scheduled.get(declared.inbound_operation_id)
            return 0 if item is None else item.end_s
        return int(declared.declared_start_s or 0)

    @staticmethod
    def _occupancy_end(declared, scheduled, coldchain: ColdChainSnapshot) -> int:
        if declared.outbound_operation_id is None:
            return coldchain.horizon_s
        item = scheduled.get(declared.outbound_operation_id)
        if item is None:
            return coldchain.horizon_s
        return item.start_s

    def exposure_segments(self, request: WarehouseScheduleRequest,
                          result: WarehouseScheduleResult) -> tuple[ExposureSegment, ...]:
        """Warehouse and loading exposure only; transport is joint-validation's job."""
        coldchain = request.snapshot.coldchain
        if coldchain is None:
            return ()
        scheduled = _by_operation(result)
        operations = {op.operation_id: op for op in request.snapshot.operations}
        batch_by_order: dict[str, str] = {
            order.order_id: order.batch_id for order in request.snapshot.orders
        }
        segments: list[ExposureSegment] = []

        for occupancy in self.build(request, result):
            segments.append(ExposureSegment(
                segment_id=_short_id('exp', occupancy.occupancy_id, 'in_warehouse'),
                batch_id=occupancy.batch_id,
                scope='in_warehouse',
                start_s=occupancy.start_s,
                end_s=occupancy.end_s,
                source_kind='planned',
            ))

        for operation_id, item in sorted(scheduled.items()):
            source = operations.get(operation_id)
            if source is None or 'load' not in source.operation_kind:
                continue
            for order_id in source.order_ids:
                batch_id = batch_by_order.get(order_id)
                if batch_id is None:
                    continue
                segments.append(ExposureSegment(
                    segment_id=_short_id('exp', operation_id, order_id, 'loading'),
                    batch_id=batch_id,
                    scope='loading',
                    start_s=item.start_s,
                    end_s=item.end_s,
                    source_kind='planned',
                ))
        segments.sort(key=lambda item: (item.start_s, item.end_s, item.segment_id))
        return tuple(segments)

    def changeovers(self, request: WarehouseScheduleRequest,
                    result: WarehouseScheduleResult) -> tuple[ScheduledChangeover, ...]:
        """Adjacent-pair changeover records; the first task vs initial class is
        checked by the validator, not recorded, because it has no predecessor."""
        coldchain = request.snapshot.coldchain
        if coldchain is None:
            return ()
        policies = {policy.policy_id: policy for policy in coldchain.setup_policies}
        resources = {res.resource_id: res for res in request.snapshot.resources}
        operations = {op.operation_id: op for op in request.snapshot.operations}

        by_resource: dict[str, list[tuple[int, int, str]]] = {}
        for item in result.operations:
            if item.scheduled_kind != 'task':
                continue
            by_resource.setdefault(item.resource_id, []).append(
                (item.start_s, item.end_s, item.operation_id)
            )

        setup_by_target = {
            item.setup_for_operation_id: item.operation_id
            for item in result.operations if item.scheduled_kind == 'setup'
        }

        records: list[ScheduledChangeover] = []
        for resource_id, entries in sorted(by_resource.items()):
            resource = resources.get(resource_id)
            if resource is None or resource.setup_policy_id is None:
                continue
            policy = policies.get(resource.setup_policy_id)
            if policy is None:
                continue
            entries.sort()
            previous_class: str | None = None
            previous_id: str | None = None
            for start, end, operation_id in entries:
                current_class = operations[operation_id].setup_class
                if current_class is None:
                    continue
                if previous_id is not None and previous_class is not None \
                        and current_class != previous_class:
                    duration = _setup_duration(policy, previous_class, current_class)
                    if duration:
                        records.append(ScheduledChangeover(
                            changeover_id=_short_id('chg', resource_id, previous_class,
                                                    current_class, previous_id, operation_id),
                            resource_id=resource_id,
                            from_class=previous_class,
                            to_class=current_class,
                            duration_s=duration,
                            after_operation_id=previous_id,
                            before_operation_id=operation_id,
                            setup_operation_id=setup_by_target.get(operation_id),
                        ))
                previous_class = current_class
                previous_id = operation_id
        return tuple(records)

    def plan(self, request: WarehouseScheduleRequest,
             result: WarehouseScheduleResult) -> ColdChainPlan | None:
        coldchain = request.snapshot.coldchain
        if coldchain is None:
            return None
        return ColdChainPlan(
            rule_version=coldchain.rule_version,
            occupancies=self.build(request, result),
            exposure_segments=self.exposure_segments(request, result),
            changeovers=self.changeovers(request, result),
        )


def _setup_duration(policy: SetupPolicy, from_class: str, to_class: str) -> int | None:
    if from_class == to_class:
        return 0
    for rule in policy.rules:
        if rule.from_class == from_class and rule.to_class == to_class:
            return rule.duration_s
    return policy.default_duration_s
