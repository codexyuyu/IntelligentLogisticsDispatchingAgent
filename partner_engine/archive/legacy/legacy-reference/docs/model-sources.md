# 仓储 3D 模型来源与当前 Demo 建模策略

本 Demo 当前没有直接打包第三方 GLB 文件，原因是：

1. 第三方模型通常体积较大，会显著拉长首屏加载时间；
2. 不同来源模型风格、材质、坐标轴和比例差异较大，容易破坏展示统一性；
3. 有些免费模型需要署名或登录下载，直接打包到项目里可能不利于后续交付。

因此当前版本采用 Three.js 程序化建模：统一低多边形工业风货架、货物箱、叉车、仓库地面和区域边界。后续如果需要替换成 GLB，只需要在 `frontend/src/components/Warehouse3D.vue` 中把 `addRackShelf()` 和 `buildForkliftModel()` 替换为 `GLTFLoader` 加载模型即可。

可选开源/免费模型资源：

- Kenney Factory Kit：适合工厂/仓储/输送带等低多边形工业资产，CC0。
- Kenney Conveyor Kit：适合输送带、工业建筑和仓库辅助道具，CC0。
- Sketchfab Warehouse Rack：可筛选 Downloadable / CC0 / CC-BY 模型作为后续补充。
- Sketchfab Forklift Low Poly：可作为叉车 GLB 替代模型，注意 CC-BY 需要署名。
- confxsd/3d-warehouse-simulator：Three.js 仓储可视化参考项目，可参考其 3D 库存/路径演示思路。

建议后续统一模型规范：

- 格式：优先 GLB；
- 风格：低多边形工业风或 PBR 工业写实风，二选一，不混搭；
- 单位：米；
- 坐标：Y-up；
- 单模型面数：货架 < 10k，叉车 < 50k；
- 贴图：单张颜色贴图或 1K/2K PBR 贴图；
- 命名：`rack_standard.glb`、`forklift_lowpoly.glb`、`pallet_box.glb`。
