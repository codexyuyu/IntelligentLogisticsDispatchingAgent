
import { useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { fmtClock } from '../../lib/format';

export default function Page() {
  const { snapshot, baselinePlan, anomalyResult, runBaseline } = useApp();
  const activePlan = anomalyResult?.replanned_plan ?? baselinePlan;
  const [running, setRunning] = useState(false);
  const warehouses = snapshot?.warehouses ?? [];
  const resources = snapshot?.resources ?? [];
  const snapshotOps = useMemo(() => new Map((snapshot?.operations ?? []).map((op) => [op.operation_id, op])), [snapshot]);
  const scheduled = activePlan?.warehouse.operations ?? [];
  const handoffs = activePlan?.warehouse.warehouse_handoffs ?? [];

  const domainEnd = useMemo(
    () => Math.max(3600, ...scheduled.map((op) => op.end_s), ...handoffs.map((h) => h.loading_window.end_s)),
    [scheduled, handoffs],
  );

  const conflicts = useMemo(() => {
    const byResource = new Map<string, { start: number; end: number; id: string }[]>();
    for (const op of scheduled) {
      byResource.set(op.resource_id, [...(byResource.get(op.resource_id) ?? []), { start: op.start_s, end: op.end_s, id: op.operation_id }]);
    }
    const hits: string[] = [];
    byResource.forEach((ops, resourceId) => {
      const sorted = [...ops].sort((a, b) => a.start - b.start);
      for (let i = 1; i < sorted.length; i += 1) {
        if (sorted[i].start < sorted[i - 1].end) hits.push(`${resourceId}: ${sorted[i - 1].id} 与 ${sorted[i].id} 重叠`);
      }
    });
    return hits;
  }, [scheduled]);

  const opAffected = (opId: string) => {
    const meta = snapshotOps.get(opId);
    return (meta?.order_ids ?? []).some((oid) => anomalyResult?.impact.affected_order_ids.includes(oid));
  };

  async function runWarehouseSolve() {
    setRunning(true);
    try { await runBaseline(); } finally { setRunning(false); }
  }

  return <div>
    <SectionHeader title="仓储排程"
      actions={<div className="section-actions"><StatusPill tone={activePlan ? 'success' : 'warning'}>{activePlan ? `CP-SAT ${activePlan.warehouse.metadata?.status ?? '—'}` : '尚未求解'}</StatusPill><button className="btn btn-primary btn-sm" disabled={!snapshot || running} onClick={() => void runWarehouseSolve()}>{running ? 'CP-SAT 求解中…' : activePlan ? '重新运行仓储排程' : '运行 CP-SAT 排程'}</button></div>} />

    <div className="kpi-grid">
      <KpiCard label="仓库节点" value={`${warehouses.length}`} sub="双温区冷链中心" icon="warehouse" />
      <KpiCard label="作业资源" value={`${resources.length}`} sub="dock / 冷间资源" icon="grid" tone="neutral" />
      <KpiCard label="已排程作业" value={`${scheduled.length}`} sub={baselinePlan ? `求解 ${baselinePlan.warehouse.metadata?.solve_ms ?? '—'} ms` : '等待方案'} icon="check" tone="green" />
      <KpiCard label="资源冲突" value={`${conflicts.length}`} sub={conflicts.length ? '检测到重叠' : '排程无重叠'} icon="alert" tone={conflicts.length ? 'red' : 'green'} />
    </div>

    <div className="card-grid two">
      {warehouses.map((w) => {
        const rs = resources.filter((r) => r.warehouse_id === w.warehouse_id);
        return <div className="panel warehouse-card" key={w.warehouse_id}>
          <div className="warehouse-top">
            <div><span className="warehouse-mark"><span /></span><div><h3>{w.warehouse_id}</h3><p>{w.node_id}</p></div></div>
            <div className="chips-inline">{w.temperature_zones.map((z) => <span key={z} className={`zone zone-${z}`}>{z === 'chilled' ? '冷藏' : '冷冻'}</span>)}</div>
          </div>
          <div className="resource-list">
            {rs.map((r) => (
              <div className="resource-row" key={r.resource_id}>
                <span><b>{r.resource_id}</b> · {r.resource_kind}</span>
                <span>容量 {r.capacity_units}</span>
                <span>{r.unavailable_windows.length ? `${r.unavailable_windows.length} 个不可用窗口` : '全天可用'}</span>
              </div>
            ))}
          </div>
        </div>;
      })}
    </div>

    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-title-row"><div><h3>作业排程时间轴</h3></div><span className="soft-badge">{scheduled.length ? `窗口 0 – ${fmtClock(domainEnd)}` : '等待方案'}</span></div>
      {scheduled.length ? (
        <div className="gantt">
          {[...new Set(scheduled.map((op) => op.resource_id))].map((resourceId) => {
            const ops = scheduled.filter((op) => op.resource_id === resourceId).sort((a, b) => a.start_s - b.start_s);
            const resource = resources.find((r) => r.resource_id === resourceId);
            return (
              <div className="gantt-row" key={resourceId}>
                <div className="gantt-label"><b>{resourceId}</b><small>{resource?.resource_kind ?? ''}</small></div>
                <div className="gantt-lane">
                  {ops.map((op) => {
                    const meta = snapshotOps.get(op.operation_id);
                    const affected = opAffected(op.operation_id);
                    return (
                      <div
                        key={op.operation_id}
                        className={`gantt-bar ${meta?.operation_kind === 'loading' ? 'is-loading' : 'is-prep'} ${affected ? 'is-affected' : ''}`}
                        style={{ left: `${(op.start_s / domainEnd) * 100}%`, width: `${Math.max(1.2, ((op.end_s - op.start_s) / domainEnd) * 100)}%` }}
                        title={`${op.operation_id}\n${meta?.operation_kind ?? 'operation'} · 订单 ${meta?.order_ids.join('、') ?? '—'}\n${fmtClock(op.start_s)} → ${fmtClock(op.end_s)}`}
                      >
                        <span>{meta?.order_ids.length ? meta.order_ids.map((o) => o.replace('ord_', 'O')).join(' ') : op.operation_id}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
          <div className="gantt-axis"><span>0s</span><span>{fmtClock(domainEnd / 4)}</span><span>{fmtClock(domainEnd / 2)}</span><span>{fmtClock((domainEnd * 3) / 4)}</span><span>{fmtClock(domainEnd)}</span></div>
          <div className="gantt-legend">
            <span><i className="legend-dot chilled" />备货 / 冷间作业</span>
            <span><i className="legend-dot route" />装车作业</span>
            <span><i className="legend-dot warning" />涉及受影响订单</span>
          </div>
        </div>
      ) : null}
    </div>

    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-title-row"><div><h3>装车交接窗口</h3></div><span className="soft-badge">{handoffs.length} 项</span></div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>订单</th><th>仓库</th><th>备货完成</th><th>装车窗口</th><th>窗口时长</th></tr></thead>
          <tbody>
            {handoffs.map((h) => (
              <tr key={`${h.order_id}-${h.warehouse_id}`}>
                <td><strong>{h.order_id}</strong></td>
                <td>{h.warehouse_id}</td>
                <td>{fmtClock(h.ready_at_s)}</td>
                <td>{fmtClock(h.loading_window.start_s)} – {fmtClock(h.loading_window.end_s)}</td>
                <td>{h.loading_window.end_s - h.loading_window.start_s} s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  </div>;
}
