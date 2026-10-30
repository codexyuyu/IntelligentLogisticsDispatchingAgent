# 2026-10-31 队友仓库三维建模合并说明

## 合并基线
- 业务基线：`coldchain_proposal_approval_and_integrated_delay_20261030.zip`（包含联合调度工作台、调度驾驶舱、流程导航、优化收益对照、审批前方案评估）。
- 三维来源：`coldchain-8c684fa-20261031.zip`。
- 合并原则：业务基线优先，队友的单仓三维场景及必要几何/交互依赖优先；不整包覆盖，不回退业务接口。

## 采用队友版本的文件
1. `apps/frontend/src/components/WarehouseTwin3D.tsx`
2. `apps/frontend/src/features/warehouseTwin/Page.tsx`
3. `apps/frontend/src/lib/warehouseTwin.ts`
4. `apps/frontend/src/lib/warehouseFixtures.ts`
5. `apps/frontend/src/lib/warehouseTwin.test.ts`

## 主要变化
- 收货区与叉车充电区布局交换，调整叉车充电点、输送线起点及回转路径。
- 收货卷帘门移至新收货入口；收货—质检—分拣输送路径贯通。
- 冷风机模型细节增强，包含风扇、换热器、管路、吊架等；支持在三维场景和侧边设备列表选中冷风机。
- 货物选中轮廓、设备视角及相关几何交互更新。
- 合入队友对应的仓库几何单元测试，以保持模型与测试期望一致。

## 未覆盖的功能
- 原基线的 `DigitalTwin3D.tsx`（运输车辆三维视图）保持原样：队友包中该文件与业务基线相同。
- 保留异常审批、真实方案对比、局部重调度、Agent、数据库后端与既有页面。
- 未采纳队友包中的较旧业务页面/API 实现，避免回退近期功能。

## 检查与限制
- TypeScript `tsc --noEmit -p apps/frontend/tsconfig.json` 通过（使用已有依赖目录，仅做静态检查）。
- 按用户要求未运行 Vitest、浏览器/端到端验收，未启动服务。
- 未连接或修改 PostgreSQL 5433/5434；未进行 Git push/merge。
- 三维显示效果、运行时性能和叉车净空需留待最终统一验收。
