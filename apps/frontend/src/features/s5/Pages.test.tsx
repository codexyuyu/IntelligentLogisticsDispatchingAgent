import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { request } from '../../api';
import GanttPage from './GanttPage';
import InventoryPage from './InventoryPage';
import TimelinePage from './TimelinePage';
import type { CheckedRun, TimelineResponse } from './model';

vi.mock('../../api', () => ({ request: vi.fn() }));
const runId = '00000000-0000-4000-8000-000000000001';
const warehouseId = '00000000-0000-4000-8000-000000000002';
const taskId = '00000000-0000-4000-8000-000000000003';
const run: CheckedRun = {
  run_id: runId, status: 'checked', joint_validation: { valid: true },
  warehouse_problem: {
    tasks: [{ id: taskId, warehouse_id: warehouseId, order_id: 'order-1', kind: 'receive', duration_s: 20 }],
    snapshot: { scope: { warehouse_ids: [warehouseId], order_ids: ['order-1'] },
      orders: [{ id: 'order-1', external_ref: 'CC10-O01' }] },
  },
  warehouse_solution: { status: 'optimal', assignments: [
    { task_id: taskId, resource_id: 'dock-1', start_s: 10, end_s: 30 },
  ] },
};
const checks = {
  event_delivery_mismatch: true, event_handoff_mismatch: true, duplicate_vehicle_route: true,
  vehicle_departure_event_mismatch: true, vehicle_return_event_mismatch: true,
  handoff_before_warehouse_operations_finished: true, departure_before_loading_ready: true,
};
const timeline: TimelineResponse = {
  schema_version: '2.0.0', run_id: runId, source_kind: 'planned_validated', event_count: 1,
  events: [{ id: 'event-1', sequence: 0, time_s: 10, kind: 'warehouse_work_start',
    object_id: taskId, order_id: 'order-1', vehicle_id: null, route_id: null, node_id: null }],
  reconciliation: { passed: true, checks, scope_orders: 1, planned_delivery_orders: 1,
    explicitly_unserved_orders: 0, order_details: [] },
};

let root: Root;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  const host = document.createElement('div'); document.body.append(host);
  root = createRoot(host);
  vi.mocked(request).mockReset();
});
afterEach(async () => { await act(async () => root.unmount()); });

describe('S5 API-connected presentation', () => {
  it('shows planned Gantt intervals and actual task status from separate endpoints', async () => {
    localStorage.setItem('integration_last_run', runId);
    vi.mocked(request).mockImplementation(async (path, init) => {
      if (path === `/integration/runs/${runId}`) return run;
      if (path === `/warehouses/${warehouseId}/tasks?limit=500`) return {
        schema_version: '2.0.0', total: 1, items: [{ ...run.warehouse_problem!.tasks[0], status: 'ready', row_version: 1 }],
      };
      if (path === `/warehouses/${warehouseId}/tasks/${taskId}/transitions` && init?.method === 'POST') {
        return { ...run.warehouse_problem!.tasks[0], status: 'running', row_version: 2 };
      }
      throw new Error(`unexpected ${path}`);
    });
    await act(async () => root.render(<GanttPage />));
    expect(document.body.textContent).toContain('CC10-O01');
    const bar = document.querySelector<HTMLButtonElement>('[aria-label*="CC10-O01 入库"]');
    expect(bar).not.toBeNull();
    expect(vi.mocked(request).mock.calls.some(call => call[0] === `/warehouses/${warehouseId}/tasks?limit=500`)).toBe(true);
    await act(async () => bar!.click());
    const advance = [...document.querySelectorAll('button')].find(button => button.textContent?.includes('手动推进为'))!;
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    await act(async () => advance.click());
    expect(vi.mocked(request).mock.calls.filter(call => call[1]?.method === 'POST')).toHaveLength(0);
    confirm.mockReturnValue(true);
    await act(async () => advance.click());
    const writes = vi.mocked(request).mock.calls.filter(call => call[1]?.method === 'POST');
    expect(writes).toHaveLength(1);
    expect(JSON.parse(writes[0][1]!.body as string)).toMatchObject({ run_id: runId,
      target_status: 'running', expected_row_version: 1 });
  });

  it('reads inventory without creating movements', async () => {
    vi.mocked(request).mockResolvedValue({ schema_version: '2.0.0', total_entries: 1, has_more: false,
      items: [{ id: 'movement', cargo_id: 'cargo', location_id: 'location', source_location_id: null,
        quantity_delta: 4, created_at: '2026-01-01T00:00:00Z', run_id: null, task_id: null,
        operation_kind: 'receive' }],
      positions: [{ cargo_id: 'cargo', location_id: 'location', quantity_units: 4 }],
    });
    await act(async () => root.render(<InventoryPage />));
    expect(document.body.textContent).toContain('入库完成');
    expect(vi.mocked(request).mock.calls.map(call => call[0])).toContain('/inventory?limit=500');
    expect(vi.mocked(request).mock.calls.every(call => call[1]?.method !== 'POST')).toBe(true);
  });

  it('blocks an unchecked run before requesting replay', async () => {
    localStorage.setItem('integration_last_run', runId);
    vi.mocked(request).mockResolvedValue({ ...run, status: 'failed', joint_validation: { valid: false } });
    await act(async () => root.render(<TimelinePage />));
    expect(document.querySelector('[role="alert"]')?.textContent).toContain('尚未通过独立联合校验');
    expect(vi.mocked(request).mock.calls.map(call => call[0])).toEqual([`/integration/runs/${runId}`]);
  });

  it('shows validated planned replay and fetches state-at without POST', async () => {
    localStorage.setItem('integration_last_run', runId);
    vi.mocked(request).mockImplementation(async path => {
      if (path === `/integration/runs/${runId}`) return run;
      if (path === `/integration/runs/${runId}/timeline`) return timeline;
      if (path === `/integration/runs/${runId}/state-at?time_s=0`) return {
        schema_version: '2.0.0', run_id: runId, source_kind: 'planned_validated', time_s: 0,
        completed_order_ids: [], completed_operation_ids: [], active_operation_ids: [],
        in_transit_vehicle_ids: [], returned_vehicle_ids: [], not_yet_departed_vehicle_ids: [],
        onboard_pending_order_ids: [], available_depot_vehicle_ids: [], halted_vehicle_positions: {},
        interrupted_operation_ids: [],
      };
      throw new Error(`unexpected ${path}`);
    });
    await act(async () => root.render(<TimelinePage />));
    expect(document.body.textContent).toContain('对账通过');
    expect(document.querySelectorAll('.s5-state-item')).toHaveLength(10);
    expect(vi.mocked(request).mock.calls.map(call => call[0])).toContain(`/integration/runs/${runId}/state-at?time_s=0`);
    expect(vi.mocked(request).mock.calls.every(call => call[1]?.method !== 'POST')).toBe(true);
  });
});
