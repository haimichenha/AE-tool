import copy
import importlib.util
import tempfile
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('task_state', Path(__file__).resolve().parents[1] / 'scripts/task_state.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.e = self.root / 'evidence.txt'
        self.e.write_text('real test readback', encoding='utf-8')
        self.card = dict(objective='cross-domain test', model='configured-grok', endpoint_origin='https://example.invalid',
            authorization='synthetic local tests only; no network', roots=[str(self.root)],
            limits=dict(max_steps=20, max_work_attempts=2, max_verify_attempts=2, max_seconds=3600),
            tasks=[dict(id='one', mode='Implement', goal='produce artifact', depends_on=[], criteria={'A1': 'actual readback'})])
        self.state = m.initialize(self.card, self.root / 'state.json')

    def receipt(self, outcome, task='one', **extra):
        t = self.state['tasks'][task]
        r = dict(task_id=task, phase=t['phase'], attempt=t['attempts'][t['phase']], reviewer='host', outcome=outcome,
                 note='independent test fixture check', evidence=[dict(id='E1', path=str(self.e), sha256=m.digest(self.e))])
        if outcome == 'passed':
            r.update(acceptance={'A1': {'verdict': 'passed', 'evidence_ids': ['E1']}}, remaining_work=[])
        r.update(extra)
        return r

    def work(self, task='one'):
        m.begin(self.state, task, 'work')
        m.record(self.state, self.receipt('ready_for_verify', task))

    def test_last_work_attempt_still_gets_verify(self):
        m.begin(self.state, 'one', 'work')
        m.record(self.state, self.receipt('retry', safe_to_retry=True))
        self.work()
        self.assertEqual(m.next_step(self.state)['phase'], 'verify')
        m.begin(self.state, 'one', 'verify')
        m.record(self.state, self.receipt('passed'))
        self.assertEqual(m.next_step(self.state)['status'], 'completed')

    def test_work_cannot_complete(self):
        m.begin(self.state, 'one', 'work')
        with self.assertRaisesRegex(ValueError, 'phase outcome'):
            m.record(self.state, self.receipt('passed'))

    def test_interruption_never_replays_action(self):
        m.begin(self.state, 'one', 'work')
        m.save(self.root / 'state.json', self.state)
        loaded = m.read(self.root / 'state.json')
        self.assertEqual(m.next_step(loaded)['status'], 'reconcile_required')
        with self.assertRaises(ValueError):
            m.begin(loaded, 'one', 'work')
        m.record(loaded, self.receipt('ready_for_verify'))
        self.assertEqual(m.next_step(loaded)['phase'], 'verify')

    def test_duplicate_receipt_refused(self):
        m.begin(self.state, 'one', 'work')
        r = self.receipt('ready_for_verify')
        m.record(self.state, r)
        with self.assertRaises(ValueError):
            m.record(self.state, r)

    def test_missing_or_fake_evidence_refused(self):
        m.begin(self.state, 'one', 'work')
        r = self.receipt('ready_for_verify')
        r['evidence'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            m.record(self.state, r)

    def test_all_criteria_and_no_remaining_required(self):
        self.work()
        m.begin(self.state, 'one', 'verify')
        for changes in ({'acceptance': {}}, {'remaining_work': ['runtime']},
                        {'acceptance': {'A1': {'verdict': 'passed', 'evidence_ids': ['UNKNOWN']}}}):
            with self.assertRaises(ValueError):
                m.record(self.state, self.receipt('passed', **changes))

    def test_blocked_branch_does_not_stop_independent_task(self):
        self.card['tasks'] += [dict(id='two', mode='ReadOnly', goal='independent', depends_on=[], criteria={'A1': 'read'}),
                               dict(id='three', mode='ReadOnly', goal='dependent', depends_on=['one'], criteria={'A1': 'read'})]
        self.state = m.initialize(self.card, self.root / 'other.json')
        m.begin(self.state, 'one', 'work')
        m.record(self.state, self.receipt('blocked'))
        self.assertEqual(m.next_step(self.state)['task_id'], 'two')

    def test_rework_obeys_original_attempt_limit(self):
        self.state['card']['limits']['max_work_attempts'] = 1
        self.work()
        m.begin(self.state, 'one', 'verify')
        m.record(self.state, self.receipt('rework'))
        self.assertEqual(m.next_step(self.state)['status'], 'blocked')

    def test_step_and_time_budgets_pause_not_complete(self):
        self.state['steps'] = 20
        self.assertEqual(m.next_step(self.state)['status'], 'paused_limit')
        self.state['steps'] = 0
        self.state['created_at'] -= 4000
        self.assertEqual(m.next_step(self.state)['status'], 'paused_limit')

    def test_cycles_and_unknown_dependencies_rejected(self):
        card = copy.deepcopy(self.card)
        card['tasks'][0]['depends_on'] = ['unknown']
        with self.assertRaises(ValueError):
            m.validate_card(card)
        card['tasks'][0]['depends_on'] = ['two']
        card['tasks'].append(dict(id='two', mode='ReadOnly', goal='read', depends_on=['one'], criteria={'A1': 'read'}))
        with self.assertRaisesRegex(ValueError, 'cycle'):
            m.validate_card(card)

    def test_changed_accepted_evidence_is_not_complete(self):
        self.work()
        m.begin(self.state, 'one', 'verify')
        m.record(self.state, self.receipt('passed'))
        self.e.write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            m.next_step(self.state)

    def test_lock_prevents_parallel_writer(self):
        with m.locked(self.root / 'state.json'):
            with self.assertRaises(FileExistsError):
                with m.locked(self.root / 'state.json'):
                    pass
        self.assertFalse(Path(str(self.root / 'state.json') + '.lock').exists())

    def test_retry_needs_side_effect_readback(self):
        m.begin(self.state, 'one', 'work')
        with self.assertRaisesRegex(ValueError, 'no-side-effects'):
            m.record(self.state, self.receipt('retry'))

    def test_readonly_task_and_verify_mode(self):
        self.card['tasks'][0]['mode'] = 'ReadOnly'
        self.assertEqual(m.next_step(self.state)['mode'], 'ReadOnly')
        self.work()
        self.assertEqual(m.next_step(self.state)['mode'], 'ReadOnly')


if __name__ == '__main__':
    unittest.main()
