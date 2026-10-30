import { useEffect, useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import DigitalTwin3D from '../../components/DigitalTwin3D';
import { loadSimulationState, selectIncident, short, tracksToTwinRoutes } from './api';
import type { SimulationState } from './api';
import { RunBar, useStageRun } from './RunContext';
import ProposalComparison from './ProposalComparison';

/** One shared replay widget embedded in the existing transport and simulation pages. */
export default function StageReplay({ mode = 'replay' }: { mode?: 'transport' | 'replay' }) {
  const stage = useStageRun();
  const { simulation, runId } = stage;
  const [time, setTime] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [view, setView] = useState<'active' | 'baseline' | 'candidate'>('active');
  const [state, setState] = useState<SimulationState | null>(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const incident = selectIncident(simulation);
  const candidateVisible = Boolean(incident && incident.proposal_valid === true &&
    (view === 'candidate' || (view === 'active' && simulation?.active_version === 1)));
  const visibleTracks = candidateVisible ? incident?.candidate_tracks ?? simulation?.tracks ?? [] : simulation?.tracks ?? [];
  const routes = useMemo(() => tracksToTwinRoutes(visibleTracks), [visibleTracks]);
  // Keep topology node coordinates stable across baseline and reroute views.
  const nodes = useMemo(() => [...new Set([
    ...tracksToTwinRoutes(simulation?.tracks ?? []).flatMap(route => route.stops.map(stop => stop.nodeId)),
    ...tracksToTwinRoutes(incident?.candidate_tracks ?? []).flatMap(route => route.stops.map(stop => stop.nodeId)),
  ])].sort(), [simulation]);
  const warehouses = useMemo(() => [...new Set(tracksToTwinRoutes(simulation?.tracks ?? []).map(route => route.warehouseId))]
    .map(id => ({ id, zones: ['chilled'] as ('chilled' | 'frozen')[] })), [simulation]);
  const horizon = simulation?.horizon_s ?? 0;
  useEffect(() => { setTime(0); setPlaying(false); setView('active'); setState(null); }, [simulation?.simulation_id]);
  useEffect(() => {
    if (!playing || !simulation) return;
    const timer = window.setInterval(() => setTime(value => {
      const next = Math.min(horizon, value + speed);
      if (next >= horizon) setPlaying(false);
      return next;
    }), 1000);
    return () => window.clearInterval(timer);
  }, [playing, simulation, horizon, speed]);
  useEffect(() => {
    if (!simulation) return;
    const controller = new AbortController();
    setError(''); setState(null);
    void loadSimulationState(runId, time, view, controller.signal).then(value => {
      if (!controller.signal.aborted && value.time_s === time) setState(value);
    }).catch(cause => { if (!controller.signal.aborted) setError(String(cause)); });
    return () => controller.abort();
  }, [simulation, runId, time, view]);
  const affected = incident?.vehicle_id ? [incident.vehicle_id] : [];
  const showAdjusted = candidateVisible && Number.isFinite(incident?.time_s) && Number.isFinite(incident?.delay_s);
  const holds = showAdjusted && incident?.vehicle_id ? { [incident.vehicle_id]: { fromS: incident.time_s!, untilS: incident.time_s! + incident.delay_s! } } : {};
  return <section aria-label="数据库驱动仓运模拟">
    <SectionHeader title={mode === 'transport' ? '本次仓运模拟 · 3D 车辆路线' : '全局仓运仿真回放'}
      desc="读取 PostgreSQL 中的已校验方案与持久化车辆轨迹；3D 路形为示意，事件和状态以服务端为准。" />
    <RunBar state={stage} allowCreate />
    {simulation && <>
      <p className="callout callout-warn">这是数据库驱动的确定性模拟，不是真实 GPS 或实际签收。拖动回放不会更改库存或派车；审批只切换模拟版本。</p>
      <div className="stageb-controls panel">
        <label>方案视图 <select aria-label="方案视图" value={view} onChange={event => setView(event.target.value as typeof view)}>
          <option value="active">当前生效模拟版本</option><option value="baseline">原方案 v0</option>
          <option value="candidate" disabled={!incident || incident.proposal_valid !== true}>延误候选方案</option>
        </select></label>
        <label>速度 <select aria-label="播放速度" value={speed} onChange={e => setSpeed(Number(e.target.value))}>
          {[1, 2, 5, 10, 30].map(value => <option key={value} value={value}>{value}x</option>)}
        </select></label>
        <button className="btn btn-primary btn-sm" onClick={() => { if (time >= horizon) setTime(0); setPlaying(!playing); }}>{playing ? '暂停' : '播放'}</button>
        <button className="btn btn-ghost btn-sm" onClick={() => { setPlaying(false); setTime(0); }}>回到起点</button>
        <label className="stageb-seek">模拟时刻 {time}s / {horizon}s <input type="range" aria-label="全局模拟时间轴"
          min={0} max={horizon} step={1} value={time} onChange={event => { setPlaying(false); setTime(Number(event.target.value)); }} /></label>
      </div>
      {error && <p role="alert" className="callout callout-error">状态回放失败：{error}</p>}
      <div className="stageb-state-row"><span>模拟版本：v{state?.active_version ?? simulation.active_version}</span>
        <span>方案：{state?.view ?? '读取中'}</span><span>在途车辆：{state?.in_transit_vehicle_ids?.length ?? '—'}</span>
        <span>已完成作业：{state?.completed_operation_ids?.length ?? '—'}</span>
        <span>已送达订单：{state?.completed_order_ids?.length ?? '—'}</span></div>
      {routes.length ? <DigitalTwin3D routes={routes} warehouses={warehouses} nodeIds={nodes} orderCount={simulation.reconciliation?.scope_orders ?? 0}
        simTimeS={time} eventActive={Boolean(incident && time >= (incident.time_s ?? horizon + 1))}
        affectedVehicleIds={affected} holdWindows={holds} selectedVehicleId={selected} onPickVehicle={setSelected} height={460} />
        : <p className="callout">当前模拟没有可绘制的轨迹节点；请查看事件表或联系后端核对轨迹结构。</p>}
      <p className="s5-muted">{candidateVisible && incident?.route_changed
        ? '当前展示经约束校验的局部重规划候选轨迹；已执行路段保持不变，之后从安全节点接续新的剩余停靠顺序。'
        : '地图绘制持久化的示意轨迹；如无可用重规划，候选方案保守采用原地等待＋顺延。'} 具体路段位置和进度以服务端 state-at 为准，并非 GPS。</p>
      {incident?.comparison && <details className="panel"><summary>候选方案的路线、时序与费用评估</summary>
        <ProposalComparison incident={incident} comparison={incident.comparison} /></details>}
      {candidateVisible && incident?.route_changed && <div className="panel">
        <h3>局部重规划：延误车辆剩余停靠顺序</h3>
        <p className="s5-muted">已发生的行程和其他车辆保持原样，以下仅用于比较原方案与待审批／已批准模拟候选。</p>
        {(['baseline', 'candidate'] as const).map(label => {
          const track = (label === 'baseline' ? simulation.tracks : incident.candidate_tracks ?? [])
            .find(item => item.vehicle_id === incident.vehicle_id);
          return <p key={label}><strong>{label === 'baseline' ? '原方案 v0' : '局部优化候选'}</strong>：{
            track?.stops?.map(stop => `${short(stop.node_id)}(${stop.arrival_s}s)`).join(' → ') || '无停靠信息'
          }</p>;
        })}
      </div>}
      <div className="panel"><h3>时刻状态与事件</h3>
        {state && <><p>后端返回车辆位置：{Object.entries(state.vehicle_positions ?? {}).map(([vehicle, position]) =>
          `${short(vehicle)}：${typeof position === 'string' ? short(position) : `${short(position.from_node_id ?? position.node_id)}→${short(position.to_node_id)} (${Math.round((position.progress ?? 0) * 100)}%)`}`).join('；') || '暂无'}</p>
        <div className="table-wrap"><table><thead><tr><th>模拟时间</th><th>事件</th><th>车辆</th><th>订单</th></tr></thead><tbody>
          {(state.events ?? []).slice(-18).map((item, index) => <tr key={item.id ?? `${item.time_s}-${index}`}><td>{item.time_s}s</td>
            <td>{item.kind}</td><td>{short(item.vehicle_id)}</td><td>{short(item.order_id)}</td></tr>)}</tbody></table></div></>}
      </div>
    </>}
  </section>;
}
