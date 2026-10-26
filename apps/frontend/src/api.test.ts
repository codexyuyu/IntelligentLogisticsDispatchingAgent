import { describe, expect, it, vi } from 'vitest';
import { request } from './api';
import { verifyToken } from './auth';
import { pgRequest } from './features/postgres/api';

describe('single backend frontend boundary', () => {
  it('authenticates against current master data and does not persist invalid tokens', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 401 }));
    vi.stubGlobal('fetch', fetchMock);
    await expect(verifyToken('invalid')).rejects.toThrow('API Key 无效');
    expect(localStorage.getItem('dsh_token')).toBeNull();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/orders?limit=1');
  });
  it('sends the saved credential to the current backend and surfaces errors', async () => {
    localStorage.setItem('dsh_token', 'test-token');
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      code: 'provider_unavailable', message: 'not configured',
    }), { status: 503 }));
    vi.stubGlobal('fetch', fetchMock);
    await expect(request('/agents/chat', { method: 'POST', body: '{}' }))
      .rejects.toThrow('provider_unavailable: not configured');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/agents/chat');
    expect(fetchMock.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer test-token');
  });
  it('never sends old local-pg requests to a second backend', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await expect(pgRequest('/r30c/status')).rejects.toThrow('旧演练服务已退出部署');
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
