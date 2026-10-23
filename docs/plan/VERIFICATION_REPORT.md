# 规划验证报告

日期：2026-09-12。结果：**PASS**。仅验证本轮AI-CODING-PLAN文档系统；不是任何应用业务Gate签收。

执行命令：`python tools/ai_coding_plan/validate_plan.py --self-test --write-report`。

| 检查项 | 结果 |
| --- | --- |
| tasks | 109 |
| gates | 40 |
| prompt_groups | 14 |
| required_prompt_sections | 24 |
| required_entities | 32 |
| markdown_files | 126 |
| selected_prompts | 109 |
| 检查器正反例测试 | 12 |
| 错误 | 0 |

检查覆盖：任务及Gate DAG无环、依赖存在、Blocks反向一致、严格前阶段Gate、同阶段并行依赖/写文件冲突、14目录和Prompt一对一、24个必需章节、OR-Tools六项算法结构、Files与命令一致、32实体覆盖、需求任务引用、20项Master内容、本地Markdown链接。

所有Task保留planned，G00–G39保留not_run。本次未执行未来pytest/浏览器/数据库/OR-Tools/SimPy/真实LLM/性能测试；未改变旧demo业务代码或外部任务状态。静态通过不能证明算法正确、实际性能或业务可用性，后续必须逐Prompt实现并提交Gate原始证据。

补充验收：两次重新生成的任务清单/Task Graph/109份Prompt逐字节hash一致。另实际运行了缺前置证据的G00签收负例，返回exit code 1且未生成G00.json，符合失败关闭的预期；这不是本次规划校验失败。
