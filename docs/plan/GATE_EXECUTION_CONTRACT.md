# Gate 执行与证据契约 · 失败关闭

版本 1.0.0。本文是 P00-03 交付物，冻结 Gate 的判定语义、证据格式、revision 与失效传播规则。它只描述规则，不签收任何 Gate：G00–G39 的真实状态一律以 `artifacts/gates/GNN.json` 及其原始日志为准。

本文与 `docs/plan/PHASE_GATES.md` 是同一契约的两个视角：PHASE_GATES 给出 40 个 Gate 的必需任务与业务断言，本文给出执行器必须做什么、证据必须包含什么、失败如何关闭。

## 1. 失败关闭的判据

Gate 默认失败；只有同时满足以下条件才能写 `status=passed`：

| 编号 | 判据 | 违反时的处理 |
| --- | --- | --- |
| F1 | 本 Gate 依赖的每个 Task 都有实现/文档产物、任务文档与完成报告 | 判失败，不启动下游 |
| F2 | 依赖的每个前序 Gate 证据存在、未失效且 `status=passed` | 判失败，禁止跨阶段 |
| F3 | manifest 中该阶段每个 Task 的命令被**执行器亲自执行**并记录 argv、cwd、exit_code | 判失败；不接受手写成功字段 |
| F4 | 每条命令 exit_code 为 0 | 判失败并保留完整 stdout/stderr |
| F5 | 测试命令真实收集到用例（`passed > 0` 且无关键 `skipped`） | 判失败；零用例视为未验收 |
| F6 | 产物 hash 与证据记录的 hash 一致 | 判失败；hash 不匹配即证据无效 |
| F7 | 本阶段附加业务断言逐条成立（见 PHASE_GATES 第 3 列） | 判失败并记录未满足断言 |
| F8 | 未使用 fake/测试替身冒充真实引擎 | 判失败；fake 只允许出现在负例测试中 |
| F9 | `limitations` 如实记录未执行项 | 判失败；隐瞒未执行项即证据无效 |

任何一条不成立都写 `status=failed`，保留原始日志与失败原因，禁止启动下一阶段。已失败 Gate 的日志不得被覆盖或删除。

## 2. 证据最小字段

`artifacts/gates/GNN.json` 必须包含：

```text
schema_version            证据格式版本，当前 1.0.0
gate_id                   G00..G39
status                    passed | failed
started_at / finished_at  UTC ISO-8601
code_revision             Git HEAD(+dirty 树 hash)；无 Git 时用相关源文件清单 hash
dirty_tree_hash           工作树内容 hash，排除产物日志与报告自身
dependency_evidence_hashes 前序 Gate 证据的 hash
input_artifact_hashes     本次判定所依赖的输入产物 hash
environment_fingerprint   工具版本(uv/python/node/npm/引擎)；禁止包含任何 secret
commands[]                每项 {argv, cwd, exit_code, log_path, log_hash, test_counts}
acceptance_artifacts      本 Gate 附加断言的产物引用
limitations               未执行/未覆盖项，逐条
reviewer                  签收角色
```

同目录必须保存原始日志（stdout/stderr 原文），证据文件只引用它们并记录其 hash，不得转述成功。

## 3. 执行器职责

`scripts/gates.py`（P01-02 交付）必须：

1. 读取 `docs/plan/TASK_MANIFEST.json`，取该阶段全部 Task 的命令与前置 Gate，不读取任何手写状态字段。
2. 用子进程参数数组执行命令（禁止 `shell=True` 拼接），逐条保存 stdout/stderr/exit code。
3. 支持 `--phase NN --revision auto` 与 `--check-only`；`--check-only` 只做 freshness 检查、不执行命令。
4. 命令失败即写 `failed` 并以非零退出码结束进程，保证 CI 与人工调用都不会误判成功。
5. 断言失败关闭的负例：故意让一条命令返回 1，必须得到 `GNN failed` 且执行器进程非零退出。

当尚无 Git 时，`code_revision` 使用与本 Gate 相关源文件清单的 sha256 组合值；该值必须可从仓库内容复算。

## 4. revision 与 freshness

- revision 可以是 Git HEAD + dirty 树 hash，也可以是相关源文件清单 hash；不同阶段允许不同提交，不要求最终 HEAD 等于各阶段旧 HEAD。
- freshness 由相关输入、源文件、公共契约与依赖证据的 hash 决定；计算时排除产物日志、时间戳与报告自身，避免自引用。
- 影响某 Gate 的变更使其自身及全部下游 Gate 证据失效；禁止通过修改日期、重写状态字段或删除日志"恢复"证据。
- 公共契约（`PROJECT_MASTER_PLAN.md`、`TASK_GRAPH.md`、`docs/architecture/*`、`docs/api/API_CONTRACT.md`、三份算法契约、`docs/plan/TEST_FIXTURES.md`、`docs/plan/PHASE_GATES.md`）变更后，必须重新导出 Schema/OpenAPI/TS 并重验受影响 Gate。

## 5. 各 Gate 附加断言

40 个 Gate 的必需 Task 与附加业务断言见 `docs/plan/PHASE_GATES.md` 的 Gate 表，本文不重复、不弱化。摘要要求：

- G00：旧 demo 资产有逐项证据；单位/32 实体/错误/Protocol 冻结；任务 DAG 与需求追踪无缺口。G00 由规划检查器记录，属文档契约证据，不得用本轮静态报告替代业务签收。
- G01：干净安装、六包导入与分层检查通过；依赖锁可复现；Gate 执行器非零命令必失败；旧 demo 未被覆盖。
- G03/G05/G16/G34/G37：真实隔离 PostgreSQL 与崩溃/回滚证据。
- G07/G09/G10/G15：真实 OR-Tools / CP-SAT 与小规模手算或独立 oracle，引擎状态不得互相冒充。
- G12：真实 SimPy 连续运行与快照恢复轨迹比对。
- G18/G23：真实模型契约 smoke 与固定测试替身的功能负例分别留档。
- G35/G36/G39：五演示逐场景证据、参考机基准与发布候选完整性清单。

## 6. 边界情形

| 输入 | 预期 |
| --- | --- |
| 依赖 `P99-01`（不存在的任务） | 检查失败：`missing dependency P99-01`，Gate 不得通过 |
| Gate 证据缺少 `commands[].exit_code` | 不允许 P01 启动；证据无效，按 F3/F4 判失败 |
| 命令 exit=1 | 该 Gate `failed`，执行器进程非零退出 |
| `domain` 导入 `fastapi` | 层边界检查失败（G01 之后由 `scripts/check_architecture.py` 断言） |
| 关键测试被 skip | 视为未验收，按 F5 判失败 |
| 证据 hash 与实际产物不一致 | 证据失效，按 F6 判失败 |
| 40 个 Gate 编号缺失或重复 | 规划检查失败，G00 不能记录 |

## 7. 限制与未验证项

- 本文是规则契约，不是执行结果；本轮没有运行任何应用测试、数据库、求解器、仿真或浏览器验收。
- `scripts/gates.py` 与 `scripts/check_architecture.py` 尚不存在（P01-02 交付）；在它们交付并通过前，G01 及之后的 Gate 无法被判为 passed。
- 尚未有 Git 仓库，`code_revision` 目前只能使用相关源文件清单 hash 方案。
- 规则通过不代表任何业务能力可用。
