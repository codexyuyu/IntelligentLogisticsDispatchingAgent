/** 界面文案：后端枚举值统一翻成中文，避免英文状态直接漏到页面上。 */

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  registered: '已登记',
  active: '启用',
  inactive: '停用',
  available: '可用',
  unavailable: '不可用',
  validated: '已校验',
  confirmed: '已确认',
  executing: '执行中',
  completed: '已完成',
  rejected: '已拒绝',
  stale: '已过期',
  superseded: '已替代',
  queued: '排队中',
  running: '运行中',
  pending: '等待中',
  checked: '已校验',
  passed: '通过',
  failed: '失败',
  not_checked: '未校验',
  cancelled: '已取消',
  blocked: '已阻塞',
};

const CJK = /[\u4e00-\u9fff]/;

/** 状态值转中文。已经是中文的值原样保留；未知英文值不直接暴露。 */
export function statusLabel(status?: string | null): string {
  if (!status) return '—';
  return STATUS_LABELS[status] ?? (CJK.test(status) ? status : '未知状态');
}

const SOURCE_KIND_LABELS: Record<string, string> = {
  synthetic: '合成测试',
  enterprise: '企业来源声明',
};

/** 场景来源转中文。 */
export function sourceKindLabel(kind?: string | null): string {
  if (!kind) return '—';
  return SOURCE_KIND_LABELS[kind] ?? (CJK.test(kind) ? kind : '来源未标注');
}
