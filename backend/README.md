# 后端设计入口

后端按 domain、application、ports、adapters、api 组织，具体边界见 [架构](../docs/03-architecture.md)。本轮仅有设计说明。

未来采用 FastAPI、Pydantic、SQLModel/SQLAlchemy、Alembic、PostgreSQL；领域对象保持纯 Python 类型，通过适配转换避免 ORM 绑定。参考官方全栈模板的目录、迁移、认证和接口生成方式，不复制其所有部署、邮件与管理功能。

第一项实现应是结构化场景导入、领域规则和纯函数校验，然后连接求解器。必须先让不依赖大模型的完整调度闭环运行。
