# B-06 / Routing 规模扩展诊断修复

本版本在保持现有 FastAPI/OpenAPI/CP-SAT/Routing/SimPy 架构与共享契约不变的前提下，修正并增强 B-02/B-03 的规模扩展路径。

## 后端修改

- B-03 协同预算按订单规模自适应：S20 约 70% Routing、S50 约 85%、S100 约 90%，避免无目标的仓储可行性搜索提前吞掉 VRPTW 搜索预算。
- Routing 首选解策略改为 `PARALLEL_CHEAPEST_INSERTION`，并保留 `PATH_CHEAPEST_ARC` 作为超时后的确定性回退。
- 增加按温区聚合的重量/体积总容量必要条件预检查，可将明显的运力不足直接标记为 `infeasible_proven`，避免无意义的长时间搜索。

## 前端修改

- B-06 对新增容量不足、无兼容车辆、Routing 无解等错误码给出更具体的诊断文案。
- 成功/失败记录仍然保留，CSV 口径不变。

## 验证

- Python compile：通过。
- `pytest -q backend/tests`：37 passed。
- 当前验收容器没有安装 OR-Tools，因此未在容器内宣称完成真实 S50/S100 求解实跑；需在 Windows 环境重新 `npm ci` / 安装后端依赖后验证。
