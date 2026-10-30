
import { useMemo, useState } from 'react';
import LiveOverview from './LiveOverview';
import DigitalTwin3D from '../../components/DigitalTwin3D';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { routesToTwinRoutes } from '../../appTypes';
import { buildFourVehicleShowcase } from '../../lib/fleetDemo';
import { useSimClock } from '../../hooks/useSimClock';
import { fmtClock, fmtDur, fmtKM, fmtMs, NA, pct } from '../../lib/format';

export function navigate(key: string) {
  window.dispatchEvent(new CustomEvent('twin:navigate', { detail: key }));
}

export default function DashboardPage() {
  const { snapshot } = useApp();
  return snapshot ? <SnapshotDashboard /> : <LiveOverview />;
}

function SnapshotDashboard() {
  const {
    connection, bootPhase, snapshot, snapshotVersion, scenarioId,
    anomaly, anomalyResult, simulation,
  } = useApp();
  const [selectedVehicle, setSelectedVehicle] = useState<string | null>(null);
  const [showcase, setShowcase] = useState(false);
  const [followVehicle, setFollowVehicle] = useState(false);
  const horizonS = 1800;
  const clock = useSimClock(horizonS, false);

  const orders = snapshot?.orders ?? [];
  const vehicles = snapshot?.vehicles ?? [];
  const warehouses = snapshot?.warehouses ?? [];
  const currentPlan = anomalyResult?.replanned_plan ?? null;

  const routes = useMemo(() => routesToTwinRoutes(currentPlan, vehicles), [currentPlan, vehicles]);
  const demoRoutes = useMemo(() => buildFourVehicleShowcase(orders, vehicles, warehouses), [orders, vehicles, warehouses]);
  const visibleRoutes = showcase && demoRoutes.length === 4 ? demoRoutes : routes;
  const nodeZones = useMemo(() => {
    const map: Record<string, 'chilled' | 'frozen'> = {};
    for (const o of orders) map[o.delivery_node_id] = o.temperature_zone;
    return map;
  }, [orders]);
  const nodeIds = useMemo(() => {
    const set = new Set<string>();
    for (const o of orders) set.add(o.delivery_node_id);
    for (const w of warehouses) set.add(w.node_id);
    return [...set];
  }, [orders, warehouses]);

  const eventActive = anomaly.phase === 'submitting' || anomaly.phase === 'accepted';
  const affectedOrders = anomalyResult?.impact.affected_order_ids ?? [];
  const affectedVehicles = anomalyResult?.impact.affected_vehicle_ids ?? [];
  const holdWindows = useMemo(() => {
    const windows: Record<string, { fromS: number; untilS: number }> = {};
    const event = anomaly.event;
    if (event && event.event_type === 'departure_delayed' && (event.payload.delay_s ?? 0) > 0) {
      windows[event.object_id] = {
        fromS: event.occurred_at_s,
        untilS: Math.min(horizonS, event.occurred_at_s + (event.payload.delay_s ?? 0)),
      };
    }
    return windows;
  }, [anomaly.event]);

  const routing = currentPlan?.routing;
  const unserved = routing?.unserved_orders ?? [];
  const distanceM = (routing?.routes ?? []).reduce((n, r) => n + (r.distance_m ?? 0), 0);
  const durationS = (routing?.routes ?? []).reduce((n, r) => n + (r.duration_s ?? 0), 0);
  const activeVehicles = routes.filter((r) => r.stops.some((s) => s.kind === 'delivery')).length;

  const vehicleRows = useMemo(() => routes.map((route) => {
    const deliveries = route.stops.filter((s) => s.kind === 'delivery');
    const isAffected = affectedVehicles.includes(route.vehicleId);
    return {
      vehicleId: route.vehicleId,
      zone: route.zone,
      orderCount: deliveries.reduce((n, s) => n + s.orderIds.length, 0),
      distanceM: route.distanceM,
      isAffected,
    };
  }), [routes, affectedVehicles]);

  return (
    <div>
      <div className="r26-cockpit-entry"><div><small>仓储视图</small><strong>配送中心</strong><span>冷藏 / 冷冻 · 货架库位 · 叉车取放货 · 月台装车回放</span></div><button className="btn btn-primary" onClick={() => navigate('warehouseTwin')}>查看仓库</button></div>

      <div className="status-strip">
        <div className="strip-item"><span>当前场景</span><b>{scenarioId ?? '未初始化'}</b></div>
        <div className="strip-item"><span>快照版本</span><b>v{snapshotVersion ?? '—'}</b></div>
        <div className="strip-item"><span>系统状态</span><b className={connection === 'ok' ? 'text-ok' : 'text-bad'}>{connection === 'ok' ? '后端已连接' : connection === 'bad' ? '后端离线' : '检查中'}</b></div>
        <div className="strip-item"><span>场景数据</span><b>{snapshot ? '已加载' : '未导入'}</b></div>
        <div className="strip-item"><span>仿真时间</span><b>{fmtClock(clock.t)}</b></div>
        <div className="strip-item"><span>Plan Version</span><b>v{currentPlan?.version ?? '—'}</b></div>
        <button className="btn btn-ghost strip-btn" onClick={() => (clock.playing ? clock.pause() : clock.play())}>{clock.playing ? '暂停态势' : '播放态势'}</button>
      </div>

      <div className="cockpit-grid">
        <aside className="cockpit-col">
          <KpiCard label="订单总量" value={`${orders.length}`} sub="当前快照" icon="package" />
          <KpiCard label="仓库节点" value={`${warehouses.length}`} sub="冷链中心" icon="warehouse" tone="neutral" />
          <KpiCard label="运输车辆" value={`${vehicles.length}`} sub={`投入 ${activeVehicles} 辆`} icon="truck" tone="green" />
          <KpiCard label="当前异常" value={eventActive ? '1' : '0'} sub={eventActive ? anomaly.event?.event_type ?? '' : '无进行中异常'} icon="alert" tone={eventActive ? 'orange' : 'green'} />
          <KpiCard label="需求满足率" value={routing ? pct(orders.length - unserved.length, orders.length) : '—'} sub={`未服务 ${unserved.length}`} icon="check" tone={unserved.length === 0 ? 'green' : 'red'} />
          <KpiCard label="冷链温区" value={`${orders.filter((o) => o.temperature_zone === 'chilled').length} / ${orders.filter((o) => o.temperature_zone === 'frozen').length}`} sub="冷藏 / 冷冻订单" icon="clock" tone="neutral" />
        </aside>

        <section className="cockpit-center">
          <div className="r25-showcase-toolbar"><div><strong>R25 · 城市车队可视化</strong><small>{showcase ? '四车示意动画，不作为真实路线和调度结果' : '实际求解车辆；道路未接 OSRM 时为示意'}</small></div>
          <button type="button" className={`btn btn-sm ${!showcase ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setShowcase(false)}>真实规划</button>
          <button type="button" className={`btn btn-sm ${showcase ? 'btn-primary' : 'btn-ghost'}`} disabled={demoRoutes.length !== 4} onClick={() => { setShowcase(true); clock.seek(0); }}>四车演示</button></div>
          <div className="r25-fleet-picker"><button className={`btn btn-sm ${!followVehicle ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFollowVehicle(false)}>全局视角</button>
          {visibleRoutes.map((r) => <button type="button" key={r.vehicleId} className={`btn btn-sm ${followVehicle && selectedVehicle === r.vehicleId ? 'btn-primary' : 'btn-ghost'}`} onClick={() => { setSelectedVehicle(r.vehicleId); setFollowVehicle(true); }}>{r.vehicleId} · 跟车</button>)}</div>
          <DigitalTwin3D
            routes={visibleRoutes}
            warehouses={warehouses.map((w) => ({ id: w.warehouse_id, zones: w.temperature_zones }))}
            nodeIds={nodeIds}
            nodeZones={nodeZones}
            orderCount={orders.length}
            simTimeS={clock.t}
            getTime={clock.getTime}
            followVehicleId={followVehicle ? selectedVehicle : null}
            eventActive={!showcase && eventActive}
            affectedVehicleIds={showcase ? [] : affectedVehicles}
            holdWindows={showcase ? {} : holdWindows}
            selectedVehicleId={selectedVehicle}
            onPickVehicle={(id) => setSelectedVehicle((prev) => (prev === id ? null : id))}
            onPickWarehouse={() => navigate('warehouseTwin')}
            height={540}
          />
          <div className="cockpit-metrics">
            <div><span>订单完成率</span><b>{routing ? pct(orders.length - unserved.length, orders.length) : '—'}</b></div>
            <div><span>准时率</span><b className="text-na">{NA}</b></div>
            <div><span>运输距离</span><b>{routing ? fmtKM(distanceM) : '—'}</b></div>
            <div><span>路线总时长</span><b>{routing ? fmtDur(durationS) : '—'}</b></div>
            <div><span>车辆投入</span><b>{`${activeVehicles} / ${vehicles.length || '—'}`}</b></div>
            <div><span>冷间利用率</span><b className="text-na">{NA}</b></div>
            <div><span>求解时间</span><b>{currentPlan ? `${fmtMs(currentPlan.warehouse.metadata?.solve_ms)} + ${fmtMs(currentPlan.routing.metadata?.solve_ms)}` : '—'}</b></div>
          </div>
        </section>

        <aside className="cockpit-col">
          <div className={`panel alert-panel ${eventActive ? 'alert-live' : ''}`}>
            <div className="panel-title-row"><div><h3>实时异常告警</h3></div>
              {eventActive ? <StatusPill tone="danger">处置中</StatusPill> : <StatusPill tone="success">无异常</StatusPill>}
            </div>
            {eventActive && anomaly.event ? (
              <div className="alert-card">
                <b>{anomaly.event.event_type === 'departure_delayed' ? '车辆出发延误' : anomaly.event.event_type}</b>
                <div className="alert-meta"><span>{anomaly.event.object_id}</span><span>+{anomaly.event.payload.delay_s ?? 0}s</span><span>@{fmtClock(anomaly.event.occurred_at_s)}</span></div>
                <small>影响订单：{anomaly.event.payload.affected_order_ids.join('、') || '—'}</small>
                <button className="btn btn-danger btn-sm" onClick={() => navigate('events')}>进入处置</button>
              </div>
            ) : null}
          </div>

          <div className="panel">
            <div className="panel-title-row"><div><h3>车辆状态</h3><p>{selectedVehicle ? `已选中 ${selectedVehicle}` : '点击 3D 车辆查看'}</p></div></div>
            <div className="mini-list">
              {(vehicleRows.length ? vehicleRows : vehicles.map((v) => ({ vehicleId: v.vehicle_id, zone: v.temperature_zone, orderCount: 0, distanceM: 0, isAffected: false }))).map((v) => (
                <button className={`mini-row ${selectedVehicle === v.vehicleId ? 'is-active' : ''}`} key={v.vehicleId} onClick={() => setSelectedVehicle((prev) => (prev === v.vehicleId ? null : v.vehicleId))}>
                  <span className={`dot dot-${v.zone}`} /><b>{v.vehicleId}</b>
                  <small>{v.orderCount ? `${v.orderCount} 单 · ${fmtKM(v.distanceM)}` : '待命'}</small>
                  {v.isAffected ? <StatusPill tone="danger">延误</StatusPill> : <StatusPill tone={v.orderCount ? 'success' : 'neutral'}>{v.orderCount ? '配送中' : '待命'}</StatusPill>}
                </button>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-title-row"><div><h3>调度状态</h3><p>OR-Tools 真实求解结果</p></div><StatusPill tone={bootPhase === 'ready' ? 'success' : 'warning'}>{bootPhase === 'ready' ? 'Ready' : bootPhase}</StatusPill></div>
            <div className="validation">
              <div><span>当前 Plan</span><b>{currentPlan ? `${currentPlan.plan_id} · v${currentPlan.version}` : '—'}</b></div>
              <div><span>Routing</span><b>{currentPlan?.routing.metadata?.status ?? '—'}</b></div>
              <div><span>Warehouse</span><b>{currentPlan?.warehouse.metadata?.status ?? '—'}</b></div>
              <div><span>独立验证</span><b>{currentPlan?.validation.status ?? '—'}</b></div>
              <div><span>受影响订单</span><b>{affectedOrders.length ? affectedOrders.join('、') : '—'}</b></div>
              <div><span>仿真</span><b>{simulation ? `完成 · ${simulation.simulation_id}` : '未运行'}</b></div>
            </div>
          </div>
        </aside>
      </div>

      <div className="panel timeline-panel">
        <div className="panel-title-row"><div><h3>仿真时间轴</h3><p>0 – {horizonS}s，异常事件在真实发生时刻标记</p></div>
          <div className="tl-actions">
            {clock.playing ? <button className="btn btn-ghost btn-sm" onClick={clock.pause}>暂停</button> : <button className="btn btn-ghost btn-sm" onClick={clock.play}>播放</button>}
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('simulations')}>进入回放</button>
          </div>
        </div>
        <div className="sim-track">
          <div className="track">
            <span className="marker marker-start" />
            {[anomaly.event, ...(simulation?.emitted_events ?? [])].filter(Boolean).map((event) => (
              <span key={(event as { event_id: string }).event_id} className="marker marker-event" style={{ left: `${((event as { occurred_at_s: number }).occurred_at_s / horizonS) * 100}%` }} title={(event as { event_type: string }).event_type} />
            ))}
            <span className="marker marker-end" style={{ left: '100%' }} />
            <span className="track-cursor" style={{ left: `${(clock.t / horizonS) * 100}%` }} />
          </div>
          <div className="track-labels"><span>0s</span><span>900s</span><span>{horizonS}s</span></div>
        </div>
      </div>
    </div>
  );
}
