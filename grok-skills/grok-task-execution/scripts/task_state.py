"""Host-operated, bounded task ledger. Does not run commands or contact a model.
Python 3.10+. Files are untrusted evidence, never executable instructions.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def save(path, value):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def locked(path):
    lock = Path(str(path) + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, str(os.getpid()).encode('ascii'))
        os.close(fd)
        yield
    finally:
        lock.unlink()


def validate_card(card):
    for key in ('objective', 'model', 'endpoint_origin', 'authorization'):
        require(isinstance(card.get(key), str) and bool(card[key].strip()), 'missing ' + key)
    require(card.get('roots') and all(Path(p).is_absolute() and Path(p).is_dir() for p in card['roots']), 'roots must be existing absolute directories')
    limits = card.get('limits', {})
    for key in ('max_steps', 'max_work_attempts', 'max_verify_attempts', 'max_seconds'):
        require(type(limits.get(key)) is int and limits[key] > 0, 'positive limit required: ' + key)
    tasks = card.get('tasks', [])
    require(isinstance(tasks, list) and tasks, 'nonempty tasks required')
    ids = [t['id'] for t in tasks]
    require(len(set(ids)) == len(ids) and all(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', i) for i in ids), 'invalid/duplicate task ids')
    for t in tasks:
        require(t.get('mode') in ('ReadOnly', 'Implement'), 'invalid task mode')
        require(isinstance(t.get('goal'), str) and t['goal'].strip(), 'goal required')
        criteria = t.get('criteria')
        require(isinstance(criteria, dict) and criteria and all(isinstance(v, str) and v.strip() for v in criteria.values()), 'criteria must map ids to observable outcomes')
        require(all(d in ids and d != t['id'] for d in t.get('depends_on', [])), 'invalid dependency')
    resolved = set()
    while len(resolved) < len(tasks):
        ready = {t['id'] for t in tasks if set(t.get('depends_on', [])) <= resolved}
        require(bool(ready - resolved), 'dependency cycle')
        resolved |= ready


def initialize(card, path):
    validate_card(card)
    require(not Path(path).exists(), 'state already exists; do not reset attempts')
    state = {'version': 1, 'card': card, 'created_at': time.time(), 'steps': 0, 'events': [], 'tasks': {}}
    for t in card['tasks']:
        state['tasks'][t['id']] = {'status': 'pending', 'phase': 'work', 'attempts': {'work': 0, 'verify': 0}, 'receipts': []}
    save(path, state)
    return state


def next_step(state):
    tasks = state['tasks']
    running = [key for key, value in tasks.items() if value['status'] == 'in_flight']
    if running:
        return {'status': 'reconcile_required', 'task_id': running[0], 'reason': 'check running process and real side effects before recording; never replay unknown work'}
    if all(t['status'] == 'done' for t in tasks.values()):
        # Completion receipts must still exist unchanged; host must separately
        # judge whether their claims actually prove the criteria.
        for task in tasks.values():
            for evidence in task['receipts'][-1]['evidence']:
                require(Path(evidence['path']).is_file() and digest(evidence['path']) == evidence['sha256'].lower(), 'accepted evidence changed; needs review')
        return {'status': 'completed'}
    limits = state['card']['limits']
    if state['steps'] >= limits['max_steps'] or time.time() - state['created_at'] >= limits['max_seconds']:
        return {'status': 'paused_limit', 'reason': 'preserve state; only user-approved new budget may continue'}
    for phase in ('verify', 'work'):
        for definition in state['card']['tasks']:
            t = tasks[definition['id']]
            if t['status'] not in ('pending', 'ready') or t['phase'] != phase:
                continue
            if not all(tasks[d]['status'] == 'done' for d in definition.get('depends_on', [])):
                continue
            if t['attempts'][phase] >= limits['max_' + phase + '_attempts']:
                continue
            return {'status': 'ready', 'task_id': definition['id'], 'phase': phase,
                    'mode': 'ReadOnly' if phase == 'verify' else definition['mode'],
                    'definition': definition, 'previous_receipt': t['receipts'][-1] if t['receipts'] else None}
    return {'status': 'blocked', 'reason': 'no runnable task: inspect blockers, dependencies and per-phase limits',
            'unfinished': [key for key, t in tasks.items() if t['status'] != 'done']}


def begin(state, task_id, phase):
    step = next_step(state)
    require(step.get('status') == 'ready' and step['task_id'] == task_id and step['phase'] == phase, 'not the next authorized task/phase')
    t = state['tasks'][task_id]
    t['status'] = 'in_flight'
    t['attempts'][phase] += 1
    state['steps'] += 1
    state['events'].append({'event': 'begin', 'task_id': task_id, 'phase': phase, 'attempt': t['attempts'][phase], 'at': time.time()})
    return step


def validate_evidence(evidence):
    require(isinstance(evidence, list) and evidence, 'local readback evidence required')
    ids = set()
    for item in evidence:
        require(item.get('id') and item['id'] not in ids, 'duplicate/missing evidence id')
        ids.add(item['id'])
        p = Path(item['path'])
        require(p.is_absolute() and p.is_file(), 'evidence must be an existing absolute file')
        require(digest(p) == item['sha256'].lower(), 'evidence hash mismatch')
    return ids


def record(state, receipt):
    task_id = receipt['task_id']
    require(task_id in state['tasks'], 'unknown task')
    t = state['tasks'][task_id]
    phase = t['phase']
    require(t['status'] == 'in_flight', 'begin required; duplicate receipt refused')
    require(receipt.get('phase') == phase and receipt.get('attempt') == t['attempts'][phase], 'stale or wrong-phase receipt')
    require(receipt.get('reviewer') == 'host', 'host review required; do not feed model output directly')
    require(isinstance(receipt.get('note'), str) and receipt['note'].strip(), 'host decision note required')
    ids = validate_evidence(receipt.get('evidence'))
    outcome = receipt['outcome']
    allowed = ('ready_for_verify', 'retry', 'blocked') if phase == 'work' else ('passed', 'retry', 'rework', 'blocked')
    require(outcome in allowed, 'invalid phase outcome')
    if outcome == 'passed':
        definition = next(d for d in state['card']['tasks'] if d['id'] == task_id)
        results = receipt.get('acceptance', {})
        require(set(results) == set(definition['criteria']), 'every criterion must be reviewed')
        for result in results.values():
            require(result.get('verdict') == 'passed' and result.get('evidence_ids') and set(result['evidence_ids']) <= ids, 'criterion lacks passing evidence')
        require(receipt.get('remaining_work') == [], 'remaining work is not empty')
        t['status'] = 'done'
    elif outcome == 'ready_for_verify':
        t.update(status='ready', phase='verify')
    elif outcome == 'rework':
        t.update(status='ready', phase='work')
    elif outcome == 'blocked':
        t['status'] = 'blocked'
    else:
        require(receipt.get('safe_to_retry') is True, 'retry requires explicit no-side-effects/readback decision')
        t['status'] = 'ready'
    t['receipts'].append(receipt)
    state['events'].append({'event': 'record', 'task_id': task_id, 'phase': phase, 'outcome': outcome, 'at': time.time()})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--state', required=True)
    subs = ap.add_subparsers(dest='command', required=True)
    p = subs.add_parser('init'); p.add_argument('--card', required=True)
    subs.add_parser('next')
    p = subs.add_parser('begin'); p.add_argument('--task', required=True); p.add_argument('--phase', choices=['work', 'verify'], required=True)
    p = subs.add_parser('record'); p.add_argument('--receipt', required=True)
    args = ap.parse_args()
    path = Path(args.state).resolve()
    require(path.parent.is_dir(), 'create the approved state directory first')
    started = None
    with locked(path):
        if args.command == 'init':
            state = initialize(read(args.card), path)
        else:
            state = read(path)
            if args.command == 'begin':
                started = begin(state, args.task, args.phase)
                save(path, state)
            elif args.command == 'record':
                record(state, read(args.receipt))
                save(path, state)
        output = dict(started, status='begun') if started else next_step(state)
        print(json.dumps(output, ensure_ascii=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=True))
        raise SystemExit(2)
