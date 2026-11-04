"""Show training progress without loading a model or querying the database."""
import json
from pathlib import Path

root=Path(__file__).resolve().parent
for path in sorted(root.glob('runs/*/status.json')):
    try:
        print(str(path.relative_to(root)))
        print(json.dumps(json.loads(path.read_text(encoding='utf-8')),ensure_ascii=False,indent=2))
    except (OSError,json.JSONDecodeError):
        print(f'{path}: status update in progress')
for path in sorted(root.glob('runs/*/results.csv')):
    lines=path.read_text(encoding='utf-8').splitlines()
    if lines:
        print(str(path.relative_to(root)))
        print(lines[0])
        print(lines[-1])
