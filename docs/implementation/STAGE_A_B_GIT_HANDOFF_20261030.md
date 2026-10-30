# Stage A + Stage B 代码整理与 Git 交接（2026-10-30）

本文件说明阶段一（Stage A 后端）与阶段二（Stage B 前端）通过验收后，代码如何整理进 Git，
以及刻意**没有**提交、**没有**推送的内容。

## 1. 分支与提交

| 项 | 值 |
| --- | --- |
| 父提交 | `fd1f241` |
| 新分支 | `feat/stage-a-b-accepted-20261030`（**独立分支，不覆盖队友现有工作**） |
| 是否已推送 | **否**，按约定保留在本地，等待确认后再推送与合并 |

```
e0445ae  feat(backend): persist checked-run simulations for delay review and replay
f85689a  feat(frontend): integrate Stage A simulation into the five existing pages
7beca9b  docs(stage-a-b): record acceptance evidence and the isolated-environment runbook
```

划分理由：后端能力、前端整合、证据与文档各自独立，便于单独 revert 或 cherry-pick。

## 2. 行尾规范化（整理时发现并修正）

Stage A overlay 带入的 3 个已存在后端文件是 CRLF，而仓库原文件是 LF，会让 diff 膨胀到
整文件重写：

| 文件 | 修正前 diff | 修正后 diff |
| --- | --- | --- |
| `bootstrap.py` | 266 / 259 行 | **9 行** |
| `api/integration.py` | 137 行 CRLF | **65 行** |
| `persistence/integration_models.py` | 81 行 CRLF | **36 行** |

已统一转回 LF。`core.autocrlf` 在本副本为 `false`，提交的字节即工作区字节；仓库的
`.gitattributes` 只对 hash-pinned 文件强制 LF，因此这次对齐是按仓库既有惯例处理，不是新增规则。

## 3. 刻意未提交的内容

- **`tests/integration/test_stage_a_acceptance_14.py`**：Stage A 的一次性取证脚本。
  CI 执行 `uv run pytest tests/unit tests/integration`，它一旦入库就会被收集，而它需要
  实时并可写的隔离库与 operator 认证流程，不适合进入常驻测试套件。副本保留在
  `stage_a_evidence/` 下（`pytest` 的 `testpaths = ["tests"]` 不会到达）。
- **UI 截图**：20 张、约 7.5MB，已加入 `.gitignore` 的 `/stage_b_evidence/shots/`，
  保留在本地与分发证据包 `StageB_frontend_acceptance_20261030.zip` 中。

## 4. 为何要登记 OWNERSHIP.json

`tests/unit/test_p01_03_migration_governance.py` 断言
`coverage.default_owner_fallbacks == []`，即每个文件都必须匹配到显式登记的 owner 前缀。
新增的 `stage_a_evidence/` 与 `stage_b_evidence/` 未登记时该断言会产生 54 个 fallback 而失败。
已按 A 方登记两处；治理测试现有 **62 passed**。

## 5. 提交前的本机自检（模拟 CI）

| 检查 | 结果 |
| --- | --- |
| `check_architecture.py` | violations=0 |
| 本次新增/修改文件的 `ruff check` | All checks passed |
| `pytest tests/unit tests/integration` 全量 | **479 passed / 2 failed / 2 skipped** |
| Stage A 后端定向回归 | 8 passed |
| 前端 build + vitest | exit 0 / **48 通过** |

两个失败均在 `tests/integration/test_p01_01_workspace_bootstrap.py`，**与本次改动无关**：

1. `test_node_runtime_satisfies_the_pinned_baseline`：本机 node 为 22.22.2，而
   `artifacts/handoffs/P01-01/dsh/evidence.json` 记录的基线是 24.18.0；CI 安装 24.18.0，对该 CI 通过。
2. `test_npm_ci_is_repeatable_and_lock_file_is_unchanged`：全量运行时因测试间干扰失败，
   单独重跑 **1 passed**；`package-lock.json` 与 `uv.lock` 自始至终未被修改。

## 6. 给下一步的建议

- **合并时的 base**：建议以 `demo/p0-integration-20261029` 为 PR base。
  `main` 是仅含 1 个 commit 的孤儿提交（目录结构 `backend/` vs `apps/backend`，差异 2734 文件），
  无法作为集成分支。
- **遗留非阻断项**：OpenAPI 契约自动生成（`contracts:generate`）与旧 `generated.ts` 不兼容；
  车辆中途重新寻路尚未支持，当前批准后是「原地等待 + 后续顺延」。
- **演示链路已具备**：仓储排程 → 模拟车辆运输 → 途中延误 → 人工审批 → 全局回放。

## 7. 约束遵守

5433 演示库全程未启动;`_demo_p0` 原工作区未被改动;未执行任何 merge / push。
