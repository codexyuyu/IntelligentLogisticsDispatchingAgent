# P02-01 完成报告 · 领域 ID、单位与唯一状态枚举

| 项 | 值 |
| --- | --- |
| Task ID | `P02-01`（owner A） |
| 阶段 Gate | `G02`（未签收；本任务不签任何 Gate） |
| 契约版本 | 业务 2.0.0（前 1.0.0）、计划 1.0.3、Gate 证据 schema 1.0.0 |
| 前置 | `G01` 官方记录 sha256 `b7ac0c60de7438dc0cd88cc7f277b6ac2e93b8216ee05efdfb3124089c98dee8`，我已独立复算 40/40 输入新鲜、7/7 命令日志匹配、依赖 G00 `c5e57a6d…` 新鲜 |
| 当前候选 | `code_revision = content-sha256:dadad19614a86a39ddf880c8ae8011e5fff889d1f02d12b7a0cfa28aaaad3cf8`，`dirty_tree_hash = content-sha256:2b8deb75aa6b28d7529b6f00e0fc958d9556792574a6b8de7018ac4aac20d297`，82 个白名单文件 |
| 本角色状态 | `READY_FOR_ZCODE` |

## Files created（精确路径）

| 路径 | 说明 |
| --- | --- |
| `packages/domain/src/logistics_domain/states.py` | 17 个枚举 + `ErrorCode` + `EntityState`/`Transition`/生命周期图 |
| `packages/domain/src/logistics_domain/primitives.py` | 标量规则与 8 个不可变值对象 |
| `packages/domain/src/logistics_domain/errors.py` | 领域异常层级与 `parse_enum` |
| `tests/unit/test_p02_01_primitives_and_states.py` | 37 例 |
| `tests/integration/test_p02_01_primitives_and_states.py` | 9 例 |
| `docs/implementation/P02-01.md` | 任务文档 |
| `docs/implementation/reports/P02-01.md` | 本报告 |

## Files modified（精确路径及原因）

| 路径 | 原因 |
| --- | --- |
| `packages/domain/src/logistics_domain/__init__.py` | **唯一白名单外改动**。原任务 §Files 允许「包marker只有确需导出本任务类型时可修改，须先在完成报告列出精确路径」。修复前 `_PENDING_APIS` 仍把 `states` 视为未交付，`from logistics_domain import states` 抛 `NotImplementedError`（`from logistics_domain.states import …` 与 `import logistics_domain.states` 正常），且该失败依赖导入顺序（先导入 `primitives` 时因副作用而"碰巧"可用）。改动：从 `_PENDING_APIS` 移除已交付的 `states`，并在包内加 `from . import errors, primitives, states`；`entities`/`ids`/`units`/`ports` 仍抛 `NotImplementedError`。 |

未修改：manifest、`OWNERSHIP.json`、依赖与锁、契约、Gate、他人交接、`demo/`、其他所有者模块。
`docs/architecture/issues/README.md` **不在白名单**，故登记文本只写入本报告与 DSH 证据（见 Known limitations）。

## Tests added（文件、用例与覆盖边界）

**`tests/unit/test_p02_01_primitives_and_states.py`（37 例）**

- 6 个冻结 Test Case 的正反例：相邻 `[0,10)`/`[10,20)` 不冲突；`delivered -> draft` 抛 `INVALID_TRANSITION`；
  `JobKind=simulation`/`JobOptimizationMode=transport` 序列化固定值；`JobKind("routing")` 拒绝；
  `CalendarInterval(10,10)` 拒绝；日历缺 `epoch_utc` 拒绝。
- 17 个枚举逐成员/逐值对照；`EntityKind` 恰 45 项；`ErrorCode` 18 项与 code→HTTP 表；`EntityState` 恰等于生命周期图并集。
- 生命周期边逐条断言（含 `↔` 双向、`active↔suspended`）。
- 标量规则：bool/float/int64 拒绝、`PositiveInt`/`NonNegativeInt`、UUID 小写、`Sha256` 小写 64、`SafeText` 1..256。
- 值对象：`TimeWindow` 闭窗、`Load` 加减与负值拒绝、`Money` 整数分、`Rational` 最简与 ceil 及溢出、`EntityRef` 可空 revision、`ArtifactRef` 四字段与路径逃逸拒绝、冻结不可变与可哈希。
- 负例一次只改一个字段，并断言具体异常类型与 `code`。

**`tests/integration/test_p02_01_primitives_and_states.py`（9 例）**

- 解析真实冻结产物并逐成员比对：`contracts/changes/N01-R01-contract-decisions.json`（states.py 条目）、
  `docs/architecture/TYPE_DEFINITION_OWNERSHIP.md`（所有权行）、`docs/architecture/DOMAIN_CATALOG.md`
  （27 行生命周期列、状态词全覆盖）、`docs/architecture/DATA_CONTRACTS.md`（标量规则原文）。
- 域名层源码扫描无框架/求解器导入；在**隔离解释器**（`-I`，cwd 为临时目录）中导入三个模块并断言无第三方模块被拉入。

## Commands executed（实际命令、工作目录、环境）

工作目录均为 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`；`UV_CACHE_DIR=tmp/P02-01/uv-cache`（仅本任务，未改全局配置）；CPython 3.12.10 / uv 虚拟环境。

```powershell
uv run pytest tests/unit/test_p02_01_primitives_and_states.py tests/integration/test_p02_01_primitives_and_states.py -q
uv run python scripts/check_architecture.py
uv run pytest tests/unit tests/integration -q     # 补充：确认 P01 套件未被我改动破坏
```

## Test results（exit code、passed/failed/skipped、原始日志）

| 命令 | 退出码 | 结果 | 原始日志 |
| --- | --- | --- | --- |
| 必需命令 1 | 0 | **46 passed / 0 failed / 0 skipped** | `artifacts/handoffs/P02-01/dsh/logs/p02-01-2026-10-04/required-cmd1-pytest.log` |
| 必需命令 2 | 0 | `scanned 10 module(s) across 7 layer(s); violations=0` | `…/required-cmd2-check-architecture.log` |
| 全量回归（补充） | 0 | **272 passed / 0 failed**（P01 的 226 + P02-01 的 46） | `…/full-regression.log` |

单独收集也通过：unit 文件 37 passed、integration 文件 9 passed（修复包 marker 前 integration 单文件收集会因上述导入缺陷直接 error）。

## Known limitations（支持/不支持及用户可见行为）

1. 只交付 P02-01 名下的类型；**不实现**实体、不导出 JSON Schema/OpenAPI/TS（P02-04/P02-05），因此 G02 的
   「32 实体可表达、Schema 确定导出」尚未成立。`logistics_domain.entities` 等仍未交付并显式失败。
2. **`ConstraintCode`/`ViolationCode` 无冻结成员表**：本任务只交付类型名（`NewType(..., str)`），
   不臆造成员；覆盖注册表由 P10-01 承担。
3. **`SafeArtifactPath` 无形状定义**：按最小安全读法实现（相对 POSIX、无盘符/UNC、无空段/`.`/`..`）。
4. `Money` 不限制符号（同值对象也表达差额）；需要非负的调用方自行断言。
5. `transition(state, event)` 按**目录生命周期并集**判定（冻结签名没有实体参数）；按实体精确判定需用
   `LIFECYCLE_TRANSITIONS[owner]`。`delivered` 的唯一后继是 cargo 的 `returned`，故 `delivered -> draft` 被拒不是巧合。
6. 上述 2、3（以及 `__init__.py` 白名单外改动）**尚未登记到 `docs/architecture/issues/README.md`**：
   该文件不在本任务白名单，DSH 未写入；登记用逐字文本见
   `artifacts/handoffs/P02-01/dsh/evidence.json` 的 `issues_to_register`，请治理会话按格式登记。
7. 无数据库、OR-Tools、SimPy、模型或浏览器验收（不属本任务）。

## Remaining risks（有证据的风险、影响、下一责任任务）

1. `__init__.py` 的公共表面改动会让 `P01-01` 既有证据绑定的候选失效（候选已从 `23930f7a…` 变为 `dadad196…`）；
   我已实跑全量回归确认 P01 的 60 例与 P02-01 的 46 例全部通过。→ ZCode N04 需按新候选复算输入哈希。
2. 生命周期图由我按 DOMAIN_CATALOG 状态列转写，个别分支语义（如 cargo `delivered→returned`、route「可 superseded」）
   依赖目录措辞；集成测试只保证不出现目录未记载的状态词，**语义细节仍需独立复核**。→ ZCode/Codex。
3. `EntityState` 是跨实体并集，同一状态词在不同实体含义不同；后续任务若直接用它做实体状态，可能掩盖实体级差异。→ P02-02/P02-03 复核。
4. 契约缺口 2、3 未登记，下游可能在 P10-01 之前自行发明约束码。→ 治理会话。
