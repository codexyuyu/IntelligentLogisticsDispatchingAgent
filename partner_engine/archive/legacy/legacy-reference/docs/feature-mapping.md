# 功能与代码对应表

| 用户要求 | MVP 实现位置 | 说明 |
|---|---|---|
| 3D 仓库整体 | `frontend/src/components/Warehouse3D.vue` | 用 Three.js 绘制地面、起点、出口、货架。 |
| 单个仓库 / 每个货柜 / 每层货柜 | `Warehouse3D.vue` 的 `viewMode` | 页面顶部按钮切换不同展示粒度。 |
| 点击货架查看库存 | `Dashboard.vue` + `Warehouse3D.vue` | Three.js 射线检测点击货架，右侧显示库存表。 |
| 指标卡 | `MetricCards.vue` + `/api/dashboard` | 总库存、预警、今日入库、今日出库。 |
| ECharts 图表 | `DashboardChart.vue` | 把关键指标变成柱状图。 |
| 添加入库任务 | `Inbound.vue` + `InboundController` | 选择商品和数量。 |
| 推荐货架 | `InboundService.recommend` | 按品类、容量、距离、周转分打分。 |
| 管理员确认入库 | `InboundService.confirm` | 更新 `inventory` 和 `shelf.used`。 |
| 创建出库订单 | `Outbound.vue` + `OutboundController` | 选择商品和数量。 |
| 查询商品货架 | `InventoryMapper.findByProductId` | 找到该商品库存所在货架。 |
| 路径规划 | `PathPlanner.manhattanPath` | 起点→货架→出口的网格路径。 |
| AGV 模拟 | `Warehouse3D.vue` | 黄色小球沿路径移动。 |
| 出库扣库存 | `OutboundService.finishOrder` | 扣减库存和货架占用。 |
| 库存预警 | `WarningService.scanLowStockWarnings` | 库存低于安全库存生成预警。 |
| 货架变红 | `Warehouse3D.vue` | `status=WARNING` 显示红色。 |
| 补货建议 | `WarningRecord.suggestion` | 生成可读建议。 |
| 确认生成补货任务 | `WarningService.confirmWarning` | 插入 `replenishment_task`。 |
| AI Agent | `AiAgentService` | 本地规则 + 实时数据上下文，DeepSeek 可选。 |
| DeepSeek API | `DeepSeekClient` | 通过 OpenAI 兼容 Chat Completions 调用。 |
| WebSocket 实时通信 | `WebSocketConfig` + `WarehouseEventPublisher` | 数据变化后推送 `/topic/warehouse`。 |
| Docker Compose | `docker-compose.yml` / `docker-compose.full.yml` | 本地依赖或完整一键运行。 |
