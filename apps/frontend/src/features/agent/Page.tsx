import { useState } from 'react';
import { request } from '../../api';
import SectionHeader from '../../components/SectionHeader';

type ChatReply = { reply: string; model: string; provider_configured: boolean; trace_id: string };

export default function AgentPage() {
  const [message, setMessage] = useState('请总结当前调度状态，只依据已有数据回答。');
  const [reply, setReply] = useState<ChatReply | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function send() {
    if (!message.trim() || busy) return;
    setBusy(true); setError(''); setReply(null);
    try {
      setReply(await request<ChatReply>('/agents/chat', { method: 'POST',
        body: JSON.stringify({ schema_version: '2.0.0', message: message.trim() }) }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : '请求失败'); }
    finally { setBusy(false); }
  }
  return <div>
    <SectionHeader title="调度助手" />
    <section className="panel">
      <label htmlFor="dispatch-message">调度问题</label>
      <textarea id="dispatch-message" value={message} onChange={event => setMessage(event.target.value)} />
      <button className="btn btn-primary" disabled={busy || !message.trim()} onClick={() => void send()}>
        {busy ? '正在处理…' : '发送'}
      </button>
      {error && <p role="alert" className="callout callout-error">{error}</p>}
      {reply && <div role="status"><p style={{ whiteSpace: 'pre-wrap' }}>{reply.reply}</p>
        <small>模型：{reply.model} · 请求：{reply.trace_id}</small></div>}
    </section>
  </div>;
}
