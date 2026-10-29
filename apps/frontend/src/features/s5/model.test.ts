import { describe, expect, it } from 'vitest';
import { buildGanttTasks, isValidatedTimeline, replayTimes } from './model';
import type { CheckedRun, TimelineResponse } from './model';

const checked: CheckedRun = {
  run_id: 'run', status: 'checked', joint_validation: { valid: true },
  warehouse_problem: {
    snapshot: { scope: { order_ids: ['order-1'], warehouse_ids: ['warehouse-1'] },
      orders: [{ id: 'order-1', external_ref: 'CC10-O01' }] },
    tasks: [
      { id: 'r', order_id: 'order-1', warehouse_id: 'warehouse-1', kind: 'receive', duration_s: 20 },
      { id: 's', order_id: 'order-1', warehouse_id: 'warehouse-1', kind: 'sort', duration_s: 10 },
      { id: 'l', order_id: 'order-1', warehouse_id: 'warehouse-1', kind: 'load', duration_s: 10 },
    ],
  },
  warehouse_solution: { status: 'optimal', assignments: [
    { task_id: 'r', resource_id: 'dock', start_s: 0, end_s: 20 },
    { task_id: 'r', resource_id: 'worker', start_s: 2, end_s: 19 },
    { task_id: 's', resource_id: 'worker', start_s: 20, end_s: 30 },
    { task_id: 'l', resource_id: 'dock', start_s: 30, end_s: 40 },
  ] },
};

const checks = {
  event_delivery_mismatch: true, event_handoff_mismatch: true, duplicate_vehicle_route: true,
  vehicle_departure_event_mismatch: true, vehicle_return_event_mismatch: true,
  handoff_before_warehouse_operations_finished: true, departure_before_loading_ready: true,
};

const sampleTimeline: TimelineResponse = {
  schema_version: '2.0.0', run_id: 'run', source_kind: 'planned_validated', event_count: 2,
  events: [
    { id: 'e1', sequence: 0, time_s: 0, kind: 'warehouse_work_start', object_id: 'r', order_id: 'order-1', vehicle_id: null, route_id: null, node_id: null },
    { id: 'e2', sequence: 1, time_s: 20, kind: 'warehouse_work_finished', object_id: 'r', order_id: 'order-1', vehicle_id: null, route_id: null, node_id: null },
  ],
  reconciliation: { passed: true, checks, scope_orders: 1, planned_delivery_orders: 1,
    explicitly_unserved_orders: 0, order_details: [] },
};

describe('S5 evidence selectors', () => {
  it('collapses multi-resource assignments into 3 ordered stages per order', () => {
    const tasks = buildGanttTasks(checked, [{ ...checked.warehouse_problem!.tasks[0], status: 'ready', row_version: 1 }]);
    expect(tasks).toHaveLength(3);
    expect(tasks.map(task => task.kind)).toEqual(['receive', 'sort', 'load']);
    expect(tasks[0]).toMatchObject({ orderLabel: 'CC10-O01', startS: 0, endS: 20,
      resourceIds: ['dock', 'worker'], status: 'ready', rowVersion: 1 });
    expect(tasks[1].status).toBeNull();
  });

  it('keeps actual task state separate from planned task time', () => {
    expect(buildGanttTasks(checked)[0].status).toBeNull();
    expect(buildGanttTasks({ ...checked, warehouse_solution: { status: 'failed', assignments: [] } })).toEqual([]);
  });

  it('deduplicates replay seconds without losing deterministic order', () => {
    expect(replayTimes([{ ...sampleTimeline.events[0], time_s: 5 },
      { ...sampleTimeline.events[1], time_s: 5 }, { ...sampleTimeline.events[1], time_s: 3 }])).toEqual([0, 3, 5]);
  });

  it('rejects unvalidated, out-of-order, or identity-inconsistent replay payloads', () => {
    expect(isValidatedTimeline(sampleTimeline)).toBe(true);
    expect(isValidatedTimeline({ ...sampleTimeline, source_kind: 'observed' })).toBe(false);
    expect(isValidatedTimeline({ ...sampleTimeline, reconciliation: {
      ...sampleTimeline.reconciliation, planned_delivery_orders: 2,
    } })).toBe(false);
    expect(isValidatedTimeline({ ...sampleTimeline, events: [sampleTimeline.events[1], sampleTimeline.events[0]] })).toBe(false);
  });
});
