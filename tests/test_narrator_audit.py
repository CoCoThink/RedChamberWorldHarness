from rcwh.generation.narrator_audit import narrator_audit
from rcwh.generation.writing import feedback_report
from test_generation import root
from test_session_generation import session_root, prepare, imported


def test_matched_spans_are_exact_advisory_and_voice_unclassified():
    text = '她说：“这并不是证据。”\n旁人不能据此认定她已知晓。'
    report = narrator_audit(text)
    assert report['status'] == 'WARN' and report['qualification'] == 'FEEDBACK_ONLY'
    assert report['authority_effect'] == 'NONE'
    assert report['observation']['match_count'] == 2
    for match in report['observation']['matches']:
        assert text[match['start']:match['end']] == match['text']
        assert match['voice'] == 'UNCLASSIFIED'
    assert 'Quoted denials' in report['limitation']


def test_ordinary_negation_and_empty_text_never_get_literary_pass():
    for text in ['', '他不来，她仍须等着。没有水，便去井边。不能走得太远。']:
        report = narrator_audit(text)
        assert report['status'] == 'NOT_CHECKED'
        assert report['observation']['matches'] == []


def test_baseline_density_is_an_observation_not_an_improvement_verdict():
    report = narrator_audit('她摇头。', baseline='不能据此推断她知道。')
    assert report['comparison']['density_delta'] < 0
    assert report['comparison']['baseline']['match_count'] == 1
    assert 'Lower density is not evidence of improvement' in report['limitation']
    assert 'improved' not in report


def test_diagnostic_is_opt_in_to_preserve_legacy_feedback_bytes(session_root):
    root = session_root
    prepare(root)
    draft = imported(root)
    legacy = feedback_report(root, draft['draft']['path'])
    assert not any(row['evaluator'] == 'narrator_audit' for row in legacy['checks'])
    audited = feedback_report(root, draft['draft']['path'], audit_narrator=True)
    extra = [row for row in audited['checks'] if row['evaluator'] == 'narrator_audit']
    assert len(extra) == 1 and extra[0]['status'] == 'NOT_CHECKED'
    assert audited['formal_eligibility'] is False
    assert [row for row in audited['checks'] if row['evaluator'] != 'narrator_audit'] == legacy['checks']
