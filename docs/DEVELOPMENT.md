# 双人开发与构建规范

Git初始化、日常上传、对方复验、冲突与恢复的复制命令见 [Git协作手册](GIT_COLLABORATION.md)。

本文件以 `merged/` 为工程根；交付给合作方后以解压根为工程根，不依赖父目录 DSH 工程。先读 `COLLABORATION_SPLIT_20261021.md`、`OWNERSHIP.json` 和最新 `docs/devlog/entries/`。旧 README 的 skeleton、501、SimPy 4.1.1 说明是历史信息，不是当前安装要求。

## 环境与安装

Python 必须为 3.12.x（backend/pyproject.toml 限定 >=3.12,<3.13）。Node 使用 22.12+ 的受支持版本，本轮本机为 24.18.0 / npm 11.16.0。Python 依赖严格使用 `backend/requirements-lock.txt`，前端使用 `frontend/package-lock.json`；不要以 requirements-optional.txt 替代完整锁。

在工程根 PowerShell 执行，每一步成功才继续：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
Push-Location frontend
npm ci
Pop-Location
```

不提交虚拟环境、node_modules、dist 或真实密钥。锁文件变更单独交接，由集成负责人核验安装与回归，不能通过 npm install 随意升级双方依赖。

## 类型、变量与单位的唯一来源

| 内容 | 唯一来源 / 使用方式 |
| --- | --- |
| 业务 DTO、字段、默认值、空值、枚举 | `backend/app/contracts/`；跨模块直接导入，不能复制另一个 Order/Vehicle |
| Python 模块边界 | `backend/app/ports/`；application 不直接装配 adapters，组合根待完成 |
| 契约版本 | `backend/app/contracts/common.py::CONTRACT_VERSION`；生成 contracts/VERSION 与前端 contractVersion.ts |
| HTTP Schema | `contracts/openapi.json`，由 scripts/export_contracts.py 导出 |
| 前端业务类型 | `frontend/src/client/generated.ts`；appTypes.tsx 只保留类型别名及展示模型 |
| 请求客户端 | `/api/v1` 用 client/api.ts；本机 `/local-pg/pg-preview` 用 features/postgres/api.ts |
| 显示格式 | `frontend/src/lib/format.ts`，禁止在提交前把展示单位直接传回后端 |
| UI 配色 | `frontend/src/styles.css` 的语义变量；中性灰、状态绿/琥珀/红，无蓝紫色及渐变 |

Python/JSON 字段保持 snake_case；TS 局部变量可 camelCase，但不改接口字段名。ID 不透明，遵守 `^[a-z][a-z0-9]*_[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`。时间 `_s` 为场景整数秒，预算 `_ms` 为毫秒，距离 `_m` 为米；重量、体积按具体契约字段单位，不能直接复用准备包的小数数值。导入转换以 `scripts/import_preparation_bundle.py` 为准：需求向上取整、容量向下取整；无法表达的语义记录在 `data/scenarios/prep_import_report.json`。

ContractModel 禁止额外字段、对象冻结、拒绝 NaN/Infinity；缺字段、null、0 含义不同。新字段是否兼容取决于必填性、语义和旧端 extra=forbid，不能宣称一律兼容或一律破坏。`has_solution` 与 feasible/optimal 必须一致；校验 passed 需要实际检查规则且无违规。

本机 PG 子应用仍有独立手写 TS 响应类型，不宣称已经全部自动生成。改该 API 必须同时更新 `features/postgres/api.ts` 和相关调用及后端测试；它的 OpenAPI 地址是 `/local-pg/openapi.json`。后续统一生成另列契约任务，不能悄悄合入主 API。

## 契约变更与编译顺序

公共变更先写 contracts/changes 的字段、语义、消费者及兼容影响，由乙方集成负责人串行修改。修改版本源后执行：

```powershell
.\.venv\Scripts\python.exe scripts/export_contracts.py
Push-Location frontend
npm run contracts:generate
npm run contracts:check
npm run typecheck
npm test
npm run build
Pop-Location
.\.venv\Scripts\python.exe scripts/export_contracts.py --check
```

不得手改 generated.ts、contractVersion.ts、openapi.json、schemas.json、VERSION。构建前只检查漂移，发现不一致直接失败，不隐式重生成。TypeScript 使用 strict、ES2022、ESNext/Bundler、react-jsx、noEmit；类型检查后由 Vite 生成 `frontend/dist/`。Python 不需要独立编译步骤，pytest 导入并执行代码。

更新文件后运行 `python scripts/build_file_map.py`。完整交接验证（使用本工程虚拟环境，输出必须为新目录）：

```powershell
.\.venv\Scripts\python.exe scripts/verify_delivery.py --out-dir ../tmp/handoff-20261022-01
```

该入口运行依赖一致性、两端契约检查、准备数据检查、全部后端测试、前端现有专项测试和生产构建、文件清单与架构检查。每项保存命令、目录、退出码、日志 SHA256；任何失败整体返回非零。现存架构问题也不豁免，不将部分通过写成全部通过。`npm ci` 属安装步骤，需单独保存安装日志。Node 专项检查不是浏览器端到端测试。

## 启动与外部服务

终端一在工程根：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

终端二进入 frontend：`npm run dev`，访问 http://127.0.0.1:5173。Vite 严格使用 5173，将 `/api` 与 `/local-pg` 代理至 8000。端口占用时停止冲突服务或由两人同步修改配置，不静默换端口。生产静态文件需由部署服务器设置相同反向代理；Vite build 本身不会部署后端。`npm run preview` 仅用于静态产物预览，不作为完整业务联调入口。

`.env.example` 仅说明变量，本工程不会自动加载它；通过当前终端环境或已有启动脚本传入。只使用后端 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL；数据库使用 PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD。PG_DEMO_ENABLED=1 才开启本机预览，PG_PREVIEW_WRITE_ENABLED 默认 0；打开写入是单独操作，禁止为构建验收自动开启。

需要模型与数据库的演示用 `backend/start_pg_r30c_local.ps1`，无数据库演示选择 -DemoOnly；此脚本有自身环境选择规则，执行前阅读其参数，不混用旧副本 venv。正常构建及合成场景回归不要求密钥。数据库迁移在 backend/migrations 与专项文档中按任务明确执行，常规构建不自动迁移。真实 PG/DeepSeek 调用须单独记录实测，测试替身不能证明它们已连通。

## 交付与故障定位

任一人接收补丁先核对基线哈希；只替换清单文件，旧哈希不符即冲突，不整包覆盖。交付附任务、路径、修改前后 SHA256、契约版本、环境版本、命令和原始结果、限制与待对方处理项。不把双方互验写成自己的实现自测。

契约漂移：检查源变更后按上述顺序生成；缺 Python 包：确认使用本工程 .venv 和锁；缺 Rollup 原生组件：在本机重新 npm ci，不复制其他平台 node_modules；后端离线：检查 8000 进程；PG 503：检查显式开关和连接配置；求解超时/不可行：保留实际状态，不改成功字段。
