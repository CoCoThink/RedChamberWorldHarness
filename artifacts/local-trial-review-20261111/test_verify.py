"""Adversarial checks for native review custody; no simulated literary votes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

MODULE = Path(__file__).with_name('verify.py')
spec = importlib.util.spec_from_file_location('trial_review_verify', MODULE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewCustodyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.execution_path = review.BASE / 'execution.json'
        self.execution = json.loads((review.ROOT / self.execution_path).read_bytes())
        paths = {self.execution_path}

        def refs(value):
            if isinstance(value, dict):
                if 'path' in value and 'sha256' in value:
                    paths.add(Path(value['path']))
                for item in value.values():
                    refs(item)
            elif isinstance(value, list):
                for item in value:
                    refs(item)

        refs(self.execution)
        refs(json.loads((review.ROOT / self.execution['selected_plan']).read_bytes()))
        for path in paths:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(review.ROOT / path, target)

    def save_execution(self):
        (self.root / self.execution_path).write_text(json.dumps(self.execution))

    def change_opinion(self, job, mutate):
        attempt = next(a for a in self.execution['attempts'] if a['job'] == job)
        ref = attempt['raw_opinion']
        path = self.root / ref['path']
        opinion = json.loads(path.read_bytes())
        mutate(opinion)
        raw = json.dumps(opinion, ensure_ascii=False, separators=(',', ':')).encode()
        path.write_bytes(raw)
        ref.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        self.save_execution()

    def rejected(self, message):
        with self.assertRaisesRegex(ValueError, message):
            review.verify(self.root)

    def test_complete_custody_keeps_real_negative_and_pending(self):
        report = review.verify(self.root)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['literary_status'], 'PENDING')
        self.assertEqual(report['finding_assessments']['FAIL'], 1)
        self.assertEqual(report['nonpass_contract_obligations'], 2)
        self.assertFalse(report['formal_eligibility'])

    def test_changed_raw_bytes_without_rebinding_rejected(self):
        path = self.root / self.execution['attempts'][0]['raw_opinion']['path']
        path.write_bytes(path.read_bytes() + b'\n')
        self.rejected('changed bytes')

    def test_unread_file_cannot_count_as_complete(self):
        self.change_opinion('blind-1', lambda o: o['declared_read_files'][0].update(read_complete=False))
        self.rejected('unread assigned input')

    def test_rebound_missing_obligation_rejected(self):
        self.change_opinion('contract-1', lambda o: o['obligation_findings'].pop())
        self.rejected('contract obligation coverage mismatch')

    def test_one_reader_cannot_count_twice(self):
        self.execution['attempts'][1]['agent'] = self.execution['attempts'][0]['agent']
        self.save_execution()
        self.rejected('reader reused')

    def test_oversize_output_is_rejected_without_truncation(self):
        self.change_opinion('blind-1', lambda o: o.update(extra='字' * 6000))
        self.rejected('raw opinion over output budget')

    def test_batch_two_cannot_overlap_batch_one(self):
        self.execution['attempts'][-1]['started_at'] = self.execution['attempts'][0]['started_at']
        self.save_execution()
        self.rejected('second batch started before')

    def test_bound_reviewer_identity_cannot_be_replaced_by_author(self):
        self.change_opinion('blind-1', lambda o: o['reviewer'].update(principal_id='session:main-agent:ch86-local-trial:20261110'))
        self.rejected('reviewer identity mismatch')

    def test_blind_reader_cannot_claim_unassigned_context_read(self):
        self.change_opinion('blind-1', lambda o: o['declared_read_files'].append({'path': 'author-audit.json', 'read_complete': True}))
        self.rejected('missing/extra read declaration')

    def test_human_admission_cannot_derive_from_model_review(self):
        self.execution['human_qualification'] = True
        self.save_execution()
        self.rejected('review qualification inflated')

    def test_coordinator_cannot_erase_original_literary_fail(self):
        ref = self.execution['disposition_binding']
        path = self.root / ref['path']
        disposition = json.loads(path.read_bytes())
        next(f for f in disposition['findings'] if f['original_assessment'] == 'FAIL')['original_assessment'] = 'PASS'
        raw = json.dumps(disposition, ensure_ascii=False).encode()
        path.write_bytes(raw)
        ref.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        self.save_execution()
        self.rejected('original finding verdict changed')

    def test_missing_model_event_cannot_hide_behind_read_declaration(self):
        self.change_opinion('contract-2', lambda o: o.update(event_and_message_findings=[
            f for f in o['event_and_message_findings'] if f['id'] != 'death_witnessed']))
        self.rejected('event coverage missing/unknown')


if __name__ == '__main__':
    unittest.main()
