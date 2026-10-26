# DSH 版本化确认前置提案

状态 proposed；当前 0.1.0，未修改共享契约，未实现 confirm 成功路径。

源码证据：coordinator.py 的 plan_hash 包含 validation/coordination；handle_event.py::_make_new_plan 不包含这两项。CandidatePlan 无哈希算法版本。ConfirmPlanRequest 仅 expected_version、expected_snapshot_version、plan_hash；没有被替换方案 ID。重排会生成新的 plan_id，因此不能据同 ID推断应释放哪份资源。

请乙方冻结：统一规范化哈希字段与算法版本；expected_version 指向候选还是当前已确认方案；replacement_plan_id 及取消/替换行为；资源预留账本身份、库存净增减、工序区间互斥与所有权；快照版本提交后如何推进；幂等键冲突和响应版本；事务失败对应错误。

恢复条件：源代码与契约生成物一致、初始/重排哈希正反例通过。甲方再实现 PlanCommitStore，真实 PostgreSQL 验证同时确认恰一成功、重复幂等不重复预留、旧版本拒绝、替换释放和异常回滚。不得猜测算法接受任一哈希，也不得只检查 validation.status 便写 confirmed。

独立快照适配器已经可开发；不等于版本化确认完成。
