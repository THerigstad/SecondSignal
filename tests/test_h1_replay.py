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
    return {"source": "main b4e819b labelled single cases with prior turns and trajectories",
            "adapter": "FakeAdapter with existing PERSONA-TEXT-MARKER fixture",
            "cases": len(cases), "turns": len(rows),
            "released": sum(row["released"] for row in rows), "rows": rows}


def test_h1_every_labelled_turn_keeps_its_policy_house_lines_and_release():
    """All 889 turns keep identical decisions, house lines, output and release; 235 still release."""
    expected = json.loads((ROOT / "tests/fixtures/h1/labelled_before.json").read_text(encoding="utf-8"))
    actual = replay()
    assert actual == expected
