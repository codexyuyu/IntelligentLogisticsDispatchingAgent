# 乙方五项对接任务

任务依据：用户 2026-10-25 明确要求完成表中五项；此前仅 R08 的范围限制在本轮扩展。
沿用当前 apps/packages、2.0.0 契约，不合并乙方独立历史，不改官方 Gate 或历史交接。
用户确认暂无企业数据，因此实现导入能力、合成样本与缺项校验；企业数据验收不声明完成。
现有 R08/前端未提交改动保持，不把旧日志作为新候选的通过证据。

按依赖顺序实施：冷链建模与独立校验 → 导入与持久化 → 指标/配对实验 → R08/R09 API 与中文前端。
本轮修改 B 求解器是用户要求补齐分时容量的实现，不用于规避 A 层缺陷；不修改运输或仿真算法。

计划文件白名单（新增文件亦须位于以下明确任务落点）：
- packages/optimization/src/logistics_optimization/warehouse/{solver,coldchain_model}.py
- packages/optimization/src/logistics_optimization/validation/{warehouse,coldchain,joint}.py
- packages/domain/src/logistics_domain/coldchain.py
- packages/contracts/src/logistics_contracts/{coldchain,integration}.py
- packages/evaluation/src/logistics_evaluation/{metrics,complete,paired}.py
- apps/backend/src/logistics_backend/application/{integration,scenario_import}.py
- apps/backend/src/logistics_backend/persistence/{snapshots,integration_models}.py
- apps/backend/src/logistics_backend/bootstrap.py、api/{integration,router}.py
- apps/backend/src/logistics_backend/application/schedule.py（使持久化候选调用联合独立校验）
- apps/backend/migrations/versions/0010_partner_integration.py
- apps/frontend/src/{App.tsx,features/integration/**}
- tests/unit/test_partner_*.py、tests/integration/test_partner_*.py
- scripts/partner_*.py、data/scenarios/partner_*.json
- 本文件、tmp/PARTNER-20261025/**

数据库/浏览器先核验依赖；Docker 当前引擎管道缺失，不重置数据、不伪造运行通过。
