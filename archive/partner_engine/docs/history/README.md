# 历史文档（已被取代，保留供追溯）

这里的文档记录项目演进过程，**不是当前实现依据**。当前状态以仓库根目录 `README.md`、`DEV_LOG.md` 与 `docs/` 下的现行指南为准。

| 文档 | 记录的是 |
|---|---|
| `CURRENT_BASELINE.md` | 某一时点的正式基线（早于 R17/R18/R19/R20，已被取代） |
| `MIGRATION_STATUS.md` | 迁移到统一 React/FastAPI 架构时的状态 |
| `MERGED_ARCHITECTURE.md` | 「910 merged baseline」两层结构的说明 |
| `B01_MIGRATION_COMPLETE.md` | B-01 仓储排程迁移到统一工程的记录 |
| `B02_ROUTING_V1.1_COMPLETE.md`、`B02_RUNTIME_FIX_2026-09-11.md` | B-02 路径规划成形与一次运行期修复 |
| `B03_WAREHOUSE_TRANSPORT_COORDINATION_COMPLETE.md` | B-03 仓运协同（R17 deep 之前的阶段） |
| `B04_LOCAL_RESCHEDULE_COMPLETE.md` | B-04 异常局部重排最初实现（后续在 R19/R20 扩展） |
| `B05_SIMPY_REAL_RUNTIME_COMPLETE.md` | B-05 接入真实 SimPy |
| `B06_LATEST_FRAMEWORK_NOTICE.md`、`B06_R12_ROUTING_DIAGNOSTIC_FIX.md` | B-06 早期框架说明与 R12 路径诊断修复 |
| `B_ALGORITHM_DEMO_GUIDE.md` | 早期算法前端演示流程 |
| `R16_RELEASE_NOTES.md` | R16 加速实验版发布说明 |

## 为什么单独放在这里

2026-10-15 交接整理时，这些文档在仓库内**已无任何引用**，但记录了"从早期 MySQL+Spring Boot/Vue3 到统一 React+FastAPI 工程、从 R2 到 R17"的演进脉络，对答辩讲"我们怎么走到今天"仍有价值，因此**移动而非删除**。

## 仍然现行、已移入 `docs/` 的指南

- `../R15_EXPERIMENT_EVIDENCE_GUIDE.md` —— 证据纪律（等预算、失败留痕、不挑样本）
- `../R16_FAST_BENCHMARK_GUIDE.md` —— 快检/标准两种评测模式
- `../R17_B03_DEEP_JOINT_OPTIMIZATION_GUIDE.md` —— 深度仓运协同原理与验收
- `../WINDOWS_SETUP.md` —— Windows 依赖安装

这些文档此前放在仓库根目录，但**没有被打进交付包**（`scripts/project_files.py` 的根文件白名单不含它们），导致包内链接失效；移入 `docs/` 后随包交付。
