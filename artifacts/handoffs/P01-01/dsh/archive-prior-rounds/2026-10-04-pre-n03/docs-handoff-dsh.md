# P01-01 · DSH → ZCode 交接说明

| 项目 | 值 |
| --- | --- |
| Task ID | `P01-01` |
| 交付方 | DSH（初步开发） |
| 交接对象 | ZCode（独立预验收，按 `docs/workflow/02-ZCODE-PRECHECK.md`——该文件当前不存在，见"流程缺口"） |
| 本角色状态 | `READY_FOR_ZCODE` |
| 阶段 Gate | `G01`（未签收；Phase 02 及之后禁止启动） |
| 证据入口 | `artifacts/handoffs/P01-01/dsh/evidence.json`、`docs/implementation/reports/P01-01.md` |

## 1. 交付范围

只交付"目标 Monorepo 与可复现依赖环境"：uv workspace + npm workspace + 六个包与后端应用的 src-layout 骨架 + 真实锁文件 + Playwright 配置 + 两条 Test Case 的真实测试。**没有任何业务能力**。

## 2. 进入本任务时的前置阻断（必须先看清）

按 TASK_GRAPH 与 PHASE_GATES 逐项核验 `G00` 的依赖后，实际状态是：

| 前置项 | 核验结果 |
| --- | --- |
| `P00-01` 交付物（`docs/architecture/BASELINE_INVENTORY.json`/`.md`、`MIGRATION_MAP.md`、任务文档与报告） | 全部缺失 |
| `P00-02` 交付物（`CONTRACT_FREEZE.json`/`.md`、`issues/README.md`、任务文档与报告） | 全部缺失 |
| `P00-03` 交付物（`docs/plan/GATE_EXECUTION_CONTRACT.md`、任务文档与报告） | 全部缺失 |
| `artifacts/gates/G00.json` | 不存在（G00 未记录） |
| 目录 `docs/workflow/`、`docs/handoffs/`、`contracts/changes/` | 不存在 |

规划检查器给出的原始失败证据（在补齐交付物之前）：

```text
python tools/ai_coding_plan/validate_plan.py --self-test --record-g00
exit code 1
errors: ["G00 NOT recorded: Phase00 deliverables/reports missing:
  docs/architecture/BASELINE_INVENTORY.md, docs/architecture/MIGRATION_MAP.md,
  docs/implementation/P00-01.md, docs/implementation/reports/P00-01.md,
  docs/architecture/CONTRACT_FREEZE.json, docs/architecture/CONTRACT_FREEZE.md,
  docs/architecture/issues/README.md, docs/implementation/P00-02.md,
  docs/implementation/reports/P00-02.md, docs/implementation/P00-03.md,
  docs/implementation/reports/P00-03.md"]
```

因为 `P01-01.deps == ["G00"]` 且 G00 无有效证据而无法启动 Phase 01，本任务先按"前置缺失/失败 → 报告具体阻断并修复前置任务，禁止跳 Gate"执行了 Phase 00 的补齐，然后由**冻结的规划检查器**（`--record-g00`，唯一可写 `G00.json` 的入口）记录 G00。当前 `artifacts/gates/G00.json` 为 `status: passed`，`scope: "Phase00 document contract verification only"`，其 `limitations` 明确写着 "No application gate has been executed. G01 must establish the runtime gate runner."

请重点判定：该前置修复是否属于越权、`BASELINE_INVENTORY.json` 的覆盖口径是否可接受、以及是否应把 `tools/ai_coding_plan/` 下新增脚本收编到 `scripts/`。

## 3. 需要独立复核的边界

1. **六包导入必须来自真实安装**：`tests/integration/test_p01_01_workspace_bootstrap.py` 用 `python -I -c` 隔离子进程导入，并断言每个模块解析到本成员 workspace src 目录或 `.venv` 内，同时断言 `importlib.metadata.distribution(...).read_text('direct_url.json')` 存在。请独立复跑，并确认这不是"靠 cwd 生效"的假通过。
2. **锁文件不是手写**：`uv.lock`/`package-lock.json` 由真实安装生成；证据记录其 sha256，测试断言当前值等于证据值。请用 `uv lock --check` 与 `npm ci` 复核。
3. **用例 2 的真实性**：`npm ci` 连续执行两次，前后 `package-lock.json` sha256 必须一致。请确认执行的是 `npm ci` 而不是 `npm install`（后者可能重写锁）。
4. **旧 demo 未被覆盖**：`demo/` 173 个登记文件的路径+内容指纹与 `demo.zip` sha256 都在测试中核对。请另用 `docs/architecture/BASELINE_INVENTORY.json` 独立复算一次。
5. **失败显式化**：七个 `__init__.py` 对未交付名字抛 `NotImplementedError`。请确认没有 TODO 占位核心逻辑、没有返回固定成功、没有吞异常。

## 4. 未测试项（ZCode 不必重复 DSH 已做项，但需覆盖这些）

- Node **22** 上的实际行为（本机只有 24.18.0；`.node-version` 固定 22）。建议在 Node 22 复跑 `npm ci` 与 `npm run test:e2e:list`。
- `scripts/gates.py` 的失败关闭行为（P01-02 交付，本任务不存在）——G01 的"Gate 执行器非零命令必失败"断言目前**无法验证**。
- `scripts/check_architecture.py` 的分层检查（P01-02 交付）——本任务只在单元测试里做了依赖方向静态断言。
- 任何 HTTP/数据库/求解器/仿真/LLM/浏览器验收。
- CI（`.github/workflows/ci.yml`）从未运行（P01-02 交付）。

## 5. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（锁 hash、工具版本、demo 指纹、三条命令） | `artifacts/handoffs/P01-01/dsh/evidence.json` |
| 原始命令日志 | `artifacts/handoffs/P01-01/dsh/logs/{pytest,uv_sync_frozen,npm_ci}.log` |
| 命令汇总（argv、exit_code、log hash、测试计数） | `artifacts/handoffs/P01-01/dsh/logs/validation-summary.json` |
| 任务文档 | `docs/implementation/P01-01.md` |
| 完成报告（含已知限制与剩余风险） | `docs/implementation/reports/P01-01.md` |
| 前置 Gate 证据 | `artifacts/gates/G00.json`、`artifacts/gates/G00-checks.log` |

## 6. 流程缺口（需要项目管理侧补齐）

以下路径由 `P01-01` 任务书引用，但在本检出中均不存在：

- `docs/workflow/README.md`、`docs/workflow/02-ZCODE-PRECHECK.md`（本任务书要求"下一步使用"该文件）
- `docs/workflow/HANDOFF_CONTRACT.md`（本任务书引用为交接证据规范）
- `docs/handoffs/`、`contracts/changes/`
- `docs/architecture/issues/` 在本任务中首次创建（P00-02 白名单包含其 `README.md`）

本任务的交接按任务书本身的要求执行：DSH 写 `docs/handoffs/P01-01/dsh.md` 与 `artifacts/handoffs/P01-01/dsh/evidence.json`；ZCode 的审查证据路径应由 `HANDOFF_CONTRACT` 规定，在该文件补齐前请与项目管理侧确认。
