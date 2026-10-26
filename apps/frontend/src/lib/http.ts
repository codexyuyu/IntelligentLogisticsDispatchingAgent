
import { api } from '../client/api';

export function idempotency(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export async function getErrorMessage(error: unknown) {
  if (!error) return '未知错误';
  if (typeof error === 'string') return error;
  if (error instanceof Error) return error.message;

  try {
    return JSON.stringify(error);
  } catch {
    return '请求失败';
  }
}

export async function getJson<T = unknown>(url: string, signal?: AbortSignal): Promise<T> {
  const { getToken } = await import('../auth');
  const token = getToken();
  const response = await fetch(url, { signal, headers: token ? { Authorization: `Bearer ${token}` } : undefined });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function postPartner<T>(
  path: string,
  body: unknown,
  key: string = idempotency('ui'),
): Promise<T> {
  const { getToken } = await import('../auth');
  const token = getToken();
  const response = await fetch(`/partner${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'Idempotency-Key': key,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  const parsed = text ? JSON.parse(text) : null;
  if (!response.ok) throw new Error(parsed?.message ?? `请求失败 HTTP ${response.status}`);
  return parsed as T;
}

export async function postApi<T>(
  path: string,
  body: unknown,
  key: string = idempotency('ui'),
): Promise<T> {
  const { data, error, response } = await api.POST(path as never, {
    params: { header: { 'Idempotency-Key': key } },
    body: body as never,
  } as never);

  if (!data) {
    const status = response?.status ?? 0;
    throw new Error(error ? JSON.stringify(error) : `请求失败 HTTP ${status}`);
  }
  return data as T;
}

export async function pollJob(
  jobId: string,
  onProgress?: (job: any) => void,
  maxSeconds = 90,
) {
  for (let i = 0; i < maxSeconds; i += 1) {
    // The backend currently executes Planning Job synchronously: most jobs are
    // already finished when POST returns. Poll once immediately instead of
    // wasting one second for every experiment. Delay only on later polls.
    if (i > 0) await new Promise((resolve) => setTimeout(resolve, 1000));
    const { data, error } = await api.GET('/api/v1/jobs/{job_id}', {
      params: { path: { job_id: jobId } },
    });
    if (!data) throw new Error(error ? JSON.stringify(error) : '读取任务状态失败');
    onProgress?.(data);
    if (['succeeded', 'failed', 'cancelled'].includes(data.status)) return data;
  }
  throw new Error(`任务超过 ${maxSeconds}s 未完成`);
}
