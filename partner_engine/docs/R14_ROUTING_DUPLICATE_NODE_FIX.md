# R14: S50 / seed 17 Routing 修复与实验说明

## 状态说明

来自用户 Windows 实验的已知事实：R13 运行 S50 / seed 17 返回 `routing_solver_failed:wh_1:ROUTING_NO_SOLUTION`，任务 ID `job_715df47d0e8b4a03915d`。该结果是失败记录，不能改写成成功。

R14 是针对该问题的代码修复，**未在当前构建环境以真实 OR-Tools 完成 S50 求解**。因此任何“R14 已解决 S50/S100”的结论都必须以用户 Windows 实跑为准。

## 发现的结构性错误

B-02 为每笔订单的每辆兼容车辆创建内部副本，并使用 `AddDisjunction(..., max_cardinality=1)` 加 `sum(active_vars)==1`（必服务订单）。

但 R13 又对每个副本调用 `routing.VehicleVar(index).SetValue(vehicle_idx)`。在 OR-Tools Routing 中，未激活节点的 `VehicleVar` 应为 `-1`。将其无条件固定为具体车辆，等于禁止该副本成为未激活节点。只要订单有两个或更多兼容车辆，约束就可能互相冲突。S20 每温区通常只有一辆车，因此不一定暴露；S50/S100 按温区扩容车辆后更容易出现。

R14 改成：

```python
active = routing.ActiveVar(index)
solver.Add(routing.VehicleVar(index) == (vehicle_idx + 1) * active - 1)
```

结果：`active=1` 时车辆编号固定为 `vehicle_idx`；`active=0` 时该副本车辆编号为 `-1`。只允许选一个副本的语义保持不变，未修改现有 API 或数据契约。

## 其他修正

- 容量必要条件仅统计**必服务订单**，避免可放弃订单导致错误的容量无解结论。
- Routing 无方案时追加仓库、订单量、必服务订单量、车辆数、内部副本数量、预算和实际求解耗时。**这只是诊断上下文，不代表证明不可行**。
- 回退策略只有确实剩余搜索时间才执行。
- B-06 页面将规模选中状态显示为“✓ 已选/未选”，默认 S50 + seed 17，新增“R14 定点验证”按钮，Seed 预览与运行统一校验与去重，避免空白误算 seed 0。

## 回归与验证

本构建环境运行 `cd backend && PYTHONPATH=. pytest -q tests`：**39 passed, 1 skipped**。其中 1 个新增的真实 Routing 集成测试因 OR-Tools 未安装而跳过。Python 源码也通过 `compileall`。

由于构建环境无法访问包索引，未成功安装 `ortools==9.15.6755` / `simpy==4.1.1`。前端 TypeScript 完整编译所需 npm 依赖在构建环境中不可用，也未宣称已在 Windows 完成验证。

## 用户 Windows 环境验证顺序

1. 解压 R14，并确保整个 ZIP 第一层只有 `915_B06_TWIN_REFRESH_BENCHMARK_R14/` 项目文件夹。
2. 退出旧的 R13 后端/前端，从 R14 目录启动：

   **后端**（PowerShell）：

   ```powershell
   cd "D:\1aaaqianduan\915_B06_TWIN_REFRESH_BENCHMARK_R14\backend"
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

   检查 `http://127.0.0.1:8000/docs`。

   **前端**（另开 PowerShell）：

   ```powershell
   cd "D:\1aaaqianduan\915_B06_TWIN_REFRESH_BENCHMARK_R14\frontend"
   npm ci
   npm run dev
   ```

   打开 `http://127.0.0.1:5173/`。

3. B-06 → 点击“R14 定点验证：S50 / 17” → 应显示 **当前将运行 1 组实验** → 点击“运行批量实验”。
4. 记录原始结果，成功时保存距离/准时率/耗时/Plan；失败时保存完整错误码和任务 ID。
5. 如果 S50/17 成功，先跑 S20/17 回归，再跑 S50 5 seeds，最后再扩 S100；如果失败，检查新的失败诊断，**不修改结果**。

可选：在安装了 OR-Tools 的本地环境，运行：

```powershell
cd "D:\1aaaqianduan\915_B06_TWIN_REFRESH_BENCHMARK_R14\backend"
python -m pytest -q tests
```

新回归测试 `tests/transport/test_r14_duplicate_vehicle_integration.py` 会实际求解“一单，两辆兼容车”的案例，并执行独立运输校验。
