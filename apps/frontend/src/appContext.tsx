
import type { ReactNode } from 'react';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type {
  CandidatePlan,
  DispatchEventWire,
  EventAcceptedWire,
  EventType,
  PlanResponse,
  SimulationResultWire,
  SimulationResponseWire,
  Snapshot,
} from './appTypes';
import { getJson, pollJob, postApi, postPartner } from './lib/http';

export type Conn = 'unknown' | 'ok' | 'bad';
export type BootPhase = 'idle' | 'checking' | 'importing' | 'planning' | 'ready' | 'failed';
export type AnomalyPhase = 'idle' | 'submitting' | 'accepted' | 'failed';
export type SimPhase = 'idle' | 'running' | 'completed' | 'failed';
export type CaseDemoPhase = 'idle' | 'importing' | 'baseline' | 'anomaly' | 'simulation' | 'completed' | 'failed';

export type AnomalyInput = {
  eventType: EventType;
  objectId: string;
  orderIds: string[];
  occurredAtS: number;
  delayS: number;
};

export type AnomalyState = {
  phase: AnomalyPhase;
  event: DispatchEventWire | null;
  accepted: EventAcceptedWire | null;
  error: string | null;
};

export type AppContextValue = {
  connection: Conn;
  bootPhase: BootPhase;
  bootError: string | null;
  snapshot: Snapshot | null;
  snapshotId: string | null;
  snapshotVersion: number | null;
  scenarioId: string | null;
  baseline: PlanResponse | null;
  baselinePlan: CandidatePlan | null;
  selectedPlan: CandidatePlan | null;
  setSelectedPlan: (plan: CandidatePlan | null) => void;
  boot: () => Promise<void>;
  importing: boolean;
  importScenario: () => Promise<CandidatePlan | null>;
  runBaseline: (options?: { mode?: 'sequential' | 'deep'; budgetMs?: number }) => Promise<CandidatePlan | null>;
  anomaly: AnomalyState;
  anomalyResult: import('./appTypes').LocalRescheduleResultWire | null;
  injectAnomaly: (input: AnomalyInput) => Promise<EventAcceptedWire | null>;
  resetAnomaly: () => void;
  simulation: SimulationResultWire | null;
  simPhase: SimPhase;
  simError: string | null;
  runSimulation: (input?: AnomalyInput) => Promise<SimulationResultWire | null>;
  caseDemoPhase: CaseDemoPhase;
  caseDemoError: string | null;
  runCaseDemo: () => Promise<void>;
  notice: string | null;
  setNotice: (text: string | null) => void;
};

const AppContext = createContext<AppContextValue | null>(null);

function buildEvent(input: AnomalyInput, snapshotId: string, snapshotVersion: number): DispatchEventWire {
  const now = new Date().toISOString();
  return {
    event_id: `ui_event_${Date.now()}`,
    event_type: input.eventType,
    snapshot_id: snapshotId,
    expected_snapshot_version: snapshotVersion,
    object_id: input.objectId,
    occurred_at_s: input.occurredAtS,
    received_at: now,
    source: { source_kind: 'simulation', source_ref: 'ui:incident-console', observed_at: now, rule_version: 'rules-0.1' },
    payload: {
      delay_s: input.eventType === 'departure_delayed' ? input.delayS : null,
      unavailable_until_s: null,
      replacement_matrix_id: null,
      affected_order_ids: input.orderIds,
      note: '来自前端异常处置控制台',
    },
  };
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [connection, setConnection] = useState<Conn>('unknown');
  const [bootPhase, setBootPhase] = useState<BootPhase>('idle');
  const [bootError, setBootError] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [snapshotId, setSnapshotId] = useState<string | null>(null);
  const [snapshotVersion, setSnapshotVersion] = useState<number | null>(null);
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [baseline, setBaseline] = useState<PlanResponse | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<CandidatePlan | null>(null);
  const [importing, setImporting] = useState(false);
  const [anomaly, setAnomaly] = useState<AnomalyState>({ phase: 'idle', event: null, accepted: null, error: null });
  const [simulation, setSimulation] = useState<SimulationResultWire | null>(null);
  const [simPhase, setSimPhase] = useState<SimPhase>('idle');
  const [simError, setSimError] = useState<string | null>(null);
  const [caseDemoPhase, setCaseDemoPhase] = useState<CaseDemoPhase>('idle');
  const [caseDemoError, setCaseDemoError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const bootingRef = useRef(false);
  const bootDoneRef = useRef(false);
  const runtimeRef = useRef({ snapshotId: null as string | null, snapshotVersion: null as number | null, snapshot: null as Snapshot | null });
  runtimeRef.current = { snapshotId, snapshotVersion, snapshot };

  const importScenario = useCallback(async (): Promise<CandidatePlan | null> => {
    setImporting(true);
    try {
      const source = await getJson<Snapshot>('/scenarios/single_warehouse_20_orders.json');
      const sid = `ui_${Date.now()}`;
      const data = { ...source, snapshot_id: sid };
      const result = await postApi<{ snapshot_id: string; version: number; scenario_id: string }>('/api/v1/scenarios/import', {
        scenario_id: sid,
        snapshot: data,
      });
      setSnapshot(data);
      setSnapshotId(result.snapshot_id);
      setSnapshotVersion(result.version);
      setScenarioId(result.scenario_id);
      runtimeRef.current = { snapshotId: result.snapshot_id, snapshotVersion: result.version, snapshot: data };
      return null;
    } finally {
      setImporting(false);
    }
  }, []);

  const runBaseline = useCallback(async (options?: { mode?: 'sequential' | 'deep'; budgetMs?: number }): Promise<CandidatePlan | null> => {
    const { snapshotId: sid, snapshotVersion: ver, snapshot: snap } = runtimeRef.current;
    if (!sid || ver == null || !snap) throw new Error('场景尚未导入，无法生成基线');
    setBootPhase((prev) => (prev === 'ready' ? 'ready' : 'planning'));
    const accepted = await postApi<{ job_id: string }>('/api/v1/planning-jobs', {
      snapshot_id: sid,
      expected_snapshot_version: ver,
      order_ids: snap.orders.map((o) => o.order_id),
      budget_ms: options?.budgetMs ?? 12000,
      max_coordination_rounds: options?.mode === 'deep' ? 3 : 1,
      coordination_mode: options?.mode ?? 'sequential',
    }, `ui-baseline-${Date.now()}`);
    const job = await pollJob(accepted.job_id, undefined, 120);
    if (job.status !== 'succeeded' || !job.plan_id) throw new Error(job.error_code ?? '基线规划失败');
    const planResp = await getJson<PlanResponse>(`/api/v1/plans/${encodeURIComponent(job.plan_id)}`);
    setBaseline(planResp);
    setSelectedPlan(planResp.plan);
    setBootPhase('ready');
    return planResp.plan;
  }, []);

  const boot = useCallback(async () => {
    if (bootDoneRef.current || bootingRef.current) return;
    bootingRef.current = true;
    setBootPhase('checking');
    try {
      const { api } = await import('./client/api');
      const { data } = await api.GET('/api/v1/health');
      setConnection(data?.status === 'ok' || data?.status === 'alive' ? 'ok' : 'bad');
      // The PR #1 pages keep their local demo/twin data. Do not call the retired legacy
      // scenario import endpoint; authenticated master data is fetched by the pages.
      setBootPhase('ready');
      bootDoneRef.current = true;
    } catch (e) {
      setBootPhase('failed');
      setBootError(e instanceof Error ? e.message : '初始化失败');
      setConnection('bad');
    } finally {
      bootingRef.current = false;
    }
  }, [importScenario, runBaseline]);

  useEffect(() => { void boot(); }, [boot]);

  const injectAnomaly = useCallback(async (input: AnomalyInput): Promise<EventAcceptedWire | null> => {
    const { snapshotId: sid, snapshotVersion: ver } = runtimeRef.current;
    if (!sid || ver == null) throw new Error('请先初始化场景');
    setAnomaly({ phase: 'submitting', event: null, accepted: null, error: null });
    try {
      const event = buildEvent(input, sid, ver);
      const accepted = await postApi<EventAcceptedWire>('/api/v1/events', event, `ui-event-${Date.now()}`);

      // The event endpoint is HTTP 202 and may return result=null when the
      // orchestration job fails. Resolve that job before moving the UI into
      // the "accepted" state so the action button never gets stuck.
      if (!accepted.result && accepted.replanning_job_id) {
        const job = await pollJob(accepted.replanning_job_id, undefined, 90);
        if (job.status !== 'succeeded') {
          setAnomaly({
            phase: 'failed',
            event,
            accepted,
            error: job.error_code ?? '局部重调度任务失败',
          });
          return accepted;
        }
        setAnomaly({
          phase: 'failed',
          event,
          accepted,
          error: '局部重调度任务已完成，但后端未返回重调度结果；请重试。',
        });
        return accepted;
      }

      setAnomaly({ phase: 'accepted', event, accepted, error: null });
      return accepted;
    } catch (e) {
      setAnomaly({ phase: 'failed', event: null, accepted: null, error: e instanceof Error ? e.message : '事件提交失败' });
      return null;
    }
  }, []);

  const resetAnomaly = useCallback(() => {
    setAnomaly({ phase: 'idle', event: null, accepted: null, error: null });
  }, []);

  const runSimulation = useCallback(async (input?: AnomalyInput): Promise<SimulationResultWire | null> => {
    const { snapshotId: sid, snapshotVersion: ver, snapshot: snap } = runtimeRef.current;
    if (!sid || ver == null || !snap) throw new Error('请先初始化场景');
    setSimPhase('running');
    setSimError(null);
    try {
      const activeEvent = anomaly.event;
      const resolved: AnomalyInput = input ?? (activeEvent ? {
        eventType: activeEvent.event_type,
        objectId: activeEvent.object_id,
        orderIds: activeEvent.payload.affected_order_ids,
        occurredAtS: activeEvent.occurred_at_s,
        delayS: activeEvent.payload.delay_s ?? 0,
      } : {
        eventType: 'departure_delayed',
        objectId: 'veh_1',
        orderIds: ['ord_001'],
        occurredAtS: 900,
        delayS: 900,
      });
      const event = buildEvent({ ...resolved, eventType: resolved.eventType }, sid, ver);
      const accepted = await postPartner<{ job_id: string; simulation_id: string }>('/api/v1/simulations', {
        snapshot: snap,
        events: [event],
        horizon_s: 1800,
        random_seed: 17,
      }, `ui-sim-${Date.now()}`);
      const job = await pollJob(accepted.job_id, undefined, 120);
      if (job.status !== 'succeeded') throw new Error(job.error_code ?? '仿真失败');
      const body = await getJson<SimulationResponseWire>(`/api/v1/simulations/${encodeURIComponent(accepted.simulation_id)}`);
      setSimulation(body.simulation);
      setSimPhase('completed');
      return body.simulation;
    } catch (e) {
      setSimPhase('failed');
      setSimError(e instanceof Error ? e.message : '仿真失败');
      return null;
    }
  }, []);

  const runCaseDemo = useCallback(async () => {
    setCaseDemoError(null);
    setCaseDemoPhase('importing');
    setBaseline(null);
    setSelectedPlan(null);
    setAnomaly({ phase: 'idle', event: null, accepted: null, error: null });
    setSimulation(null);
    setSimPhase('idle');
    setSimError(null);
    try {
      await importScenario();
      setCaseDemoPhase('baseline');
      const plan = await runBaseline();
      if (!plan) throw new Error('正常基线未生成');

      setCaseDemoPhase('anomaly');
      const accepted = await injectAnomaly({
        eventType: 'departure_delayed',
        objectId: 'veh_1',
        orderIds: ['ord_001'],
        occurredAtS: 0,
        delayS: 60,
      });
      if (!accepted?.result) throw new Error(anomaly.error ?? '局部重调度未生成结果');

      setCaseDemoPhase('simulation');
      const sim = await runSimulation({
        eventType: 'departure_delayed',
        objectId: 'veh_1',
        orderIds: ['ord_001'],
        occurredAtS: 0,
        delayS: 60,
      });
      if (!sim) throw new Error('SimPy 仿真未完成');
      setCaseDemoPhase('completed');
      setNotice('案例演示完成：20 单基线 → veh_1 延误 60s → 局部重调度 → SimPy 1800s 推演。');
    } catch (e) {
      const message = e instanceof Error ? e.message : '案例演示失败';
      setCaseDemoError(message);
      setCaseDemoPhase('failed');
      throw e;
    }
  }, [importScenario, runBaseline, injectAnomaly, runSimulation, anomaly.error, setNotice]);

  const anomalyResult = anomaly.accepted?.result ?? null;
  const baselinePlan = baseline?.plan ?? null;

  const value = useMemo<AppContextValue>(() => ({
    connection,
    bootPhase,
    bootError,
    snapshot,
    snapshotId,
    snapshotVersion,
    scenarioId,
    baseline,
    baselinePlan,
    selectedPlan,
    setSelectedPlan,
    boot,
    importing,
    importScenario,
    runBaseline,
    anomaly,
    anomalyResult,
    injectAnomaly,
    resetAnomaly,
    simulation,
    simPhase,
    simError,
    runSimulation,
    caseDemoPhase,
    caseDemoError,
    runCaseDemo,
    notice,
    setNotice,
  }), [connection, bootPhase, bootError, snapshot, snapshotId, snapshotVersion, scenarioId, baseline, baselinePlan, selectedPlan, boot, importing, importScenario, runBaseline, anomaly, anomalyResult, injectAnomaly, resetAnomaly, simulation, simPhase, simError, runSimulation, caseDemoPhase, caseDemoError, runCaseDemo, notice]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const value = useContext(AppContext);
  if (!value) throw new Error('useApp must be used inside AppProvider');
  return value;
}
