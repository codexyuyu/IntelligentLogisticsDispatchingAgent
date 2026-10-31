import { useEffect, useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import DigitalTwinMap2D from '../../components/DigitalTwinMap2D';
import { buildWenchangFourTruckShowcase } from '../../lib/liuzhouDemoMap';
import { loadSimulationState, selectIncident, short, tracksToTwinRoutes } from './api';
import type { SimulationState } from './api';
import { RunBar, useStageRun } from './RunContext';
import ProposalComparison from './ProposalComparison';
import DefenseImpactPanel from './DefenseImpactPanel';

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
  const [compareMode, setCompareMode] = useState(false);
  const [showcase, setShowcase] = useState(false);
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
  const horizon = simulation?.horizon_s ?? 0;
  useEffect(() => { setTime(0); setPlaying(false); setView('active'); setState(null); setCompareMode(false); setShowcase(false); }, [simulation?.simulation_id]);
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
    if (!simulation || showcase) return;
    const controller = new AbortController();
    setError(''); setState(null);
    void loadSimulationState(runId, time, view, controller.signal).then(value => {
      if (!controller.signal.aborted && value.time_s === time) setState(value);
    }).catch(cause => { if (!controller.signal.aborted) setError(String(cause)); });
    return () => controller.abort();
  }, [simulation, runId, time, view, showcase]);
  const affected = incident?.vehicle_id ? [incident.vehicle_id] : [];
  // Candidate tracks are already retimed by the backend. Never add the delay
  // again at rendering time; the old holdWindows prop double-applied it.
  const baselineRoutes = useMemo(() => tracksToTwinRoutes(simulation?.tracks ?? []), [simulation]);
  const candidateRoutes = useMemo(() => tracksToTwinRoutes(incident?.candidate_tracks ?? []), [incident]);
  const comparisonAvailable = Boolean(incident?.proposal_valid === true && candidateRoutes.length);
  const showcaseRoutes = useMemo(() => buildWenchangFourTruckShowcase(horizon), [horizon]);
  const displayedRoutes = showcase ? showcaseRoutes : routes;
  const displayedNodes = showcase ? [...new Set(showcaseRoutes.flatMap(route => route.stops.map(stop => stop.nodeId)))].sort() : nodes;
  return <section aria-label="数据库驱动仓运模拟">
    <SectionHeader title={mode === 'transport' ? '本次仓运模拟 · 柳州二维地图路线' : '全局仓运仿真回放'}
      desc="广西科技大学文昌校区周边实景道路底图；配送路线为固定模拟路径，车辆停靠顺序、时间与状态仍以服务端为准。" />
    <RunBar state={stage} allowCreate />
    {simulation && <>
      <p className="callout callout-warn">联合运行仿真 · 地图线路为示意道路</p>
      {!showcase && incident?.comparison && <DefenseImpactPanel comparison={incident.comparison} validated={incident.proposal_valid === true} compact />}
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
        <button className={compareMode ? 'btn btn-primary btn-sm' : 'btn btn-ghost btn-sm'} disabled={!comparisonAvailable || showcase}
          onClick={() => setCompareMode(v => !v)}>{compareMode ? '退出双方案对比' : '双方案同步对比'}</button>
        <label className="stageb-seek">模拟时刻 {time}s / {horizon}s
          <span className="replay-seek-inner"><input type="range" aria-label="全局模拟时间轴"
            min={0} max={horizon} step={1} value={time} onChange={event => { setPlaying(false); setTime(Number(event.target.value)); }} />
            {Number.isFinite(incident?.time_s) && horizon > 0 && <span className="replay-event-tick" title={`车辆延误发生于 ${incident!.time_s}s`}
              style={{left:`${Math.min(99, Math.max(1, (incident!.time_s! / horizon)*100))}%`}}/>}</span></label>
      </div>
      <div className="coldmap-showcase-switch">
        <div><strong>地图显示内容</strong><small>{showcase ? '四车轨迹展示' : '当前联合运行轨迹'}</small></div>
        <button type="button" className={`btn btn-sm ${!showcase ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setShowcase(false)}>当前调度车辆</button>
        <button type="button" className={`btn btn-sm ${showcase ? 'btn-primary' : 'btn-ghost'}`} onClick={() => {setShowcase(true);setCompareMode(false);setPlaying(false);setTime(0);}}>四车场景演示</button>
      </div>
      {showcase && <div className="callout callout-warn"><strong>四车展示：</strong>独立模拟轨迹，不参与调度指标统计。</div>}
      {error && <p role="alert" className="callout callout-error">状态回放失败：{error}</p>}
      {!showcase && <div className="stageb-state-row"><span>模拟版本：v{state?.active_version ?? simulation.active_version}</span>
        <span>方案：{state?.view ?? '读取中'}</span><span>在途车辆：{state?.in_transit_vehicle_ids?.length ?? '—'}</span>
        <span>已完成作业：{state?.completed_operation_ids?.length ?? '—'}</span>
        <span>已送达订单：{state?.completed_order_ids?.length ?? '—'}</span></div>}
      {compareMode && comparisonAvailable && !showcase ? <div className="replay-compare-grid">
        <div className="replay-compare-item"><h3>原方案 v0 · 延误前基线</h3>
          <DigitalTwinMap2D routes={baselineRoutes} nodeIds={nodes}
            simTimeS={time} playing={playing} playbackSpeed={speed} eventActive={false}
            selectedVehicleId={selected} onPickVehicle={setSelected} height={340}/></div>
        <div className="replay-compare-item"><h3>候选重调度 · 同步仿真时刻</h3>
          <DigitalTwinMap2D routes={candidateRoutes} nodeIds={nodes}
            simTimeS={time} playing={playing} playbackSpeed={speed}
            eventActive={!showcase && Boolean(incident && time >= (incident.time_s ?? horizon+1))}
            affectedVehicleIds={affected} selectedVehicleId={selected} onPickVehicle={setSelected} height={340}/></div>
      </div> : displayedRoutes.length ? <DigitalTwinMap2D routes={displayedRoutes} nodeIds={displayedNodes} showcase={showcase}
        simTimeS={time} playing={playing} playbackSpeed={speed} eventActive={!showcase && Boolean(incident && time >= (incident.time_s ?? horizon+1))}
        affectedVehicleIds={showcase ? [] : affected} selectedVehicleId={selected} onPickVehicle={setSelected} height={510}/>
        : <p className="callout">当前模拟没有可绘制的轨迹节点；请查看事件表或联系后端核对轨迹结构。</p>}
      {compareMode && !showcase && <p className="s5-muted">两幅画面采用相同仿真时刻和车辆选中状态。左侧是异常发生之前保存的原轨迹 v0，右侧是候选完整轨迹；不是“简单顺延”对照，成本和收益请以方案评估数据为准。</p>}
      {!showcase && <p className="s5-muted">{candidateVisible && incident?.route_changed
        ? '当前展示经约束校验的局部重规划候选轨迹；已执行路段保持不变，之后从安全节点接续新的剩余停靠顺序。'
        : '地图绘制持久化的示意轨迹；如无可用重规划，候选方案保守采用原地等待＋顺延。'} 具体路段位置和进度以服务端 state-at 为准，并非 GPS。</p>}
      {!showcase && incident?.comparison && <details className="panel"><summary>展开完整候选方案指标及交付时序</summary>
        <ProposalComparison incident={incident} comparison={incident.comparison} /></details>}
      {!showcase && candidateVisible && incident?.route_changed && <div className="panel">
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
      {!showcase && <div className="panel"><h3>时刻状态与事件</h3>
        {state && <><p>后端返回车辆位置：{Object.entries(state.vehicle_positions ?? {}).map(([vehicle, position]) =>
          `${short(vehicle)}：${typeof position === 'string' ? short(position) : `${short(position.from_node_id ?? position.node_id)}→${short(position.to_node_id)} (${Math.round((position.progress ?? 0) * 100)}%)`}`).join('；') || '暂无'}</p>
        <div className="table-wrap"><table><thead><tr><th>模拟时间</th><th>事件</th><th>车辆</th><th>订单</th></tr></thead><tbody>
          {(state.events ?? []).slice(-18).map((item, index) => <tr key={item.id ?? `${item.time_s}-${index}`}><td>{item.time_s}s</td>
            <td>{item.kind}</td><td>{short(item.vehicle_id)}</td><td>{short(item.order_id)}</td></tr>)}</tbody></table></div></>}
      </div>}
    </>}
  </section>;
}
