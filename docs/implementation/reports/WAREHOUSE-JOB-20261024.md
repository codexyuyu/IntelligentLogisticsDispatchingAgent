# 2026-10-24 · 测试复核、仓储作业修复与申请书差距

结论：运输浏览器最小闭环有一致的日志与版本证据。本轮修复仓储提交异常、
接入独立仓储校验，并修复不可行诊断类型；真实仓储作业专项 4 passed。
仍未完成申请书的仓运联合、完整冷链模型、事件局部重求解、反事实推演、
四角色协商和量化实验。前端零修改；本轮不签 Gate，不把专项测试视为全功能验收。

## 范围与来源

- 工作根：`D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent`。
- 基线 Git：`bb15d36`。运行路径按根目录 `apps/`、`packages/`；不使用另一工程、
  `merged/`、`demo/` 或 `demos/` 的功能/测试抵充当前运行工程的完成度。
- 原始需求：[申请书](../../../基于大模型技术的物流调度智能体应用开发.pdf)，全部 7 页已读取。
  主要实现要求见第 2–5 页；[R01–R10 追踪](../../02-requirements.md)是已有工程拆解。
- 精确范围见 [任务卡](../WAREHOUSE-JOB-20261024.md)。B 文件仅执行用户本轮明确授权的
  Diagnostic 导入修复，不修改其求解建模、公共类型或所有权。

## 既有日志复核

- `tmp/pytest-browser-loop.log` 原始尾部为 **302 passed in 237.91s**，不是本轮新结果。
- `artifacts/e2e/.last-run.json` 记录 passed；运输证据含 33 个 HTTP 请求。
- `transport-loop.json` 中提交、当前版本、刷新后版本均为
  `8ff6854a-7120-4d96-97ed-c7b953002964`，task_count=1。
- `tmp/e2e-transport/db-verification.txt` 独立 SQL 回读同版本，version_no=1、committed。
- 原始后端日志包含求解结果 200、候选创建 201、版本提交 200、刷新回读 200。
- 复算报告列出的四个交付文件 SHA256 均一致。审计摘要及原始文件哈希：
  [prior-log-audit.json](../../../tmp/WAREHOUSE-JOB-20261024/prior-log-audit.json)。
- 本轮没有重跑浏览器；上述只能证明已有最小运输用例，不能推导完整报告书已满足。

## 本轮实现与验证

1. `application/warehouse.py` 补 `hashlib` 导入。修复前真实 HTTP 提交返回 500，
   原日志确认 NameError；不是数据库或求解耗时问题。
2. 仓储 worker 在保存有解结果前调用现有 `validate_warehouse`，保存该独立报告。
   保留求解器原始状态；即使求解器认为 optimal，独立校验失败仍明确返回 valid=false。
   没有替求解器填造“已支持全部规则”的字段。
3. `warehouse/solver.py` 不可行路径使用已有仓储 Diagnostic。
   修复前错误地导入运输 Diagnostic，传字符串 severity 时抛 InvalidInputError，
   无法正常返回 infeasible；本次只改导入。

专项使用专用 PostgreSQL 17 测试容器、全套迁移、实际回环 HTTP 服务、生产 Worker
的 spawn 子进程、真实 OR-Tools CP-SAT 及哈希校验的结果文件。无数据库/求解器替身。
临时服务和结果均限定在本任务测试范围；未停止或重建原 Docker 产品栈。

| 用例 | 结果与断言 |
| --- | --- |
| 真实仓储作业 | HTTP 202 → queued → worker → completed → 仓储结果 200；两个顺序作业为 [0,10)、[10,25)，独立校验 valid=true；输入/assignment/结果 SHA256 一致 |
| 非法资源 | 当前求解器仍会选择请求中不存在的资源；独立校验返回 valid=false 与 unknown_resource，不能作为已验证方案 |
| 不可行时间窗 | 返回 infeasible、空 assignments、诊断非空、validation=null，不冒充有解 |
| 跨仓任务 | 捕获快照不包含任务仓库时返回 422 与明确原因 |
| 附加负例 | 作业未完成查询结果返回 409；篡改结果文件后返回 422/unverified_solver_result |

注意：25 秒是排程时间轴的 makespan，不是求解耗时或秒级异常响应的性能证据。
专项原始结果：**4 passed，6.39s**；存在 3 条第三方 SWIG DeprecationWarning，无 skip/xfail。
完整 unit + integration 回归：**306 passed，147.46s，exit 0**，同样 3 条第三方警告；
无 skip/xfail。架构检查扫描 118 模块、7 层、0 violations；业务 Schema `--check`
exit 0。完整证据及输入/日志 SHA256 见
[verification.json](../../../tmp/WAREHOUSE-JOB-20261024/verification.json)。

复验命令（先建立专用测试库并运行 `DATABASE_URL=<该测试库> python -m alembic upgrade head`）：

```text
TEST_DATABASE_URL=<该测试库> python -m pytest tests/unit tests/integration -q --basetemp <新的临时目录> -p no:cacheprovider
python scripts/check_architecture.py
python scripts/export_contracts.py --check
```

必须使用项目 `.venv` 和新的临时目录；旧数据库集成用例含清表操作，只允许隔离测试库。
本轮临时容器在验证结束后移除，日志/结果证据保留；复验不能直接使用已退出容器的旧端口。

## 申请书要求与未完成清单

状态含义：“部分实现”只表示当前正式代码存在相应能力；“未完成”包括核心逻辑缺失
或尚无满足该要求的端到端证据。不能以模块数量、302/306 测试数量换算完成百分比。

| 要求 / 原文页码 | 已确认能力 | 尚缺功能或必要验收 | 当前证据 |
| --- | --- | --- | --- |
| R01 路径与运力分配，4–5 页 | 真实 Routing、逐站时间/载荷、最小浏览器求解与版本提交 | 完整约束覆盖负例、路况天气分时变化、2仓4车20单及50/100单容量/耗时证据；单个用例不证明全局最优或所有冷链约束 | `optimization/transport/solver.py`、运输 E2E |
| R02 异常处置，3–5 页 | 事件入库、异常投影、影响分析、处置记录的部分接口 | 延误/货物/天气/需求/故障自动识别到有效候选再确认的完整闭环；秒级响应实测 | `application/events.py`、`exceptions.py`、`impact.py`、`reschedule.py` |
| R03 仓配与多节点协同，4–5 页 | 仓储 CP-SAT 作业链路、本轮独立校验、联合校验入口 | 同时满足月台/人员/设备的资源约束；仓储 from-job 候选提交；两仓可选接收与资源协商；装卸完成时间和车辆到离时间的联合约束及迭代求解 | 仓储 solver 的 `_eligible` 合并资源集合并只选一个；`validation/joint.py` 只组合报告并检查快照/订单覆盖，未检查交接时间 |
| R04 自然语言与工具编排，2–5 页 | 模型适配、聊天、调用审计基础；历史报告有单次真实模型 smoke | 自然语言抽取带来源的约束、澄清、调用真实求解工具、依据结果解释、确认保护；当前单次聊天不能证明调度 Agent 完成 | `agents/service.py` 只发 system/user 消息；`application/tools.py` 当前仅注册 job_status/agent_runs |
| R05 冷链与跨批次复用，1–2、4–5 页 | 温区/载荷及部分库位、库存、setup、技能独立校验代码 | 将时间变化有效容量、预冷、清洁消毒/换批、温区切换、保鲜/脱冷暴露、多资源条件完整放入求解模型；七天顺序复用及正反例 | 仓储 solver 主要建 exactly-one/no-overlap/precedence，storage_allocations/setup_operations 仍返回空 |
| R06 局部重调度，3、5 页 | 影响集合、冻结边界及 typed 调整建议 | 对受影响剩余任务真实重求解；局部→扩大→全局的有界退路；保留执行事实/救援交接；完整方案重验、版本追加、扰动对照 | `application/reschedule.py` 明示 no solver claim，只生成 DEFER/RESCUE_HANDOFF 建议 |
| R07 数字孪生推演，2–3、5 页 | SimPy 按站点计划产生到达/服务/离开事件 | 状态持续更新、暂停/步进、完整 RNG/资源/事件队列快照恢复、注入异常后演化、反事实分支隔离和恢复一致性测试 | `simulation/engine.py` 当前只有 run/_visit；使用 uuid4 事件 ID，同 seed 全轨迹字节一致亦未证明 |
| R08 四角色合同网协商，3–4 页 | 聊天与审计基础 | 协调/仓储/运输/异常四角色、发布/报价/授标/确认/撤销、版本绑定、过期报价、轮数/时间预算、最小信息交换 | `agents/` 当前仅 tools/service/llm 等基础实现，未接入合同网执行循环 |
| R09 指标与对照/消融，3 页 | 部分计划/仿真指标、两份结果差值与持久化 | 准时率、平均延误、时间占用利用率、异常检测/重排时间、扰动等完整定义与手算；等预算配对种子实验、基线/消融、原始失败样本和统计汇总 | `evaluation/metrics.py` 是子集；`ExperimentService.compare` 接收已有结果比较，不负责运行策略/种子实验 |
| R10 可安装与成果交付，2、5–6 页及命题扩展 | Docker 原型、开发文档、局部演示证据 | 干净安装复现、A/B/C完整演示、安全与恢复/性能验收、对齐实际实现的文档；视频/技术方案/简介等完整提交包证据不足 | 部署文档与最新报告；官方 Gate 仍只有 G00/G01，不能等同最终签收 |

页面只作为交付接口；本轮按用户要求不修改任何前端。报告书提及的平台可选性、
Routing/CP-SAT 分工及不支持任意拆单等已有范围决定见 `docs/02-requirements.md`；
原文“杜绝幻觉”“显著缩短”“最优”不能当成已验证事实，需以对应模型证明和实验支撑。

## 下一明确任务

先补仓储模型的“多资源同时占用与准备时间”及独立反例，尤其当前将 eligible_ids
取并集后 exactly-one 只能选一个资源，不能表达同时需要月台、工人和设备。
随后接仓储真实结果到候选/版本提交，再补仓运交接时序与联合求解。
该建模修改主要在 B 所有权范围，需正式限定任务卡；本轮的一处导入授权不扩展到它。
异常局部重求解、仿真分支、四角色工具编排与实验按依赖继续，不能以聊天或界面代替。

本轮修改尚未部署到运行中的 Docker 镜像；已验证的是当前源码和隔离测试服务。
