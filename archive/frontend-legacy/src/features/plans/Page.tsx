
import { useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { fmtClock, fmtKM } from '../../lib/format';
import type { CoordinatedPlan } from '../../appTypes';

export default function Page() {
  const { snapshot, baselinePlan, anomalyResult, runBaseline } = useApp();
  const activePlan = anomalyResult?.replanned_plan ?? baselinePlan;
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [solveMode, setSolveMode] = useState<'sequential' | 'deep'>('deep');
  const vehicles = snapshot?.vehicles ?? [];
  const orders = snapshot?.orders ?? [];

  async function runJointSolve() {
    setRunning(true); setRunError(null);
    try { await runBaseline({ mode: solveMode, budgetMs: solveMode === 'deep' ? 90000 : 60000 }); }
    catch (error) { setRunError(error instanceof Error ? error.message : String(error)); }
    finally { setRunning(false); }
  }
  const audit = (activePlan as CoordinatedPlan | null)?.coordination;
  function exportJointEvidence() {
    if (!audit || !activePlan || !snapshot) return;
    const evidence = {
      evidence_type: 'r17-warehouse-transport-deep-coordination',
      exported_at: new Date().toISOString(),
      note: '本文件保存同一规划任务的轮次指标和最终完整方案，不包含未被采纳轮次的全部路线。必须用同一场景、同一总预算另做正式对照。',
      snapshot,
      plan: activePlan,
      coordination: audit,
    };
    const blob = new Blob([JSON.stringify(evidence, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `r17_joint_${snapshot.snapshot_id}_${Date.now()}.json`;
    document.body.appendChild(link); link.click(); link.remove();
    URL.revokeObjectURL(url);
  }

  const handoffByOrder = useMemo(
    () => new Map((activePlan?.warehouse.warehouse_handoffs ?? []).map((h) => [h.order_id, h])),
    [activePlan],
  );
  const snapshotOpMeta = useMemo(
    () => new Map((snapshot?.operations ?? []).map((op) => [op.operation_id, op])),
    [snapshot],
  );
  const opsByOrder = useMemo(() => {
    const map = new Map<string, { start: number; end: number; kind: string }[]>();
    for (const op of activePlan?.warehouse.operations ?? []) {
      const meta = snapshotOpMeta.get(op.operation_id);
      for (const oid of meta?.order_ids ?? []) {
        map.set(oid, [...(map.get(oid) ?? []), { start: op.start_s, end: op.end_s, kind: meta?.operation_kind ?? 'operation' }]);
      }
    }
    return map;
  }, [activePlan, snapshotOpMeta]);

  const vehicleChains = useMemo(() => {
    return (activePlan?.routing.routes ?? []).map((route) => {
      const vehicle = vehicles.find((v) => v.vehicle_id === route.vehicle_id);
      const depotDeparture = route.stops[0]?.departure_at_s ?? null;
      const deliveries = route.stops.filter((s) => s.stop_kind === 'delivery');
      const orderIds = deliveries.flatMap((s) => s.order_ids);
      const rows = orderIds.map((oid) => {
        const handoff = handoffByOrder.get(oid);
        const ops = opsByOrder.get(oid) ?? [];
        const prepStart = ops.length ? Math.min(...ops.map((op) => op.start)) : null;
        const stop = route.stops.find((s) => s.order_ids.includes(oid));
        const check = handoff != null && depotDeparture != null
          ? (depotDeparture >= handoff.ready_at_s && depotDeparture >= handoff.loading_window.start_s && depotDeparture <= handoff.loading_window.end_s)
          : null;
        return {
          orderId: oid,
          zone: orders.find((o) => o.order_id === oid)?.temperature_zone ?? 'chilled',
          prepStart,
          readyAtS: handoff?.ready_at_s ?? null,
          loading: handoff ? { start: handoff.loading_window.start_s, end: handoff.loading_window.end_s } : null,
          departureS: depotDeparture,
          arrivalS: stop?.arrival_at_s ?? null,
          check,
        };
      });
      const ret = activePlan?.routing.warehouse_arrivals.find((a) => a.vehicle_id === route.vehicle_id);
      return { route, vehicle, rows, returnS: ret?.arrival_at_s ?? null, depotDeparture };
    });
  }, [activePlan, vehicles, handoffByOrder, opsByOrder, orders]);

  const allChecks = vehicleChains.flatMap((vc) => vc.rows.map((r) => r.check)).filter((c) => c != null) as boolean[];
  const checksPassed = allChecks.filter(Boolean).length;
  const totalOrdersChained = vehicleChains.reduce((n, vc) => n + vc.rows.length, 0);

  return <div>
    <SectionHeader title="联合调度 · 仓运协同" desc="仓储排程（CP-SAT）与运输路径（OR-Tools Routing）在同一个时间轴上闭合：备货完成 → 装车窗口 → 车辆出发 → 配送 → 返回。"
      actions={<div className="section-actions">
        <StatusPill tone={activePlan ? (activePlan.validation.status === 'passed' ? 'success' : 'danger') : 'warning'}>{activePlan ? `验证 ${activePlan.validation.status}` : '尚未求解'}</StatusPill>
        <label style={{ fontSize: 12 }}>求解模式 <select aria-label="联合优化模式" value={solveMode} disabled={running} onChange={(e) => setSolveMode(e.target.value as 'sequential' | 'deep')}>
          <option value="deep">深度双向协同（最多 90 秒）</option><option value="sequential">单轮仓运衔接（60 秒）</option>
        </select></label>
        <button className="btn btn-primary btn-sm" disabled={!snapshot || running} onClick={() => void runJointSolve()}>{running ? '方案求解中…' : activePlan ? '运行新一轮调度' : '运行仓运联合调度'}</button>
      </div>} />

    {runError && <div className="panel" role="alert" style={{ borderColor: 'var(--danger, #c55)' }}><b>求解未成功</b><p>{runError}</p><p>先前已经验证的方案不会被覆盖。</p></div>}
    {audit && <div className="panel" style={{ marginBottom: 16 }}>
      <div className="panel-title-row"><div><h3>R17 双向协同 · 可追溯求解证据</h3><p>以已通过独立校验的初始方案为保底；车辆发车时间反馈给 CP-SAT 后，仅采纳再次验证且综合目标更优的仓运方案。</p></div>
        <div className="section-actions"><StatusPill tone="success">{audit.mode === 'deep' ? '深度协同' : '单轮模式'} · 第 {audit.selected_round} 轮入选</StatusPill><button className="btn btn-secondary btn-sm" type="button" onClick={exportJointEvidence}>导出仓运协同 JSON 证据</button></div></div>
      <div className="kpi-grid">
        <KpiCard label="运输距离变化" value={`${fmtKM(audit.baseline_distance_m)} → ${fmtKM(audit.selected_distance_m)}`} sub="同一次求解内初始方案 vs 最终入选方案" icon="route" tone="green" />
        <KpiCard label="备货完成→车辆出发总等待" value={`${Math.round(audit.baseline_handoff_wait_s / 60)} → ${Math.round(audit.selected_handoff_wait_s / 60)} 分钟`} sub="按每个已服务订单累计；不是车辆排队时间" icon="check" tone="neutral" />
        <KpiCard label="实际尝试轮次" value={`${audit.attempted_rounds} / ${audit.requested_rounds}`} sub="受全局预算约束，可能提前终止" icon="route" />
        <KpiCard label="校验结果" value={activePlan?.validation.status === 'passed' ? '通过' : '未通过'} sub="仓储、运输及跨域规则独立校验" icon="check" tone="green" />
      </div>
      <div className="table-wrap"><table><thead><tr><th>轮次</th><th>阶段</th><th>采纳</th><th>路线距离</th><th>交接等待</th><th>仓储完成最晚时刻</th><th>CP-SAT / Routing</th><th>原因</th></tr></thead><tbody>
        {audit.rounds.map((step) => <tr key={step.round_number}>
          <td>#{step.round_number}</td><td>{step.stage === 'initial' ? '初始可行解' : '运输反馈→仓储重排→运输重算'}</td>
          <td><StatusPill tone={step.accepted ? 'success' : 'warning'}>{step.accepted ? '采纳' : '保留原方案'}</StatusPill></td>
          <td>{step.distance_m == null ? '—' : fmtKM(step.distance_m)}</td>
          <td>{step.total_handoff_wait_s == null ? '—' : `${(step.total_handoff_wait_s / 60).toFixed(1)} 分`}</td>
          <td>{step.warehouse_makespan_s == null ? '—' : fmtClock(step.warehouse_makespan_s)}</td>
          <td>{step.routing_solve_ms == null ? '—' : `${step.warehouse_solve_ms ?? 0} / ${step.routing_solve_ms} ms`}</td>
          <td>{step.reason}</td>
        </tr>)}</tbody></table></div>
      <p className="scope-note">优先级：未服务订单数 → 运输距离 → 订单级交接等待 → 仓储完工时间 → 路线时长。仅比较同一快照、同一约束下真实计算的候选方案；不承诺每一轮都会改善距离。R16 的 B-06 快检/标准评测仍使用单轮模式，历史统计口径不变。</p>
    </div>}

    <div className="kpi-grid">
      <KpiCard label="协同订单" value={`${totalOrdersChained}`} sub="同时具备仓储与运输计划" icon="package" tone="neutral" />
      <KpiCard label="协同链路" value={`${vehicleChains.length}`} sub="按车辆组织" icon="route" />
      <KpiCard label="衔接检查" value={allChecks.length ? `${checksPassed} / ${allChecks.length}` : '—'} sub="车辆出发处于交接时间窗内" icon="check" tone={allChecks.length && checksPassed === allChecks.length ? 'green' : 'orange'} />
      <KpiCard label="总运输距离" value={activePlan ? fmtKM((activePlan.routing.routes ?? []).reduce((n, r) => n + (r.distance_m ?? 0), 0)) : '—'} sub="Routing 结果" icon="truck" tone="green" />
    </div>

    {!activePlan && <div className="empty-state"><div className="empty-icon">◎</div><h3>等待调度方案</h3><p>驾驶舱完成基线求解后，这里将展示完整的仓运协同链路。</p></div>}

    {vehicleChains.map(({ route, vehicle, rows, returnS }) => (
      <div className="panel" key={route.vehicle_id} style={{ marginBottom: 16 }}>
        <div className="panel-title-row">
          <div><h3>{route.vehicle_id} 协同链路</h3><p>{vehicle?.warehouse_id ?? '—'} · {vehicle?.temperature_zone === 'frozen' ? '冷冻' : '冷藏'} · {fmtKM(route.distance_m)} · 全程 {fmtClock(route.stops[0]?.departure_at_s ?? 0)} → {returnS != null ? fmtClock(returnS) : '—'}</p></div>
          <div className="chips-inline">
            <span className="soft-badge">{rows.length} 订单</span>
            <span className="soft-badge">{route.stops.filter((s) => s.stop_kind === 'delivery').length} 配送点</span>
          </div>
        </div>
        <div className="joint-chain">
          <div className="joint-node joint-origin"><b>{vehicle?.warehouse_id ?? '仓库'}</b><small>备货 + 装车</small></div>
          {rows.map((row) => (
            <div className="joint-node" key={row.orderId}>
              <span className={`zone zone-${row.zone}`}>{row.zone === 'chilled' ? '冷藏' : '冷冻'}</span>
              <b>{row.orderId}</b>
              <small>备货 {row.prepStart != null ? fmtClock(row.prepStart) : '—'}<br />就绪 {row.readyAtS != null ? fmtClock(row.readyAtS) : '—'}<br />送达 {row.arrivalS != null ? fmtClock(row.arrivalS) : '—'}</small>
              {row.check != null && <i className={row.check ? 'joint-ok' : 'joint-bad'}>{row.check ? '✓ 衔接' : '✕ 冲突'}</i>}
            </div>
          ))}
          <div className="joint-node joint-origin"><b>{vehicle?.warehouse_id ?? '仓库'}</b><small>{returnS != null ? `${fmtClock(returnS)} 返回` : '—'}</small></div>
        </div>
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table>
            <thead><tr><th>订单</th><th>备货开始</th><th>备货完成</th><th>装车窗口</th><th>车辆出发</th><th>送达时刻</th><th>衔接检查</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.orderId}>
                  <td><strong>{row.orderId}</strong></td>
                  <td>{row.prepStart != null ? fmtClock(row.prepStart) : '—'}</td>
                  <td>{row.readyAtS != null ? fmtClock(row.readyAtS) : '—'}</td>
                  <td>{row.loading ? `${fmtClock(row.loading.start)} – ${fmtClock(row.loading.end)}` : '—'}</td>
                  <td>{row.departureS != null ? fmtClock(row.departureS) : '—'}</td>
                  <td>{row.arrivalS != null ? fmtClock(row.arrivalS) : '—'}</td>
                  <td>{row.check == null ? '—' : row.check ? <StatusPill tone="success">装车先于出发</StatusPill> : <StatusPill tone="danger">窗口冲突</StatusPill>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    ))}
  </div>;
}
