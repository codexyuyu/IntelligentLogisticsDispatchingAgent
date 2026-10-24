// File-view model for the converter's existing report; not a business DTO.
export type ReportRow = { scenario: string; orders: number; vehicles: number; operations: number; resources: number; losses: string[] };
export function parseReport(value: unknown): ReportRow[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('报告必须是场景对象');
  return Object.entries(value).map(([scenario, row]) => {
    if (!row || typeof row !== 'object' || Array.isArray(row)) throw new Error(`${scenario}：场景格式错误`);
    const r = row as Record<string, unknown>;
    for (const key of ['orders', 'vehicles', 'operations', 'resources']) {
      if (!Number.isSafeInteger(r[key]) || (r[key] as number) < 0) throw new Error(`${scenario}：${key} 必须是非负整数`);
    }
    if (!Array.isArray(r.losses) || !r.losses.every(x => typeof x === 'string')) throw new Error(`${scenario}：缺少有效损失清单`);
    return { scenario, orders: r.orders as number, vehicles: r.vehicles as number, operations: r.operations as number, resources: r.resources as number, losses: r.losses as string[] };
  });
}
