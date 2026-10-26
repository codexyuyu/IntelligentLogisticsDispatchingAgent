# Spring AI 与 Embedding 升级说明

当前 MVP 为了保证零基础同学能稳定启动，AI 部分采用：

```text
实时库存数据 + 业务规则知识库 + 关键词检索 + DeepSeek OpenAI 兼容接口
```

这已经能演示 RAG 思想：AI 回答前先读取仓库数据和规则，而不是凭空回答。

`backend/pom.xml` 已经加入 Spring AI 基础依赖与 BOM：

```xml
<dependency>
  <groupId>org.springframework.ai</groupId>
  <artifactId>spring-ai-openai</artifactId>
</dependency>
```

为什么没有默认启用完整 Spring AI ChatClient？

因为很多同学没有 API Key。完整 ChatClient 自动配置如果写错 key 或模型名，可能导致项目启动失败。比赛原型第一目标是稳定演示，所以默认先用 `DeepSeekClient` 手动调用 OpenAI 兼容接口，并保留 Spring AI 依赖作为升级入口。

后续升级 Embedding 的思路：

1. 建表 `knowledge_chunk`：保存仓库规则、异常处理流程、补货规则。
2. 调用 Embedding 模型把文本变成向量。
3. 用户提问时也转成向量。
4. 找最相似的规则片段。
5. 把这些片段和实时库存一起发给 DeepSeek。

MVP 阶段可以先不用真正向量库，因为比赛评委更关注闭环逻辑是否清楚、系统是否能跑通。
