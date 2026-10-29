import { useEffect, useState } from 'react';
import { request } from '../../api';
import { readStored, saveStored, useTaskRunner } from '../../lib/asyncJobs';
import type { CheckedRun } from './model';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function useCheckedIntegrationRun() {
  const [runId, setRunId] = useState(() => readStored('integration_last_run') ?? '');
  const [run, setRun] = useState<CheckedRun | null>(null);
  const { busy, error, run: action } = useTaskRunner();

  async function fetchRun(id: string, signal: AbortSignal) {
    const normalized = id.trim();
    if (!UUID_PATTERN.test(normalized)) throw new Error('请输入合法的联合调度运行 UUID。');
    setRun(null);
    const value = await request<CheckedRun>(`/integration/runs/${encodeURIComponent(normalized)}`, { signal });
    signal.throwIfAborted();
    if (value.status !== 'checked' || value.joint_validation?.valid !== true || !value.warehouse_problem || !value.warehouse_solution) {
      throw new Error(`运行尚未通过独立联合校验（当前状态：${value.status}）；不展示计划或回放。`);
    }
    setRun(value);
    saveStored('integration_last_run', normalized);
  }

  useEffect(() => {
    const remembered = readStored('integration_last_run');
    if (remembered) void action(signal => fetchRun(remembered, signal));
  }, []);

  return {
    runId, setRunId, run, busy, error,
    refresh: () => action(signal => fetchRun(runId, signal)),
  };
}

export function RunSelector({ runId, setRunId, refresh, busy, error, run }: {
  runId: string; setRunId: (value: string) => void; refresh: () => Promise<void>;
  busy: boolean; error: string; run: CheckedRun | null;
}) {
  return <section className="panel s5-run-selector">
    <form onSubmit={event => { event.preventDefault(); void refresh(); }}>
      <label htmlFor="s5-run-id">已校验的联合调度运行编号</label>
      <input id="s5-run-id" aria-label="联合调度运行编号" value={runId}
        onChange={event => setRunId(event.target.value)} placeholder="从联合调度页面取得 run_id" />
      <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !runId.trim()}>
        {busy ? '读取中…' : '读取运行结果'}
      </button>
    </form>
    {run ? <p role="status" className="s5-good">已连接经过独立联合校验的运行：{run.run_id}</p>
      : <p className="s5-muted">请先在「联合调度」完成一次计算；本页可恢复最近运行编号，也可手动粘贴。</p>}
    {error && <p className="callout callout-error" role="alert">{error}</p>}
  </section>;
}
