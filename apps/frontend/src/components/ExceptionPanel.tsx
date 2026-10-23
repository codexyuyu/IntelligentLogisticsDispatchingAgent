import { useState } from "react";
import { request } from "../api";

type EventReceipt = { event_id: string; sequence: number; status: string; duplicate: boolean };
type ExceptionItem = {
  exception_id: string;
  event_id: string;
  severity: string;
  status: string;
};
type Page<T> = { items: T[] };
type ImpactAnalysis = {
  report: {
    affected_orders: string[];
    affected_tasks: string[];
    affected_resources: string[];
  };
  boundary: {
    event_time_s: number;
    frozen_task_ids: string[];
    interrupted_task_ids: string[];
    mutable_task_ids: string[];
  };
};
type Proposal = {
  adjustments: Array<{ task_id: string; strategy: string; earliest_start_s: number | null }>;
  requires_manual_review: boolean;
  rationale: string;
};

const EVENT = JSON.stringify({
  schema_version: "2.0.0",
  source: "workbench",
  source_event_id: `evt-${Date.now()}`,
  kind: "order_cancellation",
  occurred_at_utc: "2026-01-01T00:15:00Z",
  simulation_id: null,
  expected_revision: null,
  payload: {
    kind: "order_cancellation",
    entity_ref: {
      kind: "order",
      id: "cfa10006-0100-5eea-84ad-a559923540c2",
      revision: null,
    },
    effective_at_s: 900,
    reason: "operator cancellation",
    order_id: "cfa10006-0100-5eea-84ad-a559923540c2",
    disposition_policy: "return_to_origin",
  },
}, null, 2);

const IMPACT = JSON.stringify({
  schema_version: "2.0.0",
  event: JSON.parse(EVENT),
  plan: {
    routes: [],
    unserved_order_ids: [],
    cost: {
      distance_cents: 0,
      fixed_vehicle_cents: 0,
      service_cents: 0,
      overtime_cents: 0,
      setup_cents: 0,
      total_cents: 0,
    },
  },
  stops: [],
  event_time_s: 900,
}, null, 2);

export function ExceptionPanel() {
  const [eventText, setEventText] = useState(EVENT);
  const [impactText, setImpactText] = useState(IMPACT);
  const [receipt, setReceipt] = useState<EventReceipt | null>(null);
  const [exceptions, setExceptions] = useState<ExceptionItem[]>([]);
  const [impact, setImpact] = useState<ImpactAnalysis | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState("");

  async function ingestEvent() {
    try {
      setError("");
      setReceipt(await request<EventReceipt>("/events", {
        method: "POST",
        body: eventText,
      }));
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function loadExceptions() {
    try {
      setError("");
      setExceptions((await request<Page<ExceptionItem>>("/exceptions?limit=50")).items);
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function analyseImpact() {
    try {
      setError("");
      setImpact(await request<ImpactAnalysis>("/exceptions/impact", {
        method: "POST",
        body: impactText,
      }));
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function propose() {
    try {
      setError("");
      const body = {
        schema_version: "2.0.0",
        impact: JSON.parse(impactText),
        policy: { max_extra_delay_s: 300, allow_scope_expansion: false },
      };
      setProposal(await request<Proposal>("/reschedules/proposals", {
        method: "POST",
        body: JSON.stringify(body),
      }));
    } catch (reason) {
      setError(String(reason));
    }
  }

  return (
    <>
      {error ? <p className="error">{error}</p> : null}
      <section>
        <h2>Event injection</h2>
        <textarea value={eventText} onChange={(event) => setEventText(event.target.value)} />
        <div className="row" style={{ marginTop: "0.5rem" }}>
          <button onClick={ingestEvent}>POST /events</button>
          <button className="secondary" onClick={loadExceptions}>refresh exceptions</button>
        </div>
        {receipt ? (
          <p className="muted">
            event {receipt.event_id} · sequence={receipt.sequence} · duplicate={String(receipt.duplicate)}
          </p>
        ) : null}
        <ul>
          {exceptions.map((item) => (
            <li key={item.exception_id}>
              {item.severity} · {item.status} · {item.exception_id}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Impact & reschedule proposal</h2>
        <p className="muted">
          Paste an ImpactRequestDTO (event + validated transport plan + stops + relative time).
        </p>
        <textarea value={impactText} onChange={(event) => setImpactText(event.target.value)} />
        <div className="row" style={{ marginTop: "0.5rem" }}>
          <button onClick={analyseImpact}>analyse impact</button>
          <button className="secondary" onClick={propose}>propose adjustments</button>
        </div>
        {impact ? <pre>{JSON.stringify(impact, null, 2)}</pre> : null}
        {proposal ? (
          <div>
            <p>
              adjustments={proposal.adjustments.length} · manual={String(proposal.requires_manual_review)}
            </p>
            <ul>
              {proposal.adjustments.map((item) => (
                <li key={item.task_id}>
                  {item.strategy} · {item.task_id} · start={item.earliest_start_s}
                </li>
              ))}
            </ul>
            <p className="muted">{proposal.rationale}</p>
          </div>
        ) : null}
      </section>
    </>
  );
}
