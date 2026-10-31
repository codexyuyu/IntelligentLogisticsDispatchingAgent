# 三车故障救援：DeepSeek 工具调用协同

## 使用入口
「异常处置」→「AI 协同处置」→「启动 AI 协同处置」。

后端 `POST /api/v1/integration/showcase/vehicle-breakdown/ai-collaborate`
复用 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL` 和现有 OR-Tools 求解器，按受控顺序执行：

1. DeepSeek 请求 `get_incident_context`，后端返回三车八单固定合成故障场景。
2. DeepSeek 请求 `solve_rescue_dispatch`，后端运行真实 `solve_breakdown_showcase()`。未求出或未通过校验时不产生可批准候选。
3. DeepSeek 请求 `compare_rescue_plans`，后端读取求解指标，比较故障后不救援与候选（若有效）。
4. DeepSeek 解释工具证据；审批需由操作员手动点击，且仅更新浏览器演示会话。

这是**受控工具链**：本版案例固定为“车辆02故障 → 跨车接管 O4/O5”，模型并未自主生成路线，也没有自由切换任意业务策略。模型不具备数据库写入、正式派车或审批工具。模型调用与工具步骤会显示在页面，未配置或调用失败不会冒充 AI 成功。

## 降级与验收
- 如果没有真实 DeepSeek 密钥，点击 AI 入口会显示“未配置”，可使用「仅使用 OR-Tools 求解」按钮。后者不标注为 AI 协同。
- 模型只要没有按照规定发起工具调用，后端拒绝后续步骤；不写数据库、不自动批准。
- 求解器返回的 `status` 和 `candidate_valid` 仍决定能否批准，不能由模型回答覆盖。
- 即使说明阶段调用失败，已返回并校验的求解结果仍保留，但模型状态会显示“说明失败”。
- 完成审批后「仿真回放」使用同一三车演示会话。

检查命令（不访问数据库）：

```sh
PYTHONPATH=apps/backend/src:packages/agents/src:packages/domain/src:packages/contracts/src python -m pytest tests/unit/test_ai_fault_rescue.py -q
node node_modules/typescript/bin/tsc -p apps/frontend/tsconfig.json --noEmit
```

本环境完成了 Python 5 项测试和 TypeScript 检查。当前环境没有 OR-Tools，也未连接真实 DeepSeek，**真实模型端到端与本地 OR-Tools 救援成功仍需在用户环境验收**；不能声称本轮完成了实时模型 E2E。未操作 PostgreSQL 5433 / 5434。
