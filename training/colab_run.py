"""Run the verified-label trainer on Colab; no training starts on import."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def relocate_dataset(root):
    """Only data.yaml contains machine paths; preserve the hashed manifest."""
    from train import validate_dataset
    manifest = validate_dataset(root)
    config = json.loads((root / 'data.yaml').read_text(encoding='utf-8'))
    config['path'] = str(root.resolve())
    (root / 'data.yaml').write_text(json.dumps(config, indent=2), encoding='utf-8')
    for split, records in manifest['splits'].items():
        images = list((root / 'images' / split).glob('*.jpg'))
        if len(images) != len(records):
            raise RuntimeError(f'Incomplete images for {split}')
        for image in images:
            if not (root / 'labels' / split / (image.stem + '.txt')).is_file():
                raise RuntimeError(f'Missing labels: {image}')
    return manifest


def sync_run(run, destination):
    """Replace complete copies on Drive, including resumable optimizer state."""
    for relative in ['weights/last.pt', 'weights/best.pt', 'results.csv',
                     'args.yaml', 'colab-provenance.json', 'status.json']:
        source = run / relative
        if source.is_file():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.part')
            shutil.copyfile(source, temporary)
            temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=['v8-new', 'resume-drive'])
    parser.add_argument('--name', required=True)
    parser.add_argument('--drive-root', type=Path, required=True)
    parser.add_argument('--epochs', type=int, default=50, help='Total epochs, including saved epochs on resume')
    parser.add_argument('--batch', type=int, default=4)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    if Path(args.name).name != args.name or args.name in ('.', '..'):
        parser.error('Use a run name, not a path')
    if args.epochs < 1 or args.batch < 1 or args.workers < 0:
        parser.error('Invalid epochs, batch or workers')

    import importlib.metadata
    import torch
    from ultralytics import YOLO
    from verified_training import VerifiedTrainer

    class WindowsResumeTrainer(VerifiedTrainer):
        def build_optimizer(self, *args, **kwargs):
            optimizer = super().build_optimizer(*args, **kwargs)
            # The Windows fused kernel rejected the optimizer tensors loaded from Colab.
            for group in optimizer.param_groups:
                group['fused'] = False
            return torch.optim.AdamW(optimizer.param_groups, fused=False)

    if importlib.metadata.version('ultralytics') != '8.4.188':
        raise RuntimeError('Requires ultralytics==8.4.188')
    if not torch.cuda.is_available():
        raise RuntimeError('Select a hosted GPU runtime in Colab first')
    root = ROOT / 'data/prepared/full'
    manifest = relocate_dataset(root)
    run = ROOT / 'runs' / args.name
    destination = args.drive_root / 'runs' / args.name
    settings = dict(data=str(root / 'data.yaml'), project=str(ROOT / 'runs'), name=args.name,
                    epochs=args.epochs, imgsz=640, batch=args.batch, workers=args.workers,
                    device=0, amp=True, cache=False, mosaic=0., mixup=0., cutmix=0.,
                    copy_paste=0., close_mosaic=0, seed=42, deterministic=True,
                    optimizer='AdamW', lr0=.001, weight_decay=.0005, patience=20,
                    save=True, save_period=1, plots=False, max_det=300, exist_ok=True)
    if args.mode == 'resume-drive':
        source = destination / 'weights/last.pt'
    else:
        source = ROOT.parent / 'backend/weights/best.pt'
    if not source.is_file():
        raise FileNotFoundError(source)
    if args.mode != 'resume-drive' and (run.exists() or destination.exists()):
        raise RuntimeError('Run exists; choose a new name or resume-drive')
    checkpoint = torch.load(source, map_location='cpu', weights_only=False)
    saved_model = checkpoint.get('ema') or checkpoint.get('model')
    if args.mode == 'v8-new' and len(saved_model.names) != 51:
        raise RuntimeError('Expected the original 51-label YOLOv8 checkpoint')
    if args.mode != 'v8-new':
        previous = json.loads((destination / 'colab-provenance.json').read_text(encoding='utf-8'))
        manifest_hash = hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest()
        if previous['manifest_sha256'] != manifest_hash:
            raise RuntimeError('Resume dataset differs from the previous run')
        if len(saved_model.names) != len(manifest['classes']) or checkpoint.get('optimizer') is None:
            raise RuntimeError('Resume needs the complete 1000-class optimizer checkpoint')
        if args.epochs <= checkpoint['epoch'] + 1:
            raise RuntimeError('Total epochs must exceed completed checkpoint epochs')
        # Ultralytics reloads train_args on resume: replace Windows/old-runtime paths
        # in a local COPY while preserving the saved weights, optimizer and scheduler.
        local_resume = ROOT / 'weights/colab-resume.pt'
        local_resume.parent.mkdir(parents=True, exist_ok=True)
        checkpoint['train_args'].update(settings)
        checkpoint['train_args']['model'] = str(local_resume)
        checkpoint['train_args']['save_dir'] = str(run)
        torch.save(checkpoint, local_resume)
        initial = local_resume
    else:
        initial = source
    del saved_model, checkpoint
    run.mkdir(parents=True, exist_ok=True)
    provenance = dict(started_utc=datetime.now(timezone.utc).isoformat(), mode=args.mode,
                      initial_checkpoint_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      manifest_sha256=hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest(),
                      class_count=len(manifest['classes']), settings=settings,
                      torch=torch.__version__, ultralytics=importlib.metadata.version('ultralytics'),
                      gpu=torch.cuda.get_device_name(0), metric_note='Verified-label validation proxy; not final LVIS evaluation')
    (run / 'colab-provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    model = YOLO(str(initial))
    model.add_callback('on_model_save', lambda trainer: sync_run(Path(trainer.save_dir), destination))
    trainer_class = WindowsResumeTrainer if os.name == 'nt' and args.mode == 'resume-drive' else VerifiedTrainer
    try:
        model.train(trainer=trainer_class, resume=args.mode != 'v8-new', **settings)
        state = dict(state='completed', quality='Requires independent evaluation')
    except BaseException as exc:
        state = dict(state='interrupted', error=str(exc))
        raise
    finally:
        (run / 'status.json').write_text(json.dumps(state), encoding='utf-8')
        sync_run(run, destination)
    print('Saved checkpoints and metrics:', destination)


if __name__ == '__main__':
    main()
