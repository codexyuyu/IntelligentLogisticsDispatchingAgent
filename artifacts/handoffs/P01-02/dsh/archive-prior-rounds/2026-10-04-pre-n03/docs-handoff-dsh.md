# P01-02 · DSH → ZCode 交接说明

| 项目 | 值 |
| --- | --- |
| Task ID | `P01-02` |
| 交付方 | DSH（初步开发） |
| 交接对象 | ZCode（独立预验收，按 `docs/workflow/02-ZCODE-PRECHECK.md`——该文件仍不存在，见 `ARCH-0004`） |
| 本角色状态 | `READY_FOR_ZCODE` |
| 阶段 Gate | `G01`（**未签收**：`artifacts/gates/G01.json` = `failed`） |
| 证据入口 | `artifacts/handoffs/P01-02/dsh/evidence.json`、`docs/implementation/reports/P01-02.md` |

## 1. 开工前的前置核验结果

| 前置 | 核验结论 |
| --- | --- |
| `G00` | `artifacts/gates/G00.json` `status: passed`（规划检查器记录，`input_artifact_hashes` 全部新鲜）→ 有效 |
| `P01-01` | 交付物齐备、真实测试 56 passed、`demo/` 指纹未漂移 → **有效** |
| `P01-01` 的 `Z_PRECHECK_PASSED` | **不存在**。证据文件仍为 `READY_FOR_ZCODE`；但 `artifacts/handoffs/P01-01/zcode/` 下有 ZCode 真实独立运行的三份日志（`pytest.log` 56 passed、`uv-sync-frozen.log`、`npm-ci.log`，时间晚于 DSH 的记录）。经与用户确认，按"同阶段可用预验收结果推进依赖任务"开工，并在本条如实披露标记缺失。 |

## 2. 交付物与接口

- `python scripts/gates.py --phase NN --revision REV -> artifacts/gates/GNN.json`；附加 `--check-only`（只查新鲜度、不签收）、`--skip-commands`（只验记录框架、必失败）、`--assertion <id>`、`--out-dir PATH`（写入别处并标记 `official_gate_record: false`，**永不覆盖官方记录**）、`--root PATH`。
- `python scripts/check_architecture.py [--root PATH] [--json] [--verbose]`：7 层、13 类规则，退出码 0/1/2。
- `tests/conftest.py`、`.github/workflows/ci.yml`、`apps/frontend/vitest.config.ts`、`apps/frontend/src/test/setup.ts`。

## 3. 需要独立复核的边界

1. **G01 五个断言是真跑而非声明**：逐条看 `artifacts/gates/G01-logs/` 下的原始日志；`runner-fails-closed-probe.log` 应含 `exit_code: 1`。
2. **四类审查记录规则**：`scripts/gates.py` 在 Codex review 缺失、revision 不匹配、输入哈希漂移、ZCode 记录缺失/未通过 时一律写 `failed`。请用你自己的记录格式试探一次，确认是"拒绝"而不是"放行"。
3. **`--check-only` 无副作用**：运行前后 `G01.json` 的 hash/mtime 必须一致，且不得新建日志目录。
4. **层检查能抓住反向依赖**：向 `packages/domain` 注入 `import fastapi` 应得到 `ARCH-PURITY` 且退出码 1（本任务已验证并还原；请独立复现）。
5. **失败不产生伪成功**：`--phase 00` 与非法 phase 应退出 2；`--skip-commands` 的结果必须是 `failed`。

## 4. 未执行/未覆盖（请重点覆盖）

- G01 签收：需 P01-03 交付 + 你的预验收记录 + Codex review；当前 `failed_checks` 已列明。
- 真实 CI（GitHub Actions）从未运行；只在本地做了结构断言。
- Node 22 下的前端 job；真实 PostgreSQL（`TEST_DATABASE_URL` 缺失时 fixture 故意 `pytest.fail`）。
- 任何业务验收（数据库/求解器/仿真/LLM/浏览器）。

## 5. 证据索引

| 证据 | 路径 |
| --- | --- |
| 机器证据（交付物 hash、测试计数、断言结果、Gate 状态） | `artifacts/handoffs/P01-02/dsh/evidence.json` |
| 两条强制命令原始日志 | `artifacts/handoffs/P01-02/dsh/logs/{pytest,check_architecture}.log` |
| G01 真实运行日志 | `artifacts/handoffs/P01-02/dsh/logs/gate-g01.log`、`artifacts/gates/G01-logs/*.log` |
| Gate 证据记录 | `artifacts/gates/G01.json`（`failed`，含 `failed_checks` 与 `runs[]`） |
| 任务文档 / 完成报告 | `docs/implementation/P01-02.md`、`docs/implementation/reports/P01-02.md` |
| 本任务登记的架构问题 | `docs/architecture/issues/README.md` 的 `ARCH-0004`、`ARCH-0005` |

## 6. 需要项目侧决策的事项

- `ARCH-0004`：交接契约文档（`docs/workflow/*`）缺失，审查记录的路径/字段由本任务临时约定；请确认或改为契约。
- `ARCH-0005`：任务书 4 条 Test Case 与冻结清单 2 条不一致；本任务实现 4 条且未改机器清单，请决定是否回填规划源。
- `tools/ai_coding_plan/` 下两个取证脚本（`p01_01_evidence_generate.py`、`p01_02_evidence_generate.py`）在任务白名单外，请判定归属。

---

# 交接 · 返工轮 `P01-02 / rework-2026-10-01`

首轮交接内容全部保留在上方。本节是**当前候选**的交接；上方的"待写入记录"结论已被本轮取代。

| 项 | 值 |
| --- | --- |
| Task ID / round | `P01-02` / `rework-2026-10-01` |
| 交付方 | DSH（唯一主写者） |
| 本角色状态 | **`READY_FOR_ZCODE`** |
| 阶段 Gate | `G01`（**未签收**：官方 `artifacts/gates/G01.json` = `failed`，本轮未改动，sha256 仍 `4383ccac45dddcb465410ce4f4e2d0db7828d340e4d61ed49f87249d3f75c4d4`） |
| 证据入口 | `artifacts/handoffs/P01-02/dsh/evidence.json`、`docs/implementation/reports/P01-02.md`（返工报告节）、`artifacts/handoffs/P01-02/dsh/rework-2026-10-01/` |
| 可写范围 | 严格限于任务卡列出的 8 项；未改 `tests/conftest.py`、`scripts/check_architecture.py`、依赖/锁、所有权、冻结契约、manifest、`demo/`、B 的业务模块 |

**输入候选（开工时现场实测，不照抄全工作区 revision）**：改动前的 `scripts/gates.py` = `67351df627a747f9cb1d5ea5c8ddcdc01093a10e161f198cc9c35a92ecf49873`、单元测试 = `63e70c5cc056e101839017b20028d77fc9a03f9420dee023b258734814f2a050`、集成测试 = `7bb931157eee2caaea5eca625e2b30e37ed18cbc79b1bc4dfdfe23dee917dea9`（见 `rework-2026-10-01/pre-change-hashes.txt`）；官方 `artifacts/gates/G01.json` = `4383ccac45dddcb465410ce4f4e2d0db7828d340e4d61ed49f87249d3f75c4d4`（其记录 revision `content-sha256:ab054daf…`）；首轮 `evidence.json` 的候选标签为 `content-sha256:979c10b4ea7b…`（逐字节副本见 `rework-2026-10-01/previous-round-evidence.json`）。任务卡给出的 G01 历史哈希 `4383ccac…` 与本轮实测一致，仅用于识别历史输入，不作为通过证据。

**输出候选（交付时实测）**：`code_revision` / `dirty_tree_hash` 与全部文件、日志哈希见 `artifacts/handoffs/P01-02/dsh/evidence.json` 的 `candidate`、`artifacts`、`command_logs`。

## 1. 本轮修了什么（四项，逐条对应任务卡）

1. **测试不再依赖活跃工作区的临时缺口**：`test_repository_phase_one_gate_is_fail_closed` 不再硬编码"某个记录必须缺失"，改为断言与当前输入相符的不变量，并在测试内部**独立重算** precheck 与 G00 的新鲜度后与执行器判定交叉比对；官方 `G01.json` 的哈希**在调用前**保存、调用后比对。缺 precheck、缺 review、输入漂移等场景全部移入受控临时仓库。未删除任何真实审查记录。
2. **候选标识自扰动**：`compute_revision()` 改为白名单相关文件清单（实现/配置/契约/测试 + 业务 Schema 与生成器 + 执行器消费的规划输入），`dirty_tree_hash()` 用同一清单的 `path\0size\0sha256` 公式单独记录；写入 `tmp/`、`.mimosa/`、handoff 日志、报告、审查文件、取证脚本**均不改变**候选，改动相关文件一定改变候选。公式与排除规则见 `docs/implementation/P01-02.md` §7.1。
3. **空预验收哈希不再被接受**：`verified_input_hashes` 必须非空、格式正确、逐项与磁盘一致，并覆盖 `required_precheck_inputs()`（manifest、PHASE_GATES、任务 prompt、本任务 DSH 证据）；`task_id`/`phase_gate`/`reviewer`/`status` 必须匹配。Codex review 同样拒绝空输入集合。
4. **前序 Gate 完整校验**：按 F2/F3/F4/F6 校验必需字段、逐条命令的 argv/cwd/整数 exit_code、原始日志存在/非空/哈希一致、`input_artifact_hashes` 非空且未漂移、`dependency_evidence_hashes` 只指向更早 Gate 且与磁盘一致，并拒绝自引用、前向引用与依赖环。`log_hash`（规划检查器）与 `log_sha256`（本执行器）按具体 schema 兼容，**两者皆缺即拒绝**。

## 2. 验证结果（真实计数、退出码、日志）

| 命令 | 退出码 | 结果 | 日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p01_02_checks_and_gate_runner.py tests/integration/test_p01_02_checks_and_gate_runner.py -q` | 0 | 96 passed | `rework-2026-10-01/cmd1-p01-02-suites.log` |
| `uv run python scripts/check_architecture.py` | 0 | 7 modules / 7 layers / violations=0 | `cmd2-check-architecture.log` |
| `uv run pytest tests/unit tests/integration -q` | 1 | 224 passed / 2 failed（均为 `AGENTS.md` 无归属规则的既存失败） | `cmd3-full-suites.log` |
| `uv run python scripts/gates.py --phase 01 --revision auto --check-only` | 1 | **现状检查未通过**，非 G01 签收成功 | `cmd4-gate-check-only.log` |
| `uv run python artifacts/handoffs/P01-02/dsh/rework-2026-10-01/negative-probes.py` | 0 | 10/10 期望匹配 | `negative-probes.log` |
| `uv lock --check`（`UV_CACHE_DIR=tmp/dsh-p01-02-rework/uv-cache`） | 0 | Resolved 40 packages；未改锁 | `env-lock-check.log` |

改动前复现：`1 failed, 56 passed`（失败点 `tests/integration/...:555`），见 `baseline-p01-02-suites.log`。

## 3. 请独立复核的边界

1. **候选 revision 的可复算性与不变性**：按 §7.1 的公式自行重算 `code_revision`；再向 `tmp/`、`.mimosa/`、`artifacts/handoffs/P01-02/dsh/logs/`、`docs/implementation/reports/` 各写一个文件，确认两个哈希不变；随后改动 `scripts/gates.py` 的一个字节（或在副本上）确认两者都变。
2. **失败关闭四类判定**：分别构造空 `verified_input_hashes`、仅 `{"status":"passed"}` 的 G00、G00 输入漂移、G00 命令 exit=1 / 日志缺失，确认全部被拒且**不写 passed**。请用你自己的记录格式与独立实现交叉核对，不要复用本执行器的函数。
3. **范围外阻断（最重要）**：官方 `G00.json` 的冻结输入 `docs/architecture/issues/README.md` 已在 2026-09-15 漂移。请独立确认该事实与"F2/F6 ⇒ G00 失效 ⇒ G01 不得签收"的推论，并决定由谁在当前候选上重录 G00；DSH 未改该文件，也未改 `tools/ai_coding_plan/`。
4. **`AGENTS.md` 所有权缺口**：`scripts/check_ownership.py` 报告 `default_owner_fallbacks == ['AGENTS.md']`；这是 2026-10-01 提示词轮新增文件的归属缺口，与本次返工无因果关系（本轮改动文件不在 fallback 列表内）。
5. **官方记录未被触碰**：`artifacts/gates/G01.json` 的 sha256 与 `G01-logs/` 内容在本轮全部命令前后保持一致；`--check-only` 不写任何文件。

## 4. 失效与仍然缺失

- 失效：`artifacts/handoffs/P01-01/zcode/precheck.json`（绑定了旧 `scripts/gates.py` 哈希）；官方 `G01.json`（其记录输入含 `scripts/gates.py` 与两份 P01-02 文档）；`docs/architecture/issues/README.md` 引起的 G00 失效。**旧记录一律保留原字节**，由对应审查者在新候选上重验。
- 仍缺：`artifacts/handoffs/P01-02/zcode/precheck.json`、`artifacts/handoffs/P01-03/zcode/precheck.json`、`artifacts/gates/G01-codex-review.json`；这三份按角色分离**只能由对应审查者写入**，DSH 未写、未冒签。

## 5. 停止条件

本轮在交付上述文件后停止：不执行 P01-03 实现返工，不进 P02，不签任何 Gate，不生成 `Z_PRECHECK_PASSED` 或 `G01-codex-review.json`。等待独立预验收。
