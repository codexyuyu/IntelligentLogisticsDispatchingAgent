# 运输数字孪生重构（集中交付）

## 基线与范围
以 `coldchain_ai_agent_decision_collaboration_20261031.zip` 为基线，本轮修改只集中在 `apps/frontend` 的运输数字孪生几何、展示与回放。保留 DeepSeek/Agent、OR-Tools、异常审批、后端 API 和 PostgreSQL 迁移；队友的仓库 3D 模型及其五个配套文件不做修改。

## 修复与功能
1. **多车可见性**：按真实 `vehicleId` 生成独立 Three.js 车辆对象；增加全车队列表、独立颜色和车号、行驶/待发车/停靠/完成状态、点击单车高亮。相同仓库节点的等待车辆按稳定编号放在不同可视车位；示意道路上的重叠行驶使用稳定车道偏移，不改变后端车辆逻辑坐标、速度、时刻和求解路线。离开/返回停车位的 8s 视觉过渡避免模型突然跳变；真实地理道路坐标不做车道位置篡改。
2. **道路与场景**：示意路径从生硬的直角折线改成带转角过渡的路面中心线，创建有路肩、柏油路面和虚线中心标识的几何，去除密集黑色障碍方块和覆盖道路的调试网格。冷链配送中心增加实体仓库、屋顶、冷机、卷帘门、装卸月台及停车位；客户配送节点增加建筑、门面及可读编号。
3. **地图交互**：增加摄像机鸟瞰重置、选车跟随、路线显隐、路线选中高亮；把生 UUID 收进详情辅文，正文使用“冷链车 01/02”等编号。
4. **回放**：现有 v0/candidate/active 版本切换保留；新增双视窗同一时刻的 v0 与 candidate 对照、异常时刻标记。后端已存候选轨迹有时间偏移，因此 StageReplay 不再额外应用 `holdWindows`，避免同一延误双重计时。
5. **透明度**：默认数据只有求解节点矩阵，没有地理道路坐标。因此示意线路、建筑、可视停车位不是实测 GPS，也不改变车辆真实停靠顺序和里程/费用；界面明确标注。双画面对比左侧是原 v0 基线，**不是**“简单顺延”策略，量化收益仍以原有真实 `ProposalComparison` 为准。

## 涉及文件
- `apps/frontend/src/components/DigitalTwin3D.tsx`
- `apps/frontend/src/features/stageB/Replay.tsx`
- `apps/frontend/src/lib/replayPaths.ts`
- `apps/frontend/src/lib/replayVisual.ts`（新增纯视觉辅助方法）
- `apps/frontend/src/lib/replayVisual.test.ts`（新增多车行为测试）
- `apps/frontend/src/styles.css`

## 轻量检查
- `node node_modules/typescript/bin/tsc -p apps/frontend/tsconfig.json --noEmit --pretty false` 通过。
- 以 TypeScript 编译为 CommonJS 后运行纯逻辑断言通过：两车分离、出库连续、原时间与节点未改变、车辆状态等。
- 本执行环境的 Vitest 所依赖的 Linux Rollup 原生可选模块缺失，无法运行 Vitest；未把它报告成测试通过。
- 没有连接 PostgreSQL 5433 或 5434；没有启动前后端、浏览器 E2E、真实 DeepSeek 或数据库迁移；没有 Git push/merge。

## 统一验收重点
1. 使用真实模拟的两辆及以上车辆确认列表数量与模型可见数量一致；在 0s、发车后、汇合路线、返回仓库、异常时刻分别观察。
2. 车辆点击高亮、跟随、鸟瞰重置、路线显隐、暂停/倍速/拖动是否正确，尤其检查大规模真实道路坐标和重复节点的极端情况。
3. 对照显示的 v0/candidate 时间、版本与后端 `/state-at` 一致；审批后 v1 不再二次延误。
4. WebGL 绘制性能、建筑与轨迹重合、不同屏幕尺寸最终以浏览器实测为准。
