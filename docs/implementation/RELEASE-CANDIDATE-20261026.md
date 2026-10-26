# 2.0 Release Candidate — 2026-10-26

## 候选身份

```text
branch: dsh/2026-10-23-snapshot
commit: 4dcbd46
contract: 2.0.0
```

## 运行边界

- 唯一运行契约：2.0.0
- 唯一前端：`apps/frontend`，端口 8080
- 唯一集成入口：`/#/negotiation`
- 旧 0.2 引擎：`archive/partner_engine/`，只读归档
- 旧 20 单演练：已移除
- `/partner`：已移除，Nginx 返回 404
- 后端镜像不再包含 `partner_engine`

## 验证证据

```text
根目录测试：400 passed，1 deselected
前端单元测试：4 passed
浏览器测试：4 passed
架构扫描：134 modules，0 violations
Schema check：exit 0
```

浏览器测试：

- 2.0 integration 导入、计算、14 指标、交接、刷新
- 离线中文壳
- 后端不可达登录拒绝
- 运输提交与刷新

## 构建

```text
backend   built（无 partner_engine）
worker    built（无 partner_engine）
frontend  built（无 /partner 代理，/partner 返回 404）
```

## 未完成

- 正式 Gate 签收：必须由独立 reviewer/Codex 执行，实施 Agent 不自行签收。
- 独立复核需要重跑上述命令并核验输入/日志/候选哈希。
- 旧根 `frontend/` 目录仍因文件锁暂留，不参与构建；可后续归档。

## 交付给独立 reviewer

请以本文件、commit `4dcbd46` 和仓库内测试日志为输入；不要以本文件代替 Gate 记录。
