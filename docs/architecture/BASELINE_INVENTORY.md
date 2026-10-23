# 旧 demo 基线资产登记（P00-01）

本文逐项登记 v0.1 旧 `demo/` 基线的文件、路径、哈希、责任方、处置分类与能力证据，作为后续迁移的唯一证据底账。本文是可复核的证据记录，**不是实现声明**：文件存在不等于功能完成，哈希一致只能证明该文件在基线日期未被改动。

## 1. 基线与生成出处

| 项目 | 值 |
| --- | --- |
| 基线根目录 `source_root` | `demo/` |
| 基线日期 `baseline_date` | 2026-09-10 |
| 计划版本 `plan_version` | 1.0.0 |
| 登记清单 `schema_version` | 1.0.0 |
| 任务 ID `task_id` | P00-01 |
| 生成器 `generated_by` | `tools/ai_coding_plan/baseline_inventory_generate.py` |
| 哈希算法 `hash_algorithm` | sha256 |
| 机器清单 | `docs/architecture/BASELINE_INVENTORY.json` |
| 条目总数 | 173 |
| 条目类型 | 173 个真实文件（每条都记录由磁盘现场计算的 sha256，无 `null`） |
| 责任方分布 | A 163 条、B 10 条 |

旧基线为 v0.1 二人协作骨架，包含可运行但业务未实现的 FastAPI 应用、契约样例、前端展示壳、测试与脚本，以及打包交付物 `demo.zip` 与校验文件 `demo.zip.sha256`。基线的实际能力边界见第 9 节。

表内 `target_path` 分两类：写在旧基线内部的路径（如 `demo/README.md`）表示原地只读留存，其他路径都是未来任务的交付目标，在本文件写作时均不存在。旧到新的完整映射、负责任务与转换差异登记见 `docs/architecture/MIGRATION_MAP.md`。

### 1.1 生成与校验命令

```powershell
python tools/ai_coding_plan/baseline_inventory_generate.py
python tools/ai_coding_plan/baseline_inventory_generate.py --check
```

`--check` 以磁盘真实文件重新计算哈希并重建清单文本，若与 `docs/architecture/BASELINE_INVENTORY.json` 不一致则以退出码 1 报 `BASELINE_INVENTORY.json is stale; regenerate it`，一致时打印 `BASELINE_INVENTORY.json up to date (173 entries)`。因此下面每张表中的 sha256 都可由该命令复现。

### 1.2 责任方口径

旧 `demo/OWNERSHIP.json` 以最长前缀匹配决定责任方（未匹配时默认 A）。B 的 10 条落在运输、矩阵、仿真及相关契约样例上，其余（含共享契约与前端）归 A。

## 2. 处置分类统计

处置分类来自清单的 `disposition` 字段，四类合计 173 条。

| disposition | 条目数 | 含义 |
| --- | --- | --- |
| `reference` | 99 | 只读留存的历史证据：不进入新代码，作为迁移输入或反例被引用。 |
| `adapt` | 16 | 规则、模板或约定可沿用，但路径、命名与结构必须按 v1 重写。 |
| `rewrite` | 51 | 必须在新目录按 v1 契约重新实现；旧文件只作需求与反例输入，不复制其代码结构。 |
| `reuse` | 7 | 端口或样例可作为新实现的起点，但只有在对应任务重新验证后才可复用。 |

## 3. 基线记账与协作文档

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/README.md` | `7a9118cebcc687d815e2f0f21b39d1257e814b55541cc6790114eb1cc2bbe859` | A | reference | `demo/README.md` | 二人协作基线说明; 明确声明调度业务尚未实现 |
| `demo/FILE_MAP.md` | `e1a6e018fb29bc89fc00f0f73fec373ee40fbba230c0818698a2a88ed07d27ab` | A | reference | `demo/FILE_MAP.md` | 逐文件责任清单, 只读证据 |
| `demo/DEV_LOG.md` | `7b405c08258d15004f7b593fa5bd1f0b5023a95114213408e249111ad9f204bf` | A | reference | `demo/DEV_LOG.md` | 命名/单位/改动顺序的开发日志约定, 作为v0.1历史留存 |
| `demo/OWNERSHIP.json` | `a56724ad26b04dd55836e7150e8bed665e6f6d6456221806647c5e8083ee95d1` | A | adapt | `OWNERSHIP.json` | 最长前缀所有权规则; P01-03重写为新路径graph |
| `demo/AGENTS.md` | `b5dbaddda018ccf4a3e08279dfd8e38285517a6c49e6e7cff5beefdbec138159` | A | reference | `docs/implementation/P00-01.md` | 旧Agent协作规则; 新计划以PROJECT_MASTER_PLAN为唯一目标 |

`demo/README.md`、`demo/DEV_LOG.md`、`demo/FILE_MAP.md` 的目标路径写在旧基线内部，即这三份文件原地保留、不产生新仓库副本；`OWNERSHIP.json` 与 `docs/implementation/P00-01.md` 是尚未交付的未来目标。

## 4. 旧共享契约 `demo/contracts/**`

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/contracts/VERSION` | `3d097c315a1c543040f548da4c7051265e94c77211a2411ced1d4621344270de` | A | adapt | `packages/contracts/src/logistics_contracts/__init__.py` | 旧契约版本号0.1.0; v1契约升为1.0.0, 不覆盖旧文件 |
| `demo/contracts/README.md` | `63ba1dea7e0564274a07ecc11e59da248e10972efd3aae90e53a338a7eac4cb3` | A | adapt | `docs/architecture/MIGRATION_MAP.md` | v0.1共享契约索引; 迁移到packages/contracts |
| `demo/contracts/changes/TEMPLATE.md` | `13496fd33de4e91742bfb965bd201409e606f75ff6faf94ee0e4e5297a87847e` | A | adapt | `contracts/changes/README.md` | 旧契约变更模板; P01-03建立contracts/changes验收入口 |
| `demo/contracts/openapi.json` | `3add6302409bdd739ce2e5342fbb935556ce9477b9675b34b7887a7758081545` | A | rewrite | — 不迁移 | 旧OpenAPI; v1 OpenAPI在P05-01由已实现router导出, 禁止手改 |
| `demo/contracts/schemas.json` | `2928bf52d2dd9bf44e858c836ed4b7f03ffad427af6f1f86f0e5ff9de5e6a051` | A | rewrite | — 不迁移 | 旧JSON Schema导出物; v1导出物由scripts/export_contracts.py生成(P02-04), 禁止手改 |
| `demo/contracts/examples/dispatch_request.json` | `b88ef3a8e5441b7ad6dd5dc06174e8547dc2a1d9cd08146a5047eae06a59b8ea` | A | adapt | `packages/contracts/src/logistics_contracts/__init__.py` | 旧调度请求样例; 仅作迁移输入, 不计为已验证接口 |
| `demo/contracts/examples/scenario_import_request.json` | `ff33e8d67349e994244f6e15f85b75cd65c6c27d8e32d49c5f9810047562ddd8` | A | adapt | `packages/contracts/src/logistics_contracts/__init__.py` | 旧场景导入样例; P04-01生成可手算fixture替代 |
| `demo/contracts/examples/event_departure_delayed.json` | `f512feef9e8f583becd8a779c62a89b1bd93be1ee9395ebfb635f4347ab11bd1` | A | adapt | `packages/simulation/src/logistics_simulation/__init__.py` | 旧异常事件样例; P13-01重定义为EventEnvelope |
| `demo/contracts/examples/routing_request.json` | `2e94d906aca137cd49d513c6718fba943bd18e3f1798c5ce048069c3a63dbd75` | A | reuse | `packages/optimization/src/logistics_optimization/__init__.py` | B域运输请求样例; P06-01重定义为TransportRequestDTO |
| `demo/contracts/examples/routing_result_not_implemented.json` | `d163f45e21b8b83de85220bb9d9be2a34d525aa8f38f4c8f50083c8718de16f5` | A | reference | `docs/architecture/MIGRATION_MAP.md` | 旧求解结果显式not_implemented样例; 证明v0.1无正式求解 |

`openapi.json` 与 `schemas.json` 的 `target_path` 在清单中为 `null`，因此本表记为“— 不迁移”：它们是 v1 生成物的历史对照，不得被复制为新的主契约文件。v1 的唯一交付文档在 `documents` 中声明（见第 10 节）。

## 5. 旧类型契约 `demo/backend/app/contracts/**`

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/contracts/common.py` | `0b50a3ccdc87ce500b08626542c8486f4d07bbc87480542fe1dea0115795187a` | A | adapt | `packages/domain/src/logistics_domain/__init__.py` | 旧CONTRACT_VERSION/ErrorResponse; v1错误表以DATA_CONTRACTS为准 |
| `demo/backend/app/contracts/__init__.py` | `caa652e62b1c79fed3c53c36da25b08fc3ac0812b3a91015d75beeb178e2cfec` | A | rewrite | `packages/contracts/src/logistics_contracts/__init__.py` | 旧契约包入口; 新包为src-layout的logistics_contracts |
| `demo/backend/app/contracts/entities.py` | `5739adb9abc9c100c77902e35a48cae674a398460c021a7d69b8a5691d7081cd` | A | rewrite | `packages/domain/src/logistics_domain/__init__.py` | 旧实体DTO; P02按32实体DOMAIN_CATALOG重写, 不复制业务规则 |
| `demo/backend/app/contracts/events.py` | `ec416c9bffb55bc4d7ca5ea8540421ac74b78e8f9c514801e2b09c8d0e14b845` | A | rewrite | `packages/contracts/src/logistics_contracts/__init__.py` | 旧事件契约; P13-01重定义十类异常payload |
| `demo/backend/app/contracts/http.py` | `1fdea5c40efcc53755f25a71e6422de43566507560f76644e104083c7ce54ce4` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | 旧HTTP DTO; P05-01按API_CONTRACT重建 |
| `demo/backend/app/contracts/planning.py` | `a63fd7bcc10fc9c0f49748c4c237ef4832be3f2c4d6fd2fa885e602493155a09` | A | rewrite | `packages/contracts/src/logistics_contracts/__init__.py` | 旧计划请求/结果; P06-01起按typed solve契约重定义 |

## 6. 旧端口 `demo/backend/app/ports/**`

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/ports/__init__.py` | `caa652e62b1c79fed3c53c36da25b08fc3ac0812b3a91015d75beeb178e2cfec` | A | rewrite | `packages/domain/src/logistics_domain/__init__.py` | 旧ports包入口; v1 Protocol置于domain.ports |
| `demo/backend/app/ports/language_model.py` | `0db1259a039607482647cd49ef3c9fc2fbff1101a54b0703dcbbe3e65960fbbd` | A | adapt | `packages/agents/src/logistics_agents/__init__.py` | 旧语言模型端口; P18-01重定义为LLMProvider |
| `demo/backend/app/ports/matrix.py` | `8622a29c7e429c1f4301dbf4946bc910e11c8ecbd839e41789ed43c43e8bb0c1` | B | reuse | `packages/optimization/src/logistics_optimization/__init__.py` | B域矩阵端口; P06-02实现版本化DistanceMatrixProvider |
| `demo/backend/app/ports/routing.py` | `53b57d190100bfba3ad1c5f76dcf08f04d3d4623cc1b9f14a1dcbae72170b306` | B | reuse | `packages/optimization/src/logistics_optimization/__init__.py` | B域路由端口; P06-01实现Solver Protocol, 引擎对象不穿边界 |
| `demo/backend/app/ports/simulation.py` | `41ca3d37a04d86fbe89e6962c9fb43754a64a767c9717d5f1be3e57e22dc3b30` | B | reuse | `packages/simulation/src/logistics_simulation/__init__.py` | B域仿真端口; P11-01实现仿真契约 |
| `demo/backend/app/ports/storage.py` | `494206c80ab66b2ff82d81965fa8a214cbf9a1ac8e75aded66767721a7494fc8` | A | adapt | `packages/domain/src/logistics_domain/__init__.py` | 旧存储端口; P03-03实现快照读取与工作单元 |
| `demo/backend/app/ports/warehouse.py` | `8f808b7c914bc7385dac0b42c9aa61266a41549089b7ccdc8292af152517d427` | A | reuse | `packages/optimization/src/logistics_optimization/__init__.py` | 旧仓储端口; P08-01实现WarehouseScheduling Protocol |

## 7. 旧适配器 `demo/backend/app/adapters/**`

### 7.1 路由与仓储（求解）

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/adapters/routing/ortools_solver.py` | `089e46014b8b93677b7cd754d8525f1027cb5da0ae4c95b9bb9fca9c4d174d91` | B | rewrite | `packages/optimization/src/logistics_optimization/__init__.py` | 仅4行scaffold: solve()直接raise FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/adapters/warehouse/cp_sat_scheduler.py` | `4804098e71f3dbe0c9070dff500dafd18766c27ead258221c4ee7451caa18f77` | A | rewrite | `packages/optimization/src/logistics_optimization/__init__.py` | scaffold: 未实现CP-SAT排程 |
| `demo/backend/app/adapters/warehouse/resource_calendar.py` | `6d062499eeadc06bdd3d0a43574f0ff617081e282bd8fa22cd1342b407c27263` | A | rewrite | `packages/optimization/src/logistics_optimization/__init__.py` | scaffold: 未实现资源日历 |

### 7.2 矩阵

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/adapters/matrix/fixed.py` | `1e9703e79a29cf2c92d09ea3a777b04bfde727ac289012d3cd74bff36343da2a` | B | reuse | `packages/optimization/src/logistics_optimization/__init__.py` | 需在P06-02重新验证后才可复用; 当前无有效矩阵版本证据 |
| `demo/backend/app/adapters/matrix/osrm.py` | `47275ba6fcbf5b1d360f52f510891d608e4d0cfd160a366f03819ab7bebc078c` | B | rewrite | `packages/optimization/src/logistics_optimization/__init__.py` | scaffold: 未实现网络矩阵; P06-02只在adapter内部持有引擎对象 |

### 7.3 仿真

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/adapters/simulation/simpy_simulator.py` | `394a99c3535d7ddae7fad2fadf72069a29f8aaa3d9416fac95c37c4f14efa401` | B | rewrite | `packages/simulation/src/logistics_simulation/__init__.py` | scaffold: 未实现SimPy内核 |
| `demo/backend/app/adapters/simulation/event_sources.py` | `5197f26ad35f796eefba14fa47bbae7265d6bb9b05650d9aa77ee1d5f6cdbd6c` | B | rewrite | `packages/simulation/src/logistics_simulation/__init__.py` | scaffold: 未实现事件源 |
| `demo/backend/app/adapters/simulation/state_projection.py` | `87eb8730bbcba64562b38b430d8339c18346fa46075b316a05aeefd5719e8517` | B | rewrite | `packages/simulation/src/logistics_simulation/__init__.py` | scaffold: 未实现状态投影 |

### 7.4 语言模型

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/adapters/llm/gateway.py` | `78499bccfb2ed193eab09e9beaa2fb46a468382a9b8d68da022fe5bec216e7bb` | A | rewrite | `packages/agents/src/logistics_agents/__init__.py` | scaffold: 未实现模型供应方适配 |
| `demo/backend/app/adapters/llm/prompts.py` | `963f62dc13324604cc096c7d78330be4b82b621d8ea7e9d5a2088438a4e09c5d` | A | rewrite | `packages/agents/src/logistics_agents/__init__.py` | scaffold: 未实现意图抽取prompt边界 |

### 7.5 持久化

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/adapters/persistence/models.py` | `92baeb67787ed59c80f20d514f68478d841f5afd33a62b8ef3018b12bc09e79c` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | scaffold: 未实现ORM模型; P03改为迁移脚本 |
| `demo/backend/app/adapters/persistence/jobs.py` | `2d4e789a8f65c416424b4fd8ee21884fdd0da36fda0cd4b71215391f077fcd1e` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | scaffold: 未实现持久作业/租约 |
| `demo/backend/app/adapters/persistence/plan_commit.py` | `59cabe85318e408b92ad31a2fd2b2745f70e295f3a5de82548db030d86b3cff5` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | scaffold: 未实现版本CAS提交 |
| `demo/backend/app/adapters/persistence/snapshots.py` | `9edee8582ba1f5b8379ca8452732b0a58e17ce33d753cd76664a53fc5be3d07e` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | scaffold: 未实现一致快照 |

## 8. 旧应用服务、领域规则、API 与前端

### 8.1 应用服务 `demo/backend/app/application/**`

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/application/__init__.py` | `caa652e62b1c79fed3c53c36da25b08fc3ac0812b3a91015d75beeb178e2cfec` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | 旧application包入口; v1为bootstrap+services |
| `demo/backend/app/application/confirm_plan.py` | `2199e346a75c3b77c7b6690e139241e90955307da49756b3f9571e10cdf229e0` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/application/contract_net.py` | `75e94c7cd3c3f9a2e4c8b4a940cce60c02a7e9136aa25c12a89dc8155fd50314` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/application/http_services.py` | `1512a547d335ff0d0395d3c0b1fc648e67b53b5801859bfcd3e93555b8570cb2` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only (10个入口全部501) |
| `demo/backend/app/application/coordinator.py` | `24e3993260a1acab195e4a59c0147571fde4dfde5bfaeb02671c3f756bdf19df` | A | rewrite | `packages/optimization/src/logistics_optimization/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/application/warehouse_selection.py` | `fba49a5ece82d739e8c4ad83ba901ca50411807cc16dff087946efb7810e0079` | A | rewrite | `packages/optimization/src/logistics_optimization/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/application/handle_event.py` | `4853409bb1c2677067e1fb0791b64066d7f19027c8e5744f0f7e56a9332fee31` | A | rewrite | `packages/simulation/src/logistics_simulation/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/application/impact_analysis.py` | `8f3382c376992ca703c43026dc81a3b2519ebfd72e12bbe9088046d8f2cfb7be` | A | rewrite | `packages/simulation/src/logistics_simulation/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |

### 8.2 领域规则 `demo/backend/app/domain/**`

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/domain/__init__.py` | `caa652e62b1c79fed3c53c36da25b08fc3ac0812b3a91015d75beeb178e2cfec` | A | rewrite | `packages/domain/src/logistics_domain/__init__.py` | 旧domain包入口; v1 domain不得导入框架/ORM/模型SDK |
| `demo/backend/app/domain/states.py` | `7ceb99b1804a651870a0c5f6e870dd871a47d94a9f38057b4fcec538d2a3dec1` | A | adapt | `packages/domain/src/logistics_domain/__init__.py` | 旧状态枚举; P02-01收敛为唯一状态枚举, 未映射值显式拒绝 |
| `demo/backend/app/domain/cold_chain_rules.py` | `77aeda7647ea85b6e47bb0582815a7531d2f0fb3f3fa3b14dbd674892e33d2b7` | A | rewrite | `packages/domain/src/logistics_domain/__init__.py` | scaffold: 未实现冷链/清洁规则 |
| `demo/backend/app/domain/inventory.py` | `a6b470d28f4f243cc2e086c1cc2a9820136958bb450cc3d7c0ca2f0ad88d9e8a` | A | rewrite | `packages/domain/src/logistics_domain/__init__.py` | scaffold: 未实现库存守恒 |
| `demo/backend/app/domain/plan_rules.py` | `45f5221309360cbc9da50f751b5b30f548309dcd52a2e6d159c1f48f6e8a5e81` | A | rewrite | `packages/domain/src/logistics_domain/__init__.py` | scaffold: 未实现计划规则 |
| `demo/backend/app/domain/state_transitions.py` | `5e84dbad6cce3a510c1d8472361aac50112bda1fa497717f5eab126715cecc34` | A | rewrite | `packages/domain/src/logistics_domain/__init__.py` | scaffold: 未实现状态机 |
| `demo/backend/app/domain/warehouse_rules.py` | `0b2e4e2659018c9e18818b77d909293ff3dc0a61d509c04838d10e26907d299e` | A | rewrite | `packages/domain/src/logistics_domain/__init__.py` | scaffold: 未实现仓储规则 |
| `demo/backend/app/domain/transport_rules.py` | `22faa527050ff29e2074614ebf22667c5524f36d3ba1d7efbca9528d0cebd885` | B | rewrite | `packages/domain/src/logistics_domain/__init__.py` | scaffold: 未实现运输硬约束规则 |

### 8.3 API、组合与 worker

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/app/main.py` | `35bd8d3dfbc18997a28a4fc07e03467d3ab19912bfa7315641361e4d24062fd3` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | 可运行骨架: 仅/api/v1/health真实, 业务路由统一501 |
| `demo/backend/app/bootstrap.py` | `2906af0a9746a737377483de537f6a091aabefbd054aab4deb344d7f0fd384da` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | 旧组合根; v1 bootstrap是唯一装配点, 不得装配fake adapter |
| `demo/backend/app/worker.py` | `cc3d2a02298be34c27410b01093d600d65f17683100cf258ea0f593039ae5301` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | scaffold: 未实现受限worker |
| `demo/backend/app/api/__init__.py` | `caa652e62b1c79fed3c53c36da25b08fc3ac0812b3a91015d75beeb178e2cfec` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | 旧api包入口; v1 router只注册已实现路由 |
| `demo/backend/app/api/dependencies.py` | `d499eb3bee30db47d9a7b1db9b875168da56bae699e441ac587f9400d9641381` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | scaffold: 未实现依赖注入 |
| `demo/backend/app/api/routes/scenarios.py` | `0903bc097f99fd6b4a44b17d48a242fed2cb6da94ed80b1d2562a754bb8b4f11` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/api/routes/requests.py` | `86ec5d64115848b26e54d5904f8057bc897dd924054c000bb3cd8fd644e345da` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/api/routes/planning.py` | `5014b0981d729131e28fde211be2aba4dcc5325502f9e6aab7bd606b43c737a5` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/api/routes/jobs.py` | `118c885ff872de4f5dd76fe727a68bd5d2ae2eff6010bd84fdc7d6c610bbcccc` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/api/routes/plans.py` | `b3be75006de2c4293fce5452d03a7457433601bb2c5050d2a8e4a83696a26f48` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/api/routes/events.py` | `4165180580c885df6163d3737a20466a2e686c5eac820964599f32532555cd52` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/api/routes/simulations.py` | `75091bfbd9f899a93b30f85523fe710626795f83e1a5f5f4b6acc0da44f1ede9` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| `demo/backend/app/api/routes/evidence.py` | `77c3697e6e0007d33e80546ed1a906d794b3972a1eb5d52629f82a5149d7109b` | A | rewrite | `apps/backend/src/logistics_backend/__init__.py` | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |

### 8.4 旧脚本、CI 与数据

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/scripts/build_file_map.py` | `b9c753df851a0ccacc034c5d48043ed682871f5a6f9b14f72cbc9eebaeffd080` | A | adapt | `OWNERSHIP.json` | 旧文件清单生成器; P01-03改为check_ownership.py |
| `demo/scripts/check_project.py` | `f98d9c0677981521d0955a556826cfbd737d1080c7ddc34d5335a11ac0d4a2e9` | A | adapt | `apps/backend/src/logistics_backend/__init__.py` | 旧工程检查; P01-02建立scripts/check_architecture.py与gates.py |
| `demo/scripts/export_contracts.py` | `30f0efde3fe4c4c6d4a344bf73f91dd0f21e1c2199f692623bfa660edb4c2f6c` | A | reuse | `apps/backend/src/logistics_backend/__init__.py` | 导出脚本; P02/P05重写为scripts/export_contracts.py |
| `demo/.github/workflows/checks.yml` | `8dbd81bf6dc305f54596f9bf128703a196f1c15652876a537a26524d00d8a33e` | A | adapt | `.github/workflows/ci.yml` | 旧CI; P01-02建立分层检查CI |
| `demo/data/scenarios/two_warehouses_20_orders.json` | `592ece17d7f190cad52cc53b594a2da060586255e16dafa039121866773be2df` | A | reference | `tests/integration/test_p01_01_workspace_bootstrap.py` | 旧20单2仓场景; P04-01按TEST_FIXTURES重新生成可手算fixture |

### 8.5 旧测试 `demo/backend/tests/**`

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/backend/tests/test_contracts.py` | `f9205fa3905457cbd1b50bcde9f41ca7f80c161b515dda96dfa8e5af1787e6b7` | A | adapt | `tests/unit/test_p01_01_workspace_bootstrap.py` | 旧契约测试; P02-04重写为Schema导出检查 |
| `demo/backend/tests/test_scaffold.py` | `2b3a7e120c5dc37a0b9991ab17fb1c51159f3f737650c0e229262e4b84d52ffb` | A | adapt | `tests/integration/test_p01_01_workspace_bootstrap.py` | 旧骨架测试; 新计划用分层真实测试替代, 不导入教学探针 |

旧骨架测试 `demo/backend/tests/test_scaffold.py` 断言的是 501 骨架行为，属于骨架证据而非业务验证证据：它进入新测试目录时只保留其分层结构含义，实际断言必须按 v1 契约重写。旧数据文件 `demo/data/scenarios/two_warehouses_20_orders.json` 的目标路径按清单记录为 `tests/integration/test_p01_01_workspace_bootstrap.py`，含义是该场景在 v1 的落点由真实 fixture 与集成测试承载，旧 JSON 本身只作只读输入。

### 8.6 前端 `demo/frontend/src/client/**`

| source_path | sha256 | owner | disposition | target_path | 能力证据 |
| --- | --- | --- | --- | --- | --- |
| `demo/frontend/src/client/generated.ts` | `8a3477e2d8a590b5a688fc4cf967b3b92acfdaef236062fee0f5ec00e3eba8ed` | A | rewrite | `apps/frontend/src/client/generated.ts` | 旧生成客户端; P24-02由OpenAPI重新生成, 手改即失败（`primary_document=true`） |
| `demo/frontend/src/client/api.ts` | `5c5ab80c00986296cff1bc10e83b392114d53b467f24b10556935389b7218537` | A | rewrite | `apps/frontend/src/client/generated.ts` | 旧请求层; P24-02重建数据请求层, 不单独占用生成物路径 |

`generated.ts` 是清单中唯一 `primary_document=true` 的条目：新仓库的生成客户端只能有这一个声明来源（`documents` 中声明的目标为 `apps/frontend/src/client/generated.ts`）。

## 9. 无有效能力证据的资产

下表 26 条旧模块在 v0.1 中只抛出 `FeatureNotImplemented` 或只带 `TODO[...]` 说明，没有任何可运行的业务能力；连同紧随其后的 2 条，合计 28 条旧模块无业务实现。清单 `capability_evidence` 逐条给出对应口径：

| # | source_path | sha256 | owner | disposition | 证据口径 |
| --- | --- | --- | --- | --- | --- |
| 1 | `demo/backend/app/adapters/routing/ortools_solver.py` | `089e46014b8b93677b7cd754d8525f1027cb5da0ae4c95b9bb9fca9c4d174d91` | B | rewrite | 仅4行scaffold: solve()直接raise FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| 2 | `demo/backend/app/adapters/warehouse/cp_sat_scheduler.py` | `4804098e71f3dbe0c9070dff500dafd18766c27ead258221c4ee7451caa18f77` | A | rewrite | scaffold: 未实现CP-SAT排程 |
| 3 | `demo/backend/app/adapters/warehouse/resource_calendar.py` | `6d062499eeadc06bdd3d0a43574f0ff617081e282bd8fa22cd1342b407c27263` | A | rewrite | scaffold: 未实现资源日历 |
| 4 | `demo/backend/app/adapters/matrix/osrm.py` | `47275ba6fcbf5b1d360f52f510891d608e4d0cfd160a366f03819ab7bebc078c` | B | rewrite | scaffold: 未实现网络矩阵; P06-02只在adapter内部持有引擎对象 |
| 5 | `demo/backend/app/adapters/simulation/simpy_simulator.py` | `394a99c3535d7ddae7fad2fadf72069a29f8aaa3d9416fac95c37c4f14efa401` | B | rewrite | scaffold: 未实现SimPy内核 |
| 6 | `demo/backend/app/adapters/simulation/event_sources.py` | `5197f26ad35f796eefba14fa47bbae7265d6bb9b05650d9aa77ee1d5f6cdbd6c` | B | rewrite | scaffold: 未实现事件源 |
| 7 | `demo/backend/app/adapters/simulation/state_projection.py` | `87eb8730bbcba64562b38b430d8339c18346fa46075b316a05aeefd5719e8517` | B | rewrite | scaffold: 未实现状态投影 |
| 8 | `demo/backend/app/adapters/llm/gateway.py` | `78499bccfb2ed193eab09e9beaa2fb46a468382a9b8d68da022fe5bec216e7bb` | A | rewrite | scaffold: 未实现模型供应方适配 |
| 9 | `demo/backend/app/adapters/llm/prompts.py` | `963f62dc13324604cc096c7d78330be4b82b621d8ea7e9d5a2088438a4e09c5d` | A | rewrite | scaffold: 未实现意图抽取prompt边界 |
| 10 | `demo/backend/app/adapters/persistence/models.py` | `92baeb67787ed59c80f20d514f68478d841f5afd33a62b8ef3018b12bc09e79c` | A | rewrite | scaffold: 未实现ORM模型; P03改为迁移脚本 |
| 11 | `demo/backend/app/adapters/persistence/jobs.py` | `2d4e789a8f65c416424b4fd8ee21884fdd0da36fda0cd4b71215391f077fcd1e` | A | rewrite | scaffold: 未实现持久作业/租约 |
| 12 | `demo/backend/app/adapters/persistence/plan_commit.py` | `59cabe85318e408b92ad31a2fd2b2745f70e295f3a5de82548db030d86b3cff5` | A | rewrite | scaffold: 未实现版本CAS提交 |
| 13 | `demo/backend/app/adapters/persistence/snapshots.py` | `9edee8582ba1f5b8379ca8452732b0a58e17ce33d753cd76664a53fc5be3d07e` | A | rewrite | scaffold: 未实现一致快照 |
| 14 | `demo/backend/app/worker.py` | `cc3d2a02298be34c27410b01093d600d65f17683100cf258ea0f593039ae5301` | A | rewrite | scaffold: 未实现受限worker |
| 15 | `demo/backend/app/api/dependencies.py` | `d499eb3bee30db47d9a7b1db9b875168da56bae699e441ac587f9400d9641381` | A | rewrite | scaffold: 未实现依赖注入 |
| 16 | `demo/backend/app/domain/cold_chain_rules.py` | `77aeda7647ea85b6e47bb0582815a7531d2f0fb3f3fa3b14dbd674892e33d2b7` | A | rewrite | scaffold: 未实现冷链/清洁规则 |
| 17 | `demo/backend/app/domain/inventory.py` | `a6b470d28f4f243cc2e086c1cc2a9820136958bb450cc3d7c0ca2f0ad88d9e8a` | A | rewrite | scaffold: 未实现库存守恒 |
| 18 | `demo/backend/app/domain/plan_rules.py` | `45f5221309360cbc9da50f751b5b30f548309dcd52a2e6d159c1f48f6e8a5e81` | A | rewrite | scaffold: 未实现计划规则 |
| 19 | `demo/backend/app/domain/state_transitions.py` | `5e84dbad6cce3a510c1d8472361aac50112bda1fa497717f5eab126715cecc34` | A | rewrite | scaffold: 未实现状态机 |
| 20 | `demo/backend/app/domain/warehouse_rules.py` | `0b2e4e2659018c9e18818b77d909293ff3dc0a61d509c04838d10e26907d299e` | A | rewrite | scaffold: 未实现仓储规则 |
| 21 | `demo/backend/app/domain/transport_rules.py` | `22faa527050ff29e2074614ebf22667c5524f36d3ba1d7efbca9528d0cebd885` | B | rewrite | scaffold: 未实现运输硬约束规则 |
| 22 | `demo/backend/app/application/confirm_plan.py` | `2199e346a75c3b77c7b6690e139241e90955307da49756b3f9571e10cdf229e0` | A | rewrite | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| 23 | `demo/backend/app/application/contract_net.py` | `75e94c7cd3c3f9a2e4c8b4a940cce60c02a7e9136aa25c12a89dc8155fd50314` | A | rewrite | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| 24 | `demo/backend/app/application/http_services.py` | `1512a547d335ff0d0395d3c0b1fc648e67b53b5801859bfcd3e93555b8570cb2` | A | rewrite | FeatureNotImplemented raised (demos return HTTP 501); scaffold only (10个入口全部501) |
| 25 | `demo/backend/app/application/coordinator.py` | `24e3993260a1acab195e4a59c0147571fde4dfde5bfaeb02671c3f756bdf19df` | A | rewrite | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |
| 26 | `demo/backend/app/application/warehouse_selection.py` | `fba49a5ece82d739e8c4ad83ba901ca50411807cc16dff087946efb7810e0079` | A | rewrite | FeatureNotImplemented raised (demos return HTTP 501); scaffold only |

另有 `demo/backend/app/application/handle_event.py`（`4853409bb1c2677067e1fb0791b64066d7f19027c8e5744f0f7e56a9332fee31`）与 `demo/backend/app/application/impact_analysis.py`（`8f3382c376992ca703c43026dc81a3b2519ebfd72e12bbe9088046d8f2cfb7be`）同样是 `FeatureNotImplemented raised (demos return HTTP 501); scaffold only`，合计 28 条旧模块无业务实现。此外旧 API 层 8 个路由模块与 `demo/backend/app/main.py` 共享同一证据口径：

- `demo/backend/app/main.py` 是唯一可运行的入口，但它只实现 `/api/v1/health` 一个真实端点。
- 全部业务路由与全部应用服务、领域规则、适配器在调用时抛出 `demo/backend/app/common/errors.py` 中声明的 `FeatureNotImplemented`。
- `demo/backend/app/main.py` 注册的异常处理器把该异常映射为 HTTP 501 与错误码 `not_implemented`。
- 旧契约版本由 `demo/contracts/VERSION` 固定为 0.1.0；清单中的 `demo/contracts/examples/routing_result_not_implemented.json` 是这一能力边界的显式反例样例。

结论：**501 与教学探针均不计为正式求解实现**。v0.1 不存在任何已验证的求解器、CP-SAT 排程器、SimPy 引擎、持久化实现或矩阵提供器；第 2 节中 `reuse` 类资产（B 域矩阵、路由、仿真端口与样例）只有在对应任务重新验证后才可复用，当前不具备生效条件。

## 10. 冻结不迁移边界

冻结边界分两类，都在 `entries` 中可核验：

1. **逐文件登记**：`disposition=reference` 且 `target_path=null`、`capability_evidence` 前缀为 `frozen non-migrating boundary:` 的条目，每条都带真实 `sha256`。它们覆盖旧部署（`demo/deploy/**`）、旧规划与交接文档（`demo/docs/**`）、旧平台适配（`demo/platform/wanwu/README.md`）、教学探针（`demo/reference_demos/**`）、旧编辑器与环境样例（`demo/.editorconfig`、`demo/.env.example`、`demo/.gitattributes`、`demo/.gitignore`）、旧依赖清单与占位说明（`demo/backend/requirements*.txt`、`demo/backend/migrations/**`、`demo/backend/tests/**`、`demo/benchmarks/**`、`demo/data/**`）以及旧前端构建产物与说明文件（`demo/frontend/dist/**`、`demo/frontend/README.md` 等）。
2. **派生根目录，只记录计数与树指纹**：`coverage.boundary_directories` 登记两个大型目录，不逐文件写入 `entries`，否则清单会被构建产物淹没：

| prefix | 文件数 | tree_sha256 | 冻结原因 |
| --- | --- | --- | --- |
| `demo/frontend/node_modules/` | 10984 | `c4ed3194a1889cd613f54c993b27cc0b2796c81a10dce0535cf522154885c46b` | 构建产物, 由 package-lock.json 与 npm ci 重建 |
| `demo/.venv/` | 1476 | `ef48c5103b603664ced96ce2bac1d4227af1a036076a45a9f0e2e0485628fbd0` | 本地虚拟环境, 由 uv.lock 与 uv sync 重建 |

指纹定义为 `sha256` over sorted `<relative_path>\0<file_sha256>\n`，可用生成器的 `--check` 复现。

`demo/reference_demos/` 作为正式包的导入来源被永久禁止，永不从正式包导入。打包交付物 `demo.zip` 与 `demo.zip.sha256` 位于仓库根目录（不属于 `demo/` 子树），因此不在本清单条目内；其完整性由任务证据 `artifacts/handoffs/P01-01/dsh/evidence.json` 的 `legacy_demo.demo_zip.sha256` 记录，并与 `demo.zip.sha256` 声明值一致。

## 11. 检查与复现

必须保持通过的检查由生成器的 `--check` 模式与清单的 `uniqueness_rules` 共同定义：

1. 唯一性：每个 `source_path` 在 `entries` 中恰好出现一次（173 条路径互不相同），且必须指向真实存在的文件。
2. 一致性：每个登记文件记录的 sha256 与其在磁盘上的当前内容一致；任一文件被改动或缺失，`--check` 都会以退出码 1 失败并提示重新生成。
3. 覆盖完整性：`coverage.unregistered_file_count` 必须为 0。生成器遍历 `demo/` 全部普通文件（剪枝 `node_modules`、`.venv` 与缓存目录），任何既不在 `ENTRIES`、也不在 `FROZEN_FILES` 的普通文件都会出现在 `coverage.unregistered_files` 中，必须先补登或明确排除；该检查是 `ARCH-0002` 的闭环手段。
4. 文档唯一来源：`documents` 中声明的三份唯一可交付文档（`contracts/openapi.json`、`contracts/schemas.json`、`apps/frontend/src/client/generated.ts`）各自至多只能有一个 `source_path` 声明来源。当前三份文档的声明源分别是 `demo/contracts/openapi.json`、`demo/contracts/schemas.json`、`demo/frontend/src/client/generated.ts`；其中只有 `demo/frontend/src/client/generated.ts` 在 `entries` 中带有 `primary_document=true`。
5. 迁移完整性：`disposition=rewrite` 的条目必须给出 `target_path` 或 `null`（`null` 表示明确不迁移，如旧 `openapi.json`/`schemas.json`）。

负例（必须导致检查失败）：**同一源文件声明两条目标主契约 => 检查失败**。相应地，同一个源文件被两个目标文档路径同时声明为唯一来源，或同一唯一可交付文档被第二个 `source_path` 声明为主文档，都属于必须拒绝的状态，否则会出现双主契约与生成物漂移。

同一 `target_path` 被多个 `source_path` 归并是允许的：例如 24 条旧后端文件共同归并到 `apps/backend/src/logistics_backend/__init__.py`，12 条归并到 `packages/domain/src/logistics_domain/__init__.py`。清单规则原文为“同一 target_path 可被多个 source_path 归并(例如旧HTTP DTO共同重写到新边界包)”。归并只针对代码与包入口，不适用于本节第 4 条列出的三份唯一交付文档。

## 12. 限制与未验证

本文与机器清单能证明的内容仅限于“基线日期存在哪些文件、内容哈希是否与清单一致、旧代码声明的能力边界是什么”。以下内容均未被本次登记验证，也不得据此推断：

- 未执行任何应用测试：没有运行 `demo/` 的任何测试、没有启动旧应用、没有验证 501 之外的行为；第 9 节的结论来自旧源码中显式的 `FeatureNotImplemented` 与 `not_implemented` 样例，不是运行结果。
- 无业务 Gate 执行器运行：`scripts/gates.py` 由 P01-02 交付；本任务只产生文档契约证据。规划检查器记录的 G00 是文档契约证据，不等于任何业务验收；G01 及之后的业务 Gate 尚未通过，后续阶段不得开始。
- 无数据库、求解器、仿真证据：没有对 PostgreSQL、OR-Tools、CP-SAT、SimPy、OSRM 或任何 LLM 供应方做过可运行性验证；`reuse` 类资产当前不具备复用证据。
- 未做单位与契约一致性验证：旧 `demo/contracts/VERSION` 的 0.1.0 与新契约 1.0.0 之间的字段、单位、枚举映射只在 `docs/architecture/MIGRATION_MAP.md` 中登记，尚未由任何实现或导出物验证。
- 覆盖边界由 `coverage.unregistered_file_count == 0` 证明，但该证明只针对“普通文件登记完整性”：两个派生目录（`demo/frontend/node_modules/`、`demo/.venv/`）只记录计数与指纹，其内部文件不逐条登记；缓存类目录（`__pycache__`、`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、`.git`）按约定不登记。此差异已登记为 `ARCH-0002`（见 `docs/architecture/issues/README.md`）。
- Pydantic 版本、依赖锁定与运行环境未验证于本清单：旧 `demo/backend/requirements*.txt` 与 `demo/backend/pyproject.toml` 只作登记；新环境由 P01-01 建立并锁定。
- `apps/**`、`packages/**`、`contracts/**`、`tests/**`、根 `OWNERSHIP.json` 等第 3 至第 10 节出现的全部目标路径，在本文件写作时都尚不存在，属于未来任务的目标。
