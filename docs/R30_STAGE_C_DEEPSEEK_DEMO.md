# R30-C DeepSeek AI Agent · 2026-10-20 组会冲刺交付

## 1. 本阶段具体交付

在 **R30-B 原工程** 内新增独立 R30-C 面板，保留原有 React、FastAPI、PostgreSQL、CP-SAT、OR-Tools、异常处置和 3D 回放；没有建立第二个计算服务，也没有写入生产数据库。模型服务只在后端访问。组会优先使用内置单仓合成场景，求解仍由真实 CP-SAT / OR-Tools 调用完成；如果切换 PostgreSQL 来源，需数据库与 R30-A 的扩展业务字段准备就绪。

新增本机路由（需 `PG_DEMO_ENABLED=1`，本机 127.0.0.1 才能使用）：

- `GET /local-pg/pg-preview/r30c/status`：返回模型配置状态，**不**返回密钥。
- `POST /local-pg/pg-preview/r30c/chat`：调用 DeepSeek `deepseek-flash`，支持经过白名单验证的 `get_business_status`、`generate_joint_plan`、`simulate_exception` Function Calling，返回受控解释和后端校验结果。限制参数和调用轮次；**不能执行任意 SQL / Shell / 方案确认 / 库存修改**。
- `POST /local-pg/pg-preview/r30c/quick`：仅为 API 临时故障的组会保底，直接调用同一后端工具，返回 `mode: direct_algorithm_fallback_not_ai`，**不应宣称已经运行了 DeepSeek**。

在 React 「智能调度」组导航内新增「AI 智能调度助手」：模型状态、选数据来源、常用提示词、聊天对话、真实工具证据、失败提示、手动快捷入口以及「打开现有 3D 仓运回放」按钮。回放数据仅通过浏览器 `sessionStorage` 一次性传入原 `closedLoop` 页面，不发起正式调度、数据库写入或设备操作。原 R30-B 异常面板也被保留。

## 2. 运行前的环境要求

在已安装、能运行 R30-A/B 的 **Windows** 上操作；建议先把本工程解压到新的路径，**不要覆盖**验收成功的旧工程。

- Python 与依赖：在 `backend` 下执行 `python -m pip install -r requirements-lock.txt`。确保 OR-Tools、SimPy、psycopg 已安装，Python 与 OR-Tools wheel 兼容。
- Node 与依赖：在 `frontend` 下执行 `npm ci`。本 ZIP 可能附带上版的 Windows node_modules 以便复用，但**以 npm ci 补齐锁定依赖为准**。
- DeepSeek API Key：用户本地已有，**不要通过聊天或截图提交**。在本机 PowerShell 启动脚本的安全提示中输入。API 费用与访问依赖 DeepSeek 账户与网络。
- PostgreSQL：仅切换“PostgreSQL R30-A 数据”时必须正常连接 `coldchain_db` 并已按 R30-A 导入合成演示资料。不使用该来源时可用 `-DemoOnly` 启动，不需要 PostgreSQL 密码。

### 方式 A：快速开箱演示（组会优先，内置场景）

**窗口 1**：进入工程的 `backend` 目录，执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_pg_r30c_local.ps1 -DemoOnly
```

出现提示时输入 DeepSeek Key（隐藏输入，环境变量仅在该服务进程生效）。等待出现 `Uvicorn running on http://127.0.0.1:8000`。

**窗口 2**：进入工程的 `frontend` 目录：

```powershell
npm ci
npm run build
npm run dev
```

打开 `http://127.0.0.1:5173`，点侧边栏「智能调度 → AI 智能调度助手」，选“内置单仓合成场景”，检查模型状态是“已配置密钥”。

### 方式 B：读取 PostgreSQL R30-A 资料

在 `backend` 目录运行（无 `-DemoOnly`），提示时输入 PostgreSQL 密码与 DeepSeek Key：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_pg_r30c_local.ps1
```

前端选择“PostgreSQL R30-A 数据”。若缺表、来源摘要变化或业务数据未齐，请先在原 R30-A 页面查看只读诊断；**禁止自动补造或修改正式数据**。

## 3. 下周一组会建议的演示脚本（约 5 分钟）

1. **先确认页面连通**：模型状态为已配置；来源显示合成场景，不把演示数据叫企业真实数据。
2. **业务资源查询**：输入“查询现有订单、车辆与仓库资源”。展示 DeepSeek 产生的工具调用证据，明确未求解时不出现虚假的成功声明。
3. **联合调度**：输入“为 20 单冷链订单执行仓储与运输联合调度”。等待计算完毕，确认工具证据中 `R28 reconciliation: passed`、`database_mutated: false`；点击「打开现有 3D 仓运回放」，展示仓内作业、装车与车辆配送。
4. **异常处理**：返回 AI 页面，输入“V002 发生途中故障，请运行异常重调度并说明受影响订单”。合成场景内部车辆 `veh_2` 的 V002 字面别名仅用于 Demo；实库采用 `veh_V002`。检查后端 `R30B suffix_accounting: passed` 和未服务原因，打开「原方案/重调度预览」对照。
5. **保底方式**：模型外网异常时直接点“真实联合调度”，这使用同一真实求解器但属于手动演示，**不能称为 AI Agent 推理**。

建议将真实 Demo 的两条成功链路截图保存。组会前三次成功后避免临时更换 Python、Node、依赖或核心业务数据。

## 4. 必要安全核对与局限

- 后端通过 `DEEPSEEK_API_KEY` 环境变量读取密钥，不发给模型工具、前端页面或结果导出，不存在硬编码 Key；HTTP 调用使用 `https://api.deepseek.com/chat/completions`。
- AI 工具只有三种，数据库相关行为只读。原仓储/运输结果仍要求原后端独立校验、R28 对账，异常由 R30-B 检查；失败不会被改写为成功。
- Agent 只提供 **请求/生成可校验预览**，不能对正式业务数据库做不可逆写入。异常前已完成订单冻结，故障车载货物不能瞬间迁移；不可行时可返回未服务订单。
- 深度 AI API、Windows 环境、真 PostgreSQL、OR-Tools **本沙箱未完成线上/实机验证**（沙箱无密钥，无 PostgreSQL，缺 OR-Tools，前端包内 npm 依赖不完整）；新增端点使用 Mock DeepSeek 对话与模拟 R27/R30B 下游进行回归。
- 时间窗、库存、路线为已有算法约束；SimPy/3D 展示是仿真，不能称为真实 GPS/设备遥测，也不能声称道路拥堵由真实交通服务获取。
- 可用 OpenAPI 中 `local-pg/docs` 查看 R30-C 新路由。与原 `/api/v1` 合约隔离，旧 TS OpenAPI 不受影响。

## 5. 常见错误

| 提示 | 处理方法 |
|---|---|
| DeepSeek Key 未配置 | 停止后端、重新运行 R30-C PowerShell 安全输入脚本 |
| DeepSeek HTTP 401/403/429 | 检查 Key 权限、账户额度、API 网络。不要截图泄露 Key |
| R27/异常报 OR-Tools 缺失 | `python -m pip install -r requirements-lock.txt`；注意使用运行服务时的同一 Python |
| Postgres unavailable | 用 `-DemoOnly` 先演示合成场景，后检查本机 17 版本数据库/密码 |
| npm/vite 无法启动 | 在 `frontend` 中执行 `npm ci`，然后 `npm run build`，不要直接复用缺失依赖的其他平台 node_modules |
| 响应有解释但没有工具记录 | 不能声称真实求解，改为明确要求 AI“实际调用工具执行”或用手动算法按钮 |
| R30-B 故障无可行转运路线 | 这是可接受的真实约束结果，重点展示已完成任务冻结与“明确未服务” |

## 6. 项目交接和优先级

下一周组会前不建议增加多智能体协商、OSRM、实时设备接入、数据库大迁移、3D 重制、S50/S100 实验；优先在 Windows 验证上述 2～3 个代表性演示操作，保存一组截图与 JSON 即可。
