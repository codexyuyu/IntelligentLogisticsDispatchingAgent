# N01-R02 设计示例子任务

结论：本轮定稿设计示例实跑 **268/268，exit 0**；不构成业务验收或 Gate 签收。实际根为 `D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent`，`.git` 不存在。新增文件仅在 `tmp/N01-R02/examples/` 和本目录；旧交接、旧日志、旧示例源码未改。

证据：

- 精确外层命令：`python tmp/N01-R02/examples/capture_examples.py final01`；它实际启动的解释器、argv、cwd、UTC、退出码和输入 hash 保存在 [command](contract-check-final01-command.json)。
- [原始日志](contract-check-final01.log) SHA-256：`da533b48ca41f9003d107e48f8eaa60f53d035e4cce5dddfe90db8cfcd9a60e2`。
- [逐项结果](contract-validation-final01.json)：旧 95 项检查主体保留；新增 173 项，正例 81、反例 92，全部符合预期。114 个规划生成输出在本轮临时目录逐字节复现；本轮登记的 3786 个保护文件未变；治理变动为白名单内 5 项。
- [输入与实例](contract-examples-final01.json)：45 个 EntityKind 成员逐个从当前规范解析；driver 合法；十类事件全部覆盖。traffic 覆盖同矩阵多弧、反向有向弧、跨矩阵、空/重复/自环弧、矩阵选取与版本；weather 覆盖非空唯一节点、矩阵并集、同 region_id 同集合乱序接受/不同集合拒绝、所有受影响矩阵版本前进；仓储六个允许分支和两份引用全值一致；实体 row_version、可空 revision、缺目标和错目标均有正反例。
- 规范及 checker 的当前输入 hash 分别为 `e9286aeaea6cdf553d76ee9d708a1c58aaf3d5363b28fc6582eab12e2f34836b`、`57fa21805c4342784f34677e09d1e14bde178caf46f20c6df42502af5e31da44`。首轮 attempt01 亦 exit 0；两轮实际绑定相同输入，原记录均保留。
- [副本差异](inherited-harness-copy.diff) 和 [源绑定](inherited-harness-source.json) 说明修改：规范 enum 取值、本轮范围/输出路径、manifest 初态来源、保护数量和新增事件谓词。旧源码 SHA-256 保持 `bf93287d4d68e2a05d7cdb3f482da6d196787e6fe3ce980097a907c4eedbfa42`。

限制：

- 新谓词仅检查规范映射与选定设计事实快照，不查询当前 live 状态来重验旧审计引用；未实现或运行领域类、事件接入、数据库、真实 parser/handler/worker、OR-Tools、SimPy、模型或浏览器。
- 原继承适配器对 CalendarDTO 重叠、单独 RegionRef 空节点、OnArc 时间顺序、完整场景 FK/日历绑定的覆盖限制继续存在；新增事件引用检查不宣称修复这些业务或独立 parse-only 语义。
- 场景输入使用当前具名结构和 UUID5 合成身份；CargoType 字符串显式标为未验证夹具值，不把它作为枚举裁定。继承实体适配器只检查字段形状和部分原始值，完整继承 Schema、状态机和业务关联仍由 G02 及对应 Gate 实跑。
- 没有改 JobKind、Scenario 字段、Calendar 或 JobRequest 设计；没有签 Gate、写他人通过记录或启动业务阶段。统一候选与独立复核由 root 处理。

本子任务完成后停写。
