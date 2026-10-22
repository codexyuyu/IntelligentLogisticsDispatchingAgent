// Owner: CODEX_FRONTEND. Presentation-only formatting helpers; no business values invented here.
export const NA = '后端未暴露';

export function fmtClock(s: number | null | undefined): string {
  if (s == null || Number.isNaN(s)) return '—';
  const total = Math.max(0, Math.round(s));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const sec = total % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

export function fmtKM(meters: number | null | undefined): string {
  if (meters == null || Number.isNaN(meters)) return '—';
  return `${(meters / 1000).toFixed(1)} km`;
}

export function fmtDur(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return '—';
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)} h ${m % 60} min`;
}

export function fmtMs(ms: number | null | undefined): string {
  if (ms == null || Number.isNaN(ms)) return '—';
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`;
}

export function pct(part: number, total: number): string {
  if (!total) return '—';
  return `${Math.round((part / total) * 100)}%`;
}
