# DATA-PREP-20261014 · 小规模数据准备包

本包是独立 `preparation-v1` 合成输入，不能解除 P02–P04 的正式实现阻塞，不代表竞赛或 PostgreSQL 验收。所有记录 `source=synthetic`，固定 seed=42、UUID5、整数单位、UTC epoch；没有个人资料、真实订单或伪造求解结果。

从仓库根执行（Python 标准库，无额外安装）：

```powershell
python -B data/preparation/competition-2026/build.py
python -B data/preparation/competition-2026/validate.py
```

`generated/bundle.json` 是主输入；T1 两单、A8 八单、B20 二十单。包含仓库、温区、库位、月台、具名工人、设备、司机、车辆、运输任务、初始库存、日历及完整矩阵。B20 有100项五工序输入，初始库存0、外部到货20件，工人要求为候选人员中选1人，不能把两名工人重复计作额外资源池。切换30秒是资源规则输入，尚无已排定 setup 作业。运输价格在 A/B 中为本包附加合成假设。

T1/A8 采用测试规范的“t0前出库完成”边界；初始库存表示发车前货物所在地，不是未来重复入库。B20 的库存存储区间须由真实仓储排程形成，当前不能声称已求得可行联合解。W1 独立文件保留手算 oracle，非求解器输出。C1/C2/C3 是待绑定真实执行快照的事件模板，不能视为已发生事件；救援车辆及道路需届时显式提供，缺失应 MANUAL_REQUIRED。

`generated/preview.sqlite3` 为可直接打开的关系预览库；只有 entities/refs 两张 staging 表及按实体类型筛选的视图。`entity_coverage.json` 是32实体覆盖清单；运行时文件为空并注明未来生成方，不代表32个正式业务表已经实现。`postgres_staging.sql` 只向独立 competition_preparation schema 导入 preparation 数据，不是生产迁移；未运行 PostgreSQL，未验证并发、回滚迁移或正式领域映射。

`graph_nodes.csv` / `graph_edges.csv` 是输入关系图；可选 `graph_import.cypher` 尚未在 Neo4j 执行。图关系不是最优调度、影响分析结果或图数据库性能证明。

领域映射待办：CargoType、Qualification、Skill 及完整 EquipmentKind 尚缺批准定义；本包只记录 `*_mapping=pending`、preparation_operation/kind，不杜撰正式枚举，不声称 DTO 兼容。正式导入必须先完成契约批准、DTO转换、真实PostgreSQL迁移/事务/FK测试，再由求解器和独立校验器产生运行结果。

验证覆盖：生成确定性、UUID5、引用、整数单位、温区、必要容量、工序DAG、矩阵、T1独立手算及负例、W1算术、SQLite实际读回、二次导入不重复、FK失败事务回滚、文件SHA256。容量检查只是必要条件，不证明 A/B 全部可行。manifest 不含自身，包含其余交付文件；生成后修改文件须重新 build 再 validate。

依据：`docs/plan/TEST_FIXTURES.md`、`docs/architecture/DOMAIN_CATALOG.md`、`artifacts/orchestration/2026-10-04/20261006-round-handoff.md`。权威事实与生产实现仍以仓库当前契约和后续真实测试为准。

## 当前交付与 PostgreSQL 使用

生成后共326条输入记录、979条关系，30单（2+8+20），其中B20含100项仓储工序；18项本地校验通过。验证原始日志在 `tmp/DATA-PREP-20261014/validation.log`。SQLite可直接打开 `generated/preview.sqlite3`，例如查询 `SELECT scenario, count(*) FROM "Order" GROUP BY scenario;`。查询的是输入，不是执行结果。

数据库启动配置见 `deploy/data-preparation-2026/compose.yaml`。先设置环境变量 `LOGISTICS_PREP_PASSWORD` 并使本机 Docker 引擎可用，然后在仓库根运行：

```powershell
docker compose -f deploy/data-preparation-2026/compose.yaml up -d --wait
docker compose -f deploy/data-preparation-2026/compose.yaml cp data/preparation/competition-2026/generated/postgres_staging.sql postgres:/tmp/preparation.sql
docker compose -f deploy/data-preparation-2026/compose.yaml exec -T postgres psql -v ON_ERROR_STOP=1 -U logistics_prep -d logistics_prep_test -f /tmp/preparation.sql
docker compose -f deploy/data-preparation-2026/compose.yaml exec -T postgres psql -v ON_ERROR_STOP=1 -U logistics_prep -d logistics_prep_test -c "SELECT count(*) FROM competition_preparation.entities; SELECT count(*) FROM competition_preparation.refs;"
```

预期输入计数326/979；再次执行导入应保持计数。SQL只允许目标库名 `logistics_prep_test`，使用事务，不清库；同UUID不同内容触发非空约束失败并回滚，不静默覆盖。SQLite导入也拒绝同UUID内容变化，重复相同输入实际新增/更新为0。上述 PostgreSQL 命令目前未实跑；这些预期不是成功日志。

比赛与真实数据来源方案见 `docs/data/competition-2026.md`。真实数据未下载、未接入；32种实体中运行时结果为空是有意保留，不能据此声称所有业务已交付。
