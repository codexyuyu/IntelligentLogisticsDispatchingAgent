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
  const response = await fetch(`${BASE}${path}`, { ...init, headers });
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const problem = body as ErrorEnvelope | null;
    throw new Error(problem ? `${problem.code}: ${problem.message}` : `HTTP ${response.status}`);
  }
  return body as T;
}

export function idempotencyKey(): string {
  return crypto.randomUUID();
}
