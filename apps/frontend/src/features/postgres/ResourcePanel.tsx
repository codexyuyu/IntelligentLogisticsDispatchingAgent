import { useEffect, useState } from 'react';
import { request, type Page } from '../../api';
import { statusLabel } from '../../lib/labels';

type MasterRow = { id: string; code?: string; external_ref?: string; status: string;
  capacity_weight_g?: number; setpoint_decic?: number };

/** The same 2.0.0 backend and authentication as the transport workflow. */
export default function ResourcePanel({ kind }: { kind: 'orders' | 'vehicles' }) {
  return <ResourceList key={kind} kind={kind} />;
}

function ResourceList({ kind }: { kind: 'orders' | 'vehicles' }) {
  const [data, setData] = useState<MasterRow[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [cursor, setCursor] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [history, setHistory] = useState<Array<string | null>>([]);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setData([]);
    setNextCursor(null);
    const query = new URLSearchParams({ limit: '50' });
    if (cursor) query.set('cursor', cursor);
    request<Page<MasterRow>>(`/${kind}?${query}`, { signal: controller.signal }).then(value => {
      if (controller.signal.aborted) return;
      if (value.has_more && (!value.next_cursor || value.next_cursor === cursor || history.includes(value.next_cursor))) {
        throw new Error('分页游标无效，请刷新后重试');
      }
      setData(value.items);
      setNextCursor(value.has_more ? value.next_cursor : null);
    }).catch(cause => { if (!controller.signal.aborted) setError(String(cause)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [kind, cursor, attempt, history]);
  return <section className="panel">
    <div className="panel-title-row"><div><h3>当前数据库{kind === 'orders' ? '订单' : '车辆'}</h3></div>
      <div className="section-actions">
        <button className="btn btn-ghost" disabled={loading} onClick={() => setAttempt(value => value + 1)}>刷新</button>
        <button className="btn btn-ghost" onClick={() => window.dispatchEvent(new CustomEvent('twin:navigate', { detail: 'vehicles' }))}>进入运输计划</button>
      </div>
    </div>
    {loading ? <p role="status">正在读取…</p> : error ? <div role="alert"><p>{error}</p><button onClick={() => setAttempt(value => value + 1)}>重试</button></div> : !data.length ? <p>当前没有{kind === 'orders' ? '订单' : '车辆'}数据。</p> :
      <div className="table-wrap"><table><thead><tr><th>编号</th><th>状态</th><th>资源 ID</th></tr></thead>
        <tbody>{data.map(row => <tr key={row.id}><td>{row.external_ref ?? row.code ?? row.id}</td>
          <td>{statusLabel(row.status)}</td><td>{row.id}</td></tr>)}</tbody></table></div>}
    <div className="section-actions" aria-label="资源分页">
      <button disabled={loading || history.length === 0} onClick={() => {
        setCursor(history[history.length - 1]);
        setHistory(items => items.slice(0, -1));
      }}>上一页</button>
      <span>第 {history.length + 1} 页{!loading && !error ? ` · 本页 ${data.length} 条` : ''}</span>
      <button disabled={loading || Boolean(error) || !nextCursor} onClick={() => {
        setHistory(items => [...items, cursor]);
        setCursor(nextCursor);
      }}>下一页</button>
    </div>
  </section>;
}
