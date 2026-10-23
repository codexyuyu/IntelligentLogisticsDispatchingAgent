import { useEffect, useState } from "react";
import {
  getToken,
  idempotencyKey,
  request,
  setToken,
  type JobRef,
  type JobResult,
  type Page,
} from "./api";

type OrderView = {
  id: string;
  external_ref: string;
  status: string;
};

const TRANSPORT_TEMPLATE = {
  schema_version: "2.0.0",
  scope: {
    order_ids: [] as string[],
    warehouse_ids: [] as string[],
    vehicle_ids: [] as string[],
    epoch_utc: "2026-01-01T00:00:00Z",
    horizon_s: 86400,
  },
  order_ids: [] as string[],
  vehicle_ids: [] as string[],
  matrix_ref: {
    matrix_id: "00000000-0000-4000-8000-000000000000",
    version: 1,
    hash: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  },
  budget: {
    wall_time_ms: 3000,
    deadline_utc: "2026-01-01T00:10:00Z",
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

export default function App() {
  const [token, setTokenState] = useState(getToken());
  const [health, setHealth] = useState("unknown");
  const [orders, setOrders] = useState<OrderView[]>([]);
  const [transportBody, setTransportBody] = useState(
    JSON.stringify(TRANSPORT_TEMPLATE, null, 2),
  );
  const [job, setJob] = useState<JobRef | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    request<{ status: string }>("/health")
      .then((value) => setHealth(value.status))
      .catch((reason: unknown) => setError(String(reason)));
  }, [token]);

  async function loadOrders() {
    try {
      setError("");
      const page = await request<Page<OrderView>>("/orders?limit=20");
      setOrders(page.items);
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function submitTransport() {
    try {
      setError("");
      setResult(null);
      const value = await request<JobRef>("/optimizations/transport", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey() },
        body: transportBody,
      });
      setJob(value);
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function loadResult() {
    if (!job) return;
    try {
      setError("");
      setResult(await request<JobResult>(`/jobs/${job.job_id}/result`));
    } catch (reason) {
      setError(String(reason));
    }
  }

  return (
    <main>
      <header>
        <div>
          <h1>Logistics Workbench</h1>
          <p className="muted">
            React shell for the real HTTP contract. No business rule is duplicated here.
          </p>
        </div>
        <button className="secondary" onClick={() => setHealth("unknown")}>
          reset health
        </button>
      </header>

      <section>
        <h2>Credential</h2>
        <div className="row">
          <input
            type="text"
            value={token}
            placeholder="Bearer token"
            onChange={(event) => {
              setTokenState(event.target.value);
              setToken(event.target.value);
            }}
          />
        </div>
        <p className="muted">Token stays in localStorage; it is not sent anywhere except the API.</p>
        <p>health: {health}</p>
      </section>

      <section>
        <h2>Master data</h2>
        <button onClick={loadOrders}>load orders</button>
        <ul>
          {orders.map((order) => (
            <li key={order.id}>
              {order.external_ref} · {order.status} · <code>{order.id}</code>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Transport optimization</h2>
        <textarea
          value={transportBody}
          onChange={(event) => setTransportBody(event.target.value)}
          spellCheck={false}
        />
        <div className="row" style={{ marginTop: "0.5rem" }}>
          <button onClick={submitTransport}>submit</button>
          <button className="secondary" onClick={loadResult} disabled={!job}>
            load result
          </button>
        </div>
        {job ? (
          <p className="muted">
            job {job.job_id} · {job.status}
          </p>
        ) : null}
      </section>

      {error ? <p className="error">{error}</p> : null}
      {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </main>
  );
}
