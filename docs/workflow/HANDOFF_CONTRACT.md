# 交接记录契约

版本1.0.0，2026-10-03。路径均相对正式工作根，sha256为实际文件字节的64位小写十六进制。格式依据[scripts/gates.py](../../scripts/gates.py)的`check_phase_handoffs`、`check_zcode_precheck`、`recorded_input_problems`、`check_codex_review`和`previous_gate_record_problems`；判定不得弱于[冻结规则F1–F9](../plan/GATE_EXECUTION_CONTRACT.md)。

## 固定入口与角色

| 产物 | 路径 | 生成者 |
| --- | --- | --- |
| 实现交接 | `docs/handoffs/<task>/dsh.md` | 对应DSH主写者 |
| 实现机器证据 | `artifacts/handoffs/<task>/dsh/evidence.json` | 对应DSH主写者 |
| 任务说明/完成报告 | manifest的`task_doc`、`report` | 对应主写者 |
| 预验收记录 | `artifacts/handoffs/<task>/zcode/precheck.json` | 独立ZCode |
| 预验收原始日志 | `artifacts/handoffs/<task>/zcode/logs/<round>/...` | 独立ZCode |
| 阶段review | `artifacts/gates/GNN-codex-review.json` | 独立Codex |
| 阶段证据/原始日志 | `artifacts/gates/GNN.json`、`GNN-logs/...`；G00为规划检查器格式 | 独立签收者实际调用工具 |

执行器目前只认`dsh/evidence.json`实现通道，不支持通过另一个工具名自动替代。治理Codex写自己的N01交接，不冒写DSH。未来更换正式主实现通道须单独迁移读取规则。实现者可交READY_FOR_ZCODE；Z_PRECHECK_PASSED只由ZCode写precheck，DSH不得改自己的身份冒签。执行器兼容DSH证据中的旧Z_PRECHECK_PASSED值，仅属历史读取兼容。

上述每Task预验收和阶段review流程适用于G01–G39。G00按[规划检查器](../../tools/ai_coding_plan/validate_plan.py)的引导路径与N02任务执行：读取P00交付/报告、冻结记录和基线，身份来自CONTRACT_FREEZE，不读取P00 precheck或G00-codex-review。不要求新造这两类记录，也不能以常规runner替代G00冻结复核。

## 字段与实际检查

| 记录 | 执行器当前直接检查 | 冻结规则/独立验收还要求 |
| --- | --- | --- |
| DSH evidence | 文件可读JSON，`status`为READY_FOR_ZCODE或历史Z_PRECHECK_PASSED；任务说明与报告存在 | task_id、phase_gate、role、owner/逐路径分工、root、候选revision/dirty hash、产物路径/hash、真实commands/exit_code/counts、原始日志hash、limitations、下一执行者。执行器未逐字段检查，ZCode必须核验 |
| ZCode precheck | `task_id`与任务匹配，`phase_gate`匹配，`status=Z_PRECHECK_PASSED`，非空`reviewer`；`verified_input_hashes`非空、相对路径、合法digest、逐项存在且hash一致，并覆盖下表四类输入 | schema_version、root、真实审查时间/身份、code_revision/dirty hash、commands、test_counts、原始日志及hash、findings/limitations、产物完整性和独立复跑。当前执行器不比较precheck的code_revision、不自动校验其commands/logs；不能据此省略 |
| Codex review | `gate_id`匹配，`status`为approved或passed，非空reviewer/code_revision；正常执行时revision匹配；`verified_input_hashes`非空且逐项新鲜 | 覆盖本阶段所有Task、全部precheck、相关候选文件、契约、前序Gate、日志、真实复现和附加业务断言。当前执行器没有Codex必需输入白名单，不能用一个无关hash替代这些输入 |

ZCode最小必需输入由`required_precheck_inputs(task)`精确产生：

| 输入键 | 规则 |
| --- | --- |
| `docs/plan/TASK_MANIFEST.json` | 所有任务共用 |
| `docs/plan/PHASE_GATES.md` | 所有任务共用 |
| 当前任务manifest的`prompt` | 存在非空prompt时必需；当前109项均有 |
| `artifacts/handoffs/<task>/dsh/evidence.json` | 当前任务实现证据 |

审查还应把实际核验的源码/配置/契约/产物/原始日志、workflow规范、GATE_EXECUTION_CONTRACT及前序Gate加入`verified_input_hashes`。键使用仓库内POSIX相对路径，不含绝对路径、`..`越界或自引用输出；不要把未生成的本Gate JSON加入review。空对象、缺必需输入、非法digest、文件缺失或漂移均不得通过。

## 最小结构说明（模板，不是通过记录）

```text
ZCode:
  schema_version: 1.0.0
  task_id: Pxx-yy
  phase_gate: Gxx
  status: Z_PRECHECK_PASSED | FAILED | BLOCKED
  reviewer: 本次真实独立审查者
  code_revision: 本次实际复算值
  verified_input_hashes: {相对路径: 实测sha256, ...}  # 四类必需输入及实际核验输入
  commands: [{argv, cwd, exit_code, test_counts, log_path, log_sha256}, ...]
  limitations / findings: 实际未覆盖项与缺陷
Codex:
  schema_version: 1.0.0
  gate_id: Gxx
  status: approved | passed | failed | blocked
  reviewer / code_revision / verified_input_hashes / commands / limitations: 同上
```

所有通过状态只能在相应验证真实完成后生成；模板不能复制为正式记录。失败状态会被执行器拒绝，不以成功字符串包装BLOCKED/NOT_RUN。字段名大小写按上述实际读取规则，不用人类交接中的表格字段代替JSON。

## Gate记录与日志

完整字段以冻结契约§2为准。当前runner为1.0.0，命令日志字段是`log_sha256`；规划G00使用`log_hash`，前序Gate检查按具体producer兼容两种字段，缺两者均拒绝。G00规划格式用`scope/checker_counts`标识，不含runner的started_at/dirty_tree_hash/acceptance_artifacts；这是已有格式兼容，不授权手写一个字段不全的“passed”。

前序记录必须有非空commands；argv非空字符串数组、cwd非空、exit_code整数且为0，原始日志存在、非空、hash匹配；pytest结果须有真实正数passed且无关键skip；这是冻结F5要求，当前前序记录检查未重验test_counts，独立审查须核验。`input_artifact_hashes`非空并新鲜；`dependency_evidence_hashes`只引用更早Gate、hash新鲜、无前向/自引用/环。schema要求的身份、环境、限制字段完整。不得仅凭status或编号判断有效。

runner的`runs[]`只保留有限旧摘要，不能代替旧JSON/日志逐字节归档；当前`run_command`会重用日志名。因此每次正式重验前先由签收者归档旧JSON、review、日志及hash，禁止覆盖失败原始证据后只保留摘要。开发复现使用每轮独立tmp目录。

## 候选冻结与生成顺序

当前`GateRunner.relevant_files()`的白名单和排除常量是候选文件集的事实来源。UTF-8、仓库相对POSIX路径排序，最后一行无额外换行：

```text
code_revision = content-sha256: + sha256("\n".join(path + "\0" + sha256(file_bytes)))
dirty_tree_hash = content-sha256: + sha256("\n".join(path + "\0" + size + "\0" + sha256(file_bytes)))
```

源码/配置/业务Schema/冻结规划输入纳入；workflow/prompts/日志/报告/审查记录/tmp/缓存排除。输入证据分别哈希，不混入候选；必要的被排除文档改动仍使绑定它们的审查失效。冻结后任何相关文件改动产生新候选，应停止旧审查并按影响重验。

先治理与生成源码/Schema，后实现测试，后候选清单，再DSH报告/日志/交接/evidence，后ZCode日志/precheck，再Codex日志/review，最后正式Gate。输出不能引用自身hash。候选变化后不得只重算旧记录hash并沿用旧通过、旧身份或日期。

## 正反例与执行边界

| 场景 | 必须观察的结果 |
| --- | --- |
| 沙箱中必需输入与额外源码/log hash正确，task/gate/reviewer/status匹配 | precheck读取检查通过；仍须独立检查真实测试及完整Gate条件 |
| `verified_input_hashes={}`或只绑定某无关文件 | precheck拒绝；Codex空集合拒绝，无关输入即使读取检查通过也不满足独立审查要求 |
| 修改一个输入字节，保持旧digest | 输入漂移，拒绝；回对应责任方重新审查 |
| 缺review、revision错误、命令exit=1、缺原始日志、G00仅含status | 阶段失败，非零退出，不得进下阶段 |
| 只运行`--check-only`且无记录，退出0 | 没有签收；官方Gate存在性必须另查 |
| `--skip-commands`或tmp的`--out-dir` | 不能构成官方签收；skip必失败 |

以上例子应在受控副本运行，不删除正式记录或向正式领域文件注入负例。当前只注册G01附加断言；F7/F8/F9的后续覆盖不能由空注册或通用limitations代替。下一阶段之前另做明确范围的执行器治理任务；本N01未修改执行器。
