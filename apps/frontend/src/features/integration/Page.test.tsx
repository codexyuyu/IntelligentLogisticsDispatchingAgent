import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import IntegrationPage from './Page';
import { request } from '../../api';

vi.mock('../../api', () => ({ request: vi.fn(), idempotencyKey: () => 'test-key' }));
let root: Root;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  const host = document.createElement('div'); document.body.append(host); root = createRoot(host);
  vi.mocked(request).mockReset();
});
afterEach(async () => { await act(async () => root.unmount()); });

describe('integrated run recovery', () => {
  it('restores a saved result even when the scenario list fails', async () => {
    localStorage.setItem('integration_last_run', 'saved-run');
    vi.mocked(request).mockImplementation(async path => {
      if (path === '/integration/scenarios') throw new Error('scenario list unavailable');
      return { run_id: 'saved-run', status: 'checked' };
    });
    await act(async () => root.render(<IntegrationPage />));
    expect(document.body.textContent).toContain('记录编号：saved-run');
    expect(document.querySelector('[role="alert"]')?.textContent).toContain('scenario list unavailable');
    expect(vi.mocked(request).mock.calls.every(call => !call[1]?.method)).toBe(true);
  });
  it('blocks a duplicate submit in the same event turn and saves the accepted run', async () => {
    let finish: (value: unknown) => void = () => {};
    vi.mocked(request).mockImplementation(async path => {
      if (path === '/integration/scenarios') return { items: [{ id: 'scenario', name: 'Scenario', source_kind: 'synthetic' }] };
      return new Promise(resolve => { finish = resolve; });
    });
    await act(async () => root.render(<IntegrationPage />));
    const start = [...document.querySelectorAll('button')].find(button => button.textContent === '计算并协商')!;
    await act(async () => { start.click(); start.click(); });
    expect(vi.mocked(request).mock.calls.filter(call => call[1]?.method === 'POST')).toHaveLength(1);
    await act(async () => finish({ run_id: 'new-run', status: 'checked' }));
    expect(localStorage.getItem('integration_last_run')).toBe('new-run');
    expect(document.body.textContent).toContain('记录编号：new-run');
  });
});
