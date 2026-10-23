import { useEffect, useState } from "react";
import { request } from "../api";

type Schedule = {
  schedule_id: string;
  name: string;
  status: string;
  epoch_utc: string;
  horizon_s: number;
  active_version_id: string | null;
};
type Version = {
  version_id: string;
  version_no: number;
  status: string;
  content_hash: string;
  committed_at: string;
};
type Page<T> = { items: T[] };
type VersionDetail = {
  version: Version;
  tasks: Array<{
    task_id: string;
    task_kind: string;
    planned_start_s: number;
    planned_end_s: number;
  }>;
};
type Diff = {
  added_task_ids: string[];
  removed_task_ids: string[];
  changed_tasks: unknown[];
  unchanged_count: number;
};

const DEFAULT_SCOPE = JSON.stringify({
  order_ids: [
    "cfa10006-0100-5eea-84ad-a559923540c2",
    "71371ebf-1c95-5437-b939-c753d13b3685",
  ],
  warehouse_ids: ["3095eda4-48b4-5601-8934-a3f5d2e60272"],
  vehicle_ids: ["3ad447e7-5161-50df-8b00-4f5fbd3f8a2a"],
  epoch_utc: "2026-01-01T00:00:00Z",
  horizon_s: 86400,
}, null, 2);

export function SchedulePanel() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [selected, setSelected] = useState("");
  const [versions, setVersions] = useState<Version[]>([]);
  const [detail, setDetail] = useState<VersionDetail | null>(null);
  const [base, setBase] = useState("");
  const [candidate, setCandidate] = useState("");
  const [diff, setDiff] = useState<Diff | null>(null);
  const [name, setName] = useState("demo-schedule");
  const [scope, setScope] = useState(DEFAULT_SCOPE);
  const [error, setError] = useState("");

  useEffect(() => {
    void loadSchedules();
  }, []);

  async function loadSchedules() {
    try {
      setError("");
      const page = await request<Page<Schedule>>("/schedules?limit=50");
      setSchedules(page.items);
      if (!selected && page.items.length) setSelected(page.items[0].schedule_id);
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function createSchedule() {
    try {
      setError("");
      await request<Schedule>("/schedules", {
        method: "POST",
        body: JSON.stringify({ schema_version: "2.0.0", name, scope: JSON.parse(scope) }),
      });
      await loadSchedules();
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function loadVersions(scheduleId: string) {
    setSelected(scheduleId);
    setDetail(null);
    setDiff(null);
    try {
      setError("");
      const page = await request<Page<Version>>(`/schedules/${scheduleId}/versions?limit=50`);
      setVersions(page.items);
      setBase(page.items[0]?.version_id ?? "");
      setCandidate(page.items[1]?.version_id ?? "");
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function loadCurrent() {
    try {
      setError("");
      setDetail(await request<VersionDetail>(`/schedules/${selected}/versions/current`));
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function loadDiff() {
    if (!base || !candidate) return;
    try {
      setError("");
      setDiff(await request<Diff>(
        `/schedules/${selected}/versions/${base}/diff/${candidate}`));
    } catch (reason) {
      setError(String(reason));
    }
  }

  return (
    <>
      {error ? <p className="error">{error}</p> : null}
      <section>
        <h2>Schedules</h2>
        <div className="row">
          <button className="secondary" onClick={loadSchedules}>refresh</button>
          <span className="muted">{schedules.length} schedule(s)</span>
        </div>
        <ul>
          {schedules.map((item) => (
            <li key={item.schedule_id}>
              <button className="secondary" onClick={() => void loadVersions(item.schedule_id)}>
                {item.name}
              </button>
              <span className="muted"> · {item.status} · {item.schedule_id}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Create draft schedule</h2>
        <label>
          name
          <input type="text" value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <p className="muted">PlanningScope JSON</p>
        <textarea value={scope} onChange={(event) => setScope(event.target.value)} />
        <button onClick={createSchedule}>create</button>
      </section>

      {selected ? (
        <section>
          <h2>Versions</h2>
          <div className="row">
            <button className="secondary" onClick={() => void loadVersions(selected)}>refresh</button>
            <button className="secondary" onClick={loadCurrent}>current</button>
          </div>
          <ul>
            {versions.map((item) => (
              <li key={item.version_id}>
                v{item.version_no} · {item.status} · <code>{item.content_hash.slice(0, 12)}</code>
                <span className="muted"> · {item.committed_at}</span>
              </li>
            ))}
          </ul>
          {detail ? (
            <div>
              <h3>Current v{detail.version.version_no}</h3>
              <ul>
                {detail.tasks.map((task) => (
                  <li key={task.task_id}>
                    {task.task_kind} · {task.planned_start_s}–{task.planned_end_s}s
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <h3>Compare versions</h3>
          <div className="row">
            <select value={base} onChange={(event) => setBase(event.target.value)}>
              <option value="">base</option>
              {versions.map((item) => (
                <option key={item.version_id} value={item.version_id}>v{item.version_no}</option>
              ))}
            </select>
            <select value={candidate} onChange={(event) => setCandidate(event.target.value)}>
              <option value="">candidate</option>
              {versions.map((item) => (
                <option key={item.version_id} value={item.version_id}>v{item.version_no}</option>
              ))}
            </select>
            <button className="secondary" onClick={loadDiff} disabled={!base || !candidate}>diff</button>
          </div>
          {diff ? (
            <pre>{JSON.stringify(diff, null, 2)}</pre>
          ) : null}
        </section>
      ) : null}
    </>
  );
}
