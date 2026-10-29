import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { expect, it, vi } from 'vitest';
import LiveOverview from './LiveOverview';
it('counts all pages and displays real totals', async () => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response(JSON.stringify({
    items: url.includes('cursor=next') ? [{ id: 'b' }] : [{ id: 'a' }],
    has_more: url.includes('/orders?') && !url.includes('cursor=next'),
    next_cursor: 'next',
  }))));
  const host = document.createElement('div'); document.body.append(host);
  const root = createRoot(host);
  await act(async () => { root.render(<LiveOverview />); });
  expect(host.textContent).toContain('订单总量2');
  expect(host.textContent).toContain('运输车辆1');
  await act(async () => root.unmount());
});
it('does not show failed reads as zero records', async () => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
  const host = document.createElement('div'); document.body.append(host);
  const root = createRoot(host);
  await act(async () => { root.render(<LiveOverview />); });
  expect(host.querySelector('[role="alert"]')?.textContent).toContain('offline');
  expect(host.textContent).toContain('订单总量—');
  await act(async () => root.unmount());
});

