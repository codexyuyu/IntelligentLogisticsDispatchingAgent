# 最小部署设计

第一版使用一个后端应用和 PostgreSQL，前端可编译为静态资源一同提供。求解工作进程属于同一应用发布；开发环境另开前端开发服务器。Dockerfile、compose 和锁文件已加入；本环境尚未完成镜像构建验证。

Windows 开发可选原生 Python 与容器数据库，或团队统一 WSL2/Docker；第 1 周只验证一种主路径。依赖选择当时的稳定兼容版本，验证后锁定，禁止按 latest 自动漂移。8 逻辑 CPU/16 GB 是初步测试假设，不是已验证最低配置。

不默认启动万悟、OSRM、Redis、Kafka、向量数据库或 Kubernetes。离线包准备固定场景矩阵、静态工作台和结果示意；开源地图公共瓦片不可批量下载作离线包，见 [OSMF 瓦片政策](https://operations.osmfoundation.org/policies/tiles/)。需要离线地图时使用允许该用途的数据和自托管方案。

业务秘密保存在服务端环境配置。运行包记录版本、迁移、场景导入、恢复演示初始状态和健康检查方法；脚本在实现并实测后再加入。

## 2026-10 第一版本地产品栈

当前仓库已加入 `Dockerfile`、`docker-compose.yml`、前端 Nginx 镜像和开发种子服务：

```bash
docker compose build
docker compose up -d db backend worker frontend
docker compose run --rm seed
```

打开 <http://localhost:8080>，开发 token 为 `dev-operator-token`（hash 在 compose 的
`LOGISTICS_SETTINGS_JSON`，仅限本地）。API 直连 <http://localhost:8000/api/v1/health>。

- 本环境通过镜像站拉取基础镜像后已成功构建 backend/frontend/seed，并启动 db/backend/worker/frontend；health 与登录订单查询返回 200。
- 运输 Job 已通过 Docker 栈完成：worker 在约 6s 内返回，结果查询返回 1 条 route（solver 使用 5s 服务端上限）。
- backend/worker 共享 `results` volume，结果 artifact 可被 API 读取。
- 这是本地产品候选，不是 Gate 签收版本。
