# DSH-AVAILABLE-20261022 · 可独立推进任务交接

## 实现范围

- 快照：backend/app/adapters/persistence/pg_snapshot_store.py 实现现有 PlanningSnapshotStore.get_snapshot(snapshot_id, expected_version)；事务只读、严格 DTO、最新版本检查。save_snapshot 为适配器导入辅助方法：不可变历史、内容一致重试、版本 CAS、同一快照并发串行化。显式迁移 backend/migrations/DSH_001_snapshots.sql，不改原业务表；正式组合根接入归乙方。
- R09：app/evaluation/metrics.py 输出 14 项同口径记录，当前计划数据直接计算需求满足率、准时率、平均延误、距离、车辆利用率。其他字段缺数据即 null + missing_reason；不把元数据耗时累加冒称全流程墙钟测量。另交付区间并集、容量积分和稳定任务差异/扰动纯函数，未绑定尚未冻结的冷链 DTO。
- R09 实验：隔离 callback 执行器，固定同快照、同预算、配对重复编号；原始方案、失败/异常、耗时、预算超限均保留。记录源码哈希、依赖版本、平台，输出包含失败尝试的中位数和 nearest-rank p95；配对差采用固定 seed bootstrap，少于10个有效配对不输出均值和置信区间。
- 3 个文档断链修复为明确“未合入”的历史引用，当前运行契约链接可访问，不引入第二套 DSH DTO。

## 复现

从 merged/backend 执行：

```
../.venv/Scripts/python.exe -m pytest -q tests/evaluation
../.venv/Scripts/python.exe -m app.evaluation.run_comparison --snapshot ../data/scenarios/prep_T1.json --budget-ms 200 --out-dir ../../tmp/新的实验目录
```

全套 pytest 实跑 228 passed / exit 0（当时新增13项）；最终增加容量积分测试后专项14 passed / exit 0。记录在父目录 tmp/DSH-AVAILABLE-20261022/。两次实验分别保留，最终以 t1-paired-final 为准。

这不是完整 R09 签收：仅 sequential/deep 两种现有 solver 策略，10个编号是重复实验标识，当前 routing 端口不能传 random_seed；未实现或冒充规则基线、LLM策略、完整 B0–B3、公平随机实验。真实T1距离对照不证明一般收益。

## 数据库验收入口

只对新建的隔离测试数据库设置 DSH_TEST_DATABASE_URL，执行：

```
../.venv/Scripts/python.exe -m pytest -q tests/persistence/pg_acceptance.py
```

该显式命令会执行独立 schema 迁移并插入随机测试快照。缺少变量直接失败，没有 skip、SQLite 替代或内存假通过。脚本名称使默认业务回归不自动操作任何数据库；数据库验收是必须单独执行的交付项。连接工厂必须返回新的、autocommit=False 的 PostgreSQL 连接。

## 阻塞与双方职责

版本化确认未实现：普通候选/重排候选的哈希范围不同；缺少被替换计划与资源净释放语义。详见 contracts/changes/20261022-dsh-confirmation.md，乙方需冻结算法和版本/CAS/替换语义，甲方再实现。既有 confirm 占位保持显式失败，不能写成功字段。

R05 仍等待乙方冻结契约；不重启相同阻塞。R09 剩余成本、真实库容/设备/月台观测、单调时钟、异常检测/重排测量与完整策略须在相关观测/接口就绪后接入。既有7处 application→adapter 依赖归乙方组合根任务。

本次没有修改公共 DTO、乙方业务实现或正式 HTTP 装配，没有宣称全部业务系统已交付，也未向合作方发送消息。

## PostgreSQL 实测补充

启动本机已有 Docker 后，在随机端口（仅127.0.0.1）运行独立 postgres:16 容器和 dsh_snapshot_test 数据库。显式验收 pg_acceptance.py：2 passed / exit 0，覆盖内容一致重试、同版本不同内容拒绝、最新版本读取、缺失ID、两线程CAS恰一成功。结束后删除本次测试容器并清除当前测试进程连接环境变量；未连接或修改任何现有业务数据库。

原始日志：tmp/DSH-AVAILABLE-20261022/pg-acceptance.log、pg-container.log、pg-cleanup.log。Docker Desktop 保持运行；未变更全局配置。快照适配器可交付给乙方组合根接入；版本化确认仍有独立契约阻塞，不能据快照测试通过标为已实现。
