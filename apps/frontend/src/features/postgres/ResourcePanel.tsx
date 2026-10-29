import { useEffect, useState } from 'react';
import { request, type Page } from '../../api';
import { statusLabel } from '../../lib/labels';

type MasterRow = { id: string; code?: string; external_ref?: string; status: string;
  capacity_weight_g?: number; setpoint_decic?: number };

/** The same 2.0.0 backend and authentication as the transport workflow. */
export default function ResourcePanel({ kind }: { kind: 'orders' | 'vehicles' }) {
  const [data, setData] = useState<MasterRow[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    request<Page<MasterRow>>(`/${kind}?limit=50`).then(value => {
      if (active) setData(value.items);
    }).catch(cause => { if (active) setError(String(cause)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [kind]);
  return <section className="panel">
    <div className="panel-title-row"><div><h3>当前数据库{kind === 'orders' ? '订单' : '车辆'}</h3></div>
      <button className="btn btn-ghost" onClick={() => window.dispatchEvent(new CustomEvent('twin:navigate', { detail: 'vehicles' }))}>进入运输计划</button>
    </div>
    {loading ? <p>正在读取…</p> : error ? <p role="alert">{error}</p> :
      <div className="table-wrap"><table><thead><tr><th>编号</th><th>状态</th><th>资源 ID</th></tr></thead>
        <tbody>{data.map(row => <tr key={row.id}><td>{row.external_ref ?? row.code ?? row.id}</td>
          <td>{statusLabel(row.status)}</td><td>{row.id}</td></tr>)}</tbody></table></div>}
  </section>;
}
