import { useEffect, useMemo, useState } from 'react';
import { request } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { KpiCard } from '../../components/KpiCard';
import { StatusPill } from '../../components/StatusPill';
import { useApp } from '../../appContext';
import { fmtClock } from '../../lib/format';

type Tab = 'overview' | 'inbound' | 'inventory' | 'outbound' | 'resources';
type FlowStatus = '待处理' | '预冷中' | '已入库';
type WarehouseOption = { id: string; code: string; name: string };
type ZoneOption = { id: string; warehouse_id: string; code: string; setpoint_decic: number };

type LocalLot = {
  batch_id: string;
  warehouse_id: string;
  temperature_zone: 'chilled' | 'frozen';
  on_hand_units: number;
  reserved_units: number;
  quarantined_units: number;
  expires_at: string;
  source: '场景快照' | '本地入库演示';
};

type InboundTask = {
  id: string;
  batchId: string;
  warehouseId: string;
  warehouseName: string;
  zoneId: string;
  zoneLabel: string;
  zone: 'chilled' | 'frozen';
  quantity: number;
  etaS: number;
  status: FlowStatus;
};

const tabs: { key: Tab; label: string }[] = [
  { key: 'overview', label: '仓储总览' },
  { key: 'inbound', label: '入库作业' },
  { key: 'inventory', label: '库存与批次' },
  { key: 'outbound', label: '出库作业' },
  { key: 'resources', label: '冷间与资源' },
];

function badgeTone(value: string) {
  if (value === '已入库') return 'success' as const;
  if (value === '预冷中') return 'warning' as const;
  return 'neutral' as const;
}

export default function Page() {
  const { snapshot, baselinePlan } = useApp();
  const [tab, setTab] = useState<Tab>('overview');
  const [query, setQuery] = useState('');
  const [zone, setZone] = useState<'all' | 'chilled' | 'frozen'>('all');
  const [inboundTasks, setInboundTasks] = useState<InboundTask[]>([]);
  const [lots, setLots] = useState<LocalLot[]>([]);
  const [selectedLot, setSelectedLot] = useState<string | null>(null);
  const [receipt, setReceipt] = useState({ warehouseId: '', quantity: 20, etaS: 3600 });
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);
  const [zones, setZones] = useState<ZoneOption[]>([]);
  const [zoneId, setZoneId] = useState('');
  const [warehouseLoading, setWarehouseLoading] = useState(true);
  const [zoneLoading, setZoneLoading] = useState(false);
  const [warehouseError, setWarehouseError] = useState('');
  const [zoneError, setZoneError] = useState('');
  const [reload, setReload] = useState(0);
  const [outbound, setOutbound] = useState({ orderId: '', quantity: 5 });
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setWarehouseLoading(true); setWarehouseError('');
    void request<{ items: WarehouseOption[] }>('/warehouses?limit=100').then(page => {
      if (!active) return;
      setWarehouses(page.items);
      setReceipt(current => ({ ...current, warehouseId: page.items.some(w => w.id === current.warehouseId)
        ? current.warehouseId : page.items[0]?.id ?? '' }));
    }).catch(cause => { if (active) { setWarehouseError(String(cause)); setWarehouses([]); } })
      .finally(() => { if (active) setWarehouseLoading(false); });
    return () => { active = false; };
  }, [reload]);

  useEffect(() => {
    let active = true;
    setZones([]); setZoneId(''); setZoneError('');
    if (!receipt.warehouseId) { setZoneLoading(false); return; }
    setZoneLoading(true);
    void request<{ items: ZoneOption[] }>(`/warehouses/${encodeURIComponent(receipt.warehouseId)}/zones?limit=100`).then(page => {
      if (!active) return;
      const ownZones = page.items.filter(z => z.warehouse_id === receipt.warehouseId);
      setZones(ownZones); setZoneId(ownZones[0]?.id ?? '');
    }).catch(cause => { if (active) setZoneError(String(cause)); })
      .finally(() => { if (active) setZoneLoading(false); });
    return () => { active = false; };
  }, [receipt.warehouseId, reload]);

  const availableZones = zones.filter(z => z.warehouse_id === receipt.warehouseId);
  const selectedZone = availableZones.find(z => z.id === zoneId);
  const canCreateInbound = !warehouseLoading && !zoneLoading && !warehouseError && !zoneError
    && warehouses.some(w => w.id === receipt.warehouseId) && Boolean(selectedZone)
    && Number.isInteger(receipt.quantity) && receipt.quantity > 0;
  function selectWarehouse(id: string) {
    setReceipt(current => ({ ...current, warehouseId: id }));
    setZoneId(''); setZones([]); setNotice(null);
  }

  const baseLots = useMemo<LocalLot[]>(() => (snapshot?.stock_lots ?? []).map((lot) => ({ ...lot, source: '场景快照' })), [snapshot]);
  const mergedLots = useMemo(() => {
    const local = new Map(lots.map((l) => [l.batch_id, l]));
    const combined = [...baseLots];
    for (const lot of lots) if (!combined.some((b) => b.batch_id === lot.batch_id)) combined.push(lot);
    return combined.map((lot) => local.get(lot.batch_id) ?? lot);
  }, [baseLots, lots]);
  const filteredLots = mergedLots.filter((lot) => {
    const matchZone = zone === 'all' || lot.temperature_zone === zone;
    const matchQuery = !query || `${lot.batch_id} ${lot.warehouse_id}`.toLowerCase().includes(query.toLowerCase());
    return matchZone && matchQuery;
  });

  const orderIds = snapshot?.orders.map((o) => o.order_id) ?? [];
  const selected = selectedLot ? mergedLots.find((l) => l.batch_id === selectedLot) : null;
  const stockUnits = mergedLots.reduce((sum, lot) => sum + Math.max(0, lot.on_hand_units), 0);
  const reservedUnits = mergedLots.reduce((sum, lot) => sum + lot.reserved_units, 0);
  const lowFreshnessLots = mergedLots.filter((lot) => new Date(lot.expires_at).getTime() - Date.now() < 36 * 3600 * 1000);
  const scheduledOps = baselinePlan?.warehouse.operations ?? [];

  const updateLot = (batchId: string, patch: Partial<LocalLot>) => {
    setLots((prev) => {
      const hit = prev.find((l) => l.batch_id === batchId);
      if (hit) return prev.map((l) => (l.batch_id === batchId ? { ...l, ...patch } : l));
      const source = mergedLots.find((l) => l.batch_id === batchId);
      return source ? [...prev, { ...source, ...patch, source: '本地入库演示' }] : prev;
    });
  };

  function createInbound() {
    if (!canCreateInbound || !selectedZone) { setNotice('请选择有效仓库及其温区，并填写正整数数量。'); return; }
    const taskId = `IN-${String(inboundTasks.length + 1).padStart(3, '0')}`;
    const batchId = `LOCAL-${Date.now().toString().slice(-6)}`;
    setInboundTasks((prev) => [{ id: taskId, batchId, warehouseId: receipt.warehouseId,
      warehouseName: warehouses.find(w => w.id === receipt.warehouseId)?.name || warehouses.find(w => w.id === receipt.warehouseId)?.code || '仓库',
      zoneId: selectedZone.id, zoneLabel: `${selectedZone.code}（${selectedZone.setpoint_decic / 10}°C）`,
      zone: selectedZone.setpoint_decic < 0 ? 'frozen' : 'chilled', quantity: receipt.quantity, etaS: receipt.etaS, status: '待处理' }, ...prev]);
    setNotice(`已创建入库任务 ${taskId}，下一步执行预冷和确认入库。`);
  }

  function startPreCooling(taskId: string) {
    setInboundTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: '预冷中' } : t)));
    setNotice(`入库任务 ${taskId} 已进入预冷阶段。`);
  }

  function completeInbound(task: InboundTask) {
    const expires = new Date(Date.now() + (task.zone === 'frozen' ? 14 : 4) * 86400000).toISOString();
    const existing = mergedLots.find((l) => l.batch_id === task.batchId);
    if (existing) updateLot(task.batchId, { on_hand_units: existing.on_hand_units + task.quantity, source: '本地入库演示' });
    else setLots((prev) => [{ batch_id: task.batchId, warehouse_id: task.warehouseId, temperature_zone: task.zone, on_hand_units: task.quantity, reserved_units: 0, quarantined_units: 0, expires_at: expires, source: '本地入库演示' }, ...prev]);
    setInboundTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, status: '已入库' } : t)));
    setNotice(`任务 ${task.id} 已完成入库，库存已在当前工作台更新。`);
    setTab('inventory');
  }

  function reserveOutbound() {
    if (!outbound.orderId) return setNotice('请先选择订单。');
    if (!selected) return setNotice('请先选择库存批次。');
    const available = selected.on_hand_units - selected.reserved_units - selected.quarantined_units;
    if (outbound.quantity <= 0 || outbound.quantity > available) return setNotice(`可用库存不足，当前仅可出库 ${Math.max(0, available)} 件。`);
    updateLot(selected.batch_id, { reserved_units: selected.reserved_units + outbound.quantity, source: '本地入库演示' });
    setNotice(`${outbound.orderId} 已预占 ${outbound.quantity} 件。`);
  }

  function shipOutbound() {
    if (!selected) return setNotice('请先选择库存批次。');
    if (outbound.quantity <= 0 || outbound.quantity > selected.reserved_units) return setNotice('请先预占足够库存。');
    updateLot(selected.batch_id, { on_hand_units: selected.on_hand_units - outbound.quantity, reserved_units: selected.reserved_units - outbound.quantity, source: '本地入库演示' });
    setNotice(`${outbound.orderId || '当前订单'} 已完成 ${outbound.quantity} 件出库。`);
  }

  return <div className="warehouse-module">
    <SectionHeader title="仓储管理" />

    <div className="seg warehouse-tabs">{tabs.map((item) => <button key={item.key} className={`seg-btn ${tab === item.key ? 'is-active' : ''}`} onClick={() => setTab(item.key)}>{item.label}</button>)}</div>
    {notice && <div className="callout callout-info warehouse-notice"><span>{notice}</span><button className="link-btn" onClick={() => setNotice(null)}>关闭</button></div>}

    {tab === 'overview' && <>
      <div className="kpi-grid">
        <KpiCard label="库存总量" value={`${stockUnits}`} sub="当前场景 + 本地演示变更" icon="package" />
        <KpiCard label="预占库存" value={`${reservedUnits}`} sub="待出库订单预占" icon="check" tone="neutral" />
        <KpiCard label="待处理入库" value={`${inboundTasks.filter((t) => t.status !== '已入库').length}`} sub="收货 / 预冷 / 入库" icon="warehouse" tone="green" />
        <KpiCard label="临期批次" value={`${lowFreshnessLots.length}`} sub="按当前本机时间" icon="alert" tone={lowFreshnessLots.length ? 'orange' : 'green'} />
      </div>
      <div className="card-grid two">
        <div className="panel"><div className="panel-title-row"><div><h3>仓储作业主线</h3></div></div><div className="warehouse-flow">{['到货登记', '收货验收', '预冷处理', '确认入库', '库存管理', '出库拣选', '装车交接'].map((x, i) => <div key={x} className="warehouse-flow-node"><span>{i + 1}</span><b>{x}</b></div>)}</div></div>
        <div className="panel"><div className="panel-title-row"><div><h3>与当前调度方案连接</h3><p>仓储运营结果继续交给已有 CP-SAT / Routing 链路。</p></div><StatusPill tone={baselinePlan ? 'success' : 'warning'}>{baselinePlan ? `Plan v${baselinePlan.version}` : '等待调度方案'}</StatusPill></div><div className="chain-mini"><div><b>{scheduledOps.length}</b><span>已排程作业</span></div><div><b>{baselinePlan?.warehouse.warehouse_handoffs.length ?? 0}</b><span>装车交接</span></div><div><b>{snapshot?.warehouses.length ?? 0}</b><span>仓库节点</span></div></div><button className="btn btn-primary btn-sm" onClick={() => setTab('inbound')}>从入库开始</button></div>
      </div>
    </>}

    {tab === 'inbound' && <div className="card-grid two">
      <div className="panel">
        <div className="panel-title-row"><div><h3>到货登记</h3><p>仓库与温区从后端读取；本页入库流程为工作台演示，不写回后端。</p></div>
          <button className="btn btn-ghost btn-sm" disabled={warehouseLoading || zoneLoading} onClick={() => setReload(value => value + 1)}>刷新仓库与温区</button>
        </div>
        {(warehouseError || zoneError) && <p role="alert" className="callout callout-error">{warehouseError ? `仓库读取失败：${warehouseError}` : `温区读取失败：${zoneError}`}，请刷新重试。</p>}
        {!warehouseLoading && !warehouseError && !warehouses.length && <p role="status">暂无可选仓库，请先导入仓库主数据。</p>}
        {!warehouseLoading && !zoneLoading && !zoneError && receipt.warehouseId && !availableZones.length && <p role="status">所选仓库暂无温区，请先配置温区后再创建入库任务。</p>}
        <div className="form-grid two">
          <label>仓库<select aria-label="入库仓库" value={warehouses.some(w => w.id === receipt.warehouseId) ? receipt.warehouseId : ''} disabled={warehouseLoading || !warehouses.length} onChange={e => selectWarehouse(e.target.value)}>
            <option value="" disabled>{warehouseLoading ? '正在加载仓库…' : warehouseError ? '仓库读取失败' : '请选择仓库'}</option>
            {warehouses.map(w => <option key={w.id} value={w.id}>{w.name || w.code}{w.name && w.code ? `（${w.code}）` : ''}</option>)}
          </select></label>
          <label>温区<select aria-label="入库温区" value={selectedZone?.id ?? ''} disabled={warehouseLoading || zoneLoading || !availableZones.length} onChange={e => setZoneId(e.target.value)}>
            <option value="" disabled>{zoneLoading ? '正在加载温区…' : zoneError ? '温区读取失败' : receipt.warehouseId ? '请选择温区' : '请先选择仓库'}</option>
            {availableZones.map(z => <option key={z.id} value={z.id}>{z.code} · {z.setpoint_decic < 0 ? '冷冻' : '冷藏'}（{z.setpoint_decic / 10}°C）</option>)}
          </select></label>
          <label>数量<input type="number" min={1} step={1} value={receipt.quantity} onChange={e => setReceipt(v => ({ ...v, quantity: Number(e.target.value) }))} /></label>
          <label>预计到货<input value={fmtClock(receipt.etaS)} disabled /></label>
        </div>
        <div className="section-actions"><button className="btn btn-primary" disabled={!canCreateInbound} onClick={createInbound}>创建入库任务</button><button className="btn btn-ghost" onClick={() => { setReceipt(v => ({ ...v, etaS: v.etaS + 1800 })); setNotice('预计到货已顺延 30 分钟，可用于演示动态到货。'); }}>模拟到货延迟 +30min</button></div>
      </div>
      <div className="panel"><div className="panel-title-row"><div><h3>入库任务</h3><p>点击“开始预冷”再“确认入库”，观察库存变化。</p></div><span className="soft-badge">{inboundTasks.length} 项</span></div><div className="table-wrap"><table><thead><tr><th>任务</th><th>批次</th><th>仓库</th><th>温区</th><th>数量</th><th>状态</th><th>操作</th></tr></thead><tbody>{inboundTasks.map((task) => <tr key={task.id}><td><strong>{task.id}</strong></td><td>{task.batchId}</td><td>{task.warehouseName}</td><td>{task.zoneLabel}</td><td>{task.quantity}</td><td><StatusPill tone={badgeTone(task.status)}>{task.status}</StatusPill></td><td>{task.status === '待处理' ? <button className="link-btn" onClick={() => startPreCooling(task.id)}>开始预冷</button> : task.status === '预冷中' ? <button className="link-btn" onClick={() => completeInbound(task)}>确认入库</button> : <span className="muted-line">已完成</span>}</td></tr>)}</tbody></table></div></div>
    </div>}

    {tab === 'inventory' && <>
      <div className="panel"><div className="panel-title-row"><div><h3>库存与批次</h3><p>库存来源于当前场景快照；本页的入库/出库操作只修改前端工作台状态。</p></div><div className="section-actions"><div className="seg">{(['all', 'chilled', 'frozen'] as const).map((z) => <button key={z} className={`seg-btn ${zone === z ? 'is-active' : ''}`} onClick={() => setZone(z)}>{z === 'all' ? '全部' : z === 'chilled' ? '冷藏' : '冷冻'}</button>)}</div><input className="search-input" placeholder="搜索批次 / 仓库" value={query} onChange={(e) => setQuery(e.target.value)} /></div></div><div className="table-wrap"><table><thead><tr><th>批次</th><th>仓库</th><th>温区</th><th>现存</th><th>预占</th><th>隔离</th><th>到期</th><th>来源</th><th>操作</th></tr></thead><tbody>{filteredLots.map((lot) => <tr key={lot.batch_id} className={selectedLot === lot.batch_id ? 'is-active' : ''} onClick={() => setSelectedLot(lot.batch_id)}><td><strong>{lot.batch_id}</strong></td><td>{lot.warehouse_id}</td><td><span className={`zone zone-${lot.temperature_zone}`}>{lot.temperature_zone === 'chilled' ? '冷藏' : '冷冻'}</span></td><td>{lot.on_hand_units}</td><td>{lot.reserved_units}</td><td>{lot.quarantined_units}</td><td>{new Date(lot.expires_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</td><td>{lot.source}</td><td><button className="link-btn" onClick={(e) => { e.stopPropagation(); setSelectedLot(lot.batch_id); setTab('outbound'); }}>去出库</button></td></tr>)}</tbody></table></div></div>
      {selected && <div className="panel" style={{ marginTop: 16 }}><div className="panel-title-row"><div><h3>{selected.batch_id} 详情</h3><p>可用库存 = 现存 − 预占 − 隔离。</p></div><StatusPill tone={selected.on_hand_units - selected.reserved_units - selected.quarantined_units > 0 ? 'success' : 'warning'}>{Math.max(0, selected.on_hand_units - selected.reserved_units - selected.quarantined_units)} 件可用</StatusPill></div></div>}
    </>}

    {tab === 'outbound' && <div className="card-grid two">
      <div className="panel"><div className="panel-title-row"><div><h3>出库作业</h3><p>借鉴原项目的“订单 → 库存预占 → 出库 → 装车”流程。</p></div></div><div className="form-grid two"><label>订单<select value={outbound.orderId} onChange={(e) => setOutbound((v) => ({ ...v, orderId: e.target.value }))}><option value="">请选择订单</option>{orderIds.map((id) => <option key={id}>{id}</option>)}</select></label><label>数量<input type="number" min={1} value={outbound.quantity} onChange={(e) => setOutbound((v) => ({ ...v, quantity: Math.max(1, Number(e.target.value) || 1) }))} /></label><label>库存批次<select value={selectedLot ?? ''} onChange={(e) => setSelectedLot(e.target.value || null)}><option value="">请选择批次</option>{mergedLots.filter((l) => l.on_hand_units - l.reserved_units - l.quarantined_units > 0).map((l) => <option key={l.batch_id} value={l.batch_id}>{l.batch_id} / {l.temperature_zone === 'chilled' ? '冷藏' : '冷冻'} / 可用 {l.on_hand_units - l.reserved_units - l.quarantined_units}</option>)}</select></label><label>车辆<span className="input-static">由现有 Routing / 联合调度决定</span></label></div><div className="section-actions"><button className="btn btn-secondary" onClick={reserveOutbound}>预占库存</button><button className="btn btn-primary" onClick={shipOutbound}>完成出库</button></div></div>
      <div className="panel"><div className="panel-title-row"><div><h3>出库链路</h3><p>完成仓储执行后，继续交给现有装车交接和 Routing。</p></div></div><div className="warehouse-flow compact">{['订单确认', '库存预占', '拣选', '出库', '装车交接', 'Routing配送'].map((x, i) => <div key={x} className="warehouse-flow-node"><span>{i + 1}</span><b>{x}</b></div>)}</div><div className="callout callout-info">后端接口保持冻结；正式数据库写回可在队友后续提供仓储业务 API 后接入。</div></div>
    </div>}

    {tab === 'resources' && <div className="card-grid two">{(snapshot?.warehouses ?? []).map((w) => { const rs = (snapshot?.resources ?? []).filter((r) => r.warehouse_id === w.warehouse_id); const inUse = baselinePlan?.warehouse.operations.filter((o) => rs.some((r) => r.resource_id === o.resource_id)).length ?? 0; return <div className="panel" key={w.warehouse_id}><div className="warehouse-top"><div><span className="warehouse-mark"><span /></span><div><h3>{w.warehouse_id}</h3><p>{w.node_id}</p></div></div><div className="chips-inline">{w.temperature_zones.map((z) => <span key={z} className={`zone zone-${z}`}>{z === 'chilled' ? '冷藏' : '冷冻'}</span>)}</div></div><div className="resource-list">{rs.map((r) => <div className="resource-row" key={r.resource_id}><span><b>{r.resource_id}</b> · {r.resource_kind}</span><span>容量 {r.capacity_units}</span><span>{r.unavailable_windows.length ? `${r.unavailable_windows.length} 个不可用窗口` : '当前可用'}</span></div>)}</div><div className="mini-stats"><span><b>{inUse}</b><small>当前方案作业</small></span><span><b>{w.temperature_zones.length}</b><small>温区</small></span></div></div>; })}</div>}
  </div>;
}
