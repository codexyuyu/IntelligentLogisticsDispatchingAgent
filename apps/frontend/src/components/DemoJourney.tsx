import { useCallback, useEffect, useRef, useState } from 'react';
import { request } from '../api';
import { readStored, saveStored } from '../lib/asyncJobs';
import { loadSimulation, runKey, selectIncident, short, startSimulation } from '../features/stageB/api';
import type { Simulation } from '../features/stageB/api';

type RunInfo = { status: string; joint_validation?: { valid: boolean } };
type Journey = { runId: string; run: RunInfo | null; simulation: Simulation | null; loading: boolean; error: string };
export type DemoStep = 'plan' | 'start' | 'incident' | 'replay';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function nextDemoStep(run: RunInfo | null, simulation: Simulation | null): DemoStep {
  if (!run || run.status !== 'checked' || run.joint_validation?.valid !== true) return 'plan';
  if (!simulation) return 'start';
  const incident = selectIncident(simulation);
  return incident && incident.status !== 'pending' ? 'replay' : 'incident';
}

function navigate(page: string) {
  window.dispatchEvent(new CustomEvent('twin:navigate', { detail: page }));
}

const steps: { key: DemoStep; label: string; desc: string; page: string }[] = [
  { key: 'plan', label: '生成联合方案', desc: '导入场景、计算并校验', page: 'plans' },
  { key: 'start', label: '启动数据库模拟', desc: '生成可回放的车辆轨迹', page: 'plans' },
  { key: 'incident', label: '延误与人工审批', desc: '分析候选、批准或拒绝', page: 'events' },
  { key: 'replay', label: '对比仿真回放', desc: '查看 v0 / candidate / active', page: 'simulations' },
];

export default function DemoJourney() {
  const [data, setData] = useState<Journey>({ runId: readStored(runKey) ?? '', run: null, simulation: null, loading: false, error: '' });
  const [working, setWorking] = useState(false);
  const serial = useRef(0);
  const busyRef = useRef(false);

  const refresh = useCallback(async (explicitId?: string) => {
    const id = explicitId ?? readStored(runKey) ?? '';
    const revision = ++serial.current;
    if (!UUID.test(id)) {
      setData({ runId: '', run: null, simulation: null, loading: false, error: '' });
      return;
    }
    setData(old => ({ ...old, runId: id, loading: true, error: '', ...((old.runId !== id) ? { run: null, simulation: null } : {}) }));
    try {
      const run = await request<RunInfo>(`/integration/runs/${encodeURIComponent(id)}`);
      let simulation: Simulation | null = null;
      let warning = '';
      if (run.status === 'checked' && run.joint_validation?.valid === true) {
        try { simulation = await loadSimulation(id); }
        catch (e) {
          if (!/404|not_found/i.test(String(e))) warning = '读取模拟失败，请检查后端后重试。';
        }
      }
      if (revision === serial.current) setData({ runId: id, run, simulation, loading: false, error: warning });
    } catch {
      if (revision === serial.current) setData({ runId: id, run: null, simulation: null, loading: false,
        error: '当前运行读取失败。可前往联合调度重新读取，或重试。' });
    }
  }, []);

  useEffect(() => {
    void refresh();
    const onRun = (event: Event) => {
      const id = (event as CustomEvent<string>).detail;
      if (UUID.test(id)) { saveStored(runKey, id); void refresh(id); }
    };
    const onRefresh = () => { void refresh(); };
    window.addEventListener('stageb:run', onRun);
    window.addEventListener('stageb:changed', onRefresh);
    window.addEventListener('stageb:cleared', onRefresh);
    window.addEventListener('focus', onRefresh);
    return () => { serial.current++; window.removeEventListener('stageb:run', onRun);
      window.removeEventListener('stageb:changed', onRefresh); window.removeEventListener('stageb:cleared', onRefresh); window.removeEventListener('focus', onRefresh); };
  }, [refresh]);

  useEffect(() => {
    if (!data.runId || !['queued', 'running', 'pending'].includes(data.run?.status ?? '')) return;
    const timer = window.setInterval(() => { void refresh(data.runId); }, 3000);
    return () => window.clearInterval(timer);
  }, [data.runId, data.run?.status, refresh]);

  const step = nextDemoStep(data.run, data.simulation);
  const incident = selectIncident(data.simulation);
  const checked = data.run?.status === 'checked' && data.run.joint_validation?.valid === true;
  const index = steps.findIndex(item => item.key === step);

  async function createSimulation() {
    if (!checked || !data.runId || busyRef.current) return;
    if (!window.confirm('为本次 checked run 启动数据库模拟？会在当前连接的数据库中保存模拟记录，不会修改实际库存或派车。请确认使用的是授权的隔离环境。')) return;
    busyRef.current = true; setWorking(true);
    try {
      // Recheck existence immediately before POST: repeated clicks or another tab must not create unexpectedly.
      let alreadyExists = false;
      try { await loadSimulation(data.runId); alreadyExists = true; }
      catch (e) { if (!/404|not_found/i.test(String(e))) throw e; }
      if (!alreadyExists) await startSimulation(data.runId);
      window.dispatchEvent(new Event('stageb:changed'));
      await refresh(data.runId);
      navigate('events');
    } catch (e) {
      setData(old => ({ ...old, error: `启动模拟失败：${String(e)}` }));
    } finally { busyRef.current = false; setWorking(false); }
  }

  function primaryAction() {
    if (step === 'start') void createSimulation();
    else if (data.run && ['queued', 'running', 'pending'].includes(data.run.status)) void refresh(data.runId);
    else navigate(steps[index].page);
  }

  return <section className="demo-journey" aria-label="调度业务流程">
    <div className="demo-journey-heading">
      <div><strong>调度业务流程</strong><span>联合求解、模拟运行、异常处置与方案回放</span></div>
      <div className="demo-journey-run">{data.runId ? `当前运行 ${short(data.runId)}` : '尚未选择联合运行'}
        <button type="button" className="btn btn-ghost btn-sm" disabled={data.loading || working} onClick={() => void refresh()}>同步状态</button></div>
    </div>
    <ol className="demo-journey-steps">
      {steps.map((item, i) => <li key={item.key} className={i === index ? 'current' : i < index ? 'finished' : ''}>
        <button type="button" onClick={() => navigate(item.page)} aria-current={i === index ? 'step' : undefined}
          title={`查看：${item.desc}`}><span className="demo-step-number">{i < index ? '✓' : i + 1}</span><span><strong>{item.label}</strong><small>{item.desc}</small></span></button>
      </li>)}
    </ol>
    <div className="demo-journey-bottom">
      <div className="demo-journey-status" role="status">
        {data.loading ? '正在从后端核对当前运行状态…' : !data.runId ? '尚无联合运行，请选择场景并计算方案。'
          : !checked ? `当前运行：${data.run?.status ?? '未恢复'}；需要 checked 且通过联合校验。`
          : step === 'start' ? '方案已校验；下一步启动数据库模拟（需人工确认）。'
          : step === 'incident' && incident?.status === 'pending' ? '候选方案待人工批准或拒绝；请继续异常处置。'
          : step === 'incident' ? `模拟已就绪 · ${data.simulation?.tracks.length ?? 0} 辆车辆；下一步登记延误并分析。`
          : `审批结果：${incident?.status === 'approved' ? '已批准 v1' : '已拒绝，保留 v0'}；请查看回放对比。`}
      </div>
      <div className="demo-journey-actions">
        {data.simulation && <button className="btn btn-ghost btn-sm" onClick={() => navigate('vehicles')}>查看车辆轨迹</button>}
        <button className="btn btn-primary btn-sm" disabled={working || data.loading || (Boolean(data.error) && step === 'start')}
          onClick={primaryAction}>{working ? '正在启动…' : ['queued','running','pending'].includes(data.run?.status ?? '') ? '刷新求解进度' : step === 'start' ? '启动本次模拟' : step === 'plan' ? '前往联合调度' : step === 'incident' ? '继续异常处置' : '查看 v0 / v1 回放'}</button>
      </div>
    </div>
    {data.error && <p role="alert" className="demo-journey-error">{data.error}</p>}
  </section>;
}
