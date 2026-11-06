"""Package only training inputs for upload to the user's Google Drive."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def export(output):
    from train import validate_dataset
    prepared = ROOT / 'data/prepared/full'
    manifest = validate_dataset(prepared)
    files = [ROOT / name for name in ['train.py', 'colab_run.py', 'verified_training.py',
             'prepare.py', 'download.py', 'evaluate.py', 'assess.py', 'requirements.txt',
             'catalog.json', 'sources.json']]
    files += [PROJECT / 'backend/weights/best.pt', PROJECT / 'backend/app/services/ai_service.py',
              ROOT / 'data/raw/lvis_v1_val.json', ROOT / 'data/raw/provenance.json']
    files += [prepared / name for name in ['manifest.json', 'coverage.json', 'data.yaml',
                                          'download_audit.json', 'READY']]
    files += [p for folder in ['images', 'labels'] for p in sorted((prepared / folder).rglob('*'))
              if p.is_file() and p.suffix in ('.jpg', '.txt')]
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
    image_count = sum(p.suffix == '.jpg' for p in files)
    if image_count != sum(len(records) for records in manifest['splits'].values()):
        raise RuntimeError('Image count differs from manifest')
    if output.exists() or output.with_suffix('.zip.part').exists():
        raise RuntimeError('Archive already exists; refusing overwrite')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.zip.part')
    # JPEG is already compressed. ZIP_STORED avoids wasting local CPU recompressing it.
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for index, path in enumerate(files):
            name = path.relative_to(PROJECT).as_posix()
            archive.write(path, name)
            if index and index % 5000 == 0:
                print(f'Packed {index}/{len(files)} files', flush=True)
    temporary.replace(output)
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    info = dict(archive=output.name, bytes=output.stat().st_size, sha256=digest,
                images=image_count, classes=len(manifest['classes']),
                manifest_sha256=hashlib.sha256((prepared/'manifest.json').read_bytes()).hexdigest(),
                note='Contains only public dataset inputs, selected training code and old v8 weights; no .env, credentials, YOLO11 checkpoint or Python environment')
    output.with_suffix('.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    print(json.dumps(info, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'exports/colab-training-v8n.zip')
    args = parser.parse_args()
    export(args.output.resolve())
