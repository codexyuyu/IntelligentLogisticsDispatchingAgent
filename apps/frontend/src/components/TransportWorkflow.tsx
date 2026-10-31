import StageReplay from '../features/stageB/Replay';
import DigitalTwinMap2D from './DigitalTwinMap2D';
import type { TwinRoute } from '../appTypes';
import type { DemoMapNode, LatLng } from '../lib/liuzhouDemoMap';
import { useEffect, useMemo, useState } from "react";
import { idempotencyKey, request, type JobRef } from "../api";

type Order = {
  id: string;
  external_ref: string;
  status: string;
  pickup_node_id: string;
  delivery_node_id: string;
  pickup_window: { earliest_s: number; latest_s: number };
  delivery_window: { earliest_s: number; latest_s: number };
};
type Vehicle = {
  id: string;
  code: string;
  status: string;
  start_node_id: string;
  end_node_id: string;
  calendar: { epoch_utc: string };
};
type Warehouse = { id: string; code: string; name?: string };
type Matrix = {
  id: string;
  version: number;
  hash: string;
  node_ids: string[];
  source: string;
  observed_at: string;
};
type Page<T> = { items: T[] };
type Job = JobRef & { error_code?: string | null; error_message?: string | null };
type Stop = {
  route_id: string;
  sequence: number;
  node_id: string;
  task_ids: string[];
  arrival_s: number;
  service_start_s: number;
  departure_s: number;
};
type Route = {
  id: string;
  vehicle_id: string;
  start_node_id: string;
  end_node_id: string;
  total_distance_m: number;
  total_duration_s?: number;
  stops?: Stop[];
};
type Validation = {
  valid: boolean;
  violations: Array<{ code: string; message: string; field_path: string }>;
  rules_version: string;
};
type Solution = {
  candidate: {
    routes: Route[];
    unserved_order_ids: string[];
    cost: { total_cents: number };
  } | null;
  stops: Stop[];
  validation: Validation | null;
};
type JobResult = { kind: string; value: Solution };
type Candidate = {
  candidate_id: string;
  schedule_id: string;
  snapshot_hash: string;
  content_hash: string;
  validation_report_id: string;
  valid: boolean;
};
type Version = {
  version_id: string;
  version_no: number;
  status: string;
  content_hash: string;
  committed_at: string;
};
type Task = {
  task_id: string;
  task_kind: string;
  planned_start_s: number;
  planned_end_s: number;
  assigned_resource_ids: string[];
};
type VersionDetail = { version: Version; tasks: Task[] };
type Receipt = { version_id: string; version_no: number; content_hash: string };

type ShowcaseStop = { node_id: string; kind: string; arrival_s: number; departure_s: number; order_id?: string | null };
type ShowcaseRoute = {vehicle_id: string; stops: ShowcaseStop[]};
type ShowcasePlan = {case_id: string; baseline: ShowcaseRoute[]; points: Record<string, LatLng>;
  metrics: {baseline: {delivered_orders: number; total_orders: number; distance_m: number; objective_cents: number}};
  status: string};
const SHOWCASE_KEY = 'fault_rescue_showcase_session_v2';
function readShowcase(): ShowcasePlan | null {
  try { const raw = sessionStorage.getItem(SHOWCASE_KEY); if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || !('data' in parsed)) return null;
    const data = (parsed as {data: ShowcasePlan}).data;
    return data?.case_id === 'wenchang-three-truck-breakdown-v1' && Array.isArray(data.baseline) ? data : null;
  } catch { return null; }
}
function showcaseRoutes(data: ShowcasePlan): TwinRoute[] {
  return data.baseline.map(track => ({vehicleId:track.vehicle_id, zone:'chilled', warehouseId:'demo-depot',
    distanceM:0, durationS:track.stops.at(-1)?.arrival_s ?? 0,
    stops:track.stops.map(stop => ({nodeId:stop.node_id,
      kind: stop.kind === 'depot_start' ? 'depot_start' : stop.kind === 'depot_end' ? 'depot_end' : 'delivery',
      arrivalS:stop.arrival_s, departureS:stop.departure_s,
      orderIds:stop.order_id ? [stop.order_id] : []}))}));
}
function showcaseNodes(data: ShowcasePlan): Record<string,DemoMapNode> {
  return Object.fromEntries(Object.entries(data.points).map(([id,point])=>[id,{
    id,point,isDepot:id==='demo-depot',label:id==='demo-depot'?'文昌校区附近 · 虚拟仓库':id.replace('demo-o','订单 O'),
  }]));
}
const SCHEDULE_KEY = "dsh_transport_schedule_id";
const STEPS = ["read", "solve", "result", "candidate", "commit", "verify"] as const;
type Step = (typeof STEPS)[number];

function epochOf(vehicle: Vehicle | undefined): string {
  return vehicle?.calendar.epoch_utc ?? "2026-01-01T00:00:00Z";
}

function nextDeadline(): string {
  return new Date(Date.now() + 45_000).toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** A matrix must contain every chosen pickup, destination, and vehicle endpoint. */
export function coversSelection(matrix: Matrix, orders: Order[], vehicles: Vehicle[]): boolean {
  const available = new Set(matrix.node_ids);
  return orders.every(order => available.has(order.pickup_node_id) && available.has(order.delivery_node_id)) &&
    vehicles.every(vehicle => available.has(vehicle.start_node_id) && available.has(vehicle.end_node_id));
}

/** Stops are keyed by route_id. Never show another vehicle's stops in a route card. */
function solutionToMapRoutes(solution: Solution | null, vehicles: Vehicle[]): TwinRoute[] {
  if (!solution?.candidate) return [];
  return solution.candidate.routes.map(route => {
    const stops = solution.stops.filter(stop => stop.route_id === route.id).sort((a,b) => a.sequence - b.sequence);
    if (!stops.length) return null;
    const last = stops[stops.length-1];
    const source = vehicles.find(vehicle => vehicle.id === route.vehicle_id);
    return {
      vehicleId: route.vehicle_id, zone: 'chilled' as const, warehouseId: source?.start_node_id ?? '',
      distanceM: route.total_distance_m, durationS: route.total_duration_s ?? last.departure_s,
      stops: [
        {nodeId: route.start_node_id, kind: 'depot_start' as const, arrivalS: 0, departureS: 0, orderIds: []},
        ...stops.map(stop => ({nodeId: stop.node_id, kind: 'delivery' as const,
          arrivalS: stop.arrival_s, departureS: stop.departure_s, orderIds: stop.task_ids})),
        {nodeId: route.end_node_id, kind: 'depot_end' as const,
          arrivalS: Math.max(last.departure_s, route.total_duration_s ?? last.departure_s),
          departureS: Math.max(last.departure_s, route.total_duration_s ?? last.departure_s), orderIds: []},
      ],
    } as TwinRoute;
  }).filter((route): route is TwinRoute => route !== null);
}

export function TransportWorkflow() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [matrices, setMatrices] = useState<Matrix[]>([]);
  const [orderIds, setOrderIds] = useState<string[]>([]);
  const [vehicleIds, setVehicleIds] = useState<string[]>([]);
  const [matrixId, setMatrixId] = useState("");
  const [focusedVehicle, setFocusedVehicle] = useState<string | null>(null);
  const [scheduleId, setScheduleId] = useState(() => localStorage.getItem(SCHEDULE_KEY) ?? "");
  const [, setJob] = useState<Job | null>(null);
  const [solution, setSolution] = useState<Solution | null>(null);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [current, setCurrent] = useState<VersionDetail | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("正在读取订单、车辆与矩阵…");
  const [error, setError] = useState("");
  const [step, setStep] = useState<Step>("read");
  const [requestBodies, setRequestBodies] = useState<Array<{ label: string; body: unknown }>>([]);
  const [showcase, setShowcase] = useState<ShowcasePlan | null>(readShowcase);
  const [showcaseLoading, setShowcaseLoading] = useState(false);
  const [showcaseError, setShowcaseError] = useState('');
  const previewRoutes = useMemo(() => showcase ? showcaseRoutes(showcase) : [], [showcase]);
  const previewNodes = useMemo(() => showcase ? showcaseNodes(showcase) : {}, [showcase]);

  const selectedOrders = useMemo(() => orders.filter(item => orderIds.includes(item.id)), [orders, orderIds]);
  const selectedVehicles = useMemo(() => vehicles.filter(item => vehicleIds.includes(item.id)), [vehicles, vehicleIds]);
  const eligibleMatrices = useMemo(() => matrices.filter(matrix => coversSelection(matrix, selectedOrders, selectedVehicles)), [matrices, selectedOrders, selectedVehicles]);
  const selectedMatrix = eligibleMatrices.find(matrix => matrix.id === matrixId) ?? eligibleMatrices[0];
  const planRoutes = useMemo(() => solutionToMapRoutes(solution, vehicles), [solution, vehicles]);
  const assignedCount = solution?.candidate ? selectedOrders.length - solution.candidate.unserved_order_ids.length : null;
  const totalKm = solution?.candidate ? solution.candidate.routes.reduce((sum, route) => sum + route.total_distance_m, 0) / 1000 : null;
  const totalCost = solution?.candidate ? solution.candidate.cost.total_cents / 100 : null;
  const involvedVehicles = solution?.candidate ? solution.candidate.routes.filter(route => solution.stops.some(stop => stop.route_id === route.id && stop.task_ids.length > 0)).length : null;

  useEffect(() => {
    void loadMasterData();
    const stored = localStorage.getItem(SCHEDULE_KEY);
    if (stored) void loadCurrent(stored);
  }, []);

  function note(label: string, body: unknown) {
    setRequestBodies((items) => [...items.slice(-8), { label, body }]);
  }

  async function loadMasterData() {
    try {
      setError("");
      const [orderPage, vehiclePage, warehousePage, matrixList] = await Promise.all([
        request<Page<Order>>("/orders?limit=50"),
        request<Page<Vehicle>>("/vehicles?limit=50"),
        request<Page<Warehouse>>("/warehouses?limit=50"),
        request<Matrix[]>("/matrices"),
      ]);
      setOrders(orderPage.items);
      setVehicles(vehiclePage.items);
      setWarehouses(warehousePage.items);
      setMatrices(matrixList);
      setOrderIds(value => value.length ? value.filter(id => orderPage.items.some(item => item.id === id)) : orderPage.items.map(item => item.id));
      setVehicleIds(value => value.length ? value.filter(id => vehiclePage.items.some(item => item.id === id)) : vehiclePage.items.map(item => item.id));
      setMatrixId(value => value || matrixList[0]?.id || "");
      setMessage(
        `已从数据库读取 ${orderPage.items.length} 个订单、${vehiclePage.items.length} 辆车、` +
        `${warehousePage.items.length} 个仓库、${matrixList.length} 个矩阵。`,
      );
    } catch (reason) {
      setError(String(reason));
      setMessage("读取主数据失败");
    }
  }

  async function loadNormalShowcase() {
    setShowcaseLoading(true); setShowcaseError('');
    try {
      const data = await request<ShowcasePlan>('/integration/showcase/vehicle-breakdown/solve', {
        method:'POST', body:JSON.stringify({budget_ms:1800}),
      });
      if (!Array.isArray(data.baseline) || !data.points) throw new Error('正常计划数据不完整');
      setShowcase(data);
    } catch (reason) { setShowcaseError(String(reason)); }
    finally { setShowcaseLoading(false); }
  }

  async function loadCurrent(id = scheduleId) {
    if (!id) return;
    try {
      const detail = await request<VersionDetail>(`/schedules/${id}/versions/current`);
      setCurrent(detail);
      setReceipt((value) => value ?? {
        version_id: detail.version.version_id,
        version_no: detail.version.version_no,
        content_hash: detail.version.content_hash,
      });
      setStep("verify");
      setMessage(`已读取已提交版本 v${detail.version.version_no}，任务 ${detail.tasks.length} 条。`);
    } catch (reason) {
      setCurrent(null);
      setError(String(reason));
    }
  }

  function discardPriorCandidate() {
    setSolution(null); setCandidate(null); setConfirmed(false); setReceipt(null); setCurrent(null);
    setFocusedVehicle(null); setError(''); setJob(null); setStep('read');
    setMessage('选择已更新，请重新求解以获得与当前范围一致的路线。');
  }
  function selectOrders(ids: string[]) { discardPriorCandidate(); setOrderIds(ids); }
  function selectVehicles(ids: string[]) { discardPriorCandidate(); setVehicleIds(ids); }
  function toggleId(id: string, current: string[], update: (ids: string[]) => void) {
    update(current.includes(id) ? current.filter(value => value !== id) : [...current, id]);
  }

  async function submit() {
    if (!selectedOrders.length || !selectedVehicles.length) {
      setError("请至少选择一张订单和一辆车辆");
      return;
    }
    const matrix = selectedMatrix;
    if (!matrix) {
      setError("没有覆盖当前全部配送节点的路网矩阵。请先准备矩阵或缩小选择范围。");
      return;
    }
    setBusy(true);
    setError("");
    setSolution(null);
    setCandidate(null);
    setReceipt(null);
    setCurrent(null);
    setConfirmed(false);
    setJob(null);
    setStep("solve");
    // Previously committed versions remain available. New schedule is created on explicit submit.
    localStorage.removeItem(SCHEDULE_KEY);
    try {
      const scope = {
        order_ids: selectedOrders.map(item => item.id),
        warehouse_ids: warehouses.map((item) => item.id),
        vehicle_ids: selectedVehicles.map(item => item.id),
        epoch_utc: epochOf(selectedVehicles[0]),
        horizon_s: 86400,
      };
      const scheduleBody = {
        schema_version: "2.0.0",
        name: `transport-batch-${selectedOrders.length}orders-${new Date().toISOString().slice(0, 19)}`,
        scope,
      };
      note("create schedule", scheduleBody);
      const schedule = await request<{ schedule_id: string }>("/schedules", {
        method: "POST",
        body: JSON.stringify(scheduleBody),
      });
      setScheduleId(schedule.schedule_id);
      localStorage.setItem(SCHEDULE_KEY, schedule.schedule_id);

      const body = {
        schema_version: "2.0.0",
        scope,
        order_ids: selectedOrders.map(item => item.id),
        vehicle_ids: selectedVehicles.map(item => item.id),
        matrix_ref: { matrix_id: matrix.id, version: matrix.version, hash: matrix.hash },
        budget: {
          wall_time_ms: 3000,
          deadline_utc: nextDeadline(),
          max_candidates: 1,
          seed: 0,
        },
        objective_policy: {
          version: "1.0.0",
          optional_unserved_penalty_cents: 0,
          soft_late_cents_per_s: 0,
          makespan_cents_per_s: 0,
          disturbance_weights: {
            assignment_change: 0,
            time_shift: 0,
            order_change: 0,
            membership_change: 0,
          },
        },
      };
      note("submit transport", body);
      const accepted = await request<JobRef>("/optimizations/transport", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey() },
        body: JSON.stringify(body),
      });
      setJob(accepted);
      try { localStorage.setItem('dsh_transport_job_id', accepted.job_id); } catch { /* The visible job ID remains available for manual recovery. */ }
      setMessage(`作业 ${accepted.job_id} 已入队，等待 worker…`);
      await poll(accepted.job_id, schedule.schedule_id);
    } catch (reason) {
      setError(String(reason));
      setMessage("提交失败");
      setStep("read");
    } finally {
      setBusy(false);
    }
  }

  async function poll(jobId: string, schedule: string) {
    for (let index = 0; index < 60; index += 1) {
      if (index > 0) await new Promise((resolve) => setTimeout(resolve, 1000));
      const state = await request<Job>(`/jobs/${jobId}`);
      setJob(state);
      setMessage(`作业状态：${state.status}`);
      if (state.status === "completed") {
        const result = await request<JobResult>(`/jobs/${jobId}/result`);
        setSolution(result.value);
        setStep("result");
        setMessage("求解完成，已展示真实路线与独立校验结果。");
        await createCandidate(schedule, jobId);
        return;
      }
      if (["failed", "cancelled"].includes(state.status)) {
        throw new Error(`作业 ${state.status}: ${state.error_message ?? state.error_code ?? ""}`);
      }
    }
    throw new Error("作业超过 60 秒未完成");
  }

  async function createCandidate(schedule: string, jobId: string) {
    const body = { schema_version: "2.0.0", job_id: jobId };
    note("candidate from job", body);
    const value = await request<Candidate>(`/schedules/${schedule}/candidates/from-job`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    setCandidate(value);
    setStep("candidate");
    setMessage(`候选 ${value.candidate_id} 已生成，valid=${value.valid}；请确认后提交。`);
  }

  async function commit() {
    if (!candidate || !scheduleId || !confirmed) return;
    setBusy(true);
    setError("");
    try {
      const body = {
        schema_version: "2.0.0",
        command: {
          schedule_id: scheduleId,
          candidate_id: candidate.candidate_id,
          candidate_hash: candidate.content_hash,
          expected_active_version_id: null,
          snapshot_hash: candidate.snapshot_hash,
          idempotency_key: idempotencyKey(),
          confirmation_token: null,
        },
      };
      note("commit", body);
      const value = await request<Receipt>(`/schedules/${scheduleId}/versions/commit`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setReceipt(value);
      setStep("verify");
      const detail = await request<VersionDetail>(`/schedules/${scheduleId}/versions/current`);
      if (detail.version.version_id !== value.version_id) {
        throw new Error(
          `数据库回读不一致：commit 返回 ${value.version_id}，current 返回 ${detail.version.version_id}`,
        );
      }
      setCurrent(detail);
      setMessage(
        `提交成功，数据库已确认 v${value.version_no}；刷新后会继续读取同一版本。`,
      );
    } catch (reason) {
      setError(String(reason));
      setMessage("提交或数据库回读失败");
    } finally {
      setBusy(false);
    }
  }

  const activeStep = STEPS.indexOf(step);
  const canSolve = !busy && selectedOrders.length > 0 && selectedVehicles.length > 0 && !!selectedMatrix;
  const mapNodes = [...new Set(planRoutes.flatMap(route => route.stops.map(stop => stop.nodeId)))].sort();

  return (
    <section className="workflow transport-planner">
      <header className="tp-heading">
        <div><span className="tp-eyebrow">运输调度 / 多车辆优化</span><h2>运输智能调度工作台</h2>
          <p>从数据库选择订单与冷藏车，计算多车分配并检查路线、里程和配送约束。</p></div>
        <a className="btn btn-ghost btn-sm" href="#/events">进入异常处置 →</a>
      </header>
      <div className="tp-kpis">
        <div><small>数据库订单</small><strong>{orders.length}</strong><span>本次已选 {selectedOrders.length}</span></div>
        <div><small>可用车辆资源</small><strong>{vehicles.length}</strong><span>本次已选 {selectedVehicles.length}</span></div>
        <div><small>仓库</small><strong>{warehouses.length}</strong><span>当前数据源</span></div>
        <div><small>覆盖所选节点的矩阵</small><strong>{eligibleMatrices.length}</strong><span>库存矩阵共 {matrices.length} 份</span></div>
      </div>
      <section className="panel tp-showcase" aria-label="三车八单正常配送计划">
        <div className="tp-title"><div><h3>三车八单 · 正常配送计划</h3>
          <p>与「异常处置」使用同一文昌校区演示场景；这里展示故障前的初始分配，不冒充数据库批量求解。</p></div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void loadNormalShowcase()} disabled={showcaseLoading}>
            {showcaseLoading ? '读取中…' : showcase ? '重新读取场景' : '加载三车正常计划'}</button></div>
        {showcaseError && <div className="tp-error" role="alert">{showcaseError}</div>}
        {!showcase && <div className="tp-showcase-empty">点击「加载三车正常计划」即可查看三辆冷藏车的原始分配、8 张订单和文昌校区的规划地图；无需修改数据库。</div>}
        {showcase && <>
          <div className="tp-preview-kpis"><div><small>车辆</small><b>{showcase.baseline.length} 辆</b></div>
            <div><small>计划交付</small><b>{showcase.metrics.baseline.delivered_orders}/{showcase.metrics.baseline.total_orders} 单</b></div>
            <div><small>规划里程（示例）</small><b>{(showcase.metrics.baseline.distance_m/1000).toFixed(2)} km</b></div>
            <div><small>可计算费用（示例）</small><b>¥{(showcase.metrics.baseline.objective_cents/100).toFixed(2)}</b></div></div>
          <div className="tp-preview-routes">{showcase.baseline.map((route,i)=><button key={route.vehicle_id} type="button"
            onClick={()=>setFocusedVehicle(focusedVehicle===route.vehicle_id?null:route.vehicle_id)}
            className={focusedVehicle===route.vehicle_id?'selected':''}>
            <span className="tp-route-dot" style={{background:['#138b74','#ce8b30','#3b77b6'][i%3]}} />
            <strong>冷藏车 {String(i+1).padStart(2,'0')}</strong>
            <small>{route.stops.filter(stop=>stop.kind==='delivery').map(stop=>stop.order_id?.replace('demo-o','O')).filter(Boolean).join(' → ')}</small>
          </button>)}</div>
          <DigitalTwinMap2D routes={previewRoutes} nodeIds={Object.keys(previewNodes)} demoNodes={previewNodes}
            simTimeS={0} selectedVehicleId={focusedVehicle} onPickVehicle={setFocusedVehicle} height={340}/>
          <div className="tp-preview-foot"><span>示范计划的路线和费用来自固定合成场景；真实数据库调度见下方工作台。</span>
            <a className="btn btn-primary btn-sm" href="#/events">查看途中故障与智能接管 →</a></div>
        </>}
      </section>
      <div className="tp-workbench">
        <section className="panel tp-setup">
          <div className="tp-title"><div><h3>配置调度任务</h3><p>可批量勾选；求解器自行决定车辆与订单的匹配。</p></div></div>
          <div className="tp-pick-head"><strong>配送订单 <em>{selectedOrders.length}/{orders.length}</em></strong>
            <div><button type="button" disabled={busy} onClick={() => selectOrders(orders.map(item => item.id))}>全选</button>
              <button type="button" disabled={busy} onClick={() => selectOrders([])}>清空</button></div></div>
          <div className="tp-check-list" role="group" aria-label="批量选择配送订单">
            {orders.map(item => <label key={item.id} className="tp-check">
              <input type="checkbox" disabled={busy} checked={orderIds.includes(item.id)} onChange={() => toggleId(item.id, orderIds, selectOrders)} />
              <span><b>{item.external_ref}</b><small>{item.status} · {item.delivery_node_id.slice(0,8)}</small></span>
              <small>最晚 {item.delivery_window.latest_s}s</small>
            </label>)}
            {!orders.length && <p className="muted">当前没有订单，请先在「订单与库存」准备任务。</p>}
          </div>
          <div className="tp-pick-head"><strong>参与求解的车辆 <em>{selectedVehicles.length}/{vehicles.length}</em></strong>
            <div><button type="button" disabled={busy} onClick={() => selectVehicles(vehicles.map(item => item.id))}>全选</button>
              <button type="button" disabled={busy} onClick={() => selectVehicles([])}>清空</button></div></div>
          <div className="tp-check-list tp-vehicle-list" role="group" aria-label="批量选择参与调度车辆">
            {vehicles.map(item => <label key={item.id} className="tp-check">
              <input type="checkbox" disabled={busy} checked={vehicleIds.includes(item.id)} onChange={() => toggleId(item.id, vehicleIds, selectVehicles)} />
              <span><b>{item.code}</b><small>{item.status} · {item.start_node_id.slice(0,8)}</small></span>
            </label>)}
            {!vehicles.length && <p className="muted">当前没有车辆，请先准备车辆资源。</p>}
          </div>
          <label className="tp-matrix-label">路网与行驶时间矩阵
            <select value={selectedMatrix?.id ?? ''} onChange={event => { discardPriorCandidate(); setMatrixId(event.target.value); }} disabled={busy || !eligibleMatrices.length}>
              {!eligibleMatrices.length && <option value="">无可用矩阵</option>}
              {eligibleMatrices.map(matrix => <option value={matrix.id} key={matrix.id}>{matrix.source} · v{matrix.version} · {matrix.node_ids.length} 节点</option>)}
            </select>
          </label>
          {!eligibleMatrices.length && <div className="tp-warning" role="status">{matrices.length === 0
            ? '当前数据库尚无路网矩阵。真实批量求解需要先准备距离与行驶时间矩阵；本页不会自动编造矩阵。'
            : '现有矩阵未覆盖当前选择的全部取送点及车辆起终点，请调整订单、车辆范围或补充矩阵。'}</div>}
          <div className="tp-policy"><b>优化目标</b><span>当前使用后端固定的综合费用目标；车辆容量、时间窗等约束由求解器校验。</span></div>
          <button className="btn btn-primary tp-solve" type="button" disabled={!canSolve} onClick={() => void submit()}>
            {busy ? '正在求解与校验…' : `运行 OR-Tools 批量调度（${selectedOrders.length} 单 / ${selectedVehicles.length} 车）`}
          </button>
        </section>
        <section className="panel tp-result">
          <div className="tp-title"><div><h3>求解结果总览</h3><p>全部指标来自本次后端候选方案，不包含模拟地图的几何距离。</p></div>
            <span className={`tp-status ${solution?.validation?.valid ? 'good' : ''}`}>{solution ? solution.validation?.valid ? '约束校验通过' : '校验未通过' : busy ? '求解中' : '等待求解'}</span></div>
          <div className="tp-result-kpis">
            <div><small>投入配送车辆</small><strong>{involvedVehicles ?? '—'}</strong></div>
            <div><small>已分配订单</small><strong>{assignedCount === null ? '—' : `${assignedCount}/${selectedOrders.length}`}</strong></div>
            <div><small>总运输里程</small><strong>{totalKm === null ? '—' : `${totalKm.toFixed(2)} km`}</strong></div>
            <div><small>综合费用</small><strong>{totalCost === null ? '—' : `¥${totalCost.toFixed(2)}`}</strong></div>
          </div>
          <div className="tp-progress"><strong>方案生成进度</strong><ol className="steps">{["数据读取", "提交求解", "路线校验", "候选生成", "人工确认", "版本回读"].map((label, index) =>
            <li key={label} className={index <= activeStep ? 'done' : ''}>{label}</li>)}</ol></div>
          <p className="muted" role="status">{message}</p>
          {error && <div className="tp-error" role="alert">{error}</div>}
          {!solution && <div className="tp-empty">完成订单、车辆和矩阵选择后，点击批量调度。求解成功后这里显示真实车辆路线及约束校验。</div>}
          {solution?.candidate && <div className="tp-plan-summary"><strong>方案检查</strong><span>未服务订单：{solution.candidate.unserved_order_ids.length} 单</span>
            <span>校验：{solution.validation?.valid ? '通过' : '未通过'} · {solution.validation?.rules_version ?? '未提供规则版本'}</span></div>}
          {solution?.validation?.violations.map(item => <div className="tp-error" key={`${item.code}-${item.field_path}`}>{item.code} · {item.message}</div>)}
        </section>
      </div>
      {solution?.candidate && <div className="panel tp-routes">
        <div className="tp-title"><div><h3>车辆任务分配与停靠顺序</h3><p>可逐辆展开检查节点、配送任务和预计到达时间。</p></div></div>
        <div className="tp-route-grid">{solution.candidate.routes.map((route, i) => {
          const stops = solution.stops.filter(stop => stop.route_id === route.id).sort((a,b) => a.sequence-b.sequence);
          const name = vehicles.find(vehicle => vehicle.id === route.vehicle_id)?.code ?? `车辆 ${route.vehicle_id.slice(0,8)}`;
          return <div className="tp-route-card" key={route.id}>
            <button className="tp-route-head" type="button" onClick={() => setFocusedVehicle(focusedVehicle === route.vehicle_id ? null : route.vehicle_id)}>
              <span className="tp-route-dot" style={{background:['#138b74','#ce8b30','#3b77b6','#a75ca9','#b85d4f'][i%5]}} />
              <b>{name}</b><span>{stops.length} 站 · {(route.total_distance_m/1000).toFixed(2)} km</span><span>{focusedVehicle === route.vehicle_id ? '收起' : '查看路线'}</span>
            </button>
            {(focusedVehicle === route.vehicle_id || (focusedVehicle === null && solution.candidate!.routes.length <= 3)) && <div className="tp-stop-list">
              <div>仓库出发</div>{stops.map((stop,index) => <div key={`${route.id}-${stop.sequence}-${index}`}>
                <span>{stop.sequence + 1}</span><b>{stop.node_id.slice(0, 8)}</b>
                <small>{stop.task_ids.length ? `${stop.task_ids.length} 项任务` : '途经节点'} · 到达 {stop.arrival_s}s / 离开 {stop.departure_s}s</small>
              </div>)}<div>返回仓库</div>
            </div>}
          </div>;
        })}</div>
        {planRoutes.length > 0 && <><div className="tp-title tp-map-heading"><div><h3>文昌校区 · 多车规划路线</h3><p>地图线路为示意几何，车辆与停靠顺序来自本次真实求解结果。</p></div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setFocusedVehicle(null)}>显示全部路线</button></div>
          <DigitalTwinMap2D routes={planRoutes} nodeIds={mapNodes} simTimeS={0}
            selectedVehicleId={focusedVehicle} onPickVehicle={setFocusedVehicle} height={430}/></>}
      </div>}
      {candidate && <div className="panel tp-approval"><div><h3>候选方案确认</h3>
        <p>候选校验：{candidate.valid ? '通过' : '未通过'}。提交版本将写入后端，请在核对后手动确认。</p></div>
        <label className="check"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />我已核对车辆分配、时间和约束，确认提交</label>
        <button className="btn btn-primary" onClick={() => void commit()} disabled={!confirmed || !candidate.valid || busy}>{busy ? '提交中…' : '确认提交候选版本'}</button>
      </div>}
      {receipt && current && <div className="panel success"><h3>方案已提交并回读</h3>
        <p>生效版本 v{receipt.version_no} · 已回读 {current.tasks.length} 条任务</p>
        <small>版本标识 {receipt.version_id.slice(0,8)} · 可再次打开页面查阅。</small>
      </div>}
      <details className="tp-history"><summary>历史联合运行与运输回放</summary><StageReplay mode="transport" /></details>
      {requestBodies.length > 0 && <details className="tp-history"><summary>技术请求明细</summary>{requestBodies.map((item,i) =>
        <pre key={`${item.label}-${i}`}>{item.label}{'\n'}{JSON.stringify(item.body,null,2)}</pre>)}</details>}
    </section>
  );
}
