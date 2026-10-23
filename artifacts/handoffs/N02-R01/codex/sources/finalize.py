"""Seal N02-R01's blocked independent review; preserve every official record."""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode=True
root=Path.cwd().resolve()
assert root==Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve()
out=root/'artifacts/handoffs/N02-R01/codex'
handoff=root/'docs/handoffs/N02-R01/codex.md'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads((root/p).read_text(encoding='utf-8-sig'))
def write(name,value):
    (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

before=read('artifacts/handoffs/N02-R01/codex/review-scope-before.json')
excluded=set(before['excluded_derived_parts'])
snapshot={}
for current,dirs,files in os.walk(root):
    dirs[:]=[d for d in dirs if d not in excluded]
    for name in files:
        p=Path(current)/name
        rel=p.relative_to(root).as_posix()
        if rel.startswith(('tmp/','artifacts/handoffs/N02-R01/','docs/handoffs/N02-R01/')):
            continue
        snapshot[rel]=sha(p)
changes=[dict(path=p,before=before['files'].get(p),after=snapshot.get(p))
         for p in sorted(set(before['files'])|set(snapshot)) if before['files'].get(p)!=snapshot.get(p)]
assert not changes,changes
scope=read('artifacts/handoffs/N01-R01/codex/scope-before.json')
protected_errors=[p for p,h in scope['protected'].items() if not (root/p).is_file() or sha(root/p)!=h]
assert not protected_errors,protected_errors
write('review-scope-final.json',dict(existing_tree_files=len(snapshot),changed_or_added_outside_delivery_and_scratch=changes,
      protected_files=len(scope['protected']),protected_unchanged=len(scope['protected']),
      frozen_records_unchanged=True,official_G00_G01_and_old_logs_unchanged=True,
      scope='non-derived project files; dependency/cache/.mimosa trees excluded as declared',
      all_actual_writes=['tmp/N02-R01/**','artifacts/handoffs/N02-R01/codex/**','docs/handoffs/N02-R01/codex.md']))

loader=importlib.util.spec_from_file_location('n02_r01_final_runner',root/'scripts/gates.py')
module=importlib.util.module_from_spec(loader);sys.modules[loader.name]=module;loader.loader.exec_module(module)
runner=module.GateRunner(root,1,'auto',out_dir=root/'tmp/N02-R01/final-g00-probe')
candidate=read('artifacts/handoffs/N02-R01/codex/candidate-audit.json')
assert runner.compute_revision()==candidate['code_revision']
assert runner.dirty_tree_hash()==candidate['dirty_tree_hash']
g00checks=[c.as_dict() for c in runner.check_previous_gates()]
assert len(g00checks)==1 and not g00checks[0]['passed']
now=datetime.now(timezone.utc)
time_context=read('artifacts/handoffs/N02-R01/codex/time-context.json')
client_zone=timezone(timedelta(seconds=time_context['offset_seconds']))
reviews=[
    dict(reviewer='Codex /root/n02_r01_jobs',isolation='fork_turns=none; inherited model without override',
         findings=dict(N02_F01='RESOLVED',N02_F04='RESOLVED'),
         facts=['JobRequest declared closure has 11 named types in 3 early modules; P05-03 has P02-04 ancestor',
                '45/45 independent job shape checks; five single-fault design mutations rejected'],
         limitation='ActorContext must be trusted; signature and authentication rules have no confirmed contradiction. Request context wiring requires G05 implementation verification.'),
    dict(reviewer='Codex /root/n02_r01_scenario_calendar',isolation='fork_turns=none; inherited model without override',
         findings=dict(N02_F02='FIELDS_AND_ISOLATION_RESOLVED; EntityKind direct closure BLOCKED',N02_F03='RESOLVED'),
         facts=['ScenarioSpec.event_specs -> ScenarioEventSpec.payload -> EventPayload variants -> EntityRef.kind -> EntityKind lacks complete normative enum members',
                'Calendar earliest unique owner P02-01 primitives; CalendarDTO P02-02 entities; dependencies and mapping documented'],
         limitation='Four additional semantic negatives are accepted by design example harness; these are evidence coverage limits, not demonstrated runtime defects.'),
    dict(reviewer='Codex /root/n02_r01_g00_scope',isolation='fork_turns=none; inherited model without override',
         findings=dict(G00='INVALID',N03='BLOCKED'),
         facts=['149 graph nodes, reverse edges, phase barriers and requirement references consistent',
                'P00 deliveries/reports exist; historical reports are not current acceptance',
                'Freeze generator hardcodes historical reviewer/version; do not overwrite real review metadata by replaying it'],
         limitation='No files written or official Gate signed by subreviewer')]
write('independent-reviews.json',dict(source='subreviewer messages received by this root; key probes independently rerun and captured here',
      principal_reviewer='Codex N02-R01 /root',reviews=reviews))
blocker=dict(id='N02-R01-F02-C01',parent_id='N02-F02',status='OPEN_BLOCKING_G00',owner='A contract governance',
      confirmed_fact='EntityKind is declared existing but its named normative source only references it; complete members/serialized values are absent',
      independent_judgment='Scenario event direct nested type closure is not frozen; G00 F7/P00-02 full Schema freeze is unmet',
      reference_chain=['ScenarioSpec.event_specs','ScenarioEventSpec.payload','EventPayload ten variants','payload.entity_ref','EntityRef.kind','EntityKind'],
      sources=[dict(path='contracts/changes/N01-R01-contract-decisions.json',line=226),
               dict(path='docs/architecture/DATA_CONTRACTS.md',line=7),
               dict(path='docs/architecture/DATA_CONTRACTS.md',line=128),
               dict(path='tools/ai_coding_plan/validate_plan.py',line=175),
               dict(path='tmp/N01-R01/verify_contracts.py',line=98)],
      reproduction=dict(command=['python','tmp/N02-R01/closure_probe.py'],log_path='artifacts/handoffs/N02-R01/codex/closure-probe.log',
                        machine_result='artifacts/handoffs/N02-R01/codex/closure-probe.json',
                        checker_errors=[],existing_enum_members_present=False),
      minimal_repair=['Decide EntityKind complete members/exact values and event EntityRef target mapping; keep P02-01 states owner and existing task order',
                      'Synchronize DATA_CONTRACTS, N01-R01 decision annex, type ownership audit and migration facts',
                      'Replace the example-only hardcoded enum with the normative decision; add positive/negative closure tests so an incomplete inherited enum cannot pass',
                      'Run affected design/plan checks for the new candidate, stop implementation writes, and submit independent N02 review'],
      bounded_paths=['docs/architecture/DATA_CONTRACTS.md','docs/architecture/TYPE_DEFINITION_OWNERSHIP.md',
                     'contracts/changes/N01-R01-contract-decisions.json','contracts/changes/N01-R01-contract-freeze-2.0.0.md',
                     'tools/ai_coding_plan/validate_plan.py','the A repair task own design examples/handoff/evidence/scratch'],
      scope_change_rule='Exact authorized repair paths must come from a subsequent bounded task card; this review authorizes no business code changes',
      already_resolved_do_not_reopen=['N02-F01 JobKind decisions','N02-F02 Scenario fields/version/hash/isolation/ownership',
                                    'N02-F03 Calendar early unique definition/dependencies/DTO mapping','N02-F04 JobRequest early named references'],
      recovery_condition='Normative closure independently verified, then byte archive old freeze/G00/logs, update true review facts and hashes, run --self-test --record-g00 and verify current runner prerequisites')
write('blocker.json',blocker)

# Store the actual reproduction sources in this task's durable evidence directory.
sources=out/'sources';sources.mkdir(exist_ok=True)
for p in sorted((root/'tmp/N02-R01').glob('*.py')):
    shutil.copyfile(p,sources/p.name)

audit=read('artifacts/handoffs/N02-R01/codex/audit-summary.json')
old=read('artifacts/handoffs/N02-R01/codex/old-freeze-g00-audit.json')
commands=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(out.glob('*-command.json'))]
handoff.parent.mkdir(parents=True,exist_ok=True)
report=f'''# N02-R01 独立复核 N01-R01

结论：**BLOCKED；G00 当前无效，N03 不可启动。** F01、F03、F04 已解决；F02 的字段、隔离与承载已解决，但直接嵌套 `EntityKind` 的完整成员及序列化值仍未冻结。本轮不重复退回已解决项，不以更新 hash 代替契约决定。

主审：`Codex N02-R01 /root`；实际根：`D:\\Agent\\DeepSeekHarness\\IntelligentLogisticsDispatchingAgent`；`.git` 不存在，使用内容哈希。审查时间：`{now.isoformat()}`（美国洛杉矶 `{now.astimezone(client_zone).isoformat()}`；当前偏移由 Windows TimeZoneInfo 实测）。三个独立只读子审计均使用 `fork_turns=none`、继承当前模型且未覆盖模型；主审复跑关键探针并裁定。模型、插件及全局配置未改。

计划 `1.0.3`，业务契约 `2.0.0`，证据格式 `1.0.0`。用户消息未给出完整候选值，本轮从 N01-R01 交接及机器证据提取并独立复算绑定：`{candidate['code_revision']}`；dirty-tree：`{candidate['dirty_tree_hash']}`。本轮停写前再次复算，两者未变。

## 已确认字节与结构证据

| 核验项 | 实测结果 |
| --- | --- |
| 候选 | 77/77 原字节、独立遍历集合、revision/dirty 两种公式与现行 runner 一致 |
| 治理差异 | 123 项前后 hash/字节与改前副本一致；原文本 diff 完全复现；均在 127 项白名单内 |
| 保护文件 | N01-R01 登记 3418/3418 未变；本轮前后非派生树逐项比较，冻结、G00/G01、旧日志和他人交接均未变 |
| N01-R01 证据 | 204/204 交接、输出、命令日志和绑定输入 hash 一致；包含历史失败日志 |
| 旧资产 | 173/173 登记文件 hash 一致，普通文件未登记项为空；派生依赖/缓存树不作业务证据 |
| 规划与交付 | 109 Task/40 Gate/149 节点 DAG、反向边与阶段屏障通过；18 组需求引用有效；P00 三任务 13 项白名单文件与报告必填章节齐全 |
| 旧冻结/G00 | 冻结 4/12 漂移；G00 输入 5/25 漂移；旧原始日志 hash 正确，前序依赖为合法空集合 |

详见 [字节审计](../../../artifacts/handoffs/N02-R01/codex/audit-summary.json)、[原字节差异](../../../artifacts/handoffs/N02-R01/codex/governance-diff.patch)、[最终范围核验](../../../artifacts/handoffs/N02-R01/codex/review-scope-final.json)、[旧冻结/G00核验](../../../artifacts/handoffs/N02-R01/codex/old-freeze-g00-audit.json)。P00 旧报告仅是历史实施记录；不把旧版本、旧计数或“无执行器”写成当前事实。

## 四项独立判定

| 原缺陷 | 本轮判定及依据 |
| --- | --- |
| N02-F01 | **RESOLVED**。五类 JobKind、三种优化 mode、kind/payload.family/ref.family 一致与非优化禁 mode 已明确；P02-01 states 唯一定义。DATA_CONTRACTS:122；独立形状正反例 45/45。 |
| N02-F02 | **PARTIALLY_RESOLVED / BLOCKED**。Ref/Spec/Input/Bundle 完整字段、版本/hash、期望旁文件隔离、P02-04 承载与合法依赖已解决。剩余仅 `EntityKind` 规范闭包缺口，见下文。 |
| N02-F03 | **RESOLVED**。CalendarInterval/ResourceCalendar 唯一归 P02-01 primitives；P02-02 资源/DTO复用，P03 窗口投影与源 hash 可复算；承载白名单/依赖成立。DATA_CONTRACTS:136–140。 |
| N02-F04 | **RESOLVED**。JobRequest 的 11 型、3 早期模块具名闭包成立，无未来 DTO；P05-03 祖先包含 P02-04。版本/hash/scope、404/409/422/501、缺真实能力不入队与终态/lease规则已明确。DATA_CONTRACTS:144–152、259–267。 |

ActorContext、Resource/DTO、JobFailure、早期配置及 HTTP/CLI 投影的相关字段/层边界已审查；未另确认实质规范冲突。JobService 现行参数不含 actor，但没有证据排除可信请求作用域注入，因此不新增阻断；其真实接线必须在 G05 验证。[子审查判定](../../../artifacts/handoffs/N02-R01/codex/independent-reviews.json)与[具名图/合法依赖及单点负例](../../../artifacts/handoffs/N02-R01/codex/design-graph-probe.json)保留具体范围。

## 唯一未满足条款与最小修复

责任方：**A 契约治理**；残余 `N02-R01-F02-C01` 属原 N02-F02 直接嵌套闭包，不是新增业务功能或泛治理范围。

引用链：`ScenarioSpec.event_specs → ScenarioEventSpec.payload → EventPayload` 十分支 `→ entity_ref:EntityRef → kind:EntityKind`。规范附表第 226 行把 EntityKind 标为 `existing`，指向 DATA_CONTRACTS 的“公共类型与状态”；该来源第 7 行只使用名称，第 183 行再指回同一来源，没有完整成员或精确序列化值。类型归属表第 24 行也没有补定义。实例脚本第 98 行写的 11 个字符串属于检查代码，未作为规范设计决定；不能以它们代替冻结。

未满足：[DATA_CONTRACTS:128](../../architecture/DATA_CONTRACTS.md#n01-r01-本轮完整契约决定) 要求事件及直接嵌套纯值闭合；IMPLEMENTATION_CONVENTIONS:13 要求直接引用类型先完整定义；P00-02 范围是全部实体/Schema/Protocol；PHASE_GATES:21 与 Gate 契约 F7 要求冻结断言成立。

实际复现：[closure-probe.log](../../../artifacts/handoffs/N02-R01/codex/closure-probe.log)及[机器结果](../../../artifacts/handoffs/N02-R01/codex/closure-probe.json)。当前 validate_plan 的 existing 分支（175–186）只核对来源/节/名称存在，结果 `errors=[]`，但没有验证该枚举成员或展开 EntityRef 的真实嵌套字段。静态通过不能消除此规范缺口。

最小修复：裁定 EntityKind 完整成员、精确值及各事件引用目标映射；保留 P02-01 states 归属和已有任务依赖；同步 DATA、规范附表、类型审计与迁移事实，并让设计正反例从规范取值、检查器拒绝未完整定义的该枚举。后续限定卡精确路径见[阻断说明](../../../artifacts/handoffs/N02-R01/codex/blocker.json)。不重做已解决的 Scenario/Calendar/Job 设计，不改业务实现、OWNERSHIP、执行器或锁。

## 本轮实跑命令

| 精确命令 | 真实退出码 / 结果 | 原始日志 |
| --- | --- | --- |
| `python tmp/N02-R01/audit.py` | 0；字节审计通过，非 Gate 签收 | [audit](../../../artifacts/handoffs/N02-R01/codex/audit.log) |
| `python tools/ai_coding_plan/validate_plan.py --self-test` | 0；43 自测试、109任务/40Gate、errors=[] | [plan-preflight](../../../artifacts/handoffs/N02-R01/codex/plan-preflight.log) |
| `python tmp/N02-R01/replay_contract_examples.py independent` | 0；实施者设计检查隔离重放 95/95，114生成输出字节复现 | [contract-replay-02](../../../artifacts/handoffs/N02-R01/codex/contract-replay-02.log) |
| `python tmp/N02-R01/job_shape_probe.py` | 0；独立形状/判别检查45/45 | [job-shape-probe](../../../artifacts/handoffs/N02-R01/codex/job-shape-probe.log) |
| `python tmp/N02-R01/design_graph_probe.py` | 0；依赖/承载/闭包审计与5个单点设计破坏拒绝 | [design-graph-probe](../../../artifacts/handoffs/N02-R01/codex/design-graph-probe.log) |
| `python tmp/N02-R01/closure_probe.py` | 0；成功复现规范缺口及实例覆盖限制，非 Gate 通过 | [closure-probe](../../../artifacts/handoffs/N02-R01/codex/closure-probe.log) |
| `python tmp/N02-R01/probe_g00.py` | **1**；现行 runner 只复核 G00 前置，拒绝5项输入漂移 | [g00-prerequisite](../../../artifacts/handoffs/N02-R01/codex/g00-prerequisite.log) |

各验收命令经 capture 包装，实际 argv/cwd/UTC/exit/log hash 在同名 `*-command.json` 和最终 evidence 中。初次生成隔离重放脚本因命令引号错误未生成文件，随后的重放启动实际 exit 2；[原失败日志](../../../artifacts/handoffs/N02-R01/codex/contract-replay.log)保留，修正本轮临时准备脚本后使用新文件名日志实跑成功，没有覆盖原失败证据。交付生成首次因本机缺 tzdata 退出1；改为使用 Windows TimeZoneInfo 实测本次日期的偏移，不安装依赖或修改配置。

未执行 `--record-g00`、未归档/更新旧冻结与官方 G00：独立冻结条件不成立，恢复步骤未获本任务条件授权。没有新 G00 可供签收；当前记录虽仍写历史 passed，runner 按 planner schema 校验其输入/日志/依赖后拒绝。没有签 G01，没有启动 N03/P02 或重启旧 P01-02 返工。

## 验证边界与停写

实施者95项检查是设计示例重放；独立追加探针发现 CalendarDTO重叠、空RegionRef、反向OnArc时刻、悬空仓库FK/缺日历绑定仍被实例检查接受。规范已要求拒绝这些输入，因此列为**示例覆盖限制**，不冒称业务代码缺陷或业务验收通过。真实类型/Schema在G02、数据库/worker/认证与解析器在对应Gate实跑；DB、OR-Tools、SimPy、模型、浏览器验收均 NOT_RUN，旧226 passed没有被用作本轮结论。

旧冻结生成器硬编码1.0.0/旧身份，重跑会覆盖真实复核元数据；本轮未运行它、不扩大代码修改范围。未来恢复必须先逐字节归档旧冻结/G00/原日志，记录真实身份/时间、计划1.0.3、契约2.0.0及实测哈希，保留历史观察，然后真实执行 `--self-test --record-g00` 并再用现行runner核验。不能复制旧reviewer或只改日期/hash。

最终交付为本文件及[机器证据](../../../artifacts/handoffs/N02-R01/codex/evidence.json)。下一责任方为 A 契约治理的限定修复任务；新候选独立复核且 G00 有效后，才允许 N03 刷新自身Phase01交接。G01有效前仍不进入P02。**本轮交付后停写。**
'''
handoff.write_text(report,encoding='utf-8')
inputs={p:sha(root/p) for p in [
    'AGENTS.md','AI-CODING-PLAN.md','docs/plan/TASK_MANIFEST.json','docs/plan/PHASE_GATES.md','OWNERSHIP.json',
    'docs/handoffs/N01-R01/codex.md','artifacts/handoffs/N01-R01/codex/evidence.json','docs/handoffs/N02/codex.md',
    'contracts/changes/N01-R01-contract-decisions.json','contracts/changes/N01-R01-contract-freeze-2.0.0.md',
    'artifacts/dispatch/2026-10-01/completion/messages/now/N02.md','artifacts/dispatch/2026-10-01/completion/messages/now/N03.md',
    'docs/architecture/CONTRACT_FREEZE.json','docs/architecture/CONTRACT_FREEZE.md','artifacts/gates/G00.json',
    'artifacts/gates/G00-checks.log','scripts/gates.py','tools/ai_coding_plan/validate_plan.py',
    'docs/architecture/DATA_CONTRACTS.md','docs/architecture/TYPE_DEFINITION_OWNERSHIP.md',
    'docs/architecture/IMPLEMENTATION_CONVENTIONS.md','docs/architecture/issues/README.md',
    'docs/architecture/BASELINE_INVENTORY.json','docs/plan/GATE_EXECUTION_CONTRACT.md',
    'docs/agent-toolchain/12-project-completion-dispatch.md']}
outputs=[dict(path=p.relative_to(root).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
         for p in sorted(out.rglob('*')) if p.is_file() and p.name!='evidence.json']
evidence=dict(schema_version='1.0.0',task_id='N02-R01',role='independent Codex reviewer',status='BLOCKED',
    reviewer='Codex N02-R01 /root',reviewed_at=now.isoformat(),client_timezone='America/Los_Angeles',
    reviewed_at_client=now.astimezone(client_zone).isoformat(),root=str(root),git_present=False,
    model='inherited current session model; no override',plan_version='1.0.3',business_contract_version='2.0.0',
    code_revision=candidate['code_revision'],dirty_tree_hash=candidate['dirty_tree_hash'],candidate_after_unchanged=True,
    verified_input_hashes=inputs,byte_audit=audit,commands=commands,
    findings=[dict(id='N02-F01',status='RESOLVED'),dict(id='N02-F02',status='PARTIALLY_RESOLVED_BLOCKED',remaining='N02-R01-F02-C01'),
              dict(id='N02-F03',status='RESOLVED'),dict(id='N02-F04',status='RESOLVED')],
    blocker='artifacts/handoffs/N02-R01/codex/blocker.json',
    g00=dict(valid=False,new_record_written=False,official_record_status='historical passed; rejected by current prerequisite validation',
             record_g00='NOT_RUN: unresolved direct type closure blocks document freeze',archive_and_freeze_update='NOT_RUN: conditional restoration requirements unmet',
             freeze_drift=[r for r in old['freeze_drift']],input_drift=[r for r in old['g00_input_drift']],
             log_hash_valid=True,dependency_evidence_hashes={},runner_checks=g00checks),
    g01=dict(signed=False),n03_dispatch_allowed=False,business_implementation_changed=False,
    scope_audit='artifacts/handoffs/N02-R01/codex/review-scope-final.json',
    handoff=dict(path=handoff.relative_to(root).as_posix(),sha256=sha(handoff)),outputs=outputs,
    output_file_count_excluding_evidence=len(outputs),
    limitations=['Design probes and static graph checks only; not domain/HTTP/worker/DB acceptance',
                 'Existing type leaves are not fully expanded by the registered checker; EntityKind gap independently reproduced',
                 'Four semantic negatives accepted by design harness are documented coverage limits, not runtime findings',
                 'Dependency/cache/.mimosa derived trees not comprehensively byte audited',
                 'No PostgreSQL/OR-Tools/SimPy/model/browser acceptance or new G00/G01 execution'],
    next_responsible_party='A contract governance bounded repair, then independent N02 re-review',stopped_after_delivery=True)
write('evidence.json',evidence)
print(json.dumps(dict(task='N02-R01',status='BLOCKED',G00_valid=False,N03_allowed=False,
     protected_unchanged=len(scope['protected']),non_derived_tree_unchanged=len(snapshot),
     evidence_outputs=len(outputs),handoff_sha256=sha(handoff),evidence_sha256=sha(out/'evidence.json')),ensure_ascii=False))
