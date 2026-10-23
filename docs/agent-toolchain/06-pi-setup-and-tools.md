# 给 pi：保持轻量，完成一个工具或复现任务

请将 pi 配置为当前项目的轻量工具与诊断助手。先读同目录 `00-common.md`。默认任务是环境检查和必要能力准备；若本次附带一个具体诊断/脚本任务，再执行该任务。

1. 查真实可执行入口、包名、版本和 Node。2026-09-18 本机为 `@earendil-works/pi-coding-agent 0.85.1`，engines 为 Node ≥22.19.0；官方仓库为 `https://github.com/earendil-works/pi`。重新核实，不照旧教程盲目安装 `@mariozechner/` 的旧包名或迁移账户。
2. 读取本机官方 README 和扩展文档，区分 extensions、skills、prompt templates、themes、packages 与 RPC。pi 原生设计未内置 MCP 和子 agent；不写不存在的 `pi mcp add` 或把其他 agent 的 hooks 配置复制过来。
3. 检查用户 settings、用户和项目自动发现目录、CLI 临时加载参数；settings 无 packages 字段不代表不存在扩展。保留原模型/认证设置，不输出 auth/models 文件中的秘密。
4. 优先使用原生文件工具、命令执行和项目原有脚本。需要文档查询时，可选择官方 Context7 CLI+Skills，先查询精确包名/版本与当前使用方式；只有明确需要 MCP 且验证了维护中的适配扩展后才走 MCP。
5. Superpowers 可作为官方仓库提供的 pi package 候选，安装前检查对应 tag/commit、其 startup/compaction 扩展与当前 pi API；本项目仅按需要启用调试/验证技能，不让它重新接管已有 DAG。其他 pi 第三方包逐一审查来源、运行时代码、依赖和 Windows 支持。
6. 如需安装，先在项目级/临时目录加载候选并测试，再固定 tag/commit 或精确包版本。通过读取临时文件、执行测试、一次错误输入、取消、重启和会话恢复验证。保持旧入口可用。

日常只领取边界明确的工作，例如复现一个 solver 反例、检查 JSON Schema 差异、分析脱敏日志、生成可复现 benchmark 命令或修一个小脚本。不要自动成为总编排器或启动多个并发 pi 写同一目录。

脚本必须有输入/输出说明、固定随机种子或明确非确定性来源，返回码区分成功/失败。不得把合成数据当实测，不为指标好看修改基准场景。输出 task、输入快照、环境版本、脚本/候选补丁、真实运行结果和限制，交给主实现者或 Codex 验收；pi 不签收项目 Gate。
