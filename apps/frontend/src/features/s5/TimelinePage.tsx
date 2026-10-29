import { useEffect, useMemo, useRef, useState } from 'react';
import { request } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { fmtClock } from '../../lib/format';
import { eventKindLabel, isValidatedTimeline, replayTimes, shortId } from './model';
import type { StateAtResponse, TimelineResponse } from './model';
import { RunSelector, useCheckedIntegrationRun } from './RunSelector';

const reconciliationLabels: Record<string, string> = {
  event_delivery_mismatch: '送达事件与路线一致',
  event_handoff_mismatch: '交接事件与路线一致',
  duplicate_vehicle_route: '车辆不重复分配路线',
  vehicle_departure_event_mismatch: '发车事件数量一致',
  vehicle_return_event_mismatch: '返程事件数量一致',
  handoff_before_warehouse_operations_finished: '仓储完工后才能交接',
  departure_before_loading_ready: '具备装车条件后才能出发',
};

const stateLists = [
  ['completed_order_ids', '已送达订单'],
  ['completed_operation_ids', '已完成工序'],
  ['active_operation_ids', '正在进行的工序'],
  ['in_transit_vehicle_ids', '在途车辆'],
  ['returned_vehicle_ids', '已返回车辆'],
  ['not_yet_departed_vehicle_ids', '尚未出发车辆'],
  ['onboard_pending_order_ids', '已交接、待送达订单'],
  ['available_depot_vehicle_ids', '非在途车辆（后端口径）'],
  ['interrupted_operation_ids', '中断工序'],
] as const;

export default function TimelinePage() {
  const lookup = useCheckedIntegrationRun();
  const { run } = lookup;
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [timelineError, setTimelineError] = useState('');
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [snapshot, setSnapshot] = useState<StateAtResponse | null>(null);
  const [snapshotError, setSnapshotError] = useState('');
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const cache = useRef(new Map<number, StateAtResponse>());

  useEffect(() => {
    setTimeline(null); setTimelineError(''); setSnapshot(null);
    setCursor(0); setPlaying(false); cache.current.clear();
    if (!run) return;
    const controller = new AbortController();
    setLoadingTimeline(true);
    void request<TimelineResponse>(`/integration/runs/${encodeURIComponent(run.run_id)}/timeline`, { signal: controller.signal })
      .then(value => {
        if (controller.signal.aborted) return;
        if (value.run_id !== run.run_id || !isValidatedTimeline(value)) {
          throw new Error('后端返回的计划时间线未满足七项对账、订单恒等式或确定性顺序，拒绝回放。');
        }
        setTimeline(value);
      }).catch(cause => {
        if (!controller.signal.aborted) setTimelineError(String(cause));
      }).finally(() => { if (!controller.signal.aborted) setLoadingTimeline(false); });
    return () => controller.abort();
  }, [run, reloadCount]);

  const times = useMemo(() => replayTimes(timeline?.events ?? []), [timeline]);
  const safeCursor = Math.min(cursor, Math.max(0, times.length - 1));
  const currentTime = times[safeCursor] ?? 0;
  const visibleEvents = useMemo(
    () => timeline?.events.filter(event => event.time_s <= currentTime) ?? [], [timeline, currentTime],
  );

  useEffect(() => {
    if (!timeline || !run) return;
    const controller = new AbortController();
    const cached = cache.current.get(currentTime);
    setSnapshotError('');
    if (cached) { setSnapshot(cached); setLoadingSnapshot(false); return; }
    setSnapshot(null); setLoadingSnapshot(true);
    void request<StateAtResponse>(
      `/integration/runs/${encodeURIComponent(run.run_id)}/state-at?time_s=${currentTime}`, { signal: controller.signal },
    ).then(value => {
      if (controller.signal.aborted) return;
      if (value.run_id !== run.run_id || value.time_s !== currentTime || value.source_kind !== 'planned_validated') {
        throw new Error('状态快照与当前运行或回放时间不匹配。');
      }
      cache.current.set(currentTime, value);
      setSnapshot(value);
    }).catch(cause => {
      if (!controller.signal.aborted) setSnapshotError(String(cause));
    }).finally(() => { if (!controller.signal.aborted) setLoadingSnapshot(false); });
    return () => controller.abort();
  }, [timeline, run, currentTime]);

  useEffect(() => {
    if (!playing) return;
    if (cursor >= times.length - 1) { setPlaying(false); return; }
    const timer = window.setTimeout(() => setCursor(value => value + 1), 850);
    return () => window.clearTimeout(timer);
  }, [playing, cursor, times.length]);

  return <div>
    <SectionHeader title="S5 · 仓运事件时间线" desc="经联合校验的仓储作业 → 装车交接 → 运输送达计划回放。事件时刻状态通过 S4 state-at 接口读取。" />
    <RunSelector {...lookup} />
    <div className="callout callout-warn">这是 <strong>planned_validated 计划预测</strong>，不是实时 GPS、SimPy 实际仿真或已执行派车；拖动时间轴不会推进 S3 作业状态，也不会改变库存。</div>
    {run && <section className="panel">
      <div className="panel-title-row"><div><h3>时间线与校验</h3><p>只有 checked 且七项对账全部通过的计划才允许回放。</p></div>
        <button className="btn btn-ghost btn-sm" disabled={loadingTimeline}
          onClick={() => setReloadCount(value => value + 1)}>{loadingTimeline ? '读取中…' : '刷新时间线'}</button></div>
      {timelineError && <p role="alert" className="callout callout-error">{timelineError}</p>}
      {loadingTimeline && <p role="status">正在加载经过校验的计划时间线…</p>}
      {timeline && <>
        <div className="s5-reconciliation">
          <div><strong>{timeline.event_count}</strong><small>已核对事件</small></div>
          <div><strong>{timeline.reconciliation.scope_orders}</strong><small>场景订单</small></div>
          <div><strong>{timeline.reconciliation.planned_delivery_orders}</strong><small>计划送达</small></div>
          <div><strong>{timeline.reconciliation.explicitly_unserved_orders}</strong><small>明确未服务</small></div>
        </div>
        <p className="s5-good">对账通过：订单数 = 计划送达 + 明确未服务。首次读取会幂等保存该运行的计划事件。</p>
        <details><summary>查看七项跨系统对账结果</summary><ul className="s5-checks">
          {Object.entries(timeline.reconciliation.checks).map(([name, valid]) =>
            <li key={name} className={valid ? 's5-good' : 's5-negative'}>{valid ? '✓' : '✕'} {reconciliationLabels[name] ?? name}</li>)}
        </ul></details>
        <div className="s5-player">
          <div className="s5-player-heading"><strong>计划时刻 {fmtClock(currentTime)}</strong><span>累计 {visibleEvents.length} / {timeline.events.length} 个事件</span></div>
          <input aria-label="计划回放时间" type="range" min={0} max={Math.max(0, times.length - 1)} value={safeCursor}
            disabled={times.length <= 1} onChange={event => { setPlaying(false); setCursor(Number(event.target.value)); }} />
          <div className="s5-player-controls">
            <button className="btn btn-ghost btn-sm" onClick={() => { setPlaying(false); setCursor(0); }}>回到起点</button>
            <button className="btn btn-ghost btn-sm" disabled={safeCursor === 0} onClick={() => { setPlaying(false); setCursor(value => Math.max(0, value - 1)); }}>上一时刻</button>
            <button className="btn btn-primary btn-sm" disabled={times.length <= 1} onClick={() => {
              if (!playing && safeCursor === times.length - 1) setCursor(0);
              setPlaying(value => !value);
            }}>{playing ? '暂停' : '播放'}</button>
            <button className="btn btn-ghost btn-sm" disabled={safeCursor >= times.length - 1} onClick={() => {
              setPlaying(false); setCursor(value => Math.min(times.length - 1, value + 1));
            }}>下一时刻</button>
          </div>
        </div>
      </>}
    </section>}
    {timeline && <>
      <section className="panel">
        <div className="panel-title-row"><div><h3>事件时刻状态</h3><p>10 组状态集合均由后端计算，车辆位置是计划中最近到站节点，并非实时定位。</p></div><span className="soft-badge">t = {currentTime}s</span></div>
        {loadingSnapshot && <p role="status">正在查询时刻状态…</p>}
        {snapshotError && <p role="alert" className="callout callout-error">{snapshotError}</p>}
        {snapshot && <div className="s5-state-grid">
          {stateLists.map(([field, label]) => <details className="s5-state-item" key={field}>
            <summary><span>{label}</span><strong>{snapshot[field].length}</strong></summary>
            <p>{snapshot[field].length ? snapshot[field].map(shortId).join('、') : '当前为空'}</p>
          </details>)}
          <details className="s5-state-item">
            <summary><span>在途车辆最近到站节点（非 GPS）</span><strong>{Object.keys(snapshot.halted_vehicle_positions).length}</strong></summary>
            <p>{Object.keys(snapshot.halted_vehicle_positions).length ? Object.entries(snapshot.halted_vehicle_positions)
              .map(([vehicle, node]) => `${shortId(vehicle)} → ${shortId(node)}`).join('；') : '当前为空'}</p>
          </details>
        </div>}
      </section>
      <section className="panel">
        <div className="panel-title-row"><div><h3>已发生的计划事件</h3><p>同秒事件按后端固定顺序呈现；列表显示最近 20 条。</p></div><span className="soft-badge">{visibleEvents.length} 条</span></div>
        {visibleEvents.length ? <div className="table-wrap"><table>
          <thead><tr><th>序号</th><th>计划时间</th><th>事件</th><th>订单</th><th>车辆</th><th>关联对象</th></tr></thead>
          <tbody>{visibleEvents.slice(-20).map(event => <tr key={event.id}>
            <td>{event.sequence}</td><td>{fmtClock(event.time_s)}</td>
            <td>{eventKindLabel[event.kind] ?? event.kind}</td>
            <td title={event.order_id ?? ''}>{shortId(event.order_id)}</td>
            <td title={event.vehicle_id ?? ''}>{shortId(event.vehicle_id)}</td>
            <td title={event.object_id}>{shortId(event.object_id)}</td>
          </tr>)}</tbody>
        </table></div> : <p className="s5-muted">该时刻之前尚无计划事件。</p>}
      </section>
    </>}
  </div>;
}
