import { useCallback, useEffect, useRef, useState } from 'react';
import { request, type Page } from '../../api';
import { readStored } from '../../lib/asyncJobs';
import { loadSimulation, runKey, selectIncident, short, startSimulation, type Simulation } from '../stageB/api';

type Metric = { code: string; value: number | null; unit: string; reason?: string | null };
type Run = {
  run_id: string; status: string; joint_validation?: { valid: boolean; violations?: unknown[] };
  observations?: { metrics?: { values?: Metric[] } };
  candidate?: { task_assignments?: { task_kind: string }[] };
  warehouse_solution?: { status: string }; transport_solution?: { status: string };
};
type Counts = { orders: number; vehicles: number; warehouses: number };
type State = { counts: Counts | null; run: Run | null; sim: Simulation | null; loading: boolean; error: string; runError: string };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const stages = [
  { title: '联合方案', detail: '仓储与运输协同求解', page: 'plans' },
  { title: '模拟运行', detail: '载入调度轨迹', page: 'simulations' },
  { title: '异常分析', detail: '生成恢复候选方案', page: 'events' },
  { title: '人工决策', detail: '批准或拒绝调整', page: 'events' },
  { title: '方案回放', detail: '比较基线与生效方案', page: 'simulations' },
] as const;
function navigate(page: string) { window.dispatchEvent(new CustomEvent('twin:navigate', { detail: page })); }
function isMissing(error: unknown) { return /404|not_found/i.test(String(error)); }
function metric(run: Run | null, code: string) {
  return run?.observations?.metrics?.values?.find(item => item.code === code);
}
function displayMetric(run: Run | null, code: string) {
  const item = metric(run, code);
  if (typeof item?.value !== 'number' || !Number.isFinite(item.value)) return '—';
  if (code === 'total_distance_m') return `${(item.value / 1000).toLocaleString('zh-CN', { maximumFractionDigits: 2 })} km`;
  if (code === 'total_cost_cents') return `¥${(item.value / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (item.unit === 'ratio') return `${(item.value * 100).toFixed(1)}%`;
  return item.value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}
function currentStage(run: Run | null, sim: Simulation | null) {
  if (!run || run.status !== 'checked' || run.joint_validation?.valid !== true) return 0;
  if (!sim) return 1;
  const incident = selectIncident(sim);
  if (!incident) return 2;
  if (incident.status === 'pending') return 3;
  return 4;
}
function nextActionLabel(index: number, run: Run | null) {
  if (index === 0) return ['queued', 'running', 'pending'].includes(run?.status ?? '') ? '查看求解进度' : '进入联合调度';
  if (index === 1) return '启动模拟运行';
  if (index === 2) return '登记运输异常';
  if (index === 3) return '处理候选方案';
  return '查看方案回放';
}

/** The home workbench reads persisted business state; it does not create example results or mutate DB on mount. */
export default function DispatchCockpit() {
  const [state, setState] = useState<State>({ counts: null, run: null, sim: null, loading: true, error: '', runError: '' });
  const [revision, setRevision] = useState(0);
  const [working, setWorking] = useState(false);
  const busy = useRef(false);
  const refresh = useCallback(() => setRevision(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    const runId = readStored(runKey) ?? '';
    setState(previous => ({ ...previous, loading: true, error: '', runError: '', ...(!UUID.test(runId) ? { run: null, sim: null } : {}) }));
    async function count(kind: string): Promise<number> {
      let cursor: string | null = null;
      const seen = new Set<string>();
      const ids = new Set<string>();
      do {
        const params = new URLSearchParams({ limit: '100' });
        if (cursor) params.set('cursor', cursor);
        const result = await request<Page<{ id: string }>>(`/${kind}?${params}`, { signal: controller.signal });
        result.items.forEach(item => ids.add(item.id));
        if (!result.has_more) return ids.size;
        if (!result.next_cursor || seen.has(result.next_cursor)) throw new Error('业务数据分页异常');
        seen.add(result.next_cursor); cursor = result.next_cursor;
      } while (!controller.signal.aborted);
      throw new Error('读取已取消');
    }
    async function loadCounts() {
      try {
        const [orders, vehicles, warehouses] = await Promise.all(['orders', 'vehicles', 'warehouses'].map(count));
        if (!controller.signal.aborted) setState(prev => ({ ...prev, counts: { orders, vehicles, warehouses } }));
      } catch (cause) { if (!controller.signal.aborted) setState(prev => ({ ...prev, counts: null, error: `业务数据读取失败：${String(cause)}` })); }
    }
    async function loadRun() {
      if (!UUID.test(runId)) return;
      try {
        const run = await request<Run>(`/integration/runs/${encodeURIComponent(runId)}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        let sim: Simulation | null = null;
        let runError = '';
        if (run.status === 'checked' && run.joint_validation?.valid === true) {
          try { sim = await loadSimulation(runId, controller.signal); }
          catch (cause) { if (!isMissing(cause) && !controller.signal.aborted) runError = `模拟记录读取失败：${String(cause)}`; }
        }
        if (!controller.signal.aborted) setState(prev => ({ ...prev, run, sim, runError }));
      } catch (cause) {
        if (!controller.signal.aborted) setState(prev => ({ ...prev, run: null, sim: null, runError: `运行记录读取失败：${String(cause)}` }));
      }
    }
    void Promise.all([loadCounts(), loadRun()]).finally(() => {
      if (!controller.signal.aborted) setState(prev => ({ ...prev, loading: false }));
    });
    return () => controller.abort();
  }, [revision]);

  useEffect(() => {
    const onChanged = () => refresh();
    window.addEventListener('stageb:run', onChanged);
    window.addEventListener('stageb:changed', onChanged);
    window.addEventListener('stageb:cleared', onChanged);
    window.addEventListener('focus', onChanged);
    return () => {
      window.removeEventListener('stageb:run', onChanged);
      window.removeEventListener('stageb:changed', onChanged);
      window.removeEventListener('stageb:cleared', onChanged);
      window.removeEventListener('focus', onChanged);
    };
  }, [refresh]);

  useEffect(() => {
    if (!['queued', 'running', 'pending'].includes(state.run?.status ?? '')) return;
    const timer = window.setInterval(refresh, 4000);
    return () => window.clearInterval(timer);
  }, [state.run?.status, refresh]);

  const { run, sim, counts, loading } = state;
  const incident = selectIncident(sim);
  const index = currentStage(run, sim);
  const valid = run?.status === 'checked' && run.joint_validation?.valid === true;
  const plansCount = run?.candidate?.task_assignments?.length;
  const stageText = !run ? '尚无关联调度运行' : !valid ? `运行状态：${run.status}${run.status === 'checked' ? ' · 联合校验未通过' : ''}`
    : !sim ? '联合校验已通过 · 尚未建立模拟' : !incident ? '模拟轨迹已保存 · 尚无车辆异常'
    : incident.status === 'pending' ? '候选方案待人工审批' : incident.status === 'approved' ? `审批已通过 · 生效版本 v${sim.active_version}` : `审批已拒绝 · 生效版本 v${sim.active_version}`;
  const stats = [
    { name: '业务订单', value: counts ? String(counts.orders) : '—', detail: '当前数据库记录' },
    { name: '运输车辆', value: counts ? String(counts.vehicles) : '—', detail: '当前数据库记录' },
    { name: '仓库节点', value: counts ? String(counts.warehouses) : '—', detail: '当前数据库记录' },
    { name: '联合校验', value: !run ? '—' : run.status === 'checked' ? valid ? '通过' : '未通过' : '未完成', detail: run ? `运行 ${short(run.run_id)}` : '等待联合方案' },
  ];

  async function createSimulation() {
    if (!valid || !run?.run_id || busy.current) return;
    if (!window.confirm('确认在当前连接的数据库中为已校验方案建立模拟记录？不会修改实际库存或派车。')) return;
    busy.current = true; setWorking(true);
    try {
      let exists = false;
      try { await loadSimulation(run.run_id); exists = true; }
      catch (cause) { if (!isMissing(cause)) throw cause; }
      if (!exists) await startSimulation(run.run_id);
      window.dispatchEvent(new Event('stageb:changed'));
      refresh();
      navigate('events');
    } catch (cause) {
      setState(prev => ({ ...prev, runError: `启动模拟失败：${String(cause)}` }));
    } finally { busy.current = false; setWorking(false); }
  }

  function primaryAction() {
    if (index === 1) void createSimulation();
    else navigate(stages[index].page);
  }

  function newDispatch() {
    if (!window.confirm('切换到新的调度任务？当前任务的数据库记录和审批历史将保留，只取消浏览器中对当前运行的关联。')) return;
    try { window.localStorage.removeItem(runKey); }
    catch { setState(prev => ({ ...prev, runError: '浏览器存储不可用，无法清除当前运行关联。' })); return; }
    setState(prev => ({ ...prev, run: null, sim: null, runError: '' }));
    window.dispatchEvent(new Event('stageb:cleared'));
    navigate('plans');
  }

  return <div className="dispatch-cockpit">
    <section className="dc-hero">
      <div className="dc-hero-copy">
        <span className="dc-eyebrow">OPERATIONS / DISPATCH CENTER</span>
        <h2>仓储与运输联合调度</h2>
        <p>从订单与仓储资源配置，到路径求解、异常处置与方案回放，统一管理调度运行。</p>
        <div className="dc-hero-actions">
          <button className="btn btn-primary" onClick={primaryAction} disabled={working || loading || (index === 1 && Boolean(state.runError))}>
            {working ? '正在启动…' : nextActionLabel(index, run)} <span aria-hidden="true">→</span>
          </button>
          <button className="btn btn-ghost" onClick={newDispatch}>新建调度</button>
          <button className="btn btn-ghost btn-sm" onClick={refresh} disabled={loading || working}>同步状态</button>
        </div>
      </div>
      <div className="dc-hero-status">
        <span className="dc-status-caption">当前调度状态</span>
        <strong>{loading ? '正在读取…' : stageText}</strong>
        <span>{run ? `运行 ${short(run.run_id)}` : '等待创建联合调度方案'}</span>
        <span>{sim ? `模拟 ${short(sim.simulation_id)} · v${sim.active_version}` : '尚未建立数据库模拟'}</span>
      </div>
    </section>

    <section className="dc-progress" aria-label="调度任务流程">
      <div className="dc-section-heading"><div><span className="dc-eyebrow">WORKFLOW</span><h3>任务流程</h3></div><span className="dc-subtle">{run ? `当前阶段 ${index + 1} / 5` : '尚未开始'}</span></div>
      <div className="dc-progress-grid">
        {stages.map((stage, i) => <button type="button" key={stage.title} onClick={() => navigate(stage.page)}
          className={`dc-progress-step ${i === index ? 'is-current' : i < index ? 'is-finished' : ''}`}
          aria-current={i === index ? 'step' : undefined}>
          <span className="dc-step-n">{i < index ? '✓' : String(i + 1).padStart(2, '0')}</span>
          <span><strong>{stage.title}</strong><small>{stage.detail}</small></span>
        </button>)}
      </div>
    </section>

    <section className="dc-stat-grid" aria-label="当前业务数据">
      {stats.map(item => <div className="dc-stat" key={item.name}><span>{item.name}</span><strong>{item.value}</strong><small>{item.detail}</small></div>)}
    </section>

    <div className="dc-content-grid">
      <section className="dc-panel dc-results">
        <div className="dc-section-heading"><div><span className="dc-eyebrow">OPTIMIZATION</span><h3>联合调度结果</h3></div><button className="btn btn-ghost btn-sm" onClick={() => navigate('plans')}>查看方案详情 →</button></div>
        <div className="dc-result-metrics">
          {[{ code: 'total_distance_m', label: '运输总距离' }, { code: 'total_cost_cents', label: '预计运输成本' },
            { code: 'on_time_rate', label: '订单准时率' }, { code: 'delivery_rate', label: '需求满足率' }].map(item =>
            <div className="dc-result-cell" key={item.code}><span>{item.label}</span><strong>{displayMetric(run, item.code)}</strong></div>)}
        </div>
        <div className="dc-solution-row">
          <span>仓储求解 <b>{run?.warehouse_solution?.status ?? '—'}</b></span>
          <span>运输求解 <b>{run?.transport_solution?.status ?? '—'}</b></span>
          <span>方案任务 <b>{typeof plansCount === 'number' ? `${plansCount} 项` : '—'}</b></span>
        </div>
        {!run && <p className="dc-empty">联合求解完成后，系统将显示实际成本、时效与约束指标。</p>}
      </section>
      <section className="dc-panel dc-simulation">
        <div className="dc-section-heading"><div><span className="dc-eyebrow">SIMULATION</span><h3>运行与异常</h3></div><button className="btn btn-ghost btn-sm" onClick={() => navigate('simulations')}>仿真回放 →</button></div>
        <div className="dc-activity-row"><span>模拟记录</span><strong>{sim ? `${sim.tracks.length} 辆车辆 · v${sim.active_version}` : '尚未启动'}</strong></div>
        <div className="dc-activity-row"><span>异常处置</span><strong>{!incident ? '暂无记录' : incident.status === 'pending' ? '待审批' : incident.status === 'approved' ? '已批准' : '已拒绝'}</strong></div>
        <div className="dc-activity-row"><span>恢复策略</span><strong>{incident?.strategy === 'simulated_local_reroute' ? '局部路线重规划' : incident?.strategy === 'simulated_local_retimed' ? '局部时序调整' : incident?.strategy === 'simulated_hold_resume' ? '延误顺延' : '—'}</strong></div>
        <div className="dc-activity-row"><span>轨迹变更</span><strong>{incident?.route_changed === true ? '已变更' : incident?.route_changed === false ? '未变更' : '—'}</strong></div>
        <div className="dc-activity-actions">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('events')}>异常处置</button>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('simulations')}>查看轨迹</button>
        </div>
      </section>
    </div>
    <div className="dc-link-row">
      <button onClick={() => navigate('orders')}>订单与库存 <span>↗</span></button>
      <button onClick={() => navigate('warehouseTwin')}>仓库三维视图 <span>↗</span></button>
      <button onClick={() => navigate('vehicles')}>运输计划 <span>↗</span></button>
      <button onClick={() => navigate('agent')}>调度助手 <span>↗</span></button>
      <button onClick={() => navigate('experiments')}>对照实验 <span>↗</span></button>
    </div>
    {(state.error || state.runError) && <p role="alert" className="callout callout-error">{[state.error, state.runError].filter(Boolean).join('；')}</p>}
  </div>;
}
