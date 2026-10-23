# 冷链物流调度智能体开源调研与实施建议

初次调研：2026-09-08；增补：2026-09-09。面向：大学生创新训练三人团队。初次交付文档与目录；用户随后要求落实 demo，现已增加三个独立计算探针，见 [运行说明](../demos/README.md)。用户已确认采用 9 周开发、1 周集中测试，万悟不是必需平台。

## 推荐结论

建议建立自己的轻量模块化单体，以 **FastAPI 官方全栈模板作为工程结构参考，InvenTree 作为库存领域参考，Sentry WMS 作为作业服务参考，OR-Tools 与 SimPy 作为实际计算组件**。这个选择来自任务适配、可替换性和团队成本的综合判断，不是开源项目排名，也不是部署后的性能结论。

核心研究对象是“仓储和运输互相约束时如何生成完整可行计划，以及异常后怎样低扰动修复”。完整搬用 WMS 会带入采购、财务、制造、商店连接器等大量无关功能，却仍需自己完成这两个核心问题。开源项目提供成熟构件与边界范例，不能替代本项目的建模、联合校验和实验。

工程采用 React + FastAPI + PostgreSQL；运输用 RoutingModel，仓储用 CP-SAT，SimPy 负责回放和推演。大模型负责需求抽取、有限工具编排和有证据的解释。正式执行由应用层按数据版本和校验结果控制。

## 图片项目核验

图片的星级没有评价方法，不能作为稳定性证据。用户在 2026-09-09 补充 [infiniteoo/wms](https://github.com/infiniteoo/wms)，README 明确为 Great Blue (Open WMS)，现已确认截图第一项身份，纠正初次调研时的未确认状态。它与 GreaterWMS、OpenWMS.org 不同。已检查源码，具体可拆解模块见 [增补清单](08-reuse-blueprint.md)。

| 项目 | 官方可核实情况 | 本项目如何参考 |
| --- | --- | --- |
| [Great Blue / infiniteoo/wms](https://github.com/infiniteoo/wms) | Next.js/React、Supabase 与 Clerk；本次检出未见明确 LICENSE、迁移或测试套件；多处组件直接写数据库 | 参考入出库、批次、预约、月台、签到和异常工单；不作为整体工程底座 |
| [GreaterWMS](https://github.com/GreaterWMS/GreaterWMS) | Django/DRF 与 Quasar/Vue，Apache-2.0；按 asn、dn、stock、warehouse 等拆分。与截图 Next.js/React 不符 | 看入出库、库存和盘点流程；不继承全部 app 和旧依赖 |
| [OpenWMS.org](https://github.com/openwms/org.openwms) | Java/Spring 与多个独立服务；根库 Apache-2.0，部分业务模块的开放/许可状态不同 | 借业务能力边界，不搬注册、网关、消息代理等部署体系；仓内运输概念不能等同公路 VRP |
| [Sentry WMS](https://github.com/hightower-systems/sentry-wms) | React、Flask、PostgreSQL，另含队列和连接器等；Apache-2.0 | 借 receiving、inventory、picking、shipping 服务边界及事务思路；不完整复制电商功能 |
| [Nyamador Django React WMS](https://github.com/Nyamador/Django-React-Warehouse-Management-System) | wms 与 wms-frontend 分离；旧 Django 依赖；根目录/README 未见明确许可证 | 仅做基础页面与对象关系的阅读示例，不作为稳定或可直接复制的底座 |
| [avinandanroyy FastAPI React WMS](https://github.com/avinandanroyy/warehouse-mngt-fastapi-react) | FastAPI/React，主要是角色、用户、库存 CRUD；页面仅 1 次提交；未见明确许可证 | 可看前后端连接，稳定性证据不足；无需仿照其每层机械建目录 |
| [InvenTree](https://github.com/inventree/InvenTree) | Django/DRF、React、REST API 与插件，MIT；库存、品类、订单与扩展有明确边界 | 六者中优先作为领域模型参考；只取批次、库存、库位、订单等相关概念，不引入 BOM/制造全栈 |

可进一步核对的原始文件包括 [GreaterWMS 后端依赖](https://github.com/GreaterWMS/GreaterWMS/blob/master/requirements.txt)、[前端依赖](https://github.com/GreaterWMS/GreaterWMS/blob/master/templates/package.json)、[Sentry 服务目录](https://github.com/hightower-systems/sentry-wms/tree/main/api/services)、[InvenTree 业务目录](https://github.com/inventree/InvenTree/tree/master/src/backend/InvenTree)。这些结构是参考，不自动赋予本项目同样的运行质量。

### 维护证据及其限制

| 项目 | 截至核验日的可见信号 | 意义 |
| --- | --- | --- |
| GreaterWMS | [V2.1.50，2025-06-29](https://github.com/GreaterWMS/GreaterWMS/releases/tag/V2.1.50) 发布说明转向 Bomiot 重构 | 不把重构公告当作已经成熟可用的新版冷链系统 |
| OpenWMS 根库 | [2026-07-13 提交](https://github.com/openwms/org.openwms/commit/9d263bf65ec75301e0302539ae7bf581412742b8) | 有维护活动，但根库状态不能代表所有独立服务 |
| Sentry WMS | [v1.37.0，2026-08-20](https://github.com/hightower-systems/sentry-wms/releases/tag/v1.37.0) | 持续演进；需要固定版本，不能仅凭 README 测试数字推定可靠性 |
| Nyamador | [最后可见提交 2020-07-17](https://github.com/Nyamador/Django-React-Warehouse-Management-System/commit/a8ef85e01eaa3f2654a6d5d9dca41e534ab5dde6) | 更适合学习示例，旧依赖迁移会增加工作 |
| avinandanroyy | [提交记录](https://github.com/avinandanroyy/warehouse-mngt-fastapi-react/commits/main.atom) 显示 2026-06-29 单次提交 | 新不等于成熟，缺持续维护证据 |
| InvenTree | [1.5.3，2026-09-08](https://github.com/inventree/InvenTree/releases/tag/1.5.3) 包含权限、库存并发等修复 | 有持续修复证据，仍须锁版本、跑本项目场景 |

以上日期是官方记录的可见提交/发布信号，不是发布时间越新越稳定的证明。没有运行上述完整 WMS，也没有对它们做安全审计。增补检出的 Great Blue 提交为 `144a372c71d2d596c98069ffe5616ca0c83d16b2`，时间 2023-11-23；不据此假定它已稳定支持我们的场景。

## 更适合的工程和算法参考

2026-09-09 新增 [Timefold Quickstarts](https://github.com/TimefoldAI/timefold-quickstarts) 的车辆路线与食品包装示例，值得拆解约束、异步作业与展示结构；仍保留 Python 主线。具体文件、重构边界、今日运行记录与 PyVRP/VROOM 对照见 [增补清单](08-reuse-blueprint.md)。

| 项目 | 可复用部分与许可 | 选择与限制 |
| --- | --- | --- |
| [FastAPI 官方全栈模板](https://github.com/fastapi/full-stack-fastapi-template) | 前后端分离、迁移、基础认证、测试与 OpenAPI 客户端；[MIT](https://github.com/fastapi/full-stack-fastapi-template/blob/master/LICENSE) | 主工程结构参考。保留需要的能力，再独立组织调度领域；不整包复制邮件、云部署和示例业务 |
| [Google OR-Tools](https://github.com/google/or-tools) | 路径与排程实现及样例；[Apache-2.0](https://github.com/google/or-tools/blob/stable/LICENSE) | 唯一首期优化依赖；冷链约束和仓运协调仍由团队实现 |
| [SimPy 稳定文档](https://simpy.readthedocs.io/en/stable/index.html) | Python 离散事件、共享资源和事件交互；MIT | 首期仿真。不是优化器，不自带真实冷链热模型或现场数字孪生 |
| [VROOM](https://github.com/VROOM-Project/vroom) | C++ 路线服务、多维容量、时间窗等；BSD-2-Clause | 可选运输替换/基线。不会替代仓内排程；增加服务部署成本，首期不引入 |
| [PyVRP](https://github.com/PyVRP/PyVRP) | VRP 求解与研究基线；MIT | 可选共同约束集对照。官网开发文档与稳定发布可能不同，需逐版本确认能力 |
| [OSRM](https://github.com/Project-OSRM/osrm-backend) | 道路路线与时间/距离矩阵；BSD-2-Clause | 后续矩阵适配器。首期固定矩阵更易复现；它不是车队分配、冷链或实时天气服务 |
| [万悟](https://github.com/UnicomAI/wanwu) | 工作流、模型和工具/API 入口；[Apache-2.0](https://github.com/UnicomAI/wanwu/blob/main/LICENSE) | 用户确认可选。保持入口适配，不内嵌整个平台作为必需组件 |

FastAPI 模板当前文档的 [frontend](https://github.com/fastapi/full-stack-fastapi-template/tree/master/frontend) 使用 React、Vite、TypeScript 等，并提供生成客户端；[backend](https://github.com/fastapi/full-stack-fastapi-template/tree/master/backend) 提供迁移与测试。搜索缓存曾出现旧版 Chakra UI 与旧部署结构，应以选定提交对应文件为准。本项目不需要跟随主分支自动升级。

[PyVRP 官网](https://pyvrp.org/) 本次显示 1.0.0a0 开发文档，部分兼容关系能力标为 Enterprise；[0.14.0 发布](https://github.com/PyVRP/PyVRP/releases/tag/v0.14.0) 另有接口变化。不能把未来开发文档中每项能力都视作当前稳定开源版自带；这也是首期不再增加第二个优化器的理由。

[OSRM HTTP 文档](https://project-osrm.org/docs/v26.4.0/http) 区分已定站点顺序的路线服务与矩阵服务，输出秒和米。道路数据、可视化瓦片和实时交通是不同来源；公共瓦片服务并非离线地图下载源，遵守 [OSMF 使用政策](https://operations.osmfoundation.org/policies/tiles/)。

### 参考结构到本项目的映射

| 来源 | 参考位置或思想 | 本项目落点 | 主动裁剪 |
| --- | --- | --- | --- |
| FastAPI 模板 | backend / frontend、迁移、客户端生成 | backend、frontend、contracts | 邮件、复杂云发布、样例全量 CRUD |
| InvenTree | part / stock / order / plugin 的概念分离 | domain 的品类、批次、库存、订单；ports 的外部库存边界 | BOM、生产、采购、丰富插件系统 |
| Sentry | routes / services / schemas 和仓储作业 | api 与 application 分离；入库、分拣、出库用例 | 商店集成、POS、多队列体系 |
| OpenWMS | 按业务能力界定职责 | 仓储、运输、异常、协调接口 | 微服务部署拓扑 |
| OR-Tools | 两类求解器各自模型与状态 | adapters + 独立领域结果契约 | 不让求解变量传播进业务层 |
| SimPy | 进程、资源、事件 | 仿真适配器与独立快照分支 | 不把仿真时钟变成数据库事实时钟 |

## 速度与可信性如何兼顾

采用单体不会妨碍模块解耦：业务依赖自己定义的接口，部署仍保持简单。CPU 密集求解放工作进程，矩阵提前批量获取，快照固定后在内存计算，局部重排限制范围和轮数。实际速度在第 2 周测量，第 8 周完成正式对照，不能凭库的宣传承诺毫秒或秒级。

路径优先用 Routing，仓储用 CP-SAT，协调器交换时间窗与冲突并有界反馈。两者各自成功还不足以确认，必须独立校验完整时间链和库存守恒。[Routing 指南](https://developers.google.com/optimization/routing) · [仓储排程原语](https://github.com/google/or-tools/blob/stable/ortools/sat/docs/scheduling.md)

最重要的防错误机制是“输入有来源、硬约束变更可见、执行前完整校验、确认时版本复核”。结构化格式和低温度采样都不能保证理解正确。超时未找到解、已证明不可行、可行未证明最优分别报告，解释只使用结构化证据。[CP-SAT 状态](https://developers.google.com/optimization/cp/cp_solver) · [Routing 状态](https://developers.google.com/optimization/routing/routing_options)

具体 [架构设计](03-architecture.md)、[接口契约](04-contracts.md) 和 [可信性评测](05-evaluation.md) 已把这些边界展开。前 3 周完成结构化联合调度，前 4 周完成事件修复闭环，之后增强语言、多仓与实验；[9 周开发加 1 周测试路线](06-roadmap.md) 给出每周退出条件。

## 竞赛可行性与剩余不确定项

工作区 PDF 的三大能力与 [高校发布的同名命题](https://cxcyxy.zjhzu.edu.cn/2026/0514/c2548a41937/page.htm) 一致。已建立逐项的 [需求和交付映射](02-requirements.md)。合同网、7 天仓储推演和消融实验作为申请书承诺纳入路线；不把它们混成比赛通用评分规则。

当前足以形成可执行路线，但尚缺最终报名赛道的评分表、提交日期、设备与导师认可的冷链规则。尚未取得真实企业数据、现场温度标定或真实路况服务。演示以合成场景为主，不能宣称生产级数字孪生、食品质量预测或所有规模的最优调度。

查询范围包括六个 WMS 仓库、工程模板、优化/仿真组件、平台、路网政策和标准基准；主来源是官方仓库与文档。内置浏览器导航连续超时，未完成可视页面核验；网页检索和官方文件读取成功。GitHub 公共 API 遇到限流，维护日期改由官方发布/提交记录核对。万悟两处手册链接 404，保留为可选接入风险。上述失败没有被包装成已完成的运行验证。

停止继续扩展检索的原因：每项核心选择已找到主来源与明确边界；剩余关键问题需实现探针、实际评分表或本机测试解决，继续增加同类仓库不会替代这些验证。

## 开源使用约定

本轮只借鉴结构和行为概念，未复制第三方业务源码。实现时建立第三方清单，逐项记录仓库、固定提交/版本、实际复用文件、许可证和修改说明，保留对应版权与 NOTICE。未见明确许可证的示例暂不进入代码来源名单；OpenWMS 的根许可不外推到其全部业务组件。

拟直接依赖选择稳定版并以一次干净环境安装及最小场景验证后锁定。OR-Tools [9.15 发布](https://github.com/google/or-tools/releases/tag/v9.15) 和 SimPy 稳定文档可作为版本调研起点，不在尚未验证兼容性时创建锁文件。项目自身许可证由团队后续决定。
