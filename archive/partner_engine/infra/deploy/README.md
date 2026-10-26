# Owner AC：部署

骨架不依赖数据库即可启动。compose.yaml 仅预留本地 PostgreSQL 服务，当前环境未验证 Docker 启动；数据库迁移/持久化仍待实现。默认密码只用于绑定本机的开发容器。

完整部署脚本等到 AC05 验证后再加入，不能提供声称“一键运行完整系统”的空脚本。阶段交付用 scripts/package_demo.py，实际启动见根 README。
