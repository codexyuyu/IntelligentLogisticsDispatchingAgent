import { useEffect, useState } from "react";
import { getToken, request, setToken, type JobRef, type JobResult, type Page } from "./api";
import { JsonPanel } from "./components/JsonPanel";
import { SchedulePanel } from "./components/SchedulePanel";
import { ExceptionPanel } from "./components/ExceptionPanel";
import { TransportWorkflow } from "./components/TransportWorkflow";

type OrderView = { id: string; external_ref: string; status: string };
type ChatReply = { reply: string; model: string; provider_configured: boolean; trace_id: string };
type Tab = "overview" | "schedules" | "transport" | "warehouse" | "simulation" | "incidents" | "events" | "metrics" | "reschedule" | "agent";

const TABS: readonly Tab[] = ["overview", "schedules", "transport", "warehouse", "simulation", "incidents", "events", "metrics", "reschedule", "agent"];

const TITLES: Record<Tab, string> = {
  overview: "Overview",
  schedules: "Schedules & versions",
  transport: "Transport optimization",
  warehouse: "Warehouse scheduling",
  simulation: "Simulation",
  incidents: "Incidents & reschedule",
  events: "Event ingestion",
  metrics: "Metrics",
  reschedule: "Reschedule proposal",
  agent: "Agent chat",
};

function tabFromHash(): Tab {
  const value = window.location.hash.replace(/^#\/?/, "");
  return (TABS as readonly string[]).includes(value) ? (value as Tab) : "overview";
}

const WAREHOUSE = `{
  "schema_version": "2.0.0",
  "snapshot": {},
  "tasks": [],
  "objective_policy": {
    "version": "1.0.0",
    "optional_unserved_penalty_cents": 0,
    "soft_late_cents_per_s": 0,
    "makespan_cents_per_s": 0,
    "disturbance_weights": {
      "assignment_change": 0,
      "time_shift": 0,
      "order_change": 0,
      "membership_change": 0
    }
  },
  "budget": {
    "wall_time_ms": 3000,
    "deadline_utc": "2026-01-01T00:10:00Z",
    "max_candidates": 1,
    "seed": 0
  }
}`;

const SIMULATION = `{
  "schema_version": "2.0.0",
  "plan": {
    "routes": [],
    "unserved_order_ids": [],
    "cost": {
      "distance_cents": 0,
      "fixed_vehicle_cents": 0,
      "service_cents": 0,
      "overtime_cents": 0,
      "setup_cents": 0,
      "total_cents": 0
    }
  },
  "stops": [],
  "seed": 0,
  "until_s": 86400
}`;

const EVENT = `{
  "schema_version": "2.0.0",
  "source": "workbench",
  "source_event_id": "evt-0001",
  "kind": "order_cancellation",
  "occurred_at_utc": "2026-01-01T00:15:00Z",
  "simulation_id": null,
  "expected_revision": null,
  "payload": {
    "kind": "order_cancellation",
    "entity_ref": {
      "kind": "order",
      "id": "00000000-0000-4000-8000-000000000001",
      "revision": null
    },
    "effective_at_s": 900,
    "reason": "operator cancellation",
    "order_id": "00000000-0000-4000-8000-000000000001",
    "disposition_policy": "return_to_origin"
  }
}`;

const METRICS = `{
  "schema_version": "2.0.0",
  "plan": {
    "routes": [],
    "unserved_order_ids": [],
    "cost": {
      "distance_cents": 0,
      "fixed_vehicle_cents": 0,
      "service_cents": 0,
      "overtime_cents": 0,
      "setup_cents": 0,
      "total_cents": 0
    }
  },
  "orders_total": 0,
  "vehicle_count": 0
}`;

const RESCHEDULE = `{
  "schema_version": "2.0.0",
  "impact": {
    "schema_version": "2.0.0",
    "event": ${EVENT},
    "plan": ${SIMULATION.slice(SIMULATION.indexOf('"plan"') + 7, SIMULATION.indexOf(', "stops"'))},
    "stops": [],
    "event_time_s": 900
  },
  "policy": {
    "max_extra_delay_s": 900,
    "allow_scope_expansion": false
  }
}`;

export default function App() {
  const [token, setTokenState] = useState(getToken());
  const [loggedIn, setLoggedIn] = useState(Boolean(getToken()));
  const [health, setHealth] = useState("unknown");
  const [orders, setOrders] = useState<OrderView[]>([]);
  const [job, setJob] = useState<JobRef | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>(tabFromHash());

  useEffect(() => {
    const onHashChange = () => setTab(tabFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (!token) return;
    request<{ status: string }>("/health")
      .then((value) => setHealth(value.status))
      .catch((reason: unknown) => setError(String(reason)));
  }, [token]);

  async function loadOrders() {
    try {
      setError("");
      setOrders((await request<Page<OrderView>>("/orders?limit=20")).items);
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

  if (!loggedIn) {
    return (
      <LoginPage
        onLogin={(value) => {
          setToken(value);
          setTokenState(value);
          setLoggedIn(true);
        }}
      />
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <strong>Logistics</strong>
          <span>Dispatch Workbench</span>
        </div>
        <nav className="nav">
          {TABS.map((item) => (
            <a key={item} href={`#/${item}`} className={tab === item ? "nav-item active" : "nav-item"}>
              {TITLES[item]}
            </a>
          ))}
        </nav>
        <div className="sidebar-footer">health: {health}</div>
      </aside>
      <main className="content">
        <header className="page-header">
          <div>
            <h1>{TITLES[tab]}</h1>
            <p className="muted">Real HTTP contract, no duplicated business rules.</p>
          </div>
          <div className="row">
            <input
              type="text"
              className="token"
              value={token}
              placeholder="Bearer token"
              onChange={(event) => {
                setTokenState(event.target.value);
                setToken(event.target.value);
              }}
            />
            <button className="secondary" onClick={() => {
              setToken("");
              setTokenState("");
              setLoggedIn(false);
            }}>sign out</button>
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}

        {tab === "overview" ? (
          <section>
            <h2>Operational snapshot</h2>
            <p className="muted">Token stays in localStorage and is sent only to the configured API.</p>
            <button className="secondary" onClick={loadOrders}>load orders</button>
            <ul>
              {orders.map((order) => (
                <li key={order.id}>{order.external_ref} · {order.status} · <code>{order.id}</code></li>
              ))}
            </ul>
            <h2 style={{ marginTop: "1.25rem" }}>Job result</h2>
            <div className="row">
              <input
                type="text"
                value={job?.job_id ?? ""}
                placeholder="job id from a submitted transport/simulation request"
                onChange={(event) => setJob({ ...(job as JobRef), job_id: event.target.value })}
              />
              <button className="secondary" onClick={loadResult} disabled={!job?.job_id}>load</button>
            </div>
            {job ? <p className="muted">{job.status}</p> : null}
          </section>
        ) : null}

        {tab === "schedules" ? <SchedulePanel /> : null}

        {tab === "transport" ? <TransportWorkflow /> : null}
        {tab === "warehouse" ? (
          <JsonPanel title="Warehouse scheduling" path="/optimizations/warehouse" initialBody={WAREHOUSE}
            idempotent description="Paste a WarehouseRequestDTO; the returned JobRef is queued." />
        ) : null}
        {tab === "simulation" ? (
          <JsonPanel title="Simulation" path="/simulations" initialBody={SIMULATION}
            idempotent description="SimulationRequestDTO with an explicit plan and stop rows." />
        ) : null}
        {tab === "incidents" ? <ExceptionPanel /> : null}

        {tab === "events" ? (
          <JsonPanel title="Event ingestion" path="/events" initialBody={EVENT}
            description="EventEnvelopeDTO; duplicate source/source_event_id returns a duplicate receipt." />
        ) : null}
        {tab === "metrics" ? (
          <JsonPanel title="Transport metrics" path="/metrics/transport" initialBody={METRICS}
            description="Pure read; missing values return null plus a reason." />
        ) : null}
        {tab === "reschedule" ? (
          <JsonPanel title="Reschedule proposal" path="/reschedules/proposals" initialBody={RESCHEDULE}
            description="Typed adjustments only; solver + validator must still run before commit." />
        ) : null}
        {tab === "agent" ? <AgentPanel /> : null}

        {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
      </main>
    </div>
  );
}

function LoginPage({ onLogin }: { onLogin: (token: string) => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!value.trim()) {
      setError("token is required");
      return;
    }
    setBusy(true);
    setError("");
    setToken(value.trim());
    try {
      await request<Page<OrderView>>("/orders?limit=1");
      onLogin(value.trim());
    } catch (reason) {
      setToken("");
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <h1>Logistics Workbench</h1>
      <p className="muted">Sign in with the development operator token.</p>
      <input
        type="text"
        value={value}
        placeholder="Bearer token"
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") void submit();
        }}
      />
      <button onClick={submit} disabled={busy}>{busy ? "signing in…" : "sign in"}</button>
      {error ? <p className="error">{error}</p> : null}
    </main>
  );
}

function AgentPanel() {
  const [message, setMessage] = useState("Summarize the current operational state without inventing a schedule.");
  const [reply, setReply] = useState<ChatReply | null>(null);
  const [error, setError] = useState("");

  async function send() {
    try {
      setError("");
      setReply(await request<ChatReply>("/agents/chat", {
        method: "POST",
        body: JSON.stringify({ schema_version: "2.0.0", message }),
      }));
    } catch (reason) {
      setError(String(reason));
    }
  }

  return (
    <section>
      <h2>Agent chat</h2>
      <p className="muted">
        The provider key is configured server-side. A placeholder key returns provider_unavailable;
        it never fabricates an answer.
      </p>
      <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
      <button onClick={send}>send</button>
      {error ? <p className="error">{error}</p> : null}
      {reply ? (
        <pre>{JSON.stringify(reply, null, 2)}</pre>
      ) : null}
    </section>
  );
}
