# DSH 插件最小环境安装与验证报告

- 日期：2026-10-20（America/Los_Angeles）
- 项目根：`D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`
- 任务性质：独立工具环境配置。未开展业务开发，未升级 DSH 主程序，未修改 apps/packages/业务 scripts/tests、`uv.lock`、`OWNERSHIP.json` 或官方 Gate 记录。
- 本报告不构成任何业务 Gate 结论。

## 1. 结论

1. **Context7 已在当前活动的 `desktop` profile 中真实可用。** 复用宿主自带的 `@deepseek-ai/dsh-mcp-client@0.2.1-rc.2`，仅新增一个 profile patch 条目；`resolve-library-id`、`query-docs` 均已在当前 DSH 会话内成功调用，错误输入、超时、DSH 重启后恢复也已验证。
2. **BrowserSkill 插件本体已加载，工具可用；真实页面操作已在临时 Chrome 环境中验证通过。** 发现并修复了明确兼容缺陷：原 `bsk 0.2.1` 不支持插件 0.3.2 所需的 `bsk session request`，已升级到官方 `bsk 0.3.3`；扩展 0.3.3 仅在临时 Chrome 中加载验证。
3. **仍有一个外部交互条件未完成：** BrowserSkill 扩展尚未安装进你日常使用的 Chrome/Edge。Chrome 应用商店下载端点在本机网络下不可达，安装扩展需要浏览器内交互。临时浏览器验证不替代该永久安装。
4. **项目锁定版本（FastAPI/Pydantic）未被 Context7 收录。** 已明确记录未收录事实，并回退到对应版本的官方源码与 PyPI 元数据；没有把非版本化文档冒充为锁定版本文档结论。

## 2. 实际宿主、profile 与配置来源

| 项 | 实测值 |
| --- | --- |
| 实际启动的宿主 | DeepSeek Harness Desktop（Electron） |
| 版本 | `0.2.1-rc.2` |
| 构建 commit | `332895e0f7c9d4dbfb29729f5eb367fa263ff986` |
| 可执行文件 | `C:\Users\30382\AppData\Local\Programs\DeepSeek Harness\DeepSeek Harness.exe` |
| 运行时目录 | `...\resources\app.asar\dsh`（ASAR 内） |
| `DSH_HOME` | `C:\Users\30382\.dsh` |
| 活动 profile | `desktop`（`DSH_PROFILE=desktop`） |
| profile 目录 | `C:\Users\30382\.dsh\profiles\desktop` |
| 配置来源 | `package.json` 的 `dsh.profile.bundles`、`cordis.yml`（空入口列表）、`cordis.patch.yml`（用户 patch 层）；无 home 级 `cordis.patch.yml` |
| Web GUI | 启动时为 `http://127.0.0.1:53944`；任务中 DSH 重启后为 `http://127.0.0.1:55283` |
| Node / pnpm（宿主运行时） | Node `24.21.0` / pnpm `11.28.5`（`resources/runtime/versions.json`） |
| 当前 shell 的 Node / pnpm | Node `24.18.0` / pnpm `10.34.5` |

说明：

- `dsh --profile desktop` 被宿主主动拒绝（`profile "desktop" is managed exclusively by the Electron application`），这是设计约束，不是安装失败。因此配置通过 profile 的 `cordis.patch.yml` 写入，由 DSH HMR 热加载；没有绕过该保护。
- 任务期间 DSH 桌面进程实际退出并重启过一次（Web 端口从 53944 变为 55283）。重启后 Context7 工具仍可调用，说明配置已持久化，不依赖热加载残留。
- 现有模型、账户认证、会话和插件均保留。未读取、复制或输出 `.credentials.yaml` 内容。

### 2.1 已声明/已加载的插件（未改动项只做盘点）

| 组件 | 版本 | 状态 |
| --- | --- | --- |
| `@deepseek-ai/dsh-base` / `dsh-web-app` | `0.2.1-rc.2` | 宿主自带，已加载 |
| `@liustack/modlens` | `3.26.5` | 已加载（`modlens_read_image` 等） |
| `@liustack/modsearch` | `5.10.5` | 已加载（`web_search`/`read_page`/`x_search`） |
| `@nanmicoder/dsh-agent-teams` | `0.1.22` | 已加载，未启动自动派发 |
| `@wxg-prc-cpg/browser-skill-dsh-plugin` | `0.3.2` | 已加载；按 `lazyTools` 在调用 skill 后注入 `browser_*` |
| `dsh-better-sidebar` | `0.24.1` | UI 插件，未改 |
| `dsh-mobile` | `0.5.2` | UI 插件，未改 |
| `dsh-quota` | `0.14.3` | 已加载（`quota_refresh`） |
| `dshmarket` | `1.66.6` | UI/市场插件，未改 |
| `@deepseek-ai/dsh-mcp-client`（新增条目） | `0.2.1-rc.2` | 已加载，Context7 server 已连接 |

## 3. 修改路径、备份与恢复边界

### 3.1 实际修改的宿主文件

| 路径 | 修改 | 修改前 SHA-256 | 修改后 SHA-256 |
| --- | --- | --- | --- |
| `C:\Users\30382\.dsh\profiles\desktop\cordis.patch.yml` | 追加一个 `insert` 块，新增 `mcp-context7`（8 行） | `FA12D151B269DD27A0953C22D8DFB11D841F5B3BF03AB932DFC0BFAB01AAB03B` | `3FB1B02E40691B1EFA2E4AD0625C823706D7A952F35C8D2527EA573843D7E7DF` |
| `C:\Users\30382\.local\bin\bsk.exe` | 由 `0.2.1` 替换为 `0.3.3` | `A9D33E8030D3F91C43D8E4FFD97D9C48FC31F6E1C17C76F9DB50BF15A7834B7F` | `5F0AE749AD1A3F9E2E3627B237346DA3996CB2AFFDB48D9725976DF4AB083EC3` |

未改动（任务期间哈希保持不变）：

- `...\desktop\package.json`：`769369AD41E2672BAB721B563D98468F80319492527F934B3137D7012FD1167F`
- `...\desktop\pnpm-lock.yaml`：`6EDCBF499A8D5AF6A7A5B2B4C5E6913B51CDA4EDBB0B25B013EECB6B12D1B700`
- `...\desktop\pnpm-workspace.yaml`、`cordis.yml` 亦未变。

项目侧仅新增本报告目录；`uv.lock` 未改动（当前 SHA-256 `89F78A20A840955FCFE5A13435B6AAD9C5EBB09420123812C4728B9413FE86C5`）。

### 3.2 备份状态

任务开始时曾建立两处项目外备份：

- `C:\Users\30382\AppData\Local\dsh-toolchain-backups\2026-10-20\desktop-profile-pre-context7\`
- `C:\Users\30382\AppData\Local\dsh-toolchain-backups\2026-10-20\browserskill-cli-pre-update\`

**按用户 2026-10-20 要求，上述备份（含 `bsk-0.2.1.exe`）已全部删除；当前没有可用备份。** 修改前/后的 SHA-256 仍保留在 §3.1，供审计与手动逆向参考，但不能替代字节级备份。

### 3.3 恢复边界（无备份）

完全回滚已不可字节级执行；只能手动逆向：

1. 退出 DeepSeek Harness Desktop，确认 profile 宿主进程已停止。
2. 从 `cordis.patch.yml` 删除末尾 `- insert: ... mcp-context7` 块。
3. 若确需降级 bsk，只能重新从官方发布通道获取 0.2.1 资产；本地 `bsk-0.2.1.exe` 已删除。
4. 重新启动 DSH Desktop。

只撤销 Context7（保留 BrowserSkill 修复）：

1. 退出 DSH Desktop。
2. 删除 `cordis.patch.yml` 末尾的 `mcp-context7` insert 块。
3. 重启 DSH；`bsk 0.3.3` 保持不变。

## 4. Context7

### 4.1 复用而非新装

- 宿主运行时的 `@deepseek-ai/dsh-mcp-client` 已经是 `0.2.1-rc.2`，与宿主完全同版本，`dsh/package.json` 直接依赖它。
- 没有从 npm 安装 `latest`。npm 上该包 `latest` 标签仍是旧的 `0.0.1-rc.1`，`next` 才是 `0.2.1-rc.2`；若盲装 `latest` 会得到与 0.2.1 宿主不匹配的版本。
- 没有忽略 `peerDependencies`。该包 peer 要求全部为 `0.2.1-rc.2`（cordis `~4.0.5`），由宿主运行时满足。

### 4.2 新增配置

`C:\Users\30382\.dsh\profiles\desktop\cordis.patch.yml` 末尾：

```yaml
- insert:
    - id: mcp-context7
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: context7
        transport: streamable-http
        url: https://mcp.context7.com/mcp
        toolCallTimeoutMs: 60000
```

注意：在 patch 层新增条目必须使用 `insert:`；裸 `- id:` 只会覆盖已存在条目，新增会被忽略。本次首次尝试即因此未生效，改为 `insert` 后经 HMR 生效。

### 4.3 远程服务事实

| 项 | 值 |
| --- | --- |
| 端点 | `https://mcp.context7.com/mcp`（Streamable HTTP） |
| 协议版本 | `2025-06-18` |
| 服务端自报版本 | `4.4.3` |
| 认证 | 未使用 API key；端点匿名可用 |
| 验证时间 | 2026-10-20（America/Los_Angeles） |

服务端版本**未固定**，仅记录端点、协议和验证时间。

### 4.4 真实验证结果

| 探针 | 结果 |
| --- | --- |
| 初始化/连接 | 成功；MCP server instructions 与工具 schema 进入当前会话 |
| 工具列表 | `mcp__context7__resolve-library-id`、`mcp__context7__query-docs`；MCP 资源服务 `context7` 已注册 |
| 合法调用 1 | `resolve-library-id(libraryName="FastAPI")` 返回 `/websites/fastapi_tiangolo` 等候选 |
| 合法调用 2 | 无版本 `query-docs` 返回 FastAPI 请求体/`response_model` 示例，来源标注为 `fastapi.tiangolo.com` |
| 错误输入 | `query-docs(libraryId="/not-a-real-library/none")` → `Library ... not found` |
| 版本未收录 | `FastAPI 0.141.1` → `Version "0.141.1" not found ... This library has no versions`；`/fastapi/fastapi/0.141.1` → 仅有 0.115.13、0_116_1、0.118.2、0.122.0、0.128.0 |
| 版本未收录 | `Pydantic 2.13.5` 与 `v2.13.5` 均 → not found；可用版本为 v2.9.2、v1.10.18、v2.10.6、v2.11.0、v2.14.1 |
| 超时 | 临时增加 `toolCallTimeoutMs: 1` 的探针条目，调用返回 `Error: Request timed out`；探针条目已移除，最终配置只保留 60s 正式条目 |
| 重启 | DSH 桌面重启（端口 53944→55283）后再次调用 `resolve-library-id(Pydantic)` 成功 |
| 取消 | 未单独构造取消场景；超时/失败路径已覆盖（见上） |

### 4.5 项目锁定版本与文档回退

项目 `uv.lock` 实际锁定（非快照推断）：

- FastAPI `0.141.1`（`uv.lock` 第 81–82 行；sdist/wheel 含 SHA-256）
- Pydantic `2.13.5`（`uv.lock` 第 367–368 行）
- pydantic-core `2.46.5`（与 Pydantic 2.13.5 的 `pydantic-core==2.46.5` 依赖一致）
- 运行时 `.venv` 实测：FastAPI `0.141.1`、Pydantic `2.13.5`、pydantic-core `2.46.5`、Starlette `1.6.0`、Uvicorn `0.52.4`

Context7 **明确未收录**这两个锁定版本，因此没有可声称的“版本锁定 Context7 文档”。回退到官方版本化来源：

| 来源 | 版本化 URL | 结果 |
| --- | --- | --- |
| FastAPI 源码 docs | `https://raw.githubusercontent.com/fastapi/fastapi/0.141.1/docs/en/docs/tutorial/response-model.md` | HTTP 200；15,824 bytes；SHA-256 `40893B055F60AE81F2D149C6159EF98555CA05845D210A4C88F3824D66092BE1`；已保存到 `evidence/` |
| Pydantic 源码 docs | `https://raw.githubusercontent.com/pydantic/pydantic/v2.13.5/docs/concepts/models.md` | HTTP 200；59,238 bytes；SHA-256 `A5E71A28DEE897ECEC0D2BC2F80FF388622D59D3B8EB5497164947DBBCED9499`；已保存到 `evidence/` |
| PyPI FastAPI | `https://pypi.org/pypi/fastapi/0.141.1/json` | 版本存在；上传时间 `2026-07-29T17:18:04Z`；requires-python `>=3.10` |
| PyPI Pydantic | `https://pypi.org/pypi/pydantic/2.13.5/json` | 版本存在；上传时间 `2026-08-28T14:03:59Z`；`pydantic-core==2.46.5` |

版本化文档站路径（`https://pydantic.dev/docs/validation/.../2.13.5/...`）返回 404，因此采用 GitHub 对应 tag 的官方源码文档作为可复核来源。

## 5. BrowserSkill

### 5.1 初始状态与发现的兼容缺陷

- 插件已安装并声明：`@wxg-prc-cpg/browser-skill-dsh-plugin@0.3.2`（profile `package.json` 精确版本，`pnpm-lock.yaml` 已锁定）。
- skill 可加载，`browser_*` 工具按 `lazyTools` 在调用 `browser-skill` 后注入，说明插件本身已加载。
- 首次 `browser_session start` 失败：`bsk session request prepare failed: unrecognized subcommand 'request'`。根因是已安装的 `bsk 0.2.1` 不支持插件 0.3.2 的“可恢复启动”所需的 `bsk session request`。
- 这是明确兼容缺陷，不是权限或页面问题；因此只调整 `bsk` CLI，未升级插件。

### 5.2 修复动作

- 从 BrowserSkill 官方 GitHub Release 下载 `cli-v0.3.3` 的 `bsk-v0.3.3-x86_64-pc-windows-msvc.zip`：
  - 归档 SHA-256：`5ED6AA00E60C0538A637FEBAC6BFBC6A0BD55A11083CD90A987968CFF4BC0E02`
  - 解压后 `bsk.exe` SHA-256：`5F0AE749AD1A3F9E2E3627B237346DA3996CB2AFFDB48D9725976DF4AB083EC3`
- 旧 `bsk 0.2.1` 已被替换；原备份已按用户要求删除。替换后 `bsk --version` = `0.3.3`。
- 插件保持 `0.3.2`，扩展使用 `0.3.3`，CLI/daemon 协议 `1.3`，扩展协议 `1.3`，`version_skew=false`。

### 5.3 临时浏览器环境

由于 Chrome 137+ 已不再支持 `--load-extension` 加载未打包扩展，使用以下隔离方式：

- Chrome `155.0.8059.82`，`--headless=new`，独立的 `--user-data-dir`（临时目录），`--enable-unsafe-extension-debugging`。
- 通过 DevTools Protocol `Extensions.loadUnpacked` 加载官方 `ext-v0.3.3` 扩展目录（扩展 ZIP SHA-256 `10EF76E68F352893FA22DD4CCE2F1B96CB90ED957B815D656E13180D07D3C6EA`）。
- bsk daemon 以 `bsk daemon start --foreground` 在 DSH 管理的后台任务中运行（验证时 PID 32260，`ws://127.0.0.1:52800`），浏览器实例 `39a36a2f` 已连接。
- 验证完成后，该 daemon 按默认 10 分钟空闲策略于 2026-10-20T05:42 正常退出（exit 0，不是崩溃）。随后以 `--daemon-idle 12h` 重启，当前 PID 19760；默认策略下长时间闲置仍会自动退出，属预期行为。

### 5.4 真实验证结果

本地测试页：`http://127.0.0.1:8765/test.html`（独立临时目录，含表单、控制台错误与 404 请求）。

| 探针 | 结果 |
| --- | --- |
| 初始化 / 会话 | `browser_session start` 成功，会话 `josr`，Agent Window 正常打开 |
| 页面打开 | `navigate` 到本地测试页成功（`reached: load`） |
| DOM 观察 | `observe` 返回 `@e1` 文本框、`@e2` 下拉框、`@e3` 提交按钮 |
| 表单操作 | `fill @e1 "DSH Probe"`、`select @e2 ["sz"]`、`click @e3` 均成功；页面显示 `submitted:DSH Probe:sz` |
| 截图 | `screenshot` 成功，1258×746 PNG，已保存为 `evidence/browserskill-form.png`（SHA-256 `F9667781328C92C7E9208C33EF0CD94874D4BBC392744300F1AE908E0852B2FC`） |
| 错误取证（console） | 捕获 `probe-console-error: intentional` 与 favicon 404 |
| 错误取证（network） | 捕获 `/missing-endpoint` 404 及 `favicon.ico` 404 |
| 错误输入 | `fill @e999` → `ref @e999 unknown for tab ...` |
| 超时 | `navigate /slow` 且 `timeoutMs=2000` → `tool RPC timed out after 4s` |
| 清理/取消 | 超时后首次 `stop` 返回 `Background execution cleanup timed out`；重试 `stop` 成功并返回 request id，cleanup 可恢复 |
| 重启 | bsk daemon 由 0.2.1 停止并以 0.3.3 重启后，扩展自动重连；DSH 桌面重启后再次完成整套会话测试 |

### 5.5 未完成项与外部条件

1. **日常 Chrome/Edge 扩展尚未安装。** 临时 Chrome 验证不改变你日常浏览器的扩展列表。商店在浏览器内安装需要交互，且本机 `clients2.google.com:443` 连接超时，无法自动完成。
   - Chrome 商店 ID：`hhcmgoofomhgciiibhipgmgkgnoenaoi`
   - Edge 商店 ID：`emacgiaaaiojkkpkddmmdfhmokgmnikg`
2. **bsk daemon 的持久托管。** 当前 daemon 运行在 DSH 的后台任务中（PID 19760，`--daemon-idle 12h`）。DSH 的 Job Object 禁止 detached 启动（`os error 5`），因此长期使用更适合在普通终端中执行一次 `bsk daemon start`；不要在 DSH shell 内反复尝试自动启动。daemon 默认 10 分钟空闲会正常退出，下次使用前需重新启动或依赖普通终端的自动启动。
3. 未把扩展安装成用户级永久扩展，也未修改 Chrome 策略/注册表；没有新账号、付费或登录操作。

## 6. 状态矩阵

| 能力/组件 | 已安装 | 已加载 | 已验证 | 未验证/说明 |
| --- | --- | --- | --- | --- |
| Context7 MCP（DSH 内） | 是（宿主自带 0.2.1-rc.2） | 是 | 是（初始化、工具列表、合法调用、错误输入、超时、重启） | 锁定版本的 Context7 文档未收录；已回退官方源码 |
| BrowserSkill 插件 0.3.2 | 是（原已装，未升级） | 是（skill + `browser_*`） | 是（临时 Chrome） | 日常 Chrome 扩展未安装 |
| bsk CLI | 是（0.3.3） | 是 | 是 | 长期 daemon 托管需普通终端 |
| BrowserSkill 扩展 0.3.3 | 仅临时 Chrome | 仅临时 Chrome | 是（临时环境） | 未安装进用户日常浏览器 |

## 7. 证据与临时目录

报告目录：`artifacts/toolchain/2026-10-20/dsh-plugins/`

- `report.md`：本报告
- `toolchain-lock.json`：精确版本、哈希、端点与配置修改记录
- `evidence/context7-initialize.sse`：Context7 初始化原始响应（含服务端自报 4.4.3）
- `evidence/context7-tools.sse`：Context7 `tools/list` 原始响应
- `evidence/fastapi-0.141.1-response-model.md`：FastAPI 0.141.1 官方文档源文件
- `evidence/pydantic-v2.13.5-models.md`：Pydantic 2.13.5 官方文档源文件
- `evidence/browserskill-form.png`：BrowserSkill 表单操作后截图

临时测试目录（不属于项目、可删除）：`C:\Users\30382\AppData\Local\Temp\dsh-toolchain-2026-10-20`。测试专用 profile `ctx7-headless`、`tmp-web-inspect` 已删除；临时 Chrome 测试进程已停止；bsk daemon 当前保留运行（PID 19760，`--daemon-idle 12h`）。

## 8. 规划/所有权核对与边界声明

- 已读取 `AGENTS.md`、`docs/agent-toolchain/00-common.md`、`AI-CODING-PLAN.md`、`docs/plan/TASK_MANIFEST.json`（表头）、`docs/plan/PHASE_GATES.md`、`OWNERSHIP.json`，以及最新交接（`docs/handoffs/P02-01/dsh-f01.md`、`docs/handoffs/N05-R03-ENV/codex.md`）。规划/交接核对只用于确认范围和所有权，不用于裁决或改变业务 Gate 状态。
- `OWNERSHIP.json` 中 `artifacts/`、`docs/`、`uv.lock` 均归 owner A；本任务只在 `artifacts/toolchain/` 新增报告，宿主配置在项目外，未写任何业务路径。
- 交接材料中 G01/P02 状态存在返工后过期与后续签收并存的线索；本任务不据此下业务结论，也不修改任何 Gate 记录。
- 未修改 `apps/`、`packages/`、业务 `scripts/`/`tests/`、`uv.lock`、`OWNERSHIP.json`、`artifacts/gates/`。
- 未升级 DSH 主程序；未安装任何 npm 包到 profile；`package.json` 与 `pnpm-lock.yaml` 未变。
- 未触碰模型供应商、认证、会话数据；未输出任何凭据。
- 未更新 modsearch、modlens、sidebar、quota、mobile；未新增记忆系统或自治编排器；未启动 AgentTeams 自动派发。
- 本任务结论只针对工具环境，不代表 P01/G01 或任何业务 Gate 状态。
