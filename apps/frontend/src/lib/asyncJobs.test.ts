import { afterEach, describe, expect, it, vi } from 'vitest';
import { pollStatus, validInteger, wait } from './asyncJobs';

afterEach(() => vi.useRealTimers());

describe('durable job observation', () => {
  it('accepts terminal failure without polling forever or claiming success', async () => {
    const read = vi.fn().mockResolvedValue({ status: 'failed', reason: 'solver failed' });
    const update = vi.fn();
    expect(await pollStatus(read, new AbortController().signal, update)).toEqual({ status: 'failed', reason: 'solver failed' });
    expect(read).toHaveBeenCalledTimes(1);
    expect(update).toHaveBeenCalledWith({ status: 'failed', reason: 'solver failed' });
  });
  it('stops the timer immediately when leaving a page', async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const waiting = wait(1000, controller.signal);
    const rejection = expect(waiting).rejects.toMatchObject({ name: 'AbortError' });
    controller.abort();
    await rejection;
    expect(vi.getTimerCount()).toBe(0);
  });
  it('never applies a response received after cancellation', async () => {
    const controller = new AbortController();
    const update = vi.fn();
    const read = vi.fn(async () => { controller.abort(); return { status: 'checked' }; });
    await expect(pollStatus(read, controller.signal, update)).rejects.toMatchObject({ name: 'AbortError' });
    expect(update).not.toHaveBeenCalled();
  });
  it('retains the last pending state when the waiting budget expires', async () => {
    const update = vi.fn();
    await expect(pollStatus(async () => ({ status: 'running', run_id: 'run-1' }), new AbortController().signal, update, 0))
      .rejects.toThrow('后台任务可能仍在执行');
    expect(update).toHaveBeenCalledWith({ status: 'running', run_id: 'run-1' });
  });
  it('rejects fractional, infinite and unsafe numeric inputs', () => {
    for (const value of [NaN, Infinity, 1.5, Number.MAX_SAFE_INTEGER + 1, -1]) expect(validInteger(value, 0)).toBe(false);
    expect(validInteger(100, 100, 12000)).toBe(true);
    expect(validInteger(12001, 100, 12000)).toBe(false);
  });
});
