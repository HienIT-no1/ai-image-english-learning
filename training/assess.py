"""Compare a completed candidate with the old model on the same validation set."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from download import ROOT
from prepare import LEGACY_IDS, save_json


def compare_reports(candidate: dict, baseline: dict, candidate_rows: list, baseline_rows: list) -> dict:
    for key in ['profile','split','imgsz','manifest_sha256','image_count']:
        if candidate.get(key) is None or candidate.get(key)!=baseline.get(key):
            raise ValueError(f'Cannot compare reports from different or unverified evaluation settings: {key}')
    candidate_by_id={row['lvis_category_id']:row for row in candidate_rows}
    baseline_by_id={row['lvis_category_id']:row for row in baseline_rows}
    shared=[cid for cid in sorted(set(LEGACY_IDS.values())) if cid in candidate_by_id and cid in baseline_by_id
            and candidate_by_id[cid]['AP50_95'] is not None and baseline_by_id[cid]['AP50_95'] is not None
            and baseline_by_id[cid].get('model_support') and candidate_by_id[cid].get('model_support')]
    if not shared:
        raise ValueError('No comparable legacy classes with ground truth')
    rows=[{'lvis_category_id':cid,'english':candidate_by_id[cid]['english'],
           'baseline_AP50_95':baseline_by_id[cid]['AP50_95'],
           'candidate_AP50_95':candidate_by_id[cid]['AP50_95'],
           'gain':candidate_by_id[cid]['AP50_95']-baseline_by_id[cid]['AP50_95']} for cid in shared]
    old_mean=sum(row['baseline_AP50_95'] for row in rows)/len(rows)
    new_mean=sum(row['candidate_AP50_95'] for row in rows)/len(rows)
    evidence=[r for r in candidate_rows if r['AP50_95'] is not None]
    new_rows=[r for r in evidence if r['lvis_category_id'] not in set(LEGACY_IDS.values())]
    return {'state':'assessed','assessed_utc':datetime.now(timezone.utc).isoformat(),
        'shared_class_count':len(shared),'baseline_shared_AP50_95':old_mean,
        'candidate_shared_AP50_95':new_mean,'shared_AP_gain':new_mean-old_mean,
        'improved_on_shared_validation':new_mean>old_mean,
        'per_shared_class':rows,
        'candidate_target_classes':candidate['target_classes'],
        'classes_with_evaluation_ground_truth':len(evidence),
        'classes_without_evaluation_ground_truth':len(candidate_rows)-len(evidence),
        'new_classes_with_positive_AP':sum(r['AP50_95']>0 for r in new_rows),
        'new_classes_with_AP_at_least_0_10':sum(r['AP50_95']>=.10 for r in new_rows),
        'note':'AP>=0.10 is a descriptive count, not an acceptance threshold. A gain on old classes does not prove reliable recognition of all 1000 classes.',
        'weakest_new_classes':sorted(new_rows,key=lambda r:r['AP50_95'])[:50]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True,help='Candidate run name under training/runs')
    parser.add_argument('--profile',choices=['pilot','full'],default='full')
    args=parser.parse_args()
    if Path(args.name).name!=args.name or args.name in ('.','..'):
        parser.error('Use a run name, not a path')
    candidate_dir=ROOT/'reports'/(args.name+'-val')
    baseline_dir=ROOT/'reports'/('baseline-old-'+args.profile+'-val')
    model=ROOT/'runs'/args.name/'weights/best.pt'
    for directory,checkpoint in [(candidate_dir,model),(baseline_dir,ROOT.parent/'backend/weights/best.pt')]:
        if not (directory/'summary.json').exists() or not (directory/'per_class.json').exists():
            subprocess.run([sys.executable,'-u',str(ROOT/'evaluate.py'),'--model',str(checkpoint),
                '--profile',args.profile,'--split','val','--imgsz','416' if args.profile=='pilot' else '640',
                '--name',directory.name],cwd=ROOT.parent,check=True)
    def read(path): return json.loads(path.read_text(encoding='utf-8'))
    result=compare_reports(read(candidate_dir/'summary.json'),read(baseline_dir/'summary.json'),
        read(candidate_dir/'per_class.json'),read(baseline_dir/'per_class.json'))
    result['candidate_model']=str(model)
    result['candidate_report']=str(candidate_dir)
    result['baseline_report']=str(baseline_dir)
    save_json(ROOT/'reports'/(args.name+'-assessment.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['per_shared_class','weakest_new_classes']},indent=2))


if __name__=='__main__':
    main()
