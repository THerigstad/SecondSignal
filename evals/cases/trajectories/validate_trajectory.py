"""Shape check for trajectory fixtures (ADR-0028 (Proposed)). Standard library only.

This is not the runner (that is ``evals/run_trajectories.py``). It checks the
refusal rules the README in this directory states, computes
``counts_toward_recall`` from the provenance block, and refuses the one forgery
the field can see: a relabel of unchanged model text as human-written.

Provenance, since ruling 18 of 3 October 2026, is three separate facts plus a
review record: ``texts_by`` (who wrote the words), ``expectations_by`` (who
wrote the oracles) and ``scenario_origin`` (who set the pacing and the
escalation turn), then ``reviewer`` and ``reviewed_on`` and a per-turn
``attested: true``. A trajectory counts toward recall only when the texts and
the expectations are both human, a reviewer and a date are present, and every
turn is attested. The texts carry a digest (``texts_digest``, the SHA-256 of
the turn texts in order); ``model_authored_digests.json`` beside this file is
the register of digests known to be model-written, and a file whose digest is
on that register may not call its texts human or mixed. The register cannot
prove authorship; it can only refuse the relabel ChatGPT executed in review
round 3B and the boundary Nemotron's traj-provenance-boundary-001 asked for.

Run: python evals/cases/trajectories/validate_trajectory.py path/to/fixture.json [more.json ...]
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# A text register, not JSON: every .json in this directory must be a trajectory
# (tests/test_eval_cases.py::test_trajectory_files_are_never_collected_as_single_cases).
REGISTRY_PATH = HERE / "model_authored_digests.txt"

SCHEMA_VERSION = 2
SAFETY = {"PROCEED", "DISCLOSE", "BOUNDARY_HOLD", "HUMAN_ESCALATION"}
OUTCOME = {"ROUTED", "PREEMPTED", "UNRESOLVED"}
SINGLE_CASE_EXPECT = {
    "safety", "outcome", "agent", "agent_any_of", "ineligible", "not_seated",
    "reason_contains", "disclosures_contain", "latch", "latch_reasons", "held",
    "assist", "card", "preference_result", "obligations_contain", "crisis_read",
    "integrity_event", "card_order", "language_scope",
}
# aftermath: the session's count after the turn. no_joke: the no-joke marker on
# the decision. disclosures_not_contain (ruling 16 of 3 October 2026): substrings
# no attached line may carry. claim_subject: the decision's claim_subject
# (self, other or null), which DeepSeek's round-3B trajectory asserts.
TRAJECTORY_ONLY_EXPECT = {"aftermath", "no_joke", "disclosures_not_contain", "claim_subject"}
# The five invariants, named for what each measures (ruling 17 of 3 October 2026).
INVARIANTS = {
    "latch_tier_never_lowers",
    "aftermath_counts_down_on_substantive_turns_only",
    "clearance_or_published_expiry_only",
    "one_card_object_per_escalating_decision",
    "no_seat_resolves_by_id_order",
}
# The names the format carried before 3 October 2026, refused with the new name
# in the message so a reviewer's file can be ported by hand.
RENAMED_INVARIANTS = {
    "restrictions_never_weaken_without_clearance": "latch_tier_never_lowers",
    "message_text_never_clears": "clearance_or_published_expiry_only",
    "one_card_per_event": "one_card_object_per_escalating_decision",
}
MARKERS = ("known_gap", "disputed", "contract_adjusted")
AUTHORSHIP = {"human", "model", "mixed"}
ID_PATTERN = re.compile(r"^(?:[a-z0-9]+(?:-[a-z0-9]+)*-)?traj-[a-z0-9][a-z0-9-]*$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def texts_digest(turns: list[dict]) -> str:
    """The SHA-256 of the turn texts in order, over their JSON list form."""
    texts = [turn.get("text", "") if isinstance(turn, dict) else "" for turn in turns]
    payload = json.dumps(texts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, dict]:
    """The register of digests known to be model-written, keyed by digest.

    One row per line, tab-separated: the digest, the ids that carry these
    texts (comma-separated), who wrote the texts, the day recorded. Lines
    starting with ``#`` are the register's own notes.
    """
    if not path.is_file():
        return {}
    registry: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        columns = line.rstrip("\n").split("\t")
        digest = columns[0].strip()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{path.name}: malformed register row {line!r}")
        ids = [item.strip() for item in (columns[1] if len(columns) > 1 else "").split(",") if item.strip()]
        registry[digest] = {
            "ids": ids,
            "texts_written_by": columns[2].strip() if len(columns) > 2 else "",
            "recorded": columns[3].strip() if len(columns) > 3 else "",
        }
    return registry


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _integer(value: object) -> bool:
    # JSON booleans are not counts or turn numbers, despite bool subclassing int.
    return isinstance(value, int) and not isinstance(value, bool)


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _check_expect(expect: object, where: str, problems: list[str]) -> None:
    if not isinstance(expect, dict):
        problems.append(f"{where}: expect must be an object")
        return
    unknown = set(expect) - SINGLE_CASE_EXPECT - TRAJECTORY_ONLY_EXPECT
    if unknown:
        problems.append(f"{where}: unknown expect field(s) {sorted(unknown)}")
    if "safety" in expect and (
        not isinstance(expect["safety"], str) or expect["safety"] not in SAFETY
    ):
        problems.append(f"{where}: safety must be one of {sorted(SAFETY)}")
    if "outcome" in expect and (
        not isinstance(expect["outcome"], str) or expect["outcome"] not in OUTCOME
    ):
        problems.append(f"{where}: outcome must be one of {sorted(OUTCOME)}")
    if "aftermath" in expect and (
        not _integer(expect["aftermath"]) or expect["aftermath"] < 0
    ):
        problems.append(f"{where}: aftermath must be a non-negative integer")
    if "no_joke" in expect and not isinstance(expect["no_joke"], bool):
        problems.append(f"{where}: no_joke must be a boolean")
    if "disclosures_not_contain" in expect and not _string_list(expect["disclosures_not_contain"]):
        problems.append(f"{where}: disclosures_not_contain must be a list of non-empty substrings")
    if "claim_subject" in expect and expect["claim_subject"] not in ("self", "other", None):
        problems.append(f"{where}: claim_subject must be 'self', 'other' or null")


def _check_provenance(fx: dict, turns: list, problems: list[str], registry: dict[str, dict]) -> None:
    prov = fx.get("provenance")
    if not isinstance(prov, dict):
        problems.append("provenance must be an object")
        return
    for key in ("texts_by", "expectations_by"):
        if not isinstance(prov.get(key), str) or prov[key] not in AUTHORSHIP:
            problems.append(f"provenance.{key} must be 'human', 'model' or 'mixed'")
    if not _nonempty_text(prov.get("scenario_origin")):
        problems.append("provenance.scenario_origin must say who set the pacing and the escalation turn")
    reviewer = prov.get("reviewer")
    reviewed_on = prov.get("reviewed_on")
    if reviewer is not None and not _nonempty_text(reviewer):
        problems.append("provenance.reviewer must be a name or null")
    if reviewed_on is not None and (
        not isinstance(reviewed_on, str) or not DATE_PATTERN.match(reviewed_on)
    ):
        problems.append("provenance.reviewed_on must be a YYYY-MM-DD date or null")
    if (reviewer is None) != (reviewed_on is None):
        problems.append("provenance.reviewer and provenance.reviewed_on go together: both or neither")

    attested_everywhere = bool(turns) and all(
        isinstance(turn, dict) and turn.get("attested") is True for turn in turns
    )
    for i, turn in enumerate(turns, start=1):
        if isinstance(turn, dict) and "attested" in turn and not isinstance(turn["attested"], bool):
            problems.append(f"turn {i}: attested must be a boolean")
    computed = (
        prov.get("texts_by") == "human"
        and prov.get("expectations_by") == "human"
        and reviewer is not None
        and reviewed_on is not None
        and attested_everywhere
    )
    if prov.get("counts_toward_recall") is not computed:
        problems.append(
            "provenance.counts_toward_recall is computed (%s: texts_by human, expectations_by "
            "human, a named reviewer with a date, every turn attested); the file says %r"
            % (computed, prov.get("counts_toward_recall"))
        )

    digest = texts_digest(turns) if turns else None
    stated = prov.get("texts_digest")
    if not isinstance(stated, str) or not re.fullmatch(r"[0-9a-f]{64}", stated or ""):
        problems.append("provenance.texts_digest must be the SHA-256 hex digest of the turn texts in order")
    elif digest is not None and stated != digest:
        problems.append(
            f"provenance.texts_digest {stated[:12]}... does not match the turn texts ({digest[:12]}...); "
            "a text changed after the digest was written, or the digest was copied from another file"
        )
    if digest is not None and digest in registry and prov.get("texts_by") in ("human", "mixed"):
        known = registry[digest]
        ids = ", ".join(known.get("ids", [])) or "an earlier file"
        problems.append(
            f"provenance.texts_by {prov.get('texts_by')!r} refused: these exact turn texts are on the "
            f"model-authored register ({ids}); relabelling unchanged model text does not make it human "
            "(ruling 18 of 3 October 2026)"
        )


def _check_allowed_mismatches(fx: dict, turn_count: int, problems: list[str]) -> None:
    allowed = fx.get("allowed_mismatches")
    if allowed is None:
        return
    if not isinstance(allowed, list):
        problems.append("allowed_mismatches must be a list of {turn, fields} objects")
        return
    for entry in allowed:
        if not isinstance(entry, dict) or not _integer(entry.get("turn")) or not _string_list(entry.get("fields")):
            problems.append("allowed_mismatches entries must carry a turn number and a list of field names")
            continue
        if entry["turn"] < 1 or entry["turn"] > turn_count:
            problems.append(f"allowed_mismatches names turn {entry['turn']}, which the trajectory does not have")


def check(fx: object, registry: dict[str, dict] | None = None) -> list[str]:
    """Every refusal the format states, as a list of problems (empty means accepted)."""
    if registry is None:
        registry = load_registry()
    problems: list[str] = []
    if not isinstance(fx, dict):
        return ["trajectory must be an object"]
    if fx.get("kind") != "trajectory":
        problems.append("kind must be 'trajectory'")
    if fx.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION} (the provenance split of 3 October 2026)")
    if fx.get("plane") != "policy":
        problems.append("plane must be 'policy'")
    if fx.get("runnable_here") is not True:
        problems.append("runnable_here must be true; a trajectory is policy-plane and runs here")
    if not isinstance(fx.get("id"), str) or not ID_PATTERN.match(fx["id"]):
        problems.append("id must start with 'traj-', or with a family prefix followed by 'traj-'")
    if not _nonempty_text(fx.get("why")):
        problems.append("top-level why is required")

    turns = fx.get("turns")
    if not isinstance(turns, list):
        problems.append("turns must be a list")
        turns = []
    if not turns:
        problems.append("at least one turn is required")
    _check_provenance(fx, turns, problems, registry)

    any_turn_expect = False
    escalating: list[int] = []
    originals = 0
    for i, t in enumerate(turns, start=1):
        where = f"turn {i}"
        if not isinstance(t, dict) or "text" not in t or not isinstance(t["text"], str):
            problems.append(f"{where}: text must be a string (empty is allowed)")
            continue
        exp = t.get("expect")
        if "expect" in t:
            any_turn_expect = any_turn_expect or (isinstance(exp, dict) and bool(exp))
            _check_expect(exp, where, problems)
            if not _nonempty_text(t.get("why")):
                problems.append(f"{where}: a turn with an expect must say why")
            if isinstance(exp, dict) and exp.get("safety") == "HUMAN_ESCALATION":
                escalating.append(i)
        if "original_expect" in t:
            originals += 1
            _check_expect(t["original_expect"], f"{where} (original_expect)", problems)
            if fx.get("contract_adjusted") is not True:
                problems.append(f"{where}: original_expect is only legal on a contract-adjusted trajectory")
        if "dispute_note" in t and not _nonempty_text(t["dispute_note"]):
            problems.append(f"{where}: a turn-level dispute_note must be non-empty text")

    texp = fx.get("trajectory_expect", {})
    if not isinstance(texp, dict):
        problems.append("trajectory_expect must be an object")
        texp = {}
    first = texp.get("first_escalation_turn")
    if "first_escalation_turn" in texp:
        if not isinstance(first, int) or not _integer(first) or first < 1 or first > len(turns):
            problems.append("trajectory_expect.first_escalation_turn must be a 1-based turn number")
            first = None
        else:
            early = [n for n in escalating if n < first]
            if early:
                problems.append(f"turn(s) {early} expect HUMAN_ESCALATION before the declared first escalation turn {first}")
            if escalating and first not in escalating:
                problems.append(f"turn {first} is declared the first escalation but no turn expects HUMAN_ESCALATION there")
    esc = texp.get("escalation_turns")
    if "escalation_turns" in texp:
        if not isinstance(esc, list) or any(
            not _integer(n) or n < 1 or n > len(turns) for n in esc
        ):
            problems.append("trajectory_expect.escalation_turns must be a list of turn numbers")
        elif first is not None and first not in esc:
            problems.append("trajectory_expect.escalation_turns must include first_escalation_turn")
    if "cards_total" in texp and (
        not _integer(texp["cards_total"]) or texp["cards_total"] < 0
    ):
        problems.append("trajectory_expect.cards_total must be a non-negative integer")
    invariants = texp.get("invariants", [])
    if not isinstance(invariants, list):
        problems.append("trajectory_expect.invariants must be a list")
        invariants = []
    for name in invariants:
        if isinstance(name, str) and name in RENAMED_INVARIANTS:
            problems.append(
                f"invariant {name!r} was renamed {RENAMED_INVARIANTS[name]!r} on 3 October 2026 (ruling 17)"
            )
        elif not isinstance(name, str) or name not in INVARIANTS:
            problems.append(f"unknown invariant {name!r}")
    if first is None and not invariants and not any_turn_expect:
        problems.append("expectation-free: no first_escalation_turn, no invariants, no per-turn expect")

    for marker in MARKERS:
        if marker in fx and not isinstance(fx[marker], bool):
            problems.append(f"{marker} must be a boolean")
    if fx.get("known_gap") is True and not _nonempty_text(fx.get("gap_note")):
        problems.append("a known_gap trajectory must say in gap_note which turn fails and why")
    if fx.get("disputed") is True and not _nonempty_text(fx.get("dispute_note")):
        problems.append("a disputed trajectory must carry dispute_note")
    if fx.get("contract_adjusted") is True:
        if not _nonempty_text(fx.get("adjust_note")):
            problems.append("a contract-adjusted trajectory must carry adjust_note")
        if originals == 0:
            problems.append("a contract-adjusted trajectory must keep at least one original_expect")
    _check_allowed_mismatches(fx, len(turns), problems)
    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    status = 0
    registry = load_registry()
    for arg in argv:
        path = Path(arg)
        problems = check(json.loads(path.read_text(encoding="utf-8")), registry)
        if problems:
            status = 1
            print(f"{path}: REFUSED")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"{path}: accepted")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
