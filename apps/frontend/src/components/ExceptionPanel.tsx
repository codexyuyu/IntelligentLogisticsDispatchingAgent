import { useEffect, useState } from 'react';
import { request } from '../api';
import SectionHeader from './SectionHeader';
type Order = { id: string; external_ref: string };
type Exception = { exception_id: string; severity: string; status: string };
type Impact = { report: { affected_orders: string[]; affected_tasks: string[]; affected_resources: string[] }; boundary: { frozen_task_ids: string[]; interrupted_task_ids: string[]; mutable_task_ids: string[] } };
type Proposal = { adjustments: { task_id: string; strategy: string; earliest_start_s: number | null }[]; requires_manual_review: boolean };
const words: Record<string, string> = { open: '待处理', pending: '待处理', active: '处理中', resolved: '已解决', closed: '已关闭', low: '低', medium: '中', high: '高', critical: '紧急', defer: '延后执行', rescue_handoff: '救援交接' };
export function ExceptionPanel() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [orderId, setOrderId] = useState('');
  const [seconds, setSeconds] = useState(900);
  const [reason, setReason] = useState('客户取消订单');
  const [policy, setPolicy] = useState('return_to_origin');
  const [jobId, setJobId] = useState('');
  const [exceptions, setExceptions] = useState<Exception[]>([]);
  const [impact, setImpact] = useState<Impact | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [eventKey, setEventKey] = useState(() => crypto.randomUUID());
  async function refresh() {
    const data = await request<{ items: Exception[] }>('/exceptions?limit=50'); setExceptions(data.items);
  }
  useEffect(() => { void Promise.all([
    request<{ items: Order[] }>('/orders?limit=100').then(data => { setOrders(data.items); setOrderId(data.items[0]?.id ?? ''); }), refresh(),
  ]).catch(e => setError(String(e))); }, []);
  async function action(fn: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  function event() {
    if (!orderId || !reason.trim() || !Number.isInteger(seconds) || seconds < 0) throw new Error('请选择订单，填写原因和非负整数发生时间。');
    return { schema_version: '2.0.0', source: 'competition-ui', source_event_id: eventKey,
      kind: 'order_cancellation', occurred_at_utc: new Date().toISOString(), simulation_id: null, expected_revision: null,
      payload: { kind: 'order_cancellation', entity_ref: { kind: 'order', id: orderId, revision: null },
        effective_at_s: seconds, reason: reason.trim(), order_id: orderId, disposition_policy: policy } };
  }
  async function register() {
    const payload = event();
    const receipt = await request<{ event_id: string; duplicate: boolean }>('/events', { method: 'POST', body: JSON.stringify(payload) });
    await request('/exceptions', { method: 'POST', body: JSON.stringify({ schema_version: '2.0.0', event_id: receipt.event_id,
      severity: 'medium', affected_entity_refs: [payload.payload.entity_ref] }) });
    setNotice('订单取消事件已登记。登记不会直接修改已提交的调度方案。'); setEventKey(crypto.randomUUID()); await refresh();
  }
  async function analyse() {
    setImpact(null); setProposal(null);
    const source = await request<{ kind: string; value: { candidate: unknown; stops: unknown[]; validation?: { valid: boolean } } }>(`/jobs/${encodeURIComponent(jobId.trim())}/result`);
    if (source.kind !== 'transport' || !source.value.candidate || !source.value.validation?.valid) throw new Error('请选择已完成且校验通过的运输任务。');
    const command = { schema_version: '2.0.0', event: event(), plan: source.value.candidate, stops: source.value.stops, event_time_s: seconds };
    setImpact(await request<Impact>('/exceptions/impact', { method: 'POST', body: JSON.stringify(command) }));
    setProposal(await request<Proposal>('/reschedules/proposals', { method: 'POST', body: JSON.stringify({ schema_version: '2.0.0', impact: command,
      policy: { max_extra_delay_s: 300, allow_scope_expansion: false } }) }));
  }
  return <div><SectionHeader title="异常登记与影响分析" desc="选择业务订单登记取消事件，再基于已求解的运输方案分析影响。" />
    {error && <p role="alert" className="callout callout-error">{error}</p>}{notice && <p role="status">{notice}</p>}
    <section className="panel"><h3>登记订单取消</h3><div className="grid-two">
      <label>关联订单<select disabled={busy} value={orderId} onChange={e => { setOrderId(e.target.value); setEventKey(crypto.randomUUID()); setImpact(null); setProposal(null); }}>
        <option value="">请选择订单</option>{orders.map(o => <option key={o.id} value={o.id}>{o.external_ref || '未命名订单'}</option>)}</select></label>
      <label>发生时间（计划开始后秒数）<input disabled={busy} type="number" min={0} value={seconds} onChange={e => { setSeconds(Number(e.target.value)); setEventKey(crypto.randomUUID()); setImpact(null); setProposal(null); }} /></label>
      <label>货物处置<select disabled={busy} value={policy} onChange={e => { setPolicy(e.target.value); setEventKey(crypto.randomUUID()); }}><option value="return_to_origin">退回始发地</option><option value="quarantine">隔离待处理</option></select></label>
      <label>异常原因<input disabled={busy} value={reason} onChange={e => { setReason(e.target.value); setEventKey(crypto.randomUUID()); }} /></label>
    </div><button className="btn btn-primary" disabled={busy || !orderId || !reason.trim()} onClick={() => void action(register)}>登记异常</button>
    </section>
    <section className="panel"><h3>分析影响并生成调整建议</h3><p>从运输计划复制已完成的任务编号。系统自动读取方案和站点，无需填写技术数据。</p>
      <label>运输任务编号<input disabled={busy} value={jobId} onChange={e => { setJobId(e.target.value); setImpact(null); setProposal(null); }} placeholder="运输计划页面中的任务编号" /></label>
      <button className="btn btn-primary" disabled={busy || !jobId.trim() || !orderId} onClick={() => void action(analyse)}>{busy ? '处理中…' : '分析并生成建议'}</button>
      {impact && <p>影响订单 {impact.report.affected_orders.length} 个，任务 {impact.report.affected_tasks.length} 个，资源 {impact.report.affected_resources.length} 个；已冻结任务 {impact.boundary.frozen_task_ids.length} 个，执行中任务 {impact.boundary.interrupted_task_ids.length} 个。</p>}
      {proposal && <><p>{proposal.requires_manual_review ? '需要人工处理。' : `生成 ${proposal.adjustments.length} 条调整建议。`}调整建议尚未求解和提交，不代表计划已变更。</p>
        <table><thead><tr><th>序号</th><th>建议</th><th>最早开始（秒）</th></tr></thead><tbody>{proposal.adjustments.map((a, i) => <tr key={a.task_id}><td>{i + 1}</td><td>{words[a.strategy] ?? '待确认策略'}</td><td>{a.earliest_start_s ?? '待确定'}</td></tr>)}</tbody></table></>}
    </section>
    <section className="panel"><div className="panel-title-row"><h3>异常记录</h3><button className="btn btn-ghost" disabled={busy} onClick={() => void action(refresh)}>刷新记录</button></div>
      {!exceptions.length ? <p>暂无异常记录。</p> : <table><thead><tr><th>序号</th><th>严重程度</th><th>处理状态</th></tr></thead><tbody>{exceptions.map((item, i) => <tr key={item.exception_id}><td>{i + 1}</td><td>{words[item.severity] ?? item.severity}</td><td>{words[item.status] ?? item.status}</td></tr>)}</tbody></table>}
    </section></div>;
}
