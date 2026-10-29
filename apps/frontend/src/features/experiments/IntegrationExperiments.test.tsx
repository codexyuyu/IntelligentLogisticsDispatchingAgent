import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import IntegrationExperiments from './IntegrationExperiments';
import { request } from '../../api';

vi.mock('../../api', () => ({ request: vi.fn(), idempotencyKey: () => 'test-key' }));
let root: Root;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  const host = document.createElement('div'); document.body.append(host); root = createRoot(host);
  vi.mocked(request).mockReset();
});
afterEach(async () => { await act(async () => root.unmount()); });

describe('experiment evidence preservation', () => {
  it('appends new runs and retains prior failures and accepted run IDs', async () => {
    localStorage.setItem('integration-experiments-v2', JSON.stringify([
      { scenario: 'old', seed: 0, budget_ms: 4000, elapsed_ms: 99, error: 'old failure' },
    ]));
    let submitted = 0;
    vi.mocked(request).mockImplementation(async path => path === '/integration/scenarios'
      ? { items: [{ id: 'new', name: 'New scenario', source_kind: 'synthetic' }] }
      : { run_id: `run-${++submitted}`, status: 'checked' });
    await act(async () => root.render(<IntegrationExperiments />));
    const start = [...document.querySelectorAll('button')].find(button => button.textContent === '开始新一轮')!;
    await act(async () => start.click());
    const stored = JSON.parse(localStorage.getItem('integration-experiments-v2')!);
    expect(stored).toHaveLength(11);
    expect(stored[0].error).toBe('old failure');
    expect(stored[1].result.run_id).toBe('run-1');
    expect(stored[10].result.run_id).toBe('run-10');
    expect(new Set(stored.slice(1).map((row: { batch_id: string }) => row.batch_id)).size).toBe(1);
  });
  it('does not automatically resubmit saved pending work after reload', async () => {
    localStorage.setItem('integration-experiments-v2', JSON.stringify([
      { scenario: 'saved', seed: 0, budget_ms: 4000, elapsed_ms: 1, result: { run_id: 'pending-run', status: 'running' } },
    ]));
    vi.mocked(request).mockResolvedValue({ items: [] });
    await act(async () => root.render(<IntegrationExperiments />));
    expect(document.body.textContent).toContain('pending-run');
    expect(document.body.textContent).toContain('回查结果');
    expect(vi.mocked(request).mock.calls.map(call => call[0])).toEqual(['/integration/scenarios']);
  });
});
