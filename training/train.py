"""Train a candidate model separately from the application's deployed weights."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def validate_dataset(root: Path) -> dict:
    manifest=root/'manifest.json'
    expected=hashlib.sha256(manifest.read_bytes()).hexdigest()
    if not (root/'READY').is_file() or (root/'READY').read_text(encoding='utf-8')!=expected:
        raise RuntimeError('Dataset is not verified; run prepare.py --images first')
    audit=json.loads((root/'download_audit.json').read_text(encoding='utf-8'))
    if audit['failures']:
        raise RuntimeError('Dataset has unresolved failed/duplicate images')
    coverage=json.loads((root/'coverage.json').read_text(encoding='utf-8'))
    if any(row['train_boxes']==0 for row in coverage['per_class']):
        raise RuntimeError('Some selected labels have zero train support')
    return json.loads(manifest.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['pilot','full'],default='pilot')
    parser.add_argument('--epochs',type=int)
    parser.add_argument('--imgsz',type=int)
    parser.add_argument('--batch',type=int)
    parser.add_argument('--workers',type=int)
    parser.add_argument('--name',default=None)
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--weights',type=Path,help='Initialize a new run from a previous trusted local candidate checkpoint')
    args=parser.parse_args()
    import torch
    from ultralytics import YOLO
    from verified_training import VerifiedTrainer
    if importlib.metadata.version('ultralytics')!='8.4.188':
        raise RuntimeError('This verified-label trainer is tested with ultralytics==8.4.188')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable. Use training/.venv with CUDA PyTorch; never fall back to CPU silently.')
    root=ROOT/'data/prepared'/args.profile
    manifest=validate_dataset(root)
    ROOT.joinpath('weights').mkdir(exist_ok=True)
    if args.resume and args.weights:
        parser.error('--resume and --weights are mutually exclusive')
    initial=args.weights.resolve() if args.weights else ROOT/'weights/yolo11n.pt'
    if args.weights and not initial.is_file():
        raise FileNotFoundError(initial)
    if not initial.exists():
        backend=ROOT.parent/'backend/weights/yolo11n.pt'
        if backend.exists():
            shutil.copy2(backend,initial)
        else:
            from download import download
            download('https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt',initial)
    checksum=hashlib.sha256(initial.read_bytes()).hexdigest()
    if not args.weights and checksum!='0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1':
        raise RuntimeError('Initial official checkpoint checksum differs')
    name=args.name or f"{args.profile}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run=ROOT/'runs'/name
    if run.exists() and not args.resume:
        raise RuntimeError(f'Run already exists: {run}; choose a new name or resume')
    settings={'data':str(root/'data.yaml'),'epochs':args.epochs or (2 if args.profile=='pilot' else 100),
        'imgsz':args.imgsz or (416 if args.profile=='pilot' else 640),'batch':args.batch or (2 if args.profile=='pilot' else 4),
        'device':0,'workers':args.workers if args.workers is not None else (0 if args.profile=='pilot' else 2),
        'amp':True,'cache':False,'mosaic':0.0,'mixup':0.0,
        'copy_paste':0.0,'cutmix':0.0,'close_mosaic':0,'seed':42,'deterministic':True,
        'optimizer':'AdamW','lr0':0.001,'weight_decay':0.0005,'patience':20,
        'project':str(ROOT/'runs'),'name':name,'save':True,'save_period':1,'plots':False,
        'max_det':300,'exist_ok':False,'resume':bool(args.resume)}
    run.mkdir(parents=True,exist_ok=bool(args.resume))
    # Ultralytics accepts the already-created run when writing our provenance there.
    settings['exist_ok']=True
    metadata={'started_utc':datetime.now(timezone.utc).isoformat(),'profile':args.profile,
        'purpose':'pipeline smoke training; not production-ready' if args.profile=='pilot' else 'candidate fine-tuning',
        'initial_checkpoint':str(initial),'initial_checkpoint_sha256':checksum,
        'manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),
        'class_count':len(manifest['classes']),'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),
        'torch':torch.__version__,'ultralytics':importlib.metadata.version('ultralytics'),
        'python':platform.python_version(),'settings':settings,
        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                         for name in ['train.py','verified_training.py','prepare.py','evaluate.py']},
        'metric_note':'training validation is a verified-label proxy; use evaluate.py for official LVIS metrics'}
    (run/'provenance.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    shutil.copy2(ROOT/'catalog.json',run/'catalog.json')
    model=YOLO(str(args.resume or initial))
    try:
        model.train(trainer=VerifiedTrainer,**settings)
        status={'state':'completed','best':str(run/'weights/best.pt'),'profile':args.profile,
            'quality':'unproven; requires independent evaluation','finished_utc':datetime.now(timezone.utc).isoformat()}
    except BaseException as exc:
        status={'state':'interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',
            'error':str(exc),'resume_checkpoint':str(run/'weights/last.pt')}
        (run/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
        raise
    (run/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    print(json.dumps(status,indent=2),flush=True)


if __name__=='__main__':
    main()
