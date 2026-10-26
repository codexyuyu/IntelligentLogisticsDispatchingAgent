# 合并说明 · R30-E × DeepSeekHarness（2026-10-22）

## 结论

**运行时以 R30-E 为唯一基线**；DeepSeekHarness 只贡献其独有且可验证的部分：准备数据包、规格文档、手算 oracle。DSH 的空包骨架（`apps/`、`packages/`、`tests/` 脚手架）与 40 Gate / 109 Prompt 体系**不合入**。

## 实测证据（本机 Windows，Python 3.12.10，lock 文件安装）

| 检查 | 结果 |
|---|---|
| R30-E 原有后端全套 | **210 passed**（真 OR-Tools 9.15.6755 / CP-SAT / SimPy 4.1.2；对方报告 91 项为子集） |
| 合并后全套 | **215 passed** |
| DSH 数据包导入 R30 契约 | T1/A8/B20 三个快照全部通过 `PlanningSnapshot` 严格校验 |
| T1 对照手算 oracle | 路线 D→C1→C2→D、9000 m、到达/离开 300/360、560/620 —— 与 `TEST_FIXTURES.md` 完全一致 |
| A8（8 单，冷藏+冷冻） | 8/8 交付，无跨温区混装，联合校验 passed |
| B20（双仓、20 单、100 项仓储工序） | sequential 与 deep 两种模式均 passed，0 未服务，CP-SAT optimal |

复现：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
.\.venv\Scripts\python.exe scripts/import_preparation_bundle.py --check
cd backend; ..\.venv\Scripts\python.exe -m pytest -q
```

## 报告书 R01–R10 谁更优

| 需求 | R30-E | DSH | 采用 |
|---|---|---|---|
| R01 路径与运力 | OR-Tools 775 行，实测通过 | 无代码 | R30-E |
| R02 异常处置 | 4 类事件、影响分析、新旧差异证据（R30-B/E） | 无代码 | R30-E |
| R03 仓配协同 | CP-SAT + 双向协调，双仓实测通过 | 无代码；贡献双仓 B20 测试数据 | R30-E + DSH 数据 |
| R04 大模型工具调用 | DeepSeek Function Calling，只读工具、轮数上限 | 无代码 | R30-E |
| R05 冷链 | 温区、批次、保鲜期审计；**预冷/清洁换批/冷间时变占用未建模** | 规格 + 数据有预冷工序 | **两边都未完成** |
| R06 局部重排 | 冻结路线、影响集、后缀重求解 | 规格更细（救援交接、在途起点） | R30-E，DSH 规格补缺 |
| R07 仿真推演 | SimPy、快照隔离 | 规格（S1 快照恢复 oracle） | R30-E |
| R08 四角色协商 | `contract_net.py` 空壳 | 无代码 | **两边都未完成** |
| R09 可复现实验 | r17/r18/r19 配对种子证据 | 14 指标口径、B0–B3 对照设计 | R30-E 证据 + DSH 口径 |
| R10 成果交付 | 可运行、Windows 启动脚本 | 无可运行物 | R30-E |

## 导入时的显式损失（未隐藏）

`scripts/import_preparation_bundle.py` 把契约无法表达的字段逐条写入 `data/scenarios/prep_import_report.json`，不填默认值伪装兼容：

- 冷间库位容量（契约无时变存储占用）
- 仓储作业的多资源同时占用（契约 Operation 只占 1 个资源）→ 降为首个资源
- 序列相关 setup / 月台准备时间
- 货物最大暴露时长、软期望时刻、车辆成本
- 批次有效期（数据包无，置为当日末并在报告中注明）

这份清单本身就是 R05 待办的精确输入：契约要补哪些字段才能承载冷链时变。

## 剩余工作（据实测，非估计）

1. **R05 冷链时变**：契约补 storage 占用 / 多资源需求 / setup 字段 → CP-SAT 加约束 → 独立校验器加规则。损失清单即需求清单。
2. **R08 四角色协商**：`application/contract_net.py`。
3. **R09 统一指标与 B0–B3 对照**：14 指标按 `docs/spec/METRICS_CONTRACT.md`。
4. **版本化确认**：`adapters/persistence/plan_commit.py`、`snapshots.py` 仍是空壳。
5. **组合根**：`bootstrap.py` 仍是空壳，装配散在 route 里。

以上为首次合并记录。2026-10-22 后续 INTEGRATION-20261022 已修改前端、共享对接及构建治理；详见 [增量日志](docs/devlog/entries/20261022-dsh-integration.md) 和 [分工协议 v2](COLLABORATION_SPLIT_20261021.md)。前端生产构建现已实跑通过；完整架构检查仍失败，不代表五项剩余业务完成。
