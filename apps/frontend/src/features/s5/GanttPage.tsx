import { useEffect, useMemo, useState } from 'react';
import { request } from '../../api';
import SectionHeader from '../../components/SectionHeader';
import { KpiCard } from '../../components/KpiCard';
import { fmtClock } from '../../lib/format';
import { useTaskRunner } from '../../lib/asyncJobs';
import { RunSelector, useCheckedIntegrationRun } from './RunSelector';
import { buildGanttTasks, operationLabel, shortId, taskStatusLabel } from './model';
import type { ActualTask, TaskList } from './model';

const NEXT: Record<string, string> = { pending: 'ready', ready: 'running', running: 'completed' };

export default function GanttPage() {
  const lookup = useCheckedIntegrationRun();
  const { run } = lookup;
  const [actual, setActual] = useState<ActualTask[]>([]);
  const [executionError, setExecutionError] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const { busy: writing, error: writeError, run: write } = useTaskRunner();

  useEffect(() => {
    setActual([]);
    setExecutionError('');
    setSelectedId('');
    if (!run?.warehouse_problem) return;
    const controller = new AbortController();
    const warehouseIds = [...new Set(run.warehouse_problem.tasks.map(task => task.warehouse_id))];
    const expectedIds = new Set(run.warehouse_problem.tasks.map(task => task.id));
    void Promise.all(warehouseIds.map(id =>
      request<TaskList>(`/warehouses/${encodeURIComponent(id)}/tasks?limit=500`, { signal: controller.signal }),
    )).then(lists => {
      if (controller.signal.aborted) return;
      setActual(lists.flatMap(item => item.items).filter(task => expectedIds.has(task.id)));
      if (lists.some(item => item.total > item.items.length)) {
        setExecutionError('仓储作业查询已达到 500 条上限，部分实际状态未展示。');
      }
    }).catch(cause => {
      if (!controller.signal.aborted) setExecutionError(`无法读取 S3 实际作业状态：${String(cause)}。计划甘特图仍可查看。`);
    });
    return () => controller.abort();
  }, [run]);

  const tasks = useMemo(() => run ? buildGanttTasks(run, actual) : [], [run, actual]);
  const byOrder = useMemo(() => {
    const groups = new Map<string, typeof tasks>();
    for (const task of tasks) groups.set(task.orderId, [...(groups.get(task.orderId) ?? []), task]);
    return [...groups.entries()].sort((a, b) => a[1][0].orderLabel.localeCompare(b[1][0].orderLabel));
  }, [tasks]);
  const minS = Math.min(0, ...tasks.map(task => task.startS));
  const maxS = Math.max(minS + 1, ...tasks.map(task => task.endS));
  const span = maxS - minS;
  const resources = new Set(tasks.flatMap(task => task.resourceIds));
  const selected = tasks.find(task => task.id === selectedId);

  async function advanceSelected(signal: AbortSignal) {
    if (!selected || !run || selected.rowVersion === null || !selected.status) return;
    const target = NEXT[selected.status];
    if (!target) return;
    const message = `确认将 ${selected.orderLabel} 的「${operationLabel[selected.kind] ?? selected.kind}」从 ${taskStatusLabel[selected.status] ?? selected.status} 推进为 ${taskStatusLabel[target] ?? target}？\n这是实际作业写操作；完成收货/装车会生成库存流水。`;
    if (!window.confirm(message)) return;
    const updated = await request<ActualTask>(
      `/warehouses/${encodeURIComponent(selected.warehouseId)}/tasks/${encodeURIComponent(selected.id)}/transitions`,
      { method: 'POST', signal, body: JSON.stringify({
        schema_version: '2.0.0', run_id: run.run_id, target_status: target,
        expected_row_version: selected.rowVersion,
      }) },
    );
    signal.throwIfAborted();
    setActual(previous => previous.map(task => task.id === updated.id ? updated : task));
  }

  return <div>
    <SectionHeader title="S5 · 仓储作业甘特图" desc="读取 checked 联合运行的 CP-SAT 分配：每个订单的收货、分拣、装车各显示一次；实际执行状态来自 S3。" />
    <p className="callout callout-warn" role="note">写操作页：本页的「手动推进」是真实作业写操作，会写入当前连接的数据库并在完成时生成库存流水；只读回放请看「仓运事件时间线」页。</p>
    <RunSelector {...lookup} />
    {run && <>
      <div className="kpi-grid">
        <KpiCard label="订单数" value={`${byOrder.length}`} sub="checked 运行" icon="package" />
        <KpiCard label="排程工序" value={`${tasks.length}`} sub="10 单 × 3 工序为目标场景" icon="clock" tone="green" />
        <KpiCard label="分配资源" value={`${resources.size}`} sub="多资源分配归并到工序" icon="grid" />
        <KpiCard label="实际完成" value={`${tasks.filter(task => task.status === 'completed').length}`} sub="非计划完成数" icon="check" tone="green" />
      </div>
      <section className="panel">
        <div className="panel-title-row"><div><h3>10 单工序时间轴</h3><p>时间取自仓储求解方案；彩条代表计划时段，点击可查看实际作业。</p></div><span className="soft-badge">{fmtClock(minS)} – {fmtClock(maxS)}</span></div>
        {tasks.length ? <div className="s5-gantt-scroll"><div className="s5-gantt">
          <div className="s5-gantt-axis"><span>订单</span><div>{[0, 1, 2, 3, 4].map(tick => <span key={tick}>{fmtClock(minS + span * tick / 4)}</span>)}</div></div>
          {byOrder.map(([orderId, operations]) => <div className="s5-gantt-row" key={orderId}>
            <div className="s5-gantt-label" title={orderId}>{operations[0].orderLabel}</div>
            <div className="s5-gantt-lane">
              {operations.map(task => <button key={task.id} type="button"
                className={`s5-gantt-bar s5-stage-${task.kind} ${selectedId === task.id ? 's5-selected' : ''}`}
                style={{ left: `${100 * (task.startS - minS) / span}%`, width: `${Math.max(.65, 100 * (task.endS - task.startS) / span)}%` }}
                onClick={() => setSelectedId(task.id)}
                title={`${task.orderLabel} · ${operationLabel[task.kind] ?? task.kind}\n${fmtClock(task.startS)}–${fmtClock(task.endS)}\n实际状态：${taskStatusLabel[task.status ?? ''] ?? '未读取'}`}
                aria-label={`${task.orderLabel} ${operationLabel[task.kind] ?? task.kind} ${fmtClock(task.startS)} 至 ${fmtClock(task.endS)}`}>
                <span>{operationLabel[task.kind] ?? task.kind}</span>
              </button>)}
            </div>
          </div>)}
        </div></div> : <p className="s5-muted">当前运行没有可展示的仓储作业分配。</p>}
        <div className="s5-legend"><span><i className="s5-legend-dot s5-stage-receive" />收货</span><span><i className="s5-legend-dot s5-stage-sort" />分拣</span><span><i className="s5-legend-dot s5-stage-load" />装车</span></div>
        {executionError && <p role="alert" className="callout callout-warn">{executionError}</p>}
        {selected ? <div className="s5-detail" aria-live="polite">
          <div><strong>{selected.orderLabel} · {operationLabel[selected.kind] ?? selected.kind}</strong><small title={selected.id}>任务 {shortId(selected.id)} · 仓库 {shortId(selected.warehouseId)}</small></div>
          <div>计划 {fmtClock(selected.startS)} – {fmtClock(selected.endS)}；资源 {selected.resourceIds.map(shortId).join('、') || '—'}</div>
          <div>实际状态：<strong>{selected.status ? (taskStatusLabel[selected.status] ?? selected.status) : '未读取'}</strong></div>
          {selected.status && NEXT[selected.status] && <button className="btn btn-ghost btn-sm" disabled={writing}
            onClick={() => void write(advanceSelected)}>手动推进为「{taskStatusLabel[NEXT[selected.status]]}」</button>}
          {writeError && <p role="alert" className="callout callout-error">{writeError}</p>}
          <small>手动推进操作会写入当前连接的数据库；不会由计划回放自动触发。</small>
        </div> : <p className="s5-muted">点击任意工序可查看资源、计划时段和实际状态。</p>}
      </section>
    </>}
  </div>;
}
