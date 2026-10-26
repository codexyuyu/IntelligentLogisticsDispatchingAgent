
import { useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import FlowSteps, { type FlowStep } from '../../components/FlowSteps';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { fmtClock, fmtKM, fmtMs } from '../../lib/format';

const eventTypes = [
  { value: 'departure_delayed', label: '车辆出发延误', supported: true },
  { value: 'dock_unavailable', label: '月台不可用（尚未接入 B-04）', supported: false },
  { value: 'cargo_quarantined', label: '货物隔离（尚未接入 B-04）', supported: false },
  { value: 'weather_changed', label: '天气变化（尚未接入 B-04）', supported: false },
  { value: 'demand_changed', label: '需求变化（尚未接入 B-04）', supported: false },
] as const;

export default function Page() {
  const { anomaly, anomalyResult, injectAnomaly, resetAnomaly, snapshot } = useApp();
  const [type, setType] = useState<(typeof eventTypes)[number]['value']>('departure_delayed');
  const [vehicle, setVehicle] = useState('veh_1');
  const [affected, setAffected] = useState('ord_001');
  const [occurred, setOccurred] = useState(900);
  const [delay, setDelay] = useState(900);
  const [running, setRunning] = useState(false);

  async function submit() {
    setRunning(true);
    try {
      await injectAnomaly({
        eventType: type,
        objectId: vehicle,
        orderIds: affected.split(',').map((s) => s.trim()).filter(Boolean),
        occurredAtS: occurred,
        delayS: delay,
      });
    } finally {
      setRunning(false);
    }
  }

  const accepted = anomaly.accepted;
  const event = anomaly.event;
  const impact = anomalyResult?.impact;
  const diff = anomalyResult?.diff;
  const newPlan = anomalyResult?.replanned_plan;
  const validation = anomalyResult?.validation;
  const totalOrders = snapshot?.orders.length ?? 0;
  const lockedCount = impact ? impact.locked_order_ids.length : Math.max(0, totalOrders - (event?.payload.affected_order_ids.length ?? 0));

  const steps: FlowStep[] = [
    { title: '异常发生与登记', desc: 'POST /api/v1/events，后端冻结事实并生成事件记录', state: anomaly.phase === 'idle' ? 'pending' : accepted ? 'done' : anomaly.phase === 'failed' ? 'failed' : 'active', detail: accepted ? `event_id=${accepted.event_id}${accepted.duplicate ? '（重复事件已去重）' : ''}` : undefined },
    { title: '影响范围识别', desc: '依据 affected_order_ids 锁定求解域，其余订单冻结', state: !impact ? (anomaly.phase === 'idle' ? 'pending' : 'active') : 'done', detail: impact ? `受影响 ${impact.affected_order_ids.length} 单 · 锁定 ${impact.locked_order_ids.length} 单 · 车辆 ${impact.affected_vehicle_ids.join(',') || '—'}` : undefined },
    { title: '局部候选调整', desc: '仅对受影响路线生成候选方案，不做全量重算', state: !diff ? (anomaly.phase === 'idle' ? 'pending' : 'active') : 'done', detail: diff ? `变更订单 ${diff.changed_order_ids.length} 个：${diff.changed_order_ids.join('、') || '—'}` : undefined },
    { title: 'OR-Tools 局部求解', desc: 'Routing + CP-SAT 在预算内重排受影响范围', state: !newPlan ? (anomaly.phase === 'idle' ? 'pending' : 'active') : newPlan.routing.metadata?.status || newPlan.warehouse.metadata?.status ? 'done' : 'active', detail: newPlan ? `Routing ${newPlan.routing.metadata?.status ?? '—'} · Warehouse ${newPlan.warehouse.metadata?.status ?? '—'} · ${fmtMs((newPlan.routing.metadata?.solve_ms ?? 0) + (newPlan.warehouse.metadata?.solve_ms ?? 0))}` : undefined },
    { title: '独立验证', desc: '统一校验器复核新方案的全部硬约束', state: !validation ? (anomaly.phase === 'idle' ? 'pending' : 'active') : validation.status === 'passed' ? 'done' : 'failed', detail: validation ? `${validation.status} · 规则 ${validation.checked_rule_ids.length} 条 · 违规 ${validation.violations.length}` : undefined },
    { title: '新 Plan 生效', desc: '版本递增，仿真继续推演', state: !newPlan ? (anomaly.phase === 'idle' ? 'pending' : 'active') : 'done', detail: newPlan ? `${newPlan.plan_id} · v${anomalyResult?.previous_plan_version ?? 1} → v${newPlan.version}` : undefined },
  ];

  return <div>
    <SectionHeader title="异常处置闭环" desc="异常登记 → 影响分析 → 局部重调度 → OR-Tools 求解 → 独立验证 → 新 Plan。前端只提交业务事件，影响范围、diff 与验证全部来自后端真实返回。"
      actions={anomaly.phase === 'idle'
        ? <button className="btn btn-danger" disabled={running} onClick={() => void submit()}>{running ? '提交中…' : '注入 veh_1 延误 900s'}</button>
        : <button className="btn btn-ghost" onClick={resetAnomaly}>重置演练</button>} />

    <div className="kpi-grid">
      <KpiCard label="事件状态" value={anomaly.phase === 'idle' ? '未注入' : anomaly.phase === 'failed' ? '失败' : anomaly.phase === 'accepted' ? '已受理' : '提交中'} sub={accepted ? accepted.event_id : 'departure_delayed · veh_1 · 900s'} icon="alert" tone={anomaly.phase === 'failed' ? 'red' : event ? 'orange' : 'green'} />
      <KpiCard label="受影响订单" value={impact ? `${impact.affected_order_ids.length}` : event ? `${event.payload.affected_order_ids.length}` : '—'} sub={impact?.affected_order_ids.join('、') || '由事件载荷声明'} icon="package" tone="neutral" />
      <KpiCard label="Plan Version" value={newPlan ? `v${newPlan.version}` : 'v1'} sub={newPlan ? `${anomalyResult?.previous_plan_version ?? 1} → ${newPlan.version}` : '基线方案'} icon="database" tone="green" />
      <KpiCard label="独立验证" value={validation?.status ?? '—'} sub={validation ? `规则 ${validation.checked_rule_ids.length} 条` : '待重排完成'} icon="check" tone={validation?.status === 'passed' ? 'green' : validation ? 'red' : 'neutral'} />
    </div>

    <div className="incident-grid">
      <div className="incident-col">
        <div className="panel form-panel">
          <div className="panel-title-row"><div><h3>异常注入</h3><p>目前 B-04 真实局部重排已完成并可实跑的是 departure_delayed；其他类型先明确标注未接入，避免比赛演示误操作。</p></div><StatusPill tone="warning">受控演练</StatusPill></div>
          <label>异常类型<select value={type} onChange={(e) => setType(e.target.value as typeof type)}>{eventTypes.map((x) => <option key={x.value} value={x.value} disabled={!x.supported}>{x.label}</option>)}</select></label>
          <label>异常对象（车辆）<input value={vehicle} onChange={(e) => setVehicle(e.target.value)} /></label>
          <label>受影响订单（逗号分隔）<input value={affected} onChange={(e) => setAffected(e.target.value)} /></label>
          <div className="form-grid">
            <label>发生时刻 (s)<input type="number" value={occurred} onChange={(e) => setOccurred(Number(e.target.value) || 0)} /></label>
            <label>延误时长 (s)<input type="number" value={delay} onChange={(e) => setDelay(Number(e.target.value) || 0)} /></label>
          </div>
          <button
            className="btn btn-danger"
            onClick={() => void submit()}
            disabled={running || anomaly.phase === 'submitting' || (anomaly.phase === 'accepted' && Boolean(anomalyResult))}
          >
            {running
              ? '提交中…'
              : anomaly.phase === 'failed'
                ? '重试局部重调度'
                : anomaly.phase === 'accepted' && anomalyResult
                  ? '局部重调度已完成'
                  : '登记并触发局部重调度'}
          </button>
          {anomaly.phase === 'failed' && <div className="callout callout-error">{anomaly.error}</div>}
          {!snapshot && <div className="callout">场景初始化中，请稍候。</div>}
        </div>

        {event && (
          <div className="panel">
            <div className="panel-title-row"><div><h3>异常事件卡片</h3><p>后端受理回执</p></div><StatusPill tone="danger">{event.event_type}</StatusPill></div>
            <div className="validation">
              <div><span>事件 ID</span><b>{accepted?.event_id ?? '—'}</b></div>
              <div><span>异常对象</span><b>{event.object_id}</b></div>
              <div><span>发生时刻</span><b>{fmtClock(event.occurred_at_s)}</b></div>
              <div><span>延误时长</span><b>+{event.payload.delay_s ?? 0}s</b></div>
              <div><span>影响订单</span><b>{event.payload.affected_order_ids.join('、') || '—'}</b></div>
              <div><span>重排任务</span><b>{accepted?.replanning_job_id ?? '—'}</b></div>
            </div>
          </div>
        )}

        {impact && (
          <div className="panel">
            <div className="panel-title-row"><div><h3>影响分析</h3><p>后端 ImpactAnalysis 真实输出</p></div></div>
            <div className="validation">
              <div><span>受影响订单</span><b>{impact.affected_order_ids.join('、') || '—'}</b></div>
              <div><span>锁定订单（不参与重排）</span><b>{lockedCount} 个</b></div>
              <div><span>受影响车辆</span><b>{impact.affected_vehicle_ids.join('、') || '—'}</b></div>
              <div><span>受影响路线</span><b>{impact.affected_route_ids.join('、') || '—'}</b></div>
              <div><span>识别原因</span><b className="reason-cell">{impact.reason}</b></div>
            </div>
          </div>
        )}
      </div>

      <div className="incident-col">
        <div className="panel">
          <div className="panel-title-row"><div><h3>处置流程</h3><p>每个步骤的状态与数据均来自真实 API 返回</p></div><StatusPill tone={anomaly.phase === 'failed' ? 'danger' : newPlan ? 'success' : 'info'}>{newPlan ? '闭环完成' : anomaly.phase === 'failed' ? '失败' : '等待注入'}</StatusPill></div>
          <FlowSteps steps={steps} />
        </div>

        {diff && newPlan && (
          <div className="panel">
            <div className="panel-title-row"><div><h3>局部重调度结果对比</h3><p>仅统计受影响路线，不能与全量基线直接相减</p></div></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>指标</th><th>重排前</th><th>重排后</th><th>变化</th></tr></thead>
                <tbody>
                  <tr><td><strong>受影响路线距离</strong></td><td>{fmtKM(diff.old_distance_m)}</td><td>{fmtKM(diff.new_distance_m)}</td><td>{diff.distance_delta_m >= 0 ? '+' : ''}{(diff.distance_delta_m / 1000).toFixed(1)} km</td></tr>
                  <tr><td><strong>路线总时长</strong></td><td>{fmtMs(diff.old_route_duration_s).replace('ms', 's')}</td><td>{fmtMs(diff.new_route_duration_s).replace('ms', 's')}</td><td>{diff.route_duration_delta_s >= 0 ? '+' : ''}{Math.round(diff.route_duration_delta_s / 60)} min</td></tr>
                  <tr><td><strong>变更订单</strong></td><td colSpan={2}>{diff.changed_order_ids.join('、') || '—'}</td><td>{diff.changed_order_ids.length} 个</td></tr>
                  <tr><td><strong>变更车辆</strong></td><td colSpan={2}>{diff.changed_vehicle_ids.join('、') || '—'}</td><td>{diff.changed_vehicle_ids.length} 辆</td></tr>
                  <tr><td><strong>未服务订单</strong></td><td>—</td><td>{newPlan.routing.unserved_orders.length}</td><td>{newPlan.routing.unserved_orders.length === 0 ? '全部覆盖' : '存在缺口'}</td></tr>
                </tbody>
              </table>
            </div>
            <p className="scope-note">口径说明：上表仅覆盖受影响车辆/路线的局部范围。基线 20 订单全量距离与该局部距离统计口径不同，页面不做「节省公里数」类结论。</p>
          </div>
        )}

        {newPlan && (
          <div className="panel">
            <div className="panel-title-row"><div><h3>新 Plan 求解与验证</h3><p>重排后的完整方案（局部调整 + 全局校验）</p></div><StatusPill tone={newPlan.validation.status === 'passed' ? 'success' : 'danger'}>v{newPlan.version}</StatusPill></div>
            <div className="validation">
              <div><span>Plan ID</span><b>{newPlan.plan_id}</b></div>
              <div><span>Routing 求解</span><b>{newPlan.routing.metadata?.status} · {newPlan.routing.metadata?.engine} {fmtMs(newPlan.routing.metadata?.solve_ms)}</b></div>
              <div><span>Warehouse 求解</span><b>{newPlan.warehouse.metadata?.status} · {fmtMs(newPlan.warehouse.metadata?.solve_ms)}</b></div>
              <div><span>验证器</span><b>{newPlan.validation.validator_version} · {newPlan.validation.status}</b></div>
              <div><span>违规项</span><b>{newPlan.validation.violations.length === 0 ? '无' : newPlan.validation.violations.map((v) => `${v.rule_id}: ${v.message}`).join('；')}</b></div>
            </div>
            {anomaly.phase === 'accepted' && <button className="btn btn-primary" onClick={() => { window.dispatchEvent(new CustomEvent('twin:navigate', { detail: 'simulations' })); }}>继续仿真推演 →</button>}
          </div>
        )}
      </div>
    </div>
  </div>;
}
