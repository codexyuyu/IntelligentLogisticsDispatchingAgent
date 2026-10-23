"""Seal the bounded repair handoff. No source, freeze or gate mutations."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
root = Path.cwd().resolve()
assert root == Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve()
out = root / 'artifacts/handoffs/N01-R02/codex'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads((root / p).read_text(encoding='utf-8'))
scope = load('tmp/N01-R02/scope-before.json')
audit = load('artifacts/handoffs/N01-R02/codex/audit-summary.json')
candidate = load('artifacts/handoffs/N01-R02/codex/candidate-after.json')
change = load('artifacts/handoffs/N01-R02/codex/governance-diff.json')
annex = load('contracts/changes/N01-R01-contract-decisions.json')
types = {row['name']:row for row in annex['types']}
result = load('artifacts/handoffs/N01-R02/codex/examples/contract-validation-final01.json')
gate_state = load('artifacts/handoffs/N01-R02/codex/legacy-freeze-g00-state.json')
for row in candidate['files']:
    assert sha(root / row['path']) == row['sha256']
for source in ('deliver.py', 'seal_check.py'):
    target = out / 'reproduction' / source
    assert not target.exists()
    target.write_bytes((root / 'tmp/N01-R02' / source).read_bytes())

commands = []
descriptor_paths = sorted(list((out / 'validator').glob('*-command.json')) + list((out / 'examples').glob('*-command.json')) + [out / 'final-audit-command.json'])
for p in descriptor_paths:
    data = json.loads(p.read_text(encoding='utf-8'))
    log_path = data['log_path']
    log_hash = data.get('log_hash', data.get('log_sha256'))
    assert sha(root / log_path) == log_hash
    preserved_log = 'artifacts/handoffs/N01-R02/codex/validator/' + Path(log_path).name if log_path.startswith('tmp/N01-R02/validator/') else log_path
    assert sha(root / preserved_log) == log_hash
    current_matches = {q:(sha(root / q) == h) for q,h in data.get('inputs_sha256', data.get('verified_input_hashes',{})).items()}
    commands.append(dict(descriptor=p.relative_to(root).as_posix(), descriptor_sha256=sha(p), actual_argv=data['argv'], actual_cwd=data['cwd'], started_at=data['started_at'], finished_at=data['finished_at'], exit_code=data['exit_code'], original_log_path=log_path, durable_log_path=preserved_log, log_sha256=log_hash, recorded_inputs=data.get('inputs_sha256', data.get('verified_input_hashes',{})), current_input_matches=current_matches, historical=data['exit_code'] != 0 or p.name=='self-tests-01-command.json'))

enum_table = '| 成员名 | 精确序列化值 | 引用目标 | ID | revision |\n| --- | --- | --- | --- | --- |\n'
for name,value in types['EntityKind']['members'].items():
    target = annex['entity_ref_targets'][value]
    enum_table += f"| {name} | `{value}` | {target['type']} | {target['identity_field']} | {target['revision_field'] or '必须 null'} |\n"
id_expressions = {
    'traffic_disruption':'entity_ref.id 选中 snapshot.matrices 的一个 TravelMatrix.id；全部弧限定在该矩阵',
    'weather_change':'entity_ref.id = region_ref.region_id；内嵌显式节点集合',
    'warehouse_resource_unavailable':'entity_ref = resource_ref，kind/id/revision 全值相等；解析真实仓库或资源',
}
event_table = '| payload.kind | 合法 entity_ref.kind | 引用目标与 ID 一致性 | revision |\n| --- | --- | --- | --- |\n'
for event,rule in annex['event_entity_ref_mapping'].items():
    target = rule['target']
    meaning = id_expressions.get(event, f"entity_ref.id = {target['id_path']}；{target.get('type', '')}.id")
    revision = {'row_version_if_present':'给定时等于事实快照 row_version', 'matrix_version_required':'必填且等于矩阵 version', 'null_required':'必须 null'}[target['revision']]
    event_table += f"| {event} | {' / '.join(rule['allowed_kinds'])} | {meaning} | {revision} |\n"

tables = '# N01-R02 完整枚举与十类事件映射\n\n本轮新规范决定，待独立复核；表从当前规范附表读取。不是旧示例的11字符串，也不是业务Schema导出。\n\n' + enum_table + '\n' + event_table
tables += '\n交通采用一个既有矩阵及非空、唯一、非自环有向弧，节点属于该矩阵，新版本严格前进；跨矩阵拆事件。天气节点非空唯一且属于场景矩阵并集，同场景版本同region_id固定节点集合；受影响矩阵的版本全部前进，无受影响弧可保留为显式无作用输入。仓储两份引用完全一致，warehouse保持独立本体，不扩充Resource五分支；zone不增加calendar。完整规则以DATA_CONTRACTS及规范JSON为准。\n'
(out / 'enum-and-event-tables.md').write_text(tables, encoding='utf-8')
created = datetime.now(timezone.utc).isoformat()
base = '../../../artifacts/handoffs/N01-R02/codex/'
handoff = f'''# N01-R02 唯一阻断修复 · 待独立复核

结论：**READY_FOR_INDEPENDENT_REVIEW**。N02-R01-F02-C01 的完整枚举、十类事件引用映射、显式闭包及设计检查已完成；是否解阻由独立 Codex N02-R02 裁定。**G00 当前无效，N03 不可启动；P02未启动。** 本轮没有更新官方冻结/Gate，没有执行 `--record-g00`，没有签G01。

实施身份：`Codex N01-R02 /root`；交付时间UTC：`{created}`。实际工作根：`{root}`，`.git`不存在；沿用会话模型，三个子任务未覆盖模型。协作审读只辅助本轮实施，不替代下一轮独立复核。

计划 `1.0.3`，业务契约 `2.0.0`，Gate证据格式 `1.0.0`。2.0.0候选尚未被接受，本轮补齐其中未决规范，不宣称对已发布2.0.0兼容，也不改manifest版本。此前32实体及11辅助实体已经在领域目录，本轮地址空间决定不新增业务实体/字段/表/API。

输入候选：`{scope['input_revision']}`。

新候选：`{candidate['code_revision']}`。

新dirty-tree：`{candidate['dirty_tree_hash']}`。

两种公式各自复算；候选集合77项，独立整树遍历与现行runner一致，变动恰为5项。[逐文件新候选]({base}candidate-after.json)、[原候选]({base}candidate-before.json)、[精确差异及前后hash]({base}governance-diff.json)、[原文本diff]({base}governance-diff.patch)、[改前原字节]({base}before/docs/architecture/DATA_CONTRACTS.md)保留可复核输入。报告、日志、示例和tmp不混入候选身份。

## 完整枚举与引用目标

45项 = 领域目录32实体 + 11必需辅助实体 + TravelMatrix/RegionRef两个既有纯值目标。成员名和精确序列化值为本轮规范决定；旧脚本的11字符串没有被冻结为规范。zone/location保留既有资源边界标签；不接受warehouse_zone/storage_location别名或大小写变体。

{enum_table}
EntityKind仍由P02-01 `states.py`唯一定义；EntityRef仍由P02-01 `primitives.py`唯一定义，字段为 `kind:EntityKind; id:UUID; revision:NonNegativeInt?`。提供修订时按选定事实快照检查；null只声明身份，不宣称当前版本一致。RegionRef无实体行，revision必须null；矩阵事件修订必填。元数据中的未来目标名不构成早期模型导入，历史审计/冲突记录保留当时事实，不按不断变化的live行统一重验。

## 十类事件映射

{event_table}
交通：同事件绑定一个现有矩阵，arc_refs非空、唯一、无自环，两个端点属于该矩阵；反向有向弧仍不同。跨矩阵拆事件，new_matrix_version严格大于旧version；ArcRef字段未改。

天气：内嵌节点集合非空唯一，节点属于场景矩阵并集；同场景版本同region_id绑定同集合，乱序不改变集合。影响每个矩阵中两个端点均在集合内的弧，新版本严格大于全部受影响矩阵版本；无受影响弧可作为明确无作用输入保留，不能虚构新弧或Region表。

仓储：两份引用kind/id/revision全值相等，限定Warehouse及五资源，解析同scope真实对象；warehouse不加入Resource五分支，zone不补calendar。既有TimeWindow闭窗与占用半开区间语义未改。

完整规则：[DATA_CONTRACTS](../../architecture/DATA_CONTRACTS.md)、[类型归属](../../architecture/TYPE_DEFINITION_OWNERSHIP.md)、[规范JSON](../../../contracts/changes/N01-R01-contract-decisions.json)、[本轮迁移追加](../../../contracts/changes/N01-R01-contract-freeze-2.0.0.md)。可独立读取的全表也在[枚举与映射]({base}enum-and-event-tables.md)。

## 实跑与范围核验

| 检查 | 实测结果 | 原始证据 |
| --- | --- | --- |
| `python -B tools/ai_coding_plan/validate_plan.py --self-test` | exit0；73项、109Task/40Gate、errors=[] | [最终日志]({base}validator/plan-validation-02.log)、[真实argv/cwd/UTC/输入hash]({base}validator/plan-validation-02-command.json) |
| `python tmp/N01-R02/examples/verify_design_examples.py final01`（由capture启动） | exit0；268/268 = 原95 + 新173，正例81/反例92；114生成输出隔离字节复现 | [日志]({base}examples/contract-check-final01.log)、[命令]({base}examples/contract-check-final01-command.json)、[逐项结果]({base}examples/contract-validation-final01.json)、[实例]({base}examples/contract-examples-final01.json) |
| `python -B tmp/N01-R02/audit_final.py`（由capture启动） | exit0；77候选、5差异、3786保护；原43测试AST和record_g00的AST/原bytes未变 | [日志]({base}final-audit.log)、[摘要]({base}audit-summary.json)、[保护核验]({base}protected-file-audit.json) |

规划负例包括EntityKind退回existing、定义缺失、成员遗漏、重复序列化值/JSON成员、EntityRef字段/归属漂移、映射缺项/错kind/错目标/不可解析或非UUID的ID路径。设计正反例从当前规范读取枚举与映射，涵盖45个值、十事件合法引用、未知值、错误目标、ID/修订不一致、缺目标，以及交通多弧、天气区域和全部六个仓储kind。它们验证设计谓词，不是已交付业务handler。

首次完整规划检查实际exit1：EntityRef显式字段暴露了遗漏的 `primitives → states` 单向模块边。已补此同P02-01边并使用新输入重新实跑；任务祖先/顺序和其他模块边未改。[原失败日志]({base}validator/plan-validation-01.log)与[原输入hash]({base}validator/plan-validation-01-command.json)保留；没有把旧输入的通过结论迁给新输入。前期71项局部自测试日志只作历史记录，最终73项才绑定新候选。

最终日志sha256：规划 `2e8da1ef32acbe18bb8aac40f8f907fa54debea4108faac70b57b2d409151fff`；设计 `da533b48ca41f9003d107e48f8eaa60f53d035e4cce5dddfe90db8cfcd9a60e2`。当前输入逐项匹配。原43项断言未删改，增加30项；record_g00函数原字节sha256 `6726a1f866e9f345ac6ea3feeba4d924bad6e1381ace601e9fbeb5c5632b88a9`保持一致。[AST保护证据]({base}validator/ast-protection-final.json)。

保护3786项全部未变，范围外新增/删除为空。5个既有文件均在用户白名单内；196个类型未增减，EntityKind/EntityRef显式化、十payload仅追加引用规则，其他类型全部字节结构一致，JobKind、Scenario字段/隔离、Calendar、JobRequest未重做。业务实现、OWNERSHIP、锁、manifest、原Prompt、他人交接、历史示例、冻结JSON/MD和G00/G01及旧日志均未改。新增只在本轮三个授权目录。

## 迁移影响、验证边界与后续

新候选使受影响旧审查/契约证据失效；未来domain → DTO → ports → 消费者 → 测试 → 生成物按原阶段实施。旧事件不能根据旧11字符串猜目标、ID或修订；转换需要可信事实映射，保留原字节/hash/版本和转换记录，无法映射则拒绝。影响G00/G01候选输入、G02类型/Schema、G04场景、事件/审计引用消费者及依赖后继；本轮不刷新这些任务的旧证据。

当前G00原记录虽写历史passed，现行runner `previous_gate_record_problems('G00', record)`仍拒绝5项输入漂移；旧冻结12项中4项漂移，原日志及依赖校验没有被绕过。[只读旧冻结/G00核验]({base}legacy-freeze-g00-state.json)。不以本轮设计通过推断G00恢复。

设计脚本使用UUID5合成身份及固定事实快照。继承适配器的CalendarDTO重叠、单独RegionRef空节点、OnArc时序、全场景FK/日历完整性覆盖限制仍在；CargoType夹具明确未验证，不能把场景示例称为完整业务合法Schema。新增区域谓词仅保证本轮事件映射所需约束。数据库、真实parser/handler/worker、OR-Tools、SimPy、模型、浏览器验收均NOT_RUN。[示例范围说明]({base}examples/subtask-note.md)。没有新增独立demo。

下一执行者：**独立 Codex N02-R02**，复算此新候选、5项差异、保护文件与日志，裁定唯一修复；通过后才归档原冻结/G00/原日志、更新真实审查事实与哈希，实跑 `--self-test --record-g00`，再以现行runner核验新G00输入/日志/依赖。G00有效才可启动N03，G01有效才进入P02。

交付：[机器证据]({base}evidence.json)。完成封存核验后停写，不自行执行下一轮。
'''
handoff_path = root / 'docs/handoffs/N01-R02/codex.md'
assert not handoff_path.exists()
handoff_path.parent.mkdir(parents=True, exist_ok=True)
handoff_path.write_text(handoff, encoding='utf-8')

inputs = dict(scope['before'])
inputs = {p:sha(root / p) for p in scope['whitelist']}
for p in ('AGENTS.md','AI-CODING-PLAN.md','OWNERSHIP.json','docs/plan/TASK_MANIFEST.json','docs/plan/PHASE_GATES.md','docs/architecture/DOMAIN_CATALOG.md','scripts/gates.py','docs/handoffs/N02-R01/codex.md','artifacts/handoffs/N02-R01/codex/blocker.json','artifacts/handoffs/N02-R01/codex/closure-probe.json','docs/handoffs/N01-R01/codex.md','artifacts/handoffs/N01-R01/codex/evidence.json','docs/architecture/CONTRACT_FREEZE.json','docs/architecture/CONTRACT_FREEZE.md','artifacts/gates/G00.json','tmp/N01-R02/scope-before.json','tmp/N01-R02/audit_final.py','tmp/N01-R02/deliver.py','tmp/N01-R02/seal_check.py'):
    inputs[p] = sha(root / p)
outputs = []
for p in sorted(out.rglob('*')):
    if p.is_file() and p.name not in ('evidence.json', 'delivery-seal.log', 'delivery-seal-command.json'):
        outputs.append(dict(path=p.relative_to(root).as_posix(), sha256=sha(p), bytes=p.stat().st_size))
outputs.append(dict(path=handoff_path.relative_to(root).as_posix(), sha256=sha(handoff_path), bytes=handoff_path.stat().st_size))
evidence = dict(schema_version='N01-R02-handoff-1', task_id='N01-R02', status='READY_FOR_INDEPENDENT_REVIEW', author='Codex N01-R02 /root', sealed_at=created, root=str(root), git_present=False, model_override=None, versions=dict(plan='1.0.3', business_contract='2.0.0', official_gate_evidence='1.0.0'), addressed_finding='N02-R01-F02-C01', implementation_complete=True, independent_review='NOT_RUN; next N02-R02', code_revision=candidate['code_revision'], dirty_tree_hash=candidate['dirty_tree_hash'], previous_code_revision=scope['input_revision'], candidate_manifest_path='artifacts/handoffs/N01-R02/codex/candidate-after.json', changed_existing_files=change['changes'], protected_file_count=3786, protected_changes=[], input_artifact_hashes=inputs, commands=commands, validations=dict(planning_self_tests=73, original_tests_unchanged=43, design_checks=268, inherited_design_checks=95, new_design_checks=173, new_positive=81, new_negative=92, generated_outputs_reproduced=114, explicit_enum_members=45, event_mappings=10, type_count=196, final_bound_commands_exit_zero=True, record_g00_unchanged=True), G00_valid=False, N03_may_start=False, P02_started=False, official_records_written=[], record_g00_run=False, next_executor='Independent Codex N02-R02', migration='Complete the unaccepted 2.0.0 candidate; no release compatibility or guessed legacy conversion claim; invalidate affected earlier evidence', limitations=result['limitations'], output_manifest=outputs, output_count=len(outputs), manifest_exclusions=['evidence.json (self)', 'delivery-seal.log (post-seal verification)', 'delivery-seal-command.json (post-seal verification)'])
assert not (out / 'evidence.json').exists()
(out / 'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(status=evidence['status'], handoff=str(handoff_path), evidence_sha256=sha(out/'evidence.json'), output_count=len(outputs), code_revision=evidence['code_revision']), ensure_ascii=False))
