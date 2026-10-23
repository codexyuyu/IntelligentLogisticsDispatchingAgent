from __future__ import annotations
import shutil
from common import ROOT,TEMP,OUT,sha,j,dump,now,gate_module

g=gate_module();runner=g.GateRunner(ROOT,1,'auto');revision=runner.compute_revision();runner.revision=revision
audit=j(OUT/'initial-audit.json');probe=j(OUT/'independent-import-probe.json')
assert audit['passed'] and probe['passed'] and probe['case_count']==6
assert revision==audit['code_revision'] and runner.dirty_tree_hash()==audit['dirty_tree_hash']
verified=dict(audit['verified_input_hashes']);decisions=list(audit['input_decisions'])
for p,d in verified.items():assert sha(ROOT/p)==d,p
commands=[]
for name in ('initial-audit','independent-import-probe'):
    path=OUT/'commands'/(name+'-command.json');record=j(path)
    assert record['exit_code']==0 and sha(ROOT/record['log_path'])==record['log_sha256']
    commands.append(record)
    for p in (path,ROOT/record['log_path']):verified[p.relative_to(ROOT).as_posix()]=sha(p)
for p in (OUT/'initial-audit.json',OUT/'independent-import-probe.json'):verified[p.relative_to(ROOT).as_posix()]=sha(p)
# Immutable copies preserve the actual audit recipes; execution remains in system TEMP.
for name in ('common.py','audit.py','probe.py','review.py'):
    source=TEMP/name;dest=OUT/'analysis-sources'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(source,dest)
    assert sha(source)==sha(dest);verified[dest.relative_to(ROOT).as_posix()]=sha(dest)
for p in verified:
    assert not p.startswith('artifacts/dispatch/2026-10-04/orchestration/state')
    assert p not in ('artifacts/gates/G01.json','artifacts/gates/G01-codex-review.json')
for row in audit['layer_modules']:assert row['path'] in verified
assert all(c.passed for c in runner.check_previous_gates()+runner.check_zcode_precheck())
for p,d in verified.items():assert sha(ROOT/p)==d,p
review={'schema_version':'1.0.0','gate_id':'G01','phase':1,'status':'approved',
        'reviewer':'Codex N05-R02-IMPACT /root/n05_independent (original independent N05; no implementation edits)',
        'reviewed_at':now(),'root':str(ROOT),'code_revision':revision,'dirty_tree_hash':runner.dirty_tree_hash(),'candidate_file_count':82,
        'review_context':{'task_id':'N05-R02-IMPACT','independent':True,'model_requested':'gpt-6.1-sol','reasoning_effort_requested':'xhigh','implementation_edits':[]},
        'dependency_evidence_hashes':{'G00':audit['G00_sha256']},'verified_input_hashes':dict(sorted(verified.items())),
        'reviewed_tasks':['P01-01','P01-02','P01-03'],'commands':commands,'findings':[],
        'input_scope_decisions':decisions,
        'scope_policy':{
            'actual_source':'All 10 sources read by the full layer scanner retained as live inputs, including domain marker/states/primitives/errors; active source cannot be replaced by history.',
            'P02_business_inputs':'P02 business tests/current report/task doc/human handoff/business logs not adopted for Phase01 correctness. They remain observable in the real global candidate when applicable; no fabricated phase-specific revision is used.',
            'P02_sealed_provenance':'Current P02 evidence/seal retained only as transitive hashes already required by the independently passed P01-01 precheck. Their business assertions are not used to accept Phase01; future DSH dependency refresh must append a new attachment and preserve these bytes.',
            'marker_authorization':'Old P02 completion report verified against the prior review digest then archived byte-identically with the original marker exception prompt. Only immutable history proves past authorization.',
            'metadata':'No live state/heartbeat/future dependency attachment/P02 business log or ongoing raw log bound. Dispatched scope cards are immutable archived snapshots. Exact before/after keep/remove/add decisions recorded.',
            'future_impact':'Related source/import/layer/config/contract changes still require impact review. An unrelated unbound document or only changed global revision does not mechanically invalidate a historical stage; current check-only itself still compares global revision.'},
        'acceptance_review':{
            'current_impact':'Real auto candidate477a883d/82 and complete dirty recomputed. Marker, locked configuration and 79 old candidate files unchanged; states and two P02 business tests changed.',
            'independent_probe':'Six fresh -I -B processes in exclusive system TEMP outside cwd: six packages import to workspace src, all domain export permutations pass, pending names fail loudly, unknown name AttributeError, zero third-party loaded roots. AST independently confirms all domain imports are standard library or same package.',
            'preconditions':'G00 25 inputs and raw command verified; three independent prechecks123 inputs/29 command logs verified. Latest P01-01 M01 binds full dirty and immutable historical G01, avoiding active official record cycles.',
            'history':'Old G01 direct40 inputs are fresh; old review now has10 drifted inputs after latest ZCode metadata/report refresh (8 F01 implementation/provenance changes plus current precheck and ZCode handoff). The whole independent chain was therefore reviewed instead of trusting the predecessor reader omission.',
            'official_gate':'Approval precedes one actual uv run python scripts/gates.py --phase 01 --revision auto. Current official validity will be determined only by that run and its final source/input/log/dependency/assertion audit.'},
        'reused_not_rerun':{
            'P01-02_P01-03':'Unchanged independent prechecks36/33 inputs and their logs reused; formal runner still executes all7 Phase01 commands.',
            'controlled_rework_probes':'Original52 positive/negative probes use unchanged gates.py/check_architecture.py and exact unchanged probe/raw log; controlled logic unaffected by real states.py change.',
            'clean_install':'Original N05 fresh locked installation and external import proof reused for unchanged package metadata/locks. Current live-source import behavior independently re-executed; no new fresh installation claimed.'},
        'limitations':[
            'Phase01 only. P02 business acceptance NOT_RUN; old failed P02 precheck remains failed/history. No G02 or P02-02 action.',
            'No Git repository or GitHub Actions run; Node24 runtime is used, Node22 itself not executed.',
            'Original clean-install proof reused; existing workspace environment used for current isolated imports. Formal Gate executes uv sync --frozen and npm ci.',
            'Dedicated cache seeded by read-only copy of the previous exclusive N05 cache, isolated pytest root, and active helper/log files all within this card system TEMP. No ACL/global setting changes.',
            'Native Gate import probe runs with repository cwd; independent outside-cwd -I -B probe supplies the isolation check.',
            'Current runner predecessor reader does not recursively audit later review/precheck drift; this review explicitly audits the actual closure. Runner global candidate/check-only behavior is unchanged.',
            'Only G01 has registered additional assertions in the current runner; G02-G39 business assertion coverage needs a separately scoped governance task.'
        ]}
dump(ROOT/'artifacts/gates/G01-codex-review.json',review)
assert runner.check_codex_review().passed
assert runner.dirty_tree_hash()==audit['dirty_tree_hash']
print({'approved':True,'review_sha256':sha(ROOT/'artifacts/gates/G01-codex-review.json'),'review_inputs':len(verified),'retained_sources':10,'old_review_drift_count':10,'P02_business_acceptance':False})
