import { useEffect, useMemo, useState } from 'react';
import { request } from '../../api';
import type { TwinRoute } from '../../appTypes';
import DigitalTwinMap2D from '../../components/DigitalTwinMap2D';
import type { DemoMapNode, LatLng } from '../../lib/liuzhouDemoMap';
import './fault-rescue.css';

type DemoStop = { node_id: string; kind: string; arrival_s: number; departure_s: number; order_id?: string | null };
type DemoTrack = { vehicle_id: string; stops: DemoStop[] };
type Metric = { total_orders: number; delivered_orders: number; undelivered_orders: number; late_orders: number;
  late_s: number; distance_m: number; objective_cents: number; undelivered_order_ids: string[] };
type FaultResponse = {
  case_id: string; name: string; mode: string; status: 'solved' | 'invalid' | 'infeasible' | 'model_invalid' | 'no_solution_within_budget';
  incident_kind: string; solver: string; reason?: string | null;
  failure_vehicle_id: string; failure_node_id: string; failure_time_s: number;
  horizon_s: number; baseline: DemoTrack[]; no_rescue: DemoTrack[]; candidate: DemoTrack[];
  candidate_valid: boolean; rescued_order_ids?: string[]; rescue_order_ids: string[];
  recovered_orders?: number; reassigned_order_ids?: string[];
  rescue_assignments?: Record<string, string>; points: Record<string, LatLng>;
  metrics: { baseline: Metric; no_rescue: Metric; candidate?: Metric };
  assumptions: string[]; objective_note?: string;
  solver_diagnostic?: { physical_seed_count: number; ortools_seed_accepted: boolean;
    routing_status_code?: number; attempts: Array<{stage:string;result:string}>; candidate_checks?:string[] };
};

type AiCollaboration = { ai_status: 'model_success' | 'model_unavailable' | 'model_failed' | 'model_invalid_tool_call' |
  'solver_failed' | 'model_explanation_failed'; model?: string | null; reply?: string;
  error_code?: string | null; tool_trace: Array<{tool: string; requested_by: string; executed_by: string; ok: boolean}>;
  rescue?: FaultResponse | null; comparison?: { recovered_orders?: number | null; cost_delta_cents?: number | null;
    distance_delta_m?: number | null; candidate_valid?: boolean } | null };
type DemoSession = {data: FaultResponse; approval:'pending'|'approved'|'rejected'; ai?: AiCollaboration | null};
type DemoMode = 'baseline' | 'no_rescue' | 'candidate';
const STORAGE = 'fault_rescue_showcase_session_v2';
const numberVehicle = (id: string) => id.endsWith('01') ? '冷藏车 01' : id.endsWith('02') ? '冷藏车 02' : id.endsWith('03') ? '冷藏车 03' : id;
const orderName = (id: string) => id.replace('demo-o', '订单 O').replace(/^demo-pickup-demo-o/, '交接 O');
const money = (cents: number) => `¥${(cents / 100).toFixed(2)}`;
const metricCopy = (m: Metric, key: string) => key === 'deliveries' ? `${m.delivered_orders} / ${m.total_orders}` :
  key === 'missed' ? `${m.undelivered_orders} 单` : key === 'late' ? `${m.late_orders} 单` :
  key === 'distance' ? `${(m.distance_m / 1000).toFixed(2)} km` : money(m.objective_cents);
const metricRows = [{key:'deliveries',name:'成功交付'},{key:'missed',name:'无法交付'},
  {key:'late',name:'迟到订单'},{key:'distance',name:'示意里程'},{key:'cost',name:'可计算成本'}];
function makeRoutes(tracks: DemoTrack[]): TwinRoute[] {
  return tracks.map(track => ({
    vehicleId: track.vehicle_id, zone: 'chilled' as const, warehouseId: 'demo-depot',
    distanceM: 0, durationS: track.stops.at(-1)?.arrival_s ?? 0,
    stops: track.stops.map(stop => ({
      nodeId: stop.node_id,
      kind: stop.kind === 'depot_start' ? 'depot_start' : stop.kind === 'depot_end' ? 'depot_end' : 'delivery',
      arrivalS: stop.arrival_s, departureS: stop.departure_s,
      orderIds: stop.kind === 'delivery' && stop.order_id ? [stop.order_id] : [],
    })),
  }));
}
function mapNodes(data: FaultResponse): Record<string,DemoMapNode> {
  return Object.fromEntries(Object.entries(data.points).map(([id, point]) => [id, {
    id, point, isDepot: id === 'demo-depot',
    label: id === 'demo-depot' ? '文昌校区附近 · 虚拟冷链仓库'
      : id === 'demo-o3' ? '订单 O3 · 故障交接点'
      : id.startsWith('demo-fault-position') ? '故障时刻 · 在途位置'
      : id.startsWith('demo-pickup') ? '现场接管冷链货品'
      : orderName(id),
  }]));
}
function recoverSession(): DemoSession | null {
  try {
    const value = sessionStorage.getItem(STORAGE);
    if (!value) return null;
    const parsed: unknown = JSON.parse(value);
    if (!parsed || typeof parsed !== 'object' || !('data' in parsed) || !('approval' in parsed)) return null;
    const result = parsed as DemoSession;
    return result.data?.case_id === 'wenchang-three-truck-breakdown-v1' ? result : null;
  } catch { return null; }
}
export default function FaultRescueDemo({ mode = 'incident' }: { mode?: 'incident' | 'replay' }) {
  const [session, setSession] = useState(recoverSession);
  const [busy, setBusy] = useState(false);
  const [aiResult, setAiResult] = useState<AiCollaboration | null>(() => recoverSession()?.ai ?? null);
  const [error, setError] = useState('');
  const [view, setView] = useState<DemoMode>(() => recoverSession()?.approval === 'approved' ? 'candidate' : 'no_rescue');
  const [compare, setCompare] = useState(false);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(5);
  const [selected, setSelected] = useState<string | null>(null);
  const data = session?.data;
  const canApprove = data?.status === 'solved' && data.candidate_valid && session?.approval === 'pending';
  const nodes = useMemo(() => data ? mapNodes(data) : {}, [data]);
  const nodeIds = useMemo(() => Object.keys(nodes).sort(), [nodes]);
  const routes = useMemo(() => data ? {
    baseline: makeRoutes(data.baseline), no_rescue: makeRoutes(data.no_rescue),
    candidate: makeRoutes(data.candidate),
  } : null, [data]);
  useEffect(() => {
    if (!playing || !data) return;
    const timer = window.setInterval(() => setTime(value => {
      const next = Math.min(data.horizon_s, value + speed / 4);
      if (next >= data.horizon_s) setPlaying(false);
      return next;
    }), 250);
    return () => window.clearInterval(timer);
  }, [playing, data, speed]);
  function installRescue(solved: FaultResponse, ai: AiCollaboration | null) {
    const next: DemoSession = {data: solved, approval: 'pending', ai};
    setSession(next);
    setAiResult(ai);
    sessionStorage.setItem(STORAGE, JSON.stringify(next));
    setPlaying(false); setTime(Math.max(0, solved.failure_time_s - 60));
    setCompare(false); setView('no_rescue');
  }
  async function triggerAi() {
    if (busy) return;
    if (data && !window.confirm('重新执行 AI 协同将清除当前演示审批，确定继续吗？')) return;
    setBusy(true); setError(''); setAiResult(null);
    try {
      const outcome = await request<AiCollaboration>('/integration/showcase/vehicle-breakdown/ai-collaborate', {
        method: 'POST', body: JSON.stringify({ budget_ms: 1800 }),
      });
      setAiResult(outcome);
      if (outcome.rescue) installRescue(outcome.rescue, outcome);
      else setError(outcome.ai_status === 'model_unavailable'
        ? '未配置 DeepSeek，AI 没有参与；可使用下方 OR-Tools 手动求解。'
        : `AI 协同没有完成工具链（${outcome.error_code || outcome.ai_status}）。没有伪造候选结果，可手动求解。`);
    } catch (cause) { setError(`AI 协同请求失败：${String(cause)}`); }
    finally { setBusy(false); }
  }
  async function trigger() {
    if (busy) return;
    if (data && !window.confirm('重新求解将清除本次场景已有的审批状态，确定继续吗？')) return;
    setBusy(true); setError(''); setSession(null); setAiResult(null); sessionStorage.removeItem(STORAGE);
    setPlaying(false); setTime(0); setCompare(false); setView('no_rescue');
    try {
      const solved = await request<FaultResponse>('/integration/showcase/vehicle-breakdown/solve', {
        method: 'POST', body: JSON.stringify({ budget_ms: 1800 }),
      });
      installRescue(solved, null);
    } catch (cause) { setError(`故障求解失败：${String(cause)}`); }
    finally { setBusy(false); }
  }
  function decide(approval:'approved'|'rejected') {
    if (!session || (approval === 'approved' && !canApprove)) return;
    if (!window.confirm(approval === 'approved' ? '确认仅在本浏览器演示中采用 OR-Tools 救援方案？不写入数据库或运营派车。'
      : '确认拒绝候选救援路线并保留故障后不救援方案？')) return;
    const next = {...session,approval};
    setSession(next); sessionStorage.setItem(STORAGE,JSON.stringify(next));
    setPlaying(false); setView(approval === 'approved' ? 'candidate' : 'no_rescue');
    setTime(Math.max(0, session.data.failure_time_s - 30));
  }
  const displayView: DemoMode = data && view === 'candidate' && !(data.candidate_valid && data.status === 'solved') ? 'no_rescue' : view;
  return <section className={`fault-demo panel ${mode === 'replay' ? 'fault-demo-replay' : ''}`} aria-label={mode === 'replay' ? '三车故障救援地图回放' : '三车故障智能接管'}>
    <div className="fault-heading">
      <div><span className="fault-eyebrow">柳州 · 文昌校区 · 三车八单</span>
        <h3>{mode === 'replay' ? '三车故障救援 · 运输地图回放' : '车辆故障 → 订单接管 → 智能重调度'}</h3>
        <p>冷藏车 02 在途中故障，系统评估其他车辆接管 O4、O5 的可行路线。</p></div>
      <span className="fault-mode">仿真场景 · 模拟路线</span>
    </div>
    {mode === 'incident' && <div className="fault-story">
      <span><b>① 运行中</b><small>车 02 先完成 O3</small></span>
      <span><b>② 故障停运</b><small>O4、O5 滞留待转运</small></span>
      <span><b>③ OR-Tools</b><small>先取货、再配送；重新分配</small></span>
      <span><b>④ 人工审核</b><small>切换本次演示的候选</small></span>
    </div>}
    {mode === 'incident' && <div className="fault-ai-panel">
      <div className="fault-ai-heading"><div><strong>AI 协同处置</strong><small>DeepSeek 识别工具任务 · OR-Tools 计算 · 人工最终审批</small></div>
        <button className="btn btn-primary" disabled={busy} onClick={() => void triggerAi()}>
          {busy ? '正在执行…' : '启动 AI 协同处置'}
        </button>
      </div>
      {aiResult && <div className="fault-ai-evidence">
        <p><b>模型状态：</b>{aiResult.ai_status === 'model_success' ? `DeepSeek 已完成工具调用与说明${aiResult.model ? ` · ${aiResult.model}` : ''}`
          : aiResult.ai_status === 'model_explanation_failed' ? '工具调用完成，DeepSeek 最终说明失败'
          : `未完成 AI 协同 · ${aiResult.error_code || aiResult.ai_status}`}</p>
        {aiResult.tool_trace.length > 0 && <div className="fault-ai-tools">{aiResult.tool_trace.map((item, index) =>
          <span key={`${item.tool}-${index}`}>✓ {item.tool === 'get_incident_context' ? '读取异常' :
            item.tool === 'solve_rescue_dispatch' ? '调用 OR-Tools' : '比较方案'}</span>)}</div>}
        {aiResult.reply && aiResult.ai_status === 'model_success' && <p className="fault-ai-answer">{aiResult.reply}</p>}
        {aiResult.rescue && <small>求解状态：{aiResult.rescue.status} · 方案校验：{aiResult.rescue.candidate_valid ? '通过' : '未通过'} · 仍需人工审批</small>}
      </div>}
    </div>}
    <div className="stageb-actions">
      <button className="btn btn-ghost" disabled={busy} onClick={() => void trigger()}>
        {busy ? '求解中…' : data ? '重新触发故障并求解' : mode === 'replay' ? '载入三车故障回放' : '仅使用 OR-Tools 求解'}
      </button>
      {data && <button className="btn btn-ghost" onClick={() => {setPlaying(false);setTime(0);setView('baseline');}}>查看故障前原计划</button>}
    </div>
    {mode === 'replay' && !data && !busy && <p className="callout">尚无三车故障救援运行。点击“载入三车故障回放”后可查看车辆轨迹与处置方案。</p>}
    {error && <p role="alert" className="callout callout-error">{error}</p>}
    {data && routes && <>
      <div className="fault-event" role="status"><strong>已触发：{numberVehicle(data.failure_vehicle_id)} 途中故障</strong>
        <span>故障时刻 {Math.round(data.failure_time_s)}s · 已交付 O3 · 安全交接点 O3 · 待接管 {data.rescue_order_ids.map(orderName).join('、')}</span>
        <span>求解状态：{data.status === 'solved' && data.candidate_valid ? 'OR-Tools 求解成功，约束校验通过' : `候选不可批准：${data.reason || data.status}`}</span>
      </div>
      <div className="fault-metrics">
        {([{key:'baseline',name:'原计划 v0',detail:'未发生故障，仅作参考'},
           {key:'no_rescue',name:'故障后不救援',detail:'车 02 停运，部分订单无法交付'},
           {key:'candidate',name:'智能接管候选',detail:'真实跨车重调度 · 待人工确认'}] as const).map(entry => {
          const metric = data.metrics[entry.key];
          return <div key={entry.key} className={`fault-metric-card ${entry.key==='candidate' ? 'fault-candidate' : ''}`}>
            <h4>{entry.name}</h4><small>{entry.detail}</small>
            {metric ? <><strong className="fault-big">{metric.delivered_orders}<em> / {metric.total_orders} 单</em></strong>
              {metricRows.map(row => <div className="fault-metric-line" key={row.key}><span>{row.name}</span><b>{metricCopy(metric,row.key)}</b></div>)}</>
              : <p>暂无有效候选方案。</p>}
          </div>;
        })}
      </div>
      {data.status === 'solved' && data.candidate_valid ? <div className="fault-result">
        <strong>真实处置结果：恢复 {data.recovered_orders} 单配送能力</strong>
        <p>故障车停运；救援车辆先到 O3 交接点取货，再配送 {data.reassigned_order_ids?.map(orderName).join('、')}。</p>
        <div className="fault-assignments">{Object.entries(data.rescue_assignments ?? {}).map(([order,vehicle]) => <span key={order}>{orderName(order)} → {numberVehicle(vehicle)}</span>)}</div>
        <small>比较基准：故障后不救援。费用为模拟里程费用及延误罚金。</small>
      </div> : <p className="callout callout-warn">当前没有可批准的救援路线。{data.reason}</p>}
      <div className="fault-approval">
        <strong>人工方案审核 · {session?.approval === 'pending' ? '待审批' : session?.approval === 'approved' ? '本次演示已批准' : '本次演示已拒绝'}</strong>
        <span>场景审批状态：本地会话记录，不影响实际派车。</span>
        {session?.approval === 'pending' && <div className="stageb-actions">
          <button className="btn btn-primary" disabled={!canApprove} onClick={() => decide('approved')}>批准并回放接管路线</button>
          <button className="btn btn-ghost" onClick={() => decide('rejected')}>拒绝候选方案</button>
        </div>}
      </div>
      <div className="fault-playbar">
        <label>地图方案 <select value={displayView} onChange={e => {setView(e.target.value as DemoMode);setPlaying(false);}}>
          <option value="baseline">故障前原计划 v0</option><option value="no_rescue">故障后不救援</option>
          <option value="candidate" disabled={!data.candidate_valid}>OR-Tools 接管候选（可预览）</option></select></label>
        <button className="btn btn-primary btn-sm" onClick={() => {if(time >= data.horizon_s)setTime(0);setPlaying(!playing);}}>{playing?'暂停':'播放'}</button>
        <button className="btn btn-ghost btn-sm" onClick={() => {setPlaying(false);setTime(0);}}>回到起点</button>
        <label>速度 <select value={speed} onChange={e=>setSpeed(Number(e.target.value))}><option value={1}>1×</option><option value={5}>5×</option><option value={10}>10×</option><option value={30}>30×</option></select></label>
        <button className={`btn btn-sm ${compare?'btn-primary':'btn-ghost'}`} disabled={!data.candidate_valid} onClick={()=>setCompare(v=>!v)}>{compare?'退出同步对比':'双方案同步回放'}</button>
        <label className="fault-timeline">{Math.round(time)}s / {data.horizon_s}s
          <input type="range" min={0} max={data.horizon_s} step="1" value={time} onChange={e=>{setPlaying(false);setTime(Number(e.target.value));}} />
          <small>故障发生：{data.failure_time_s}s</small>
        </label>
      </div>
      {compare && data.candidate_valid ? <div className="fault-map-grid">
        <div><h4>不救援 · 故障后原地停运</h4><DigitalTwinMap2D routes={routes.no_rescue} nodeIds={nodeIds} demoNodes={nodes} simTimeS={time}
          selectedVehicleId={selected} onPickVehicle={setSelected} playing={playing} playbackSpeed={speed}
          affectedVehicleIds={[data.failure_vehicle_id]} haltedVehicleIds={[data.failure_vehicle_id]} eventActive={time >= data.failure_time_s} height={340}/></div>
        <div><h4>OR-Tools · 救援车辆接管</h4><DigitalTwinMap2D routes={routes.candidate} nodeIds={nodeIds} demoNodes={nodes} simTimeS={time}
          selectedVehicleId={selected} onPickVehicle={setSelected} playing={playing} playbackSpeed={speed}
          affectedVehicleIds={[data.failure_vehicle_id]} haltedVehicleIds={[data.failure_vehicle_id]} eventActive={time >= data.failure_time_s} height={340}/></div>
      </div> : <DigitalTwinMap2D routes={routes[displayView]} nodeIds={nodeIds} demoNodes={nodes}
        simTimeS={time} selectedVehicleId={selected} onPickVehicle={setSelected}
        affectedVehicleIds={[data.failure_vehicle_id]} haltedVehicleIds={[data.failure_vehicle_id]} eventActive={displayView !== 'baseline' && time >= data.failure_time_s}
        playing={playing} playbackSpeed={speed} height={460}/>}
      <details className="fault-details"><summary>查看约束与运行诊断</summary>
        <ul>{data.assumptions.map(a=><li key={a}>{a}</li>)}</ul>
        <p>求解器：{data.solver}；模型可行性校验：{data.candidate_valid?'通过':'未通过'}；原运行及数据库数据未被更改。</p>
        {data.solver_diagnostic && <p>求解诊断：独立构造出 {data.solver_diagnostic.physical_seed_count} 条业务可行初始路线；
          OR-Tools 初始解验证{data.solver_diagnostic.ortools_seed_accepted ? '已接受' : '未接受'}；
          搜索阶段 {data.solver_diagnostic.attempts.map(a=>`${a.stage}:${a.result}`).join('、')}。
          {data.solver_diagnostic.candidate_checks?.length ? ` 候选校验：${data.solver_diagnostic.candidate_checks.join('；')}` : ''}
        </p>}
      </details>
    </>}
  </section>;
}
