# R30-D · 仓储协同后端增强（2026-10-20）

## 一、版本范围

- 继承 R30-C / R30-B / R30-A，不改变原有单现役仓库 WH001、PostgreSQL 表结构、OSRM 策略、DeepSeek 身份验证、React 及 3D 模型，不对正式数据库执行写操作。
- 复用已有 CP-SAT / OR-Tools / R28 对账；本次**没有实现新的库容时间轴求解、预冷工艺优化或清洁换批排程**。
- 本次采用“已有调度求解器 + 业务事实预检查 + 独立方案校验 + 可追溯工具摘要”，不为完成度制造虚假字段和结果。

## 二、功能变化

1. `app.domain.cold_chain_rules.validate_cold_chain`：纯领域规则，不依赖数据库/求解器，按本轮所选订单审查批次存在性、仓库归属、温区匹配、同批次数量总需求、保质期、仓储任务资源类型和仓库归属。过期时间仅对比**已知实际配送结束时刻**，求解前使用订单最早服务窗口进行保守预检，不错误地把最晚允许送达时间当作实际送达时间。
2. 规则审计区分 `failed`（已知违反约束）和 `partial`（没有发现已知违规，但部分规则**未验证**）。对于 PostgreSQL R24/R27 模式，原数据没有实时预留、隔离余额字段，因此 **不能证明真实可出库库存**；该缺口作为 `coldchain.pg_live_reservation_and_quarantine_unknown` 返回。完整冷间长期容量和预冷/清洁换批同样明确未验证。原始仓储业务事实未修改。
3. R27 PostgreSQL 业务快照生成时复查已知规则；协调求解之前、WarehouseScheduleValidator 独立核验、R27 完成运输后均进行审查。后者检查实际送达时刻是否超过批次保质期。
4. `WarehouseScheduleValidator` 检查每订单 `warehouse_handoffs.ready_at_s` 必须等于实际全部相关仓储作业完成时刻；缺少交接、重复交接或人为提前交接会被拒绝。既有 B03/R28 的路由发车先后独立校验保持原样。
5. R30-C `generate_joint_plan` 工具向模型提供每车实际订单访问顺序、总距离与发车相对时刻、每项仓储作业的资源/起止相对时刻、每单装车就绪时刻，以及冷链规则覆盖审计。工具输出仅来自求解后结果和现有快照，未自造配送明细。详情超过上限时会注明截断。

## 三、如何运行（Windows）

在**新文件夹**解压完整 ZIP，勿覆盖已验收的 R30-C；保持本机 PostgreSQL 密码和 DeepSeek Key 只在后端设置。正常使用 R30-C 启动流程：

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\start_pg_r30c_local.ps1 -DemoOnly
```

另开 PowerShell：

```powershell
cd frontend
npm ci
npm run build
npm run dev
```

打开 `http://127.0.0.1:5173`，在“AI 智能调度助手”中使用内置合成场景；需验证 PostgreSQL R30-A 时，按 R30-C 手册移除 `-DemoOnly` 并使用已验收的 R30-A 数据环境。正常调度输出会包含 `cold_chain_audit` 及更多业务明细。API Key 不写入前端或交付包。

**建议验收**：

- 内置 20 单合成场景正常生成联合排程、车辆与订单分配，R28 对账 `passed`；冷链覆盖审计按实际支持范围显示 `partial`，不得宣传“所有冷链规则已通过”。
- PostgreSQL WH001 场景已有的 R30-A 20 单/40 作业数据能保持原映射；若实际记录变化，则应按该快照真实数量解释。
- 对比每单 `handoff.ready_at_s` 和全部相关仓储作业最晚 `end_s`，二者应相等，车辆发车不早于对应装车就绪。
- 故障重调度过程中已经完成的仓储与配送历史不变；不能处理的订单明确列为未服务。
- 对有确凿数量/温区/批次错误的快照应拒绝执行；对于实时库存预留未知的实库记录，应显示未校验标识。

## 四、已经验证 / 尚未验证

- 当前 Linux 隔离环境：新增 9 项业务反例/回归测试与相关 R27、R28、R30-A/B/C 等 **70 项定向测试通过**；Python 编译检查通过。（具体命令、覆盖文件见 `docs/devlog/entries/20261020-r30d-warehouse-enhancement.md`。）
- 未提供 DeepSeek Key，未连接你的 PostgreSQL、OR-Tools、Windows 浏览器。`pytest tests` 全量收集受到缺少 SimPy 依赖阻断。上述 70 项**不是**真实 Windows/DeepSeek/CP-SAT 全链路验收。
- 当前新功能属于**只读求解与核验**，没有正式排班下发、实时库存扣减、权限审计、冷间长期容量占用优化、预冷清洁切换求解。

## 五、故障排查与回退

- 正常入口与旧 R30-C 相同：`/local-pg/pg-preview/r30c/chat`，只读直接算法入口 `/local-pg/pg-preview/r30c/quick`。新字段是响应附加数据，保留旧字段，不新增迁移。
- 如果新审计报 `coldchain.batch_quantity` 或 `coldchain.batch_expiry`：先检查数据来源、批次和订单数量，不要绕过硬约束修改求解器。
- `status=partial` 不代表不合法，只代表部分业务条件无法被当前数据与模型证明；组会应如实标注。
- 可随时回退至独立文件夹内的 R30-C ZIP，R30-D 不触发数据库 DDL 或更新。
