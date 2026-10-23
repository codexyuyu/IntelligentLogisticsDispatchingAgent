# 开源拆解清单与今日 demo

核验日期：2026-09-09。结论：**值得新增拆解的是 Timefold 的车辆路线和食品包装示例；今天实际计算继续用 OR-Tools，异常回放用 SimPy。** Great Blue 用来理解仓库现场流程；InvenTree 补库存概念；Sentry 补作业事务。采用这些参考不意味着同时安装它们的整套系统。

今天已在本机运行独立编写的三个 Python 小 demo，见 [运行入口](../demos/README.md)。完整 WMS、Timefold、PyVRP、VROOM 没有在本机部署，本文件区分源码阅读与实际运行。

## 优先读哪些 GitHub demo

| 优先级 | 来源与直接入口 | 拆解重点 | 本项目落点/负责人 |
| --- | --- | --- | --- |
| P0 | [OR-Tools 时间窗路径例子](https://github.com/google/or-tools/blob/v9.15/ortools/constraint_solver/samples/vrp_time_windows.py) | 节点映射、时间累计、等待、车辆起终点；另加容量与温区 | 运输适配器；B；今日已跑 |
| P0 | [OR-Tools 最小作业排程](https://github.com/google/or-tools/blob/v9.15/ortools/sat/samples/minimal_jobshop_sat.py) | 作业区间、资源互斥、工序先后；另加预约窗、故障和冻结事实 | 仓储适配器；A；今日已跑 |
| P0 | [Timefold vehicle-routing](https://github.com/TimefoldAI/timefold-quickstarts/tree/b9abb3bcd417d51cbd972a69744ba9fc81173b7f/use-cases/vehicle-routing) | 一个完整调度 demo 如何组织对象、约束、提交/查询和解释 | B 读约束、C 读作业接口、Codex 读展示；源码已读，未启动 |
| P0 | [Timefold food-packaging](https://github.com/TimefoldAI/timefold-quickstarts/tree/b9abb3bcd417d51cbd972a69744ba9fc81173b7f/use-cases/food-packaging) | 清洁占用、硬截止和期望截止分离、资源分配 | A 的清洁/模式切换扩展；源码已读，未启动 |
| P0 | [SimPy Machine Shop](https://simpy.readthedocs.io/en/stable/examples/machine_shop.html) | 进程、故障、中断、维修资源；官方项目托管 GitLab | B 的仿真基础与 C 的异常触发；今日只跑边界时刻故障简化版 |
| P1 | [InvenTree 库存模型](https://github.com/inventree/InvenTree/blob/master/src/backend/InvenTree/stock/models.py) | 库位层次、库存条目、批次与追溯关系 | A 的纯领域对象，不搬大型 Django 模型文件 |
| P1 | [Sentry 收货撤销服务](https://github.com/hightower-systems/sentry-wms/blob/main/api/services/receiving_service.py) | 撤销、可用库存、订单状态重算、事务归属 | A 的库存事务；另看 inventory/picking/shipping 服务边界 |
| P2 | [PyVRP](https://github.com/PyVRP/PyVRP) / [notebooks](https://github.com/PyVRP/PyVRP/tree/main/notebooks) | Python 路由建模和对照实验；版本支持范围要单独核对 | B 在第 7 周后可做共同约束集基线，今天不增加第二个求解依赖 |
| P2 | [VROOM](https://github.com/VROOM-Project/vroom) / [输入输出约定](https://github.com/VROOM-Project/vroom/blob/master/docs/API.md) | jobs/shipments/vehicles、容量和时间窗的 JSON 接口 | 未来可替换运输服务，首期不引入 C++ 服务部署 |

这里的 P0/P1/P2 是本项目拆解顺序，不是项目稳定性排名。Timefold 的两个例子比 WMS 更贴近调度演示，但 Java/Quarkus/Maven 会增加当前 Python 主线的学习与运行成本，故先学习其行为与边界。

## Timefold 最值得逐文件拆解的地方

固定阅读提交：`b9abb3bcd417d51cbd972a69744ba9fc81173b7f`。Quickstarts 仓库许可证为 Apache-2.0；README 中另列 Plus/Enterprise 启动方式，不将这些商业版能力视作默认开源能力。

1. [VehicleRoutingConstraintProvider.java](https://github.com/TimefoldAI/timefold-quickstarts/blob/b9abb3bcd417d51cbd972a69744ba9fc81173b7f/use-cases/vehicle-routing/src/main/java/org/acme/vehiclerouting/solver/VehicleRoutingConstraintProvider.java)：看容量、服务结束截止与行程成本如何分别定义。它把未分配访问作为中等级惩罚；我们必须另行明确“必服务”订单，不能直接继承可漏单策略。
2. [FoodPackagingConstraintProvider.java](https://github.com/TimefoldAI/timefold-quickstarts/blob/b9abb3bcd417d51cbd972a69744ba9fc81173b7f/use-cases/food-packaging/src/main/java/org/acme/foodpackaging/solver/FoodPackagingConstraintProvider.java)：看操作员清洁时间冲突、最大截止与理想截止。移植的是约束含义；食品包装任务不会自动变成冷库容量/温区模型。
3. [VehicleRoutePlanResource.java](https://github.com/TimefoldAI/timefold-quickstarts/blob/b9abb3bcd417d51cbd972a69744ba9fc81173b7f/use-cases/vehicle-routing/src/main/java/org/acme/vehiclerouting/rest/VehicleRoutePlanResource.java)：看异步提交、作业 ID 和结果查询。原示例用内存映射保存作业且注明增长问题；正式项目需要持久化、租约和版本核对。

如以后希望亲自启动原版，两个目录的 README 给出 Java/Maven 环境和 `mvn quarkus:dev`，随后访问本地 8080。今天未验证这条 Java 启动路径；已验证的是下面的 Python demo。

## 用户找到的 Great Blue：六处值得读，整体不继承

`infiniteoo/wms` 的 README 明确名为 **Great Blue (Open WMS)**，与截图名称匹配，之前“无法确定身份”的判断现已更正。它与 GreaterWMS、OpenWMS.org 是不同项目。

本次本地浅克隆提交为 `144a372c71d2d596c98069ffe5616ca0c83d16b2`，提交时间 2023-11-23。没有安装其依赖或连接 Supabase/Clerk。以下均检查了对应组件源码。

| 值得拆解的部分 | 来源 | 学什么 | 我们如何重新实现 |
| --- | --- | --- | --- |
| 收货/发货与订单行 | [receiving/Orders.jsx](https://github.com/infiniteoo/wms/blob/144a372c71d2d596c98069ffe5616ca0c83d16b2/components/receiving/Orders.jsx)、[OrderModal.jsx](https://github.com/infiniteoo/wms/blob/144a372c71d2d596c98069ffe5616ca0c83d16b2/components/receiving/OrderModal.jsx) | 订单头、批次、箱数、生产/到期日、作业状态 | A 做 Order/Batch/Operation 和状态迁移；Codex 做表单 |
| 库存与批次 | [DisplayInventory.jsx](https://github.com/infiniteoo/wms/blob/144a372c71d2d596c98069ffe5616ca0c83d16b2/components/inventory/Inventory/DisplayInventory.jsx) | LPN、批号、库位、数量、保质期展示 | A 分开实物、预留、隔离和库存历史，借 InvenTree 补齐边界 |
| 仓库预约 | [Appointments/Calendar.jsx](https://github.com/infiniteoo/wms/blob/144a372c71d2d596c98069ffe5616ca0c83d16b2/components/tools/Appointments/Calendar.jsx) | 预约时间与关联订单、承运商字段 | A 做资源日历与 CP-SAT；拖动只提交改期请求，经后端校验确认 |
| 月台作业看板 | [DockActivity.jsx](https://github.com/infiniteoo/wms/blob/144a372c71d2d596c98069ffe5616ca0c83d16b2/components/tools/DockActivity/DockActivity.jsx) | 月台对应当前装卸订单 | A 提供实际占用与未来预留，Codex 展示；看板不充当求解器 |
| 司机签到与现场状态 | [driver_check_in/ReportTable.jsx](https://github.com/infiniteoo/wms/blob/144a372c71d2d596c98069ffe5616ca0c83d16b2/components/shared/driver_check_in/ReportTable.jsx) | 签到记录、操作员、状态、归档 | B 提供车辆到达事件，C 处理延误影响，A 对接装卸任务 |
| 异常工单 | [Incidents/IncidentModal.jsx](https://github.com/infiniteoo/wms/blob/144a372c71d2d596c98069ffe5616ca0c83d16b2/components/inventory/Incidents/IncidentModal.jsx) | 描述、位置、提交人、指派、解决和归档 | C 做 Event→影响集→候选重排→校验→处置记录；保持证据来源 |

代码组织不直接沿用：上述多个 React 组件直接访问 Supabase，业务状态和界面耦合；预约组件主要是手动日历增改，没有体现自动仓运联合求解。收发货表单有重复结构及 `staus` 字段拼写；库存保存处用到期日减生产日计算 `days_to_expire`，不能照搬成“当前剩余保质期”。这些是阅读时的具体例子，不是完整缺陷审计。

当前检出树未找到明确 LICENSE、数据库迁移或测试套件；README 还引用了当前树中没有的 `/server/models/labRequests`。所以将其作为流程参考，独立实现领域对象；不直接复制业务源码。员工排班/绩效、标签打印、复杂报表、移动扫描端暂不纳入比赛主线。前端样式与交互阅读统一交给 Codex。

## 从拆解到项目，避免变成拼装大系统

每次只走五步：选一个行为 → 写输入/输出和反例 → 实现纯领域规则 → 接计算或存储适配器 → 用独立校验验证。禁止直接把 React 数据库操作、Django 模型、Java 求解对象塞进自己的核心模块。

今天的三个 demo 只交换普通字典，并由不依赖求解器的校验文件检查结果；后续进入正式 `domain/application/ports/adapters` 时用明确类型与版本替代教学字典。先得到真实约束和失败样例，再封装接口，避免为了“解耦”制造一批没有替换需求的抽象层。

没有找到经过本次运行验证、能直接满足全部大创要求且足够轻量的一体化开源成品。路线应是复用计算组件和业务设计，自己实现仓运协同、执行一致性与可信证据这三项核心贡献。
