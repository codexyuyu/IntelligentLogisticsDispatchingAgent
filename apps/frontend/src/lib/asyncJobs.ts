import { useEffect, useRef, useState } from 'react';

export const isPending = (status: string) => ['queued', 'running', 'pending'].includes(status);
export const validInteger = (value: number, min: number, max = Number.MAX_SAFE_INTEGER) =>
  Number.isSafeInteger(value) && value >= min && value <= max;

export function readStored(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}

export function saveStored(key: string, value: string): boolean {
  try { localStorage.setItem(key, value); return true; } catch { return false; }
}

export function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    signal.throwIfAborted();
    const abort = () => { clearTimeout(timer); reject(signal.reason); };
    const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve(); }, ms);
    signal.addEventListener('abort', abort, { once: true });
  });
}

/** Cancellation stops observation only; accepted server jobs remain recoverable. */
export async function pollStatus<T extends { status: string }>(
  read: () => Promise<T>, signal: AbortSignal, update: (value: T) => void,
  timeoutMs = 120_000,
): Promise<T> {
  const started = performance.now();
  while (true) {
    signal.throwIfAborted();
    const value = await read();
    signal.throwIfAborted();
    update(value);
    if (!isPending(value.status)) return value;
    if (performance.now() - started >= timeoutMs) {
      throw new Error('等待超过 120 秒，后台任务可能仍在执行；已保留任务编号，可刷新状态。');
    }
    await wait(1000, signal);
  }
}

/** Ref lock closes the interval before React renders a disabled submit button. */
export function useTaskRunner() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const mounted = useRef(false);
  const current = useRef<AbortController | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; current.current?.abort(); current.current = null; };
  }, []);
  async function run(task: (signal: AbortSignal) => Promise<void>) {
    if (current.current || !mounted.current) return;
    const controller = new AbortController();
    current.current = controller;
    setBusy(true); setError('');
    try { await task(controller.signal); }
    catch (cause) {
      if (!controller.signal.aborted && mounted.current) setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      if (current.current === controller) {
        current.current = null;
        if (mounted.current) setBusy(false);
      }
    }
  }
  return { busy, error, setError, run };
}
