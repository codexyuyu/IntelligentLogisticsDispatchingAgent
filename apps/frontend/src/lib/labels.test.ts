import { describe, expect, it } from 'vitest';
import { sourceKindLabel, statusLabel } from './labels';

describe('中文状态标签', () => {
  it('把数据库和任务状态翻译成中文', () => {
    expect(statusLabel('draft')).toBe('草稿');
    expect(statusLabel('available')).toBe('可用');
    expect(statusLabel('queued')).toBe('排队中');
    expect(statusLabel('checked')).toBe('已校验');
  });

  it('保留已是中文的状态，未知英文值不直接显示', () => {
    expect(statusLabel('待处理')).toBe('待处理');
    expect(statusLabel('mystery_state')).toBe('未知状态');
    expect(statusLabel(null)).toBe('—');
  });

  it('把场景来源翻译成中文', () => {
    expect(sourceKindLabel('synthetic')).toBe('合成测试');
    expect(sourceKindLabel('enterprise')).toBe('企业来源声明');
    expect(sourceKindLabel('unknown_source')).toBe('来源未标注');
  });
});
