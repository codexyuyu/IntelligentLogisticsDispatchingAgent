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
      const previous = readStored(runKey);
      setSimulation(value); saveStored(runKey, normalized); setRunId(normalized);
      if (allowCreate || previous !== normalized) window.dispatchEvent(new Event('stageb:changed'));
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
    <div className="stageb-run-summary">
      <div><strong>{state.runId ? '已关联当前联合运行' : '尚未关联调度运行'}</strong>
        <small>{state.runId ? `${state.runId.slice(0, 8)}… · 自动读取最近一次联合调度` : '请先前往联合调度，计算并校验方案。'}</small></div>
      <div className="stageb-actions">
        <button className="btn btn-ghost btn-sm" disabled={state.busy || !state.runId} onClick={() => void state.reload()}>刷新模拟状态</button>
        {allowCreate && !state.simulation && <button className="btn btn-primary btn-sm" disabled={state.busy || !state.runId} onClick={() => {
          if (window.confirm('确认启动本次数据库模拟？仅写入当前授权的模拟数据库，不修改实际派车及库存。')) void state.reload(state.runId, true);
        }}>启动本次模拟</button>}
        {!state.runId && <button className="btn btn-primary btn-sm" onClick={() => window.dispatchEvent(new CustomEvent('twin:navigate', { detail: 'plans' }))}>先去联合调度</button>}
      </div>
    </div>
    <details className="stageb-run-manual"><summary>高级操作：手动切换运行编号</summary>
      <label>联合运行 UUID <input aria-label="联合运行编号" value={state.runId} onChange={event => state.setRunId(event.target.value)} placeholder="只在需要切换历史运行时输入" /></label>
      <button className="btn btn-ghost btn-sm" disabled={state.busy} onClick={() => void state.reload()}>读取指定运行</button>
    </details>
    {state.busy && <span role="status">读取中…</span>}
    {state.error && <p role="alert" className="callout callout-error">{state.error}</p>}
    {state.simulation && <p role="status">数据库模拟已载入 · {state.simulation.tracks.length} 辆车辆 · v{state.simulation.active_version} · 仅用于模拟，不写实际库存</p>}
  </section>;
}
