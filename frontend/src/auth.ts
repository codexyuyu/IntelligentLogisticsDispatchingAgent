const TOKEN_KEY = "dsh_token";

export function getToken(): string {
  return window.localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token.trim());
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export async function verifyToken(token: string): Promise<void> {
  const response = await fetch("/api/v1/orders?limit=1", {
    headers: { Accept: "application/json", Authorization: `Bearer ${token.trim()}` },
  });
  if (!response.ok) {
    throw new Error(response.status === 401 ? "API Key 无效" : `登录失败 HTTP ${response.status}`);
  }
}
