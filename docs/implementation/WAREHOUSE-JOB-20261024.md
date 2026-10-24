# WAREHOUSE-JOB-20261024 · 仓储作业链路限定修复

用户要求：检查最新测试日志，继续满足申请书要求；前端暂不修改。

基线：bb15d36；工作根为 DeepSeekHarness/IntelligentLogisticsDispatchingAgent。
本任务修复已有仓储实现，不宣告启动/签收 P16 或任何 Gate。

对应申请书第 4–5 页：仓储作业时间窗、资源指派、求解与可验证结果。
已确认缺陷：application/warehouse.py 使用 hashlib 但未导入；worker 保存的
validation 来自求解器内部，而非现有独立仓储校验器。

精确写入范围：
- apps/backend/src/logistics_backend/application/warehouse.py
- tests/integration/test_warehouse_job_pipeline.py
- docs/implementation/WAREHOUSE-JOB-20261024.md
- docs/implementation/reports/WAREHOUSE-JOB-20261024.md
- tmp/WAREHOUSE-JOB-20261024/**（本任务测试/审计证据）

不修改前端、B 求解器/仿真源码、契约、锁、所有权、旧日志或官方 Gate。
验证使用专用 PostgreSQL 测试容器与真实 worker 子进程/CP-SAT；原服务不停止。
正例检查作业完成、两个前后相接作业、独立校验、原始结果哈希；反例检查
不存在的资源不能被校验为通过、不可行结果不能被当成有解、跨仓任务拒绝。
完整仓储约束建模、仓运联合、仓储 from-job 提交接口不属于本次修复。

执行中新增复现：不可行路径引用运输 Diagnostic 并传入字符串 severity，触发
InvalidInputError，无法返回仓储不可行诊断。用户于本轮明确授权单文件例外：
packages/optimization/src/logistics_optimization/warehouse/solver.py 仅改为导入
既有仓储 Diagnostic；不修改求解模型、公共类型或所有权规则。
