from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
from typing import Any
from app.contracts.planning import CandidatePlan
from app.contracts.entities import PlanningSnapshot
from app.domain.states import JobStatus

@dataclass
class JobRecord:
    job_id: str
    status: JobStatus
    plan_id: str | None = None
    error_code: str | None = None

class DemoRuntime:
    def __init__(self):
        self._lock = RLock()
        self.snapshots: dict[str, PlanningSnapshot] = {}
        self.snapshot_history: dict[tuple[str, int], PlanningSnapshot] = {}
        self.jobs: dict[str, JobRecord] = {}
        self.plans: dict[str, CandidatePlan] = {}
        self.idempotency: dict[str, dict[str, Any]] = {}
        self.reschedules: dict[str, Any] = {}
        self.events: dict[str, Any] = {}
        self.simulations: dict[str, Any] = {}
    def put_snapshot(self, s):
        with self._lock:
            self.snapshots[s.snapshot_id] = s
            self.snapshot_history[(s.snapshot_id, s.version)] = s
    def get_snapshot(self, sid, version):
        s = self.snapshot_history.get((sid, version))
        if s is None:
            s = self.snapshots.get(sid)
        if s is None: raise KeyError(f"snapshot_not_found:{sid}")
        if s.version != version: raise ValueError(f"snapshot_version_conflict:{sid}:expected={version}:actual={s.version}")
        return s
    def put_job(self, r):
        with self._lock: self.jobs[r.job_id] = r
    def get_job(self, jid):
        r = self.jobs.get(jid)
        if r is None: raise KeyError(f"job_not_found:{jid}")
        return r
    def put_plan(self, p):
        with self._lock: self.plans[p.plan_id] = p
    def get_latest_plan(self, snapshot_id, snapshot_version):
        matches = [p for p in self.plans.values() if p.snapshot_id == snapshot_id and p.snapshot_version == snapshot_version]
        if not matches:
            raise KeyError(f"plan_not_found_for_snapshot:{snapshot_id}:{snapshot_version}")
        return max(matches, key=lambda p: p.version)
    def put_reschedule(self, result):
        with self._lock: self.reschedules[result.event.event_id] = result
    def get_reschedule(self, event_id):
        result = self.reschedules.get(event_id)
        if result is None: raise KeyError(f"reschedule_not_found:{event_id}")
        return result
    def put_simulation(self, result):
        with self._lock: self.simulations[result.simulation_id] = result
    def get_simulation(self, simulation_id):
        result = self.simulations.get(simulation_id)
        if result is None: raise KeyError(f"simulation_not_found:{simulation_id}")
        return result
    def get_plan(self, pid):
        p = self.plans.get(pid)
        if p is None: raise KeyError(f"plan_not_found:{pid}")
        return p
runtime = DemoRuntime()
