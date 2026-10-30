import { useEffect, useState } from 'react';
import { request } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { readStored, saveStored } from '../../lib/asyncJobs';
import { runKey, short } from '../stageB/api';

type ToolTrace = {
  name: string; ok: boolean; arguments: Record<string, unknown> | null;
  content: Record<string, unknown>; error_code: string | null;
};
type DispatchReply = {
  agent_run_id: string; run_id: string; reply: string; model: string;
  provider_configured: boolean; trace_id: string;
  stopped_reason: 'final_answer' | 'max_turns' | 'no_tool_evidence';
  tools: ToolTrace[];
};
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const previousKey = 'dispatch_last_agent_run';
const handoffKey = 'dispatch_delay_handoff';
function navigate(page: string) {
  window.dispatchEvent(new CustomEvent('twin:navigate', { detail: page }));
}

/** Bound to an actual checked integration run. The model has no write/approve tools. */
export default function AgentPage() {
  const [runId, setRunId] = useState(() => readStored(runKey) ?? '');
  const [message, setMessage] = useState('请读取当前联合运行的校验状态和调度指标，并说明数据来源。');
  const [reply, setReply] = useState<DispatchReply | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const syncRun = (event: Event) => {
      const value = (event as CustomEvent<string>).detail;
      if (UUID.test(value)) setRunId(value);
    };
    window.addEventListener('stageb:run', syncRun);
    const last = readStored(previousKey);
    if (last && UUID.test(last)) {
      void request<DispatchReply>(`/agents/dispatch/${encodeURIComponent(last)}`)
        .then(value => { setReply(value); setRunId(value.run_id); })
        .catch(() => { /* Old or inaccessible saved analysis is not authoritative. */ });
    }
    return () => window.removeEventListener('stageb:run', syncRun);
  }, []);

  async function send() {
    if (!message.trim() || !UUID.test(runId.trim()) || busy) return;
    setBusy(true); setError(''); setReply(null);
    try {
      const result = await request<DispatchReply>('/agents/dispatch', { method: 'POST',
        body: JSON.stringify({ schema_version: '2.0.0', run_id: runId.trim(), message: message.trim() }),
      });
      setReply(result); saveStored(runKey, result.run_id);
      saveStored(previousKey, result.agent_run_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : '请求失败'); }
    finally { setBusy(false); }
  }

  return <div>
    <SectionHeader title="调度助手" />
    <section className="panel">
      <p className="muted">读取已校验的联合运行与数据库模拟状态；模型负责选择只读工具并解释结果，不能登记异常或自动批准。</p>
      <label htmlFor="agent-run-id">当前联合运行 UUID</label>
      <input id="agent-run-id" value={runId} onChange={event => setRunId(event.target.value)}
        placeholder="请先从联合调度生成 checked run" aria-invalid={!!runId && !UUID.test(runId.trim())} />
      <button className="btn btn-ghost btn-sm" onClick={() => setRunId(readStored(runKey) ?? '')}>读取最近一次运行</button>
      <button className="btn btn-ghost btn-sm" onClick={() => navigate('plans')}>前往联合调度</button>
      <label htmlFor="dispatch-message">调度问题</label>
      <textarea id="dispatch-message" value={message} onChange={event => setMessage(event.target.value)} rows={4} />
      <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => setMessage('请读取并总结本次联合调度的真实指标，说明校验状态。')}>查询调度指标</button>
        <button className="btn btn-ghost btn-sm" onClick={() => setMessage('读取本次模拟在第 1400 秒的车辆状态与仓储作业进度。')}>查询模拟状态</button>
        <button className="btn btn-ghost btn-sm" onClick={() => setMessage('先查询第 1400 秒在途车辆，再对其中一辆做 60 秒延误的只读预分析；不要登记或批准异常。')}>预分析车辆延误</button>
      </div>
      <button className="btn btn-primary" disabled={busy || !message.trim() || !UUID.test(runId.trim())} onClick={() => void send()}>
        {busy ? '正在查询真实调度数据…' : '执行智能调度分析'}
      </button>
      {!runId && <p>尚未选择联合运行，请先到联合调度生成 checked run。</p>}
      {error && <p role="alert" className="callout callout-error">{error}</p>}
      {reply && <div role="status" style={{ marginTop: 16 }}>
        {reply.stopped_reason !== 'final_answer' &&
          <p role="alert" className="callout callout-error">本次分析未完整结束，不应将回答作为业务事实。</p>}
        <p style={{ whiteSpace: 'pre-wrap' }}>{reply.reply}</p>
        <p><small>模型：{reply.model} · 联合运行：{short(reply.run_id)} · 审计编号：{short(reply.agent_run_id)}</small></p>
        <h3>工具执行证据（{reply.tools.length} 次）</h3>
        {reply.tools.length === 0 && <p>本次模型未调用业务工具；系统不会把无证据的回答认定为调度结论。</p>}
        {reply.tools.map((tool, index) => <details key={`${tool.name}-${index}`}>
          <summary>{tool.ok ? '✓' : '✕'} {tool.name} {tool.error_code ? `· ${tool.error_code}` : ''}</summary>
          <small>输入：{JSON.stringify(tool.arguments ?? {}, null, 2)}</small>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 220, overflowY: 'auto' }}>{JSON.stringify(tool.content, null, 2)}</pre>
        </details>)}
        <p className="muted">候选分析只用于模拟；异常登记、批准、拒绝仍在现有页面由人工操作。</p>
        <button className="btn btn-ghost btn-sm" onClick={() => {
          saveStored(runKey, reply.run_id);
          const preview = reply.tools.find(item => item.ok && item.name === 'preview_vehicle_delay');
          if (preview?.content) {
            const data = preview.content;
            if (data.run_id === reply.run_id && typeof data.vehicle_id === 'string'
              && typeof data.time_s === 'number' && typeof data.delay_s === 'number') {
              saveStored(handoffKey, JSON.stringify({ run_id: reply.run_id, vehicle_id: data.vehicle_id,
                time_s: data.time_s, delay_s: data.delay_s }));
            }
          }
          navigate('events');
        }}>前往异常处置（自动带入候选）</button>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('simulations')}>前往仿真回放</button>
      </div>}
    </section>
  </div>;
}
