/** S5 views use the checked integration run and S3/S4 read APIs as evidence. */
export type OperationKind = 'receive' | 'sort' | 'load' | string;

export type PlannedTask = {
  id: string;
  order_id: string | null;
  warehouse_id: string;
  kind: OperationKind;
  duration_s: number;
};

export type ActualTask = PlannedTask & {
  status: string;
  row_version: number;
};

export type TaskList = {
  schema_version: string;
  total: number;
  items: ActualTask[];
};

export type CheckedRun = {
  run_id: string;
  status: string;
  joint_validation?: { valid: boolean };
  warehouse_problem?: {
    tasks: PlannedTask[];
    snapshot: {
      scope: { order_ids: string[]; warehouse_ids: string[] };
      orders: { id: string; external_ref: string }[];
    };
  };
  warehouse_solution?: {
    status: string;
    assignments: {
      task_id: string;
      resource_id: string;
      start_s: number;
      end_s: number;
    }[];
  };
};

export type GanttTask = {
  id: string;
  orderId: string;
  orderLabel: string;
  warehouseId: string;
  kind: string;
  startS: number;
  endS: number;
  resourceIds: string[];
  status: string | null;
  rowVersion: number | null;
};

export type InventoryMovement = {
  id: string;
  cargo_id: string;
  location_id: string;
  source_location_id: string | null;
  quantity_delta: number;
  created_at: string;
  run_id: string | null;
  task_id: string | null;
  operation_kind: string | null;
};

export type InventoryResponse = {
  schema_version: string;
  items: InventoryMovement[];
  positions: { cargo_id: string; location_id: string; quantity_units: number }[];
  total_entries: number;
  has_more: boolean;
};

export type TimelineEvent = {
  id: string;
  sequence: number;
  time_s: number;
  kind: string;
  object_id: string;
  order_id: string | null;
  vehicle_id: string | null;
  route_id: string | null;
  node_id: string | null;
};

export type TimelineResponse = {
  schema_version: string;
  run_id: string;
  source_kind: string;
  event_count: number;
  events: TimelineEvent[];
  reconciliation: {
    passed: boolean;
    checks: Record<string, boolean>;
    scope_orders: number;
    planned_delivery_orders: number;
    explicitly_unserved_orders: number;
    order_details: {
      order_id: string;
      routing_status: string;
      planned_delivery_at_s: number | null;
      planned_vehicle_id: string | null;
    }[];
  };
};

export type StateAtResponse = {
  schema_version: string;
  run_id: string;
  source_kind: string;
  time_s: number;
  completed_order_ids: string[];
  completed_operation_ids: string[];
  active_operation_ids: string[];
  in_transit_vehicle_ids: string[];
  returned_vehicle_ids: string[];
  not_yet_departed_vehicle_ids: string[];
  onboard_pending_order_ids: string[];
  available_depot_vehicle_ids: string[];
  halted_vehicle_positions: Record<string, string>;
  interrupted_operation_ids: string[];
};

const STAGES: Record<string, number> = { receive: 0, sort: 1, load: 2 };

export const operationLabel: Record<string, string> = {
  receive: '入库', sort: '分拣', load: '装车',
};

export const taskStatusLabel: Record<string, string> = {
  pending: '待准备', ready: '已准备', running: '执行中', completed: '已完成',
  cancelled: '已取消', interrupted: '已中断', failed: '失败',
};

export const eventKindLabel: Record<string, string> = {
  warehouse_work_start: '仓储作业开始',
  warehouse_work_finished: '仓储作业结束',
  loading_ready: '具备装车条件',
  order_handoff: '仓运交接',
  vehicle_departure: '首次提货后离开',
  order_delivered: '计划送达',
  vehicle_return: '车辆返回',
};

export function shortId(id: string | null | undefined): string {
  if (!id) return '—';
  return id.length > 18 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
}

/** One interval per logical task, even when multiple resources were assigned. */
export function buildGanttTasks(run: CheckedRun, actualTasks: ActualTask[] = []): GanttTask[] {
  const planned = run.warehouse_problem?.tasks ?? [];
  const assignments = run.warehouse_solution?.assignments ?? [];
  const orderLabels = new Map(run.warehouse_problem?.snapshot.orders.map(order => [order.id, order.external_ref]) ?? []);
  const actualById = new Map(actualTasks.map(task => [task.id, task]));
  const spans = new Map<string, { start: number; end: number; resources: Set<string> }>();
  for (const assignment of assignments) {
    const prior = spans.get(assignment.task_id);
    if (prior) {
      prior.start = Math.min(prior.start, assignment.start_s);
      prior.end = Math.max(prior.end, assignment.end_s);
      prior.resources.add(assignment.resource_id);
    } else {
      spans.set(assignment.task_id, {
        start: assignment.start_s, end: assignment.end_s,
        resources: new Set([assignment.resource_id]),
      });
    }
  }
  return planned.flatMap(task => {
    const span = spans.get(task.id);
    if (!span || !task.order_id) return [];
    const actual = actualById.get(task.id);
    return [{
      id: task.id, orderId: task.order_id, orderLabel: orderLabels.get(task.order_id) ?? shortId(task.order_id),
      warehouseId: task.warehouse_id, kind: task.kind, startS: span.start, endS: span.end,
      resourceIds: [...span.resources].sort(), status: actual?.status ?? null,
      rowVersion: actual?.row_version ?? null,
    }];
  }).sort((a, b) => a.orderLabel.localeCompare(b.orderLabel)
    || (STAGES[a.kind] ?? 99) - (STAGES[b.kind] ?? 99) || a.startS - b.startS);
}

export function replayTimes(events: TimelineEvent[]): number[] {
  return [...new Set([0, ...events.map(event => event.time_s)])]
    .filter(value => Number.isSafeInteger(value) && value >= 0).sort((a, b) => a - b);
}

export function isValidatedTimeline(data: TimelineResponse): boolean {
  return data.source_kind === 'planned_validated'
    && data.reconciliation.passed
    && Object.values(data.reconciliation.checks).length === 7
    && Object.values(data.reconciliation.checks).every(Boolean)
    && data.reconciliation.scope_orders === data.reconciliation.planned_delivery_orders
      + data.reconciliation.explicitly_unserved_orders
    && data.event_count === data.events.length
    && data.events.every((event, index) => event.sequence === index
      && Number.isSafeInteger(event.time_s) && event.time_s >= 0
      && (index === 0 || event.time_s >= data.events[index - 1].time_s));
}
