"""Separate CLI completion from goal acceptance. Parse only, never execute model output."""
import argparse
import json
from pathlib import Path


def classify(events, verification):
    final = next((e for e in reversed(events) if e.get('type') == 'result'), None)
    noops = 0
    tools = []
    for e in events:
        msg = e.get('message', {})
        blocks = msg.get('content', []) if isinstance(msg, dict) else []
        if not isinstance(blocks, list):
            continue
        for b in blocks:
            if not isinstance(b, dict):
                continue
            if b.get('type') == 'tool_use':
                tools.append(b.get('name'))
            if b.get('type') == 'tool_result' and b.get('is_error'):
                content = b.get('content', '')
                text = content if isinstance(content, str) else json.dumps(content)
                noops += int('NO_PROGRESS:' in text)
    out = {'accepted': False, 'tool_calls': tools, 'noop_denials': noops,
           'cli_success': bool(final and final.get('subtype') == 'success' and not final.get('is_error'))}
    if final is None:
        return dict(out, status='incomplete', reason='no final CLI envelope; reconcile process before retrying')
    if not out['cli_success']:
        return dict(out, status='failed_execution', reason=final.get('subtype', 'CLI error'))
    if not str(final.get('result') or '').strip():
        return dict(out, status='blocked_no_progress' if noops else 'incomplete', reason='CLI success with empty final is not task completion; possibly stopped by a hook')
    required = verification.get('required_criteria', [])
    criteria = verification.get('criteria', {})
    passed = (verification.get('reviewer') == 'host' and verification.get('exit_code') == 0
              and verification.get('protected_inputs_unchanged') is True and required
              and set(required) == set(criteria) and all(v == 'passed' for v in criteria.values()))
    if not passed:
        return dict(out, status='failed_acceptance', reason='independent host criteria failed or are incomplete; model completion claim rejected')
    return dict(out, accepted=True, status='accepted', reason='CLI ended normally and all host acceptance criteria passed')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stream', type=Path, required=True)
    ap.add_argument('--host-verification', type=Path, required=True)
    args = ap.parse_args()
    events = [json.loads(line) for line in args.stream.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    result = classify(events, json.loads(args.host_verification.read_text(encoding='utf-8-sig')))
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result['accepted'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
