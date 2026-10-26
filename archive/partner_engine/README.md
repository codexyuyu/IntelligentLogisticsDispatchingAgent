# 合并工程 · 开发入口（2026-10-22）

Git同步、上传和问题处理的复制命令见 [双人Git协作手册](docs/GIT_COLLABORATION.md)。

运行基线 R30-E + DSH 准备数据。当前双人分工见 [协议 v2](COLLABORATION_SPLIT_20261021.md)，安装、共享变量、契约生成、编译、启动、联调和交付规则统一见 [DEVELOPMENT.md](docs/DEVELOPMENT.md)。完整验证使用 `scripts/verify_delivery.py --out-dir <新目录>`，具体结果见最新增量日志。

下方保留发行历史，旧 skeleton/501 与依赖版本说明不作为当前构建依据。剩余业务：R05、R08、R09 统一、版本化确认与组合根；构建通过不表示这些已完成。

---

# R30-E · 异常处置与业务差异证据增强（2026-10-21）

直接继承已经通过用户 Windows 运行检查的 R30-D，增强四类异常下的**逐单变化、车辆后续预计送达、仓储作业中断/取消/重排、新旧方案证据**，并将核验后的差异摘要提供给 DeepSeek。原有 CP-SAT / OR-Tools、数据库结构及 3D 主体不变；全部结果仍是只读预测，不是实际派车。详见 [R30-E 使用与验收说明](docs/R30_STAGE_E_EXCEPTION_OPERATION_ENHANCEMENT.md)。

---

# R30-D · 仓储协同后端增强（2026-10-20）

继承 R30-C DeepSeek AI Agent，新增独立冷链仓储业务规则审计、仓储作业与装车就绪一致性验证，以及真实求解明细的 AI 工具返回。**数据库不写入、原算法和前端不重构；当前库容长期占用、预冷、换批仍未建模。** Windows 启动方式不变，参见 [R30-D 使用和验收说明](docs/R30_STAGE_D_WAREHOUSE_BUSINESS_ENHANCEMENT.md)。

---

# R30-C · DeepSeek AI 智能体组会 Demo（2026-10-20）

新增 DeepSeek Function Calling + FastAPI 三种只读工具 + React 对话入口 + 原 3D 回放联动。**现有 R30-B、R30-A 算法和数据历史保留。** 最快运行：进入 `backend` 执行 `powershell -ExecutionPolicy Bypass -File .\start_pg_r30c_local.ps1 -DemoOnly`，输入 DeepSeek Key；进入 `frontend` 执行 `npm ci; npm run dev`。详见 [R30-C 完整启动与演示手册](docs/R30_STAGE_C_DEEPSEEK_DEMO.md)。交付代码未经过真实 DeepSeek/Windows 联网验收，API 余额、OR-Tools 和 PostgreSQL 需用户本机确认。

## R30 阶段 B · 异常事件与动态重调度（新增只读预览，2026-10-20）

直接继承 R30-A，新增 **车辆途中故障 / 配送延误 / 仓储资源故障 / 库存批次隔离** 四类异常，冻结异常时刻前已发生的事件，利用已有 CP-SAT 与 OR-Tools 计算可行的仓储/运输后缀，独立统计交付/未服务，保存原方案并提供新旧比较、异常后 3D 回放和 JSON 导出。不可行会明示，不允许已发车车辆瞬移、已送达重新派送或自动写减正式库存；在途货物无已验证转运能力时暂停而非假装成功。

**安装与 Windows 验收**：[R30-B 完整操作指南](docs/R30_STAGE_B_EXCEPTION_RESCHEDULE.md)。后端从 `backend` 执行 `powershell -ExecutionPolicy Bypass -File .\start_pg_r30b_local.ps1`，前端运行 `npm ci`、`npm run build`、`npm run dev`；先算 R30-A 基线，再在「单仓仓运闭环」的异常面板模拟。**此包未经真实 OR-Tools/PostgreSQL/Windows 验收；请先在本机确认运行，不是声称正式生产可执行系统。** 后面的 R30-A 及早期说明为历史阶段信息（其中“阶段 B 尚未实现”为当时描述）。

## R30 阶段 A · PostgreSQL → 仓储 CP-SAT → 运输 OR-Tools（最新）

保留 R29 已验收的 **WH001 单现役仓库**和历史路线；R30 阶段 A 新增本机业务资料生成、来源标记、备份后显式导入、PostgreSQL 联合求解和演示/人工录入严格区分。**目前新增的合成数据仅供演示，不是实测业务资料，默认不写数据库。** 完整运行与安全步骤：[`docs/R30_STAGE_A_POSTGRES_BUSINESS_DATA.md`](docs/R30_STAGE_A_POSTGRES_BUSINESS_DATA.md)。阶段 B/C（异常重调度、AI Agent）尚未实现。

> **R29 最新交付：单现役仓库安全迁移。** 将 V003/V004 归属 WH001，4 条历史路线保留原样；WH002 作为历史外键锚点继续物理保留，但从新的数据库调度读取与矩阵中排除，并禁止新业务引用。先备份再显式执行。详见 [`docs/R29_SINGLE_ACTIVE_WAREHOUSE_MIGRATION.md`](docs/R29_SINGLE_ACTIVE_WAREHOUSE_MIGRATION.md)。

> **R28 最新开发交付**：单仓仓运闭环新增订单级后端对账、全程计划/播放中进度拆分、PostgreSQL 只读诊断和真实编号的空白 CSV 工作清单。先看 `docs/R28_DATA_RECONCILIATION.md`；不自动合并 WH002、不补虚构业务资料。

# R27 · 单仓库仓运业务闭环版

新增 **智能调度 → R27 仓运业务闭环**：单仓演示可直接通过 CP-SAT → OR-Tools 产生统一仓库/车辆事件与 3D 回放；PostgreSQL 核验模式需要先安全统一单仓并补录 R24/R27 业务事实，绝不伪造或写入真实执行计划。参见 [R27 使用与数据补录说明](docs/R27_SINGLE_WAREHOUSE_CLOSED_LOOP.md)。

## R26 · 单仓库数字孪生与叉车作业

默认演示只使用一座配送中心，详情见 [`docs/R26_SINGLE_WAREHOUSE_DIGITAL_TWIN.md`](docs/R26_SINGLE_WAREHOUSE_DIGITAL_TWIN.md)。
R26 在左侧「仓储管理 → 3D 单仓数字孪生」新增精细 3D 仓内场景及 3 辆叉车作业回放。
Windows 后端使用 `backend/start_pg_r26_local.ps1`，历史 R25 可随时回退。
原 PostgreSQL 真实数据**不会自动迁移**；只读检查请用 `backend/check_single_warehouse_r26.ps1`，所有实库修改必须备份后显式执行。

# R25 · 流畅仿真回放 + 四车演示 + OSRM 3D 道路路线（2026-10-18）

**本版直接升级前端数字孪生**：重构每帧 WebGL 时钟与 12Hz UI 状态同步，减少场景无谓重建，按停靠时刻沿分段路线行驶；在数字孪生驾驶舱/仿真回放提供可选择的四车展示与跟车镜头；PostgreSQL 路线预览增加 3D 车辆回放，配置 OSRM 时显示真实路网几何，否则清楚标注为示意道路。**四车展示路线不是求解器结果，不是实际运输任务**。已完成 R24 冷链扩展表的用户不需要重复迁移。

Windows：新解压目录下 `backend` PowerShell 运行 `powershell -ExecutionPolicy Bypass -File .\start_pg_r25_local.ps1`（修正了 Windows PowerShell 5.1 的中文脚本编码）；另在 `frontend` 运行 `npm ci`、`npm run build`、`npm run dev`。打开 http://127.0.0.1:5173 → 「仿真回放」→ 「四车演示」，或在「PostgreSQL 实库调度」求解完成后打开「3D 道路回放」。OSRM 可选 `-OsrmBaseUrl 'http://127.0.0.1:5000'`，前提是路网服务与地区道路数据真实可用。详情 [R25 指南](docs/R25_TWIN_REPLAY_FLEET.md)。原 R24 功能全部保留，仓库详细内景与叉车计划放 R26。

---

# R24 · PostgreSQL 冷链补录 + OSRM 道路估计 + 仓运 ready_at 适配（2026-10-17）

R23 已由用户 Windows 实机验收成功。R24 增加**可选 OSRM road Table/Route**、增量六类冷链业务表与 CSV 补录、从数据库读取真实体积/批次/班次/装车时间窗并调用原 R20 路由求解器、React 模式切换/缺口提示。旧模拟模式、R22 历史归档、原业务七表均保留；所有输出仍为**不可执行的模拟方案**。

后端 `backend/` PowerShell：`powershell -ExecutionPolicy Bypass -File .\start_pg_r24_local.ps1`；首次经备份并确认后可加 `-CreateR24Tables` 创建空扩展表；OSRM 需额外 `-OsrmBaseUrl 'http://127.0.0.1:5000'` 且相关区域路网服务已启动。前端 `frontend/`：`npm ci`、`npm run build`、`npm run dev`。完整操作与范围：[R24 指南](docs/R24_POSTGRES_OSRM_COLDCHAIN.md)。未录入真实业务字段时，`verified_r24` 预期不可用；旧 R23 正常可用。

---

# R23 · PostgreSQL 数据接入 React 调度台（2026-10-17）

**新增实用页面**：React 左侧“PostgreSQL 实库调度”读取现有冷链订单/车辆，使用 R20 求解器进行明确标注的模拟路线预览；已校验预览在用户确认后通过 R22 独立表归档，并在网页内展示地图。原“订单与库存”“运输计划”页也显示 PostgreSQL 实库摘要，旧场景数据明确分离。**非可执行方案，不碰正式 `dispatch_plans`。**

启动：`backend` 下执行 `powershell -ExecutionPolicy Bypass -File .\start_pg_r22_local.ps1`；另在 `frontend` 下执行 `npm ci`、`npm run dev`，打开 http://127.0.0.1:5173 。R22 已创建的演示表无需重复创建。详细验收步骤、当前环境未完成的前端构建验证见 [R23 指南](docs/R23_POSTGRESQL_REACT_INTEGRATION.md)。

---

# R22 · PostgreSQL 模拟路线归档（2026-10-17）

R21 已由用户 Windows 实际验证成功：`ROUTING_SOLUTION`、独立校验通过、无未服务订单。R22 **新增真实功能**：用同一 R20 求解器重新求解后，将通过校验的**演示路线**写入独立 `public.pg_simulation_previews`，提供列表/详情/GeoJSON/只读地图。**不修改**历史业务调度表和正式算法；模拟方案**不可确认执行**。

最简操作：另解压本 ZIP → `backend` 目录 PowerShell → 第一次执行 `powershell -ExecutionPolicy Bypass -File .\start_pg_r22_local.ps1 -CreateDemoTable`；后续执行 `powershell -ExecutionPolicy Bypass -File .\start_pg_r22_local.ps1`；浏览器打开 http://127.0.0.1:8000/local-pg/docs ，测试 `POST /pg-preview/saved`。步骤及数据安全边界详见 [R22 归档指南](docs/R22_PG_SIMULATION_ARCHIVE.md)。旧 `start_pg_local.ps1` 保持只读方式启动。

---

# R21 · 现有 PostgreSQL → R20 订单/车辆读取和路径预览（2026-10-17）

**这一轮直接交付功能，不继续做规模实验：**同一 FastAPI 进程新增本机 `http://127.0.0.1:8000/local-pg/docs`，可以实时读取 PostgreSQL 的订单/车辆，并以用户明确确认的模拟假设，将真实数据转换为 R20 原有 `RoutingRequest`，调用**未改动的** `OrToolsRoutingSolver` 和独立运输校验；结果只预览，不会写回旧数据库。受缺失的体积、道路行驶时长、仓储交接和车辆班次限制，**还不是正式可执行调度方案**。

**最少操作：**解压 ZIP → 打开 `backend` 的 PowerShell → `python -m pip install -r requirements.txt`（当前环境缺依赖时才做）→ `powershell -ExecutionPolicy Bypass -File .\start_pg_local.ps1` → 打开上述浏览器地址。数据库密码只在本机窗口交互输入；程序默认仅绑定 127.0.0.1。详见 [R21 数据库集成指南](docs/R21_POSTGRES_R20_INTEGRATION.md)。R17～R20 的算法/证据保持原样，不重复实验；旧计划不修改。

---

# 项目目录整理说明（2026-10-16）

**这是 R20 当前工程的目录整理交付包，仅调整历史资料和辅助目录位置；正式 `backend/`、`frontend/`、`contracts/`、`data/`、`benchmarks/`、`scripts/` 路径保持不变，不修改调度算法与冻结实验数据。**

一级目录固定为 `backend/`、`frontend/`、`contracts/`、`data/`、`benchmarks/`、`scripts/`、`docs/`、`infra/`、`archive/`（9 个）。

- `infra/deploy/`：原部署配置；`infra/platform/`：未来智能体平台接入预留。
- `archive/legacy/`：旧 `algorithm-service`、Spring Boot、Vue3 和 `legacy-reference`；`archive/reference_demos/`：历史演示探针；`archive/releases/`：原 `artifacts` 的旧版交付 ZIP 和 SHA256。
- 出于便携性，不附带可重新安装的 `frontend/node_modules`、可重新构建的 `frontend/dist`、Java `target` 与 Python 缓存。前端在 `frontend/` 执行 `npm ci` 后再 `npm run dev` 或 `npm run build`。
- 根目录历史文档中的旧目录名称属于**当时的记录**，不要作为当前文件位置使用。迁移路径、证据保留范围、验证结果详见 [目录整理与交付说明](docs/PROJECT_LAYOUT_R20.md)。

源码轻量打包：`python scripts/package_demo.py`；**包含完整历史目录与旧版 ZIP 的打包**：`python scripts/package_demo.py --include-archive --output R20_COLD_CHAIN_COMPLETE.zip --top-level R20_COLD_CHAIN_REORGANIZED`。前者不包含已归档旧代码和历史发行 ZIP，后者包含。

---

> **最新增量 R20：B-04 异常事件扩充到 3 种（车辆延误 / 月台不可用 / 货物隔离），真实求解器已实测；月台封锁会把受影响车辆推后到重开时刻，赶不上的订单显式记录而不丢弃。见 [docs/B04_EVENT_TYPES_R20.md](docs/B04_EVENT_TYPES_R20.md)。R19 三策略结果见 `benchmarks/b04/r19_accepted_v2/`；R17 与 R18 已验收证据勿重新运行。**

# R19/R20 异常处置与仓运协同正式入口

**当前交付版本：R20（基于 R19 三策略对照）**。B-04 支持的异常事件见 [B-04 事件类型说明](docs/B04_EVENT_TYPES_R20.md)，B-04 三策略等预算对照见 [R19 指南](docs/R19_B04_RESCHEDULE_GUIDE.md)，B-06 多场景同预算 A/B 见 [R18 指南](docs/R18_B06_MULTISCENE_GUIDE.md)，R17 深度协同原理与验收见 [R17 指南](docs/R17_B03_DEEP_JOINT_OPTIMIZATION_GUIDE.md)。下方是早期工程骨架的历史 README，部分“尚未实现”描述已过时；以 R20/R19/R18 指南和实际代码为准。

---

## Current B-05 runtime note

B-05 `/api/v1/simulations` is wired to the real SimPy adapter. Install `simpy==4.1.1` in the runtime environment. The simulator generates an isolated simulation snapshot, creates a B-03 baseline plan, injects events in deterministic time order, and delegates local replanning to B-04.

# demo · 冷链物流调度项目协作骨架

**交接基线：2026-09-10。这是可启动的工程骨架，调度业务尚未实现。** 用户负责 A＋C，B 负责运输/矩阵/仿真，前端全部交给用户侧 Codex。

## 交给 Codex 的第一句话

- 用户侧：读取 `AGENTS.md`、`DEV_LOG.md` 开头与 `docs/handoff/AC_CODEX.md`，按当前公共契约实施 A＋C 和前端，保持 B 的模块边界，每次工作记录增量日志。
- B 侧：读取 `AGENTS.md`、`DEV_LOG.md` 开头与 `docs/handoff/B_CODEX.md`，从 B01 开始，仅实施 B 所有权内模块，复用 contracts/ports，公共变更走提案并交 AC 集成。

两个 Codex 从同一份 demo.zip 解压开始。后续建立同一个 Git 仓库、各自分支交付；合并提交或限定文件补丁，不能反复互相覆盖整个文件夹。包内 PACKAGE_MANIFEST.json 记录逐文件哈希用于核对原始基线。

## 阅读顺序

1. [开发日志与统一接口方法](DEV_LOG.md) —— 命名、权威来源、改动顺序和日志要求。
2. [模块所有权](OWNERSHIP.json) 与 [完整文件清单](FILE_MAP.md)。
3. [共享契约](contracts/README.md)、[命名与单位](docs/NAMING.md)。
4. [A＋C 的 Codex 说明](docs/handoff/AC_CODEX.md) / [B 的 Codex 说明](docs/handoff/B_CODEX.md)。
5. [四周路线](docs/ROADMAP.md)、[架构](docs/ARCHITECTURE.md)、[验证范围](docs/VERIFICATION.md)。
6. 现行专项指南：[B-04 事件类型](docs/B04_EVENT_TYPES_R20.md)、[R19 三策略对照](docs/R19_B04_RESCHEDULE_GUIDE.md)、[R18 多场景 A/B](docs/R18_B06_MULTISCENE_GUIDE.md)、[R17 深度协同](docs/R17_B03_DEEP_JOINT_OPTIMIZATION_GUIDE.md)。
7. [证据目录说明](benchmarks/README.md)（`*_accepted/` 是证据，`*_runs/` 只是过程输出）；已被取代的历史文档集中在 [docs/history/](docs/history/README.md)，仅供参考、不是当前实现依据。

## 目录

```text
backend/app/
  contracts/       共享类型唯一来源，AC 集成维护
  domain/          纯业务规则，运输规则归 B
  ports/           仓储/运输/矩阵/仿真/存储/模型接口
  application/     AC：协调、确认、事件、影响分析、合同网
  adapters/        B：routing/matrix/simulation；AC：其余
  api/             AC：统一 HTTP 路由及错误
  bootstrap.py     AC：组合根
  worker.py        AC：受限工作进程预留
backend/tests/     骨架/契约测试与分域业务测试入口
backend/migrations/ 数据库迁移入口
frontend/src/      Codex：7 个模块页、共用组件、生成客户端
contracts/         生成的 OpenAPI/schema、样例、变更提案
data/              共用场景与 B 的运输/仿真数据
benchmarks/        仓储、运输、仿真、联合、模型评测入口
docs/              交接、规则、路线、增量日志；docs/history/ 为已被取代的历史文档
infra/platform/wanwu/    后续可选接入
infra/deploy/      本地数据库配置与部署预留
scripts/           导出、漂移检查、清单、打包
archive/reference_demos/   已有教学探针，分钟单位，非业务契约
```

## 本地启动（Windows）

需要 Python 3.12、Node 22.12+。压缩包不带虚拟环境/node_modules；依赖首次安装联网。解压后在 demo 目录：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

另开终端进入 frontend：

```powershell
npm ci
npm run dev
```

访问 http://127.0.0.1:5173，点击“检查后端连接”。健康接口 `/api/v1/health` 返回 `mode=skeleton`；其余 9 个业务接口目前返回 501。Swagger 在本地 8000 的 `/docs`，也可离线查看 contracts/openapi.json。

核心启动不需要数据库、模型密钥、OR-Tools 或 SimPy。相关适配器实现时再按 backend/requirements-optional.txt 安装并验证锁版本；当前 optional 文件不是已验证的完整依赖锁。

## 验证与打包

在 demo 根目录使用刚创建的 Python 环境运行（下列 python 指向该环境）：

```powershell
python scripts/export_contracts.py --check
python scripts/check_project.py
python -m pytest backend
```

前端目录运行 `npm run contracts:check`、`npm run build`。修改契约后先 `python scripts/export_contracts.py`，再前端 `npm run contracts:generate`。新增文件后 `python scripts/build_file_map.py`。

```powershell
python scripts/package_demo.py
```

默认输出 archive/releases/demo.zip 和 SHA-256；ZIP 顶层统一是 demo/。包只包含源码、说明、锁文件、样例和校验清单，不包含凭据、环境、依赖缓存或构建产物。

本次包覆盖目前规划的所有功能域和公共接口骨架，后续具体私有函数/迁移/测试文件随实现新增，并写所有权与日志。不能把“预留文件齐全”理解为全部功能已完成。

## B-01 migration status

The legacy `archive/legacy/algorithm-service` remains intact as a regression baseline. The proven B-01 CP-SAT capability is now also represented in the unified `backend/app/adapters/warehouse/cp_sat_scheduler.py` under the shared `WarehouseScheduler` port. The unified adapter intentionally implements only semantics expressible by the current shared contracts; richer legacy batch/order/temperature/capacity semantics remain in the legacy service until an explicit contract upgrade.
