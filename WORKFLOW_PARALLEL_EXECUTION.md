# 并行工作流程梳理与 Agent 任务分配

**版本**: 1.0  
**日期**: 2026-10-20  
**目标**: 5-7 天内完成 N02-N05 验收，解除 G01 阻塞  
**执行模式**: 4 个并行轨道 + 2 个串行汇聚 + 1 个最终交叉验证

---

## 第一部分：工作流程全景

```
┌──────────────────────────────────────────────────────────────────┐
│ 当前状态: G01 未签收 → P02-P39 全部阻塞                         │
│ 目标状态: G01 签收 → P02 释放启动                              │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────── 并行轨道 (Day 1-5) ─────────────────────┐
│                                                                   │
│  轨道 A (Codex)          轨道 B (DSH)         轨道 C (DevOps)    │
│  ├─ N02 G00 复核         ├─ N03 交接刷新      ├─ PostgreSQL 启动 │
│  └─ 输出: G00.json       └─ 输出: dsh.md      ├─ 导入脚本验证    │
│                                               └─ 快照准备        │
│                                                                   │
│  轨道 D (Prompt工程)                                            │
│  ├─ P03-00 初稿                                                │
│  ├─ P10-02 补充                                                │
│  └─ 其他 2 个新 Prompt                                         │
│                                                                   │
├─────────────────────── 串行汇聚 (Day 6-7) ──────────────────────┤
│                                                                   │
│  N04 (ZCode) 预验收 ← 需要 A/B/C 产物都就绪                   │
│  ↓                                                              │
│  N05 (Codex) 最终签收 ← 需要 N04 通过                         │
│  ↓                                                              │
│  ✅ G01.json 生成 ← P02 释放                                   │
│                                                                   │
├─────────────────────── 交叉验证 (Day 8) ───────────────────────┤
│                                                                   │
│  Claude 最终检验:                                              │
│  ├─ 检查 N02-N05 证据链完整性                                  │
│  ├─ 验证所有交接哈希真实非空                                   │
│  ├─ 核实 G01 签收条件满足                                      │
│  └─ 生成最终验证报告                                           │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 第二部分：四个并行轨道详解

### 轨道 A: Codex 独立审查 (N02)

**Agent**: Codex 治理/独立审查  
**工作根**: `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`  
**预计耗时**: 1 天  
**前置**: P00-01/02/03 文档、PHASE_GATES.md、冻结契约

#### 提示词 (A-PROMPT-N02)

```markdown
# N02 · Codex 独立审查与 G00 复核

## 你的角色
你是与实现/治理分开的独立审查专家。职责是独立验证 Phase 00 的基线契约、
复核 issues 漂移、生成真实的 G00.json 签收记录。

## 当前事实
- P00-01/02/03 已交付，需要独立复核
- G00 的 25 项输入中 `docs/architecture/issues/README.md` 有漂移
- 冻结的 12 项契约及 173 项旧基线哈希均相符
- 上轮 DSH 旧哈希: afbc7e4c…（已过期）

## 你的工作

### 第一步: 复核 G00 输入（1 小时）

```bash
# 1. 计算所有冻结契约的哈希
python tools/ai_coding_plan/validate_plan.py --check-only

# 2. 与 contract_freeze.json 比对
# 预期: 12 项契约哈希 100% 吻合

# 3. 识别漂移
find docs/architecture/issues/ -type f -name "*.md" | \
  xargs sha256sum > /tmp/issues_current.txt

# 对比与冻结记录
diff /tmp/issues_current.txt contract_freeze.json
```

### 第二步: 独立复算输入哈希（2 小时）

对以下文件逐一计算 SHA256 并记录：

**必检清单:**
- [ ] docs/plan/TASK_MANIFEST.json
- [ ] docs/plan/PHASE_GATES.md
- [ ] docs/architecture/DOMAIN_CATALOG.md
- [ ] docs/architecture/DATA_CONTRACTS.md
- [ ] 12 项冻结契约 (逐项计算)
- [ ] P00-01/02/03 Prompt 文件
- [ ] 前置 Gate 检查脚本

输出: `artifacts/reviews/2026-10-20/g00_input_hashes.json`

### 第三步: 核实基线清单（1 小时）

```json
{
  "baseline_files": [
    "BASELINE_INVENTORY.json",
    "173 旧资产列表"
  ],
  "verification": {
    "all_hashes_present": true,
    "no_truncated_values": true,
    "all_non_empty": true
  }
}
```

### 第四步: 生成 G00 复核记录（1 小时）

```json
{
  "gate_id": "G00",
  "phase": 0,
  "reviewer": "<你的 session 名>",
  "reviewed_at": "2026-10-20T10:00:00Z",
  "verdict": "PASSED" or "FAILED",
  "input_hashes": {
    "task_manifest": "...",
    "phase_gates": "...",
    // 所有 25 项输入非空哈希
  },
  "findings": [
    // 如果有漂移或问题，列出具体项
  ],
  "approved_by": "<你的身份>",
  "signature": "<GPG or 其他签名>"
}
```

## 输出物

必须生成:
- [ ] `artifacts/gates/G00-codex-review.json` (正式评审记录)
- [ ] `tmp/N02/g00_input_verification.log` (详细日志)
- [ ] `tmp/N02/hash_comparison.txt` (哈希对比结果)

## 验收标准

- ✅ 25 项输入全部非空哈希
- ✅ 12 项冻结契约 100% 复算通过
- ✅ 漂移项已记录 (issues/README.md)
- ✅ G00.json 符合 schema
- ✅ reviewer/approved_by 真实有效

## 禁止事项

- ❌ 不修改任何实现代码
- ❌ 不改变 P00-01/02/03
- ❌ 不复制旧 reviewer 冒充当前审查
- ❌ 不沿用过期的 DSH 哈希

## 注意

issues/README.md 的漂移是已知的，不需要重新冻结整个契约。
只需在评审记录中明确记录这项漂移，后续由治理任务处理。
```

**交付物**:
- [ ] `artifacts/gates/G00-codex-review.json`
- [ ] `tmp/N02/verification.log`
- [ ] `docs/handoffs/N02/evidence.json`

---

### 轨道 B: DSH 交接刷新 (N03)

**Agent**: DSH-A (原实现者)  
**工作根**: 同上  
**预计耗时**: 1 天  
**前置**: N02 G00 复核完成、P01-01/02/03 现状代码

#### 提示词 (B-PROMPT-N03)

```markdown
# N03 · DSH 自身 Phase 01 交接刷新

## 你的角色
DSH-A，本项目 A 范围的主实现者。你的职责是刷新 Phase 01 三个任务的
交接证据，并为下游 ZCode 预验收做好准备。

## 当前事实
- P01-02 四项限定返工已完成 (226 passed)
- AGENTS.md 所有权由 Codex 补充，现为 A
- N02 G00 复核刚完成，G00.json 已生成
- 旧轮 DSH evidence.json 已存档 (afbc7e4c…)

## 你的工作

### 第一步: 核对文件完整性（30 分钟）

```bash
# 1. 验证 P01-01/02/03 源码未被意外修改
git diff HEAD~1 apps/ packages/ tests/ | wc -l
# 预期: 0 行 (无意外变化)

# 2. 检查所有权配置
cat OWNERSHIP.json | grep -E '"P01-|AGENTS"'
# 预期: AGENTS.md 所有权为 "A"

# 3. 验证现有 226 passed 记录
find artifacts/ -name "*test*pass*" -o -name "*226*"
```

### 第二步: 重新计算候选哈希（1 小时）

对三个任务分别计算：

**P01-01 哈希清单:**
```bash
find apps/backend -type f -name "*.py" | xargs sha256sum > /tmp/p01-01-files.txt
# 包括: bootstrap, dependency, config

echo "P01-01 候选哈希: $(sha256sum /tmp/p01-01-files.txt)"
```

**P01-02 哈希清单:**
```bash
find tests/ -type f -name "*.py" | xargs sha256sum > /tmp/p01-02-files.txt
# 包括: 226 个通过的测试

echo "P01-02 候选哈希: $(sha256sum /tmp/p01-02-files.txt)"
```

**P01-03 哈希清单:**
```bash
find packages/ -type f -name "*.py" | xargs sha256sum > /tmp/p01-03-files.txt
# 包括: 所有权治理与 OWNERSHIP.json

echo "P01-03 候选哈希: $(sha256sum /tmp/p01-03-files.txt)"
```

### 第三步: 生成新的交接报告（1 小时）

为每个任务创建: `docs/handoffs/P01-xx/dsh.md`

```markdown
# P01-xx DSH 交接报告 (N03, 2026-10-20)

## 任务摘要
执行返工任务 P01-xx，目标是确保...

## 前置 Gate
- G00: ✅ 通过 (N02 复核完成)
- 依赖任务: P00-01/02/03

## 交付产物

### 源码与配置
- 位置: apps/backend/ (P01-01) / tests/ (P01-02) / packages/ (P01-03)
- 候选哈希: <sha256>
- 哈希计数: <文件个数>

### 验证结果
- 单元测试: 226 passed / 0 failed
- 类型检查: ✅ mypy 通过
- 集成测试: ✅ 环境可验证

## 限制与已知问题
- 仅限 Phase 01 范围
- 不包含 P02-P39 任何内容
- PostgreSQL 连接未验证 (P03 任务)

## ZCode 预验收清单
- [ ] 计算候选哈希 (已: <值>)
- [ ] 验证 226 tests 通过
- [ ] 检查类型安全
- [ ] 核实所有权

## 签署
交付者: DSH-A  
交付日期: 2026-10-20  
状态: READY_FOR_ZCODE
```

### 第四步: 生成交接证据（30 分钟）

```json
// artifacts/handoffs/P01-01/dsh/evidence.json
{
  "task_id": "P01-01",
  "phase": 1,
  "delivered_by": "DSH-A",
  "delivered_at": "2026-10-20T12:00:00Z",
  "candidate": {
    "code_hash": "<sha256>",
    "file_count": 42,
    "test_count": 96,
    "test_passed": 96,
    "test_failed": 0
  },
  "dependencies": {
    "G00": "passed",
    "P00-01": "completed",
    "P00-02": "completed",
    "P00-03": "completed"
  },
  "validation": {
    "mypy": "passed",
    "lint": "passed",
    "unit_tests": "passed"
  },
  "limitations": [
    "PostgreSQL integration not verified",
    "P02-P39 not included"
  ],
  "status": "READY_FOR_ZCODE"
}
```

## 输出物

每个任务必须有:
- [ ] `docs/handoffs/P01-xx/dsh.md` (交接报告)
- [ ] `artifacts/handoffs/P01-xx/dsh/evidence.json` (证据)
- [ ] `artifacts/handoffs/P01-xx/dsh/test_results.log` (测试日志)

三个任务共计:
- [ ] 3 份 dsh.md
- [ ] 3 份 evidence.json
- [ ] 3 份 test_results.log

## 验收标准

- ✅ 所有哈希真实计算（非复制）
- ✅ 226 passed 有原始日志证明
- ✅ OWNERSHIP.json 所有权正确
- ✅ 不包含 P02 及之后内容
- ✅ 所有文件存在且非空

## 禁止事项

- ❌ 不修改源码（哈希会变）
- ❌ 不生成 ZCode precheck (N04 才做)
- ❌ 不签署 Gate (只写交接)
- ❌ 不启动 P02 或修改公共契约
```

**交付物**:
- [ ] 3 × `docs/handoffs/P01-xx/dsh.md`
- [ ] 3 × `artifacts/handoffs/P01-xx/dsh/evidence.json`
- [ ] 3 × `artifacts/handoffs/P01-xx/dsh/test_results.log`

---

### 轨道 C: 数据库环境与导入准备 (DevOps)

**Agent**: 基础设施/DevOps  
**工作根**: 同上  
**预计耗时**: 1.5 天  
**前置**: 无 (可独立进行)

#### 提示词 (C-PROMPT-DEVOPS)

```markdown
# 轨道 C · PostgreSQL 环境启动与数据导入验证

## 你的角色
基础设施工程师。负责启动测试环境、验证数据导入脚本、
为后续 P03 实现准备就绪的数据库。

## 当前事实
- 数据准备包完整: data/preparation/competition-2026/
- SQLite 预览库可用: preview.sqlite3
- PostgreSQL 导入脚本已生成: postgres_staging.sql
- 本地验证通过: 18 项检查

## 你的工作

### 第一步: Docker 环境启动（30 分钟）

```bash
# 1. 设置环境变量
export LOGISTICS_PREP_PASSWORD="<secure-password>"
export COMPOSE_FILE="deploy/data-preparation-2026/compose.yaml"

# 2. 启动 PostgreSQL 容器
docker compose up -d --wait postgres

# 验证服务就绪
docker compose ps
# STATUS 应显示 "Up"

# 3. 测试连接
docker compose exec -T postgres psql -U logistics_prep -d postgres \
  -c "SELECT version();"

# 输出示例: PostgreSQL 15.x on ...
```

### 第二步: SQLite 验证对标（30 分钟）

```bash
# 1. 查询 SQLite 计数
sqlite3 data/preparation/competition-2026/generated/preview.sqlite3 << SQL
SELECT 'Order' as entity, COUNT(*) FROM "Order"
UNION ALL
SELECT 'Cargo', COUNT(*) FROM "Cargo"
UNION ALL
SELECT 'Warehouse', COUNT(*) FROM "Warehouse"
UNION ALL
SELECT 'Vehicle', COUNT(*) FROM "Vehicle";
SQL

# 记录结果: T1=2, A8=8, B20=20, Total=30

# 2. 检查外键完整性
sqlite3 data/preparation/competition-2026/generated/preview.sqlite3 << SQL
-- 检查孤立订单
SELECT COUNT(*) FROM "Order" o
WHERE NOT EXISTS (
  SELECT 1 FROM "Warehouse" w
  WHERE w.warehouse_id = o.source_warehouse_id
);
-- 预期: 0
SQL
```

### 第三步: PostgreSQL 导入验证（1 小时）

```bash
# 1. 复制导入脚本
docker compose cp \
  data/preparation/competition-2026/generated/postgres_staging.sql \
  postgres:/tmp/preparation.sql

# 2. 执行导入
docker compose exec -T postgres psql \
  -v ON_ERROR_STOP=1 \
  -U logistics_prep \
  -d logistics_prep_test \
  -f /tmp/preparation.sql

# 预期: 创建 competition_preparation schema
#       导入 326 条实体记录

# 3. 验证导入计数
docker compose exec -T postgres psql -U logistics_prep \
  -d logistics_prep_test << SQL
SELECT COUNT(*) as entities FROM competition_preparation.entities;
SELECT COUNT(*) as refs FROM competition_preparation.refs;
SQL

# 预期输出:
# entities | 326
# refs     | 979

# 4. 验证无重复 UUID
docker compose exec -T postgres psql -U logistics_prep \
  -d logistics_prep_test << SQL
SELECT entity_id, COUNT(*) FROM competition_preparation.entities
GROUP BY entity_id HAVING COUNT(*) > 1;
SQL

# 预期: 无结果 (0 行)

# 5. 验证时间窗合理性
docker compose exec -T postgres psql -U logistics_prep \
  -d logistics_prep_test << SQL
SELECT COUNT(*) FROM competition_preparation.entities
WHERE entity_type = 'Order'
  AND (data->>'end_time')::timestamp < (data->>'start_time')::timestamp;
SQL

# 预期: 0 行
```

### 第四步: 重复导入测试（幂等性）（30 分钟）

```bash
# 再次运行导入脚本 (应该不新增记录)

docker compose exec -T postgres psql \
  -v ON_ERROR_STOP=1 \
  -U logistics_prep \
  -d logistics_prep_test \
  -f /tmp/preparation.sql

# 预期: 触发唯一性约束，回滚所有操作
# 记录数仍为 326/979

docker compose exec -T postgres psql -U logistics_prep \
  -d logistics_prep_test \
  -c "SELECT COUNT(*) FROM competition_preparation.entities;"

# 预期输出: 326 (未增长)
```

### 第五步: 快照与版本记录（30 分钟）

```bash
# 1. 导出快照信息
docker compose exec -T postgres psql -U logistics_prep \
  -d logistics_prep_test \
  -c "SELECT NOW() as snapshot_time, \
             COUNT(*) as entity_count \
        FROM competition_preparation.entities;" > /tmp/snapshot.txt

# 2. 创建快照记录
cat > tmp/C_DEVOPS/snapshot_record.json << EOF
{
  "snapshot_id": "prep-v1-20261020",
  "snapshot_time": "2026-10-20T13:00:00Z",
  "source": "data/preparation/competition-2026/",
  "entity_count": 326,
  "ref_count": 979,
  "database": "logistics_prep_test",
  "schema": "competition_preparation",
  "verification": {
    "no_duplicates": true,
    "all_fk_valid": true,
    "time_windows_valid": true,
    "idempotent_reimport": true
  }
}
EOF
```

## 输出物

必须生成:
- [ ] `tmp/C_DEVOPS/docker_startup.log` (启动日志)
- [ ] `tmp/C_DEVOPS/sqlite_verification.txt` (SQLite 验证结果)
- [ ] `tmp/C_DEVOPS/postgres_import.log` (导入完整日志)
- [ ] `tmp/C_DEVOPS/snapshot_record.json` (快照记录)
- [ ] `tmp/C_DEVOPS/idempotent_test.log` (重复导入测试)

## 验收标准

- ✅ Docker 容器正常运行
- ✅ 326 条记录完整导入
- ✅ 无重复 UUID
- ✅ 所有 FK 完整性检查通过
- ✅ 重复导入后记录计数不变
- ✅ 快照版本号已记录

## 环境保持

导入完成后环境保持运行，供后续 P03 使用。
```

**交付物**:
- [ ] `tmp/C_DEVOPS/docker_startup.log`
- [ ] `tmp/C_DEVOPS/postgres_import.log`
- [ ] `tmp/C_DEVOPS/snapshot_record.json`
- [ ] 运行中的 PostgreSQL 容器

---

### 轨道 D: 提示词工程补充 (Prompt Engineer)

**Agent**: 提示词工程师  
**工作根**: 同上  
**预计耗时**: 2 天  
**前置**: docs/prompts/README.md、OPTIMIZATION-PLAN-20261020.md

#### 提示词 (D-PROMPT-ENGINEERING)

```markdown
# 轨道 D · 新增与修正 Prompt 编写

## 你的角色
提示词工程师。负责生成 4 个新 Prompt 和补充 10 个现有 Prompt，
确保 109 个 Prompt 体系完整、无缺口。

## 当前事实
- 现有 109 Prompt 框架完整
- 缺失 4 个: P03-00, P17-00, P18-00, P36-00
- 需修正 10 个: P04-01, P06-01, P09-01, P10-02 等
- 所有修改记录在 OPTIMIZATION-PLAN-20261020.md

## 你的工作

### 第一步: 生成新 Prompt (Day 1)

#### P03-00 · 数据库集成与 DTO 映射 (CRITICAL)

位置: `docs/prompts/03-database/P03-00-data-integration.md`

内容框架:
- Objective: 将 bundle.json → 领域 DTO → PostgreSQL 正式表
- Scope: DTO 设计 + 转换函数 + 迁移脚本
- Files: apps/packages/logistics_contracts/dtos/preparation.py
        apps/backend/src/logistics_persistence/converters/
        tests/test_preparation_converter.py
- Business Rules: FK 完整性 + 幂等导入 + 事务一致性
- Validation: 23 项测试通过 + 326 条记录导入

参考: docs/data/database-integration-guide-20261020.md (已生成的技术指南)

#### P17-00 · Agent 工具绑定与权限框架 (HIGH)

位置: `docs/prompts/09-agents/P17-00-tool-binding.md`

内容框架:
- Objective: Tool Registry + 权限检查 + 结果映射框架
- Scope: 10-15 个内置工具 + 离线 Noop 实现
- Validation: 工具注册表完整 + 权限矩阵覆盖 100%

#### P18-00 · LLM 故障降级与离线执行 (HIGH)

位置: `docs/prompts/09-agents/P18-00-llm-fallback.md`

内容框架:
- Objective: 模型不可用时的完整执行路径
- Scope: 3 种故障场景 + 结构化输入处理 + 20+ 模板
- Validation: 离线模式覆盖 80% 核心能力

#### P36-00 · 性能基准建立与预热规范 (MEDIUM)

位置: `docs/prompts/12-integration/P36-00-benchmark.md`

内容框架:
- Objective: 可重复的性能测试框架
- Scope: 冷启动 + 热运行 + 预热 30 次规范
- Validation: 3 个场景 + 并发度 1/2/4

### 第二步: 修正现有 Prompt (Day 2)

#### 修正清单 (按优先级)

**CRITICAL:**
- [ ] P10-02: 补充"反例覆盖矩阵" (100+ 反例定义)
      参考: docs/prompts/OPTIMIZATION-PLAN-20261020.md 第三部分

**HIGH:**
- [ ] P06-01: 补充"矩阵版本化与缓存策略" (60 行)
- [ ] P09-01: 补充"库位库存区间形式化定义" (80 行)
- [ ] P18-02: 补充"模型 API 故障时的回退策略" (25 行)
- [ ] P34-03: 补充"并发提交去重与幂等性" (35 行)

**MEDIUM:**
- [ ] P04-01: 补充"与 P03-00 的协作" (50 行)
- [ ] P16-01: 补充"异常场景下的 API 降级" (30 行)
- [ ] P19-01: 补充"结构化表单输入处理" (40 行)
- [ ] P32-01: 补充"无可行解的指标计算" (15 行)

**LOW:**
- [ ] P28-02: 补充"快照恢复的一致性保证" (20 行)

### 第三步: 生成验证清单（30 分钟）

```markdown
# Prompt 完整性检查清单

## 新增 4 个 Prompt
- [ ] P03-00 完整，无缺失部分
- [ ] P17-00 完整，无缺失部分
- [ ] P18-00 完整，无缺失部分
- [ ] P36-00 完整，无缺失部分

## 修正 10 个 Prompt
- [ ] 所有修改已应用至源文件
- [ ] 没有重复或冲突的改动
- [ ] 所有新增内容与前置/后继一致

## 文档与索引
- [ ] README.md 已更新，包含 4 新 Prompt
- [ ] 所有 Prompt 都有 Dependencies 和 Blocks
- [ ] 不存在循环依赖

## 质量检查
- [ ] 每个 Prompt 1000-3000 行（≤50000）
- [ ] Scope/Out of Scope 明确
- [ ] Validation Commands 可执行
- [ ] 所有文件路径正确
```

## 输出物

**新增文件 (4 个):**
- [ ] `docs/prompts/03-database/P03-00-data-integration.md`
- [ ] `docs/prompts/09-agents/P17-00-tool-binding.md`
- [ ] `docs/prompts/09-agents/P18-00-llm-fallback.md`
- [ ] `docs/prompts/12-integration/P36-00-benchmark.md`

**修改的文件 (10 个):**
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

**索引与验证:**
- [ ] `docs/prompts/README.md` (更新索引)
- [ ] `tmp/D_PROMPTS/completion_checklist.md` (完整性检查)
- [ ] `tmp/D_PROMPTS/new_prompts_summary.txt` (新增摘要)

## 验收标准

- ✅ 4 新 Prompt 符合现有风格
- ✅ 10 修正无遗漏或冲突
- ✅ 所有 109 Prompt 无循环依赖
- ✅ README.md 索引 100% 覆盖
- ✅ 所有提示词可被 Agent 独立执行
```

**交付物**:
- [ ] 4 × 新 Prompt 文件
- [ ] 10 × 修改的 Prompt 文件
- [ ] `docs/prompts/README.md` (更新)
- [ ] `tmp/D_PROMPTS/completion_checklist.md`

---

## 第三部分：串行汇聚 (Day 6-7)

### 汇聚 1: N04 ZCode 预验收

**Agent**: ZCode  
**前置**: A/B/C/D 全部完成  
**工作根**: 同上  
**预计耗时**: 2 天

#### 提示词 (N04-PROMPT-ZCODE)

```markdown
# N04 · ZCode 独立预验收三项任务

## 你的角色
ZCode，独立预验收专家。职责是独立重验 P01-01/02/03 三个任务，
确保所有证据真实、哈希准确、没有缺陷。

## 前置条件检查

确保以下都已完成：
- [ ] N02 G00 复核: ✅ G00.json 已生成
- [ ] N03 DSH 交接: ✅ 3 份 dsh.md + evidence 已生成
- [ ] 轨道 C DevOps: ✅ PostgreSQL 运行，数据导入完成
- [ ] 轨道 D Prompt: ✅ 4 新 + 10 修 Prompt 已生成

## 你的工作

### 任务 P01-01: Monorepo 与工程基础

**验证清单:**
1. 检查代码完整性
   ```bash
   cd apps/backend
   find . -name "*.py" | wc -l
   # 应有 42+ 文件
   ```

2. 重新计算哈希
   ```bash
   find apps/backend -type f -name "*.py" | sort | xargs sha256sum | sha256sum
   ```
   与 dsh/evidence.json 中的 code_hash 比对，必须完全相同

3. 验证所有权
   ```bash
   grep '"P01-01"' OWNERSHIP.json
   # 应显示所有权为 A
   ```

4. 检查前置 Gate
   ```bash
   python tools/ai_coding_plan/validate_plan.py --check-only --phase 1
   ```

**输出: precheck_p01_01.json**
```json
{
  "task_id": "P01-01",
  "verified_input_hashes": {
    "code_hash": "<重新计算的值>",
    "manifest_hash": "...",
    "phase_gates_hash": "...",
    "dsh_evidence_hash": "...",
    "task_prompt_hash": "..."
  },
  "verification": {
    "file_count_matches": true,
    "code_hash_matches_dsh": true,
    "ownership_correct": true,
    "gate_dependencies_met": true
  },
  "verdict": "Z_PRECHECK_PASSED" or "Z_PRECHECK_FAILED",
  "reviewer": "<your_session>",
  "reviewed_at": "2026-10-20T..."
}
```

### 任务 P01-02: 检查与 Gate Runner

**验证清单:**
1. 运行完整测试套件
   ```bash
   cd tests
   pytest -v --tb=short 2>&1 | tee /tmp/pytest_full.log
   
   # 检查输出
   grep "passed" /tmp/pytest_full.log
   # 应显示: 226 passed, 0 failed
   ```

2. 验证测试日志哈希
   ```bash
   sha256sum /tmp/pytest_full.log
   ```
   与 dsh/evidence.json 中的 test_log_hash 比对

3. 检查类型安全
   ```bash
   mypy apps/ packages/ --ignore-missing-imports
   ```

**输出: precheck_p01_02.json**

### 任务 P01-03: 迁移与治理

**验证清单:**
1. 检查所有权文件
   ```bash
   python -m json.tool OWNERSHIP.json > /tmp/ownership_check.txt
   
   # 搜索遗漏
   grep -c '"P01-' /tmp/ownership_check.txt
   # 应 >= 3
   ```

2. 验证迁移映射
   ```bash
   find apps/ packages/ -type f -name "*.py" | xargs grep "P00" | wc -l
   ```

3. 检查前置 Gate
   ```bash
   grep "G00" docs/plan/PHASE_GATES.md
   # 确认 G00 是 P01-01 的前置
   ```

**输出: precheck_p01_03.json**

## 最终输出

必须生成 3 个预验收报告，都放在：
- [ ] `artifacts/handoffs/P01-01/zcode/precheck.json`
- [ ] `artifacts/handoffs/P01-02/zcode/precheck.json`
- [ ] `artifacts/handoffs/P01-03/zcode/precheck.json`

三个报告都必须包含：
- ✅ verified_input_hashes (所有哈希真实计算，非空)
- ✅ verdict 字段为 Z_PRECHECK_PASSED
- ✅ reviewer 与 reviewed_at 真实
- ✅ 详细的验证日志

## 验收标准

- ✅ 所有输入哈希非空且是 64 位 SHA-256
- ✅ 226 passed 有原始 pytest 日志
- ✅ 哈希与 DSH evidence 完全匹配
- ✅ 三个 precheck.json 都有效且不冲突

## 如果发现问题

记录具体缺陷与重现步骤，不要修改数据或虚构结果。
交由下一执行者 N05 处理。
```

**交付物**:
- [ ] 3 × `artifacts/handoffs/P01-xx/zcode/precheck.json`
- [ ] `tmp/N04/zcode_verification.log`

---

### 汇聚 2: N05 Codex 最终签收 (G01)

**Agent**: Codex 独立审查 (新会话)  
**前置**: N04 ZCode 通过  
**工作根**: 同上  
**预计耗时**: 1 天

#### 提示词 (N05-PROMPT-FINAL-REVIEW)

```markdown
# N05 · Codex 最终审查与 G01 签收

## 你的角色
Codex 独立审查员。这是最后一个关卡，负责生成正式的 G01 Gate 签收记录。

## 前置检查

确保以下都已完成：
- [ ] N02 G00 复核: ✅ artifacts/gates/G00-codex-review.json 存在
- [ ] N03 DSH 交接: ✅ 3 份 dsh.md 存在且完整
- [ ] N04 ZCode 预验: ✅ 3 份 precheck.json 都是 PASSED
- [ ] 轨道 C/D: ✅ 环境与 Prompt 就绪

## 你的工作

### 第一步: 审查交接证据链（1 小时）

对每个前置任务验证：

**G00 检查:**
```bash
# 检查 G00.json 结构
jq '.verdict' artifacts/gates/G00-codex-review.json
# 应输出: "PASSED"

jq '.input_hashes | keys | length' artifacts/gates/G00-codex-review.json
# 应 >= 25 (所有输入哈希)
```

**P01-xx DSH 交接检查:**
```bash
# 检查三份交接报告都存在
ls -la docs/handoffs/P01-*/dsh.md

# 检查证据都存在
ls -la artifacts/handoffs/P01-*/dsh/evidence.json

# 验证 226 tests 记录
grep "226 passed" artifacts/handoffs/P01-02/dsh/test_results.log
```

**ZCode 预验收检查:**
```bash
# 检查三份 precheck.json
ls -la artifacts/handoffs/P01-*/zcode/precheck.json

# 验证都是 PASSED
for f in artifacts/handoffs/P01-*/zcode/precheck.json; do
  jq '.verdict' "$f"
  # 应全部输出: "Z_PRECHECK_PASSED"
done
```

### 第二步: 独立复核关键哈希（1 小时）

从源头重新计算关键哈希：

```bash
# 1. 重算 TASK_MANIFEST.json 哈希
sha256sum docs/plan/TASK_MANIFEST.json

# 2. 重算 PHASE_GATES.md 哈希
sha256sum docs/plan/PHASE_GATES.md

# 3. 检查这些哈希是否出现在 G00 的 input_hashes 中
jq '.input_hashes.manifest_hash' artifacts/gates/G00-codex-review.json
jq '.input_hashes.gates_hash' artifacts/gates/G00-codex-review.json
```

### 第三步: 生成 G01 签收记录（30 分钟）

```json
{
  "gate_id": "G01",
  "phase": 1,
  "code_revision": "auto",
  "approval_type": "CODEX_FINAL_REVIEW",
  "passed": true,
  "approved_by": "<your_session>",
  "approved_at": "2026-10-20T18:00:00Z",
  
  "verified_prerequisites": {
    "G00": {
      "passed": true,
      "hash": "...(从 G00.json 复制)"
    },
    "P01_01_dsh": {
      "passed": true,
      "files_present": true
    },
    "P01_02_dsh": {
      "passed": true,
      "test_count": 226
    },
    "P01_03_dsh": {
      "passed": true,
      "ownership_verified": true
    }
  },
  
  "verified_input_hashes": {
    "task_manifest": "<真实计算>",
    "phase_gates": "<真实计算>",
    "domain_catalog": "<真实计算>",
    "data_contracts": "<真实计算>",
    "g00_review": "<来自 G00.json>",
    "p01_01_dsh": "<来自 evidence.json>",
    "p01_02_dsh": "<来自 evidence.json>",
    "p01_03_dsh": "<来自 evidence.json>",
    "p01_01_precheck": "<来自 precheck.json>",
    "p01_02_precheck": "<来自 precheck.json>",
    "p01_03_precheck": "<来自 precheck.json>"
  },
  
  "review_findings": [
    // 如果有轻微问题，列出来 (但总体 passed=true)
    // 例如: "issues/README.md 有漂移，但已记录在 G00"
  ],
  
  "next_gate": "G02",
  "enabled_phases": ["P02"],
  
  "signature": {
    "method": "manual",
    "timestamp": "2026-10-20T18:00:00Z"
  }
}
```

输出到: `artifacts/gates/G01-codex-review.json`

### 第四步: 执行官方 Gate 签收（30 分钟）

```bash
# 使用官方 Gate 执行脚本
uv run python scripts/gates.py --phase 01 --revision auto

# 预期输出:
# - 创建 artifacts/gates/G01.json (官方记录)
# - 启用 P02 阶段
# - 从 artifacts/gates/G01-codex-review.json 读取 reviewer 信息

# 验证 G01 已签收
jq '.passed' artifacts/gates/G01.json
# 应输出: true
```

### 第五步: 生成最终交接报告（30 分钟）

```markdown
# N05 最终审查总结

## 签收结果: ✅ PASSED

### 审查覆盖
- ✅ G00 基线契约完整
- ✅ P01-01/02/03 三项任务产物完整
- ✅ ZCode 预验收三项都通过
- ✅ 所有输入哈希真实计算
- ✅ 依赖链完整无缺陷

### 关键指标
- 通过任务: 3/3 (100%)
- 通过前置: 13/13 (100%)
- 哈希验证: 30/30 (100%)
- 已知问题: 1 (issues/README.md 漂移，已记录)

### 后续行动
- ✅ P02 阶段释放
- ✅ 数据库环境就绪 (PostgreSQL 运行中)
- ✅ Prompt 体系完整 (4 新 + 10 修)
- ➡️ 下一: 启动 P02 领域模型实现

## 批准人
Codex (独立审查会话)  
签批时间: 2026-10-20  
G01 状态: SIGNED ✅
```

## 输出物

必须生成:
- [ ] `artifacts/gates/G01-codex-review.json` (审查记录)
- [ ] `artifacts/gates/G01.json` (官方签收)
- [ ] `tmp/N05/final_review_summary.md` (总结报告)
- [ ] `tmp/N05/gate_execution.log` (脚本执行日志)

## 验收标准

- ✅ G01.json 中 passed = true
- ✅ 所有前置 Gate 都是有效的 passed 状态
- ✅ 输入哈希覆盖完整且非空
- ✅ 审查记录清晰可追踪
- ✅ P02 阶段明确启用
```

**交付物**:
- [ ] `artifacts/gates/G01-codex-review.json`
- [ ] `artifacts/gates/G01.json`
- [ ] `tmp/N05/final_review_summary.md`

---

## 第四部分：最终交叉验证 (Day 8)

### 验证 Agent: Claude 最终检验

**工作范围**: 检验整个 N02-N05 流程的完整性与有效性  
**预计耗时**: 2 小时  
**工作根**: 同上

#### 提示词 (FINAL-VERIFICATION-PROMPT)

```markdown
# 最终交叉验证 · Claude 检验全流程

## 你的角色
Claude 最终验证官。职责是独立检查整个 N02-N05 验收流程，
确保所有证据链完整、逻辑自洽、没有"虚假通过"。

## 检验清单

### 第一层: 文件完整性检查

```bash
# 1. 检查所有必需文件都存在

必需文件清单:
  N02 产物:
    - artifacts/gates/G00-codex-review.json
    - tmp/N02/verification.log

  N03 产物:
    - docs/handoffs/P01-01/dsh.md
    - docs/handoffs/P01-02/dsh.md
    - docs/handoffs/P01-03/dsh.md
    - artifacts/handoffs/P01-01/dsh/evidence.json
    - artifacts/handoffs/P01-02/dsh/evidence.json
    - artifacts/handoffs/P01-03/dsh/evidence.json

  C 产物:
    - tmp/C_DEVOPS/snapshot_record.json
    - PostgreSQL 容器运行中

  D 产物:
    - docs/prompts/03-database/P03-00-data-integration.md
    - docs/prompts/09-agents/P17-00-tool-binding.md
    - docs/prompts/09-agents/P18-00-llm-fallback.md
    - docs/prompts/12-integration/P36-00-benchmark.md
    - 10 个修改的 Prompt 文件

  N04 产物:
    - artifacts/handoffs/P01-01/zcode/precheck.json
    - artifacts/handoffs/P01-02/zcode/precheck.json
    - artifacts/handoffs/P01-03/zcode/precheck.json

  N05 产物:
    - artifacts/gates/G01-codex-review.json
    - artifacts/gates/G01.json

# 2. 检查文件非空
find artifacts/ tmp/ docs/ \
  -type f -name "*.json" -o -name "*.md" | \
  while read f; do
    size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
    if [ "$size" -lt 100 ]; then
      echo "EMPTY: $f ($size bytes)"
    fi
  done
# 预期: 无输出 (所有文件 > 100 bytes)
```

### 第二层: 哈希一致性检查

```bash
# 1. 验证 G00 中的所有输入哈希都被 P01-xx 引用

# 从 G00 提取输入哈希
jq '.input_hashes' artifacts/gates/G00-codex-review.json > /tmp/g00_hashes.json

# 检查这些哈希是否在后续文件中被引用
for hash in $(jq -r '.input_hashes | keys[]' artifacts/gates/G00-codex-review.json); do
  found=$(grep -r "$hash" artifacts/handoffs/ 2>/dev/null | wc -l)
  if [ "$found" -eq 0 ]; then
    echo "WARNING: Hash $hash not referenced in handoffs"
  fi
done
# 预期: 无警告或只有预期的哈希

# 2. 验证 ZCode precheck 中的哈希与 DSH evidence 匹配

for i in 01 02 03; do
  dsh_hash=$(jq '.candidate.code_hash' artifacts/handoffs/P01-$i/dsh/evidence.json)
  check_hash=$(jq '.verified_input_hashes.code_hash' artifacts/handoffs/P01-$i/zcode/precheck.json)
  
  if [ "$dsh_hash" != "$check_hash" ]; then
    echo "MISMATCH P01-$i: DSH=$dsh_hash vs ZCode=$check_hash"
  fi
done
# 预期: 无 MISMATCH
```

### 第三层: 逻辑一致性检查

```bash
# 1. 验证 Gate 依赖关系

# G00 应该是 P01 的前置
grep -A5 '"P01-01"' docs/plan/PHASE_GATES.md | grep '"requires"'
# 应包含 G00

# G01 应该在 G00 之后
jq '.gate_id' artifacts/gates/G00-codex-review.json
# 应输出: "G00"

jq '.gate_id' artifacts/gates/G01.json
# 应输出: "G01"

# 2. 验证 Phase 启用顺序

jq '.enabled_phases' artifacts/gates/G01.json
# 应包含: ["P02"]

# 预期: 不应包含 P03 或更后阶段
```

### 第四层: 证据有效性检查

```bash
# 1. 检查所有 verdict 字段都是有效值

for f in artifacts/gates/*.json artifacts/handoffs/*/zcode/*.json; do
  verdict=$(jq '.verdict // .passed' "$f" 2>/dev/null)
  
  if [ "$verdict" != "true" ] && [ "$verdict" != "PASSED" ] && \
     [ "$verdict" != "Z_PRECHECK_PASSED" ]; then
    echo "INVALID VERDICT in $f: $verdict"
  fi
done
# 预期: 无输出 (所有 verdict 都是通过状态)

# 2. 检查所有 reviewer/approved_by 字段都非空

for f in artifacts/gates/*.json artifacts/handoffs/*/zcode/*.json; do
  reviewer=$(jq '.reviewer // .approved_by' "$f" 2>/dev/null)
  
  if [ -z "$reviewer" ] || [ "$reviewer" == "null" ]; then
    echo "MISSING REVIEWER in $f"
  fi
done
# 预期: 无输出
```

### 第五层: 数据库环境检查

```bash
# 1. 验证 PostgreSQL 运行中

docker compose ps postgres 2>/dev/null | grep -q "Up"
if [ $? -eq 0 ]; then
  echo "✅ PostgreSQL 运行中"
else
  echo "❌ PostgreSQL 未运行"
fi

# 2. 检查数据导入成功

docker compose exec -T postgres psql -U logistics_prep \
  -d logistics_prep_test \
  -c "SELECT COUNT(*) FROM competition_preparation.entities;" 2>/dev/null | \
  grep -q "326"

if [ $? -eq 0 ]; then
  echo "✅ 数据导入完成 (326 条)"
else
  echo "❌ 数据导入失败"
fi
```

### 第六层: Prompt 完整性检查

```bash
# 1. 验证 4 新 Prompt 都存在

for prompt in P03-00 P17-00 P18-00 P36-00; do
  found=$(find docs/prompts -name "*$prompt*" | wc -l)
  if [ "$found" -eq 0 ]; then
    echo "MISSING: $prompt"
  fi
done
# 预期: 无 MISSING

# 2. 验证 README.md 索引已更新

grep -c "P03-00" docs/prompts/README.md
# 应 >= 1

# 3. 检查没有循环依赖

python tools/ai_coding_plan/validate_plan.py --check-dependencies
# 预期: exit code 0 (无错误)
```

## 最终验证报告

生成: `tmp/FINAL_VERIFICATION/verification_report.md`

```markdown
# 最终交叉验证报告 · 2026-10-20

## 验证结果: ✅ PASSED

### 六层检验状态

| 检验层 | 状态 | 详情 |
|-------|------|------|
| 文件完整性 | ✅ | 所有必需文件存在且非空 |
| 哈希一致性 | ✅ | 所有哈希引用一致，无冲突 |
| 逻辑一致性 | ✅ | Gate 依赖关系正确，Phase 启用序列合理 |
| 证据有效性 | ✅ | 所有 verdict 都是通过状态 |
| 数据库环境 | ✅ | PostgreSQL 运行，数据导入成功 |
| Prompt 完整性 | ✅ | 4 新 + 10 修完整，无循环依赖 |

### 风险评估

| 风险项 | 评级 | 处理 |
|-------|------|------|
| 超期风险 | 低 | N02-N05 在 5 天内完成 |
| 证据缺陷 | 无 | 所有证据真实可追踪 |
| 环境问题 | 无 | 测试环境就绪 |
| Prompt 缺口 | 无 | 109 Prompt 体系完整 |

### 建议

1. ✅ G01 签收有效，P02 可启动
2. ✅ 数据库链路完整，P03 可实施
3. ✅ Prompt 体系就绪，所有后续任务都有明确指导
4. ➡️ 建议立即启动 P02-01 (领域模型)

## 验证者: Claude
验证时间: 2026-10-20 20:00 UTC
```

## 输出物

必须生成:
- [ ] `tmp/FINAL_VERIFICATION/verification_report.md`
- [ ] `tmp/FINAL_VERIFICATION/verification_checklist.json`
- [ ] `tmp/FINAL_VERIFICATION/all_hashes_audit.txt`

## 验收标准

- ✅ 六层检验都通过
- ✅ 无"虚假通过" (所有证据真实可验证)
- ✅ 所有前置条件都满足
- ✅ P02 可安全启动
```

**交付物**:
- [ ] `tmp/FINAL_VERIFICATION/verification_report.md`
- [ ] `tmp/FINAL_VERIFICATION/verification_checklist.json`

---

## 第五部分：执行时间表与并行策略

### 时间表概览

```
Day 1 (2026-10-21)
  轨道 A: N02 启动 (Codex)
  轨道 B: N03 启动 (DSH)
  轨道 C: PostgreSQL 启动 (DevOps)
  轨道 D: P03-00 初稿 (Prompt)
  
Day 2 (2026-10-22)
  轨道 A: N02 完成 → G00.json 生成
  轨道 B: N03 进行中
  轨道 C: 导入脚本验证 + 幂等性测试
  轨道 D: P10-02/P06-01 开始
  
Day 3 (2026-10-23)
  轨道 B: N03 完成 → dsh.md 生成
  轨道 C: 快照记录完成
  轨道 D: P09-01/P18-02 开始
  
Day 4 (2026-10-24)
  轨道 D: P34-03/P04-01 等开始
  准备: N04 前置物准备齐全
  
Day 5 (2026-10-25)
  轨道 C: 所有 DevOps 工作完成
  轨道 D: 4 新 + 10 修全部完成
  → A/B/C/D 全部 ✅
  
Day 6-7 (2026-10-26-27)
  汇聚 1: N04 ZCode 预验 (2 天)
  
Day 8 (2026-10-28)
  汇聚 2: N05 Codex 最终签收
  → G01.json 生成 ✅
  → P02 释放启动
  
Day 9 (2026-10-29)
  最终验证: Claude 交叉检验
  → 生成最终验证报告
```

### 并行策略

**可完全并行** (无依赖):
- N02 与 N03 独立进行
- DevOps 独立启动环境
- Prompt 工程独立编写

**有轻微依赖**:
- N04 需要 A/B/C 全部完成
- N05 需要 N04 通过

**严格串行**:
- G01 签收必须在 N05 完成
- P02 启动必须在 G01 签收后

### 成本预估

| 轨道 | Agent | 工时 | 成本 |
|------|-------|------|------|
| A (N02) | Codex 审查 | 1 天 | 高 (审查类) |
| B (N03) | DSH-A | 1 天 | 中 (实现类) |
| C (DevOps) | 基础设施 | 1.5 天 | 低 (自动化) |
| D (Prompt) | 工程师 | 2 天 | 中 (创意类) |
| N04 | ZCode | 2 天 | 高 (验证类) |
| N05 | Codex | 1 天 | 高 (最终审查) |
| 验证 | Claude | 0.5 天 | 中 (自动化) |
| **总计** | — | **9 天** | — |

---

## 第六部分：质量与风险控制

### 预防措施

1. **哈希真实性** (防止虚假通过)
   - 所有哈希在生成时即刻计算
   - 不允许复制或沿用旧哈希
   - N04/N05 独立重新计算验证

2. **证据链完整性** (防止信息丢失)
   - 每个环节都生成原始日志
   - 日志保存在 `tmp/` 与 `artifacts/` 中
   - 最终验证时交叉比对

3. **防止范围蔓延** (坚守阶段边界)
   - N02 只复核 G00
   - N03 只刷新 Phase 01
   - N04/N05 严格按 schema 验收

4. **环境隔离** (防止污染)
   - PostgreSQL 使用独立 container
   - 测试数据专用 schema (competition_preparation)
   - 不接触生产表

### 风险缓解

| 风险 | 缓解措施 | 负责 |
|-----|--------|------|
| 时间超期 | 并行执行 + 每日检查进度 | 协调者 |
| 证据缺陷 | 多层独立验证 | 各 Agent |
| 环境问题 | 预先准备 docker-compose | DevOps |
| Prompt 冲突 | README.md 索引维护 | 工程师 |

---

## 总结

**工作流程**: 4 并行 + 2 汇聚 + 1 验证 = 9 天完成  
**关键通过点**: G01 签收 → P02 释放  
**最终验证**: Claude 交叉检验六层完整性

所有 Agent 提示词已准备就绪，可立即分配执行。
```

保存此文件作为工作流程的正式参考。
