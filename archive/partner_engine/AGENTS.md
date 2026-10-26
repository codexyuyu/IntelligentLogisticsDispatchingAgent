# 合并工程协作入口（2026-10-22）

当前运行根是本文件所在目录，R30-E 为运行基线。先读 [分工协议](COLLABORATION_SPLIT_20261021.md)、[开发与构建规范](docs/DEVELOPMENT.md)、[所有权](OWNERSHIP.json)、[共享契约](contracts/README.md) 和最新增量日志。原 AC/B/C 分工为历史记录；当前两位开发者 DSH / PARTNER 遵守 v2 单写者边界。

本轮任务 INTEGRATION-20261022 已获用户授权：甲方完成前端优化、共享类型复用及构建治理。后续共享契约由乙方串行集成，双方互验，不再沿用“所有角色任意跨模块修改”的旧授权说明。不得修改父目录 demo 历史资产或套用其旧 Gate 状态。

## 开发约束

1. 跨模块数据只从 `backend/app/contracts/` 导入；B 的公开调用只使用 `backend/app/ports/`，不得自定义第二套 Order、Vehicle、RoutingResult 或 JSON 别名。
2. 领域规则只依赖标准库与 `app.common`/领域内部代码；不得导入 Pydantic、HTTP、数据库、OR-Tools、SimPy 或模型 SDK。边界 DTO 在 contracts，application/adapter 负责映射；不要复制一套仅改名的 DTO 到 domain。
3. `application` 依赖 ports/contracts/domain，不能导入 adapters。`bootstrap.py` 是唯一组合根。求解器回调不得联网/查库。
4. 改跨模块接口时执行 DEV_LOG 的完整变更流程；生成 OpenAPI 和 TS 类型，不能手改生成产物。B 内部重构不需要更改公共契约。
5. 改动前读最新日志。每次完成写一份角色命名的增量日志，附测试原始结果和未完成项；同一修改中更新 TODO/文件清单，不能最后靠聊天补交接。
6. 不修改另一角色的实现来掩盖自己的集成问题。记录输入、预期、实际和影响文件；契约未变时用测试替身隔离开发，测试替身不得装配到正式启动。
7. 首月范围以 docs/ROADMAP.md 为准。额外模块保留清楚 TODO，不扩展成微服务或多套智能体框架。
8. 交付前按 README 的验证命令执行；测试只证明其覆盖范围。不能声称骨架健康检查通过就完成调度业务。
9. `archive/reference_demos/` 仅是历史教学参考，使用分钟及简化字典，不属于当前契约；不得从业务代码直接导入。
