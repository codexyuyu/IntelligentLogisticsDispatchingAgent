"""The 14 metrics in METRICS_CONTRACT.md; missing evidence stays null."""
from dataclasses import dataclass
from itertools import pairwise

from logistics_domain.metrics import MetricSource, MetricValue, MissingReason
from logistics_evaluation.metrics import _missing, _value


@dataclass(frozen=True)
class Span:
    start_s: int
    end_s: int
    units: int = 1

    def __post_init__(self):
        if self.start_s < 0 or self.end_s < self.start_s or self.units < 0:
            raise ValueError('invalid resource span')


@dataclass(frozen=True)
class ResourceUse:
    resource_id: str
    used: tuple[Span, ...]
    available: tuple[Span, ...]


@dataclass(frozen=True)
class OrderOutcome:
    order_id: str
    completion_s: int | None
    due_s: int | None
    hard_latest_s: int | None = None
    service_s: int = 0
    cancelled_at_s: int | None = None
    service_started_s: int | None = None


@dataclass(frozen=True)
class TaskState:
    task_id: str
    resource_ids: tuple[str, ...]
    start_s: int
    end_s: int
    predecessor_id: str | None = None
    completed_at_s: int | None = None


@dataclass(frozen=True)
class MetricInput:
    scope_id: str
    source: MetricSource
    window_start_s: int
    window_end_s: int
    orders: tuple[OrderOutcome, ...] | None = None
    distance_m: int | None = None
    transport_cost_cents: int | None = None
    vehicles: tuple[ResourceUse, ...] | None = None
    warehouse_zones: tuple[ResourceUse, ...] | None = None
    docks: tuple[ResourceUse, ...] | None = None
    equipment: tuple[ResourceUse, ...] | None = None
    solve_ms: tuple[float, ...] | None = None
    detection_ms: tuple[float, ...] | None = None
    reschedule_ms: tuple[float, ...] | None = None
    base_tasks: tuple[TaskState, ...] | None = None
    candidate_tasks: tuple[TaskState, ...] | None = None
    event_s: int = 0
    shift_scale_s: int = 3600

    def __post_init__(self):
        if not self.scope_id or self.window_start_s < 0 or self.window_end_s <= self.window_start_s:
            raise ValueError('metric scope and positive observation window required')
        if not isinstance(self.source, MetricSource) or self.shift_scale_s <= 0:
            raise ValueError('invalid metric source or shift scale')
        for values, key in ((self.orders, 'order_id'), (self.vehicles, 'resource_id'),
                            (self.warehouse_zones, 'resource_id'), (self.docks, 'resource_id'),
                            (self.equipment, 'resource_id'), (self.base_tasks, 'task_id'),
                            (self.candidate_tasks, 'task_id')):
            if values is not None and len({getattr(v, key) for v in values}) != len(values):
                raise ValueError('duplicate metric evidence identity')


@dataclass(frozen=True)
class MetricReport:
    scope_id: str
    source: MetricSource
    window_start_s: int
    window_end_s: int
    definition_version: str
    values: tuple[MetricValue, ...]
    cancelled_count: int | None
    open_overdue_s: int | None
    due_fallback_order_ids: tuple[str, ...]


def _utilization(resources, start, end, weighted):
    numerator = denominator = 0
    for resource in resources:
        points = sorted({start, end} | {p for span in (*resource.used, *resource.available)
                                       for p in (span.start_s, span.end_s) if start < p < end})
        for left, right in pairwise(points):
            use = sum(s.units for s in resource.used if s.start_s <= left < s.end_s)
            available = sum(s.units for s in resource.available if s.start_s <= left < s.end_s)
            if not weighted:
                use, available = int(use > 0), int(available > 0)
            denominator += available * (right-left)
            # Fault/unavailability intervals are excluded from busy seconds too.
            if available:
                numerator += use * (right-left)
    return numerator, denominator


def calculate_metrics(data: MetricInput) -> MetricReport:
    metrics = []
    source = data.source
    def missing(code, unit, reason=MissingReason.MISSING_DATA):
        metrics.append(_missing(code, source, unit, reason))
    def number(code, unit, value, n=1):
        if value is None:
            missing(code, unit)
        elif value < 0:
            raise ValueError(f'negative metric evidence: {code}')
        else:
            metrics.append(_value(code, source, unit, value, value, None, n))
    def ratio(code, unit, a, b, n):
        if b == 0:
            missing(code, unit, MissingReason.DIVISION_BY_ZERO)
        else:
            metrics.append(_value(code, source, unit, a/b, a, b, n))
    cancelled = overdue = None
    fallback = []
    if data.orders is None:
        for code, unit in (('delivery_rate', 'ratio'), ('on_time_rate', 'ratio'), ('average_delay_s', 's')):
            missing(code, unit)
    else:
        effective = [o for o in data.orders if not (o.cancelled_at_s is not None
            and o.cancelled_at_s <= data.window_end_s and (o.service_started_s is None
            or o.cancelled_at_s < o.service_started_s))]
        cancelled = len(data.orders)-len(effective)
        delivered = [o for o in effective if o.completion_s is not None and o.completion_s <= data.window_end_s]
        due = {}
        for order in effective:
            due[order.order_id] = order.due_s
            if order.due_s is None and order.hard_latest_s is not None:
                due[order.order_id] = order.hard_latest_s + order.service_s
                fallback.append(order.order_id)
        ratio('delivery_rate', 'ratio', len(delivered), len(effective), len(effective))
        if any(due[o.order_id] is None for o in effective):
            missing('on_time_rate', 'ratio')
            missing('average_delay_s', 's')
        else:
            ratio('on_time_rate', 'ratio', sum(o.completion_s <= due[o.order_id] for o in delivered),
                  len(effective), len(effective))
            ratio('average_delay_s', 's', sum(max(0, o.completion_s-due[o.order_id]) for o in delivered),
                  len(delivered), len(delivered))
            delivered_ids = {o.order_id for o in delivered}
            overdue = sum(max(0, data.window_end_s-due[o.order_id]) for o in effective
                          if o.order_id not in delivered_ids)
    number('total_distance_m', 'm', data.distance_m)
    number('total_cost_cents', 'fen', data.transport_cost_cents)
    for code, resources, weighted in (
        ('vehicle_utilization', data.vehicles, False), ('warehouse_utilization', data.warehouse_zones, True),
        ('dock_utilization', data.docks, False), ('equipment_utilization', data.equipment, True)):
        if resources is None:
            missing(code, 'ratio')
        else:
            a, b = _utilization(resources, data.window_start_s, data.window_end_s, weighted)
            ratio(code, 'ratio', a, b, len(resources))
    for code, samples in (('solve_time_ms', data.solve_ms), ('exception_detection_ms', data.detection_ms),
                          ('reschedule_time_ms', data.reschedule_ms)):
        if samples is None or not samples:
            missing(code, 'ms')
        elif any(v < 0 for v in samples):
            raise ValueError('negative measured duration')
        else:
            ratio(code, 'ms', sum(samples), len(samples), len(samples))
    if data.base_tasks is None or data.candidate_tasks is None:
        missing('changed_tasks', 'count')
        missing('plan_disturbance', 'ratio')
    else:
        base, candidate = ({t.task_id: t for t in items} for items in (data.base_tasks, data.candidate_tasks))
        def state(t):
            return (set(t.resource_ids), t.start_s, t.end_s, t.predecessor_id)
        completed = {k for k, t in base.items() if t.completed_at_s is not None and t.completed_at_s <= data.event_s}
        if any(k not in candidate or state(base[k]) != state(candidate[k]) for k in completed):
            raise ValueError('completed facts changed')
        future = set(base)-completed
        added, removed = set(candidate)-set(base), future-set(candidate)
        common = future & set(candidate)
        changed = added | removed | {k for k in common if state(base[k]) != state(candidate[k])}
        n = max(1, len(future | added))
        assignment = sum(set(base[k].resource_ids) != set(candidate[k].resource_ids) for k in common)/n
        time = sum(min(1, abs(candidate[k].start_s-base[k].start_s)/data.shift_scale_s) for k in common)/n
        order = sum(base[k].predecessor_id != candidate[k].predecessor_id for k in common)/n
        disturbance = .4*assignment + .3*time + .2*order + .1*len(added | removed)/n
        number('changed_tasks', 'count', len(changed), len(future | added))
        number('plan_disturbance', 'ratio', disturbance, len(future | added))
    return MetricReport(data.scope_id, source, data.window_start_s, data.window_end_s, '1.0.0',
                        tuple(metrics), cancelled, overdue, tuple(sorted(fallback)))
