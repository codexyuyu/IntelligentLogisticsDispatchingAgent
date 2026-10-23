import { useState } from "react";
import { idempotencyKey, request } from "../api";

type CandidateView = {
  candidate_id: string;
  schedule_id: string;
  snapshot_id: string;
  snapshot_hash: string;
  content_hash: string;
  validation_report_id: string;
  valid: boolean;
};

type CommitReceipt = {
  version_id: string;
  version_no: number;
  content_hash: string;
};

const EMPTY_PLAN = JSON.stringify({
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
}, null, 2);

export function CandidateCommitPanel({ scheduleId, activeVersionId, onCommitted }: {
  scheduleId: string;
  activeVersionId: string | null;
  onCommitted: () => void;
}) {
  const [problem, setProblem] = useState("{}");
  const [plan, setPlan] = useState(EMPTY_PLAN);
  const [stops, setStops] = useState("[]");
  const [refs, setRefs] = useState("[]");
  const [candidate, setCandidate] = useState<CandidateView | null>(null);
  const [receipt, setReceipt] = useState<CommitReceipt | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function createCandidate() {
    try {
      setBusy(true);
      setError("");
      setReceipt(null);
      const value = await request<CandidateView>(`/schedules/${scheduleId}/candidates`, {
        method: "POST",
        body: JSON.stringify({
          schema_version: "2.0.0",
          problem: JSON.parse(problem),
          plan: JSON.parse(plan),
          stops: JSON.parse(stops),
          solver_evidence_refs: JSON.parse(refs),
        }),
      });
      setCandidate(value);
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!candidate) return;
    try {
      setBusy(true);
      setError("");
      const value = await request<CommitReceipt>(
        `/schedules/${scheduleId}/versions/commit`, {
          method: "POST",
          body: JSON.stringify({
            schema_version: "2.0.0",
            command: {
              schema_version: "2.0.0",
              schedule_id: scheduleId,
              candidate_id: candidate.candidate_id,
              candidate_hash: candidate.content_hash,
              expected_active_version_id: activeVersionId,
              snapshot_hash: candidate.snapshot_hash,
              idempotency_key: idempotencyKey(),
              confirmation_token: null,
            },
          }),
        });
      setReceipt(value);
      onCommitted();
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h2>Candidate & commit</h2>
      <p className="muted">
        Paste a TransportProblemDTO. The server validates the plan/stops and stores the report;
        commit reads that stored report.
      </p>
      <p className="muted">problem JSON</p>
      <textarea value={problem} onChange={(event) => setProblem(event.target.value)} />
      <p className="muted">plan JSON</p>
      <textarea value={plan} onChange={(event) => setPlan(event.target.value)} />
      <div className="row">
        <div style={{ flex: 1 }}>
          <p className="muted">stops JSON</p>
          <textarea value={stops} onChange={(event) => setStops(event.target.value)} />
        </div>
        <div style={{ flex: 1 }}>
          <p className="muted">solver_evidence_refs JSON</p>
          <textarea value={refs} onChange={(event) => setRefs(event.target.value)} />
        </div>
      </div>
      <button onClick={createCandidate} disabled={busy}>validate & create candidate</button>
      {candidate ? (
        <p className="muted">
          candidate {candidate.candidate_id} · valid={String(candidate.valid)}
        </p>
      ) : null}
      <button className="secondary" onClick={commit} disabled={!candidate || busy}>
        commit candidate
      </button>
      {receipt ? (
        <p>committed v{receipt.version_no} · {receipt.content_hash.slice(0, 12)}</p>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
