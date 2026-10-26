"""Run existing sequential/deep solvers without publishing any plan."""
import argparse
import json
from pathlib import Path
from app.contracts.entities import PlanningSnapshot
from app.application.coordinator import coordinate
from app.evaluation.experiment import run_paired, paired_summary

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True)
    parser.add_argument('--budget-ms',type=int,default=1000)
    args=parser.parse_args()
    snap=PlanningSnapshot.model_validate_json(args.snapshot.read_text(encoding='utf-8'))
    def strategy(mode):
        def run(snapshot,seed,budget_ms):
            # Existing Routing API has no random_seed; record repetition IDs honestly.
            return coordinate(snapshot=snapshot,order_ids=tuple(o.order_id for o in snapshot.orders),
                              budget_ms=budget_ms,max_coordination_rounds=3 if mode=='deep' else 1,
                              coordination_mode=mode)
        return run
    rows=run_paired(snap,{m:strategy(m) for m in ('sequential','deep')},range(10),args.budget_ms,args.out_dir)
    summary=paired_summary(rows,'sequential','deep','transport_distance')
    summary['limitations']=['Seeds are paired repetition identifiers; current routing contract does not accept them.',
                           'Only sequential/deep existing solvers; not B0-B3 or LLM effectiveness acceptance.',
                           'End-to-end budget overrun is excluded from paired improvement estimates.']
    (args.out_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__': main()
