"""Offline single-turn replay for the order-1 safety comparison."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--cases-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.root / 'src'))
    sys.path.insert(0, str(args.root))
    from evals.run_fixtures import run_case
    from secondsignal import load_roster
    case_dir = args.cases_dir or args.root / 'evals' / 'cases'
    roster = load_roster()
    rows = []
    for path in sorted(case_dir.rglob('*.json')):
        doc = json.loads(path.read_text(encoding='utf-8'))
        if ('deferred' in path.relative_to(case_dir).parts or doc.get('deferred')
            or doc.get('runnable_here') is False or doc.get('kind') == 'trajectory'
            or doc.get('plane', 'policy') != 'policy'):
            continue
        for case in doc.get('cases', []):
            if (not isinstance(case.get('text'), str) or case.get('deferred')
                or case.get('runnable_here') is False or case.get('kind') == 'trajectory'):
                continue
            decision, session = run_case(case, roster)
            rows.append({
                'id': case['id'], 'source': path.relative_to(case_dir).as_posix(),
                'action': decision.safety.action.name, 'outcome': decision.outcome.value,
                'agent': decision.agent_id, 'assist': decision.assist_agent_id,
                'held': list(decision.held), 'obligations': list(decision.obligations),
                'claim_subject': decision.claim_subject, 'seat_claim': decision.seat_claim,
                'card': decision.safety.card, 'latch': session.latch,
                'preferences': session.preferences,
            })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Replayed {len(rows)} runnable single-turn cases -> {args.output}')


if __name__ == '__main__':
    main()
