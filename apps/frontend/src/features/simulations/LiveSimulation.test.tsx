import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LiveSimulation from './LiveSimulation';
import { request } from '../../api';

vi.mock('../../api', () => ({ request: vi.fn(), idempotencyKey: () => 'test-key' }));
let root: Root;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  const host = document.createElement('div'); document.body.append(host); root = createRoot(host);
  vi.mocked(request).mockReset();
});
afterEach(async () => { await act(async () => root.unmount()); });

describe('simulation recovery', () => {
  it('loads the saved job and result without submitting a second simulation', async () => {
    localStorage.setItem('dsh_simulation_job_id', 'saved-job');
    localStorage.setItem('dsh_transport_job_id', 'transport-job');
    vi.mocked(request).mockImplementation(async path => path.endsWith('/result')
      ? { kind: 'simulation', value: { status: 'completed', final_time_s: 100, events: [], delivered_order_ids: ['order-1'], seed: 0 } }
      : { job_id: 'saved-job', status: 'completed' });
    await act(async () => root.render(<LiveSimulation />));
    expect(document.body.textContent).toContain('送达订单：1');
    expect((document.querySelector('input') as HTMLInputElement).value).toBe('transport-job');
    expect(vi.mocked(request).mock.calls.map(call => call[0])).toEqual(['/jobs/saved-job', '/jobs/saved-job/result']);
  });
  it('rejects a completed job whose result is not a simulation', async () => {
    localStorage.setItem('dsh_simulation_job_id', 'wrong-job');
    vi.mocked(request).mockImplementation(async path => path.endsWith('/result')
      ? { kind: 'transport', value: {} } : { job_id: 'wrong-job', status: 'completed' });
    await act(async () => root.render(<LiveSimulation />));
    expect(document.querySelector('[role="alert"]')?.textContent).toContain('不是有效仿真结果');
    expect(document.body.textContent).not.toContain('送达订单：');
  });
});
