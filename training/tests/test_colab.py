"""Portability and checkpoint backup checks; never starts a training run."""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from colab_run import relocate_dataset, sync_run


class ColabTests(unittest.TestCase):
    def test_relocation_preserves_manifest_and_requires_images_and_labels(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'reports') as directory:
            root = Path(directory)
            (root / 'data.yaml').write_text(json.dumps({'path': 'D:/old', 'names': {'0': 'cup'}}))
            (root / 'manifest.json').write_bytes(b'unchanged manifest')
            manifest = {'splits': {'train': [{'id': 1}]}}
            (root / 'images/train').mkdir(parents=True)
            (root / 'labels/train').mkdir(parents=True)
            image = root / 'images/train/1.jpg'
            image.write_bytes(b'image file presence only')
            with patch('train.validate_dataset', return_value=manifest):
                with self.assertRaises(RuntimeError):
                    relocate_dataset(root)
                (root / 'labels/train/1.txt').write_text('0 .5 .5 .1 .1')
                self.assertEqual(relocate_dataset(root), manifest)
            self.assertEqual((root/'manifest.json').read_bytes(), b'unchanged manifest')
            self.assertEqual(json.loads((root/'data.yaml').read_text())['path'], str(root.resolve()))

    def test_checkpoint_backup_replaces_complete_file_and_copies_metrics(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'reports') as directory:
            run, target = Path(directory)/'local', Path(directory)/'drive'
            (run/'weights').mkdir(parents=True)
            (run/'weights/last.pt').write_bytes(b'optimizer checkpoint')
            (run/'results.csv').write_text('epoch,metric\n1,.2')
            sync_run(run, target)
            self.assertEqual((target/'weights/last.pt').read_bytes(), b'optimizer checkpoint')
            (run/'weights/last.pt').write_bytes(b'next complete checkpoint')
            sync_run(run, target)
            self.assertEqual((target/'weights/last.pt').read_bytes(), b'next complete checkpoint')
            self.assertTrue((target/'results.csv').is_file())
            self.assertFalse(list(target.rglob('*.part')))

    def test_notebook_cells_compile_and_training_defaults_off(self):
        notebook = json.loads((ROOT/'train_yolov8n_colab.ipynb').read_text(encoding='utf-8'))
        code = [''.join(entry['source']) for entry in notebook['cells'] if entry['cell_type']=='code']
        for source in code:
            ast.parse(source)
        self.assertTrue(any('RUN_TRAINING = False' in source for source in code))
        self.assertFalse(any('11-resume' in source for source in code))


if __name__ == '__main__':
    unittest.main()
