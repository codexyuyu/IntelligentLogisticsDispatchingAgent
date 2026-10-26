# B-04 异常事件类型（R20）

B-04 的状态机与契约一直声明 5 种异常，但只有 `departure_delayed` 实现了完整处置链路。本轮把其中 2 种补齐到**可真实运行、可校验、失败留痕**的程度。

## 支持矩阵

| 事件类型 | 状态 | 对象 (`object_id`) | 必需 payload | 影响范围 |
|---|---|---|---|---|
| `departure_delayed` | ✅ 已实现（R17 起） | 车辆 id | `delay_s > 0` | 该车整条路线 |
| `dock_unavailable` | ✅ **R20 新增** | 仓库 id | `unavailable_until_s > 0` | 计划发车早于该时刻的车辆 |
| `cargo_quarantined` | ✅ **R20 新增** | 批次 id | `affected_order_ids` 非空 | 被隔离订单所在车辆 |
| `weather_changed` | ⛔ 未实现 | — | 需 `replacement_matrix_id` 指向可解析的替换矩阵 | — |
| `demand_changed` | ⛔ 未实现 | — | 需订单新数量/优先级字段（契约当前没有） | — |

未实现的两个类型会**明确抛错** `b04_event_type_not_implemented:<type>`，不会静默返回空方案或假装成功。

## `dock_unavailable`（月台不可用）

**语义**：某仓库在 `unavailable_until_s` 之前无法装车。

- **改的是装车窗口，不是货物就绪时间**：`loading_window.start_s` 抬到 `unavailable_until_s`，`ready_at_s` 保持原值。原因是 `ready_at` 描述"货什么时候备好"，月台封锁不改变这一点，而且跨域校验器会用仓内作业完工时间去反查 `ready_at`，改它会导致校验失败。
- **影响范围取最小集**：只有"计划发车时刻早于月台重开时刻"的车辆进入重排，其余车辆路线冻结保留。
- **赶不上的订单不会被静默丢弃**：若某订单的装车窗口在月台重开前就已关闭（`loading_window.end_s < until`），该订单记入 `replanned_plan.routing.unserved_orders`，`reason_code = "dock_unavailable"`，并从本次重排范围中移除。
- **求解器侧配套修正**：模型此前只约束"发车 ≤ 装车窗口结束"，装车窗口**开始**时刻仅由校验器把关。月台封锁完全依赖这个下界，因此已在模型中补上 `start ≥ loading_window.start_s`（条件于该订单副本被选中）。这同时修掉了一个潜在不一致：求解器可能返回一个校验器必然拒绝的方案。

## `cargo_quarantined`（货物隔离）

**语义**：指定订单被质检隔离，不再参与配送。

- 被隔离订单从重排范围移除，所在车辆进入重排（其余车辆冻结）；
- 结果中显式记录 `reason_code = "cargo_quarantined"`；
- 校验规则新增 `b04.quarantine.orders_removed_and_recorded`，确保"移除"与"记录"同时发生。

## 快照版本语义

三种事件都会把快照 `version + 1`：`departure_delayed` 改车辆可用时刻，`dock_unavailable` 与 `cargo_quarantined` 的**快照事实本身不变**（前者体现在装车窗口，后者体现在重排范围），但版本号仍要推进，好让每个方案可追溯到唯一一个作业状态。

## 校验规则（`LocalRescheduleResult.validation.checked_rule_ids`）

公共：`b04.snapshot.derived`、`b04.impact.local_scope`、`b04.locked_routes.preserved`、`b04.affected_routes.replanned`、`b04.transport.revalidated`、`b04.plan.revalidated`。

- `dock_unavailable` 追加：`b04.dock.loading_window_shifted`、`b04.dock.undeliverable_recorded`
- `cargo_quarantined` 追加：`b04.quarantine.orders_removed_and_recorded`

`validator_version` 由 `b04-local-reschedule-validator-1.0` 升到 `2.0`；方案侧 `b04-local-reschedule-plan-2.0`。

## 失败模式（全部显式报错）

| 情况 | 错误码 |
|---|---|
| 未知事件类型 | `b04_event_type_not_implemented:<type>` |
| 月台缺 `unavailable_until_s` 或 ≤ 0 | `dock_unavailable_requires_positive_unavailable_until_s` |
| 月台对象不是本方案里的仓库 | `dock_warehouse_not_in_plan:<id>` |
| 隔离缺 `affected_order_ids` | `cargo_quarantined_requires_affected_order_ids` |
| 隔离订单不在本方案范围内 | `quarantined_orders_not_in_plan:<ids>` |
| 车/仓校验失败 | `b04_transport_validation_failed` / `b04_plan_validation_failed` |

## 测试

- `backend/tests/test_b04_event_types.py`（8 条，纯逻辑 + 假求解器 + 真实校验器）：
  影响范围最小化、payload 校验、未实现类型显式报错、装车窗口位移、赶不上订单记录、隔离订单移除与记录。
- `backend/tests/test_b04_reschedule.py`（既有 2 条）继续覆盖 `departure_delayed`，语义未变。

## B-05 仿真事件流（R20 接入）

三种事件都能通过 `POST /api/v1/simulations` 或 `SimPySimulator` 按时间序自动回放，不再需要手工逐条注入。

- **基线范围**：只有 `departure_delayed` 的 `affected_order_ids` 会作为基线规划的缩小范围（那些订单同属一条路线）；`dock_unavailable` 的 `object_id` 是仓库、`cargo_quarantined` 的 `affected_order_ids` 是被封锁订单，若用它们缩小基线，仿真的初始方案里根本不会有事件要处理的订单。收敛规则见 `simpy_simulator.baseline_order_ids()`。
- **先校验再求解**：事件流里出现未支持类型时，在花费基线预算**之前**就以 `simulation_unsupported_event_types:<types>` 失败。
- **不再静默截断**：若 `horizon_s` 短于最后一个事件，过去会静默丢掉尾部事件，现在抛 `simulation_horizon_cut_event_stream:<ids>`，避免产出一个"看起来正常"但其实没回放完的结果。
- **失败即中止**：任一事件处置失败会中止整场仿真并向上抛出，HTTP 层把它记为失败作业（`job.status=failed` + `error_code`）。事件不会被静默跳过，`emitted_events` 只包含真正回放成功的事件。

**实测**（`python -m tools.b05_event_stream_probe --budget-ms 12000`，20 单双仓）：

| 时间 | 事件 | 结果 |
|---|---|---|
| 0 s | `departure_delayed` veh_1 +900 s | 应用 |
| 1200 s | `dock_unavailable` wh_1 至 3600 s | 应用，wh_1 两车发车推到 3600 |
| 3600 s | `cargo_quarantined` ord_001/ord_002 | 应用，18 单服务、2 单记录原因 |

最终方案 v4（基线 + 3 次事件）：`veh_1` 3600 s（3 单）、`veh_2` 3600 s（5 单）、`veh_3` 600 s、`veh_4` 540 s；同种子连跑两次最终快照**摘要完全一致**。

## 还没做的部分（诚实清单）

1. `weather_changed`：需要能解析 `replacement_matrix_id` 的矩阵提供方（`adapters/matrix/osrm.py` 仍是 `FeatureNotImplemented` 骨架），或把替换矩阵随快照一起给出。
2. `demand_changed`：需要订单数量/优先级的新契约字段；当前 `EventPayload` 没有承载位置。
3. 月台粒度：当前 `object_id` 是**仓库**，不是单个装卸口；域模型里还没有月台实体。
4. 事件流是**预置列表**，还不是"由仿真状态触发"的事件（例如冷间温度越界自动产生隔离事件）。
