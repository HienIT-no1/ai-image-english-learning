"""Run preparation, training and validation as a resumable background job."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['pilot','full'],required=True)
    parser.add_argument('--name',required=True)
    parser.add_argument('--epochs',type=int)
    parser.add_argument('--after-job',type=Path,help='Before training, require this prerequisite job to complete')
    parser.add_argument('--from-stage',choices=['prepare','train','evaluate'],default='prepare')
    args=parser.parse_args()
    job=ROOT/'runs'/f'job-{args.name}'
    job.mkdir(parents=True,exist_ok=True)
    state={'pid':os.getpid(),'profile':args.profile,'name':args.name,
           'started_utc':datetime.now(timezone.utc).isoformat()}
    def persist(**changes):
        state.update(changes)
        state['updated_utc']=datetime.now(timezone.utc).isoformat()
        temporary=job/'status.json.part'
        temporary.write_text(json.dumps(state,indent=2),encoding='utf-8')
        temporary.replace(job/'status.json')
    commands=[('prepare',[sys.executable,'-u',str(ROOT/'prepare.py'),'--profile',args.profile,'--images']),
              ('train',[sys.executable,'-u',str(ROOT/'train.py'),'--profile',args.profile,'--name',args.name]),
              ('evaluate',[sys.executable,'-u',str(ROOT/'evaluate.py'),'--model',str(ROOT/'runs'/args.name/'weights/best.pt'),
                           '--profile',args.profile,'--split','val','--imgsz','416' if args.profile=='pilot' else '640',
                           '--name',args.name+'-val'])]
    if args.profile=='full':
        commands.append(('assess',[sys.executable,'-u',str(ROOT/'assess.py'),'--name',args.name,'--profile','full']))
    if args.epochs:
        commands[1][1].extend(['--epochs',str(args.epochs)])
    try:
        for stage,command in commands:
            if ['prepare','train','evaluate','assess'].index(stage)<['prepare','train','evaluate','assess'].index(args.from_stage):
                continue
            if stage=='train' and args.after_job:
                while True:
                    prerequisite=json.loads(args.after_job.read_text(encoding='utf-8'))
                    if prerequisite.get('state')=='completed':
                        break
                    if prerequisite.get('state') in ('failed','interrupted'):
                        persist(state='failed',stage='prerequisite',error='Pilot job failed; full training has not started')
                        raise SystemExit(1)
                    persist(state='waiting',stage='prerequisite',prerequisite=str(args.after_job))
                    time.sleep(10)
            persist(state='running',stage=stage,command=command)
            with (job/f'{stage}.log').open('a',encoding='utf-8') as log:
                child=subprocess.Popen(command,cwd=ROOT.parent,stdout=log,stderr=subprocess.STDOUT)
                persist(child_pid=child.pid)
                code=child.wait()
            if code:
                persist(state='failed',exit_code=code,log=str(job/f'{stage}.log'))
                raise SystemExit(code)
        persist(state='completed',stage='finished',child_pid=None,
                model=str(ROOT/'runs'/args.name/'weights/best.pt'),
                report=str(ROOT/'reports'/(args.name+'-val')/'summary.json'))
    except KeyboardInterrupt:
        if 'child' in locals() and child.poll() is None:
            child.terminate()
            child.wait()
        persist(state='interrupted')
        raise


if __name__=='__main__':
    main()
