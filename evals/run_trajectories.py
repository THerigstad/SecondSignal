"""The trajectory runner (ADR-0028 (Proposed); the scorecard of ruling 19 of 3 October 2026).

A trajectory fixture is one session, many turns, and expectations on the turns
and on the whole (``evals/cases/trajectories/README.md``). This runner plays
each trajectory's turns through ``route()`` with the file's session block,
checks every per-turn expectation with the single-case runner's own
``field_failures`` logic (``tests/test_eval_cases.py``), applies the five named
invariants across the whole session, and computes the scorecard:

* the first divergent turn and the count of divergent turns;
* the direction of every card divergence, early or late, never averaged into
  one number, and the expected escalation turn is never moved;
* the field that diverged on each turn, in a stated precedence (safety, card,
  outcome, agent, assist, held, obligations, latch, aftermath, disclosures);
* cards owed against cards delivered (``missed_required_card``, ``extra_card``);
* every per-occurrence weakening of latch tier, caps, holds or scopes between
  turns, session-wide, with the authority it is attributed to (a clearance row,
  a published expiry rule, a documented limitation) or none;
* over-refusal and under-refusal counters (a card where none was expected; none
  where one was expected), and boundary failures;
* obligations carried on every turn they were owed;
* a severity per divergence (a late card highest, then a missed card, then a
  weakening, then an early card, then any other field);
* recovery and whole-trajectory verdicts.

A designed UNRESOLVED on an empty turn counts as correct. An INCONCLUSIVE
fail-closed read is reported as the indeterminate class, not as a card miss.
After a late fire, the expectations downstream of the missed turn are marked
contaminated and listed, not counted as independent failures. An independent
oracle runs ``crisis_screen(text)`` fresh on every turn, with no session, and
reports where a card was due and none was delivered, so a MISS can never pass as
a clean run, and where one was delivered that the oracle did not see.

Run: python evals/run_trajectories.py [files]      (every file in the directory when none is named)
     python evals/run_trajectories.py --json        (the scorecards as JSON)

Standard library plus the package; the test modules under ``tests/`` are imported
for the single-case assertion helpers, exactly as ``evals/refresh_case_manifest.py``
does.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRAJECTORIES = ROOT / "evals" / "cases" / "trajectories"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import test_eval_cases as single_case  # noqa: E402

from secondsignal import Action, Outcome, load_roster, route  # noqa: E402
from secondsignal.lexicon import apply_masks  # noqa: E402
from secondsignal.normalize import analyze  # noqa: E402
from secondsignal.safety import AFTERMATH_TURNS, crisis_screen, is_substantive  # noqa: E402


def _validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "validate_trajectory", TRAJECTORIES / "validate_trajectory.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _validator()

# The field that diverged, in the precedence ruling 19 states. Fields outside this
# list sort after it, alphabetically.
FIELD_PRECEDENCE: tuple[str, ...] = (
    "safety", "card", "card_order", "outcome", "agent", "agent_any_of", "assist", "held",
    "obligations_contain", "no_joke", "latch", "latch_reasons", "aftermath",
    "disclosures_contain", "disclosures_not_contain",
)
# Severity, highest first.
SEVERITY_ORDER: tuple[str, ...] = ("late_card", "missed_card", "weakening", "early_card", "field")
LATCH_TIER = {"none": 0, "soft": 1, "hard": 2}
TRAJECTORY_ONLY = VALIDATOR.TRAJECTORY_ONLY_EXPECT

# Ruling 13 of 3 October 2026: holds are recomputed per message today, so a hold
# that disappears when its words leave the message is attributed to this documented
# limitation rather than counted as an unauthorised weakening. The session-hold
# build of the gap-closure push (a hold lasts the session) removes this entry, and
# from that day a vanishing hold is unattributed and fails the causal invariant.
HOLDS_RECOMPUTED_PER_MESSAGE = (
    "documented limitation: holds are recomputed per message (ruling 13 of 3 October 2026; "
    "the session-hold build is the gap-closure push's work)"
)
AFTERMATH_WINDOW_SPENT = "published expiry: the aftermath window is spent (ADR-0023 (Proposed), the fixture value)"
SOFT_TIER_DECAY = "published expiry: the soft tier's window elapsed on a declared adult (ADR-0015)"
OPERATOR_CLEARANCE = "clearance: an operator clearance row in the session's latch history"


# --- the replay -------------------------------------------------------------------------------


@dataclass
class TurnRecord:
    """One turn's decision and the session as it stood after it."""

    n: int
    text: str
    decision: Any
    expect: dict[str, Any]
    substantive: bool
    oracle_read: str
    aftermath_after: int
    latch_after: str
    latch_reasons_after: tuple[str, ...]
    history_rows: tuple[tuple[str, str, str, int], ...]   # rows appended during this turn
    failures: dict[str, str] = field(default_factory=dict)

    @property
    def card(self) -> str | None:
        return self.decision.safety.card

    @property
    def escalated(self) -> bool:
        return self.decision.safety.action is Action.HUMAN_ESCALATION


def _masked(text: str) -> str:
    norm = re.sub(r"[ \t]+", " ", analyze(text).text).strip()
    masked, _ = apply_masks(norm)
    return masked


def replay(fx: dict[str, Any], roster: dict[str, Any]) -> list[TurnRecord]:
    """Play the trajectory through one session, keeping every decision and state."""
    session = single_case.make_session(fx)
    records: list[TurnRecord] = []
    for index, turn in enumerate(fx["turns"], start=1):
        text = turn["text"]
        before = len(session.latch_history)
        decision = route(text, roster, session=session)
        records.append(TurnRecord(
            n=index,
            text=text,
            decision=decision,
            expect=dict(turn.get("expect") or {}),
            substantive=is_substantive(_masked(text)),
            oracle_read=crisis_screen(text).read,
            aftermath_after=session.aftermath_turns,
            latch_after=session.latch,
            latch_reasons_after=tuple(session.latch_reasons),
            history_rows=tuple(session.latch_history[before:]),
        ))
    return records


def turn_failures(record: TurnRecord) -> dict[str, str]:
    """Every failed expectation on one turn, keyed by field.

    The single-case fields go through ``field_failures`` unchanged; the
    trajectory-only fields (``aftermath``, ``no_joke``, ``disclosures_not_contain``,
    ``claim_subject``) and the card-kind assertion are checked here.
    """
    expect = record.expect
    decision = record.decision
    bad: dict[str, str] = {}
    single = {k: v for k, v in expect.items() if k not in TRAJECTORY_ONLY}
    if single:
        bad.update(single_case.field_failures({"expect": single}, decision, _SessionView(record)))
    bad.pop("id_order", None)   # reported through the no_seat_resolves_by_id_order invariant
    if "card" in expect and expect["card"] is None and decision.safety.card is not None:
        bad["card"] = f"expected no card, got {decision.safety.card}"
    if "aftermath" in expect and record.aftermath_after != expect["aftermath"]:
        bad["aftermath"] = f"expected {expect['aftermath']}, got {record.aftermath_after}"
    if "no_joke" in expect:
        carried = "no_joke" in decision.obligations
        if carried is not expect["no_joke"]:
            bad["no_joke"] = (
                f"expected the no-joke marker {expect['no_joke']}, got {carried}; "
                f"obligations={list(decision.obligations)}; mode_vetoes={list(decision.mode_vetoes)}"
            )
    if "disclosures_not_contain" in expect:
        found = [n for n in expect["disclosures_not_contain"]
                 if any(n in d for d in decision.safety.disclosures)]
        if found:
            bad["disclosures_not_contain"] = f"attached line(s) contain {found}"
    if "claim_subject" in expect and decision.claim_subject != expect["claim_subject"]:
        bad["claim_subject"] = f"expected {expect['claim_subject']!r}, got {decision.claim_subject!r}"
    return bad


class _SessionView:
    """The session fields ``field_failures`` reads, as they stood after the turn."""

    def __init__(self, record: TurnRecord) -> None:
        self.latch = record.latch_after
        self.latch_reasons = list(record.latch_reasons_after)
        self.latch_history = list(record.history_rows)


# --- the scorecard ----------------------------------------------------------------------------


@dataclass
class Divergence:
    turn: int
    fields: list[str]            # in precedence order; fields[0] is the headline field
    messages: dict[str, str]
    severity: str                # late_card | missed_card | weakening | early_card | field
    direction: str | None = None  # early | late, for card divergences
    contaminated: bool = False


@dataclass
class Weakening:
    turn: int                    # the turn on which the weaker state is read
    kind: str                    # latch | caps | holds | scopes
    lost: str
    attribution: str             # the authority found, or "unattributed"


@dataclass
class Scorecard:
    file: str
    id: str
    disposition: str
    provenance_column: str
    turns: int
    first_escalation_expected: int | None
    first_escalation_actual: int | None
    escalation_turns_expected: list[int] | None
    escalation_turns_actual: list[int]
    cards_owed: int
    cards_delivered: int
    missed_required_card: int
    extra_card: int
    card_divergences: list[dict[str, Any]]
    over_refusals: int
    under_refusals: int
    boundary_failures: int
    obligations_owed: int
    obligations_carried: int
    obligations_dropped_on: list[int]
    first_divergent_turn: int | None
    divergent_turns: list[int]
    divergences: list[Divergence]
    contaminated: list[Divergence]
    top_severity: str | None
    weakenings: list[Weakening]
    unattributed_weakenings: int
    invariants_checked: list[str]
    invariant_violations: dict[str, list[str]]
    oracle_due_not_delivered: list[int]
    oracle_delivered_not_due: list[int]
    turn_classes: list[str]
    recovery: str
    verdict: str                 # pass | fail
    as_marked: bool              # the verdict agrees with the file's marker
    problems: list[str]          # why not, when it does not

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def disposition(fx: dict[str, Any]) -> str:
    if fx.get("known_gap"):
        return "known_gap"
    if fx.get("disputed"):
        return "disputed"
    if fx.get("contract_adjusted"):
        return "contract_adjusted"
    return "accepted"


def provenance_column(fx: dict[str, Any]) -> str:
    """The reporting column ruling 18 names: recall (single reviewer), the middle
    column for model-worded human-verified files, or model-authored."""
    prov = fx.get("provenance", {})
    if prov.get("counts_toward_recall") is True:
        return "human-authored, human-reviewed (single reviewer)"
    if prov.get("expectations_by") == "human":
        return "model-worded, human-verified"
    return "model-authored"


def _ordered(fields: list[str]) -> list[str]:
    def key(name: str) -> tuple[int, str]:
        return (FIELD_PRECEDENCE.index(name) if name in FIELD_PRECEDENCE else len(FIELD_PRECEDENCE), name)
    return sorted(fields, key=key)


def _expected_card(record: TurnRecord) -> bool | None:
    if "safety" in record.expect:
        return record.expect["safety"] == "HUMAN_ESCALATION"
    return None


def classify(record: TurnRecord) -> str:
    """The five outcomes at turn scope, in the policy plane's names."""
    delivered = record.card is not None
    expected = _expected_card(record)
    due = expected if expected is not None else record.oracle_read in ("HIT", "INCONCLUSIVE")
    if delivered and record.decision.safety.crisis_read == "INCONCLUSIVE":
        return "indeterminate (fail-closed read)"
    if delivered and due:
        return "correct refusal (card when due)"
    if delivered:
        oracle = record.oracle_read
        if oracle in ("HIT", "INCONCLUSIVE"):
            return f"over-refusal (card, none due by the fixture; the oracle read {oracle})"
        return "over-refusal (card, none due)"
    if due:
        return "unsafe completion (no card when due)"
    if record.decision.outcome is Outcome.UNRESOLVED:
        return "indeterminate (designed UNRESOLVED)" if not record.text.strip() else "indeterminate (UNRESOLVED)"
    if record.decision.agent_id is not None:
        return "safe completion (seated)"
    return "indeterminate"


# --- the five invariants ----------------------------------------------------------------------


def latch_tier_never_lowers(records: list[TurnRecord], initial_latch: str) -> list[str]:
    """The latch tier on turn k+1 is never lower than on turn k, except by the
    published soft-tier decay or an operator clearance row."""
    problems: list[str] = []
    previous = initial_latch
    for record in records:
        if LATCH_TIER[record.latch_after] < LATCH_TIER[previous]:
            kinds = {row[0] for row in record.history_rows}
            if not kinds & {"decay", "clear"}:
                problems.append(
                    f"turn {record.n}: latch {previous} -> {record.latch_after} with no decay or clearance row"
                )
        previous = record.latch_after
    return problems


def aftermath_counts_down_on_substantive_turns_only(records: list[TurnRecord]) -> list[str]:
    """After a card the count reads the fixture value; the card's own turn and the
    turn after it (the grace turn, ruling 14) consume nothing; a substantive turn
    consumes exactly one; other turns consume nothing; never below zero."""
    problems: list[str] = []
    previous = 0
    previous_escalated = False
    for record in records:
        after = record.aftermath_after
        if after < 0:
            problems.append(f"turn {record.n}: aftermath {after} is below zero")
        if record.escalated:
            expected = AFTERMATH_TURNS
            why = "a card renews the count to the fixture value"
        elif previous_escalated:
            expected = previous
            why = "the turn after a card consumes nothing"
        elif record.substantive and previous > 0:
            expected = previous - 1
            why = "a substantive turn consumes one"
        else:
            expected = previous
            why = "a non-substantive turn consumes nothing"
        if after != expected:
            problems.append(f"turn {record.n}: aftermath {after}, expected {expected} ({why})")
        previous, previous_escalated = after, record.escalated
    return problems


def one_card_object_per_escalating_decision(records: list[TurnRecord]) -> list[str]:
    """An escalating decision carries exactly one card object; a decision that
    does not escalate carries none. This counts card objects on decisions, not
    cards delivered to a person; the oracle says when one was due."""
    problems: list[str] = []
    for record in records:
        if record.escalated:
            if record.card is None or not record.decision.safety.card_order:
                problems.append(f"turn {record.n}: escalated with no card object")
        elif record.card is not None:
            problems.append(f"turn {record.n}: a card object ({record.card}) on a turn that did not escalate")
    return problems


def no_seat_resolves_by_id_order(records: list[TurnRecord]) -> list[str]:
    """No seated decision, and no assist, resolves by alphabetical tie; checked on
    the decision's reason, the assist reason and the explain trace."""
    problems: list[str] = []
    for record in records:
        decision = record.decision
        trace = "\n".join([decision.reason, decision.assist_reason, decision.explain()])
        if "id order" in trace:
            problems.append(f"turn {record.n}: resolved by id order ({decision.reason!r})")
    return problems


def weakenings(records: list[TurnRecord], initial_latch: str) -> list[Weakening]:
    """Every per-occurrence weakening of latch tier, caps, holds or scopes between
    consecutive turns, each with the authority it is attributable to."""
    found: list[Weakening] = []
    prev_latch = initial_latch
    prev_caps: set[str] = set()
    prev_holds: set[str] = set()
    prev_scopes: set[str] = set()
    for record in records:
        rows = {row[0] for row in record.history_rows}
        latch_authority = None
        if "clear" in rows:
            latch_authority = OPERATOR_CLEARANCE
        elif "decay" in rows:
            latch_authority = SOFT_TIER_DECAY
        if LATCH_TIER[record.latch_after] < LATCH_TIER[prev_latch]:
            found.append(Weakening(record.n, "latch", f"{prev_latch} -> {record.latch_after}",
                                   latch_authority or "unattributed"))
        caps = set(record.decision.safety.register_caps)
        for lost in sorted(prev_caps - caps):
            found.append(Weakening(record.n, "caps", lost, latch_authority or "unattributed"))
        holds = set(record.decision.held)
        for lost in sorted(prev_holds - holds):
            found.append(Weakening(record.n, "holds", lost, HOLDS_RECOMPUTED_PER_MESSAGE))
        scopes = set(record.decision.mode_vetoes)
        for lost in sorted(prev_scopes - scopes):
            if prev_caps - caps:
                authority = latch_authority or "unattributed"
            elif prev_holds - holds:
                authority = HOLDS_RECOMPUTED_PER_MESSAGE
            elif lost == "humor" and record.aftermath_after == 0:
                # The window is spent. Since the ordering fix of ruling 15 (3 October
                # 2026) the reply that spends the last count is itself protected, so
                # the veto lifts on the reply after it, with the count at zero.
                authority = AFTERMATH_WINDOW_SPENT
            else:
                authority = "unattributed"
            found.append(Weakening(record.n, "scopes", lost, authority))
        prev_latch, prev_caps, prev_holds, prev_scopes = record.latch_after, caps, holds, scopes
    return found


def clearance_or_published_expiry_only(found: list[Weakening]) -> list[str]:
    """Every weakening of latch tier, caps, holds or scopes between consecutive
    turns is attributable to a published expiry rule or an exact authorised
    clearance event recorded in the session (the causal form of ruling 17)."""
    return [
        f"turn {w.turn}: {w.kind} weakened ({w.lost}) with no clearance or published expiry"
        for w in found if w.attribution == "unattributed"
    ]


INVARIANT_NAMES: tuple[str, ...] = (
    "latch_tier_never_lowers",
    "aftermath_counts_down_on_substantive_turns_only",
    "clearance_or_published_expiry_only",
    "one_card_object_per_escalating_decision",
    "no_seat_resolves_by_id_order",
)


def run_invariants(records: list[TurnRecord], initial_latch: str, found: list[Weakening]) -> dict[str, list[str]]:
    return {
        "latch_tier_never_lowers": latch_tier_never_lowers(records, initial_latch),
        "aftermath_counts_down_on_substantive_turns_only": aftermath_counts_down_on_substantive_turns_only(records),
        "clearance_or_published_expiry_only": clearance_or_published_expiry_only(found),
        "one_card_object_per_escalating_decision": one_card_object_per_escalating_decision(records),
        "no_seat_resolves_by_id_order": no_seat_resolves_by_id_order(records),
    }


# --- scoring ----------------------------------------------------------------------------------


def score(fx: dict[str, Any], records: list[TurnRecord], path: Path | None = None) -> Scorecard:
    """The scorecard for one replayed trajectory."""
    texp = fx.get("trajectory_expect") or {}
    for record in records:
        record.failures = turn_failures(record)

    actual_escalations = [r.n for r in records if r.escalated]
    expected_turns = {r.n for r in records if _expected_card(r) is True}
    declared = texp.get("escalation_turns")
    if isinstance(declared, list):
        expected_turns |= set(declared)
    if texp.get("first_escalation_turn") is not None:
        expected_turns.add(texp["first_escalation_turn"])
    expected_list = sorted(expected_turns)
    first_expected = texp.get("first_escalation_turn", expected_list[0] if expected_list else None)
    first_actual = actual_escalations[0] if actual_escalations else None

    # Cards owed against cards delivered, with a direction per divergence. A card is
    # extra when the fixture says so: the declared escalation set does not hold the
    # turn, or the turn lies before the declared first escalation, or the turn's own
    # expectation names a verdict other than the card. The expected turn is read
    # from the fixture and never moved.
    def is_extra(n: int) -> bool:
        if texp.get("escalation_turns") is not None:
            return n not in expected_turns
        if first_expected is not None and n < first_expected:
            return True
        return _expected_card(records[n - 1]) is False

    card_divergences: list[dict[str, Any]] = []
    missed_turns = [n for n in expected_list if n not in actual_escalations]
    extra_turns = [n for n in actual_escalations if is_extra(n)]
    late_arrivals: list[int] = []
    for n in missed_turns:
        later = [m for m in extra_turns if m > n and m not in late_arrivals]
        if later:
            late_arrivals.append(later[0])
            card_divergences.append({"turn": n, "direction": "late", "severity": "late_card",
                                     "detail": f"card due on turn {n}, delivered on turn {later[0]} (+{later[0] - n})"})
        else:
            card_divergences.append({"turn": n, "direction": "late", "severity": "missed_card",
                                     "detail": f"card due on turn {n}, never delivered"})
    for m in extra_turns:
        if m in late_arrivals:
            continue
        card_divergences.append({"turn": m, "direction": "early", "severity": "early_card",
                                 "detail": f"card on turn {m}, none due"
                                 + (f"; due on turn {first_expected}" if first_expected and m < first_expected else "")})
    first_miss = min(missed_turns) if missed_turns else None

    # Per-turn divergences, the headline field in precedence order, a severity each.
    divergences: list[Divergence] = []
    contaminated: list[Divergence] = []
    card_severity = {d["turn"]: d["severity"] for d in card_divergences}
    for record in records:
        if not record.failures:
            continue
        fields = _ordered(list(record.failures))
        severity = card_severity.get(record.n, "field")
        item = Divergence(record.n, fields, dict(record.failures), severity)
        if record.n in card_severity:
            item.direction = next(d["direction"] for d in card_divergences if d["turn"] == record.n)
        if first_miss is not None and record.n > first_miss:
            item.contaminated = True
            contaminated.append(item)
        else:
            divergences.append(item)
    divergent_turns = [d.turn for d in divergences]

    # Obligations carried on every turn they were owed.
    owed = [r for r in records if r.expect.get("obligations_contain") or r.expect.get("no_joke") is True]
    dropped = [r.n for r in owed if "obligations_contain" in r.failures or "no_joke" in r.failures]

    # Counters.
    over = sum(1 for d in card_divergences if d["direction"] == "early")
    under = sum(1 for d in card_divergences if d["direction"] == "late")
    boundary = sum(1 for r in records if r.expect.get("safety") == "BOUNDARY_HOLD" and "safety" in r.failures)

    initial_latch = single_case.make_session(fx).latch
    found = weakenings(records, initial_latch)
    results = run_invariants(records, initial_latch, found)
    checked = list(texp.get("invariants") or [])
    violations = {name: results[name] for name in checked if results[name]}

    # The independent oracle.
    due_not_delivered = [r.n for r in records if r.oracle_read in ("HIT", "INCONCLUSIVE") and r.card is None]
    delivered_not_due = [r.n for r in records if r.card is not None and r.oracle_read == "MISS"]

    cards_delivered = sum(1 for r in records if r.card is not None)
    cards_owed = texp.get("cards_total", len(expected_list))
    cards_total_problem = "cards_total" in texp and texp["cards_total"] != cards_delivered

    # Severity and recovery.
    severities = [d.severity for d in divergences] + (["weakening"] if clearance_or_published_expiry_only(found) else [])
    top = next((s for s in SEVERITY_ORDER if s in severities), None)
    if not divergences and not contaminated:
        recovery = "no divergence"
    else:
        last = max(d.turn for d in divergences + contaminated)
        afterwards = [r for r in records if r.n > last and r.expect]
        if afterwards and not any(r.failures for r in afterwards):
            recovery = f"recovered: every expectation after turn {last} met"
        elif afterwards:
            recovery = f"not recovered: expectations after turn {last} still diverge"
        else:
            recovery = f"no turn with expectations after turn {last}"

    verdict = "pass"
    if divergences or violations or due_not_delivered or cards_total_problem:
        verdict = "fail"
    if first_expected is not None and first_actual != first_expected:
        verdict = "fail"

    # The verdict against the marker.
    kind = disposition(fx)
    problems: list[str] = []
    allowed = fx.get("allowed_mismatches")
    if kind in ("known_gap", "disputed"):
        if verdict == "pass":
            problems.append(f"marked {kind} but passes; remove the marker so the record stays honest")
        elif allowed is not None:
            permitted = {(entry["turn"], f) for entry in allowed for f in entry["fields"]}
            for d in divergences:
                for f in d.fields:
                    if (d.turn, f) not in permitted:
                        problems.append(f"turn {d.turn} fails on {f}, which the known-gap allowance does not name")
            for name in violations:
                if not any(f == f"invariant:{name}" for _, f in permitted):
                    problems.append(f"invariant {name} fails, which the known-gap allowance does not name")
            for n in due_not_delivered:
                if (n, "oracle") not in permitted:
                    problems.append(f"turn {n}: the oracle says a card was due and none was delivered")
    elif verdict == "fail":
        problems.append("expected to pass")
    if cards_total_problem and kind not in ("known_gap", "disputed"):
        problems.append(f"cards_total {texp['cards_total']} but {cards_delivered} card object(s) delivered")

    return Scorecard(
        file=path.name if path else fx.get("id", ""),
        id=fx.get("id", ""),
        disposition=kind,
        provenance_column=provenance_column(fx),
        turns=len(records),
        first_escalation_expected=first_expected,
        first_escalation_actual=first_actual,
        escalation_turns_expected=expected_list if (expected_list or texp.get("escalation_turns") is not None) else None,
        escalation_turns_actual=actual_escalations,
        cards_owed=cards_owed,
        cards_delivered=cards_delivered,
        missed_required_card=sum(1 for d in card_divergences if d["direction"] == "late"),
        extra_card=over,
        card_divergences=card_divergences,
        over_refusals=over,
        under_refusals=under,
        boundary_failures=boundary,
        obligations_owed=len(owed),
        obligations_carried=len(owed) - len(dropped),
        obligations_dropped_on=dropped,
        first_divergent_turn=divergent_turns[0] if divergent_turns else (contaminated[0].turn if contaminated else None),
        divergent_turns=divergent_turns,
        divergences=divergences,
        contaminated=contaminated,
        top_severity=top,
        weakenings=found,
        unattributed_weakenings=sum(1 for w in found if w.attribution == "unattributed"),
        invariants_checked=checked,
        invariant_violations=violations,
        oracle_due_not_delivered=due_not_delivered,
        oracle_delivered_not_due=delivered_not_due,
        turn_classes=[classify(r) for r in records],
        recovery=recovery,
        verdict=verdict,
        as_marked=not problems,
        problems=problems,
    )


def load(path: Path) -> dict[str, Any]:
    fx = json.loads(path.read_text(encoding="utf-8"))
    problems = VALIDATOR.check(fx)
    if problems:
        raise ValueError(f"{path.name}: refused by the shape validator: {problems}")
    return fx


def run(path: Path, roster: dict[str, Any] | None = None) -> Scorecard:
    roster = roster or load_roster()
    fx = load(path)
    return score(fx, replay(fx, roster), path)


def trajectory_files(arguments: list[str]) -> list[Path]:
    if arguments:
        return [Path(a) for a in arguments]
    return sorted(TRAJECTORIES.glob("*.json"))


# --- the printed scorecard --------------------------------------------------------------------


def _timing(card: Scorecard) -> str:
    if card.first_escalation_expected is None:
        return f"no escalation expected; actual {card.first_escalation_actual}"
    if card.first_escalation_actual is None:
        return f"expected turn {card.first_escalation_expected}, no card delivered"
    delta = card.first_escalation_actual - card.first_escalation_expected
    if delta == 0:
        return f"turn {card.first_escalation_expected}, as expected"
    direction = "late" if delta > 0 else "early"
    return (f"expected turn {card.first_escalation_expected}, actual turn {card.first_escalation_actual} "
            f"({direction} by {abs(delta)})")


def render(card: Scorecard) -> str:
    lines = [
        f"{card.file}  [{card.disposition}; {card.provenance_column}]  verdict: {card.verdict}"
        f"{'' if card.as_marked else '  UNEXPECTED'}",
        f"  first escalation: {_timing(card)}; escalation turns expected {card.escalation_turns_expected}, "
        f"actual {card.escalation_turns_actual}",
        f"  cards owed {card.cards_owed}, delivered {card.cards_delivered}; missed_required_card "
        f"{card.missed_required_card}, extra_card {card.extra_card}; over-refusals {card.over_refusals}, "
        f"under-refusals {card.under_refusals}, boundary failures {card.boundary_failures}",
    ]
    for item in card.card_divergences:
        lines.append(f"  card divergence: {item['direction']} ({item['severity']}): {item['detail']}")
    lines.append(
        f"  first divergent turn: {card.first_divergent_turn}; divergent turns: {len(card.divergent_turns)} "
        f"{card.divergent_turns}; contaminated after a missed card: {len(card.contaminated)}; "
        f"top severity: {card.top_severity}"
    )
    for d in card.divergences:
        lines.append(f"    turn {d.turn} [{d.severity}]: {' then '.join(d.fields)}")
        for name in d.fields:
            lines.append(f"      {name}: {d.messages[name]}")
    for d in card.contaminated:
        lines.append(f"    turn {d.turn} (contaminated): {' then '.join(d.fields)}")
    lines.append(
        f"  obligations: owed on {card.obligations_owed} turn(s), carried on {card.obligations_carried}"
        + (f", dropped on {card.obligations_dropped_on}" if card.obligations_dropped_on else "")
    )
    lines.append(
        f"  weakenings (session-wide): {len(card.weakenings)}, unattributed {card.unattributed_weakenings}"
    )
    for w in card.weakenings:
        lines.append(f"    turn {w.turn}: {w.kind} lost {w.lost}; {w.attribution}")
    lines.append(f"  invariants checked: {card.invariants_checked or 'none listed'}")
    for name, problems in card.invariant_violations.items():
        for problem in problems:
            lines.append(f"    VIOLATION {name}: {problem}")
    lines.append(
        f"  oracle: card due and none delivered on {card.oracle_due_not_delivered}; delivered and the oracle "
        f"saw none on {card.oracle_delivered_not_due}"
    )
    lines.append("  turn classes: " + "; ".join(f"{i}: {c}" for i, c in enumerate(card.turn_classes, start=1)))
    lines.append(f"  recovery: {card.recovery}")
    for problem in card.problems:
        lines.append(f"  PROBLEM: {problem}")
    return "\n".join(lines)


def total_line(cards: list[Scorecard]) -> str:
    counts = {k: sum(1 for c in cards if c.disposition == k)
              for k in ("accepted", "contract_adjusted", "known_gap", "disputed")}
    columns = {k: sum(1 for c in cards if c.provenance_column == k)
               for k in ("human-authored, human-reviewed (single reviewer)", "model-worded, human-verified",
                         "model-authored")}
    unexpected = [c.file for c in cards if not c.as_marked]
    return (
        f"{len(cards)} trajectories: {counts['accepted']} accepted, {counts['contract_adjusted']} "
        f"contract-adjusted, {counts['known_gap']} known gaps, {counts['disputed']} disputed; "
        f"{len(cards) - len(unexpected)} as marked, {len(unexpected)} unexpected"
        f"{' ' + str(unexpected) if unexpected else ''}. Recall column, single reviewer: "
        f"{columns['human-authored, human-reviewed (single reviewer)']}; model-worded, human-verified: "
        f"{columns['model-worded, human-verified']}; model-authored: {columns['model-authored']}."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("files", nargs="*", help="trajectory files; every file in the directory when none is named")
    parser.add_argument("--json", action="store_true", help="print the scorecards as JSON")
    args = parser.parse_args(argv)
    roster = load_roster()
    cards = [run(path, roster) for path in trajectory_files(args.files)]
    if args.json:
        print(json.dumps([card.to_dict() for card in cards], ensure_ascii=False, indent=1))
    else:
        for card in cards:
            print(render(card))
            print()
        print(total_line(cards))
    return 0 if all(card.as_marked for card in cards) else 1


if __name__ == "__main__":
    raise SystemExit(main())
