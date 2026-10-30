import { useEffect, useState } from 'react';
import { readStored, saveStored } from '../../lib/asyncJobs';
import { request } from '../../api';
import type { Simulation } from './api';
import { loadSimulation, startSimulation, runKey } from './api';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export function useStageRun() {
  const [runId, setRunId] = useState(() => readStored(runKey) ?? '');
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function reload(id = runId, allowCreate = false) {
    const normalized = id.trim();
    if (!UUID.test(normalized)) { setError('请从联合调度读取有效运行 UUID。'); return; }
    setBusy(true); setError('');
    try {
      const run = await request<{ status: string; joint_validation?: { valid: boolean } }>(`/integration/runs/${encodeURIComponent(normalized)}`);
      if (run.status !== 'checked' || run.joint_validation?.valid !== true) throw new Error('运行未通过联合校验，不能启动模拟。');
      const value = allowCreate ? await startSimulation(normalized) : await loadSimulation(normalized);
      if (!value.tracks || !Array.isArray(value.events) || !value.reconciliation?.passed) throw new Error('缺少后端轨迹或联合对账证据，拒绝显示模拟。');
      setSimulation(value); saveStored(runKey, normalized); setRunId(normalized);
    } catch (cause) { setSimulation(null);
      if (!(String(cause).includes('HTTP 404') && !allowCreate)) setError(String(cause));
    }
    finally { setBusy(false); }
  }
  useEffect(() => {
    const onRun = (event: Event) => {
      const id = (event as CustomEvent<string>).detail;
      if (UUID.test(id)) { setRunId(id); setSimulation(null); }
    };
    window.addEventListener('stageb:run', onRun);
    const known = readStored(runKey);
    if (known && UUID.test(known)) void reload(known, false);
    return () => window.removeEventListener('stageb:run', onRun);
  }, []);
  return { runId, setRunId, simulation, setSimulation, busy, error, reload };
}

export function RunBar({ state, allowCreate = false }: {
  state: ReturnType<typeof useStageRun>; allowCreate?: boolean;
}) {
  return <section className="panel stageb-run-bar">
    <label>联合运行编号 <input aria-label="联合运行编号" value={state.runId} onChange={event => state.setRunId(event.target.value)} placeholder="先到联合调度运行 checked 方案" /></label>
    <button className="btn btn-ghost btn-sm" disabled={state.busy} onClick={() => void state.reload()}>读取模拟</button>
    {allowCreate && <button className="btn btn-primary btn-sm" disabled={state.busy} onClick={() => void state.reload(state.runId, true)}>启动本次模拟</button>}
    <button className="btn btn-ghost btn-sm" onClick={() => { window.dispatchEvent(new CustomEvent('twin:navigate', { detail: 'plans' })); }}>前往联合调度</button>
    {state.busy && <span role="status">读取中…</span>}
    {state.error && <p role="alert" className="callout callout-error">{state.error}</p>}
    {state.simulation && <p role="status">数据库模拟已载入 · {state.simulation.tracks.length} 辆车辆 · v{state.simulation.active_version} · 仅用于模拟，不写实际库存</p>}
  </section>;
}
