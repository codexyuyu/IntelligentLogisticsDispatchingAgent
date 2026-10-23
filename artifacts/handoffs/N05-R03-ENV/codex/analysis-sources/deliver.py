from __future__ import annotations
import shutil
from common import ROOT,TEMP,OUT,sha,j,dump,now

audit=j(OUT/'final-audit.json');initial=j(OUT/'initial-audit.json');review=j(ROOT/'artifacts/gates/G01-codex-review.json');gate=j(ROOT/'artifacts/gates/G01.json')
assert audit['official_G01_valid'] and audit['problems']==[]
assert sha(ROOT/'artifacts/gates/G01.json')==audit['G01_sha256']
assert sha(ROOT/'artifacts/gates/G01-codex-review.json')==audit['review_sha256']==initial['review_sha256']=='e64827a62caa4c497304c66d85df154ac6047e571b3c5947b97a2d7c93925efc'
for p,d in review['verified_input_hashes'].items():assert sha(ROOT/p)==d,p
for row in initial['candidate_rows']:assert sha(ROOT/row['path'])==row['sha256'] and (ROOT/row['path']).stat().st_size==row['bytes'],row['path']
prior=j(ROOT/'artifacts/handoffs/N05-R02-IMPACT/codex/seal.json')
for row in prior['files']:assert sha(ROOT/row['path'])==row['sha256'] and (ROOT/row['path']).stat().st_size==row['bytes'],row['path']
assert sha(ROOT/'artifacts/handoffs/N05-R02-IMPACT/codex/seal.json')==initial['previous_seal_sha256']
commands=[j(p) for p in sorted((OUT/'commands').glob('*-command.json'))]
assert len(commands)==4 and all(c['exit_code']==0 for c in commands)
for c in commands:assert sha(ROOT/c['log_path'])==c['log_sha256'],c['log_path']
for name in ('final.py','deliver.py','prepare-final.py'):
    src=TEMP/name;dst=OUT/'analysis-sources'/name;shutil.copyfile(src,dst);assert sha(src)==sha(dst)
created=now()
report=f'''# N05-R03-ENV：限定缓存环境恢复与正式 G01

结论：**N05-R03-ENV PASSED；官方G01已真实重新执行签收，当前有效。** 本新卡仅一次正式运行，exit0、26/26检查通过，最终40直接输入、184review闭包、12原日志及G00依赖复算无漂移；旧N05-R02-IMPACT失败事实和44封存文件均原字节保留。封存后停写。

独立主审 `{review['reviewer']}`，原 `/root/n05_independent`，未参与实现或增加子审查；模型/推理请求gpt-6.1-sol/xhigh，不冒称核验服务端路由。工作根 `D:\\Agent\\DeepSeekHarness\\IntelligentLogisticsDispatchingAgent`，无Git。本轮活跃脚本、UV/npm缓存、pytest及日志仅在 `C:\\Users\\30382\\AppData\\Local\\Temp\\IntelligentLogisticsDispatchingAgent-n05-r03-env`；审计源码只在本任务artifact归档，不从工程根执行。仅写授权本任务交接和G01及本次原日志，未改源码/测试/锁/契约/ACL/全局配置/所有权/15号policy/G00/他人交接/state，未干预另一工程。

缓存必要条件实际改变：旧失败源于本轮前序任务未预热npm缓存，首次真实下载ECONNRESET并超过900秒，不能据此改业务断言。本卡启动时从已停写前序独占目录只读复制uv和npm暖缓存到新卡唯一TEMP，再用npm自带cacache.get同时核对源/新副本：冻结锁内三tarball完整SHA512均相符，字节8749/899597/3123044；验证0网络请求、0缓存写。实际安装仍用原npm ci，未设置离线模式、删断言或改变超时。证据见 `environment/cache-verify.json` 与原日志。

候选：`{audit['code_revision']}`，82文件；完整dirty：`{audit['dirty_tree_hash']}`。使用现行runner真实auto全局算法，源码/相关输入未变，未传旧revision伪装。G00 `{audit['G00_sha256']}`、三个预验收123输入/29命令日志及44份旧封存复算一致。

现有影响review `{audit['review_sha256']}` 原字节复用，未重写日期/hash。原6新进程外部cwd `-I -B` 导入/纯度/显式失败探针和未变影响审查按真实适用范围复用，本轮不声称再跑6进程。层扫描仍读取同一10个活跃源码，包含marker/states/primitives/errors，完整相关源码/依赖继续绑定。原52受控返工探针、冻结新环境安装证据的复用限制保留。P02业务测试/当前报告/人工交接不作为Phase01通过证明；P02已封存evidence/seal仅因必需precheck的来源绑定保留，后继刷新须追加附件。

| 本轮实际验证 | 结果 |
| --- | --- |
| 正式原执行器 | 7条manifest必需命令全部真实exit0 |
| 三份Phase01套件 | 56/96/74 passed，合计226，无skip |
| 附加断言/记录 | 5断言、14记录检查通过，总26/26 |
| 当前分层 | 10模块、7层、domain4模块，违规0 |
| 签收后复算 | 官方40输入、review184输入、12原日志、依赖/argv/cwd/计数/断言/UTC及真实auto均一致 |
| 追加check-only | exit0，16官方文件原字节前后不变；签收来自正式运行 |

正式命令 `uv run python scripts/gates.py --phase 01 --revision auto`；真实UTC `{audit['official_run_command']['started_at']}` → `{audit['official_run_command']['finished_at']}`。交接UTC `{created}`。精确argv/cwd/退出码/原日志SHA见 `commands/*-command.json`。

- 新官方G01 SHA256：`{audit['G01_sha256']}`。
- 未变独立review SHA256：`{audit['review_sha256']}`。
- 本轮正式总原日志 SHA256：`{audit['official_run_command']['log_sha256']}`。
- 全部12官方原日志逐项SHA见 `final-audit.json`。
- 环境：Python {gate['environment_fingerprint']['python']}、{gate['environment_fingerprint']['os']}、{gate['environment_fingerprint']['uv']}、Node {gate['environment_fingerprint']['node']}、npm {gate['environment_fingerprint']['npm']}。

旧失败官方G01 `9f30bb45307721ecdb6d85259bac18230002d91d6dc5eabc61f55fd41337e35c`、review及12原日志共14文件，在任何覆盖前逐字节归档，路径/hash/bytes见 `archive-manifest.json`。旧任务仍明确BLOCKED、55passed/1failed与正式exit1，本轮通过不能覆盖该历史。没有将失败改写为226passed，也没有在旧卡重复必败流程；缓存条件改变且新卡明确授权后才执行这一新调用。

边界：本轮仅环境恢复和Phase01签收，未执行P02业务预验收、未签G02、未派P02/P02-02。数据库/求解/仿真/模型/浏览器及Node22/GitHub Actions未实跑；当前原生Gate导入cwd是工程根，前序独立外部cwd证据按未变源码复用。执行器的前序review递归缺口和global revision比较行为未改；G02-G39附加断言覆盖仍需另卡治理。相关源码/导入/新增层扫描输入/配置/契约变化仍需影响复核；仅无关未绑定元数据或全局revision变化不机械宣告历史阶段失效。

下一执行者：root核验封存、解除hold，再让DSH只追加P02-01本轮G01/review依赖附件，保留已绑定封存evidence/seal；随后独立ZCode验P02-01业务。本主审封存后停写。机器入口 `evidence.json`，最终 `seal.json`。无重置卡、购买或全局设置变更。
'''
doc=ROOT/'docs/handoffs/N05-R03-ENV/codex.md';doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text(report,encoding='utf-8')
evidence={'schema_version':'1.0.0','task_id':'N05-R03-ENV','phase_gate':'G01','status':'PASSED','generated_at':created,'root':str(ROOT),
          'reviewer':review['reviewer'],'code_revision':audit['code_revision'],'dirty_tree_hash':audit['dirty_tree_hash'],'candidate_file_count':82,
          'official_G01_valid':True,'official_G01_sha256':audit['G01_sha256'],'review_sha256':audit['review_sha256'],'review_reused_unchanged':True,
          'dependency_evidence_hashes':gate['dependency_evidence_hashes'],'final_audit':audit,'commands':commands,'cache_verification':initial['cache_verification'],
          'previous_seal_sha256':initial['previous_seal_sha256'],'old_failure_preserved':True,'limitations':review['limitations'],'findings':[],
          'implementation_edits':[],'precheck_edits':[],'dispatched_tasks':[],'P02_business_acceptance':False,'G02_signed':False,
          'report':{'path':doc.relative_to(ROOT).as_posix(),'sha256':sha(doc)}}
dump(OUT/'evidence.json',evidence)
sealed=[]
for p in [doc,*sorted(OUT.rglob('*'))]:
    if p.is_file() and p!=OUT/'seal.json':sealed.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
seal={'task_id':'N05-R03-ENV','status':'PASSED','created_at':now(),'official_G01_valid':True,'official_G01_sha256':audit['G01_sha256'],
      'review_sha256':audit['review_sha256'],'candidate_revision':audit['code_revision'],'file_count':len(sealed),'files':sealed}
dump(OUT/'seal.json',seal)
for row in sealed:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for p,d in review['verified_input_hashes'].items():assert sha(ROOT/p)==d,p
for row in prior['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
assert sha(ROOT/'artifacts/gates/G01.json')==audit['G01_sha256'] and sha(ROOT/'artifacts/gates/G01-codex-review.json')==audit['review_sha256']
print({'delivered':True,'status':'PASSED','official_G01_valid':True,'G01_sha256':audit['G01_sha256'],'review_sha256':audit['review_sha256'],
       'seal_sha256':sha(OUT/'seal.json'),'sealed_file_count':len(sealed),'report_sha256':sha(doc),'evidence_sha256':sha(OUT/'evidence.json'),
       'official_run_log_sha256':audit['official_run_command']['log_sha256'],'official_exit_code':0,'root_writes_stopped':True})
