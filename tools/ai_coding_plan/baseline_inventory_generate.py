"""Generate docs/architecture/BASELINE_INVENTORY.json from the real old-demo tree.

P00-01 deliverable generator. Never writes into demo/ (read-only baseline).
Usage: python tools/ai_coding_plan/baseline_inventory_generate.py [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/architecture/BASELINE_INVENTORY.json"

SCHEMA_VERSION = "1.0.0"
BASELINE_DATE = "2026-09-10"
UNIMPLEMENTED = "FeatureNotImplemented raised (demos return HTTP 501); scaffold only"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# source_path -> (owner, target_path, disposition, capability_evidence, is_primary_document)
# Every row is an exact existing file in the repository; hashes are computed, never hand-typed.
ENTRIES: list[tuple[str, str, str, str, str, bool]] = [
    # --- baseline bookkeeping -------------------------------------------------
    ("demo/README.md", "A", "demo/README.md", "reference",
     "二人协作基线说明; 明确声明调度业务尚未实现", False),
    ("demo/DEV_LOG.md", "A", "demo/DEV_LOG.md", "reference",
     "命名/单位/改动顺序的开发日志约定, 作为v0.1历史留存", False),
    ("demo/OWNERSHIP.json", "A", "OWNERSHIP.json", "adapt",
     "最长前缀所有权规则; P01-03重写为新路径graph", False),
    ("demo/FILE_MAP.md", "A", "demo/FILE_MAP.md", "reference",
     "逐文件责任清单, 只读证据", False),
    ("demo/AGENTS.md", "A", "docs/implementation/P00-01.md", "reference",
     "旧Agent协作规则; 新计划以PROJECT_MASTER_PLAN为唯一目标", False),
    # --- old contracts --------------------------------------------------------
    ("demo/contracts/README.md", "A", "docs/architecture/MIGRATION_MAP.md", "adapt",
     "v0.1共享契约索引; 迁移到packages/contracts", False),
    ("demo/contracts/VERSION", "A", "packages/contracts/src/logistics_contracts/__init__.py", "adapt",
     "旧契约版本号0.1.0; v1契约升为1.0.0, 不覆盖旧文件", False),
    ("demo/contracts/schemas.json", "A", None, "rewrite",
     "旧JSON Schema导出物; v1导出物由scripts/export_contracts.py生成(P02-04), 禁止手改", False),
    ("demo/contracts/openapi.json", "A", None, "rewrite",
     "旧OpenAPI; v1 OpenAPI在P05-01由已实现router导出, 禁止手改", False),
    ("demo/contracts/changes/TEMPLATE.md", "A", "contracts/changes/README.md", "adapt",
     "旧契约变更模板; P01-03建立contracts/changes验收入口", False),
    ("demo/contracts/examples/dispatch_request.json", "A", "packages/contracts/src/logistics_contracts/__init__.py", "adapt",
     "旧调度请求样例; 仅作迁移输入, 不计为已验证接口", False),
    ("demo/contracts/examples/routing_request.json", "A", "packages/optimization/src/logistics_optimization/__init__.py", "reuse",
     "B域运输请求样例; P06-01重定义为TransportRequestDTO", False),
    ("demo/contracts/examples/routing_result_not_implemented.json", "A", "docs/architecture/MIGRATION_MAP.md", "reference",
     "旧求解结果显式not_implemented样例; 证明v0.1无正式求解", False),
    ("demo/contracts/examples/event_departure_delayed.json", "A", "packages/simulation/src/logistics_simulation/__init__.py", "adapt",
     "旧异常事件样例; P13-01重定义为EventEnvelope", False),
    ("demo/contracts/examples/scenario_import_request.json", "A", "packages/contracts/src/logistics_contracts/__init__.py", "adapt",
     "旧场景导入样例; P04-01生成可手算fixture替代", False),
    # --- old typed contracts --------------------------------------------------
    ("demo/backend/app/contracts/__init__.py", "A", "packages/contracts/src/logistics_contracts/__init__.py", "rewrite",
     "旧契约包入口; 新包为src-layout的logistics_contracts", False),
    ("demo/backend/app/contracts/common.py", "A", "packages/domain/src/logistics_domain/__init__.py", "adapt",
     "旧CONTRACT_VERSION/ErrorResponse; v1错误表以DATA_CONTRACTS为准", False),
    ("demo/backend/app/contracts/entities.py", "A", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "旧实体DTO; P02按32实体DOMAIN_CATALOG重写, 不复制业务规则", False),
    ("demo/backend/app/contracts/events.py", "A", "packages/contracts/src/logistics_contracts/__init__.py", "rewrite",
     "旧事件契约; P13-01重定义十类异常payload", False),
    ("demo/backend/app/contracts/http.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "旧HTTP DTO; P05-01按API_CONTRACT重建", False),
    ("demo/backend/app/contracts/planning.py", "A", "packages/contracts/src/logistics_contracts/__init__.py", "rewrite",
     "旧计划请求/结果; P06-01起按typed solve契约重定义", False),
    # --- old ports ------------------------------------------------------------
    ("demo/backend/app/ports/__init__.py", "A", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "旧ports包入口; v1 Protocol置于domain.ports", False),
    ("demo/backend/app/ports/language_model.py", "A", "packages/agents/src/logistics_agents/__init__.py", "adapt",
     "旧语言模型端口; P18-01重定义为LLMProvider", False),
    ("demo/backend/app/ports/matrix.py", "B", "packages/optimization/src/logistics_optimization/__init__.py", "reuse",
     "B域矩阵端口; P06-02实现版本化DistanceMatrixProvider", False),
    ("demo/backend/app/ports/routing.py", "B", "packages/optimization/src/logistics_optimization/__init__.py", "reuse",
     "B域路由端口; P06-01实现Solver Protocol, 引擎对象不穿边界", False),
    ("demo/backend/app/ports/simulation.py", "B", "packages/simulation/src/logistics_simulation/__init__.py", "reuse",
     "B域仿真端口; P11-01实现仿真契约", False),
    ("demo/backend/app/ports/storage.py", "A", "packages/domain/src/logistics_domain/__init__.py", "adapt",
     "旧存储端口; P03-03实现快照读取与工作单元", False),
    ("demo/backend/app/ports/warehouse.py", "A", "packages/optimization/src/logistics_optimization/__init__.py", "reuse",
     "旧仓储端口; P08-01实现WarehouseScheduling Protocol", False),
    # --- old adapters (teaching probes, never imported) -----------------------
    ("demo/backend/app/adapters/routing/ortools_solver.py", "B", "packages/optimization/src/logistics_optimization/__init__.py", "rewrite",
     "仅4行scaffold: solve()直接raise " + UNIMPLEMENTED, False),
    ("demo/backend/app/adapters/warehouse/cp_sat_scheduler.py", "A", "packages/optimization/src/logistics_optimization/__init__.py", "rewrite",
     "scaffold: 未实现CP-SAT排程", False),
    ("demo/backend/app/adapters/warehouse/resource_calendar.py", "A", "packages/optimization/src/logistics_optimization/__init__.py", "rewrite",
     "scaffold: 未实现资源日历", False),
    ("demo/backend/app/adapters/matrix/fixed.py", "B", "packages/optimization/src/logistics_optimization/__init__.py", "reuse",
     "需在P06-02重新验证后才可复用; 当前无有效矩阵版本证据", False),
    ("demo/backend/app/adapters/matrix/osrm.py", "B", "packages/optimization/src/logistics_optimization/__init__.py", "rewrite",
     "scaffold: 未实现网络矩阵; P06-02只在adapter内部持有引擎对象", False),
    ("demo/backend/app/adapters/simulation/simpy_simulator.py", "B", "packages/simulation/src/logistics_simulation/__init__.py", "rewrite",
     "scaffold: 未实现SimPy内核", False),
    ("demo/backend/app/adapters/simulation/event_sources.py", "B", "packages/simulation/src/logistics_simulation/__init__.py", "rewrite",
     "scaffold: 未实现事件源", False),
    ("demo/backend/app/adapters/simulation/state_projection.py", "B", "packages/simulation/src/logistics_simulation/__init__.py", "rewrite",
     "scaffold: 未实现状态投影", False),
    ("demo/backend/app/adapters/llm/gateway.py", "A", "packages/agents/src/logistics_agents/__init__.py", "rewrite",
     "scaffold: 未实现模型供应方适配", False),
    ("demo/backend/app/adapters/llm/prompts.py", "A", "packages/agents/src/logistics_agents/__init__.py", "rewrite",
     "scaffold: 未实现意图抽取prompt边界", False),
    ("demo/backend/app/adapters/persistence/models.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "scaffold: 未实现ORM模型; P03改为迁移脚本", False),
    ("demo/backend/app/adapters/persistence/jobs.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "scaffold: 未实现持久作业/租约", False),
    ("demo/backend/app/adapters/persistence/plan_commit.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "scaffold: 未实现版本CAS提交", False),
    ("demo/backend/app/adapters/persistence/snapshots.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "scaffold: 未实现一致快照", False),
    # --- old application services (all 501) -----------------------------------
    ("demo/backend/app/application/__init__.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "旧application包入口; v1为bootstrap+services", False),
    ("demo/backend/app/application/confirm_plan.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     UNIMPLEMENTED, False),
    ("demo/backend/app/application/contract_net.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     UNIMPLEMENTED, False),
    ("demo/backend/app/application/coordinator.py", "A", "packages/optimization/src/logistics_optimization/__init__.py", "rewrite",
     UNIMPLEMENTED, False),
    ("demo/backend/app/application/handle_event.py", "A", "packages/simulation/src/logistics_simulation/__init__.py", "rewrite",
     UNIMPLEMENTED, False),
    ("demo/backend/app/application/http_services.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     UNIMPLEMENTED + " (10个入口全部501)", False),
    ("demo/backend/app/application/impact_analysis.py", "A", "packages/simulation/src/logistics_simulation/__init__.py", "rewrite",
     UNIMPLEMENTED, False),
    ("demo/backend/app/application/warehouse_selection.py", "A", "packages/optimization/src/logistics_optimization/__init__.py", "rewrite",
     UNIMPLEMENTED, False),
    # --- old domain rules ----------------------------------------------------
    ("demo/backend/app/domain/__init__.py", "A", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "旧domain包入口; v1 domain不得导入框架/ORM/模型SDK", False),
    ("demo/backend/app/domain/cold_chain_rules.py", "A", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "scaffold: 未实现冷链/清洁规则", False),
    ("demo/backend/app/domain/inventory.py", "A", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "scaffold: 未实现库存守恒", False),
    ("demo/backend/app/domain/plan_rules.py", "A", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "scaffold: 未实现计划规则", False),
    ("demo/backend/app/domain/states.py", "A", "packages/domain/src/logistics_domain/__init__.py", "adapt",
     "旧状态枚举; P02-01收敛为唯一状态枚举, 未映射值显式拒绝", False),
    ("demo/backend/app/domain/state_transitions.py", "A", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "scaffold: 未实现状态机", False),
    ("demo/backend/app/domain/transport_rules.py", "B", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "scaffold: 未实现运输硬约束规则", False),
    ("demo/backend/app/domain/warehouse_rules.py", "A", "packages/domain/src/logistics_domain/__init__.py", "rewrite",
     "scaffold: 未实现仓储规则", False),
    # --- old API / composition ------------------------------------------------
    ("demo/backend/app/main.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "可运行骨架: 仅/api/v1/health真实, 业务路由统一501", False),
    ("demo/backend/app/bootstrap.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "旧组合根; v1 bootstrap是唯一装配点, 不得装配fake adapter", False),
    ("demo/backend/app/worker.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "scaffold: 未实现受限worker", False),
    ("demo/backend/app/api/__init__.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "旧api包入口; v1 router只注册已实现路由", False),
    ("demo/backend/app/api/dependencies.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite",
     "scaffold: 未实现依赖注入", False),
    ("demo/backend/app/api/routes/planning.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite", UNIMPLEMENTED, False),
    ("demo/backend/app/api/routes/requests.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite", UNIMPLEMENTED, False),
    ("demo/backend/app/api/routes/plans.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite", UNIMPLEMENTED, False),
    ("demo/backend/app/api/routes/jobs.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite", UNIMPLEMENTED, False),
    ("demo/backend/app/api/routes/events.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite", UNIMPLEMENTED, False),
    ("demo/backend/app/api/routes/simulations.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite", UNIMPLEMENTED, False),
    ("demo/backend/app/api/routes/scenarios.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite", UNIMPLEMENTED, False),
    ("demo/backend/app/api/routes/evidence.py", "A", "apps/backend/src/logistics_backend/__init__.py", "rewrite", UNIMPLEMENTED, False),
    # --- old frontend --------------------------------------------------------
    ("demo/frontend/src/client/generated.ts", "A", "apps/frontend/src/client/generated.ts", "rewrite",
     "旧生成客户端; P24-02由OpenAPI重新生成, 手改即失败", True),
    ("demo/frontend/src/client/api.ts", "A", "apps/frontend/src/client/generated.ts", "rewrite",
     "旧请求层; P24-02重建数据请求层, 不单独占用生成物路径", False),
    # --- old tests / scripts -------------------------------------------------
    ("demo/backend/tests/test_scaffold.py", "A", "tests/integration/test_p01_01_workspace_bootstrap.py", "adapt",
     "旧骨架测试; 新计划用分层真实测试替代, 不导入教学探针", False),
    ("demo/backend/tests/test_contracts.py", "A", "tests/unit/test_p01_01_workspace_bootstrap.py", "adapt",
     "旧契约测试; P02-04重写为Schema导出检查", False),
    ("demo/scripts/export_contracts.py", "A", "apps/backend/src/logistics_backend/__init__.py", "reuse",
     "导出脚本; P02/P05重写为scripts/export_contracts.py", False),
    ("demo/scripts/check_project.py", "A", "apps/backend/src/logistics_backend/__init__.py", "adapt",
     "旧工程检查; P01-02建立scripts/check_architecture.py与gates.py", False),
    ("demo/scripts/build_file_map.py", "A", "OWNERSHIP.json", "adapt",
     "旧文件清单生成器; P01-03改为check_ownership.py", False),
    ("demo/data/scenarios/two_warehouses_20_orders.json", "A", "tests/integration/test_p01_01_workspace_bootstrap.py", "reference",
     "旧20单2仓场景; P04-01按TEST_FIXTURES重新生成可手算fixture", False),
    ("demo/.github/workflows/checks.yml", "A", ".github/workflows/ci.yml", "adapt",
     "旧CI; P01-02建立分层检查CI", False),
]

# Frozen boundary: real legacy files that are deliberately NOT migrated. The G00 recorder
# hashes every inventory path with file hashing and refuses directories, so the boundary is
# expressed as explicit file rows (disposition=reference, target_path=null) instead of
# directory globs; every row's hash is computed by this generator.
FROZEN_FILES: list[tuple[str, str]] = [
    ("demo/deploy/compose.yaml", "旧部署编排, 由新部署目录与P39发布任务重写"),
    ("demo/deploy/README.md", "旧部署说明, 由P38/P39运维文档替代"),
    ("demo/docs/ARCHITECTURE.md", "旧架构说明, 由docs/architecture取代"),
    ("demo/docs/LINEAR_PLAN.md", "旧外部任务计划, 不作为v1任务来源"),
    ("demo/docs/LINEAR_SYNC.md", "旧外部同步记录, 只读留存"),
    ("demo/docs/linear_tasks.json", "旧外部任务导出, 不迁入新仓库"),
    ("demo/docs/NAMING.md", "旧命名与单位约定, 由DATA_CONTRACTS的v1单位口径取代"),
    ("demo/docs/OPEN_SOURCE.md", "旧开源清单, 由P39发布完整性清单取代"),
    ("demo/docs/ROADMAP.md", "旧四周路线, 由PROJECT_MASTER_PLAN取代"),
    ("demo/docs/VERIFICATION.md", "旧验证范围说明, 由Gate证据协议取代"),
    ("demo/docs/devlog/entries/20260910-0000-ac-scaffold.md", "旧开发日志, 只读留存"),
    ("demo/docs/devlog/entries/20260910-1200-a-linear-plan.md", "旧开发日志, 只读留存"),
    ("demo/docs/devlog/entries/README.md", "旧开发日志索引, 只读留存"),
    ("demo/docs/handoff/A_CODEX.md", "旧A侧交接说明, 由docs/workflow交接契约取代"),
    ("demo/docs/handoff/B_CODEX.md", "旧B侧交接说明, 由docs/workflow交接契约取代"),
    ("demo/platform/wanwu/README.md", "旧平台适配资产, 无v1对应能力"),
    ("demo/reference_demos/README.md", "教学参考入口, 只读留存, 永不导入"),
    ("demo/reference_demos/exception_replan.py", "教学探针, 不作为v1实现或oracle"),
    ("demo/reference_demos/run.py", "教学探针入口, 只读留存"),
    ("demo/reference_demos/test_demos.py", "教学测试, 不计为正式验收证据"),
    ("demo/reference_demos/transport.py", "教学运输探针, 不作为正式求解实现"),
    ("demo/reference_demos/validation.py", "教学校验探针, 不作为独立硬校验"),
    ("demo/reference_demos/warehouse.py", "教学仓储探针, 不作为正式排程实现"),
    ("demo/reference_demos/requirements.txt", "教学依赖清单, 不进入v1依赖图"),
    ("demo/reference_demos/requirements-lock.txt", "教学依赖锁, 不进入uv.lock"),
]

# Additional legacy files that exist under demo/ but are not part of the migration target
# set (editor/cache leftovers, package markers, dist output, placeholder READMEs, teaching
# assets). They are registered so that coverage is provable: every real file under demo/
# either has an ENTRIES row or a FROZEN_FILES row.
FROZEN_FILES += [
    ("demo/.editorconfig", "旧编辑器约定, 由新工程约定取代"),
    ("demo/.env.example", "旧环境变量样例, 只记录变量名不记录secret"),
    ("demo/.gitattributes", "旧版本控制属性, 只读留存"),
    ("demo/.gitignore", "旧忽略规则, 由新.gitignore取代"),
    ("demo/.venv/pyvenv.cfg", "旧本地虚拟环境配置, 由uv.lock与uv sync重建"),
    ("demo/backend/app/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/adapters/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/adapters/llm/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/adapters/matrix/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/adapters/persistence/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/adapters/routing/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/adapters/simulation/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/adapters/warehouse/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/api/routes/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/common/__init__.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/app/common/errors.py", "旧包marker, 由logistics_*src-layout取代"),
    ("demo/backend/migrations/README.md", "旧迁移目录占位, P03按新迁移脚本重建"),
    ("demo/backend/migrations/versions/.gitkeep", "旧迁移目录占位, P03按新迁移脚本重建"),
    ("demo/backend/pyproject.toml", "旧后端工程配置, 由apps/backend/pyproject.toml取代"),
    ("demo/backend/requirements-lock.txt", "旧依赖清单, 由uv.lock取代"),
    ("demo/backend/requirements-optional.txt", "旧依赖清单, 由uv.lock取代"),
    ("demo/backend/requirements.txt", "旧依赖清单, 由uv.lock取代"),
    ("demo/backend/tests/fakes/README.md", "旧测试占位说明, 新测试在tests/下重建"),
    ("demo/backend/tests/integration/README.md", "旧测试占位说明, 新测试在tests/下重建"),
    ("demo/backend/tests/llm/README.md", "旧测试占位说明, 新测试在tests/下重建"),
    ("demo/backend/tests/simulation/README.md", "旧测试占位说明, 新测试在tests/下重建"),
    ("demo/backend/tests/transport/README.md", "旧测试占位说明, 新测试在tests/下重建"),
    ("demo/backend/tests/warehouse/README.md", "旧测试占位说明, 新测试在tests/下重建"),
    ("demo/benchmarks/joint/README.md", "旧基准占位说明, 由P36基准框架取代"),
    ("demo/benchmarks/llm/README.md", "旧基准占位说明, 由P36基准框架取代"),
    ("demo/benchmarks/simulation/README.md", "旧基准占位说明, 由P36基准框架取代"),
    ("demo/benchmarks/transport/README.md", "旧基准占位说明, 由P36基准框架取代"),
    ("demo/benchmarks/warehouse/README.md", "旧基准占位说明, 由P36基准框架取代"),
    ("demo/data/scenarios/README.md", "旧数据说明, 由P04-01可手算fixture取代"),
    ("demo/data/simulation/README.md", "旧数据说明, 由P04-01可手算fixture取代"),
    ("demo/data/transport/README.md", "旧数据说明, 由P04-01可手算fixture取代"),
    ("demo/frontend/MODEL_ASSETS.md", "旧前端工程配置, 由apps/frontend重建"),
    ("demo/frontend/README.md", "旧前端工程配置, 由apps/frontend重建"),
    ("demo/frontend/dist/assets/index-BbLVtfpI.css", "旧前端构建产物, 由Vite重新构建"),
    ("demo/frontend/dist/assets/index-D7Yu-JIO.js", "旧前端构建产物, 由Vite重新构建"),
    ("demo/frontend/dist/index.html", "旧前端构建产物, 由Vite重新构建"),
    ("demo/frontend/index.html", "旧前端工程配置, 由apps/frontend重建"),
    ("demo/frontend/node_modules/.package-lock.json", "旧前端依赖安装物, 由package-lock.json与npm ci重建"),
    ("demo/frontend/package-lock.json", "旧前端工程配置, 由apps/frontend重建"),
    ("demo/frontend/package.json", "旧前端工程配置, 由apps/frontend重建"),
    ("demo/frontend/public/favicon.svg", "旧静态资源, 逐项核对后复用"),
    ("demo/frontend/scripts/contracts.mjs", "旧前端脚本, 由P24-02生成脚本取代"),
    ("demo/frontend/scripts/model-budget.test.mjs", "旧前端脚本, 由P24-02生成脚本取代"),
    ("demo/frontend/src/App.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/components/ModulePlaceholder.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/components/scene/LogisticsScene.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/components/scene/modelAssets.ts", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/components/scene/scene.css", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/WorkspacePages.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/events/Page.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/experiments/Page.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/orders/Page.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/plans/Page.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/simulations/Page.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/vehicles/Page.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/warehouses/Page.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/features/workspace.css", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/main.tsx", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/src/styles.css", "旧前端源码, 由apps/frontend重建"),
    ("demo/frontend/tsconfig.json", "旧前端工程配置, 由apps/frontend重建"),
    ("demo/frontend/vite.config.ts", "旧前端工程配置, 由apps/frontend重建"),
    ("demo/scripts/package_demo.py", "旧一次性脚本, 只读留存"),
    ("demo/scripts/project_files.py", "旧一次性脚本, 只读留存"),
]

# large derived directories: never enumerated into the inventory (tens of thousands of
# files), recorded instead as fingerprinted boundaries in `frozen_boundaries`.
BOUNDARY_DIRECTORIES: list[tuple[str, str]] = [
    ("demo/frontend/node_modules/", "构建产物, 由 package-lock.json 与 npm ci 重建"),
    ("demo/.venv/", "本地虚拟环境, 由 uv.lock 与 uv sync 重建"),
]

# Never registered: interpreter/build caches and editor leftovers.
IGNORED_DIRECTORY_NAMES = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".git"}
IGNORED_PREFIXES = tuple(prefix for prefix, _ in BOUNDARY_DIRECTORIES)


def unregistered_files(registered: set[str]) -> list[str]:
    """Every real file under demo/ that the inventory does not register.

    Traversal prunes the two large derived directories and cache directories so the
    check stays bounded; those are covered by `frozen_boundaries` instead.
    """
    root = ROOT / "demo"
    found: list[str] = []
    for current, directories, files in os.walk(root):
        current_posix = Path(current).relative_to(ROOT).as_posix() + "/"
        directories[:] = [
            name for name in directories
            if name not in IGNORED_DIRECTORY_NAMES and not current_posix.startswith(IGNORED_PREFIXES)
        ]
        for name in files:
            relative = (Path(current) / name).relative_to(ROOT).as_posix()
            if relative not in registered:
                found.append(relative)
    return sorted(found)


def boundary_fingerprints() -> list[dict]:
    records = []
    for prefix, reason in BOUNDARY_DIRECTORIES:
        directory = ROOT / prefix
        if not directory.is_dir():
            raise SystemExit(f"boundary directory missing: {prefix}")
        digest = hashlib.sha256()
        count = 0
        for current, directories, files in os.walk(directory):
            directories[:] = [name for name in directories if name not in IGNORED_DIRECTORY_NAMES]
            for name in sorted(files):
                path = Path(current) / name
                digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
                digest.update(b"\0")
                digest.update(sha256(path).encode("utf-8"))
                digest.update(b"\n")
                count += 1
        records.append({
            "prefix": prefix,
            "reason": reason,
            "file_count": count,
            "tree_sha256": digest.hexdigest() if count else None,
            "fingerprint_definition": "sha256 over sorted '<relative_path>\\0<file_sha256>\\n'",
        })
    return records


def build() -> dict:
    rows = []
    for source, owner, target, disposition, evidence, is_document in ENTRIES:
        src = ROOT / source
        if not src.is_file():
            raise SystemExit(f"baseline source missing: {source}")
        rows.append({
            "source_path": source,
            "sha256": sha256(src),
            "owner": owner,
            "disposition": disposition,
            "target_path": target,
            "capability_evidence": evidence,
            "primary_document": is_document,
        })
    for source, reason in FROZEN_FILES:
        src = ROOT / source
        if not src.is_file():
            raise SystemExit(f"frozen boundary file missing: {source}")
        rows.append({
            "source_path": source,
            "sha256": sha256(src),
            "owner": "A",
            "disposition": "reference",
            "target_path": None,
            "capability_evidence": f"frozen non-migrating boundary: {reason}",
            "primary_document": False,
        })
    registered = {row["source_path"] for row in rows}
    if len(registered) != len(rows):
        duplicates = sorted({path for path in registered if [r["source_path"] for r in rows].count(path) > 1})
        raise SystemExit(f"duplicate source_path rows: {duplicates}")
    boundaries = boundary_fingerprints()
    unregistered = unregistered_files(registered)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "P00-01",
        "baseline_date": BASELINE_DATE,
        "plan_version": "1.0.0",
        "source_root": "demo/",
        "generated_by": "tools/ai_coding_plan/baseline_inventory_generate.py",
        "hash_algorithm": "sha256",
        "coverage": {
            "registered_file_count": len(registered),
            "unregistered_file_count": len(unregistered),
            "unregistered_files": unregistered,
            "boundary_directories": boundaries,
            "convention": (
                "登记集合=ENTRIES+FROZEN_FILES；未登记文件必须为空，否则生成器在 --check/写入时报告 "
                "ARCH-0002 的覆盖缺口；node_modules 与 .venv 属派生目录，只记录计数与指纹，不逐文件登记"
            ),
        },
        "uniqueness_rules": [
            "每个 source_path 恰好一条记录，且必须是真实存在的文件(不得指向目录)",
            "每个登记文件必须有一个非空 sha256，由本生成器现场计算",
            "demo/ 下未登记的普通文件必须为空；派生目录(node_modules/.venv)只记录计数与指纹",
            "同一 target_path 可被多个 source_path 归并(例如旧HTTP DTO共同重写到新边界包)",
            "任何 target_path 若为唯一可交付文档, 至多只能有一个 source_path 声明为 docs=True",
            "disposition=rewrite 必须给出 target_path 或 null(明确不迁移)",
        ],
        "documents": [
            {"source_path": "demo/contracts/openapi.json", "target_path": "contracts/openapi.json",
             "note": "v1 OpenAPI唯一来源; P05-01起由已实现router导出, 禁止手改; 旧demo/contracts/*.json不得被第二个source声明为主文档"},
            {"source_path": "demo/contracts/schemas.json", "target_path": "contracts/schemas.json",
             "note": "v1类型JSON Schema唯一来源; P02-04起由scripts/export_contracts.py导出"},
            {"source_path": "demo/frontend/src/client/generated.ts", "target_path": "apps/frontend/src/client/generated.ts",
             "note": "v1生成客户端唯一来源; P24-02由OpenAPI生成, 禁止手改"},
        ],
        "entries": sorted(rows, key=lambda r: r["source_path"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != text:
            print("BASELINE_INVENTORY.json is stale; regenerate it")
            return 1
        print(f"BASELINE_INVENTORY.json up to date ({len(payload['entries'])} entries)")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(payload['entries'])} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
