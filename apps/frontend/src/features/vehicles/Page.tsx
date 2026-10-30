import PgResourcePanel from '../postgres/ResourcePanel';

import { useMemo, useState } from 'react';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { fmtClock, fmtDur, fmtKM } from '../../lib/format';

export default function Page() {
  const { snapshot, baselinePlan, anomalyResult, runBaseline } = useApp();
  const activePlan = anomalyResult?.replanned_plan ?? baselinePlan;
  const [running, setRunning] = useState(false);
  const vehicles = snapshot?.vehicles ?? [];
  const [expanded, setExpanded] = useState<string | null>(null);

  const routes = useMemo(() => new Map((activePlan?.routing.routes ?? []).map((r) => [r.vehicle_id, r])), [activePlan]);
  const returns = useMemo(() => new Map((activePlan?.routing.warehouse_arrivals ?? []).map((a) => [a.vehicle_id, a])), [activePlan]);
  const affectedVehicles = new Set(anomalyResult?.impact.affected_vehicle_ids ?? []);
  const changedVehicles = new Set(anomalyResult?.diff.changed_vehicle_ids ?? []);

  async function runRouting() { setRunning(true); try { await runBaseline(); } finally { setRunning(false); } }

  return <div>
    <PgResourcePanel kind="vehicles" />
    <div className="section-head"><div className="head-actions" style={{ marginLeft: 'auto' }}><StatusPill tone={activePlan ? 'success' : 'warning'}>{activePlan ? `Routing ${activePlan.routing.metadata?.status ?? '—'}` : '尚未求解'}</StatusPill><button className="btn btn-primary btn-sm" disabled={!snapshot || running} onClick={() => void runRouting()}>{running ? 'Routing 求解中…' : activePlan ? '重新规划路线' : '运行 OR-Tools Routing'}</button></div></div>

    <div className="kpi-grid">
      <KpiCard label="车辆总数" value={`${vehicles.length}`} sub="当前快照" icon="truck" />
      <KpiCard label="投入配送" value={`${[...routes.values()].filter((r) => r.stops.some((s) => s.stop_kind === 'delivery')).length}`} sub="承担配送任务" icon="route" tone="neutral" />
      <KpiCard label="总运输距离" value={activePlan ? fmtKM([...routes.values()].reduce((n, r) => n + r.distance_m, 0)) : '—'} sub="Routing 真实结果" icon="chart" tone="green" />
      <KpiCard label="受影响车辆" value={`${affectedVehicles.size}`} sub={affectedVehicles.size ? [...affectedVehicles].join('、') : '无'} icon="alert" tone={affectedVehicles.size ? 'orange' : 'green'} />
    </div>

    <div className="panel">
      <div className="panel-title-row"><div><h3>车队路线详情</h3><p>停靠序列、装载量与到达时刻均来自 VehicleRoute 真实字段</p></div></div>
      <div className="fleet-grid">
        {vehicles.map((v) => {
          const route = routes.get(v.vehicle_id);
          const ret = returns.get(v.vehicle_id);
          const deliveries = route?.stops.filter((s) => s.stop_kind === 'delivery') ?? [];
          const isAffected = affectedVehicles.has(v.vehicle_id);
          const isChanged = changedVehicles.has(v.vehicle_id);
          const open = expanded === v.vehicle_id;
          return (
            <div className={`fleet-card ${open ? 'is-open' : ''}`} key={v.vehicle_id}>
              <button className="fleet-head" onClick={() => setExpanded(open ? null : v.vehicle_id)}>
                <span className={`dot dot-${v.temperature_zone}`} />
                <div className="fleet-id"><b>{v.vehicle_id}</b><small>{v.warehouse_id} · {v.temperature_zone === 'chilled' ? '冷藏' : '冷冻'}</small></div>
                <div className="fleet-quick">
                  <span>{deliveries.length} 个配送点</span>
                  <span>{route ? fmtKM(route.distance_m) : '—'}</span>
                  <span>{route ? fmtDur(route.duration_s) : '—'}</span>
                </div>
                {isAffected ? <StatusPill tone="danger">延误</StatusPill> : isChanged ? <StatusPill tone="warning">已重排</StatusPill> : route ? <StatusPill tone="success">执行中</StatusPill> : <StatusPill tone="neutral">待命</StatusPill>}
              </button>
              {open && (
                <div className="fleet-body">
                  <div className="validation">
                    <div><span>出发仓库</span><b>{v.start_node_id} → {v.end_node_id}</b></div>
                    <div><span>载重</span><b>{deliveries.reduce((n, s) => n + s.load_weight_kg, 0)} / {v.capacity_weight_kg} kg</b></div>
                    <div><span>容积</span><b>{deliveries.reduce((n, s) => n + s.load_volume_l, 0)} / {v.capacity_volume_l} L</b></div>
                    <div><span>班次窗口</span><b>{fmtClock(v.shift_window.start_s)} – {fmtClock(v.shift_window.end_s)}</b></div>
                    <div><span>返回仓库</span><b>{ret ? fmtClock(ret.arrival_at_s) : '—'}</b></div>
                  </div>
                  <div className="stop-timeline">
                    {(route?.stops ?? []).map((s, i) => (
                      <div className={`stop-item stop-${s.stop_kind}`} key={`${v.vehicle_id}-${i}`}>
                        <span className="stop-time">{fmtClock(s.stop_kind === 'depot_end' ? s.arrival_at_s : s.departure_at_s)}</span>
                        <span className="stop-dot" />
                        <div className="stop-info">
                          <b>{s.node_id}{s.stop_kind === 'depot_start' ? '（出发）' : s.stop_kind === 'depot_end' ? '（返回）' : ''}</b>
                          <small>
                            {s.order_ids.length ? `订单 ${s.order_ids.join('、')} · ` : ''}
                            {s.stop_kind === 'depot_end' ? `到达 ${fmtClock(s.arrival_at_s)}` : `到达 ${fmtClock(s.arrival_at_s)} · 离开 ${fmtClock(s.departure_at_s)}`}
                            {' · '}{s.load_weight_kg}kg
                          </small>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  </div>;
}
