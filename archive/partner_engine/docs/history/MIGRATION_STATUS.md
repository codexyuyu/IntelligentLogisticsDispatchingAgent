# 当前项目迁移状态

## 当前正式开发基线
- `backend/`：团队统一 FastAPI 后端基线，承载新架构模块与 B-02 Routing。
- `frontend/`：团队统一 React 前端基线。
- `contracts/`：团队公共接口契约。
- `algorithm-service/`：保留原 910 的 B-01 CP-SAT 实际算法服务，作为现阶段回归/迁移基线。

## 原项目完整代码保留
- `frontend-legacy-vue3/`：原 910 项目的 Vue3 + Vite + Element Plus 前端。仅作为旧业务前端保留，不覆盖正式 React 前端。
- `backend-legacy-springboot/`：原 910 项目的 Spring Boot 业务后端。仅作为迁移过渡/参考，不作为新功能开发入口。
- `legacy-reference/db/`：原项目数据库相关 SQL/升级脚本，仅供参考；本次没有执行或修改数据库。
- `legacy-reference/docs/`：原 910 项目说明与历史文档。

## B-02 当前方向
B-02 Routing 应继续在 `backend/` 的统一架构中实现，不再向旧 `algorithm-service` 或 Spring Boot 增加新业务逻辑。

## 数据库原则
本次没有执行数据库迁移，没有 ALTER/CREATE/DROP 业务表。旧数据库脚本仅作为参考材料保留。

## 敏感配置
没有把旧项目本地 `.env` 密钥文件复制到合并包；仅保留非敏感的示例配置文件。
