# P02-01 · 依赖刷新附件 `P02-01-R01`

> 本附件是**新增**记录，不取代、不改写也不冒充更新原有交接。原 `docs/handoffs/P02-01/dsh.md`、
> `artifacts/handoffs/P02-01/dsh/evidence.json`、`seal.json` 保持交付轮原字节——因为最新 G01 独立 review
> 同时绑定它们，覆盖会使刚签的 review 失效。

| 项 | 值 |
| --- | --- |
| Task ID / round | `P02-01` / `P02-01-R01`（仅依赖交接刷新，**未改业务实现**） |
| 作者 | DSH-A（本会话；本附件唯一主写者） |
| 生成（实际 UTC） | `2026-10-05T03:53:22.806840+00:00` |
| 状态 | **`READY_FOR_ZCODE`**（本附件；不签任何 Gate） |
| 当前候选 | `content-sha256:dadad19614a86a39ddf880c8ae8011e5fff889d1f02d12b7a0cfa28aaaad3cf8`，82 文件 |
| 当前前置（现行有效） | `G01` sha256 `a7eed6aee3f0e21b39e440aee6a7d4f2f5f74b5d1407eb4011eac7215a3b18c4`（`status=passed`，`failed_checks=[]`）；review sha256 `c41888a77a22d146502dd5f91de85f12f036c4cbd70fbf3de00d45789630a275`（`status=approved`，reviewer 为独立 Codex N05-R01） |
| 启动时历史前置 | 旧 `G01` `b7ac0c60de7438dc0cd88cc7f277b6ac2e93b8216ee05efdfb3124089c98dee8`、旧 review `1cfd47668b64b49062c14eb0af648d8fd23eaf86748bc0b68ecb3421331e185d` —— **仅历史**，已被 N05-R01 重新签收取代，不得当作现行有效 |

## 1. 原交接原字节（未被本附件改动）

| 文件 | sha256 | 本附件动作 |
| --- | --- | --- |
| `docs/handoffs/P02-01/dsh.md` | `b3de54ebb24300388bcec4c6911964252a2358eb6bf82fae2e9c2c7a13364d49` | 不改写 |
| `artifacts/handoffs/P02-01/dsh/evidence.json` | `36f08ff6a8b983c8ba749ef1bbf6fc4b0ae157059e4036f1e6f7917ec274c4c8` | 不改写（身份已复算一致） |
| `artifacts/handoffs/P02-01/dsh/seal.json` | `cd6731c117a11215dbceb1d1878415db890172fdf35e6af1fa9516eb40b9ba1b` | 不改写 |

首次刷新尝试曾按上一条指令改写上述文件；本补充到达后，已用写入前保存的原字节**逐字节恢复**，并确认
`evidence.json` sha256 == `36f08ff6a8b983c8ba749ef1bbf6fc4b0ae157059e4036f1e6f7917ec274c4c8`；G01 review 的 **9/9** P02-01 绑定输入与 **253/253** 其他输入全部重新满足（`tmp/P02-01/R01/restore-originals.log`，problems=0）。

## 2. 独立复算（本附件提供的最新前置，供 ZCode 核验）

`tmp/P02-01/R01/verify-prereqs.py`（exit 0）：

- 候选与我交付的 `evidence.json`、`G01.code_revision`、`review.code_revision` **四者一致**；
- 新 `G01`：**40/40** 记录输入新鲜、依赖 `G00` 新鲜、**7/7** 命令日志 hash 匹配且 exit 0、`failed_checks=[]`；
- 新 `review`：**262/262** `verified_input_hashes` 新鲜、`status=approved`；
- `--check-only`：exit 0，`recorded status=passed`、`failed_checks=[]`、`all recorded inputs are fresh`。

## 3. 复用依据（本轮不重跑任何测试）

实现、测试、锁与候选**逐字节未变**，故直接复用交付轮真实日志：

- `artifacts/handoffs/P02-01/dsh/logs/p02-01-2026-10-04/required-cmd1-pytest.log` — {'passed': 46, 'exit_code': 0}
- `artifacts/handoffs/P02-01/dsh/logs/p02-01-2026-10-04/required-cmd2-check-architecture.log` — {'violations': 0, 'exit_code': 0}
- `artifacts/handoffs/P02-01/dsh/logs/p02-01-2026-10-04/full-regression.log` — {'passed': 272, 'exit_code': 0}

本附件**不声称**重跑过测试或全回归；新增文件中不含任何新测试结论。

## 4. 边界与停止状态

- 本附件**不加入** G01 review 的输入集合；该 review 保持其原有 262 项输入不变。
- 未修改任何业务源码、测试、契约、锁、所有权、规划、ZCode/Codex 记录或官方 Gate。
- 写出本附件与 `dependency-refresh-r01-seal.json` 后**立即停写**，交 ZCode 独立预验收；不启动 P02-02。
