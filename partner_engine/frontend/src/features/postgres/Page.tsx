import { useCallback, useEffect, useMemo, useState } from 'react';
import SectionHeader from '../../components/SectionHeader';
import DigitalTwin3D from '../../components/DigitalTwin3D';
import { useSimClock } from '../../hooks/useSimClock';
import type { TwinRoute } from '../../appTypes';
import {
  pgBase, pgRequest, prettyDate, safeText, secondsLabel,
  type PgParameters, type PgPreview, type PgReadiness, type PgRow, type PgSavedDetail,
  type PgSavedItem, type PgSavedList, type PgSaveResult, type PgSummary, type ResourceResponse,
} from './api';

type Tab = 'orders' | 'vehicles' | 'route' | 'saved';
const tabs: { id: Tab; name: string }[] = [
  { id: 'orders', name: '实际订单' }, { id: 'vehicles', name: '实际车辆' },
  { id: 'route', name: '运行路线预览' }, { id: 'saved', name: '归档与地图' },
];
const baseParams: PgParameters = {
  warehouse_code: 'WH001', temperature_zone: 'chilled', speed_kmh: 30,
  budget_ms: 5000, max_orders: 20, acknowledge_simulation_only: true,
  travel_mode: 'straight_line_simulation', business_mode: 'legacy_simulation',
};

function RouteSummary({ preview }: { preview: PgPreview }) {
  const routes = preview.result?.routes ?? [];
  const missing = preview.result?.unserved_orders ?? [];
  const validated = preview.independent_validation === 'passed' && preview.result?.metadata?.has_solution && missing.length === 0;
  return <div className="pg-route-results">
    <div className="pg-stats">
      <div><span>求解器</span><b>{safeText(preview.solver_status)}</b></div>
      <div><span>校验</span><b className={validated ? 'pg-success' : 'pg-warning'}>{safeText(preview.independent_validation)}</b></div>
      <div><span>本次选中</span><b>{safeText(preview.selected_orders)} 单</b></div>
      <div><span>模拟路线</span><b>{routes.length} 条</b></div>
      <div><span>未服务</span><b>{missing.length} 单</b></div>
    </div>
    {routes.map((route) => <div className="pg-route-card" key={route.vehicle_id}>
      <h4>{route.vehicle_id} · {(route.distance_m / 1000).toFixed(2)} km（{preview.distance_type === 'OSRM_road_network_estimate' ? 'OSRM 道路估计' : '直线'}） · {secondsLabel(route.duration_s)}（{preview.travel_mode === 'osrm_road_estimate' ? '道路估计' : '模拟'}）</h4>
      <div className="pg-stop-list">{route.stops.map((stop, index) =>
        <span key={`${route.vehicle_id}-${index}`} className="pg-stop-chip" title={`到达 ${secondsLabel(stop.arrival_at_s)} · 服务 ${secondsLabel(stop.service_start_at_s)}`}>
          {stop.stop_kind === 'delivery' ? stop.order_ids.join('、') || stop.node_id : stop.node_id}
        </span>)}</div>
    </div>)}
    {preview.assumptions?.length > 0 && <details className="pg-assumptions"><summary>查看模拟假设（{preview.assumptions.length} 项）</summary>
      <ul>{preview.assumptions.map((line, i) => <li key={i}>{line}</li>)}</ul></details>}
  </div>;
}

export default function PostgresPage() {
  const [tab, setTab] = useState<Tab>('route');
  const [summary, setSummary] = useState<PgSummary | null>(null);
  const [readiness, setReadiness] = useState<PgReadiness | null>(null);
  const [orders, setOrders] = useState<ResourceResponse | null>(null);
  const [vehicles, setVehicles] = useState<ResourceResponse | null>(null);
  const [saved, setSaved] = useState<PgSavedItem[]>([]);
  const [selectedCode, setSelectedCode] = useState('');
  const [detail, setDetail] = useState<PgSavedDetail | null>(null);
  const [params, setParams] = useState<PgParameters>(baseParams);
  const [preview, setPreview] = useState<PgPreview | null>(null);
  const [allowSave, setAllowSave] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [archiveError, setArchiveError] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [show3D, setShow3D] = useState(false);
  const [followVehicleId, setFollowVehicleId] = useState<string | null>(null);
  const [selected3DVehicle, setSelected3DVehicle] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [s, o, v] = await Promise.all([
        pgRequest<PgSummary>('/summary'),
        pgRequest<ResourceResponse>('/orders'),
        pgRequest<ResourceResponse>('/vehicles'),
      ]);
      setSummary(s); setOrders(o); setVehicles(v);
      try { setReadiness(await pgRequest<PgReadiness>('/readiness')); }
      catch { setReadiness(null); }
      setParams((before) => ({ ...before, warehouse_code: s.warehouses.includes(before.warehouse_code) ? before.warehouse_code : (s.warehouses[0] || before.warehouse_code) }));
    } catch (cause) { setError(cause instanceof Error ? cause.message : '读取失败'); }
    finally { setLoading(false); }
  }, []);
  const refreshSaved = useCallback(async () => {
    try {
      const list = await pgRequest<PgSavedList>('/saved?limit=30');
      setSaved(list.items); setArchiveError('');
    } catch (cause) { setArchiveError(cause instanceof Error ? cause.message : '归档不可用'); }
  }, []);
  useEffect(() => { void refreshData(); void refreshSaved(); }, [refreshData, refreshSaved]);

  const warehouses = summary?.warehouses ?? [];
  const canSave = preview?.independent_validation === 'passed' && preview?.result?.metadata?.has_solution === true
    && preview.result?.unserved_orders?.length === 0 && (preview.result?.routes?.length ?? 0) > 0;
  const routeMapUrl = selectedCode ? `${pgBase}/saved/${encodeURIComponent(selectedCode)}/map` : '';
  const savedMeta = useMemo(() => saved.find((s) => s.preview_code === selectedCode), [saved, selectedCode]);
  const previewRoutes = useMemo((): TwinRoute[] => {
    if (!preview?.result?.routes) return [];
    const roadByVehicle = new Map((preview.demo_route_geojson?.features ?? [])
      .filter((feature) => feature.geometry?.type === 'LineString' && feature.properties?.distance_type === 'OSRM_road_network_estimate')
      .map((feature) => [feature.properties.vehicle_id, feature] as const));
    return preview.result.routes.map((r) => {
      const road = roadByVehicle.get(r.vehicle_id);
      return { vehicleId: r.vehicle_id, warehouseId: params.warehouse_code,
        zone: params.temperature_zone, distanceM: r.distance_m, durationS: r.duration_s,
        stops: r.stops.map((stop) => ({ nodeId: stop.node_id, kind: stop.stop_kind as TwinRoute['stops'][number]['kind'],
          orderIds: stop.order_ids, arrivalS: stop.arrival_at_s, departureS: stop.departure_at_s })),
        roadCoordinates: road?.geometry.coordinates, stopCoordinates: road?.properties.stop_coordinates };
    });
  }, [preview, params.warehouse_code, params.temperature_zone]);
  const previewHorizon = Math.max(1800, ...previewRoutes.flatMap((r) => r.stops.map((s) => s.departureS)));
  const replay = useSimClock(previewHorizon, false);
  const previewNodeIds = useMemo(() => [...new Set(previewRoutes.flatMap((r) => r.stops.map((s) => s.nodeId)))], [previewRoutes]);
  const hasOsrmPaths = previewRoutes.length > 0 && previewRoutes.every((r) => (r.roadCoordinates?.length ?? 0) >= 2 && r.stopCoordinates?.length === r.stops.length);


  function updateParams<K extends keyof PgParameters>(name: K, value: PgParameters[K]) {
    setParams((before) => ({ ...before, [name]: value }));
    setPreview(null); setActionMessage(''); setAllowSave(false);
  }
  async function solve() {
    setBusy(true); setError(''); setActionMessage(''); setPreview(null); setAllowSave(false); setShow3D(false); replay.pause(); replay.seek(0);
    try { setPreview(await pgRequest<PgPreview>('/route', params)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : '路线求解失败'); }
    finally { setBusy(false); }
  }
  async function archive() {
    if (!canSave || !allowSave || busy) return;
    setBusy(true); setError(''); setActionMessage('');
    try {
      // R22 intentionally re-solves on fresh DB data; no client route is submitted.
      const value = await pgRequest<PgSaveResult>('/saved', { ...params, acknowledge_store_simulation_only: true });
      setActionMessage(`模拟方案已保存：${value.preview_code}；业务正式方案未修改。`);
      setSelectedCode(value.preview_code); setDetail(null); setTab('saved');
      await refreshSaved();
      await viewSaved(value.preview_code);
    } catch (cause) { setError(cause instanceof Error ? cause.message : '归档失败'); }
    finally { setBusy(false); setAllowSave(false); }
  }
  async function viewSaved(code: string) {
    setSelectedCode(code); setDetail(null); setArchiveError('');
    try { setDetail(await pgRequest<PgSavedDetail>(`/saved/${encodeURIComponent(code)}`)); }
    catch (cause) { setArchiveError(cause instanceof Error ? cause.message : '读取归档失败'); }
  }

  return <div className="pg-console">
    <SectionHeader title="PostgreSQL 冷链调度台" desc="R30-A：补录业务字段来源可辨认；可选 OSRM 道路估计及模拟方案归档。" />
    <div className="pg-warning"><b>模拟预览 · 不可执行</b>：可选择 PostGIS 直线假设或 OSRM 道路估计；OSRM 不含实时拥堵。R24 业务字段仅在补录完整后可用；R30-A 合成扩展数据必须明确标注为演示，不代表真实运营。归档仅在独立演示表。</div>
    {error && <div className="pg-error" role="alert">{error}</div>}
    {actionMessage && <div className="pg-ok" role="status">{actionMessage}</div>}
    <div className="pg-stats pg-top-stats">
      <div><span>实库订单</span><b>{summary?.orders ?? '—'}</b></div>
      <div><span>车辆</span><b>{summary?.vehicles ?? '—'}</b></div>
      <div><span>地理节点</span><b>{summary?.nodes ?? '—'}</b></div>
      <div><span>距离记录</span><b>{summary?.distance_pairs ?? '—'}</b></div>
      <div><span>来源</span><b>{summary ? 'PostgreSQL 只读' : '等待连接'}</b></div>
    </div>
    {summary && <div className={`pg-hint ${summary.r26_single_warehouse_ready ? "pg-ok" : "pg-warning"}`} role="status">R29 单仓业务检查：{summary.r29_active_warehouse ? "现役仓库仅 WH001；四辆车统一归属 WH001。WH002 只作为 4 条历史路线的外键存根保留，不参与新调度；原历史数据未改写。" : summary.r26_single_warehouse_ready ? "当前调度输入只有 WH001，请先核查数据库迁移状态与历史数据。" : `当前数据库仓库节点：${(summary.warehouse_nodes ?? summary.warehouses).join("、")}；尚未执行 R29 单仓现役迁移。请在 backend 运行 .\migrate_pg_r29_local.ps1 做只读预检；本页面不自动写数据库。`}</div>}
    <div className="pg-hint" role="status">R24 扩展业务数据：{readiness ? (readiness.complete ? '已录入基础资料（仍需核查业务一致性）' : readiness.tables_installed ? '资料尚未齐全：' + Object.entries(readiness.missing ?? {}).map(([k,v])=>`${k} ${v}`).join(' / ') : '尚未安装增量表（旧功能可继续使用）') : '扩展资料状态不可用'}。</div>
    {readiness?.provenance?.source_kind==='explicit_synthetic_demo'&&<div className="pg-warning" role="status"><b>R30-A PostgreSQL 合成演示资料</b>：订单编号和基础重量来自实库；新补的库存批次、体积、班次和工时是生成的演示参数，不能当作真实经营数据。</div>}
    <div className="pg-toolbar"><div className="pg-tabs" role="tablist" aria-label="实库调度功能">
      {tabs.map((item) => <button key={item.id} type="button" role="tab" aria-selected={tab === item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)}>{item.name}</button>)}
    </div><button className="btn btn-ghost btn-sm" disabled={loading || busy} onClick={() => { void refreshData(); void refreshSaved(); }}>{loading ? '正在刷新…' : '刷新实库数据'}</button></div>

    {tab === 'orders' && <section className="panel"><div className="panel-title-row"><div><h3>数据库订单清单</h3><p>来自 v_dispatch_orders；字段未填的业务含义不自动推测。</p></div><span className="soft-badge">{orders?.count ?? 0} 条</span></div>
      <div className="table-wrap"><table><thead><tr><th>订单</th><th>客户</th><th>重量 kg</th><th>温度 ℃</th><th>服务时间窗</th><th>服务分钟</th></tr></thead><tbody>
        {(orders?.rows ?? []).map((row: PgRow, index) => <tr key={String(row.order_code ?? index)}><td><strong>{safeText(row.order_code)}</strong></td><td>{safeText(row.customer_name)}</td><td>{safeText(row.weight_kg)}</td><td>{safeText(row.min_temp_c)} ~ {safeText(row.max_temp_c)}</td><td>{prettyDate(row.window_start)} – {prettyDate(row.window_end)}</td><td>{safeText(row.service_minutes)}</td></tr>)}
      </tbody></table></div></section>}
    {tab === 'vehicles' && <section className="panel"><div className="panel-title-row"><div><h3>数据库车辆清单</h3><p>来自 v_dispatch_vehicles；温度为真实表字段，不等于已经完成冷链温区业务建模。</p></div><span className="soft-badge">{vehicles?.count ?? 0} 辆</span></div>
      <div className="table-wrap"><table><thead><tr><th>车辆</th><th>仓库</th><th>载重 kg</th><th>最低温 ℃</th><th>最高温 ℃</th></tr></thead><tbody>
        {(vehicles?.rows ?? []).map((row: PgRow, index) => <tr key={String(row.vehicle_code ?? index)}><td><strong>{safeText(row.vehicle_code)}</strong></td><td>{safeText(row.warehouse_code)}</td><td>{safeText(row.capacity_kg)}</td><td>{safeText(row.min_temp_c)}</td><td>{safeText(row.max_temp_c)}</td></tr>)}
      </tbody></table></div></section>}
    {tab === 'route' && <section className="panel pg-run-panel">
      <div className="panel-title-row"><div><h3>R20 OR-Tools 路线求解 · R24 业务适配</h3><p>单仓、单温区、单趟；可选 OSRM 和真实补录的装载/仓储参数。</p></div><span className="soft-badge">不写数据库</span></div>
      <div className="pg-form">
        <label>所属仓库<select value={params.warehouse_code} onChange={(e) => updateParams('warehouse_code', e.target.value)}>{(warehouses.length ? warehouses : [params.warehouse_code]).map((id) => <option key={id} value={id}>{id}</option>)}</select></label>
        <label>温区<select value={params.temperature_zone} onChange={(e) => updateParams('temperature_zone', e.target.value as 'chilled' | 'frozen')}><option value="chilled">冷藏 chilled</option><option value="frozen">冷冻 frozen</option></select></label>
        <label>行驶矩阵来源<select value={params.travel_mode} onChange={(e)=>updateParams('travel_mode', e.target.value as PgParameters['travel_mode'])}><option value="straight_line_simulation">PostGIS 直线 + 假设速度</option><option value="osrm_road_estimate">OSRM 道路估计（需服务）</option></select></label>
        <label>业务字段来源<select value={params.business_mode} onChange={(e)=>updateParams('business_mode', e.target.value as PgParameters['business_mode'])}><option value="legacy_simulation">R23 演示假设（保留）</option><option value="verified_r24" disabled={!readiness?.complete}>R24 补录业务字段（演示 / 人工录入来源）</option></select></label>
        <label>演示速度 km/h<input type="number" min={1} max={100} disabled={params.travel_mode === 'osrm_road_estimate'} value={params.speed_kmh} onChange={(e) => updateParams('speed_kmh', Number(e.target.value))}/></label>
        <label>单次预算 ms<input type="number" min={500} max={20000} value={params.budget_ms} onChange={(e) => updateParams('budget_ms', Number(e.target.value))}/></label>
        <label>订单上限<input type="number" min={1} max={20} value={params.max_orders} onChange={(e) => updateParams('max_orders', Number(e.target.value))}/></label>
      </div>
      <div className="pg-actions"><button className="btn btn-primary" disabled={busy || loading || !summary} onClick={() => void solve()}>{busy ? '正在处理…' : '运行模拟路线预览'}</button>
      <span className="pg-hint">OSRM 模式需要后端 OSRM_BASE_URL；失败时不会偷偷回退到直线。</span></div>
      {preview && <>{preview.business_fact_origin==='r30a_explicit_synthetic_demo'&&<div className="pg-warning" role="status">本路线使用了 PostgreSQL 内已标记的 R30-A 合成演示业务参数，非真实库存或车辆班次。</div>}<RouteSummary preview={preview}/>
        <div className="r25-showcase-toolbar"><div><strong>R25 · 3D 道路动态回放</strong>
          <small>{hasOsrmPaths ? '路线几何来自 OSRM driving，预计行驶时间不含实时拥堵；车速动画按规划时间映射。' : '当前是 PostGIS 直线矩阵，3D 使用示意道路布局，不是实际道路。'} 求解器使用的车辆数为 {previewRoutes.length} 辆。</small></div>
          <button type="button" className="btn btn-primary" onClick={() => { setShow3D((old) => !old); replay.seek(0); }}>
            {show3D ? '收起 3D 回放' : '打开 3D 回放'}
          </button></div>
        {show3D && <>
          <div className="r25-fleet-picker"><button className={`btn btn-sm ${followVehicleId === null ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFollowVehicleId(null)}>全局视角</button>
            {previewRoutes.map((r) => <button key={r.vehicleId} className={`btn btn-sm ${followVehicleId === r.vehicleId ? 'btn-primary' : 'btn-ghost'}`} onClick={() => { setFollowVehicleId(r.vehicleId); setSelected3DVehicle(r.vehicleId); }}>{r.vehicleId} · 跟车</button>)}
          </div>
          <DigitalTwin3D routes={previewRoutes} warehouses={[{id:params.warehouse_code,zones:[params.temperature_zone]}]}
            nodeIds={previewNodeIds} orderCount={preview.selected_orders} simTimeS={replay.t} getTime={replay.getTime}
            selectedVehicleId={selected3DVehicle} followVehicleId={followVehicleId}
            onPickVehicle={setSelected3DVehicle} eventActive={false} height={490}/>
          <div className="r25-pg-player"><button className="btn btn-primary" onClick={replay.toggle}>{replay.playing ? '暂停' : '播放'}</button>
            <label>倍速 <select value={replay.speed} onChange={(e) => replay.setSpeed(Number(e.target.value))}>
              {[1,4,16,64,256,512].map((v) => <option key={v} value={v}>{v}x</option>)}
            </select></label>
            <input aria-label="R25 路线回放进度" type="range" min={0} max={previewHorizon} step={1} value={Math.round(replay.t)} onChange={(e) => replay.seek(Number(e.target.value))}/>
            <strong>{secondsLabel(replay.t)} / {secondsLabel(previewHorizon)}</strong></div>
        </>}
        <div className="pg-save-panel"><label><input type="checkbox" checked={allowSave} onChange={(e) => setAllowSave(e.target.checked)} disabled={!canSave || busy}/> 我确认仅保存演示模拟路线，不能作为真实业务配送方案</label>
        <button className="btn btn-primary" disabled={!canSave || !allowSave || busy} onClick={() => void archive()}>{busy ? '正在重新求解并保存…' : '归档到独立模拟表'}</button>
        <small>保存时后端会从数据库重新读取并求解，不会盲信浏览器内的预览结果。</small></div>
      </>}
    </section>}
    {tab === 'saved' && <section className="panel"><div className="panel-title-row"><div><h3>已保存模拟方案</h3><p>仅展示独立 pg_simulation_previews 表；按归档时的模式展示 OSRM 道路估计或 PostGIS 直线示意。</p></div><button className="btn btn-ghost btn-sm" onClick={() => void refreshSaved()}>刷新归档</button></div>
      {archiveError && <div className="pg-error" role="alert">归档接口：{archiveError}</div>}
      <div className="pg-archive-grid"><div className="pg-archive-list">
        {!saved.length && !archiveError && <p className="pg-hint">还没有保存的模拟方案。请在“运行路线预览”中求解后勾选确认并归档。</p>}
        {saved.map((item) => <button type="button" key={item.preview_code} onClick={() => void viewSaved(item.preview_code)} className={`pg-archive-item ${selectedCode === item.preview_code ? 'active' : ''}`}>
          <b>{item.preview_code}</b><span>{item.warehouse_code} · {item.temperature_zone} · {item.selected_orders} 单 / {item.selected_vehicles} 辆</span><small>{prettyDate(item.created_at)}</small>
        </button>)}
      </div><div className="pg-map-area">
        {selectedCode ? <><div className="pg-map-heading"><strong>{selectedCode}</strong><span>R24 归档路线 · 不含实时路况、不可执行</span></div>
          <iframe title={`模拟路线地图 ${selectedCode}`} src={routeMapUrl} className="pg-map-frame" loading="lazy" referrerPolicy="same-origin" />
          <a className="pg-map-link" href={routeMapUrl} target="_blank" rel="noopener noreferrer">在新窗口打开地图 ↗</a>
          {savedMeta && <p className="pg-hint">{savedMeta.warehouse_code} / {savedMeta.temperature_zone} · {prettyDate(savedMeta.created_at)}</p>}
          {detail && <RouteSummary preview={detail.preview}/>}</> : <div className="pg-map-empty">从左侧选择一个已保存的模拟方案，即可查看路线地图和站点。</div>}
      </div></div>
    </section>}
    <p className="pg-footer-note">R24 仍仅供本机演示。正式生产业务表 dispatch_plans / routes / route_stops 未由本模块写入；原有数字孪生模块使用独立场景数据。</p>
  </div>;
}
