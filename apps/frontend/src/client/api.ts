// Owner CODEX_FRONTEND. API JSON fields retain their original snake_case spelling.
import createClient from 'openapi-fetch';
import type { paths } from './generated';
import { getToken } from '../auth';

export const api = createClient<paths>({ baseUrl: '' });
api.use({
  async onRequest({ request }) {
    const url = new URL(request.url, window.location.origin);
    if (url.pathname !== '/api/v1/health') url.pathname = `/partner${url.pathname}`;
    request = new Request(url, {
      method: request.method, headers: request.headers, signal: request.signal,
      credentials: request.credentials,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.text(),
    });
    const token = getToken();
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  },
});
