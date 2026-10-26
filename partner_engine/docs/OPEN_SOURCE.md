# 参考来源

实际计算拟使用 [OR-Tools](https://github.com/google/or-tools)（Apache-2.0）和 [SimPy](https://gitlab.com/team-simpy/simpy)（MIT）。当前正式 adapters 仍未实现，历史探针在 archive/reference_demos。

结构/业务参考：[FastAPI 全栈模板](https://github.com/fastapi/full-stack-fastapi-template)、[Timefold 调度示例](https://github.com/TimefoldAI/timefold-quickstarts)、[InvenTree](https://github.com/inventree/InvenTree)、[Sentry WMS](https://github.com/hightower-systems/sentry-wms)、[Great Blue](https://github.com/infiniteoo/wms)。只借行为边界，不整包复制业务源码。Great Blue 检出时无明确 LICENSE，不能作为可直接复制的业务代码来源。

Python contracts → OpenAPI → TS 派生流程依据 [FastAPI 响应模型](https://fastapi.tiangolo.com/tutorial/response-model/)、[Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) 与 [openapi-typescript](https://openapi-ts.dev/introduction)。

后续引用代码需记录仓库、固定提交、复用文件、许可证及修改，保留版权/NOTICE。项目自身许可证未指定；内部交接包不自动赋予外部开源许可。
