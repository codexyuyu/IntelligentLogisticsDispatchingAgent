import { useEffect, useMemo, useState } from 'react';
import { request } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { KpiCard } from '../../components/KpiCard';
import { readStored, useTaskRunner } from '../../lib/asyncJobs';
import { shortId } from './model';
import type { InventoryResponse } from './model';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const movementLabels: Record<string, string> = { receive: '收货完成', load: '装车出库' };

export default function InventoryPage() {
  const [inventory, setInventory] = useState<InventoryResponse | null>(null);
  const [cargoFilter, setCargoFilter] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const { busy, error, run } = useTaskRunner();
  const latestRun = readStored('integration_last_run');

  async function load(signal: AbortSignal) {
    if (cargoFilter.trim() && !UUID_PATTERN.test(cargoFilter.trim())) throw new Error('货物 ID 须为完整 UUID。');
    if (locationFilter.trim() && !UUID_PATTERN.test(locationFilter.trim())) throw new Error('库位 ID 须为完整 UUID。');
    const params = new URLSearchParams({ limit: '500' });
    if (cargoFilter.trim()) params.set('cargo_id', cargoFilter.trim());
    if (locationFilter.trim()) params.set('location_id', locationFilter.trim());
    const value = await request<InventoryResponse>(`/inventory?${params}`, { signal });
    signal.throwIfAborted();
    setInventory(value);
  }

  useEffect(() => { void run(load); }, []);

  const summary = useMemo(() => {
    const items = inventory?.items ?? [];
    return {
      received: items.filter(item => item.quantity_delta > 0).length,
      shipped: items.filter(item => item.quantity_delta < 0).length,
      matchingRun: latestRun ? items.filter(item => item.run_id === latestRun).length : 0,
    };
  }, [inventory, latestRun]);

  return <div>
    <SectionHeader title="S5 · 实际库存台账" desc="读取 S3 追加式库存流水及按货物/库位汇总的结存；只有仓储任务被显式完成后才产生收货/出库记录。" />
    <section className="panel">
      <form className="s5-filter-bar" onSubmit={event => { event.preventDefault(); void run(load); }}>
        <label>货物 UUID（可选）<input aria-label="筛选货物 UUID" value={cargoFilter} onChange={event => setCargoFilter(event.target.value)} placeholder="不填则显示全部" /></label>
        <label>库位 UUID（可选）<input aria-label="筛选库位 UUID" value={locationFilter} onChange={event => setLocationFilter(event.target.value)} placeholder="不填则显示全部" /></label>
        <button className="btn btn-primary btn-sm" type="submit" disabled={busy}>{busy ? '读取中…' : '查询 / 刷新台账'}</button>
        <button className="btn btn-ghost btn-sm" type="button" disabled={busy} onClick={() => {
          setCargoFilter(''); setLocationFilter('');
          void run(async signal => {
            const value = await request<InventoryResponse>('/inventory?limit=500', { signal });
            signal.throwIfAborted(); setInventory(value);
          });
        }}>清除筛选</button>
      </form>
      {error && <p role="alert" className="callout callout-error">{error}</p>}
      <p className="s5-muted">库存为当前权限范围内的实际执行流水，不是 CP-SAT 计划占用；筛选条件同时作用于流水和结存。</p>
    </section>
    {inventory && <>
      <div className="kpi-grid">
        <KpiCard label="流水总数" value={`${inventory.total_entries}`} sub={inventory.has_more ? '仅展示最新 500 条' : '全部符合条件的记录'} icon="package" />
        <KpiCard label="收货记录" value={`${summary.received}`} sub="当前已加载流水" icon="check" tone="green" />
        <KpiCard label="出库记录" value={`${summary.shipped}`} sub="当前已加载流水" icon="truck" />
        <KpiCard label="关联最近运行" value={`${summary.matchingRun}`} sub={latestRun ? shortId(latestRun) : '尚无运行编号'} icon="route" />
      </div>
      <section className="panel">
        <div className="panel-title-row"><div><h3>库存结存</h3><p>按货物 × 库位对已写入流水求和，0 表示净入出相抵。</p></div><span className="soft-badge">{inventory.positions.length} 项</span></div>
        {inventory.positions.length ? <div className="table-wrap"><table>
          <thead><tr><th>货物</th><th>库位</th><th>结存件数</th></tr></thead>
          <tbody>{inventory.positions.map(position => <tr key={`${position.cargo_id}-${position.location_id}`}>
            <td title={position.cargo_id}>{shortId(position.cargo_id)}</td><td title={position.location_id}>{shortId(position.location_id)}</td>
            <td><strong className={position.quantity_units < 0 ? 's5-negative' : ''}>{position.quantity_units}</strong></td>
          </tr>)}</tbody>
        </table></div> : <p className="s5-muted">还没有可汇总的实际库存变化；可先在仓储作业甘特图中显式完成收货任务。</p>}
      </section>
      <section className="panel">
        <div className="panel-title-row"><div><h3>收货/出库流水</h3><p>原始追加式记录；同一操作不会因刷新而重复入账。</p></div><span className="soft-badge">显示 {inventory.items.length} / {inventory.total_entries}</span></div>
        {inventory.items.length ? <div className="table-wrap"><table>
          <thead><tr><th>操作时间</th><th>业务类型</th><th>货物</th><th>库位</th><th>数量变化</th><th>关联运行 / 任务</th></tr></thead>
          <tbody>{inventory.items.map(item => <tr key={item.id}>
            <td>{new Date(item.created_at).toLocaleString('zh-CN')}</td>
            <td>{movementLabels[item.operation_kind ?? ''] ?? (item.operation_kind ?? '未标注')}</td>
            <td title={item.cargo_id}>{shortId(item.cargo_id)}</td>
            <td title={`${item.location_id}\n来源库位：${item.source_location_id ?? '—'}`}>{shortId(item.location_id)}</td>
            <td className={item.quantity_delta < 0 ? 's5-negative' : 's5-positive'}>{item.quantity_delta > 0 ? '+' : ''}{item.quantity_delta}</td>
            <td title={`运行：${item.run_id ?? '—'}\n任务：${item.task_id ?? '—'}`}>{shortId(item.run_id)} / {shortId(item.task_id)}</td>
          </tr>)}</tbody>
        </table></div> : <p className="s5-muted">暂无实际库存流水。计划求解和时间线回放不会自动写入台账。</p>}
        {inventory.has_more && <p className="callout callout-warn">API 每次最多返回 500 条流水；可通过货物/库位 UUID 缩小查询范围，不能把当前列表视为全部记录。</p>}
      </section>
    </>}
  </div>;
}
