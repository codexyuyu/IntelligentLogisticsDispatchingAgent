# R24 增量日志 · 2026-10-17 · 用户授权全栈 AC/B/C

- 基线 R23；用户已在 Windows 实机确认 R23 订单/车辆/路径/归档/地图全部正常。用户明确授权修改 A/B/C/前端及共享模块，历史 OWNERSHIP 仅用于追溯。
- 新增 OSRM Table/Route 适配：路网时长与距离驱动既有 R20 RoutingRequest，结果仍用原求解器和独立校验；用求解结果的停靠次序获取道路几何，存档和地图区分来源，不改变 R17～R20 求解核心及验收归档。
- 新增仅可显式执行的 R24 增量 SQL：六类表（温区、库存批次、订单/车辆参数、资源、装车作业），加 FK/CHECK 约束。不重写七张旧业务表，不自动生成虚构值。另有六份无数据 CSV 模板和只在 --apply 时以单事务导入的命令。
- 适配 R24 补录数据到原 Order/Vehicle/WarehouseHandoff；校验单仓/温区/批次总数量/装车作业资源/时间窗等，否则拒绝启动已验证模式。新增 /readiness 汇总接口，React 页面可选择 legacy/verified 和 straight_line/OSRM 两种正交来源。
- HTTP 原主接口契约未变化（PostgreSQL 子应用独立 OpenAPI）；原 R22 存档表与旧方案保持兼容；OSRM 新预览归档到原独立表，旧存档地图不重写。
- 验证：45 项选定后端/契约回归测试通过（包括 OSRM 格式、不可达失败、R24 补录约束、旧接口回归）；`export_contracts.py --check`、`build_file_map.py --check` 均通过；R23 前端接线测试 10 项通过；新改动 TS/TSX 无解析错误。当前环境无真实 PostgreSQL/OSRM/OR-Tools 可用，不声称实机端到端通过；完整前端 npm ci 被当前容器运行环境限制阻塞，TSX/TS 仅进行静态语法和接线检查。
- 后续：真实业务资料填报、OSRM 本机服务、已验证模式实际求解与 React 本机验收；真实业务确认/写回、复杂仓内调度与真实交通数据另行开发。
