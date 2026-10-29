import { useEffect, useState } from 'react';
import { request, type Page } from '../../api';
import { KpiCard } from '../../components/KpiCard';

export default function LiveOverview() {
  const [counts, setCounts] = useState<number[] | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setCounts(null);
    async function count(kind: string) {
      let cursor: string | null = null;
      const seen = new Set<string>();
      const ids = new Set<string>();
      do {
        const params = new URLSearchParams({ limit: '100' });
        if (cursor) params.set('cursor', cursor);
        const page = await request<Page<{ id: string }>>(`/${kind}?${params}`, { signal: controller.signal });
        page.items.forEach(item => ids.add(item.id));
        if (!page.has_more) return ids.size;
        if (!page.next_cursor || seen.has(page.next_cursor)) throw new Error('分页数据异常，请重试。');
        seen.add(page.next_cursor); cursor = page.next_cursor;
      } while (!controller.signal.aborted);
      throw new Error('已取消');
    }
    void Promise.all(['orders', 'vehicles', 'warehouses'].map(count)).then(value => {
      if (!controller.signal.aborted) setCounts(value);
    }).catch(cause => { if (!controller.signal.aborted) setError(String(cause)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [revision]);
  const navigate = (key: string) => window.dispatchEvent(new CustomEvent('twin:navigate', { detail: key }));
  return <div>
    <section className="panel"><h2>业务总览</h2><p>当前数据库中的订单、车辆与仓库；调度结果请在对应任务中查看。</p>
      <button className="btn btn-ghost" disabled={loading} onClick={() => setRevision(value => value + 1)}>刷新数据</button>
      {loading && <p role="status">正在读取业务数据…</p>}
      {error && <p role="alert">{error}</p>}
    </section>
    <div className="kpi-grid">{['订单总量', '运输车辆', '仓库节点'].map((label, index) =>
      <KpiCard key={label} label={label} value={counts ? String(counts[index]) : '—'} sub={counts ? '数据库记录' : '尚未取得数据'} icon={['package', 'truck', 'warehouse'][index]} />)}</div>
    <section className="panel"><h3>开始工作</h3><div className="section-actions">
      {[['orders', '查看订单'], ['vehicles', '运输计划'], ['plans', '联合调度'], ['warehouseTwin', '查看仓库'], ['simulations', '仿真回放']].map(([key, label]) =>
        <button key={key} className="btn btn-primary" onClick={() => navigate(key)}>{label}</button>)}
    </div><p>尚未加载计划时，不计算需求满足率、准时率或资源利用率。</p></section>
  </div>;
}
