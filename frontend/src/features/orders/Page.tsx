import PgResourcePanel from '../postgres/ResourcePanel';

import { useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { fmtClock, fmtDur } from '../../lib/format';

export default function Page() {
  const { snapshot, baselinePlan, anomalyResult } = useApp();
  const activePlan = anomalyResult?.replanned_plan ?? baselinePlan;
  const [zoneFilter, setZoneFilter] = useState<'all' | 'chilled' | 'frozen'>('all');
  const [activeOrder, setActiveOrder] = useState<string | null>(null);

  const orders = snapshot?.orders ?? [];
  const vehicles = snapshot?.vehicles ?? [];

  const chainIndex = useMemo(() => {
    // order_id -> {vehicle, stop, ops, handoff, returnArrival}
    const map = new Map<string, {
      vehicleId: string | null; warehouseId: string | null; arrivalS: number | null; serviceStartS: number | null;
      opIds: string[]; readyAtS: number | null; loading: { start: number; end: number } | null; returnS: number | null;
    }>();
    if (!activePlan) return map;
    const opMeta = new Map((snapshot?.operations ?? []).map((op) => [op.operation_id, op]));
    const opsByOrder = new Map<string, string[]>();
    for (const op of activePlan.warehouse.operations) {
      const meta = opMeta.get(op.operation_id);
      for (const oid of meta?.order_ids ?? []) {
        opsByOrder.set(oid, [...(opsByOrder.get(oid) ?? []), op.operation_id]);
      }
    }
    const handoffByOrder = new Map(activePlan.warehouse.warehouse_handoffs.map((h) => [h.order_id, h]));
    const stopByOrder = new Map<string, { vehicleId: string; arrivalS: number; serviceStartS: number }>();
    for (const route of activePlan.routing.routes) {
      for (const stop of route.stops) {
        for (const oid of stop.order_ids) {
          stopByOrder.set(oid, { vehicleId: route.vehicle_id, arrivalS: stop.arrival_at_s, serviceStartS: stop.service_start_at_s });
        }
      }
    }
    const returnByVehicle = new Map(activePlan.routing.warehouse_arrivals.map((a) => [a.vehicle_id, a.arrival_at_s]));
    for (const order of orders) {
      const stop = stopByOrder.get(order.order_id);
      const handoff = handoffByOrder.get(order.order_id);
      map.set(order.order_id, {
        vehicleId: stop?.vehicleId ?? null,
        warehouseId: order.warehouse_id,
        arrivalS: stop?.arrivalS ?? null,
        serviceStartS: stop?.serviceStartS ?? null,
        opIds: opsByOrder.get(order.order_id) ?? [],
        readyAtS: handoff?.ready_at_s ?? null,
        loading: handoff ? { start: handoff.loading_window.start_s, end: handoff.loading_window.end_s } : null,
        returnS: stop ? returnByVehicle.get(stop.vehicleId) ?? null : null,
      });
    }
    return map;
  }, [activePlan, snapshot, orders, vehicles]);

  const affectedOrders = new Set(anomalyResult?.impact.affected_order_ids ?? []);
  const servedOrders = new Set([...chainIndex.entries()].filter(([, v]) => v.vehicleId).map(([k]) => k));
  const unservedIds = new Set(activePlan?.routing.unserved_orders.map((u) => u.order_id) ?? []);

  const filtered = orders.filter((o) => zoneFilter === 'all' || o.temperature_zone === zoneFilter);
  const active = activeOrder ? orders.find((o) => o.order_id === activeOrder) : null;
  const activeChain = activeOrder ? chainIndex.get(activeOrder) : null;
  const activeStop = useMemo(() => {
    if (!activeOrder || !activePlan) return null;
    for (const route of activePlan.routing.routes) {
      const stop = route.stops.find((s) => s.order_ids.includes(activeOrder));
      if (stop) return { vehicleId: route.vehicle_id, stop };
    }
    return null;
  }, [activeOrder, activePlan]);

  return <div>
    <PgResourcePanel kind="orders" />
    <SectionHeader title="订单与库存" desc="订单、温区、时间窗与调度状态实时联动；点击任意订单查看从仓储作业到配送签收的完整链路。"
      actions={<div className="seg">
        {(['all', 'chilled', 'frozen'] as const).map((z) => <button key={z} className={`seg-btn ${zoneFilter === z ? 'is-active' : ''}`} onClick={() => setZoneFilter(z)}>{z === 'all' ? '全部' : z === 'chilled' ? '冷藏' : '冷冻'}</button>)}
      </div>} />

    <div className="kpi-grid">
      <KpiCard label="订单总数" value={`${orders.length}`} sub="当前快照" icon="package" />
      <KpiCard label="冷藏 / 冷冻" value={`${orders.filter((o) => o.temperature_zone === 'chilled').length} / ${orders.filter((o) => o.temperature_zone === 'frozen').length}`} sub="双温区覆盖" icon="clock" tone="neutral" />
      <KpiCard label="已纳入路线" value={`${servedOrders.size}`} sub={activePlan ? `${unservedIds.size} 未服务` : '等待基线方案'} icon="truck" tone="green" />
      <KpiCard label="受异常影响" value={`${affectedOrders.size}`} sub={affectedOrders.size ? [...affectedOrders].join('、') : '无'} icon="alert" tone={affectedOrders.size ? 'orange' : 'green'} />
    </div>

    <div className="panel">
      <div className="panel-title-row"><div><h3>订单清单</h3></div><span className="soft-badge">{activePlan ? '方案已联动' : '等待基线方案'}</span></div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>订单</th><th>仓库</th><th>批次</th><th>温区</th><th>数量</th><th>服务时间窗</th><th>当前车辆</th><th>送达时刻</th><th>状态</th></tr></thead>
          <tbody>
            {filtered.map((o) => {
              const chain = chainIndex.get(o.order_id);
              const affected = affectedOrders.has(o.order_id);
              const unserved = unservedIds.has(o.order_id);
              return (
                <tr key={o.order_id} className={activeOrder === o.order_id ? 'is-active' : ''} onClick={() => setActiveOrder(activeOrder === o.order_id ? null : o.order_id)}>
                  <td><strong>{o.order_id}</strong></td>
                  <td>{o.warehouse_id}</td>
                  <td>{o.batch_id}</td>
                  <td><span className={`zone zone-${o.temperature_zone}`}>{o.temperature_zone === 'chilled' ? '冷藏' : '冷冻'}</span></td>
                  <td>{o.quantity_units} 件 · {o.weight_kg}kg</td>
                  <td>{fmtClock(o.service_window.start_s)} – {fmtClock(o.service_window.end_s)}</td>
                  <td>{chain?.vehicleId ?? '—'}</td>
                  <td>{chain?.arrivalS != null ? fmtClock(chain.arrivalS) : '—'}</td>
                  <td>{unserved ? <StatusPill tone="danger">未服务</StatusPill> : affected ? <StatusPill tone="warning">受异常影响</StatusPill> : <StatusPill tone="success">已排程</StatusPill>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>

    {active && (
      <div className="drawer-mask" onClick={() => setActiveOrder(null)}>
        <aside className="drawer" onClick={(e) => e.stopPropagation()}>
          <div className="drawer-head">
            <div><h3>{active.order_id} 完整调度链路</h3></div>
            <button className="icon-btn" onClick={() => setActiveOrder(null)}>✕</button>
          </div>
          <div className="chain">
            <div className="chain-node"><span className="chain-tag">订单</span><div><b>{active.order_id}</b><small>{active.quantity_units} 件 · {active.weight_kg}kg · {active.volume_l}L · {active.temperature_zone === 'chilled' ? '冷藏' : '冷冻'}</small></div></div>
            <div className="chain-node"><span className="chain-tag">仓库</span><div><b>{active.warehouse_id}</b><small>批次 {active.batch_id} · 新鲜度截止 {fmtClock(active.freshness_deadline_s)}</small></div></div>
            <div className="chain-node"><span className="chain-tag">仓储作业</span><div><b>{activeChain?.opIds.length ? `${activeChain.opIds.length} 项作业` : '—'}</b><small>{activeChain?.opIds.join('、') || '等待方案'}</small></div></div>
            <div className="chain-node"><span className="chain-tag">备货完成</span><div><b>{activeChain?.readyAtS != null ? fmtClock(activeChain.readyAtS) : '—'}</b><small>warehouse_handoffs.ready_at_s</small></div></div>
            <div className="chain-node"><span className="chain-tag">装车窗口</span><div><b>{activeChain?.loading ? `${fmtClock(activeChain.loading.start)} – ${fmtClock(activeChain.loading.end)}` : '—'}</b><small>loading_window</small></div></div>
            <div className="chain-node"><span className="chain-tag">车辆出发</span><div><b>{activeStop ? fmtClock(activeStop.stop.departure_at_s) : '—'}</b><small>{activeChain?.vehicleId ?? '未分配'} · depot 出发</small></div></div>
            <div className="chain-node"><span className="chain-tag">送达</span><div><b>{activeStop ? fmtClock(activeStop.stop.arrival_at_s) : '—'}</b><small>节点 {activeStop?.stop.node_id ?? '—'} · 服务开始 {activeChain?.serviceStartS != null ? fmtClock(activeChain.serviceStartS) : '—'}</small></div></div>
            <div className="chain-node"><span className="chain-tag">车辆返回</span><div><b>{activeChain?.returnS != null ? fmtClock(activeChain.returnS) : '—'}</b><small>{activeStop ? fmtDur(activeChain?.returnS != null && activeStop.stop.departure_at_s ? activeChain.returnS - activeStop.stop.departure_at_s : null) : ''}全程（出发 → 返回）</small></div></div>
          </div>
          {affectedOrders.has(active.order_id) && <div className="callout callout-warn">该订单在最近一次异常处置中受到直接影响，方案可能已被局部重排。</div>}
        </aside>
      </div>
    )}
  </div>;
}
