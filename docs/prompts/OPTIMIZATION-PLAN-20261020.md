# 提示词工程优化方案

**版本**: 1.0  
**日期**: 2026-10-20  
**适用阶段**: P02-P39  
**目标**: 补充关键缺口、优化 109 个现有 Prompt、确保完成度 100%

---

## 第一部分：现状分析

### 1.1 现有 Prompt 体系

| 阶段 | 数量 | 状态 | 关键缺口 |
|------|------|------|---------|
| P00 | 3 | ✅ 完成 | — |
| P01 | 3 | 🔄 返工中 | N02-N05 验收流程 |
| P02-P04 | 10 | ⏳ 阻塞 | 数据库映射 (P03-00 缺失) |
| P05-P16 | 37 | ⏳ 阻塞 | LLM 降级路径 (P18-00 缺失) |
| P17-P31 | 35 | ⏳ 阻塞 | 工具绑定 (P17-00 缺失) |
| P32-P39 | 14 | ⏳ 阻塞 | 性能基准 (P36-00 缺失) |
| **合计** | **109** | — | **4 处新增** |

### 1.2 关键缺陷

#### 🔴 Critical (立即修复)

1. **阶段串行阻塞** (P02-P39 因 G01 停滞)
   - 问题: P02 前置 G01 签收，无法并行准备
   - 影响: 整体延期 5-7 天
   - 修复: 提供 P02 的"干运行" Prompt (模拟 DTO)

2. **数据库映射缺口** (P03-00 不存在)
   - 问题: bundle.json → 领域模型的转换规则未定义
   - 影响: P03-P04 会遇到 DTO 设计困难
   - 修复: 生成新 P03-00-data-integration Prompt

#### 🟠 High (1-2 周内修复)

3. **LLM 降级路径未定义** (P18-00 不存在)
   - 问题: 无模型时系统能力边界模糊
   - 影响: P19-P23 Agent 流程不清楚
   - 修复: 生成新 P18-00-llm-fallback Prompt

4. **工具绑定缺失** (P17-00 需补充)
   - 问题: 工具注册与权限框架不明确
   - 影响: P19-P22 工具调用流程有歧义
   - 修复: 扩展 P17-01 的内容到专题 P17-00

#### 🟡 Medium (后续优化)

5. **现有 Prompt 的 10 处补充** (修正清单见下表)

### 1.3 现有 Prompt 修正清单

| 序号 | Prompt | 修正点 | 优先级 |
|------|--------|-------|--------|
| 1 | P04-01 | 补充"与 P03-00 的数据流向" | MEDIUM |
| 2 | P06-01 | 明确"矩阵版本化与缓存策略" | HIGH |
| 3 | P09-01 | 补充"库位库存区间"的形式化定义 | HIGH |
| 4 | P10-02 | 补充"独立校验反例集合"的生成规范 | CRITICAL |
| 5 | P16-01 | 补充"异常场景下的 API 降级" | MEDIUM |
| 6 | P18-02 | 补充"模型 API 故障时的回退策略" | HIGH |
| 7 | P19-01 | 补充"非 LLM 结构化输入的处理流程" | MEDIUM |
| 8 | P28-02 | 补充"快照恢复的一致性保证" | LOW |
| 9 | P32-01 | 补充"无可行解场景的指标计算" | MEDIUM |
| 10 | P34-03 | 补充"并发提交的去重与幂等性" | HIGH |

---

## 第二部分：新增 Prompt 规范

### 新增 1: P03-00 · 数据库集成与 DTO 映射

**优先级**: CRITICAL  
**启动条件**: G01 签收后立即启动  
**估计工期**: 2-3 天  
**所有权**: A  

#### 概要

```markdown
# P03-00 · 数据库集成与 DTO 映射

## Objective
将 `data/preparation/competition-2026/bundle.json` 的 Synthetic 数据转换为正式 P02 领域 DTO，
并为 P03-01/02/03 提供完整的数据导入流程。

## Scope
- ✅ 设计 Preparation DTO 类结构
- ✅ 实现 Bundle → DTO 转换函数
- ✅ 定义 DTO → PostgreSQL 的映射规则
- ✅ 编写导入脚本与验证测试
- ❌ 不实现真实 ERP/WMS 接口
- ❌ 不支持动态 DTO 生成

## Key Deliverables
1. `apps/packages/logistics_contracts/src/logistics_contracts/dtos/preparation.py`
   - PreparedBundle / PreparedWarehouse / PreparedVehicle / PreparedOrder DTO
   - 28 个 DTO 类 + 5 个 Enum

2. `apps/backend/src/logistics_persistence/converters/preparation_converter.py`
   - PreparationBundleConverter 类
   - from_json_file / from_dict 方法
   - 3 层转换验证

3. `tests/fixtures/preparation_snapshot.py`
   - PreparationSnapshot 类
   - 固定哈希与计数验证
   - 快照加载与幂等性测试

4. `tests/test_preparation_converter.py` & `tests/integration/test_preparation_import.py`
   - 18 项单元测试
   - 5 项集成测试 (需真实 PostgreSQL)
   - 导入幂等性验证

5. `docs/data/database-integration-guide-20261020.md`
   - 数据流向说明
   - DTO 映射规范
   - PostgreSQL 导入步骤
   - 常见问题排查

## Validation
- mypy 类型检查 100% 通过
- 23 项测试通过 (18 unit + 5 integration)
- 326 条记录完整导入，无重复
- 导入耗时 < 5 秒 (PostgreSQL 本地)
- DTO 字段与 DOMAIN_CATALOG.md 100% 对应
```

### 新增 2: P17-00 · Agent 工具绑定与权限框架

**优先级**: HIGH  
**启动条件**: P16 API 完成后，P17-01 前启动  
**估计工期**: 2 天  
**所有权**: A  

#### 概要

```markdown
# P17-00 · Agent 工具绑定与权限框架

## Objective
定义 Agent 工具注册、权限检查、参数验证与结果映射的统一框架，
为 P19-P23 四角色工具调用提供基础。

## Scope
- ✅ Tool Registry 框架设计
- ✅ ToolSchema 与参数验证
- ✅ Permission 检查规则
- ✅ Result Mapping 与类型转换
- ✅ 离线降级时的 Noop 工具实现
- ❌ 不实现实时权限同步
- ❌ 不支持工具动态生成

## Key Deliverables
1. `apps/packages/logistics_agents/src/logistics_agents/protocols/tool_registry.py`
   - ToolRegistry 类
   - ToolSchema Protocol
   - register() / get_tools() / verify_permission()

2. `apps/packages/logistics_agents/src/logistics_agents/tools/builtin_tools.py`
   - 10-15 个内置工具 (对应 P16 API)
   - 每个工具包含 schema + invoke() + result_mapper()

3. `apps/packages/logistics_agents/src/logistics_agents/adapters/noop_executor.py`
   - NoopToolExecutor 类
   - 无模型环境下的文本解析与模板替代

4. `tests/test_tool_registry.py` & `tests/test_tool_invocation.py`
   - 工具注册与查询测试
   - 权限检查测试
   - 参数验证与类型转换测试
   - 离线降级测试

5. `docs/agents/TOOL_BINDING_GUIDE.md`
   - 工具设计指南
   - 权限矩阵
   - 离线模式说明

## Validation
- 所有内置工具 schema 通过 pydantic 验证
- 15 项工具交互测试通过
- 权限检查对 10 个角色覆盖 100%
- 离线模式下关键工具可用
```

### 新增 3: P18-00 · LLM 故障降级与离线执行

**优先级**: HIGH  
**启动条件**: P18-01/02 前启动  
**估计工期**: 1.5 天  
**所有权**: A  

#### 概要

```markdown
# P18-00 · LLM 故障降级与离线执行

## Objective
定义大模型不可用或故障时的完整执行路径，确保系统可在离线或无授权状态下完成
结构化规划、校验、仿真和模板解释。

## Scope
- ✅ 故障检测与回退策略
- ✅ 结构化表单输入的直接处理
- ✅ 预定义模板与规则的解释
- ✅ 离线模式的明确提示
- ✅ 日志与诊断信息
- ❌ 不声称无模型时能力等同有模型

## Key Deliverables
1. `apps/packages/logistics_agents/src/logistics_agents/adapters/llm_provider_interface.py`
   - LLMProvider Protocol (增强版)
   - FallbackProvider 类
   - health_check() / fallback_extract() / fallback_explain()

2. `apps/packages/logistics_agents/src/logistics_agents/adapters/noop_extractor.py`
   - NoopIntentExtractor 类
   - 从 JSON/form 直接解析需求
   - 无 NLP 的模式匹配与验证

3. `apps/packages/logistics_agents/src/logistics_agents/adapters/template_explainer.py`
   - TemplateExplainer 类
   - 20+ 预定义解释模板
   - 结果与约束的直接映射

4. `tests/test_llm_fallback.py` & `tests/test_offline_execution.py`
   - 10 项故障注入测试
   - 离线模式的结构化输入处理
   - 模板解释准确性测试

5. `docs/agents/OFFLINE_EXECUTION_GUIDE.md`
   - 离线功能说明
   - 支持的能力列表
   - 模板参考

## Validation
- 3 种故障场景都能正确回退
- 离线模式覆盖 80% 核心能力
- 模板解释准确率 > 95%
- 用户能清晰识别离线限制
```

### 新增 4: P36-00 · 性能基准建立与预热规范

**优先级**: MEDIUM  
**启动条件**: P35 演示前 2 周启动  
**估计工期**: 3 天  
**所有权**: A/B  

#### 概要

```markdown
# P36-00 · 性能基准建立与预热规范

## Objective
建立可重复的性能测试框架，为 P36-01/02 的优化提供基线数据。

## Scope
- ✅ 冷启动 vs 热运行基准
- ✅ 不同规模场景的耗时分布
- ✅ 内存与 CPU 占用率
- ✅ 缓存策略评估
- ✅ 预热规范 (30 次迭代)
- ❌ 不声称跨机器可复现的绝对数字

## Key Deliverables
1. `apps/backend/tests/performance/benchmark_harness.py`
   - BenchmarkRunner 类
   - 温度控制 (冷启动, 预热 30 次, 热运行)
   - 内存/CPU 采样
   - 结果汇总与统计

2. `apps/backend/tests/performance/scenarios_p36.py`
   - T1 基线 (2 单, 运输只)
   - A8 标准 (8 单, 运输+仓储)
   - B20 压力 (20 单, 完整仓运)
   - C1/C2/C3 异常恢复

3. `apps/backend/tests/performance/test_p36_baseline.py`
   - 8 项基准测试
   - P50 / P95 / P99 分布
   - 并发度 1/2/4 的对比

4. `artifacts/benchmarks/baseline-20261020/`
   - baseline.json (参考数据)
   - profile.txt (机器配置与依赖版本)

5. `docs/performance/BENCHMARK_GUIDE.md`
   - 基准使用说明
   - 预热规范
   - 对标指标

## Validation
- 基准测试稳定性: 连续 5 次运行偏差 < 10%
- 3 个场景全覆盖
- 并发安全: 4 线程无竞争条件
- 结果可重现: seed=42 固定
```

---

## 第三部分：现有 Prompt 的修正方案

### 修正 1: P04-01 (优先级: MEDIUM)

**原文**
```markdown
# P04-01 · 生成可手算的合成场景与反例数据

## Objective
生成 T1 / A8 / B20 三个合成场景...
```

**修正内容** (补充段落)

```markdown
## 数据准备与集成

本任务的输出数据集将在 P03-00 中通过 DTO 映射集成到正式数据库。生成过程应遵循以下原则：

1. **与 P03-00 的协作**
   - 生成的 JSON 结构必须与 `PreparedBundle` DTO 完全对应
   - 所有 ID 使用 UUID5 (seed=42) 确保可复现性
   - 时间戳必须是 UTC timezone-aware

2. **DTO 映射预留**
   - CargoType 枚举仅使用: GENERAL, FROZEN, CHILLED
   - TemperatureZone 枚举: AMBIENT, CHILLED, FROZEN
   - 其他枚举标记为 `pending` 等待 P02 批准

3. **导入幂等性**
   - UUID 重复时必须产生约束错误 (不静默覆盖)
   - 所有数值使用整数或 ISO 8601 格式
   - 时间窗倒序时数据生成即报错

4. **快照验证** (后续 P03-00 依赖)
   - 每个场景生成后计算 SHA256 哈希
   - 将哈希记录在 `manifest.json` 中
   - 重复生成时哈希必须相同
```

### 修正 2: P06-01 (优先级: HIGH)

**新增小节**

```markdown
## 矩阵版本化与缓存策略

### 6.1 矩阵生命周期

矩阵是求解的关键数据，必须显式版本化：

```
MatrixVersion {
  id: UUID
  created_at: datetime
  road_network_version: str          # "road-v1", "road-v2-weather", etc.
  time_slot: (start_time, end_time)  # 何时有效
  validity_until: datetime           # 过期时间
  source: "synthesis" | "api" | "offline"
  metadata: {
    cell_count: int,               # N×N
    sample_density: float,         # 0.0-1.0
    weather_event_id: str | null,  # 天气影响
    hash: SHA256                   # 内容完整性
  }
}
```

### 6.2 缓存范围与失效

- 缓存键: (coordinates_tuple, road_version, vehicle_config, time_slot)
- 保留最近 1000 矩阵或最近 7 天，按容量限制 100 MB
- 道路网版本升级时旧矩阵标记为 DEPRECATED（不删除）
- 天气事件发生时生成新矩阵版本，旧版本保留用于对比

### 6.3 求解器内调用规范

- 不在回调内查询或生成矩阵（已在外部批量获取）
- 矩阵版本 ID 必须写入 OptimizationResult 用于审计
- 同一求解内多次使用矩阵时验证版本一致
```

### 修正 3: P09-01 (优先级: HIGH)

**新增小节**

```markdown
## 库位库存区间的形式化定义

仓储中库位的库存变化是时间相关的，必须显式建模：

### 9.1 库存占用函数

对于库位 `loc` 和时间区间 `[t0, t∞)`：

```
occupancy(loc, t) = 
  initial_stock(loc) 
  + ∑ inbound(t') for t' ∈ [t0, t]         (到货累积)
  - ∑ outbound_committed(t') for t' ∈ [t0, t]  (已分配出库)
  - ∑ outbound_executed(t') for t' ∈ [t0, t]   (已执行出库)
```

其中：
- `inbound(t')`: 该时刻完成入库的数量
- `outbound_committed(t')`: 规划分配的出库（未执行）
- `outbound_executed(t')`: 实际已出库的数量

### 9.2 容量约束在 CP-SAT 中的表达

```python
# 对于每个库位与时间区间
for task_i, task_j in task_pairs:
    if task_i.warehouse_loc == task_j.warehouse_loc:
        # 两个仓储任务不能同时占用库位
        model.Add(
            task_i.end_time <= task_j.start_time |
            task_j.end_time <= task_i.start_time
        )

# 库存保鲜约束（示例）
for loc in warehouse_locations:
    for t in [t_entry, t_entry + retention_period]:
        model.Add(
            occupancy[loc][t] >= 0
        )
```

### 9.3 独立校验的 Oracle 定义

在 P10-03 的反例套件中，应包含：
- 库位容量超限的失败案例 (20 个)
- 时间重叠导致超容的失败案例 (15 个)
- 保鲜期超出的失败案例 (10 个)
- 库位库存突增/消失的异常案例 (5 个)
```

### 修正 4: P10-02 (优先级: CRITICAL)

**新增小节**

```markdown
## 独立校验反例集合的生成与覆盖

### 10.1 反例覆盖矩阵

创建 `tests/fixtures/adversarial_validation_suite.py` 包含 100+ 反例：

```python
VALIDATION_TEST_SUITE = {
    # 数据层反例 (20 个)
    'data': {
        'missing_warehouse': [...],        # 订单指向不存在的仓库
        'invalid_time_window': [...],      # 时间窗倒序
        'zero_capacity': [...],            # 容量为 0
        'negative_weight': [...],          # 负重量
        # ...
    },
    
    # 自然语言与输入层反例 (15 个)
    'nlp': {
        'conflicting_constraints': [...],  # 相互矛盾的约束
        'missing_critical_field': [...],   # 缺少温区/截止时间
        'prompt_injection': [...],         # 试图绕过校验的注入
        # ...
    },
    
    # 运输层反例 (20 个)
    'transport': {
        'weight_ok_volume_exceeded': [...],  # 重量合格但体积超
        'mixed_temperature_zones': [...],    # 单温区车装多温货
        'unreachable_location': [...],       # 无路径的节点对
        # ...
    },
    
    # 仓储层反例 (25 个)
    'warehouse': {
        'time_overlap_exceeds_capacity': [...],
        'shelf_life_expired': [...],
        'isolation_stock_used': [...],
        'cleaning_without_workers': [...],
        # ...
    },
    
    # 联合层反例 (15 个)
    'joint': {
        'vehicle_departs_before_cargo_ready': [...],
        'no_dock_at_warehouse': [...],
        'warehouse_change_missing_leg': [...],
        # ...
    },
    
    # 事务与一致性反例 (5 个)
    'transaction': {
        'duplicate_commitment': [...],
        'snapshot_version_drift': [...],
        # ...
    },
}
```

### 10.2 Oracle 定义与检查方法

每个反例必须包含：
```python
@dataclass
class AdversarialCase:
    name: str                      # 描述
    input_data: dict              # 测试输入
    expected_violation: str        # 预期违规类型
    oracle_check: Callable         # 独立验证函数
    should_fail: bool             # 是否应该失败
    
    def validate(self, result: PlanResult) -> bool:
        """使用 oracle_check 独立验证"""
        return self.oracle_check(result)
```

### 10.3 验收标准

- 100+ 反例完整实现
- 100% 通过 oracle 验证
- 求解器对所有反例都输出错误或 INFEASIBLE
- 独立校验覆盖 100% 的硬约束类型
```

### 修正 5-10 (简要列表)

| Prompt | 具体修正 | 行数 |
|--------|---------|------|
| P16-01 | 补充"异常时 API 降级与缓存策略" | 30 |
| P18-02 | 补充"模型重试、超时与回退" | 25 |
| P19-01 | 补充"结构化表单与非 LLM 流程" | 40 |
| P28-02 | 补充"快照恢复时的一致性保证" | 20 |
| P32-01 | 补充"无可行解时的指标计算" | 15 |
| P34-03 | 补充"并发提交去重与幂等性" | 35 |

---

## 第四部分：执行计划

### Phase A: 立即启动 (本周)

```
Day 1-2: 补充修正 1-4 (P04/P06/P09/P10)
  → 核心逻辑定义，让 P06-P10 实现方有明确指引
  
Day 3-4: 生成 P03-00 初稿
  → DTO 结构 + 转换逻辑
  → 测试框架 (unit + integration)
  
Day 5: 内部审查与迭代
  → 核对与 P02 交接的一致性
  → 修正类型与命名
```

### Phase B: P02 完成后 (1-2 周)

```
Day 1-2: 完成 P03-00 + P03-01 集成
  → PostgreSQL 导入验证
  → 快照固定
  
Day 3-4: 生成 P17-00 初稿
  → 工具注册框架
  → 权限矩阵
  
Day 5: 生成 P18-00 初稿
  → 离线模式规范
  → 模板库 (20+ 模板)
```

### Phase C: P35 演示前 (2-3 周)

```
Day 1-3: 生成 P36-00
  → 基准框架
  → 3 个场景的冷/热运行测试
  
Day 4-5: 补充修正 5-10
  → 现有 Prompt 的细节完善
```

---

## 第五部分：交付物清单

### 新增文件 (4 个)

- [ ] `docs/prompts/03-database/P03-00-data-integration.md` (150 行)
- [ ] `docs/prompts/09-agents/P17-00-tool-binding.md` (120 行)
- [ ] `docs/prompts/09-agents/P18-00-llm-fallback.md` (140 行)
- [ ] `docs/prompts/12-integration/P36-00-benchmark.md` (130 行)

### 修改的文件 (10 个)

- [ ] `docs/prompts/04-data/P04-01-canonical-fixtures.md` (+ 50 行)
- [ ] `docs/prompts/05-transport/P06-01-transport-contract.md` (+ 60 行)
- [ ] `docs/prompts/06-warehouse/P09-01-intervals-precedence.md` (+ 80 行)
- [ ] `docs/prompts/06-warehouse/P10-02-joint-validator.md` (+ 120 行)
- [ ] `docs/prompts/04-api/P16-01-optimization-job-api.md` (+ 30 行)
- [ ] `docs/prompts/09-agents/P18-02-llm-resilience.md` (+ 25 行)
- [ ] `docs/prompts/09-agents/P19-01-intent-extraction.md` (+ 40 行)
- [ ] `docs/prompts/07-simulation/P28-02-replay-comparison-ui.md` (+ 20 行)
- [ ] `docs/prompts/11-evaluation/P32-01-metric-calculators.md` (+ 15 行)
- [ ] `docs/prompts/12-integration/P34-03-failure-recovery-e2e.md` (+ 35 行)

### 验证清单

- [ ] 所有 Prompt 在 README.md 中索引更新
- [ ] 4 个新增 Prompt 包含完整的 Scope/Objective/Validation
- [ ] 10 个修改的 Prompt 核对与前置/后继的一致性
- [ ] 不存在循环依赖 (DAG 检查)
- [ ] 所有 Prompt 字数在 1000-3000 行之间 (超大分为多个)

---

**版本历史**
- 1.0 (2026-10-20): 初稿，4 新增 + 10 修正

**下一审查**
- N05 Codex 最终审查完成后
