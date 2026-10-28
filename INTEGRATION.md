# 2.0 集成分支说明

本分支以 **2.0.0 契约** 为唯一运行契约：根目录产品栈、本地中文前端和 2.0 integration
页面组成唯一产品入口。旧 0.2 引擎已归档到 `archive/partner_engine/`，不再参与镜像构建、
后端路由或前端调用。

## 组成

| 部分 | 内容 | 状态 |
| --- | --- | --- |
| 根目录 `apps/` `packages/` `tests/` | 2.0.0 产品栈、Docker/PostgreSQL、OR-Tools、CP-SAT、持久化、R05/R08/R09 | 唯一运行主线 |
| `apps/frontend` | 本地中文前端，端口 8080 | 唯一前端 |
| `archive/partner_engine/` | 旧 0.2 引擎、旧 20 单演练、旧前端与测试 | 只读归档，不参与运行 |
| `archive/frontend-legacy/` | 旧 8080 PR #1 前端构建 | 只读归档 |

`OWNERSHIP.json` 中 `archive/` 归 A；归档代码不出现在 Docker 镜像和运行栈。

## 怎么跑

```powershell
docker compose up -d
docker compose --profile tools run --rm seed   # 导入 tiny_master 演示数据
# 前端 http://localhost:8080，token: dev-operator-token
```

唯一前端入口：

```text
http://localhost:8080/
```

2.0 集成页面：

```text
http://localhost:8080/#/negotiation
```

不再提供：

- 8081 旧工作台
- `/partner` 兼容路由
- 旧 20 单“开始演练”入口

## 2.0 功能

后端实现与兼容说明见 [后端统一实现](docs/architecture/BACKEND_CONSOLIDATION.md)。
联合求解与运输、仓储、仿真共用 Job/Worker；现有同步接口保留，`POST /api/v1/integration/runs?wait=false`
可异步提交。部署时必须同时启动 backend 和 worker。

- 本地中文总览、3D 仓库视图
- 运输求解、候选创建、版本提交、刷新回读
- 2.0 integration 页面：
  - 导入/校验 2.0 场景
  - 仓储 CP-SAT + 运输 Routing
  - 联合校验
  - 四角色协商
  - 14 项指标
  - 冷链与仓运交接
- 7 天跨批次复用

## 状态边界

- 旧 0.2 代码仅作历史参考，不再被运行时代码导入。
- 旧 20 单演练不再提供；业务演示使用 2.0 integration 页面。
- 正式 Gate 签收仍需独立 reviewer 执行，本分支不自行签收。
