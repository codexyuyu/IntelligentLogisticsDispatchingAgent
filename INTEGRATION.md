# 集成分支说明（integration/unified-20261026）

本分支把**双方的全部成果放在同一个分支里**：任何人检出这一个分支，就能同时运行甲方产品栈和乙方求解引擎，不需要再分别拉取或合并。

## 组成

| 部分 | 内容 | 来源 |
| --- | --- | --- |
| 仓库根（apps/ packages/ tests/ …） | 甲方完整产品栈：Docker+PG+React 十页前端、OR-Tools 求解 job、PG 持久化 | `dsh/2026-10-23-snapshot` @ `5c12914`（已含 PR #7：R08 三角色 + build_negotiator） |
| `partner_engine/` | 乙方完整项目：R05 契约 0.2.0 + CP-SAT 冷链约束、R08 四角色协商、组合根、R09 观测、演示闭环工具、345 条测试、旧版前端、文档与数据 | 乙方 PR 链 #1–#6 最终状态 `4cb302c`，整树原样搬入，一字未改 |

`OWNERSHIP.json` 中 `partner_engine/` 登记为 A（本清单只允许 A/B 两个所有者且 B 前缀被治理测试冻结）；其内容的真实作者与审查记录见 git 历史与 PR #1–#7。

## 怎么跑

### 甲方产品栈（Docker 一键起）

```powershell
docker compose up -d
docker compose --profile tools run --rm seed   # 导入 tiny_master 演示数据
# 前端 http://localhost:8080，token: dev-operator-token（本地中文前端）
```

> 合并后以本地 `apps/frontend` 中文界面为唯一前端，端口 8080；
> 不再使用 8081 旧工作台或 `apps/frontend-legacy`。

### 乙方引擎（无需 Docker，只需 Python 3.12 + ortools/simpy/fastapi）

```powershell
# 一键业务闭环：真实 CP-SAT 仓储 + OR-Tools 运输求解 → 四角色协商 → R09 观测
cd partner_engine
..\..\path\to\.venv\Scripts\python.exe backend\tools\r09_demo_loop.py --max-orders 3 --budget-ms 12000
# 期望输出：validation=passed，coverage 3/3，cold-chain peaks=1 exposures=3，协商 3/3 confirmed

# 全量测试（345 条）
cd backend
python -m pytest tests -q
```

## 状态边界（如实声明）

- 本分支保留两条代码线：根目录 2.0.0 产品栈与 `partner_engine/` 乙方 0.2.0 引擎；业务契约尚未统一。
- 本地中文前端通过后端 `/partner` 兼容命名空间调用乙方求解/协商/观测接口；正式运输调度仍走 2.0.0 `/api/v1`，两套契约没有混用。
- 乙方引擎的 R05 冷链层为标注 `simulation` 的合成数据，非企业实测。
- 345 条乙方测试是 `partner_engine` 自身结果，不等同于根目录集成测试或正式验收。
