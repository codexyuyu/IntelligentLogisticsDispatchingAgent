import { useEffect, useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import DigitalTwin3D from '../../components/DigitalTwin3D';
import { loadSimulationState, selectIncident, short, tracksToTwinRoutes } from './api';
import type { SimulationState } from './api';
import { RunBar, useStageRun } from './RunContext';

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
  const routes = useMemo(() => tracksToTwinRoutes(simulation?.tracks ?? []), [simulation]);
  const nodes = useMemo(() => [...new Set(routes.flatMap(route => route.stops.map(stop => stop.nodeId)))], [routes]);
  const warehouses = useMemo(() => [...new Set(routes.map(route => route.warehouseId))]
    .map(id => ({ id, zones: ['chilled'] as ('chilled' | 'frozen')[] })), [routes]);
  const incident = selectIncident(simulation);
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
  const showAdjusted = Boolean(incident && (view === 'candidate' || (view === 'active' && simulation?.active_version === 1))
    && incident.proposal_valid === true && Number.isFinite(incident.time_s) && Number.isFinite(incident.delay_s));
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
      <p className="s5-muted">地图绘制的是已持久化路线的示意拓扑；若审批记录包含延误时刻与时长，候选视图将按原地等待＋顺延绘制；后端 state-at 始终是最终状态证据（并非 GPS）。</p>
      <div className="panel"><h3>时刻状态与事件</h3>
        {state && <><p>后端返回车辆位置：{Object.entries(state.vehicle_positions ?? {}).map(([vehicle, position]) =>
          `${short(vehicle)}：${typeof position === 'string' ? short(position) : short(position.node_id ?? position.to_node_id)}`).join('；') || '暂无'}</p>
        <div className="table-wrap"><table><thead><tr><th>模拟时间</th><th>事件</th><th>车辆</th><th>订单</th></tr></thead><tbody>
          {(state.events ?? []).slice(-18).map((item, index) => <tr key={item.id ?? `${item.time_s}-${index}`}><td>{item.time_s}s</td>
            <td>{item.kind}</td><td>{short(item.vehicle_id)}</td><td>{short(item.order_id)}</td></tr>)}</tbody></table></div></>}
      </div>
    </>}
  </section>;
}
