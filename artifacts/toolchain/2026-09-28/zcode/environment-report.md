# ZCode 环境检查与兼容性盘点 · 2026-09-28

- **本角色**：ZCode，独立预验收 agent（05-zcode-precheck.md 的初次环境配置）
- **范围**：本机 ZCode 宿主、模型供应商路由、插件/MCP/hooks 声明与实际加载、清单兼容性、探针结果
- **凭据原则**：只记录「存在/缺失/可用」，不输出密钥内容
- **产出**：本文件 + `probes.json` + `logs/`（探针原始输出）；原始机密配置未保存

## 1. 宿主与运行时（实测）

| 项 | 值 | 证据 |
| --- | --- | --- |
| 宿主应用 | ZCode Desktop `3.14.3`（`@zcode/desktop`，Electron） | `app.asar/package.json`（`C:\Users\30382\AppData\Local\Programs\ZCode\resources`） |
| 会话模型路由 | providerId `4b759684-9f16-4a4a-a315-d666c9464e62` = **DeepSeek**，model `deepseek-v4-pro`，api type `anthropic-messages`，baseUrl `https://api.deepseek.com/anthropic`（api-key 认证，存在） | `.zcode/v2/provider_config.json`（仅标识；密钥未记录）+ 本会话 system 信息一致 |
| 其他已配置 provider | `builtin:zai-coding-plan`（oauth）、`builtin:bigmodel-coding-plan`（oauth，`GLM-5.3` 系模型，当前 disabled）、`enabledBuiltinAgentCliProviders=["glm"]` | `.zcode/v2/config.json` / `setting.json` |
| 配置作用域 | 用户级 `C:\Users\30382\.zcode\`（`cli\config.json` 管 CLI 插件启用表；`v2\` 管桌面会话、provider、setting）；**本项目无** `.zcode/`、`.zcode-plugin/`、`.claude-plugin/`、`.mcp.json` ⇒ 全为用户级配置生效 | 目录清单 |
| 插件目录 | 缓存 `C:\Users\30382\.zcode\cli\plugins\cache\{zcode-plugins-official,claude-plugins-official}`；安装记录 `cli\plugins\installed_plugins.json`（scope=user）；市场 `cli\plugins\marketplaces\`；桌面内置 skills 在 `resources\glm\packages\bundled-skills` | 目录清单 |
| Node / npm | v24.18.0 / 11.16.0（项目基线 pin 22） | `node -v` |
| Python / uv | 3.12.10（.venv）；`tools/bin/uv.exe` 引导副本（uv 0.12.13，PATH 无系统 uv） | 实测 |

## 2. 插件盘点：声明 vs 实际加载

### 2.1 CLI 启用表（`.zcode/cli/config.json` `enabledPlugins`，7 项）

android-emulator、ios-simulator、cloudbase-skills、restore-legacy-sessions、mimosa（以上 `zcode-plugins-official`）；chrome-devtools-mcp、huggingface-skills（`claude-plugins-official`）。

### 2.2 本会话实际加载的 skills（系统列出的可加载技能为权威证据）

**15 个插件 + 1 个内置技能组**：android-emulator 0.1.0、browser-use 0.5.1、chrome-devtools-mcp 1.6.0、cloudbase-skills 0.1.0、documents 0.1.7、huggingface-skills 1.0.23、ios-simulator 0.1.0、mimosa 1.0.3、pdf 0.1.7、plugin-creator 0.1.1、presentations 0.1.7、restore-legacy-sessions 0.1.0、skill-creator 0.1.0、spreadsheets 0.1.7、zcode-guide 0.3.0、内置 dynamic-workflows。

**差异记录（非故障）**：CLI `enabledPlugins` 只有 7 项，但会话还加载了 browser-use、documents、pdf、plugin-creator、presentations、skill-creator、spreadsheets、zcode-guide（均来自 `zcode-plugins-official` 缓存）与内置 dynamic-workflows。桌面会话的插件加载作用域与 CLI 启用表**不完全一致**（桌面侧另有默认/内置装载路径），按官方文档「清单被识别 ≠ 完全兼容」的要求记录为「已加载但声明来源未在 CLI 启用表中列全」，待官方文档/设置面板进一步核对后收敛。

### 2.3 组件类型盘点（对照官方文档 `zcode.z.ai/cn/docs/plugin`）

| 组件 | 声明处（实例） | 实际加载 | 备注 |
| --- | --- | --- | --- |
| skills | 各插件 `skills/<名>/SKILL.md`（frontmatter `name`/`description`） | ✅ 全部出现在会话可加载列表 | — |
| commands | android-emulator / ios-simulator / mimosa（`commands/` 目录） | 未在本会话直接调用（无任务需求） | 声明存在；未逐条冷启动 |
| agents | documents / pdf / presentations / spreadsheets（`agents/*.md`） | ✅ `visual-judge` 四实例在 Agent 工具可用 | — |
| hooks | mimosa 1.0.3（外层与 payload 各一份 `hooks/hooks.json`：PreToolUse/PostToolUse/UserPromptSubmit/SessionStart/Stop）；android/ios 声明空 hooks | ✅ **UserPromptSubmit 实测生效**（本会话注入 Mimosa 安全约束）；PreToolUse/PostToolUse 挂 Edit|Write|MultiEdit 与 Bash | — |
| MCP | 见 §3 | 见 §3 | — |

### 2.4 清单兼容性结论

- `.zcode-plugin/plugin.json`（官方推荐）与 `.claude-plugin/plugin.json`（兼容）在本机缓存中均被识别（chrome-devtools-mcp 以 `.claude-plugin` 装载成功，android-emulator 等以 `.zcode-plugin` 装载成功）。
- **逐组件核对已做**：`chrome-devtools-mcp` 的 mcpServers 实为 `npx chrome-devtools-mcp@1.6.0`；android/ios 的 MCP 以 `ZCode.exe __zcode-plugin-host <server.js>` 进程宿主；cloudbase 的 MCP 声明在插件内 `.mcp.json`（`npx -y @cloudbase/cloudbase-mcp@2.23.11`）；mimosa 外层 manifest 无 mcpServers、payload 子清单才声明（`node dist/mcp/server.js`，`MIMOSA_ENGINE=native`）。
- **不兼容声明**：OpenCode JS 插件（`.opencode/`、opencode.jsonc）、DSH Cordis 插件（`~/.dsh`）、pi extension（`~/.pi` 设置）**均未也不应作为 ZCode 插件加载**——本项目其他 agent 的配置留在各自宿主作用域，与 ZCode 互不导入。

## 3. MCP 盘点（声明 → 加载 → 探针）

| MCP | 声明来源 | 进程/协议 | 探针结果 |
| --- | --- | --- | --- |
| chrome-devtools | 插件 manifest（`npx chrome-devtools-mcp@1.6.0`） | stdio | ✅ 合法调用 `list_pages` 成功（1 空白页）；错误输入 `click uid=nonexistent` 返回结构化错误；**前端预验收可用，无需新增 Playwright MCP** |
| cloudbase | 插件内 `.mcp.json`（`@cloudbase/cloudbase-mcp@2.23.11`） | stdio | ⚠️ 工具就绪但 `queryEnv(list)` 返回 `AUTH_REQUIRED`（**未登录外部服务**）——记录为「缺登录」，非兼容性故障 |
| mimosa | payload 子清单 | stdio（node） | ✅ 错误输入 `security_scan_status(jobId=bogus)` 返回结构化错误 `非法 security scan job id`，优雅降级 |
| android-emulator | 插件 manifest（ZCode 插件宿主） | stdio | ✅ `android_preflight` 合法调用：SDK/adb 就绪；emulator/Java/Gradle/AVD 缺失（环境事实，非插件故障） |
| ios-simulator | 插件 manifest（ZCode 插件宿主） | stdio | ✅ `ios_preflight` 合法调用：macOS-only，Windows 上如实报不适用 |
| node-repl | node-repl-host（桌面内置，computer-use/browser-use 配套） | — | 仅浏览器/电脑使用场景专用；本会话按说明未作通用运行时使用 |

- **取消/重启探针**：后台 Bash 任务 `sleep 40` → `TaskStop` **killed 成功**；随后新后台任务立即 `completed (exit 0)` ⇒ 取消与重启语义正常。
- **未做的探针（如实记录）**：MCP 服务进程级冷启动/重启（stdin 关闭等）未执行——被探 MCP 均为会话预加载，由宿主管理生命周期，不在本会话内重启；`commands/` 组件未逐条冷启动（本任务无命令需求）。
- **不需要新增的能力**：文档查询已由 WebSearch/WebFetch 覆盖（官方插件文档实测可读）⇒ **不装 Context7**；浏览器已由 chrome-devtools-mcp 覆盖 ⇒ **不装 Playwright MCP**。

## 4. 变更与恢复方式

- **本会话改动**：仅新增 `docs/handoffs/P01-01/zcode.md`、`artifacts/handoffs/P01-01/zcode/**`、`artifacts/toolchain/2026-09-28/zcode/**`、`tmp/zcode-p0101/**`（gitignored）；未改任何用户配置、provider、插件或 `.zcode` 目录内容。
- **失败项**：cloudbase `AUTH_REQUIRED`（需用户登录腾讯云开发，恢复方式：`auth start_auth` device 授权）；android 模拟器链路缺 Java/Gradle/emulator（恢复方式：安装 Android Studio/JDK 或改用真机）。
- **原配置保留**：用户原有模型供应商、登录方式、插件启用表均未改动；未开启任何付费服务。

## 5. 结论

ZCode Desktop 3.14.3 环境与插件生态**可用于本项目的独立预验收**：技能、agents、hooks、MCP 的主干能力已按官方清单语义逐一核对并探针验证；OpenCode/DSH/pi 插件明确隔离在 ZCode 作用域之外。唯一需用户介入的项是 cloudbase 登录（本任务不需要）；其余失败项均为环境性事实并已给出恢复方式。
