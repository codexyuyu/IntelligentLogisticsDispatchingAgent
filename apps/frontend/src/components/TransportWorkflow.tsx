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
  sequence: number;
  node_id: string;
  task_ids: string[];
  arrival_s: number;
  service_start_s: number;
  departure_s: number;
};
type Route = {
  vehicle_id: string;
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

const SCHEDULE_KEY = "dsh_transport_schedule_id";
const STEPS = ["read", "solve", "result", "candidate", "commit", "verify"] as const;
type Step = (typeof STEPS)[number];

function epochOf(vehicle: Vehicle | undefined): string {
  return vehicle?.calendar.epoch_utc ?? "2026-01-01T00:00:00Z";
}

function nextDeadline(): string {
  return new Date(Date.now() + 45_000).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function fmt(value: number): string {
  return value.toLocaleString("zh-CN");
}

export function TransportWorkflow() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [matrices, setMatrices] = useState<Matrix[]>([]);
  const [orderId, setOrderId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [scheduleId, setScheduleId] = useState(() => localStorage.getItem(SCHEDULE_KEY) ?? "");
  const [job, setJob] = useState<Job | null>(null);
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

  const order = useMemo(() => orders.find((item) => item.id === orderId), [orders, orderId]);
  const vehicle = useMemo(() => vehicles.find((item) => item.id === vehicleId), [vehicles, vehicleId]);

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
      setOrderId((value) => value || orderPage.items[0]?.id || "");
      setVehicleId((value) => value || vehiclePage.items[0]?.id || "");
      setMessage(
        `已从数据库读取 ${orderPage.items.length} 个订单、${vehiclePage.items.length} 辆车、` +
        `${warehousePage.items.length} 个仓库、${matrixList.length} 个矩阵。`,
      );
    } catch (reason) {
      setError(String(reason));
      setMessage("读取主数据失败");
    }
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

  function chooseMatrix(): Matrix | undefined {
    if (!order || !vehicle) return matrices[0];
    return matrices.find((matrix) =>
      matrix.node_ids.includes(order.pickup_node_id) &&
      matrix.node_ids.includes(order.delivery_node_id) &&
      matrix.node_ids.includes(vehicle.start_node_id),
    ) ?? matrices[0];
  }

  async function submit() {
    if (!order || !vehicle) {
      setError("请选择订单和车辆");
      return;
    }
    const matrix = chooseMatrix();
    if (!matrix) {
      setError("数据库中没有可用矩阵");
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
    localStorage.removeItem(SCHEDULE_KEY);
    try {
      const scope = {
        order_ids: [order.id],
        warehouse_ids: warehouses.map((item) => item.id),
        vehicle_ids: [vehicle.id],
        epoch_utc: epochOf(vehicle),
        horizon_s: 86400,
      };
      const scheduleBody = {
        schema_version: "2.0.0",
        name: `transport-${order.external_ref}-${new Date().toISOString().slice(0, 19)}`,
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
        order_ids: [order.id],
        vehicle_ids: [vehicle.id],
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

  return (
    <section className="workflow">
      <h2>运输调度</h2>
      <ol className="steps">
        {["读取主数据", "提交求解", "路线与校验", "候选", "提交版本", "数据库回读"].map((label, index) => (
          <li key={label} className={index <= activeStep ? "done" : ""}>{label}</li>
        ))}
      </ol>
      <p className="muted">{message}</p>
      {error ? <p className="error">{error}</p> : null}

      <div className="grid-two">
        <label>
          订单（数据库）
          <select value={orderId} onChange={(event) => setOrderId(event.target.value)}>
            {orders.map((item) => (
              <option key={item.id} value={item.id}>
                {item.external_ref} · {item.status} · {item.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
        <label>
          车辆（数据库）
          <select value={vehicleId} onChange={(event) => setVehicleId(event.target.value)}>
            {vehicles.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} · {item.status} · {item.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="muted">
        矩阵：{matrices.length} 个；仓库：{warehouses.length} 个；截止时间提交时自动生成。
      </p>
      <button onClick={submit} disabled={busy || !order || !vehicle}>
        {busy && step === "solve" ? "求解中…" : "提交运输求解"}
      </button>

      {job ? (
        <div className="panel">
          <h3>作业进度</h3>
          <p>job_id <code>{job.job_id}</code> · status <b>{job.status}</b></p>
          {job.trace_id ? <p className="muted">trace {job.trace_id}</p> : null}
        </div>
      ) : null}

      {solution ? (
        <div className="panel">
          <h3>真实路线与独立校验</h3>
          <p>
            校验：<b className={solution.validation?.valid ? "ok" : "bad"}>
              {solution.validation?.valid ? "passed" : "failed"}
            </b>
            {solution.validation ? ` · rules ${solution.validation.rules_version}` : ""}
          </p>
          {solution.validation?.violations.length ? (
            <ul>{solution.validation.violations.map((item) => (
              <li key={`${item.code}-${item.field_path}`} className="error">
                {item.code} · {item.field_path} · {item.message}
              </li>
            ))}</ul>
          ) : null}
          {solution.candidate ? (
            <>
              <p className="muted">
                总里程 {fmt(solution.candidate.routes.reduce((sum, route) => sum + route.total_distance_m, 0))} m ·
                成本 {solution.candidate.cost.total_cents / 100} 元 ·
                未服务 {solution.candidate.unserved_order_ids.length}
              </p>
              {solution.candidate.routes.map((route) => (
                <div key={route.vehicle_id} className="route">
                  <h4>车辆 {route.vehicle_id.slice(0, 8)} · {fmt(route.total_distance_m)} m</h4>
                  <table>
                    <thead><tr><th>#</th><th>节点</th><th>到达 s</th><th>离开 s</th></tr></thead>
                    <tbody>
                      {solution.stops.filter((stop) => stop.task_ids.length).map((stop) => (
                        <tr key={`${stop.node_id}-${stop.sequence}`}>
                          <td>{stop.sequence}</td>
                          <td><code>{stop.node_id.slice(0, 8)}</code></td>
                          <td>{stop.arrival_s}</td>
                          <td>{stop.departure_s}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </>
          ) : <p className="error">作业没有 candidate</p>}
        </div>
      ) : null}

      {candidate ? (
        <div className="panel">
          <h3>候选与提交</h3>
          <p>candidate_id <code>{candidate.candidate_id}</code> · valid <b>{String(candidate.valid)}</b></p>
          <p className="muted">validation_report_id <code>{candidate.validation_report_id}</code></p>
          <label className="check">
            <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
            我已核对候选和校验结果，确认提交为新版本
          </label>
          <button onClick={commit} disabled={!confirmed || !candidate.valid || busy}>
            {busy ? "提交中…" : "确认提交版本"}
          </button>
        </div>
      ) : null}

      {receipt && current ? (
        <div className="panel success">
          <h3>已提交并从数据库回读</h3>
          <p>version <b>v{receipt.version_no}</b> · <code>{receipt.version_id}</code></p>
          <p>content_hash <code>{receipt.content_hash.slice(0, 16)}…</code></p>
          <p>当前版本 v{current.version.version_no} · 任务 {current.tasks.length} 条</p>
          <table>
            <thead><tr><th>task</th><th>kind</th><th>start</th><th>end</th><th>resource</th></tr></thead>
            <tbody>
              {current.tasks.map((task) => (
                <tr key={task.task_id}>
                  <td><code>{task.task_id.slice(0, 8)}</code></td>
                  <td>{task.task_kind}</td>
                  <td>{task.planned_start_s}</td>
                  <td>{task.planned_end_s}</td>
                  <td>{task.assigned_resource_ids.join(", ").slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">schedule_id <code>{scheduleId}</code>；刷新页面后仍会读取此版本。</p>
        </div>
      ) : null}

      {requestBodies.length ? (
        <details>
          <summary>请求记录（调试）</summary>
          {requestBodies.map((item, index) => (
            <pre key={`${item.label}-${index}`}>{item.label}{`\n`}{JSON.stringify(item.body, null, 2)}</pre>
          ))}
        </details>
      ) : null}
    </section>
  );
}

