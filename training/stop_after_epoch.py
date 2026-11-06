"""Stop this already-running job after its requested epoch checkpoint is complete.

The runner has no live stop callback. Watch its post-validation checkpoint,
preserve that checkpoint and metrics, then stop only the verified process tree.
No subsequent epoch's weights are retained.
"""
import argparse
import csv
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent


def checkpoint_ready(checkpoint, results, epoch):
    if not checkpoint.is_file() or not results.is_file():
        return False
    try:
        with results.open(encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        if not any(int(row['epoch'].strip()) == epoch for row in rows):
            return False
        with zipfile.ZipFile(checkpoint) as archive:
            return archive.testzip() is None
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--epoch', type=int, default=1)
    args = parser.parse_args()
    if Path(args.name).name != args.name or args.epoch < 1:
        parser.error('Invalid run name or epoch')
    run = ROOT / 'runs' / args.name
    job = ROOT / 'runs' / ('job-' + args.name)
    state = json.loads((job / 'status.json').read_text(encoding='utf-8'))
    parent, child = psutil.Process(state['pid']), psutil.Process(state['child_pid'])
    for process, script in [(parent, 'run_job.py'), (child, 'train.py')]:
        command = process.cmdline()
        if not any(Path(part).name == script for part in command) or args.name not in command:
            raise RuntimeError('Process identity mismatch; refusing to stop')
    checkpoint = run / 'weights' / f'epoch{args.epoch - 1}.pt'
    report = job / 'stop-after-epoch.json'

    def persist(**changes):
        record = dict(updated_utc=datetime.now(timezone.utc).isoformat(), **changes)
        temporary = report.with_suffix('.json.part')
        temporary.write_text(json.dumps(record, indent=2), encoding='utf-8')
        temporary.replace(report)

    persist(state='armed', epoch=args.epoch, parent_pid=parent.pid, child_pid=child.pid)
    while not checkpoint_ready(checkpoint, run / 'results.csv', args.epoch):
        if not child.is_running() or not parent.is_running():
            persist(state='failed', reason='Training process exited before requested checkpoint')
            raise SystemExit(1)
        time.sleep(0.05)

    # The epoch checkpoint is written after validation, results.csv, last and best.
    # Suspend the trainer first to prevent further optimizer steps during cleanup.
    child.suspend()
    descendants = child.children(recursive=True)
    parent.terminate()  # prevent the runner from interpreting our stop as a failure
    child.terminate()
    for process in descendants:
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs([parent, child, *descendants], timeout=10)
    for process in alive:
        process.kill()
    if alive:
        psutil.wait_procs(alive, timeout=5)
    stopped = dict(state='paused', reason='User requested stop after one completed epoch',
                   completed_epochs=args.epoch, checkpoint=str(checkpoint),
                   finished_utc=datetime.now(timezone.utc).isoformat())
    (run / 'status.json').write_text(json.dumps(stopped, indent=2), encoding='utf-8')
    state.update(stopped, stage='stopped_after_epoch', child_pid=None,
                 updated_utc=stopped['finished_utc'])
    (job / 'status.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    persist(**stopped)
    print(json.dumps(stopped), flush=True)


if __name__ == '__main__':
    main()
