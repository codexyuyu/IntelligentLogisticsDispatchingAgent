# 给 DSH：P01-02 返工，修复 G01 测试和证据判定

**本卡历史状态：**四项限定返工已于 2026-10-01 交付 READY_FOR_ZCODE 并停写。无新的限定缺陷卡不得再次执行本卡；当前顺序见 [返工后完整派发](12-project-completion-dispatch.md)。以下保留原修复要求和历史输入，不能当作当前已验收结论。

日期：2026-10-01。这是原任务 `P01-02` 的限定返工补充，不新增 manifest 节点，不签收 Gate。先读根 `AGENTS.md`、`00-common.md`、`04-dsh-development.md`、原任务 `docs/prompts/01-foundation/P01-02-checks-and-gate-runner.md` 和当前检查报告。只完成本任务后停止，交给独立审查者。

适用目录仅为 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`。分发时发现 DSH 当前会话使用 `D:\Agent\Codex\IntelligentLogisticsDispatchingAgent`，其规划/证据不同；目标目录确认前不得发送本任务，也不得把本副本 G01 结论搬到另一目录。

## 任务卡

```text
task_id / round: P01-02 / rework-2026-10-01
owner / primary_implementer: A / DSH
project_root: D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent
prerequisites: 核验 G00；读取 P01-01 当前实现及 ZCode 预验收。
               本任务属于 G01 内返工，G01 failed 不阻止修复本任务。
objective: 让 Gate 的测试、候选标识和证据核验符合已冻结的失败关闭规则。
handoff: docs/handoffs/P01-02/dsh.md
         artifacts/handoffs/P01-02/dsh/（新轮日志与证据）
next_step: 新候选独立预验收；通过后才能进入 G01 最终审查。
stop: 不执行 P01-03 的实现返工、P02 及后续任务，不写任何他人签收文件。
```

输入候选以开始时现场计算的相关文件 SHA-256 清单为准，不照抄全工作区 revision。原 G01 文件 SHA-256 是 `4383ccac45dddcb465410ce4f4e2d0db7828d340e4d61ed49f87249d3f75c4d4`，仅用于识别本次检查的历史输入；它不是当前通过证据。

## 精确可写范围

- `scripts/gates.py`
- `tests/unit/test_p01_02_checks_and_gate_runner.py`
- `tests/integration/test_p01_02_checks_and_gate_runner.py`
- `docs/implementation/P01-02.md`
- `docs/implementation/reports/P01-02.md`
- `docs/handoffs/P01-02/dsh.md`
- `artifacts/handoffs/P01-02/dsh/` 下的新轮日志、证据及取证脚本
- `tmp/dsh-p01-02-rework/` 下的临时探针和缓存

不修改 `tests/conftest.py`、`scripts/check_architecture.py`、依赖清单/锁、所有权、冻结契约、manifest、旧 demo 或 B 的业务模块。没有可验证必要性不得扩展上述集合；发现范围外的新阻断只指出精确修复项和责任方。本轮不安装数据库、不升级工具链、不实现领域/API/worker。

## 已确认问题与修复要求

1. **测试依赖活跃工作区的临时缺口。** `test_repository_phase_one_gate_is_fail_closed` 当前硬编码 `"zcode-precheck:P01-01" in failed_checks`；真实 P01-01 precheck 补齐后，正确 Gate 判定使这个断言失败。把缺少 precheck、缺少 review、输入漂移等场景放入受控临时仓库，分别设置前置与预期；真实工作区探针只验证与当前输入相符的不变量。官方记录的哈希应在调用前保存并在调用后比对，不能在调用后才取 before。测试应在“precheck 缺失”和“合法 precheck 存在”两种状态下验证正确行为，不能通过删除真实审查记录恢复测试。
2. **候选标识自扰动。** `compute_revision()` 纳入 `tmp/`、`.mimosa/`、handoff 日志；`dirty_tree_hash()` 纳入取证脚本。改为相关源文件、配置、契约和测试的确定性文件清单，明确排序、排除规则、缺文件处理及复算方式；实现候选和依赖证据分别记录。业务 Schema 与生成器属于相关输入，不能一并排除。添加负例：写日志/报告/审查文件或临时文件不改变候选；修改相关代码/配置/契约/测试会改变候选。修正生产实现及有意义的临时仓库样例，不能只把 revision 固定为任意字符串绕过检查。
3. **空预验收哈希被接受。** `check_zcode_precheck()` 对 `verified_input_hashes={}` 判为通过，缺少可核验输入。非空、格式正确且覆盖本任务必需输入的哈希清单是必要条件；缺失、空集合、错误 hash、关键输入遗漏、错误 task_id/phase_gate 应拒绝。Codex review 同样不能仅凭非空 reviewer 和 approved 接受空输入集合。与已有真实 P01-01 记录比对字段和输入覆盖，若不够则报告需要该审查者重新验收；不代改其记录。
4. **前置 Gate 只检查 status。** `check_previous_gates()` 会接受只有 `{"status":"passed"}` 的 G00 文件。依照 `GATE_EXECUTION_CONTRACT.md` F2/F3/F4/F6 校验必要字段、命令/日志、输入及依赖哈希，并拒绝缺失、漂移、非零命令和循环依赖。兼容已存在 G00 的 `log_hash` 与正式执行器的 `log_sha256` 字段差异，按具体 schema 明确处理；不要通过忽略日志验证达成兼容。临时仓库正例必须提供完整受控证据，负例逐一破坏必要字段或哈希。

第 3、4 项来自隔离最小探针，证明判定缺口，不表示已在真实项目伪造通过记录。证据：`artifacts/reviews/2026-10-01/codex/snapshot-and-evidence-probes.json`。本轮仍只修复 Phase 01 使用的 Gate 机制；后续阶段附加业务断言的实施范围另由阶段任务指定，不能宣称 G02–G39 已可验收。

## 验证

先执行原任务两条必需命令，再执行新增正反例及受影响 Phase 01 回归：

```powershell
uv run pytest tests/unit/test_p01_02_checks_and_gate_runner.py tests/integration/test_p01_02_checks_and_gate_runner.py -q
uv run python scripts/check_architecture.py
uv run pytest tests/unit tests/integration -q
uv run python scripts/gates.py --phase 01 --revision auto --check-only
```

记录真实 collected/passed/failed/skipped、退出码和日志 SHA-256；新增测试后不要求计数仍为 187。真实工作区尚缺其他角色记录，最后一条命令允许非零，必须明确它是“现状检查未通过”，不算 G01 签收成功。需要写探针时另加 `--out-dir tmp/dsh-p01-02-rework/gate-probe`，不得覆盖官方 Gate。

本次 Codex 首轮因默认 uv 缓存写权限失败；设置可写缓存后复测为 **186 passed / 1 failed**，唯一失败位于上述硬编码断言。遇到相同环境问题，当前 PowerShell 会话可设置 `UV_CACHE_DIR` 为 `tmp/dsh-p01-02-rework/uv-cache`，先核验 `uv lock --check`；离线模式仅在现有缓存满足依赖时使用。权限/网络失败单独记录，不能当作锁漂移，也不能改锁文件解决缓存权限。

## 交付与停止条件

保留旧证据与原始日志，在新轮目录记录文件清单、改动理由、候选哈希、真实命令结果、对应正反例和仍缺的独立记录。实际文件写完后再统计与取 hash。受影响旧 ZCode 记录失效应交给对应审查者重验；既有 P01-01 precheck 不能因文件名仍在就沿用。

本任务通过后状态只可写 `READY_FOR_ZCODE`；未达到条件则写 `FAILED` 或 `BLOCKED` 并给出一个可执行恢复条件。不得写 `Z_PRECHECK_PASSED`、不得生成 `G01-codex-review.json`、不得自动进入 P02。接下来由独立审查者核验新候选，解决缺失交接治理/环境前置，并签收有效 G01 后再下发 P02-01。
