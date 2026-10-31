import StageReplay from '../stageB/Replay';
import FaultRescueDemo from '../stageB/FaultRescueDemo';

import { useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import DigitalTwinMap2D from '../../components/DigitalTwinMap2D';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { routesToTwinRoutes } from '../../appTypes';
import { buildFourVehicleShowcase } from '../../lib/fleetDemo';
import { useSimClock } from '../../hooks/useSimClock';
import { fmtClock, fmtKM, pct } from '../../lib/format';

const HORIZON = 1800;
const SPEEDS = [0.5, 1, 2, 4, 8, 16];

export default function Page() {
  const {
    snapshot, baselinePlan, anomaly, anomalyResult, simulation, simPhase, simError, runSimulation, runBaseline,
  } = useApp();
  const clock = useSimClock(HORIZON, false);

  const [showcase, setShowcase] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedVehicle, setSelectedVehicle] = useState<string | null>(null);
  const [followVehicle, setFollowVehicle] = useState(false);
  const [occurredAt, setOccurredAt] = useState(900);
  const [delayS, setDelayS] = useState(900);
  const activePlan = anomalyResult?.replanned_plan ?? baselinePlan;
  const orders = snapshot?.orders ?? [];
  const vehicles = snapshot?.vehicles ?? [];
  const solvedRoutes = useMemo(() => routesToTwinRoutes(activePlan, vehicles), [activePlan, vehicles]);
  const demoRoutes = useMemo(() => buildFourVehicleShowcase(orders, vehicles, snapshot?.warehouses ?? []), [orders, vehicles, snapshot]);
  const routes = showcase && demoRoutes.length === 4 ? demoRoutes : solvedRoutes;
  const nodeIds = useMemo(() => {
    const set = new Set<string>();
    for (const o of orders) set.add(o.delivery_node_id);
    for (const w of snapshot?.warehouses ?? []) set.add(w.node_id);
    return [...set];
  }, [orders, snapshot]);

  const simEvents = simulation?.emitted_events ?? [];
  const trigger = anomaly.event ?? simEvents.find((e) => e.event_type === 'departure_delayed') ?? null;
  const triggerAt = trigger?.occurred_at_s ?? 900;
  const eventFired = clock.t >= triggerAt && Boolean(trigger);
  const affectedOrders = trigger ? trigger.payload.affected_order_ids : [];
  const affectedVehicles = trigger ? [trigger.object_id] : [];
  const planVersion = eventFired && anomalyResult ? anomalyResult.replanned_plan.version : (activePlan?.version ?? null);
  const phaseLabel = !trigger
    ? '正常基线推演'
    : clock.t < triggerAt ? '异常前 · 正常配送'
      : clock.t < triggerAt + (trigger?.payload.delay_s ?? 0) ? '异常处置中 · veh_1 延误'
        : anomalyResult ? '局部重调度完成 · 恢复运行' : '延误消化中';

  const unservedNow = eventFired && anomalyResult ? anomalyResult.replanned_plan.routing.unserved_orders : (activePlan?.routing.unserved_orders ?? []);

  async function runReplay() {
    const input = { eventType: 'departure_delayed' as const, objectId: 'veh_1', orderIds: ['ord_001'], occurredAtS: Math.max(0, occurredAt), delayS: Math.max(1, delayS) };
    if (!baselinePlan) await runBaseline();
    await runSimulation(input);
  }

  return <div>
    <FaultRescueDemo mode="replay" />
    <details className="panel" style={{ marginTop: 14 }} onToggle={event => setShowHistory(event.currentTarget.open)}><summary>历史联合运行与原有仿真回放</summary>
    {showHistory && <><StageReplay mode="replay" />
    <details><summary>本地快照与 SimPy 仿真</summary>
    <SectionHeader title="仿真回放"
      actions={<button className="btn btn-primary" disabled={simPhase === 'running' || !snapshot} onClick={() => void runReplay()}>{simPhase === 'running' ? '仿真运行中…' : '运行当前异常仿真'}</button>} />

    <div className="kpi-grid">
      <KpiCard label="仿真状态" value={simPhase === 'idle' ? '未运行' : simPhase === 'running' ? '运行中' : simPhase === 'completed' ? '已完成' : `失败`} sub={simulation?.simulation_id ?? 'seed 17 · horizon 1800s'} icon="play" tone={simPhase === 'failed' ? 'red' : simPhase === 'completed' ? 'green' : 'neutral'} />
      <KpiCard label="仿真事件" value={`${simEvents.length}`} icon="alert" tone="orange" />
      <KpiCard label="当前 Plan Version" value={planVersion != null ? `v${planVersion}` : '—'} sub={eventFired && anomalyResult ? `v${anomalyResult.previous_plan_version} → v${anomalyResult.replanned_plan.version} @${fmtClock(triggerAt)}` : undefined} icon="database" tone="green" />
      <KpiCard label="最终快照" value={simulation ? `v${simulation.final_snapshot.version} · ${fmtClock(simulation.final_snapshot.simulation_time_s)}` : '—'} icon="clock" tone="neutral" />
    </div>

    {simPhase === 'failed' && <div className="callout callout-error">仿真失败：{simError}</div>}
    <div className="panel simulation-controls">
      <div className="panel-title-row"><div><h3>仿真场景参数</h3></div><StatusPill tone="warning">模拟参数</StatusPill></div>
      <div className="form-grid">
        <label>异常对象<select value="veh_1" disabled><option value="veh_1">veh_1 · 车辆</option></select></label>
        <label>受影响订单<select value="ord_001" disabled><option value="ord_001">ord_001</option></select></label>
        <label>异常发生时刻 (s)<input type="number" min="0" max="1800" value={occurredAt} onChange={(e) => setOccurredAt(Number(e.target.value) || 0)} /></label>
        <label>延误时长 (s)<input type="number" min="1" max="1800" value={delayS} onChange={(e) => setDelayS(Number(e.target.value) || 1)} /></label>
      </div>
    </div>

    <div className="r25-showcase-toolbar">
      <div><strong>四车轨迹回放</strong><small>{showcase && demoRoutes.length === 4
        ? '四车独立模拟轨迹'
        : '联合运行轨迹 · 模拟地图路线'}</small></div>
      <button type="button" className={`btn ${!showcase ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setShowcase(false)}>真实规划</button>
      <button type="button" className={`btn ${showcase ? 'btn-primary' : 'btn-ghost'}`} disabled={demoRoutes.length !== 4} onClick={() => { setShowcase(true); clock.seek(0); }}>四车演示</button>
    </div>
    {showcase && <div className="r25-showcase-note" role="status">四车模拟轨迹与实际联合运行独立。</div>}
    {showcase && demoRoutes.length !== 4 && <div className="callout">四车演示需要场景快照中有至少四辆车辆及仓库、订单；请先运行或导入基线场景。</div>}
    <div className="r25-fleet-picker">
      <span>镜头视角：</span><button type="button" className={`btn btn-sm ${!followVehicle ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFollowVehicle(false)}>全局自由视角</button>
      {routes.map((r) => <button type="button" key={r.vehicleId} className={`btn btn-sm ${followVehicle && selectedVehicle === r.vehicleId ? 'btn-primary' : 'btn-ghost'}`} onClick={() => { setSelectedVehicle(r.vehicleId); setFollowVehicle(true); }}>{r.vehicleId} · 跟车</button>)}
    </div>
    <DigitalTwinMap2D
      routes={routes}
      nodeIds={nodeIds}
      simTimeS={clock.t}
      selectedVehicleId={selectedVehicle}
      followVehicleId={followVehicle ? selectedVehicle : null}
      onPickVehicle={setSelectedVehicle}
      eventActive={!showcase && eventFired}
      affectedVehicleIds={!showcase && eventFired ? affectedVehicles : []}
      height={460}
    />

    <div className="panel player-panel">
      <div className="player-row">
        <button className="btn btn-primary player-btn" onClick={clock.toggle}>{clock.playing ? '暂停' : '播放'}</button>
        <div className="seg">
          {SPEEDS.map((s) => <button key={s} className={`seg-btn ${clock.speed === s ? 'is-active' : ''}`} onClick={() => clock.setSpeed(s)}>{s}x</button>)}
        </div>
        <input className="player-slider" type="range" min={0} max={HORIZON} step={1} value={Math.round(clock.t)} onChange={(e) => clock.seek(Number(e.target.value))} />
        <div className="player-time"><b>{fmtClock(clock.t)}</b><small>/ {fmtClock(HORIZON)}</small></div>
      </div>
      <div className="sim-track">
        <div className="track">
          <span className="marker marker-start" />
          {trigger && <span className="marker marker-event" style={{ left: `${(triggerAt / HORIZON) * 100}%` }} title={`${trigger.event_type} · ${trigger.object_id}`} />}
          <span className="marker marker-end" style={{ left: '100%' }} />
          <span className="track-cursor" style={{ left: `${(clock.t / HORIZON) * 100}%` }} />
        </div>
        <div className="track-labels"><span>0s</span><span>{triggerAt}s · {trigger ? `${trigger.object_id} 延误` : '—'}</span><span>{HORIZON}s</span></div>
      </div>
    </div>

    <div className="replay-grid">
      <div className="panel">
        <div className="panel-title-row"><div><h3>仿真事件流</h3></div><StatusPill tone={simPhase === 'completed' ? 'success' : 'info'}>{simPhase === 'completed' ? 'completed' : simPhase}</StatusPill></div>
        {simEvents.length ? (
          <div className="event-stream">
            {simEvents.map((e) => (
              <div className={`event-item ${clock.t >= e.occurred_at_s ? 'is-hit' : ''}`} key={e.event_id}>
                <span className="event-time">{fmtClock(e.occurred_at_s)}</span>
                <div><b>{e.event_type === 'departure_delayed' ? '车辆出发延误' : e.event_type}</b><small>{e.object_id}{e.payload.delay_s ? ` · +${e.payload.delay_s}s` : ''}{e.payload.affected_order_ids.length ? ` · ${e.payload.affected_order_ids.join('、')}` : ''}</small></div>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      <div className="panel">
        <div className="panel-title-row"><div><h3>当前回放阶段</h3></div><StatusPill tone={eventFired ? 'warning' : 'success'}>{phaseLabel}</StatusPill></div>
        <div className="validation">
          <div><span>仿真时间</span><b>{fmtClock(clock.t)}</b></div>
          <div><span>异常状态</span><b>{!trigger ? '未注入' : eventFired ? `${trigger.object_id} 已延误 +${trigger.payload.delay_s ?? 0}s` : `将于 ${fmtClock(triggerAt)} 触发`}</b></div>
          <div><span>受影响订单</span><b>{eventFired ? affectedOrders.join('、') || '—' : '—'}</b></div>
          <div><span>Plan Version</span><b>{planVersion != null ? `v${planVersion}` : '—'}</b></div>
          <div><span>未服务订单</span><b>{unservedNow.length}</b></div>
          <div><span>局部重调度</span><b>{anomalyResult ? '已完成（异常处置页闭环）' : '未执行'}</b></div>
        </div>
        {eventFired && anomalyResult && (
          <p className="scope-note">播放越过 {fmtClock(triggerAt)} 后展示 v{anomalyResult.replanned_plan.version} 局部重排结果：受影响路线 {fmtKM(anomalyResult.diff.new_distance_m)}，独立验证 {anomalyResult.validation.status}，需求满足率 {pct(orders.length - anomalyResult.replanned_plan.routing.unserved_orders.length, orders.length)}。</p>
        )}
        {eventFired && !anomalyResult && (
          <p className="scope-note">尚未执行局部重调度：请先在「异常处置」页完成闭环，回放将自动联动 v2 方案。</p>
        )}
      </div>

      <div className="panel">
        <div className="panel-title-row"><div><h3>推演终态</h3></div></div>
        <div className="validation">
          <div><span>simulation_id</span><b>{simulation?.simulation_id ?? '—'}</b></div>
          <div><span>base_snapshot</span><b>{simulation?.base_snapshot_id ?? '—'}</b></div>
          <div><span>final_snapshot</span><b>{simulation ? `${simulation.final_snapshot.snapshot_id} · v${simulation.final_snapshot.version}` : '—'}</b></div>
          <div><span>仿真时长</span><b>{simulation ? `${simulation.final_snapshot.simulation_time_s}s` : '—'}</b></div>
          <div><span>随机种子</span><b>17</b></div>
        </div>
      </div>
    </div>
  </details></>}
  </details>
  </div>;
}
