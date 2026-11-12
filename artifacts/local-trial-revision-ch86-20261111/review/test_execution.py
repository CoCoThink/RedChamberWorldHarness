"""Negative checks for evidence loss and qualification inflation."""
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.relative_to(ROOT)


class ReviewCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        paths = [BASE, BASE.parent / 'reading-inputs', Path('AGENTS.md'),
                 Path('artifacts/local-trial-review-20261111/verify.py')]
        plan = json.loads((HERE / 'manifest.json').read_bytes())
        paths.append(Path(plan['candidate']['path']))
        for relative in paths:
            source, target = ROOT / relative, self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copyfile(source, target)

    def verify(self):
        return runpy.run_path(str(self.root / BASE / 'verify_execution.py'))['verify']()

    def change_disposition(self, edit):
        path = self.root / BASE / 'disposition.json'
        value = json.loads(path.read_bytes())
        edit(value)
        path.write_text(json.dumps(value, ensure_ascii=False))
        receipt = self.root / BASE / 'execution.json'
        execution = json.loads(receipt.read_bytes())
        execution['disposition_binding'].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
        receipt.write_text(json.dumps(execution))

    def test_complete_receipts(self):
        self.assertEqual(self.verify()['events'], 24)

    def test_changed_raw_review_is_rejected(self):
        path = self.root / BASE / 'opinions/blind-1.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.verify()

    def test_pending_finding_cannot_be_omitted_with_rebound_receipt(self):
        self.change_disposition(lambda d: d.update(findings=[f for f in d['findings'] if f['finding_id'] != 'C1-DEATH-KNOWLEDGE']))
        with self.assertRaises(AssertionError):
            self.verify()

    def test_semantic_pass_cannot_be_granted_with_rebound_receipt(self):
        self.change_disposition(lambda d: d.update(semantic_status='PASS'))
        with self.assertRaises(AssertionError):
            self.verify()


if __name__ == '__main__':
    unittest.main()
