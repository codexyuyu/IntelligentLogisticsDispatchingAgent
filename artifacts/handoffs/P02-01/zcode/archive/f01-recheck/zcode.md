# P02-01 ZCode 独立预验收（2026-10-05）

结论：**FAILED（未通过预验收，未写 Z_PRECHECK_PASSED）。** 一个 major 缺陷：交付的 Reservation 生命周期与冻结 DOMAIN_CATALOG 不一致（目录命名的 `released` 状态词在交付词汇表中完全不存在，边集合也不符）。其余全部核验通过。未修改任何实现，未签 G02，P02-02 未启动。

机器记录：[precheck.json](../../../artifacts/handoffs/P02-01/zcode/precheck.json)（sha256 `e517feec33e50cc56f4627bc1c74ccb698b8fb288090aeee40f1ed32d0e32394`，status=`FAILED`，41 项输入），原始日志在 `artifacts/handoffs/P02-01/zcode/logs/2026-10-05/`。

## 验收身份与绑定

- 审查者：ZCode P02-01 独立业务预验收会话（ZCode CLI，GLM-5.3-Flash，未参与实现）；实际工作根 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，无 Git。
- 当前候选（本轮独立重算，与 R01 附件/N05-R01 一致）：`content-sha256:dadad19614a86a39ddf880c8ae8011e5fff889d1f02d12b7a0cfa28aaaad3cf8`（82 项）；dirty-tree `content-sha256:2b8deb75…`。
- **前置现行有效**（本轮独立复核，非照抄附件）：G00 `c5e57a6d…` 25 项输入 0 漂移；G01 `a7eed6ae…`(passed, revision=dadad196) 经现行 runner `previous_gate_record_problems` 实测 **0 问题**，依赖 G00 新鲜；review `c41888a…`(approved, N05-R01, 262 项输入)。R01 附件 json `b542026f…`/seal `5c7b3b71…` 与派发一致；原 P02-01 evidence `36f08ff6…`/seal `cd6731c1…`/dsh.md `b3de54eb…` 原字节未动（与附件声明一致）。

## 必需命令（本轮实测）

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `uv run pytest tests/unit/test_p02_01_primitives_and_states.py tests/integration/test_p02_01_primitives_and_states.py -q` | 0 | **46 passed**（collect-only 亦 46，无空洞/无 skip） |
| `uv run python scripts/check_architecture.py` | 0 | 10 模块/7 层，violations=0 |

## 缺陷 ZC-P02-01-F01（major）

- **位置**：`packages/domain/src/logistics_domain/states.py:794-801`（reservation 图）与 EntityState 联合词汇（无 RELEASED 成员）；冻结依据 `docs/architecture/DOMAIN_CATALOG.md:54` 辅助散文 `Reservation(held→committed→released/expired)`。
- **预期**（按目录链）：存在 `released` 生命周期状态；边 held→committed、committed→released、committed→expired。
- **实际**：EntityState 全联合（69 态）无 `released`；图实为 held→{committed, cancelled, expired}、committed→{cancelled}；缺 committed→released/committed→expired；held→expired、held→cancelled、committed→cancelled 三条额外边未获目录授权。
- **影响**：G02 阶段判据「32实体及辅助记录可表达」无法表达"已释放"的预留；P03-04（版本 CAS/资源预留存储）与 P05/P16 预留 API 将继承把"释放"混同"取消"的词汇。
- **复现**：比较 `LIFECYCLE_TRANSITIONS['reservation']` 与目录 54 行；`grep RELEASED packages/domain/src/logistics_domain/states.py` 为空；本轮日志 `21-business-probes-run2-authoritative.log` 的 `LC reservation…`/`LC EntityState == union` 检查项。
- **责任方**：DSH-A（states.py 生命周期转录，P02-01 主写者）；目录措辞归 A 契约治理。
- **限定修复建议**（候选变更仅限 states.py 及其测试）：EntityState 增 `RELEASED="released"`，reservation 图改为目录忠实边 held→{committed}、committed→{released, expired}；业务上合理的额外边（held→cancelled/expired、committed→cancelled）仅在治理修订 DOMAIN_CATALOG 或登记 issue 后保留，不得静默保留。随后重跑必需命令并重派本任务预验收。

## 观察项 ZC-P02-01-N01（minor）

`DOMAIN_CATALOG.md:39` 散文 `created→running↔paused→completed` 存在两读：图采用 created→running→completed + running↔paused（无 paused→completed），业务连贯且未杜撰状态，但两种读法均未文档化。建议与 F01 同批由治理澄清目录措辞并登记 issue；单独不阻断。

## 其余独立核验（全部通过）

- **六项任务测试用例独立复现**（自写探针，非复述 DSH 测试）：[0,10)/[10,20) 不冲突且半开边界正确；delivered→draft 抛 `InvalidTransitionError(code=invalid_transition)`；JobKind/JobOptimizationMode 序列化固定小写值（成员值逐项等于任务卡冻结集）；`JobKind("routing")` 与 `parse_enum` 均拒绝（typed INVALID_INPUT）；`CalendarInterval(10,10)` 与 (20,10) 拒绝；calendar 缺 epoch_utc（TypeError）与 naive（InvalidInputError）拒绝，未覆盖时间为 0。
- **枚举冻结**：EntityKind **45/45** 精确等于 `DATA_CONTRACTS.md` 类型表（名+值+数量）；全树无第二套 `class JobKind/JobStatus/JobOptimizationMode/EntityKind/ErrorCode` 定义；ErrorCode 18 成员且 `UNSUPPORTED` 不在（符合任务错误处理规则）；`HTTP_STATUS_BY_ERROR_CODE` 与 ErrorCode 双射。
- **Calendar/TimeWindow**：ResourceCalendar 三字段完整（epoch_utc/version/intervals）、区间严格升序不重叠、闭式服务窗两端可取、布尔/浮点拒绝。
- **冻结范围判定（按真实契约，不臆造）**：`ConstraintCode`/`ViolationCode` 以 `NewType(str)` 交付、无成员杜撰（A 项治理缺口，evidence 已携 `issues_to_register`，README 尚未登记=治理待办，非本任务缺陷）；`SafeArtifactPath` 按 ArtifactRef 引用交付最小安全读法（五种逃逸形状全部拒绝），B 项治理待办。
- **纯度与失败语义**：隔离解释器（`-I`）导入 domain 全家第三方模块 **0**；`entities`/`units` 仍 `NotImplementedError`、未知名 `AttributeError`。
- **无自扰动**：全部探针后候选字节不变。

## 停止状态

本轮按派发未跑全回归（DSH 272 作为有来源依赖证据引用）、未改任何实现/契约/DSH/Gate、未启动 P02-02。缺陷卡已交回 DSH-A；修复形成新候选后重派 P02-01 预验收；通过后按阶段流程交独立 Codex 做 G02 审查。
