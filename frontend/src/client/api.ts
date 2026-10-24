// Owner CODEX_FRONTEND. API JSON fields retain their original snake_case spelling.
import createClient from 'openapi-fetch';
import type { paths } from './generated';
import { getToken } from '../auth';

export const api = createClient<paths>({ baseUrl: '' });
api.use({
  onRequest({ request }) {
    const token = getToken();
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  },
});
