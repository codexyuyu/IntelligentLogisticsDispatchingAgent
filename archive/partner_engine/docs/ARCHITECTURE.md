# 架构与装配

一个仓库、FastAPI 模块化单体、PostgreSQL、React。CPU 求解由受限 worker 执行，后续作业用数据库持久化/租约；当前仅 HTTP 健康检查和占位接口可启动。

依赖方向：api → application → ports/contracts/domain；adapters → ports/contracts；domain → 标准库及 common。bootstrap 组合各 adapter。Pydantic 只用于 contracts 等边界，domain 保持纯规则，不复制契约实体。

| 模块 | 文件入口 | 负责人 |
| --- | --- | --- |
| 仓储排程 | adapters/warehouse/cp_sat_scheduler.py | AC |
| 运输求解 | adapters/routing/ortools_solver.py | B |
| 矩阵 | adapters/matrix/fixed.py | B |
| 仿真 | adapters/simulation/simpy_simulator.py | B |
| 协调/确认/异常 | application/coordinator.py、confirm_plan.py、handle_event.py | AC |
| 领域校验 | domain/*_rules.py、inventory.py | AC 与 B 按所有权 |
| 存储 | adapters/persistence/、migrations/ | AC 集成，B 提本域需求 |
| 模型 | adapters/llm/ | AC |
| 前端 | frontend/src/features/ | 用户侧 Codex |

首月固定两仓所属、四车二十单、一日窗口。仓储与运输必须交换真实就绪/到达时间并共同验证。未来扩展在 docs/ROADMAP.md 声明，不默认支持所有预留字段。

正式确认是唯一库存/资源承诺入口。验证通过、版本一致、哈希一致才确认；重排保留事实并原子替换未执行预留。模型用于理解/解释，不能绕过校验。

当前骨架中的部分私有函数尚无参数，是明确的实现占位，不是供其他模块调用的公共契约。跨边界必须从 ports 使用已经固定的类型签名；实现私有函数时可以细分，不能随之另建对外协议。
