# R25 · AC/B/C · 2026-10-18

- 来源：用户对 R24 3D 驾驶舱与回放卡顿、单调线路提出修改，并明确授权优先 R25：流畅时间轴、四车演示、真实 OSRM 3D 路形与镜头互动；R26 深度仓库暂缓。
- 修改：`frontend/src/hooks/useSimClock.ts`、`components/DigitalTwin3D.tsx`、`lib/replayPaths.ts`、`lib/fleetDemo.ts`、dashboard/simulations/postgres 页面、appTypes/API、本地 OSRM 预览 GeoJSON 停靠点元数据。增了 UTF-8-BOM Windows 启动脚本以避免 R24 曾遭遇的中文乱码（无新表迁移）。
- 独立四车演示用现有快照订单/车辆，**明确非真实求解结果**；正常规划仍使用历史算法输出、不改 KPI。路网路线仅使用真实 OSRM GeoJSON；无 OSRM 就标记示意。
- 安全：旧业务表/调度/归档/扩展业务表/契约/旧 R17-R20 证据全部保持不变；OSRM `stop_coordinates` 是预览数据内只读附加元数据。
- 测试：后端定向 46 passed（含新增 `test_pg_r25_replay.py`）；`frontend/scripts/test-r25-replay.cjs` PASS；原 R23 UI 接线测试 PASS。frontend TS/TSX global TypeScript 转译语法校验通过，**完整 npm 构建和浏览器帧率尚未实测**，因隔离环境安装 npm 依赖阻塞。Windows `npm ci && npm run build && npm run dev` 待用户运行。
- 文档：[R25 指南](../../R25_TWIN_REPLAY_FLEET.md)。R26 仓库内景/叉车演示、R27 业务事件闭环均不属于本轮。
