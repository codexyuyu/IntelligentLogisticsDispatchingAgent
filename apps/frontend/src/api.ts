const BASE = "/api/v1";

export type JobRef = {
  schema_version: string;
  job_id: string;
  status: string;
  status_url: string;
  result_url: string;
  trace_id: string;
};

export type Page<T> = {
  schema_version: string;
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
};

export type JobResult = {
  kind: "transport" | "warehouse" | "simulation";
  value: Record<string, unknown>;
};

export type ErrorEnvelope = {
  schema_version: string;
  code: string;
  message: string;
  trace_id: string;
  retryable: boolean;
};

export function getToken(): string {
  return window.localStorage.getItem("dsh_token") ?? "";
}

export function setToken(token: string): void {
  window.localStorage.setItem("dsh_token", token);
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const controller = new AbortController();
  const abort = () => controller.abort(init.signal?.reason);
  if (init.signal?.aborted) abort();
  else init.signal?.addEventListener('abort', abort, { once: true });
  let timedOut = false;
  const timeoutMs = path === '/integration/showcase/vehicle-breakdown/ai-collaborate' ? 145_000 :
    (path === '/agents/dispatch' || path === '/agents/dispatch-tasks') ? 65_000 : 30_000;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    const response = await fetch(`${BASE}${path}`, { ...init, headers, signal: controller.signal });
    const text = await response.text();
    let body: unknown = null;
    try { body = text ? JSON.parse(text) : null; }
    catch {
      throw new Error(response.ok ? '服务返回了无效的 JSON 数据，请重试。' : `HTTP ${response.status}：服务暂时无法响应，请重试。`);
    }
    if (!response.ok) {
      const problem = body as Partial<ErrorEnvelope> | null;
      throw new Error(typeof problem?.message === 'string'
        ? `${problem.code ?? `HTTP ${response.status}`}: ${problem.message}`
        : `HTTP ${response.status}`);
    }
    return body as T;
  } catch (error) {
    if (timedOut) throw new Error(`请求超过 ${timeoutMs / 1000} 秒。请先查看运行记录，不要立即重复提交。`);
    throw error;
  } finally {
    clearTimeout(timer);
    init.signal?.removeEventListener('abort', abort);
  }
}

export function idempotencyKey(): string {
  return crypto.randomUUID();
}
