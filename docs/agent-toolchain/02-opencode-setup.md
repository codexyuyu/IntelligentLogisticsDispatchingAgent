# 给 OpenCode：检查现有插件并建立稳定配置

请检查并配置我现有的 OpenCode，使它能稳定承担大型长期项目的实现与前端联调。先读同目录 `00-common.md`、`README.md`。默认只补“版本匹配的文档查询”和“一个可复现的浏览器通道”，其他插件按下述条件评估；不要一次装满推荐清单。

## 已知线索，执行时必须重新确认

- npm 全局曾是 `opencode-ai 1.18.25`；Node `24.18.0`；OCX `2.0.15`；Bun 包 `1.4.2`。
- `C:\Users\30382\.config\opencode` 同时有 json/jsonc；jsonc 声明本地 `opencode-chrome-bridge`、`@slkiser/opencode-quota`、`@lesquel/opencode-pilot@latest`，并启用 `open-computer-use` MCP。
- 配置目录 node_modules 发现 pilot `1.23.1` 与 `@opencode-ai/plugin 1.18.30`，但仍需确定运行缓存实际加载版本。
- pilot 的官方仓库是 `lesquel/open-remote-control`，它负责远程控制，不是自动编程调度器。

## 执行

1. 从真实启动方式取得版本、配置来源、项目/全局/profile 合并规则和已加载插件。检查本地桥接与 npm 插件是否重复注入同类工具、compaction hooks、权限 hooks 或会话循环。先形成能力清单，保留原配置备份和回滚办法。
2. 依据本机 OpenCode 版本对应源码/文档确定插件 API、导出形式和包名；不要把 V1/V2 示例或不同 SDK 直接混用。宿主和 SDK 版本不同只是待查项，以依赖声明和功能测试判定。
3. 用已安装 OCX 创建或复用 `stable`、`candidate` profile；先查看该版本 help。验证全局、项目和 profile 哪些配置实际生效，证明 candidate 不加载待排除的全局插件。无法充分隔离时，用官方支持的独立配置路径与临时项目；不要声称 profile 是进程/文件权限沙箱。
4. 查询 Context7 官方元数据与安装说明。若没有等效文档工具，选择 MCP 或 CLI+Skills 一种入口；2026-09-18 候选 MCP 是 `4.1.1`，Node 下限 `20.18.1`，执行时重查。用项目锁定的 FastAPI/React/ORM 版本做一次带来源的查询，检查无法匹配时是否正确回退。
5. 检查现有 Chrome bridge/Computer Use 是否足以完成本地页面操作和错误取证。有稳定能力就复用；缺失时在 candidate 增加微软官方 Playwright MCP，快照候选 `0.0.81`、Node ≥18。测试临时页面、表单、截图/快照、控制台与网络错误、退出与重启。不要改动应用 `@playwright/test` 来迎合 MCP 的版本号。
6. Plannotator 仅在需要可视化计划/diff 审阅时启用；候选 `0.27.16` 当天新发布，要先验证与本机宿主及 Bun 的兼容。Superpowers 仅选择所需技能或在 candidate 评估其完整 bootstrap，确保不会覆盖本项目 Task Manifest、Gate 与所有权。
7. Oh My OpenCode / Oh My OpenAgent 只放候选环境。查询 npm 包名、官方仓库重定向、stable 与 beta 的实际区别；快照 latest 是 `4.19.4`，beta 是 `5.0.0-beta.75`。若测试它，停用同候选任务的其他自治编排循环，限制并发、时间与调用预算；不要自动晋级 beta。DCP 当前列观察名单，不因旧推荐单默认安装。
8. 现有 quota、远程控制、浏览器桥接分别做最小冒烟；如冲突，只在 candidate 暂停对应组件，保留旧 stable 的可恢复状态。quota 插件不能成为实现任务的前置条件。
9. 通过冷启动、文档工具、临时文件改写、浏览器、取消/超时、会话恢复与错误输入验证后，将本地插件写成精确版本/commit并保留实际缓存/传递依赖锁。移除拟投产配置里的浮动 `@latest`，仅限已验证组件。可选能力失败则回退原生工具，不破坏工作配置。

## 日常实现模式

只接收一张来自 Codex 的任务卡，核对 owner、白名单和前置 Gate。自己是该任务唯一主写者；不和 DSH 同写。实现、运行任务验收、保留日志，交给 ZCode/Codex 审查。若前置缺失，返回最早阻塞根因，不继续实现下游。按项目现有 schema 写交接，不伪装其他 agent 身份。

输出：各配置来源、现有与新增能力对照、安装/跳过理由、精确版本、成功/失败探针、稳定与候选入口、回滚方法。所有更新先落候选环境；若本次无需安装也要明确说明“已复用现有能力”。
