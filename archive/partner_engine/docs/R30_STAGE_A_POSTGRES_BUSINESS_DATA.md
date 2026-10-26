# R30 · 阶段 A：单仓 PostgreSQL 业务输入与仓运求解

## 完成范围

阶段 A **只完善数据库业务资料和数据库驱动的联合求解**，**不包含**下一阶段的异常重调度或 AI Agent。R25–R29 的 3D 回放、R29 已通过的单现役仓库策略、原来的路线/计划/历史实验全部保留。OSRM 仍是可选服务，默认使用清楚标识的 PostGIS 直线估计。

本工程已有 R24 冷链扩展表（仓温区、批次、订单/车辆体积和班次、资源、装车作业）与 R27 仓储工时表。R30-A 补充：

1. `backend/tools/pg_r30a_bundle.py`：从 `coldchain_db` **只读读取** R29 现役 WH001 的订单重量、时间窗、车辆原有载重和温度区间等基础资料；生成 7 份 CSV，保留真实编号并对不存在的扩展数值使用**显式合成演示值**。
2. 在生成和校验时调用既有的 `verified_snapshot` 适配器，不只检查 CSV 表头，还检查温区/作业前驱/资源类型/时间/装车关系和来源标记；**不是求解成功保证**。
3. 默认只生成/校验本地文件，绝不写数据库。只有操作者在备份后显式 `-Apply -BackupVerified` 并输入 `DEMO_WH001`，才事务性 INSERT ONLY 到 R24/R27 扩展表及新增 `pg_r30a_data_provenance` 来源标记表；基础七表、历史方案和旧路线不改。
4. 如果任何 R24/R27 扩展数据已存在，**整批演示导入拒绝执行**，避免与真实/人工资料混用和覆盖。CSV 与生成时基础数据的 SHA256 不一致亦拒绝。遇到原车无法承接所选温区或跨温区车辆歧义也会报错，不能编造车型能力。
5. 读取端能识别来源并标注：`explicit_synthetic_demo` 为 PostgreSQL 中的合成演示扩展资料，`unmarked_operator_or_legacy_rows` 是原有人工/历史资料，**未被独立证明是现实业务实测**。真实来源与演示来源不得混淆。
6. R27/R28 原闭环入口继续调用真实 CP-SAT 与 OR-Tools 求解，R28 逐单对账与单时间轴继续可用。`GET /local-pg/pg-preview/r30a/readiness` 只读查看是否具备联合求解输入。

## Windows 操作步骤（按顺序，不能跳过备份）

### 0. 先确认 R29 已完成

你的 R29 只读输出已显示 `already_applied:true`、`state_valid:true`、`active_warehouse_codes:["WH001"]`。R30-A **不用重新执行 R29 迁移，也不删除 WH002 的历史 FK 记录**。先关闭旧后端，避免 8000 端口冲突。R30-A 解压到新文件夹，不覆盖 R29。

### 1. 先生成 CSV（只读，不需要关闭 PostgreSQL）

进入 R30-A 工程 `backend` 目录，PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\r30a_data_local.ps1
```

该命令要求本机 PostgreSQL 密码，生成上级 `r30a_synthetic_data` 目录，内有 `zones.csv`、`lots.csv`、`orders.csv`、`vehicles.csv`、`resources.csv`、`handoffs.csv`、`work_operations.csv`、`manifest.json` 和说明文件。**若目录已存在且非空就拒绝覆盖。** 生成器从真实基础表保留代码、重量、服务时间窗和原车辆冷温/载重上限；新增的单位/体积、批次、班次、库区、工时均是明确合成演示数据，不是观测资料。

### 2. 对当前 R29 迁移后的数据库做新备份

```powershell
powershell -ExecutionPolicy Bypass -File .\backup_pg_r30a_local.ps1
```

脚本识别此前发现的 `D:\postgresql\17\bin`，必要时临时配置 PATH，生成 `r30a_backups\coldchain_db_before_R30A_*.dump`，并用 `pg_restore --list` 检查归档可读取。**保留 R29 旧备份，但它是在迁移前创建的，不能替代现在这次迁移后的新备份。** 如果没有出现“已验证归档目录可读取”，禁止继续写库。此检查不等于完成实际恢复演练。

### 3. 检查 / 首次创建 R27 作业表（若以前未创建）

R24 六张表你已在 R24 安装，**不重建**。R27 的 `pg_r27_work_operations` 可能尚未创建。先按下一步校验数据，若 `-Apply` 提示 `r30a_R24_R27_tables_must_be_explicitly_installed_first`，在备份完成后显式安装**一张空表**：

```powershell
powershell -ExecutionPolicy Bypass -File .\r30a_data_local.ps1 -CreateR27Tables -BackupVerified
```

该步骤需要确认码 `WH001`，不自动导入任何记录。已有表时 `CREATE TABLE IF NOT EXISTS` 不会清空旧记录。**不需要启动第二个后端。**

### 4. 校验 CSV 和数据库没有变化（只读）

```powershell
powershell -ExecutionPolicy Bypass -File .\r30a_data_local.ps1 -Validate
```

如有 `r30a_base_data_changed_since_export_refuse_write`：基础表在生成后变化，**不要继续使用旧 CSV**，应检查差异后重新生成到全新空目录。遇到温区车辆不匹配，改用人工业务录入；不要修改车辆原有温控能力来强行通过演示。

### 5. 显式写入合成演示扩展资料（可选）

**只有你接受在 `coldchain_db` 增加合成演示记录并已经完成新的数据库备份时才运行：**

```powershell
powershell -ExecutionPolicy Bypass -File .\r30a_data_local.ps1 -Apply -BackupVerified
```

输入 PostgreSQL 密码和 `DEMO_WH001` 确认码。写入的合成演示记录有永久来源标记。**不是生产真实资料，不得用于实际库存扣减、排车发车或真实签收。** 由于导入工具是 INSERT ONLY，将来需要改成真实业务参数时不能简单再导入覆盖；应先按备份执行受审核的恢复/迁移，不可直接删除历史记录。

如暂时不想将演示数据写进主库，就只运行步骤 1、2、4，之后仍可用 R27 的“单仓演示”直接展示；从 PostgreSQL 导入实库字段的模式必须等待用户实际录入数据。

### 6. 启动 R30-A 并使用 PostgreSQL 数据运行仓运闭环

先关闭旧的 R29 后端。`backend` 目录：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_pg_r30a_local.ps1
```

`frontend` 目录在另一个 PowerShell：

```powershell
npm ci
npm run build
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`，进入左侧 **智能调度 → R28 仓运业务闭环**（沿用原入口）。选择 **PostgreSQL 核验 · 数据驱动（来源标识）**，检查数据显示来源为 **R30-A 合成演示数据**，选冷藏 `chilled`，点击运行；应得到 **CP-SAT 仓储 → 装车就绪 → OR-Tools 运输 → R28 订单逐单对账** 的单温区计划。如果真实数据库包含冷冻订单，需要另外选择 `frozen` 跑对应温区；**不同温区不会假装一次联合混装**。如求解器返回无解，要依据真实服务时间窗、速度估计与模型限制诊断，不会伪报求解成功。

API：`http://127.0.0.1:8000/local-pg/docs` 中 `GET /pg-preview/r30a/readiness` 和 `POST /pg-preview/r27/workflow`。全部仍为 localhost 限定、显式只读预览；**不向正式业务表写 dispatch_plans/routes/route_stops、不扣减库存。**

## 如果你已经有人工填写的实际资料

**不要执行 R30-A 的 `-Apply` 演示补录！** 使用 `docs/r24_csv_templates`、`data/pg_r27_templates/work_operations.csv` 的人工业务数据导入流程（见 R24、R27 文档），并在新备份后独立审核来源。R30-A `readiness` 仍能检查全部资料，并连接现有求解器；但旧扩展表没有可信外部来源凭证，网页只能标为“人工/历史录入，未独立核实”，不能宣称现场实测。

## 已验证 / 尚未验证

- 新增结构适配、生成-校验-拒绝覆盖-拒绝基础漂移以及来源判别：离线专项测试通过；原有 R21–R29 的相关测试复核通过。
- 环境不提供本机 `coldchain_db` 和 OR-Tools/SimPy，所以没有在这里证明**Windows PostgreSQL 事务性导入成功、现场数据求解可行、全量 React 构建成功或实际 3D 帧率**。这些必须以你自己的 Windows 运行结果为准。
- 阶段 A 不包含异常事件重调度、AI Agent 工具调用和新 3D 特效，留给 R30 B/C。
