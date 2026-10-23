from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
from common import ROOT,TEMP,OUT,sha,j,dump,now,gate_module

g=gate_module();runner=g.GateRunner(ROOT,1,'auto');rows=runner.relevant_manifest_rows();revision=runner.compute_revision();runner.revision=revision
gate=j(ROOT/'artifacts/gates/G01.json');review=j(ROOT/'artifacts/gates/G01-codex-review.json');audit=j(OUT/'initial-audit.json');run=j(OUT/'commands/official-g01-command.json')
assert gate['status']=='failed' and run['exit_code']!=0 and gate['failed_checks'], 'this handler only seals an actual failed run'
assert revision==gate['code_revision']==review['code_revision']==audit['code_revision'] and runner.dirty_tree_hash()==audit['dirty_tree_hash'] and len(rows)==82
assert sha(ROOT/run['log_path'])==run['log_sha256']
for p,d in gate['input_artifact_hashes'].items():assert sha(ROOT/p)==d,p
for p,d in review['verified_input_hashes'].items():assert sha(ROOT/p)==d,p
assert gate['dependency_evidence_hashes']=={'G00':audit['G00_sha256']} and sha(ROOT/'artifacts/gates/G00.json')==audit['G00_sha256']
assert all(c.passed for c in runner.check_previous_gates()+runner.check_phase_handoffs())
expected=[g.normalize_argv(g.split_command(c)) for t in runner.phase_tasks() for c in t['commands']]
assert len(expected)==len(gate['commands'])==7
actual_commands=[]
for index,(c,wanted) in enumerate(zip(gate['commands'],expected)):
    assert [Path(c['argv'][0]).stem.lower(),*c['argv'][1:]]==[Path(wanted[0]).stem.lower(),*wanted[1:]],c['check_id']
    assert Path(c['cwd']).resolve()==ROOT and sha(ROOT/c['log_path'])==c['log_sha256']
    raw=(ROOT/c['log_path']).read_text(encoding='utf-8');counts=g.parse_pytest_counts(raw)
    assert f"## exit_code: {c['exit_code']}" in raw
    if g.looks_like_pytest(c['argv']):assert counts==c['test_counts']
    actual_commands.append({'check_id':c['check_id'],'exit_code':c['exit_code'],'test_counts':counts,'log_path':c['log_path'],'log_sha256':c['log_sha256']})
first=(ROOT/gate['commands'][0]['log_path']).read_text(encoding='utf-8')
assert 'subprocess.TimeoutExpired' in first and 'timed out after 900 seconds' in first and 'npm.cmd' in first
assert gate['commands'][0]['exit_code']==1 and gate['commands'][0]['test_counts']=={'failed':1,'passed':55}
assert gate['failed_checks']==['P01-01-cmd1'],gate['failed_checks']
assert all(c['exit_code']==0 for c in gate['commands'][1:])
assert all(a['passed'] for a in gate['acceptance_assertions']) and len(gate['acceptance_assertions'])==5
assert len(gate['record_checks'])==14 and all(c['passed'] for c in gate['record_checks'])
archive=j(OUT/'archive-manifest.json')
for row in archive['files']:assert sha(ROOT/row['archive_path'])==row['sha256'] and (ROOT/row['archive_path']).stat().st_size==row['bytes']
logs={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'artifacts/gates/G01-logs').glob('*.log'))};assert len(logs)==12
warm=j(TEMP/'npm-cache-warm.json');assert warm['passed'] and len(warm['packages'])==3 and warm['network_requests']==0
environment=[]
for src in [TEMP/'npm-cache-warm.json',TEMP/'npm-cache-warm.log',TEMP/'process-tree-before-cleanup.json',*sorted((TEMP/'npm-cache/_logs').glob('*.log'))]:
    dst=OUT/'environment'/src.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(src,dst);assert sha(src)==sha(dst)
    environment.append({'path':dst.relative_to(ROOT).as_posix(),'sha256':sha(dst),'bytes':dst.stat().st_size})
for name in ('warm-npm.cjs','failure.py'):
    src=TEMP/name;dst=OUT/'analysis-sources'/name;shutil.copyfile(src,dst);assert sha(src)==sha(dst)
result={'task_id':'N05-R02-IMPACT','status':'BLOCKED','official_G01_valid':False,'official_G01_status':'failed','audited_at':now(),
        'code_revision':revision,'dirty_tree_hash':runner.dirty_tree_hash(),'candidate_file_count':82,'G01_sha256':sha(ROOT/'artifacts/gates/G01.json'),
        'review_sha256':sha(ROOT/'artifacts/gates/G01-codex-review.json'),'G00_sha256':audit['G00_sha256'],'official_input_count':len(gate['input_artifact_hashes']),
        'review_input_count':len(review['verified_input_hashes']),'bound_hashes_fresh':True,'failed_checks':gate['failed_checks'],
        'commands':actual_commands,'required_commands_executed':7,'passed_assertions':5,'passed_record_checks':14,'total_checks_passed':25,'total_checks':26,
        'official_raw_log_hashes':logs,'official_run_command':run,'archive_file_count':19,'old_official_archived_count':14,
        'environment_proof':environment,'cache_warm':warm,'new_Gate_run_count':1,'killed_processes':[],
        'earliest_blocker':{'id':'N05-R02-ENV-NPM-01','owner':'N05 environment preparation / subsequent scoped N05 recovery',
                            'trigger':'first real npm ci --no-audit --no-fund in P01-01 integration suite, dedicated initially empty npm cache; registry ECONNRESET then 900-second TimeoutExpired',
                            'classification':'confirmed external download/cache preparation timeout; no claim of a business-source defect',
                            'recovery_conditions':'exclusive task npm cache now contains all three lock-integrity-verified tarballs; subsequent required npm ci in this same run actually exited0 in about6.6s. Root may authorize one new recovery task after rechecking necessary conditions; no rerun of this card.'},
        'P02_business_acceptance':False,'G02_signed':False}
dump(OUT/'final-audit.json',result)
doc=ROOT/'docs/handoffs/N05-R02-IMPACT/codex.md';doc.parent.mkdir(parents=True,exist_ok=True)
report=f'''# N05-R02-IMPACT：实际 G01 失败封存

结论：**N05-R02-IMPACT BLOCKED；官方 G01 本次真实执行 failed，当前不得作为有效前置。** 一次正式调用实际exit `{run['exit_code']}`，25/26检查通过；唯一失败 `{gate['failed_checks'][0]}`。7必需命令全部由现行执行器执行，正确性断言、测试、锁、源码均未改变；未重跑本卡，未冒签成功，未签G02或开始P02-02。封存后停写。

最小阻塞 `N05-R02-ENV-NPM-01`：P01-01集成测试 `test_npm_ci_is_repeatable_and_lock_file_is_unchanged` 首轮 npm ci 使用本卡新空npm缓存，真实registry下载发生ECONNRESET，最终 `subprocess.TimeoutExpired`（900秒）；套件55passed/1failed，exit1。命令实际耗时约1027秒，原日志见 `artifacts/gates/G01-logs/P01-01-cmd1.log`。这是已确认的外部下载/缓存准备问题；当前没有证据据此认定业务源码缺陷。`.pytest_cache`拒绝访问只产生两个警告，不是此失败的根因。

环境准备遗漏：本轮只预先复制了旧N05独占uv缓存，没有预先复制已验证npm缓存。下载等待中在原900秒边界之后，按冻结package-lock的SHA512验证三包，使用npm自带cacache原子API补到本卡系统TEMP缓存；0额外网络请求，无全局配置、ACL或源码变更。没有改变正式Gate参数、重启命令或修改失败结果。随后正式P01-01-cmd3真实npm ci exit0（约6.6秒），说明必要缓存条件已发生变化；首轮失败仍原样保留。仅只读查询本任务进程树，没有结束任何进程，也未干预另一Android工程。

本轮独立影响审查及输入闭包已实证完成：真实auto候选 `{revision}`，82文件；完整dirty `{result['dirty_tree_hash']}`。当前G00、三份预验收123输入/29命令日志及原Phase01交付有效；最新M01已改绑不可变历史G01。6个外部cwd `-I -B` 新进程通过六包/领域导出顺序/零第三方/未交付入口显式失败。新review184项保留全部10个活跃层源码和必需传递依赖，逐项说明旧262输入保留/移出；P02业务测试/当前文档/人工交接/业务日志未被用作bootstrap正确性证明。P02 evidence/seal仅因必需precheck的封存来源绑定保留，后继依赖刷新只能追加附件。原52项受控返工探针及冻结新环境安装证据仅按未变主体明确复用。

本次其它真实结果：P01-02套件96passed、P01-03套件74passed；剩余6必需命令全部exit0，5附加断言/14记录检查通过。正式阶段测试合计225passed/1failed，不能写226passed。官方40输入、review184输入、12原日志、G00依赖复算无漂移；新review为独立源码/证据影响approval，并不覆盖随后失败的必需命令及F4签收条件，不能把approved当G01通过。

- 官方失败G01 SHA256：`{result['G01_sha256']}`。
- 独立review SHA256：`{result['review_sha256']}`。
- 正式实际运行原日志 SHA256：`{run['log_sha256']}`；UTC `{run['started_at']}` → `{run['finished_at']}`，exit `{run['exit_code']}`。
- G00 SHA256：`{result['G00_sha256']}`，未改。
- 旧官方G01/review/12日志共14文件及历史marker授权/精确路由5文件，共19文件，覆盖前逐字节归档；路径/hash/bytes见 `archive-manifest.json`。
- 机器审计、全部命令计数、12原日志SHA和环境处置原始来源见 `final-audit.json` / `commands` / `environment`；封存见 `seal.json`。

工作根 `D:\\Agent\\DeepSeekHarness\\IntelligentLogisticsDispatchingAgent`，无Git；独立原N05身份，模型/推理请求gpt-6.1-sol/xhigh，未参与实现、未加子审查。活跃脚本/UV/npm缓存/pytest/日志仅在本卡系统TEMP。未修改实现/测试/契约/锁/所有权/policy/G00/他人交接/state，无重置或购买。

恢复责任：root核验封存后，若专属npm缓存完整性与实际安装必要条件仍成立，再明确安排新的限定N05环境恢复任务；保留本次失败原字节，沿用同一正确性测试/冻结锁，再执行新的正式Gate。未授权本卡第二次实跑，不继续P02链。

限制：仅Phase01源码/导入/分层影响审查，未执行P02业务预验收；当前无有效G01，不授权下游。Node22/GitHub Actions及数据库/求解/仿真/模型/浏览器未实跑。执行器predecessor递归review缺口和global revision比较行为未改；后续相关源码/导入/层扫描输入变化仍需影响复核，无关未绑定元数据不机械使历史阶段失效。当前只有G01附加断言注册，后续阶段需另卡覆盖治理。
'''
doc.write_text(report,encoding='utf-8')
dump(OUT/'evidence.json',{'schema_version':'1.0.0','task_id':'N05-R02-IMPACT','phase_gate':'G01','status':'BLOCKED','generated_at':now(),'root':str(ROOT),
          'reviewer':review['reviewer'],'code_revision':revision,'dirty_tree_hash':result['dirty_tree_hash'],'candidate_file_count':82,
          'official_G01_valid':False,'official_G01_status':'failed','official_G01_sha256':result['G01_sha256'],'review_sha256':result['review_sha256'],
          'final_audit':result,'findings':[result['earliest_blocker']],'implementation_edits':[],'precheck_edits':[],'dispatched_tasks':[],
          'report':{'path':doc.relative_to(ROOT).as_posix(),'sha256':sha(doc)}})
sealed=[]
for p in [doc,*sorted(OUT.rglob('*'))]:
    if p.is_file() and p!=OUT/'seal.json':sealed.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
seal={'task_id':'N05-R02-IMPACT','status':'BLOCKED','created_at':now(),'official_G01_valid':False,'official_G01_status':'failed',
      'official_G01_sha256':result['G01_sha256'],'review_sha256':result['review_sha256'],'candidate_revision':revision,'file_count':len(sealed),'files':sealed}
dump(OUT/'seal.json',seal)
for row in sealed:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for p,d in review['verified_input_hashes'].items():assert sha(ROOT/p)==d,p
assert sha(ROOT/'artifacts/gates/G01.json')==result['G01_sha256']
print({'delivered':True,'status':'BLOCKED','official_G01_valid':False,'official_G01_status':'failed','official_exit_code':run['exit_code'],
       'G01_sha256':result['G01_sha256'],'review_sha256':result['review_sha256'],'seal_sha256':sha(OUT/'seal.json'),'sealed_file_count':len(sealed),
       'official_run_log_sha256':run['log_sha256'],'report_sha256':sha(doc),'evidence_sha256':sha(OUT/'evidence.json'),'root_writes_stopped':True})
