"""H1: replay every supplied single case, prior turn and trajectory against the original harness."""
import hashlib
import json
from pathlib import Path

from test_harness_contract import MARKER, _policy_cases

from evals.run_fixtures import make_session
from secondsignal import load_roster
from secondsignal_harness import CodexStore, FakeAdapter, Harness

ROOT = Path(__file__).resolve().parents[1]

def replay():
    roster, codexes = load_roster(), CodexStore(ROOT / "docs/codex")
    rows = []
    cases = [(label + "::" + case["id"], case,
              [*(p["text"] if isinstance(p, dict) else p
                 for p in case.get("prior_turns", [])), case["text"]])
             for label, case in _policy_cases()]
    for path in sorted((ROOT / "evals/cases/trajectories").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("kind") == "trajectory":
            cases.append((path.relative_to(ROOT / "evals/cases").as_posix() + "::" + case["id"],
                          case, [p["text"] for p in case["turns"]]))
    for label, case, texts in cases:
        harness = Harness(roster, FakeAdapter(script=(MARKER,)), codexes,
                          session=make_session(case), operator_circle=True)
        for number, text in enumerate(texts, 1):
            turn = harness.speak(text)
            material = json.dumps({"decision": turn.decision, "house_lines": turn.house_lines,
                                   "text": turn.text}, sort_keys=True, ensure_ascii=False,
                                  separators=(",", ":"))
            rows.append({"case": label, "turn": number, "released": turn.released,
                         "release_reason": turn.release_reason,
                         "policy_and_output_sha256": hashlib.sha256(material.encode()).hexdigest()})
    return {"source": "SecondSignal-20de102-P2V1, order T5R (landing 15), 2026-11-04: labelled single cases with prior turns and trajectories",  # Order P2V1, 2026-10-13: 82521ba G1/P3 -> 20de102 P2V1; kinds and roster hashes, no changed old releases. Order T5R, 2026-11-04: source 'SecondSignal-20de102, order P2V1, 13 October 2026: labelled single cases with prior turns and trajectories' -> 'SecondSignal-20de102-P2V1, order T5R (landing 15), 2026-11-04: labelled single cases with prior turns and trajectories'; second-ask replay hashes regenerated.
            "adapter": "FakeAdapter with existing PERSONA-TEXT-MARKER fixture",
            "cases": len(cases), "turns": len(rows),
            "released": sum(row["released"] for row in rows), "rows": rows}


def test_h1_every_labelled_turn_keeps_its_policy_house_lines_and_release():
    """All 904 turns match the recorded decisions, house lines, output and release; 231 release."""  # Follow-on to order P2V1, 13 October 2026: 693 cases/893 turns/225 releases -> 704 cases/904 turns/231 releases; all 893 prior rows unchanged.
    expected = json.loads((ROOT / "tests/fixtures/h1/labelled_before.json").read_text(encoding="utf-8"))
    actual = replay()
    assert actual == expected
