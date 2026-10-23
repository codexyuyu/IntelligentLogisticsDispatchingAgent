from pathlib import Path
temp=Path(__file__).resolve().parent
source=Path(r'C:\Users\30382\AppData\Local\Temp\IntelligentLogisticsDispatchingAgent-n05-r02-impact\final.py').read_text(encoding='utf-8')
source=source.replace("probe=j(OUT/'independent-import-probe.json')","probe=j(ROOT/'artifacts/handoffs/N05-R02-IMPACT/codex/independent-import-probe.json')")
source=source.replace("archive['file_count']==len(archive['files'])==19 and archive['old_official_file_count']==14","archive['file_count']==len(archive['files'])==14")
source=source.replace("'task_id':'N05-R02-IMPACT'","'task_id':'N05-R03-ENV'")
source=source.replace("'independent_fresh_import_processes':6","'reused_independent_import_processes':6")
source=source.replace("'archive_file_count':19","'archive_file_count':14")
source=source.replace("result={'task_id'","prior=j(ROOT/'artifacts/handoffs/N05-R02-IMPACT/codex/seal.json')\nfor row in prior['files']:require(sha(ROOT/row['path'])==row['sha256'],'prior44 sealed evidence drift '+row['path'])\nrequire(sha(ROOT/'artifacts/gates/G01-codex-review.json')==audit['review_sha256'],'reused review bytes changed')\nresult={'task_id'")
(temp/'final.py').write_text(source,encoding='utf-8')
print('Prepared independent final audit in this card system TEMP; no project file written')
