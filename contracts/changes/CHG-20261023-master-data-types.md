# P02-02 具名类型解阻决定

日期：2026-10-23。责任者：Codex 实现会话。依据：用户要求“解决阻塞”；这是本轮设计决定，不冒称历史冻结结论或独立验收。

## 原因与范围

DOMAIN_CATALOG 引用了尚未实现的 CargoType、Qualification、Skill、OperationKind、EquipmentKind。上一轮将 CargoType 也列为无取值依据不准确：docs/prompts/OPTIMIZATION-PLAN-20261020.md 与 docs/data/database-integration-guide-20261020.md 已指定 GENERAL/FROZEN/CHILLED。

精确写入白名单：本文件；packages/domain/src/logistics_domain/orders.py；packages/domain/src/logistics_domain/resources.py；docs/implementation/P02-02.md；docs/implementation/reports/P02-02.md。均为 A 范围；不修改 B 模块、旧冻结文件、states.py、规划生成物或官方验收记录。

## 类型决定

| 类型 | 唯一定义文件 | 形状和线格式 |
| --- | --- | --- |
| CargoType | orders.py | StrEnum：GENERAL="GENERAL", FROZEN="FROZEN", CHILLED="CHILLED"；不默认推定类型，不接受未登记别名 |
| Qualification | resources.py | 名义字符串代码类型；非空、无首尾空白，大小写保留，按完整代码精确匹配；词表由主数据提供，不宣称法定资质认证 |
| Skill | resources.py | 与 Qualification 独立的名义字符串代码类型；同样的编码规则；不凭技能名称自动赋予作业权限 |
| OperationKind | resources.py | StrEnum：receive/dispatch/sort/load/unload/setup；来源 DOMAIN_CATALOG WarehouseTask |
| EquipmentKind | resources.py | StrEnum：sorting/handling；当前封闭实现集合，来源 TEST_FIXTURES W1/Scenario B；扩展需要新的契约决定 |

Qualification/Skill 采用独立 str 子类，JSON 保持字符串；领域构造显式使用对应类型。后续 DTO 将代码映射为领域类型，不定义第二套枚举或依赖框架的领域类。空资质/技能集合表示未声明能力，不补默认资质。

## 版本、迁移与兼容性

业务 schema_version 保持 2.0.0：补齐未实现的具名类型，无现有正式实体数据可迁移；决定 ID 为 CHG-20261023-master-data-types。未声明历史 2.0.0 输入已通过新类型验证。JobStatus/ErrorCode 不变。

迁移顺序：domain（本轮类型）→ DTO（后续 P02-02 entities.py）→ ports（当前无调用方）→ 调用方（后续 P02-02 实体与 P07/P08）→ 测试（用户本轮禁止）→ 生成物（P02 schema 导出时统一生成，当前不手改）。历史 demo 不导入、不迁移。回滚仅撤销本轮新增类型和引用，禁止恢复伪造的通过状态。

受影响调用方：尚未实现的 Cargo/Vehicle/WarehouseZone、Driver/Worker/Dock/Equipment 及其 DTO。当前正式源码中未找到这些类型的现有实现。后续 schema 使用上述唯一源；无本轮需修改的已生成客户端。

## 校验引用与证据

本轮不产生 version_id、parent_version_id 或 snapshot_hash；由后续规划/快照任务生成。P02-02/G02 尚未验收。新增代码改变候选身份；G01 是否受新增文件/候选算法影响须由后续独立影响审查判断，不直接沿用历史签收身份。不重算或覆盖旧冻结哈希、review、precheck、Gate。

未运行测试、导入探针、编译或 Gate；仅阅读源码、检索引用、核对写入及计算文件哈希。本决定解除类型设计缺口，不代表 P02-02 整体完成。
