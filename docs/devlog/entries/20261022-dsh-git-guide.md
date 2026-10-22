# 2026-10-22 · DSH · Git复制命令手册

任务 GIT-GUIDE-20261022：用户要求双方可直接复制执行的上传、同步及问题处理文档。

新增 docs/GIT_COLLABORATION.md，覆盖 PowerShell 准备、单方初始化/另一方克隆、任务分支、选择文件提交、验证和证据上传、PR复验、main同步、冲突、stash、取消暂存、revert、误在main开发、地址/权限问题与离线bundle。README 与 DEVELOPMENT 加入入口，刷新 FILE_MAP。未修改业务实现或公共契约。

核查时合并工程没有 .git。文档中的远端、身份、克隆目录由实际操作者输入，未猜测或保存远端地址。没有初始化真实工程、提交、推送、邀请用户或修改全局Git配置。

验证：全部PowerShell代码块语法解析；在独立临时bare远端和两个工作副本中演练核心流程。详细结果见父目录 tmp/GIT-GUIDE-20261022。验证仅证明本机Git命令流程，不证明远程GitHub认证、权限或分支保护已配置。
