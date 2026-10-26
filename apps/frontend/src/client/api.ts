// Owner CODEX_FRONTEND. API JSON fields retain their original snake_case spelling.
import createClient from 'openapi-fetch';
import type { paths } from './generated';
export const api = createClient<paths>({ baseUrl: '' });
