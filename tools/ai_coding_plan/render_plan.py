"""Render the documentation task system, not the application."""
from pathlib import Path
import json
import re
from build_catalog import ROOT, enrich, PLAN_VERSION

HEADINGS=['Context','Current State','Objective','Scope','Out of Scope','Architecture Constraints','Files','Domain Model','Input','Output','Interfaces','Data Contract','Business Rules','Algorithm','Edge Cases','Error Handling','Logging','Observability','Testing','Test Cases','Acceptance Criteria','Validation Commands','Documentation','Completion Report']
REFERENCES=[
    ('总体设计','PROJECT_MASTER_PLAN.md'),('领域模型','docs/architecture/DOMAIN_CATALOG.md'),
    ('类型与Protocol','docs/architecture/DATA_CONTRACTS.md'),('HTTP与Tool','docs/api/API_CONTRACT.md'),
    ('优化与硬约束','docs/algorithms/OPTIMIZATION_CONTRACT.md'),('仿真与回放','docs/algorithms/SIMULATION_CONTRACT.md'),
    ('指标公式','docs/algorithms/METRICS_CONTRACT.md'),('测试数据','docs/plan/TEST_FIXTURES.md'),
    ('内部接口与接线','docs/architecture/IMPLEMENTATION_CONVENTIONS.md'),
    ('N01-R01规范决定附表','contracts/changes/N01-R01-contract-decisions.json'),
    ('2.0.0迁移范围','contracts/changes/N01-R01-contract-freeze-2.0.0.md'),
    ('Gate','docs/plan/PHASE_GATES.md'),
]
GATE_ASSERTIONS=[
    '旧demo资产有逐项证据；单位/32实体/错误/Protocol冻结；任务DAG与需求追踪无缺口，G00签收不能用本轮静态报告替代。',
    '干净安装、六包导入与分层检查通过；依赖锁可复现；Gate执行器非零命令必失败；旧demo未被覆盖。',
    '32实体及辅助记录可表达，非法状态/单位/额外字段拒绝；Schema确定导出；domain无框架依赖。',
    '真实PostgreSQL迁移、回滚与FK通过；一致快照；最后一份资源并发提交恰一成功；事务失败无半版本。',
    'T1/W1/I1/M1数据hash可复现；反例各有原因；同种子二次导入不重复，不清空既有库。',
    'API认证、错误、分页、revision与持久Job可验收；杀worker后租约可重领；无长求解阻塞请求。',
    '运输typed输入/矩阵节点顺序/版本明确；不可达与0区分；天气倍率100→150秒可手算。',
    '真实OR-Tools T1=9000m/1400分；容量/提送/硬窗/温区/状态各有反例；独立校验通过，无假成功。',
    '五类仓储作业、所有资源与库存/交接具名；DAG环拒绝；初始库存与存储区间契约可验证。',
    '真实CP-SAT W1=25秒；工序/资源/库存/setup反例通过；UNKNOWN不当INFEASIBLE；返回资源时间轴。',
    '所有required硬约束有checked或unsupported记录；J1联合冲突检出；每条硬约束单点破坏反例检出。',
    '仿真状态/事件/RNG/快照类型冻结；非法执行状态拒绝；计划和真实执行事实分离。',
    '真实SimPy T1终态1020秒；t400恢复一致；同秒事件稳定排序；分支隔离、资源无死锁、取消无伪完成。',
    '十类异常payload全覆盖；重复去重、乱序/迟到有明确处理；事件与outbox原子保存。',
    'I1闭包只有T1/T2；T3冻结；在途起点和剩余载荷真实；已执行事实不可改写。',
    '局部→扩大→全局剩余共享预算；救援无瞬移；完整合并方案重验；六项diff正确；失败给诊断/暂停建议。',
    '运输/仓储/联合/重排/仿真API真实连通；J1反馈消除交接冲突；并发/过期确认409；V1不覆盖。',
    '白名单Tool typed args/role/scope/deadline/幂等生效；不直写数据库；未确认commit被拒绝。',
    '真实供应商适配契约smoke有脱敏证据；schema/429/超时/预算/无密钥降级通过；fake不能冒充真实smoke。',
    '意图抽取保留原文/实体证据；缺字段先澄清；有界状态机在预算耗尽停止，不自造ID。',
    'TransportAgent仅通过工具取得候选；无解不造路线；T1数值解释与证据一致。',
    'WarehouseAgent报价非预留且会过期；资源瓶颈解释引用真实任务/诊断，不能杜撰利用率。',
    'ExceptionAgent九步有完整记录；缺救援数据manual_required；解释区分建议与已确认版本。',
    '四角色有界协调、父取消传播、工具注入/越权拒绝；确认令牌绑定对象/actor/revision并防重放。',
    '11导航可达；375px可用；loading/empty/error分开；OpenAPI生成类型无漂移。',
    '订单/车辆/仓库资源页使用真实API；If-Match冲突可见；执行中变更走事件；无业务规则复制。',
    '运输请求/Job/取消/诊断/路线表/费用/确认可操作；T1数值一致，TIMEOUT不显示成功。',
    '仓储甘特显示任务/setup/日历，J1交接冲突可见；只能统一确认有效联合候选。',
    '仿真暂停/步进/注入/快照/分支比较可操作；正式状态不污染，3D不是必要依赖。',
    '异常九步、原因路径、六项diff可检查；原方案/候选/新版本区分，失效候选不可确认。',
    '聊天澄清/工具状态/取消/刷新恢复可用；建议卡数值有证据，脚本注入不执行，明确点击才确认。',
    'WS授权/补发/重复去重/过期cursor重取/慢客户端限额通过；断线轮询继续获得正确终态。',
    '14指标逐项M1及边界通过；source/窗口/定义明确；Dashboard与Metrics不伪造null为0。',
    '至少10次配对seed、同预算实验；规则/solver/Agent与local/global对照；失败样本保留；实验UI/导出真实。',
    '真实PostgreSQL+OR-Tools+SimPy+浏览器完整闭环；worker崩溃/陈旧提交/并发冲突/模型断线可恢复。',
    'A/B/C1/C2/C3五演示均有输入hash、实际解、硬校验、事件、版本diff、指标和回放证据；重复可复现。',
    '参考机10次基准齐备；20单4车2仓HTTP目标与求解预算按Master验收；缓存64MiB有界且换版本失效，所有正确性回归通过。',
    '访问控制/注入/依赖/密钥负例无未处置阻断项；trace可追V2；备份恢复到隔离库保持历史与账本。',
    '开发/使用/运维文档对真实实现，无夸大能力；干净环境命令可执行，缺模型密钥降级有明确指南。',
    'G00–G38证据未失效；发布候选hash/SBOM/锁/迁移完整；干净安装五演示通过；没有凭据，限制与恢复点明确。',
]

SNIPPETS={
 'foundation':'输入为路径/版本/依赖清单和Architecture Contract。输出为文件、Schema或测试证据，不产生业务调度。环境变量只记录名称不记录secret；所有相对路径从目标仓库根目录解析。',
 'domain':'每实体id:UUID,status:唯一Enum,created_at/updated_at:UTC,row_version:int>=0,schema_version:str。重量g、容积cm³、距离m、金额分、温度decic、求解相对秒。嵌套列表必须有具名元素Schema，公共状态引用domain.states。',
 'transport':'TransportProblem(snapshot,nodes:tuple[RoutingNode],vehicles:tuple[VehicleState],matrix:TravelMatrix,constraints,policy)；TransportSolution(status,engine_metadata,candidate:TransportPlan|None,validation:ValidationReport|None,diagnostics)。RoutingNode含业务ID、pickup/delivery类型、service_s、hard_window、load_delta；VehicleState含起终点、start_load、两维容量、setpoint、司机班次。',
 'warehouse':'WarehouseProblem(snapshot,tasks:tuple[WarehouseTask],calendars,initial_inventory,storage_intervals,setup_policy,handoffs,budget)；WarehouseSolution(status,assignments,storage_allocations,setup_operations,validation,engine_metadata)。任务含kind/duration/window/predecessor_ids/typed requirements；资源占用[start,end)。',
 'simulation':'SimulationRequest(scenario_ref,validated_plan,schedule_version_id,seed,until_s,stochastic_policy)；TwinState(time_s,orders,vehicles,warehouses,inventory,resource_usage,last_event_seq)；Snapshot另存pending_events/RngState/剩余工作/hash。分支ID明确，不传SimPy Event/Process出边界。',
 'exception':'ImpactReport(event_ids,affected_tasks,affected_orders,affected_resources,reason_paths)；RescheduleBoundary(frozen_tasks,virtual_starts,residual_loads,resource_blocks,mutable_task_ids)；RescheduleSolution(status,candidates,rounds,selected_id,diff)。ScheduleDiff必含changed_tasks/added_cost/delay_difference/resource_changes/affected_orders/constraint_results。',
 'api':'HTTP使用DTO，不传ORM或引擎对象。JobRef(job_id,status,status_url,result_url,trace_id)；CommitCommand(schedule_id,candidate_id,candidate_hash,expected_active_version_id,snapshot_hash,idempotency_key,confirmation_token?)；错误ErrorEnvelope(code,message,trace_id,retryable,typed details)。POST长作业202，陈旧/竞争409，字段422。',
 'agent':'ToolCallRequest(run_id,call_id,name:ToolName,arguments:判别union,deadline,idempotency_key,expected_revision)；ToolResult(status,data:typed union,error?,trace_id)。AgentOutcome(status,candidate_refs,questions,explanation,decision_ref)只引用服务结果；IntentDraft每约束带原文证据；模型不得提交自由生成route。',
 'frontend':'UI Props从生成OpenAPI类型组合。QueryState为loading/ready/empty/error/stale/cancelled判别联合；业务ID和enum从generated.ts引用。JobRef与版本状态分开；显示秒/米/克/分到用户单位时仅格式转换，不重算调度。',
 'evaluation':'MetricSet(scope_id,source,window,definition_version,values:tuple[MetricValue],sample_count,coverage,missing_reasons)；MetricValue含code/unit/value|null/numerator/denominator；ExperimentSpec含scenario_ref/policy_ids/paired_seeds/equal_budget/environment。无分母null，失败样本不能删除。',
 'integration':'输入为固定ScenarioBundle、真实服务配置和GateEvidence；输出为带revision/环境/hash/原始命令退出码的EvidenceBundle。不得将mock运行计作真实引擎或模型验收，所有产物注明planned/simulation/actual来源。',
}
def category(t):
    p=t['phase']
    if p<=1 or p==4:return 'foundation'
    if p in (2,3):return 'domain'
    if p in (5,16,31):return 'api'
    if p in (6,7):return 'transport'
    if p in (8,9,10):return 'warehouse'
    if p in (11,12,13):return 'simulation'
    if p in (14,15):return 'exception'
    if p in range(17,24):return 'agent'
    if p in range(24,31):return 'frontend'
    if p in (32,33):return 'evaluation'
    return 'integration'

def solver_sections(t):
    p=t['phase']
    if p==7:
        values=[
            'NextVar、VehicleVar、ActiveVar；Time/Weight/Volume CumulVar；仅本任务负责的构件可修改。',
            '必需节点唯一服务、车辆起终点/资格、逐段载荷、提送同车先后、服务开始硬窗/班次、温控/货物资格；本任务新增项见Business Rules，其余沿用已有模块。',
            '距离弧成本与ObjectivePolicy整数分费用；未服务惩罚仅用于明确optional订单；禁止用罚分破坏硬约束；记录目标分项与溢出上界。',
            'OR-Tools精确锁版本；默认5000ms共享wall预算；初解PARALLEL_CHEAPEST_INSERTION，局部搜索GUIDED_LOCAL_SEARCH；参数仅使用当前锁版本支持字段；worker提供硬截止。',
            '仅非空assignment提取业务ID/route/stop/arrival/service/depart/load/cost；保存engine_status与incumbent标记，不把启发式可行称全局最优。',
            '独立按原快照与矩阵重算；T1正例与本任务负例；时间预算耗尽区分未知/超时与已证明无解。',
        ]
    elif p==9:
        values=[
            '整数start/end/duration、资源presence、optional intervals、相邻setup弧；只扩展当前构件。',
            'ExactlyOne资源、NoOverlap/Cumulative、前驱/硬窗/日历/库存温区；setup以相邻弧及占用interval表达，不能只写注释。',
            'soft_tardiness_cost + overtime_cost + setup_cost + makespan_weight*makespan，整数分统一；硬约束不可软化。',
            'CP-SAT num_search_workers=1、random_seed=42、默认5s；共享deadline扣除已消耗时间；固定版本配置hash。',
            '只取选中presence区间；明确资源/开始/结束/setup/存储，保留OPTIMAL/FEASIBLE/INFEASIBLE/MODEL_INVALID/UNKNOWN与bound。',
            '独立sweep-line和任务链检查；W1=25s与容量/setup反例；UNKNOWN不宣称无解。',
        ]
    elif p==15:
        values=[
            '仅mutable任务的路径、资源、时刻；completed/frozen prefix固定，外部资源占用固定interval。',
            '原运输/仓储硬约束完整保留；额外冻结承诺、在途起点/剩余载荷、救援/返仓实物链；局部边界不漏资源冲突。',
            '沿用ObjectivePolicy并加入显式扰动项；仅已验证候选按未服务/软延误/成本/扰动比较，不宣称词典序全局最优。',
            'local→expanded→all_unexecuted最多3层、15s共享budget；单层消耗从总预算扣除，不自动放松硬窗。',
            '合并全计划并保留task_id，生成CandidateEvaluation/六项diff及每轮状态；不在solver写正式ScheduleVersion。',
            '完整ConstraintValidator检查合并候选和冻结hash；I1保留T3；缺救援事实MANUAL_REQUIRED；失败保留诊断。',
        ]
    else:
        values=[
            '本任务为独立校验/测试，不建立生产求解决策变量；oracle枚举只位于tests。',
            '按ConstraintCoverage逐条从候选和快照重算；未知required规则fail closed。',
            '本任务不改变求解目标；只验证原目标分项与硬约束，没有以罚分接受违规的通道。',
            '调用真实引擎的测试固定锁版本、预算和seed；独立validator自身不依赖solver变量。',
            '输出Violation列表、checked/required/unsupported、hash与规则版本，不输出伪造assignment。',
            '每个必需硬规则至少单点破坏反例；小例手算/oracle；不能复用solver结果当作独立证明。',
        ]
    names=['Decision Variables','Constraints','Objective Function','Solver Configuration','Result Extraction','Validation']
    return '\n\n'.join(f'### {name}\n\n{v}' for name,v in zip(names,values))

def render_prompt(t, seen):
    tid=t['id']; p=t['phase']; k=t['kind']; cat=category(t)
    created=[f for f in t['allowed_files'] if f not in seen]
    modified=[f for f in t['allowed_files'] if f in seen]
    seen.update(t['allowed_files'])
    refs='\n'.join(f'- [{label}](../../../{path})' for label,path in REFERENCES)
    deps='、'.join(t['deps']) or '无前置Task；必须先阅读本包架构总览与原始需求。'
    tests='\n'.join(f'| {i+1} | {c.replace("|"," / ")} | 必须按箭头右侧断言；禁止只断言status非空。 |' for i,c in enumerate(t['cases']))
    write_list=lambda files:'\n'.join('- `'+f+'`' for f in files) if files else '- 无；如运行时已存在同名文件，核对前置产物后只做本任务范围增量。'
    alg=t['algorithm']+('\n\n'+solver_sections(t) if k=='solver' else '\n\n按已冻结的接口完成上述步骤；纯领域规则不引入框架，副作用经所属应用服务；不得为本任务新建第二套算法或规则。')
    extra=''
    if k=='simulation':extra='\n- Simulation Test：`'+t['special_test']+'`；验证时间边界、状态守恒、恢复/重复事件行为，使用真实SimPy。'
    if k=='solver':extra='\n- Solver Test：`'+t['special_test']+'`；真实OR-Tools与独立oracle/负例；约束覆盖不得只用mock。'
    if k=='frontend':extra+='\n- Integration Test是组件+生成客户端+MSW网络边界测试；Phase34另用真实API浏览器验收。不要把MSW测试称生产后端已接通。'
    if k=='e2e':extra+='\n- 已列出的Playwright spec必须对真实API/数据库/引擎运行，保存截图与网络证据；测试隔离库禁止使用个人正式数据。'
    if k=='docs' and p==0:extra+='\n- 此任务只验证规划文档：Unit为规划检查器负例测试，Integration为任务/契约/依赖交叉检查；不要求虚构业务测试。'
    commands='\n'.join(t['commands'])
    observation={
        'transport':'solver_runs_total{kind,status}、solver_build_seconds、solver_solve_seconds、validator_rejections_total{code}',
        'warehouse':'warehouse_solve_seconds、constraint_checks_total{code,outcome}、solver_status_total{kind,status}',
        'simulation':'simulation_events_total{kind,outcome}、simulation_step_seconds、snapshot_restore_seconds、simulation_pending_events',
        'exception':'impact_analysis_seconds、reschedule_seconds、reschedule_rounds_total{scope,outcome}、candidate_validation_failures_total{code}',
        'agent':'agent_runs_total{role,outcome}、tool_calls_total{tool,outcome}、llm_requests_total{provider,outcome}、llm_tokens_total{direction}',
        'api':'http_requests_total{operation,status_class}、job_queue_wait_seconds、job_lease_expirations_total、commit_conflicts_total{reason}',
        'frontend':'页面加载/错误/交互耗时及接口失败次数（测试证据中可观测）；不新增订单级用户跟踪',
        'evaluation':'experiment_runs_total{policy,outcome}、metric_compute_seconds、missing_metric_values_total{reason}',
        'foundation':'规划/工程检查的通过数、失败数、耗时与处理文件数（保存检查报告）',
        'domain':'schema_validation_total{schema,outcome}和状态转换拒绝计数，由API/适配层记录，domain不引入telemetry SDK',
        'integration':'验收命令退出码、用例数、关键skip数、环境版本、产物hash、执行耗时与失败原因',
    }[cat]
    sections={
      'Context':f'你是本项目的Coding Agent。本项目以LLM工具调用 + OR-Tools确定性优化 + SimPy推演 + FastAPI/React/PostgreSQL实现冷链优先调度。当前任务位于Phase {p:02d}「{PHASE_NAMES[p]}」，任务ID `{tid}`，负责方 `{t["owner"]}`。只执行本任务，不实现整个模块或后续阶段。\n\n本Prompt连同仓库内契约足以工作，不依赖历史聊天。开始时读取以下本地规范；字段以契约实施后的唯一Python类型为准，文档若冲突先记录issue：\n\n{refs}',
      'Current State':f'理论上以下依赖已经交付且证据有效：`{deps}`。用TASK_GRAPH和Gate证据逐项核验，不能仅根据文件名存在认定完成。\n\n本计划初始所有任务为planned，Gate为not_run；当前旧`demo/`是0.1骨架/展示资产，不代表本任务已实现。目标工作根为含PROJECT_MASTER_PLAN.md的目录，新包在apps/和packages/；旧demo只读，不从教学探针导入。若前置缺失/失败，报告具体阻断并修复前置任务，禁止跳Gate。',
      'Objective':t['title']+'。唯一可验收交付物为下述Files对应实现/文档，以及本任务明确测试证据。',
      'Scope':f'仅实现 `{t["slug"]}` 所属能力，遵循下面Business Rules和Algorithm。允许的实现、测试、文档文件完整列于Files。跨模块依赖通过既有Protocol注入。当前任务并行候选：{", ".join(t["parallel"]) or "无，按阶段内依赖顺序执行"}；即使列出候选，运行前仍检查实际写集合与依赖。',
      'Out of Scope':'禁止顺手实现后续阶段、重新设计架构、改另一所有者实现掩盖集成错误、引入微服务/Kubernetes/队列集群/复杂GIS/复杂权限/3D关键依赖。测试替身不得进正式bootstrap。除Files及经明确记录的阻断契约迁移外，其他文件均不在范围。',
      'Architecture Constraints':'1. Domain Contract → Schema → Service Interface → Implementation → Test → Integration，跨边界不传未经定义dict/Any。\n2. LLM只抽取/分解/调用/解释，不自由生成最终调度；Agent只经工具到应用服务，不能直写数据库。\n3. Solver候选必须经确定性独立硬校验；正式提交只能由ScheduleService完成，重排追加ScheduleVersion不覆盖历史。\n4. Domain不导入框架/ORM/模型SDK；application不导入adapters，bootstrap唯一装配点；React不硬编码业务规则或另写枚举。\n5. 不擅自改公共接口。发现架构问题先记录`docs/architecture/issues/`；非阻断继续限定任务，阻断只做最小契约迁移并更新所有受影响调用方/测试/导出物，禁止大规模重构。\n6. 禁止TODO占位核心逻辑、fake implementation、hard-coded demo answer、绕过Solver、只写代码不写测试、吞掉Exception、重复定义Domain Model。开发时未实现部分必须显式失败，不能返回固定成功。',
      'Files':'预计创建（若前置已创建则仅核对并增量修改）：\n\n'+write_list(created)+'\n\n预计修改已有前置产物：\n\n'+write_list(modified)+'\n\n禁止修改：`demo/`、`demos/`教学代码、非本任务文件、已提交历史版本或审计内容。`contracts/*.json`和`generated.ts`若列入范围只能运行生成器更新，不得手改。包marker只有确需导出本任务类型时可修改，须先在完成报告列出精确路径；不能借此越过接口边界。',
      'Domain Model':t['model']+'。实体字段/状态/生命周期以DOMAIN_CATALOG为准；本任务新增的非实体view只组合既有字段。每实体继承UUID、唯一status Enum、UTC created_at/updated_at、row_version、schema_version，不复制业务模型。',
      'Input':'正式输入由Interfaces的签名左侧和DATA_CONTRACTS相应具名Schema定义：\n\n'+SNIPPETS[cat]+'\n\n必须覆盖Test Cases给出的具体输入变体；使用TEST_FIXTURES的完整T1/W1/I1/S1/M1定义，未指出的字段保持原值。HTTP边界额外携带actor、trace_id、Idempotency-Key或If-Match（按API_CONTRACT）。',
      'Output':'返回Interfaces右侧的具名结果/明确文件产物，包含本任务Test Cases所列可观察值；不能只返回任意dict或成功布尔。业务失败保留类型化原因；候选/已验证/已确认分别表达；任何正式新方案必须带version_id、parent_version_id、snapshot_hash和校验引用。本文档/测试任务只返回证据，不生成调度数据。',
      'Interfaces':'本任务采用以下精确公开入口；多个入口用分号分隔，HTTP路径均带API_CONTRACT前缀：\n\n```text\n'+t['interface']+'\n```\n\n新实现放在本任务Files并导出到既有组合根/注册入口时仅做必要装配；第三方引擎对象留在adapter内部。若签名需扩展，不得先改后解释：先写`contracts/changes/`说明输入输出影响。',
      'Data Contract':SNIPPETS[cat]+'\n\n共享单位：整数秒/米/克/cm³/分/decic，UTC epoch；服务开始窗闭区间，占用[start,end)。业务契约版本2.0.0，Gate证据schema仍1.0.0；边界extra=forbid。N01-R01新增必需字段/enum/引用规则是本轮破坏设计决定，旧1.0.0不能只改版本号沿用；按迁移说明显式转换与重验。Optional、未知、无解、超时的语义不得混淆；参考DATA_CONTRACTS的SolveStatus/JobStatus/错误表。',
      'Business Rules':t['rule']+'\n\n所有业务结果绑定输入快照和规则版本。空输入仅在契约允许零需求时可返回有效空结果；有必需需求却无解不能返回空路线成功。已执行事实与已确认历史不可改写。',
      'Algorithm':alg,
      'Edge Cases':'必须处理：'+ '；'.join(t['cases'])+'。\n\n共同边界按本任务适用范围测试：空集合、重复ID、非法枚举/单位、负值/整数溢出、缺失关联、边界时间相等、过期revision、取消/超时、依赖不可用。对不适用项在Completion Report说明，不为制造覆盖率添加无意义断言。',
      'Error Handling':'输入契约错误→INVALID_INPUT/422；非法状态→INVALID_TRANSITION；请求未知必需能力→INVALID_INPUT/422并用UnsupportedDetail说明，拒绝有效结果；独立硬校验发现未支持规则时保留unsupported_codes且不得报告有效候选；开发期间未实现能力仍按DATA_CONTRACTS返回501且不得进入对应Gate，不自造UNSUPPORTED错误码；版本/资源/幂等冲突→409；权限→401/403；依赖不可用→503。求解TIMEOUT/UNKNOWN/INFEASIBLE为typed结果，不统一包装成500。\n\n仅捕获明确可处理的第三方异常并保留cause/trace；边界可最后捕获未预期错误记录脱敏stack并返回INTERNAL_ERROR，禁止except Exception: pass。重试仅幂等暂态操作，有最大次数与deadline；不重试业务硬约束失败。',
      'Logging':f'事件名使用 `{tid.lower().replace("-","_")}.started/completed/rejected`（纯函数由调用边界记录）。记录operation、trace_id、输入/输出hash、schema_version、结果状态、duration_ms、明确错误码；涉及求解追加引擎版本/配置/seed，涉及版本追加base/candidate/version引用。禁止输出secret、完整个人数据或模型内部思维。文档任务保存检查日志与文件hash。',
      'Observability':observation+'。\n\n不得用order_id/vehicle_id/trace_id作metric标签；这些只在日志或trace。此阶段还没有完整监控backend时，先输出结构化测量/诊断，P37接统一出口；不能因此跳过可观察结果。',
      'Testing':f'- Unit Test：`{t["unit_test"]}`；测试本任务规则/转换/状态或文档检查负例。\n- Integration Test：`{t["integration_test"]}`；验证真实相邻模块的数据/服务边界；涉及数据库使用隔离真实PostgreSQL。'+extra+'\n- 所有测试均有确定数据和预期，不用固定假成功掩盖缺失实现；命令零用例或关键skip视为未验收。',
      'Test Cases':'| 编号 | 明确输入 → 预期结果 | 断言要求 |\n| --- | --- | --- |\n'+tests+'\n\n正例数值来自TEST_FIXTURES手算；负例一次仅改指定字段，明确断言错误码/违规位置及无副作用。多可行解场景检查不变量/目标容许范围，不随意固定solver搜索顺序。',
      'Acceptance Criteria':f'1. Objective与Files交付完全对应，本任务所有具体Test Cases通过。\n2. 下列命令实际执行且exit code=0，记录真实测试数量，不含关键skip/占位返回；编译成功不等于业务通过。\n3. 无共享类型/生成客户端漂移，依赖边界检查通过；失败路径不产生半计划或伪成功。\n4. 完成报告和任务文档齐备，并将证据交 `{t["phase_gate"]}`：{GATE_ASSERTIONS[p]}\n5. 单任务成功不自动使Gate成功；当前Gate未通过，禁止开始下一Phase。',
      'Validation Commands':'从仓库根目录执行。Phase01之后使用已锁定环境；数据库任务先按环境手册启动隔离PostgreSQL。以下为完成本任务后的强制命令，**本轮规划没有执行未来应用测试**：\n\n```powershell\n'+commands+'\n```\n\n如工具/依赖/凭据不可用，保留实际错误并记录未执行项，不能写全部通过。修改失败后只重跑受影响测试和必需Gate；不得在未通过时跳阶段。',
      'Documentation':f'更新 `{t["task_doc"]}`：已实现能力、接口/单位、输入输出样例、状态与失败语义、实际限制、关联测试。完成报告写 `{t["report"]}`。公共契约变化另追加contracts/changes说明及架构issue，重新导出Schema/OpenAPI/TS并重验受影响Gate，不通过聊天补交接。',
      'Completion Report':'最终答复和报告必须逐项包含：\n\n- Files created（精确路径）\n- Files modified（精确路径及原因）\n- Tests added（文件、用例和覆盖的业务边界）\n- Commands executed（实际命令、工作目录、环境）\n- Test results（exit code、passed/failed/skipped数量、原始日志与产物位置）\n- Known limitations（支持/不支持及用户可见行为）\n- Remaining risks（有证据的风险、影响、下一责任任务）\n\n另记录Task ID、契约版本前后、输入/输出hash、当前代码revision/相关文件hash、Gate证据引用。不得声称尚未运行的测试通过，不把本任务完成说成整个系统完成。',
    }
    return f'# {tid} · {t["title"]}\n\n计划版本{PLAN_VERSION} · 状态planned · 阶段Gate {t["phase_gate"]}\n\n'+'\n\n'.join('## '+h+'\n\n'+sections[h] for h in HEADINGS)+'\n'

def write(path,content):
    target=ROOT/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content,encoding='utf-8')

def render_graph(data):
    tasks=data['tasks'];gates=data['gates']
    rows=['# Task Graph · 严格阶段屏障下的DAG','',
        f'共{len(tasks)}个独立Task、40个Gate节点。箭头为先完成→后启动。机器事实见[任务清单](docs/plan/TASK_MANIFEST.json)。所有Task初始planned，Gate初始not_run；下表不是实时项目状态，也未修改外部Linear。','',
        'Dependencies列包含前阶段Gate以及必要同阶段任务；每个Gate依赖本阶段全部Task。Blocks是直接反向边（并非所有传递后继）。Can Run In Parallel只列同阶段无传递依赖且写文件不冲突的候选；启动时仍要求各自所有Dependencies有效。未通过Gate不能通过并行跳阶段。','',
        '```mermaid','flowchart LR']
    milestone_gates=[0,5,10,16,23,33,35,39]
    for a,b in zip(milestone_gates,milestone_gates[1:]):rows.append(f'  G{a:02d} -->|依次通过中间各Gate| G{b:02d}')
    rows+=['```','','以上仅为里程碑Gate投影，连线不能跳过中间Gate；完整可机读任务边在manifest，下表列出全部149个Task/Gate节点。','']
    for p,name in enumerate(data['phase_names']):
        rows += [f'## Phase {p:02d} · {name}','','| Task / 明确交付物 | Dependencies | Blocks | Can Run In Parallel |','| --- | --- | --- | --- |']
        for t in [t for t in tasks if t['phase']==p]:
            rows.append(f'| [{t["id"]} · {t["title"]}]({t["prompt"]}) | '+', '.join(t['deps'])+' | '+', '.join(t['blocks'])+' | '+(', '.join(t['parallel']) or '无')+' |')
        g=gates[p]
        rows.append(f'| **{g["id"]}：阶段验收证据** | '+', '.join(g['deps'])+' | '+(', '.join(g['blocks']) or '发布候选签收完成')+' | 无，屏障 |')
        rows += ['',GATE_ASSERTIONS[p],'']
    write('TASK_GRAPH.md','\n'.join(rows))

def render_gates(data):
    rows=['# Phase Gate · 执行与证据协议','',
        '每阶段均有G00–G39；默认严格00→39。Task完成不等于Gate通过，静态规划校验不等于业务验收。缺文件、命令非零、零测试、关键skip、使用fake冒充真实引擎、产物hash不匹配均失败。失败保留原始日志，禁止启动下一阶段。','',
        '## 引导和统一命令','',
        'P00的三个任务只处理架构文档，由现有规划检查器验证。完成P00专属文档与Completion Reports后，执行 `python tools/ai_coding_plan/validate_plan.py --self-test --record-g00`，它核验G00所需文件并记录静态/文档Gate证据；本轮仅静态检查不带此选项，不签收G00。','',
        'P01-02实现正式`scripts/gates.py`。随后每阶段所有Task完成时执行 `uv run python scripts/gates.py --phase NN --revision auto`（把NN换成表中两位数字）。执行器读取TASK_MANIFEST任务命令，逐个亲自执行、保存完整stdout/stderr/exit code和产物hash；禁止仅读取手写成功字段。','',
        'Evidence最小字段：schema_version、gate_id、status、started_at/finished_at、code_revision、dirty_tree_hash、dependency_evidence_hashes、input_artifact_hashes、environment_fingerprint、commands[{argv,cwd,exit_code,log_path,log_hash,test_counts}]、acceptance_artifacts、limitations、reviewer。输出`artifacts/gates/GNN.json`和同目录原始日志；用户密钥不得包含在环境指纹。','',
        'revision可为Git HEAD+dirty树hash；若尚无Git，用相关源文件清单hash。不同阶段可以不同提交，不要求最终HEAD等于每阶段旧HEAD。freshness由相关输入/源文件/公共契约与依赖证据hash判断，排除产物日志、时间戳及报告自身避免自引用；影响某Gate的变更使其及所有下游证据失效，不能以改日期恢复。','',
        '非代码检查也需可验证证据：文档命令实跑、链接/schema负例、能力追踪；UI用组件网络测试+后续真实浏览器；模型供应商smoke需要实际配置和脱敏请求ID。凭据缺失是未验收，不擅自取消G18要求；可预备同阶段独立测试但不能跳过Gate。','',
        '## 40个Gate','', '| Gate / 出口Phase | 必需Task | 额外业务断言 / 证据 | 失败阻塞 |','| --- | --- | --- | --- |']
    for g in data['gates']:
        p=g['phase'];blocked=f'Phase {p+1:02d}及以后' if p<39 else '正式发布签收'
        rows.append(f'| {g["id"]} / {p:02d} | '+', '.join(g['deps'])+' | '+GATE_ASSERTIONS[p]+' | '+blocked+' |')
    rows += ['','## 特定环境和发布门槛','',
        '- G03/G05/G16/G34/G37：真实隔离PostgreSQL，双事务/进程崩溃与回滚证据。清空/恢复仅显式测试库。',
        '- G07/G09/G10/G15：真实OR-Tools、小例手算或独立oracle、硬约束反例；各引擎状态记录不得互相冒充。',
        '- G12：真实SimPy连续/恢复轨迹比对、事件排序、分支隔离。',
        '- G18/G23：真实模型契约smoke与固定测试替身的功能负例分别留档；smoke不得写成统计质量保证。',
        '- G35：A/B/C1/C2/C3逐场景输入hash、真实候选、校验、原新版本、diff、指标、事件及快照。',
        '- G36：参考机明示CPU/RAM/OS，20单4车2仓、单worker、10次；HTTP接收p95<500ms/健康p95<200ms；正常小例单域5s/联合局部15s预算内有可行解；超时/失败不得删除。100单扩展profile仅观测，不伪称大规模生产能力。',
        '- G39：精确发布候选hash、锁文件/SBOM、许可证、无secret、干净安装和五演示实测；只有本地候选打包在任务Scope内，外部发布另按用户授权。','']
    write('docs/plan/PHASE_GATES.md','\n'.join(rows))

def render_traceability(data):
    mapping=[
      ('R01','混合职责边界/Contract First/禁止任意dict',['P00-02','P01-02','P02-04','P17-01','P23-02'],'G23'),
      ('R02','运输：起终点、订单、车辆、重量、容积、温区、货物类型、时效/服务/时间窗、距离/行时、路况/天气、可用状态',['P06-01','P06-02','P07-01','P07-02','P07-03','P07-04','P07-05','P07-06','P07-07'],'G07'),
      ('R03','仓储入库/出库/分拣/装车/卸货及全部资源',['P08-01','P08-02','P09-01','P09-02','P09-03'],'G09'),
      ('R04','仓储时间窗/互斥/容量/依赖/准备/清洁/月台/温区/分拣切换',['P09-01','P09-02','P09-04','P09-05'],'G09'),
      ('R05','十类异常：故障、延误、交通、天气、货物、取消、需求增减、设备故障、仓资源不可用',['P13-01','P13-02','P14-01'],'G14'),
      ('R06','异常九步流程、Local优先、范围扩展及失败处置',['P14-01','P14-02','P15-01','P15-02','P15-03','P15-04','P22-01'],'G22'),
      ('R07','32实体逐一ID/状态/生命周期/字段/关联/时间',['P02-01','P02-02','P02-03','P02-04','P03-01','P03-02'],'G03'),
      ('R08','ScheduleVersion不可覆盖及六项差异',['P02-03','P03-04','P15-04','P16-03','P29-02'],'G29'),
      ('R09','确定性硬校验/仓运联合可行性',['P07-06','P09-05','P10-01','P10-02','P10-03','P16-02'],'G16'),
      ('R10','DigitalTwin/Simulation/Event/Scenario引擎、快照回放和反事实',['P11-01','P11-02','P12-01','P12-02','P12-03','P12-04','P13-01'],'G13'),
      ('R11','Coordinator/Transport/Warehouse/Exception Agent及工具接口',['P17-01','P17-02','P18-01','P18-02','P19-01','P19-02','P20-01','P20-02','P21-01','P21-02','P22-01','P22-02','P23-01','P23-02'],'G23'),
      ('R12','11个React页面及WebSocket实时',['P24-01','P24-02','P25-01','P25-02','P25-03','P26-01','P26-02','P27-01','P27-02','P28-01','P28-02','P29-01','P29-02','P30-01','P30-02','P31-01','P31-02','P32-03','P33-02'],'G33'),
      ('R13','14项指标、口径、差异和实验基线',['P32-01','P32-02','P32-03','P33-01','P33-02'],'G33'),
      ('R14','A正常冷链/B仓运联合/C故障取消天气演示',['P35-01','P35-02','P35-03','P35-04','P35-05'],'G35'),
      ('R15','可追踪性/错误/安全/并发/幂等/备份恢复',['P03-04','P05-01','P05-03','P17-01','P34-03','P37-01','P37-02','P37-03'],'G37'),
      ('R16','性能、工程部署、文档及发布',['P01-01','P36-01','P36-02','P38-01','P38-02','P39-01','P39-02'],'G39'),
      ('R17','完整Master/TaskGraph/14目录/每Prompt结构/40Gate',['P00-01','P00-02','P00-03'],'G00'),
      ('R18','3D及其他过早设计不得影响核心MVP',['P00-02','P24-01','P28-01','P38-02'],'G38'),
    ]
    rows=['# 需求→任务→Gate追踪','','原始用户要求保存在[USER_REQUIREMENTS](USER_REQUIREMENTS.md)。R编号用于本计划追踪，不替代外部任务系统。每行的证据来自对应Prompt中Test Cases/Validation Commands及Gate原始结果，不能仅看该行存在即算实现。','','| 需求 | 内容 | Task | Gate / 必需证据 |','| --- | --- | --- | --- |']
    for key,title,ids,gate in mapping:
        rows.append(f'| {key} | {title} | '+', '.join(ids)+f' | {gate}；对应具体用例、命令日志与产物hash |')
    rows+=['','32实体详表见[DOMAIN_CATALOG](../architecture/DOMAIN_CATALOG.md)；各实体由P02/P03完整映射，不能省略某一行。十类异常payload与处理约束见[DATA_CONTRACTS](../architecture/DATA_CONTRACTS.md)，P13测试要求十种判别全部过Schema正/反例。14指标逐项公式见[METRICS_CONTRACT](../algorithms/METRICS_CONTRACT.md)，P32每一项均需手算/边界测试。','']
    write('docs/plan/REQUIREMENTS_TRACEABILITY.md','\n'.join(rows))

def main():
    data=enrich();global PHASE_NAMES;PHASE_NAMES=data['phase_names']
    write('docs/plan/TASK_MANIFEST.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    render_graph(data);render_gates(data);render_traceability(data)
    seen=set(); index=['# 独立Coding Prompt索引','',f'共{len(data["tasks"])}个Prompt，40个Phase，14个目录。编号Pxx-yy中的xx是Phase，目录数字不是Phase编号。每个文件可以完整交给新的Codex执行；先核验Dependencies，严格执行Gate。','', '[返回使用入口](../../AI-CODING-PLAN.md) · [Task Graph](../../TASK_GRAPH.md) · [Gate](../plan/PHASE_GATES.md)','']
    for p,name in enumerate(PHASE_NAMES):
        index += [f'## Phase {p:02d} · {name}','']
        for t in [x for x in data['tasks'] if x['phase']==p]:
            write(t['prompt'],render_prompt(t,seen))
            rel=t['prompt'].removeprefix('docs/prompts/')
            index.append(f'- [{t["id"]} {t["title"]}]({rel})')
        index.append('')
    write('docs/prompts/README.md','\n'.join(index))
    print(f'Rendered {len(data["tasks"])} prompts, 40 gates, task graph and indexes.')

if __name__=='__main__': main()
