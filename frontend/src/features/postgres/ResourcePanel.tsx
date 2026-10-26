import { useEffect, useState } from 'react';
import { pgRequest, prettyDate, safeText, type ResourceResponse } from './api';

/** Real PostgreSQL section displayed separately from the original synthetic snapshot. */
export default function ResourcePanel({ kind }: { kind: 'orders' | 'vehicles' }) {
  const [data, setData] = useState<ResourceResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    pgRequest<ResourceResponse>(`/${kind}`).then((value) => {
      if (alive) setData(value);
    }).catch((cause: unknown) => {
      if (alive) setError(cause instanceof Error ? cause.message : '读取失败');
    }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [kind]);
  return <section className="panel pg-resource-panel">
    <div className="panel-title-row"><div><h3>PostgreSQL 实库{kind === 'orders' ? '订单' : '车辆'}</h3></div>
      <button className="btn btn-ghost btn-sm" onClick={() => window.dispatchEvent(new CustomEvent('twin:navigate', { detail: 'postgres' }))}>进入实库调度台 →</button>
    </div>
    {loading ? <p className="pg-hint">正在从 PostgreSQL 读取…</p> : error ? <div className="pg-error">实库未连接：{error}。请使用 R22/R23 本机后端启动脚本。</div> :
      <>
      <div className="table-wrap"><table><thead><tr>{kind === 'orders' ?
        <><th>订单号</th><th>客户</th><th>重量（kg）</th><th>温度（℃）</th><th>时间窗</th></> :
        <><th>车辆</th><th>归属仓库</th><th>载重（kg）</th><th>温度（℃）</th></>}</tr></thead><tbody>
        {(data?.rows ?? []).slice(0, 8).map((row, index) => <tr key={String(row[kind === 'orders' ? 'order_code' : 'vehicle_code'] ?? index)}>
          {kind === 'orders' ? <><td>{safeText(row.order_code)}</td><td>{safeText(row.customer_name)}</td><td>{safeText(row.weight_kg)}</td>
            <td>{safeText(row.min_temp_c)} ~ {safeText(row.max_temp_c)}</td><td>{prettyDate(row.window_start)} ~ {prettyDate(row.window_end)}</td></> :
            <><td>{safeText(row.vehicle_code)}</td><td>{safeText(row.warehouse_code)}</td><td>{safeText(row.capacity_kg)}</td><td>{safeText(row.min_temp_c)} ~ {safeText(row.max_temp_c)}</td></>}
        </tr>)}</tbody></table></div></>}
  </section>;
}
