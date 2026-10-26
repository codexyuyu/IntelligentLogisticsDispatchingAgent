// Owner CODEX_FRONTEND. API JSON fields retain their original snake_case spelling.
import createClient from 'openapi-fetch';
import type { paths } from './generated';
import { getToken } from '../auth';

export const api = createClient<paths>({ baseUrl: '' });
api.use({
  onRequest({ request }) {
    // Historical view models are retained for the first UI's visualizations.
    // They are not the current wire contract. Native features use ../api.ts.
    if (new URL(request.url, window.location.origin).pathname !== '/api/v1/health') {
      throw new Error('该演练入口尚未接入当前后端，请使用「运输计划」或「联合调度」。');
    }
    const token = getToken();
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  },
});
