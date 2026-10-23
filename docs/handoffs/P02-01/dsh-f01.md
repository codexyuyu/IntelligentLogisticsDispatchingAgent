# P02-01 · `P02-01-F01` 限定返工交接（当前候选）

| 项 | 值 |
| --- | --- |
| Task ID / round | `P02-01` / `P02-01-F01-2026-10-05` |
| 交付方 | DSH-A（原实现会话，本任务唯一主写者） |
| 状态 | **`READY_FOR_ZCODE`**（不签任何 Gate） |
| 缺陷 | `ZC-P02-01-F01`（major，独立预验收 FAILED 后交回） |
| 当前候选 | `content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`，82 个白名单文件（旧候选 `content-sha256:dadad19614a86a39ddf880c8ae8011e5fff889d1f02d12b7a0cfa28aaaad3cf8`） |
| 证据入口 | `artifacts/handoffs/P02-01/dsh/evidence.json`（sha256 `1ff843dab47cfbd0a1085ce78c76df2efb641347b61e45dcde351da68ff8e177`） |
| 旧交接 | `docs/handoffs/P02-01/dsh.md`（交付轮原字节，已归档）+ `dsh-r01.md`（R01 附件，按卡未重写） |

## 1. 修了什么

按冻结 `docs/architecture/DOMAIN_CATALOG.md:54` 的 `Reservation(held→committed→released/expired)`：

| | 更正前 | 更正后 |
| --- | --- | --- |
| `EntityState` | 69 成员，无 `released` | **70** 成员，含 `RELEASED = "released"` |
| `reservation` 边 | `held→{committed, cancelled, expired}`、`committed→{cancelled}` | `held→{committed}`、`committed→{released, expired}` |
| 终态 | `cancelled`、`expired` | `released`、`expired` |
| 未授权边 | `held→cancelled`、`held→expired`、`committed→cancelled` | 已删除 |

`cancelled` 未从其它实体移除（order / transport_task / job / confirmation_token 等取消边仍在），
`transition()` 公共签名与并集判定未改，未加入任何防御层。

## 2. 本轮实跑（真实计数与退出码）

| 命令 | 退出码 | 结果 | 日志 |
| --- | --- | --- | --- |
| `uv run pytest tests/unit/test_p02_01_primitives_and_states.py tests/integration/test_p02_01_primitives_and_states.py -q` | 0 | **52 passed / 0 failed**（原 46 + 新 6） | `artifacts/handoffs/P02-01/dsh/logs/p02-01-f01-2026-10-05/required-cmd1-pytest.log` |
| `uv run python scripts/check_architecture.py` | 0 | 10 modules / 7 layers，violations=0 | `…/required-cmd2-check-architecture.log` |

**未**运行全仓回归（按卡）；旧 272 只属旧候选，见交接 §4。

## 3. 新增回归断言（保留全部既有断言，无 skip/xfail/降断言）

5 个单元例 + 1 个集成例，逐项见 `evidence.json` 的 `reservation_lifecycle_fix.new_tests`。要点：
精确边集断言落在 **entity-specific 图** `LIFECYCLE_TRANSITIONS["reservation"]` 上，并显式排除并集中来自
其它实体的 `committed→superseded`，避免把全域并集误判成本图边；8 条逆向/未授权边全部实测抛 `InvalidTransitionError`。

## 4. 因本次合法返工而过期的旧证据（交调度做独立证据恢复）

| 旧证据 | 状态 | 原因 |
| --- | --- | --- |
| `artifacts/gates/G01.json`（`a7eed6ae…`） | 修订号过期 | 记录 `code_revision` = 旧候选，当前为 `content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c`；其 40 项**输入哈希 0 项漂移**（P02-01 的源码/测试/文档不在该集合内，集合里的 `packages/domain/src/logistics_domain/__init__.py` 未变）；记录字节未动 |
| `artifacts/gates/G01-codex-review.json`（`c41888a7…`） | 8 项输入过期 + 修订号过期 | 过期输入：`artifacts/handoffs/P02-01/dsh/evidence.json`、`artifacts/handoffs/P02-01/dsh/seal.json`、`docs/handoffs/P02-01/dsh.md`、`docs/implementation/P02-01.md`、`docs/implementation/reports/P02-01.md`、`packages/domain/src/logistics_domain/states.py`、`tests/integration/test_p02_01_primitives_and_states.py`、`tests/unit/test_p02_01_primitives_and_states.py` |
| `artifacts/handoffs/P01-01/zcode/precheck.json` | 5 项输入过期 | 该预验收也绑定了 P02-01 文件：`artifacts/handoffs/P02-01/dsh/evidence.json`、`docs/implementation/reports/P02-01.md`、`packages/domain/src/logistics_domain/states.py`、`tests/integration/test_p02_01_primitives_and_states.py`、`tests/unit/test_p02_01_primitives_and_states.py` |
| `artifacts/handoffs/P02-01/zcode/precheck.json`（`e517feec…` FAILED） | 已过期 | FAILED 记录绑定旧候选与其旧 evidence |
| 旧 `evidence.json`(`36f08ff6…`)/`seal.json`(`cd6731c1…`)/`dsh.md`(`b3de54eb…`) | 原字节保留 | 已在 `dsh/archive/f01-before/` 逐字节归档；本轮交付新 evidence/seal 与 `dsh-f01.md` |
| `docs/handoffs/P02-01/dsh-r01.md` 等 R01 附件 | 仍为旧候选历史 | 按卡未重写，也不冒充修复后的新前置 |
| 旧日志 `logs/p02-01-2026-10-04/*`（含 272 回归） | 属旧候选，未覆盖 | **不代表本候选已全回归** |

G01 在返工开始前有效；本轮**不修复、不重签**任何他人记录或 Gate，当前 G01 有效性**待独立恢复**。

## 5. 治理待办（本轮不改目录、不扩范围）

- `ZC-P02-01-N01`（minor）：`DOMAIN_CATALOG.md:39` 的 `created→running↔paused→completed` 有两读，建议治理澄清。
- `ConstraintCode`/`ViolationCode` 无成员表、`SafeArtifactPath` 无形状定义（已判非本任务缺陷）。

## 6. 停写

写出本交接、`evidence.json`、`seal.json` 后**立即停写**；不启动 P02-02，不执行官方 Gate，交独立复核。
