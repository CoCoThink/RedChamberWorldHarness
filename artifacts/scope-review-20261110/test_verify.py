"""Negative checks for original-opinion custody and unsupported scope promotion."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

DIRECTORY = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('scope_execution_verify', DIRECTORY / 'verify.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CustodyChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / 'artifacts/scope-review-20261110'
        shutil.copytree(DIRECTORY, self.directory, ignore=shutil.ignore_patterns('__pycache__'))
        partition = 'artifacts/scope-preflight-20261110/review-v2'
        shutil.copytree(DIRECTORY.parents[1] / partition, self.root / partition)
        self.execution = json.loads((self.directory / 'execution.json').read_bytes())
        self.decision = json.loads((self.directory / 'coordinator-decisions.json').read_bytes())

    def reference(self, path):
        raw = path.read_bytes()
        return {'path': path.relative_to(self.root).as_posix(),
                'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

    def write(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')))
        return self.reference(path)

    def opinion(self, mutate):
        attempt = self.execution['tasks'][0]['attempts'][-1]
        path = self.root / attempt['raw_output']['path']
        value = json.loads(path.read_bytes())
        mutate(value)
        attempt['raw_output'] = self.write(path, value)

    def check(self):
        self.decision['execution'] = self.write(self.directory / 'execution.json', self.execution)
        self.decision['accepted_opinions'] = [a['raw_output'] for t in self.execution['tasks']
                                             for a in t['attempts'] if a['status'] == 'ACCEPTED']
        self.write(self.directory / 'coordinator-decisions.json', self.decision)
        return MODULE.verify(self.root, self.execution)

    def test_complete_receipt_preserves_pending_and_outside_scope(self):
        result = self.check()
        self.assertEqual(result['complete_readings'], 8)
        self.assertEqual(result['independent_native_readers'], 8)
        self.assertEqual(result['observed_peak_parallel'], 3)
        self.assertEqual(result['scope_status'], 'PENDING')
        self.assertEqual(result['production_admission'], 'NOT_GRANTED')
        self.assertTrue(result['results'][0]['unread_scope'])
        self.assertEqual(sum(r['rejected_attempts'] for r in result['results']), 3)

    def test_original_bytes_cannot_be_replaced(self):
        path = self.root / self.execution['tasks'][0]['attempts'][0]['raw_output']['path']
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'binding bytes differ'):
            self.check()

    def test_nonexistent_quote_is_rejected_after_rebinding(self):
        self.opinion(lambda v: v['findings'][0]['evidence'][0].update(quote='NONEXISTENT_QUOTE'))
        with self.assertRaisesRegex(ValueError, 'quote absent'):
            self.check()

    def test_citation_cannot_escape_assigned_scope(self):
        self.opinion(lambda v: v['findings'][0]['evidence'][0].update(file='task-14.json'))
        with self.assertRaisesRegex(ValueError, 'outside assigned scope'):
            self.check()

    def test_complete_cannot_hide_unread_assigned_file(self):
        self.opinion(lambda v: v['files'][0].update(read_complete=False))
        with self.assertRaisesRegex(ValueError, 'omitted assigned files'):
            self.check()

    def test_incomplete_reading_cannot_pass(self):
        self.opinion(lambda v: v.update(reading_status='NOT_CHECKED', scope_verdict='PASS'))
        with self.assertRaisesRegex(ValueError, 'incomplete reading cannot pass'):
            self.check()

    def test_reader_cannot_claim_provider_proof(self):
        self.opinion(lambda v: v.update(provider_consumption_proof=True))
        with self.assertRaisesRegex(ValueError, 'unsupported authority'):
            self.check()

    def test_oversize_original_output_cannot_be_accepted(self):
        attempt = self.execution['tasks'][0]['attempts'][-1]
        path = self.root / attempt['raw_output']['path']
        path.write_bytes(path.read_bytes() + b' ' * 8192)
        attempt['raw_output'] = self.reference(path)
        with self.assertRaisesRegex(ValueError, 'exceeds output reservation'):
            self.check()

    def test_repair_cannot_drop_previous_output_context(self):
        attempt = self.execution['tasks'][0]['attempts'][-1]
        path = self.root / attempt['start_receipt']['path']
        value = json.loads(path.read_bytes())
        value['repair_history_bytes'] = 0
        attempt['start_receipt'] = self.write(path, value)
        with self.assertRaisesRegex(ValueError, 'history accounting differs'):
            self.check()

    def test_output_reservation_cannot_be_enlarged(self):
        self.execution['tasks'][0]['output_limit_bytes'] = 16384
        with self.assertRaisesRegex(ValueError, 'reservation differs'):
            self.check()

    def test_coordinator_cannot_resolve_original_unknowns(self):
        row = self.decision['original_contract_declarations_preserved'][0]
        row['state_declarations']['exit_state'][0]['status'] = 'KNOWN'
        with self.assertRaisesRegex(ValueError, 'changed original unknowns'):
            self.check()

    def test_coordinator_cannot_grant_production_admission(self):
        self.decision['production_admission'] = 'GRANTED'
        with self.assertRaisesRegex(ValueError, 'promotes unsupported authority'):
            self.check()

    def test_proposed_order_cannot_contain_cycle(self):
        self.decision['proposed_local_order']['before'].append(['doctor_feedback', 'ordinary_care'])
        with self.assertRaisesRegex(ValueError, 'contains a cycle'):
            self.check()

    def test_pressure_mapping_cannot_drop_seed_obligations(self):
        self.decision['pressure_phases'][-1]['seeds'] = []
        with self.assertRaisesRegex(ValueError, 'omitted a seed'):
            self.check()

    def test_concurrency_above_three_is_rejected(self):
        for task in self.execution['tasks']:
            for attempt in task['attempts']:
                attempt['capture']['started_at'] = 1
                attempt['capture']['completed_at'] = 2
        with self.assertRaisesRegex(ValueError, 'concurrency differs'):
            self.check()


if __name__ == '__main__':
    unittest.main()
