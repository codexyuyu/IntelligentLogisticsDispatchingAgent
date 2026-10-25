# 双人开发分工协议 · v2

日期：2026-10-22。任务：INTEGRATION-20261022（合并后对接、前端与构建规范）。
甲方：用户侧 Codex/DSH；乙方：合作方 Claude。运行代码以 R30-E 加准备数据包的合并工程为唯一基线，本机位于 merged/，所有下述路径相对该目录。合作方收到完整工程后以解压根为准，不依赖父目录 DSH 规划工程。

本版替代 v1。用户已明确授权本轮前端及对接修改，不再保留“甲方禁止修改前端”的冲突规则。双方收到的基线必须用哈希确认，不能假定对方已接收或签收。40 Gate / 109 Prompt 不进入运行工程，也不作为本次业务完成证明。

## 已完成与待验证

- A7 数据适配落点是 scripts/import_preparation_bundle.py、backend/tests/test_preparation_bundle.py、data/preparation/ 和 data/scenarios/prep_*.json；不是原计划的 preparation_ingest.py。T1/A8/B20 已有严格契约及求解测试；字段损失见 prep_import_report.json。
- B1 后端原报告 210 项，合并报告 215 项；这是 MERGE_NOTES.md 的既有记录。本轮结果单列增量日志，不能自动沿用旧通过结论。前端构建与界面检查见本轮日志。
- A7“完成”仅表示文件转换与测试，不表示入正式数据库，也不表示 R05 已支持全部冷链字段。
- R05、R08、R09 完整统一、版本化确认、组合根仍是剩余业务工作，不因本协议更新而完成。

## 单写者与交接边界

OWNERSHIP.json 是机器可读所有权来源。两个人分别是 DSH（甲方）与 PARTNER（乙方），SHARED 由乙方作为公共契约集成人串行处理。不得同时编辑共享文件；一方提出字段清单，另一方集成并连同生成物交付。用户本轮已授权的共享治理文件调整属于例外，已记录日志。

| 工作 | 主写者 | 文件范围 | 依赖与验收 |
| --- | --- | --- | --- |
| R05 冷链模型与独立校验 | 甲方 | backend/app/domain/coldchain_capacity.py、joint_validation.py；backend/tests/coldchain/ | 先由乙方冻结新契约；重叠区间峰值容量、多资源、换批、暴露时长均需正反例，不能仅用总容量积分代替每时刻容量约束 |
| R05 契约与求解器接入 | 乙方 | backend/app/contracts/、ports/、adapters/warehouse/；对应测试 | 以 prep_import_report.json 为输入；真实 CP-SAT 求解后独立校验，不复用建模函数自证 |
| R08 四角色协商 | 乙方 | backend/app/application/contract_net.py；backend/tests/negotiation/ | 版本、轮次预算、过期报价、幂等、确认/撤销；经双方冻结契约接存储，不复制 DTO |
| R09 指标及对照 | 甲方 | backend/app/evaluation/；backend/tests/evaluation/ | 14 指标口径、覆盖率、配对种子和等预算；统一既有实验，失败/超时保留，旧证据不冒充新实验 |
| 版本化确认与快照 | 甲方 | backend/app/adapters/persistence/plan_commit.py、snapshots.py、pg_plan_commit.py、pg_snapshot_store.py；backend/tests/persistence/；backend/migrations/ | PlanningSnapshotStore / PlanCommitStore；真实 PostgreSQL 的 CAS、并发、幂等、原子回滚测试；迁移串行交接 |
| 组合根 | 乙方 | backend/app/bootstrap.py、api/dependencies.py、main.py、application/ 中装配点 | 对接上述端口；移除 application→adapters 装配依赖；不装配测试替身 |
| 前端维护与本轮优化 | 甲方 | frontend/（generated 文件由共享契约生成） | 黑白灰、无蓝紫色、无渐变；npm ci、契约检查、类型检查、专项测试、生产构建及页面检查 |
| 公共契约集成 | 乙方 | backend/app/contracts/、ports/、contracts/、scripts/export_contracts.py | 一次交付源、版本、OpenAPI、TS 类型和消费者适配，双方复跑 |

未列业务路径归乙方，甲方不得另建同功能模块绕过所有权。前端需要尚未存在的新指标/协商接口时，先由双方冻结契约，不能用假数据代替。原 AC/B/C 标签为历史角色，不代表当前有三名开发者。

## 共用变量与编译规则

完整命令及配置见 docs/DEVELOPMENT.md。公共业务类型只源自 backend/app/contracts；前端通过 generated.ts 和 appTypes.tsx 的别名复用，接口字段保留 snake_case。契约版本源自 common.py，不手改 VERSION。PG 子应用的手写 TS 类型仍需与后端一起改，已列为明确限制。

变更顺序：契约提案 → 单写者修改源与版本 → export_contracts.py → npm run contracts:generate → 两端 drift 检查 → 类型检查/后端测试/前端专项检查与 build → 对方复验。不是所有新增字段都必然兼容，也不是所有新增字段都必然破坏；按必填性、语义和旧端拒绝额外字段的行为判定。

统一验收入口：在工程根使用本工程 .venv 执行 `python scripts/verify_delivery.py --out-dir ../tmp/新的交接目录`。Python 3.12、前后端锁文件、安装顺序、端口、环境变量、构建产物和故障定位均在 DEVELOPMENT.md；脚本任一检查失败整体非零，不生成虚假签收。

## 合并、证据与恢复条件

当前本机没有 Git 仓库；不虚构分支或提交。交付限定文件补丁和修改前后 SHA256，接收方先核对旧哈希；冲突逐文件合并，不整包覆盖。未来使用 Git 时双方另行约定远端与分支。

每次交接必须包含：任务与文件范围、基线和新哈希、契约版本、Python/Node/npm 版本、安装与验证命令、原始日志及退出码、未验证外部服务、待对方处理项。新候选使受影响旧证据失效。实现者自测与合作方独立复验分开记录；本版不代签乙方验收。

禁止吞异常、伪造成功、删除失败用例、skip/xfail 换通过；独立校验器保留。健康接口或前端构建通过不等于业务交付。外部凭据缺失时注明责任方和恢复条件，不把模型/数据库测试替身称为真机联通。
