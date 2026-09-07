"""Reproduce the round-1 external-review fixture report.

The pytest fixture runner remains the executable policy contract.  This module
mirrors its session setup, prior-turn replay, and expectation checks so the
reviewer totals can be regenerated without asking pytest to format a report.
Only policy-plane documents explicitly marked ``external`` and carrying a
``reviewer`` are selected; all JSON documents are still discovered and parsed.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Sequence, TypeAlias

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
SOURCE_PATH = str(SOURCE_ROOT)
if SOURCE_PATH in sys.path:
    sys.path.remove(SOURCE_PATH)
# Direct execution makes ``evals/`` sys.path[0]. Prefer this checkout over an
# unrelated, globally installed copy so the report always measures this tree.
sys.path.insert(0, SOURCE_PATH)

from secondsignal import (  # noqa: E402
    Action,
    AgentProfile,
    Outcome,
    RoutingDecision,
    SessionState,
    load_roster,
    route,
)

CASE_DIR = PROJECT_ROOT / "evals" / "cases"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "evals"
    / "results"
    / "external-review"
    / "fixture-results-round1-2026-09-03.md"
)

INELIGIBLE_STATUSES = {"vetoed", "below_floor", "capped", "outranked"}
REVIEWER_ORDER = ("grok", "chatgpt", "deepseek", "qwen", "vibe")
REVIEWER_LABELS = {
    "grok": "Grok 4.6",
    "chatgpt": "ChatGPT",
    "deepseek": "DeepSeek",
    "qwen": "Qwen",
    "vibe": "Vibe",
}

CaseData: TypeAlias = dict[str, Any]
Roster: TypeAlias = dict[str, AgentProfile]
Status: TypeAlias = Literal[
    "pass as written", "contract-adjusted", "disputed", "known gap"
]


@dataclass(frozen=True)
class Fixture:
    """One selected external-review case and its document metadata."""

    label: str
    case_id: str
    reviewer: str
    source_path: Path
    case: CaseData


@dataclass(frozen=True)
class FixtureResult:
    """The classification and routed observation for one fixture."""

    fixture: Fixture
    expected: CaseData
    expectation_source: Literal["current", "reviewer original"]
    observed: CaseData
    status: Status
    expectation_failures: tuple[str, ...]
    validation_error: str | None
    note: str

    @property
    def matches_current_expectation(self) -> bool:
        return not self.expectation_failures


@dataclass(frozen=True)
class FixtureCounts:
    """Mutually exclusive counts after applying classification precedence."""

    total: int
    pass_as_written: int
    contract_adjusted: int
    disputed: int
    known_gap: int

    def as_dict(self) -> dict[str, int]:
        return {
            "total": self.total,
            "pass_as_written": self.pass_as_written,
            "contract_adjusted": self.contract_adjusted,
            "disputed": self.disputed,
            "known_gap": self.known_gap,
        }


@dataclass(frozen=True)
class FixtureSummary:
    """Import-friendly aggregate returned by :func:`run_fixtures`."""

    results: tuple[FixtureResult, ...]
    by_reviewer: dict[str, FixtureCounts]
    totals: FixtureCounts

    @property
    def total(self) -> int:
        return self.totals.total

    @property
    def pass_as_written(self) -> int:
        return self.totals.pass_as_written

    @property
    def contract_adjusted(self) -> int:
        return self.totals.contract_adjusted

    @property
    def disputed(self) -> int:
        return self.totals.disputed

    @property
    def known_gap(self) -> int:
        return self.totals.known_gap

    @property
    def validation_errors(self) -> tuple[str, ...]:
        return tuple(
            result.validation_error
            for result in self.results
            if result.validation_error is not None
        )

    def assert_valid(self) -> None:
        """Enforce the strict-xfail behavior used by ``test_eval_cases.py``."""
        if self.validation_errors:
            detail = "\n".join(f"- {error}" for error in self.validation_errors)
            raise AssertionError(f"fixture contract validation failed:\n{detail}")


def discover_fixtures(case_dir: Path = CASE_DIR) -> tuple[Fixture, ...]:
    """Parse every case document and select runnable external policy fixtures.

    Selection is metadata-driven rather than tied to a directory name.  A
    deferred path or document, a non-policy plane, ``runnable_here: false``, a
    non-external document, or a document without a reviewer is not runnable in
    this report.
    """
    fixtures: list[Fixture] = []
    seen_ids: set[str] = set()

    paths = sorted(case_dir.rglob("*.json"), key=lambda path: path.as_posix())
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError(f"{path}: case document must be a JSON object")

        relative_path = path.relative_to(case_dir)
        is_deferred = "deferred" in relative_path.parts or bool(document.get("deferred"))
        is_policy = document.get("plane", "policy") == "policy"
        is_runnable = document.get("runnable_here") is not False
        is_external = document.get("external") is True
        reviewer = document.get("reviewer")
        if not (
            not is_deferred
            and is_policy
            and is_runnable
            and is_external
            and isinstance(reviewer, str)
            and reviewer
        ):
            continue

        cases = document.get("cases")
        if not isinstance(cases, list):
            raise ValueError(f"{path}: selected case document has no cases list")
        document_label = relative_path.with_suffix("").as_posix()
        for raw_case in cases:
            if not isinstance(raw_case, dict):
                raise ValueError(f"{path}: every case must be a JSON object")
            if raw_case.get("deferred") or raw_case.get("runnable_here") is False:
                continue
            case_id = raw_case.get("id")
            if not isinstance(case_id, str) or not case_id:
                raise ValueError(f"{path}: every selected case needs a non-empty id")
            if case_id in seen_ids:
                raise ValueError(f"duplicate external fixture id: {case_id}")
            seen_ids.add(case_id)
            fixtures.append(
                Fixture(
                    label=f"{document_label}::{case_id}",
                    case_id=case_id,
                    reviewer=reviewer,
                    source_path=path,
                    case=raw_case,
                )
            )
    return tuple(fixtures)


def make_session(case: CaseData) -> SessionState:
    """Build only the session fields admitted by the fixture contract."""
    block = case.get("session") or {}
    if not isinstance(block, dict):
        raise ValueError(f"{case.get('id', '<unknown>')}: session must be an object")
    return SessionState(
        locale=case.get("locale"),
        declared_language=block.get("declared_language"),
        declared_age_band=block.get("declared_age_band", "unknown"),
        affinities=tuple(block.get("affinities", ())),
        preferences=dict(block.get("preferences", {})),
    )


def _prior_text(turn: object) -> str:
    if isinstance(turn, dict):
        text = turn.get("text")
    else:
        text = turn
    if not isinstance(text, str):
        raise ValueError("a prior turn must be a string or an object with string field 'text'")
    return text


def run_case(case: CaseData, roster: Roster) -> tuple[RoutingDecision, SessionState]:
    """Replay prior turns and route the final turn through one shared session."""
    session = make_session(case)
    for prior in case.get("prior_turns", []):
        route(_prior_text(prior), roster, session=session)
    text = case.get("text")
    if not isinstance(text, str):
        raise ValueError(f"{case.get('id', '<unknown>')}: text must be a string")
    return route(text, roster, session=session), session


def _decision_trace(decision: RoutingDecision) -> str:
    return " || ".join(
        [
            decision.reason,
            *decision.safety.reasons,
            decision.assist_reason,
            *(" ".join(scored.rationale) for scored in decision.ranked),
        ]
    )


def check_case(
    case: CaseData, decision: RoutingDecision, session: SessionState
) -> tuple[str, ...]:
    """Return every failure under the same assertions as ``test_eval_cases.py``."""
    expect = case["expect"]
    if not isinstance(expect, dict):
        raise ValueError(f"{case.get('id', '<unknown>')}: expect must be an object")

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    if "safety" in expect:
        require(
            decision.safety.action is Action[expect["safety"]],
            f"safety: expected {expect['safety']}, got {decision.safety.action.name}; "
            f"reasons={decision.safety.reasons}",
        )
    if "outcome" in expect:
        require(
            decision.outcome is Outcome[expect["outcome"]],
            f"outcome: expected {expect['outcome']}, got {decision.outcome.value} "
            f"({decision.reason})",
        )
    if "agent" in expect:
        require(
            decision.agent_id == expect["agent"],
            f"agent: expected {expect['agent']!r}, got {decision.agent_id!r}; "
            f"reason={decision.reason!r}; "
            f"ranked={[(s.agent_id, s.status, s.score) for s in decision.ranked]}",
        )
    if "agent_any_of" in expect:
        require(
            decision.agent_id in expect["agent_any_of"],
            f"agent: expected one of {expect['agent_any_of']}, got {decision.agent_id!r}; "
            f"reason={decision.reason!r}",
        )
    if "reason_contains" in expect:
        trace = _decision_trace(decision)
        require(
            expect["reason_contains"] in trace,
            f"reason: expected the record to contain {expect['reason_contains']!r}; "
            f"reason={decision.reason!r}; safety={decision.safety.reasons}",
        )
    if "crisis_read" in expect:
        require(
            decision.safety.crisis_read == expect["crisis_read"],
            f"crisis_read: expected {expect['crisis_read']}, "
            f"got {decision.safety.crisis_read}",
        )
    if "integrity_event" in expect:
        require(
            decision.safety.integrity_event is expect["integrity_event"],
            f"integrity_event: expected {expect['integrity_event']!r}, "
            f"got {decision.safety.integrity_event!r}",
        )
    if "disclosures_contain" in expect:
        needle = expect["disclosures_contain"]
        require(
            any(needle in disclosure for disclosure in decision.safety.disclosures),
            f"disclosures: none contains {needle!r}; got {decision.safety.disclosures}",
        )
    if "latch" in expect:
        require(
            session.latch == expect["latch"],
            f"latch: expected {expect['latch']}, got {session.latch} "
            f"({session.latch_reasons}); history={session.latch_history}",
        )
    if "latch_reasons" in expect:
        for reason in expect["latch_reasons"]:
            require(
                reason in decision.safety.latch_reasons,
                f"latch_reasons: expected {reason!r} in "
                f"{decision.safety.latch_reasons}",
            )
    if "held" in expect:
        for domain in expect["held"]:
            require(
                domain in decision.held,
                f"held: expected {domain!r} in {decision.held}",
            )
    if "assist" in expect:
        require(
            decision.assist_agent_id == expect["assist"],
            f"assist: expected {expect['assist']!r}, got "
            f"{decision.assist_agent_id!r} ({decision.assist_reason})",
        )
    if "card" in expect and expect["card"] is not None:
        require(
            decision.safety.card == expect["card"],
            f"card: expected {expect['card']}, got {decision.safety.card}",
        )
    if "preference_result" in expect:
        require(
            decision.safety.preference_result == expect["preference_result"],
            f"preference_result: expected {expect['preference_result']}, "
            f"got {decision.safety.preference_result}; reasons={decision.safety.reasons}",
        )
    if "language_scope" in expect:
        require(
            decision.safety.language_scope == expect["language_scope"],
            f"language_scope: expected {expect['language_scope']!r}, "
            f"got {decision.safety.language_scope!r}",
        )
    for agent_id in expect.get("not_seated", []):
        require(
            decision.agent_id != agent_id,
            f"{agent_id!r} was seated but must not be",
        )
        require(
            decision.assist_agent_id != agent_id,
            f"{agent_id!r} was the assist but must not be",
        )
    for needle in expect.get("obligations_contain", []):
        require(
            any(needle in obligation for obligation in decision.obligations),
            f"obligations: none contains {needle!r}; got {decision.obligations}",
        )
    statuses = {scored.agent_id: scored.status for scored in decision.ranked}
    for agent_id in expect.get("ineligible", []):
        require(
            decision.agent_id != agent_id,
            f"{agent_id!r} was seated but must be ineligible",
        )
        require(
            decision.assist_agent_id != agent_id,
            f"{agent_id!r} was the assist but must be ineligible",
        )
        if agent_id in statuses and not decision.preempted:
            require(
                statuses[agent_id] in INELIGIBLE_STATUSES,
                f"{agent_id!r} must be vetoed, below floor, capped or outranked "
                f"in the trace; status={statuses[agent_id]!r}",
            )
    require(
        "id order" not in decision.reason,
        f"a labeled case must never resolve by id order: {decision.reason!r}",
    )
    return tuple(failures)


def classify_case(case: CaseData) -> Status:
    """Apply mutually exclusive precedence: gap, dispute, adjustment, pass."""
    if case.get("known_gap"):
        return "known gap"
    if case.get("disputed"):
        return "disputed"
    if case.get("contract_adjusted"):
        return "contract-adjusted"
    return "pass as written"


def _observed_fields(
    expectation: CaseData, decision: RoutingDecision, session: SessionState
) -> CaseData:
    """Project real record values corresponding to a displayed expectation."""
    observed: CaseData = {
        "safety": decision.safety.action.name,
        "outcome": decision.outcome.value,
        "agent": decision.agent_id,
    }
    if "agent_any_of" in expectation:
        observed["agent_any_of"] = decision.agent_id
    if "reason_contains" in expectation or "reason_ contains" in expectation:
        observed["reason_trace"] = _decision_trace(decision)
    if "crisis_read" in expectation:
        observed["crisis_read"] = decision.safety.crisis_read
    if "integrity_event" in expectation:
        observed["integrity_event"] = decision.safety.integrity_event
    if "disclosures_contain" in expectation:
        observed["disclosures"] = list(decision.safety.disclosures)
    if "latch" in expectation:
        observed["latch"] = session.latch
    if "latch_reasons" in expectation:
        observed["latch_reasons"] = list(decision.safety.latch_reasons)
    if "held" in expectation:
        observed["held"] = list(decision.held)
    if "assist" in expectation or "not_seated" in expectation or "ineligible" in expectation:
        observed["assist"] = decision.assist_agent_id
    if "card" in expectation:
        observed["card"] = decision.safety.card
    if "preference_result" in expectation:
        observed["preference_result"] = decision.safety.preference_result
    if "language_scope" in expectation:
        observed["language_scope"] = decision.safety.language_scope
    if "obligations_contain" in expectation:
        observed["obligations"] = list(decision.obligations)
    named_agents = [
        *expectation.get("ineligible", []),
        *expectation.get("not_seated", []),
    ]
    if named_agents:
        statuses = {scored.agent_id: scored.status for scored in decision.ranked}
        observed["named_agent_statuses"] = {
            agent_id: statuses.get(agent_id) for agent_id in sorted(set(named_agents))
        }
    return observed


def _case_note(case: CaseData, status: Status) -> str:
    if status == "known gap":
        note = case.get("gap_note") or case.get("adjust_note") or case.get("why", "")
    elif status == "disputed":
        note = case.get("dispute_note") or case.get("why", "")
    elif status == "contract-adjusted":
        note = case.get("adjust_note") or case.get("why", "")
    else:
        note = case.get("why", "")
    return " ".join(str(note).split())


def _validation_error(
    fixture: Fixture, status: Status, failures: tuple[str, ...]
) -> str | None:
    issues: list[str] = []
    case = fixture.case
    if case.get("contract_adjusted"):
        original = case.get("original_expect")
        if not original:
            issues.append("contract-adjusted case has no original_expect")
        if not case.get("adjust_note"):
            issues.append("contract-adjusted case has no adjust_note")
        if original == case.get("expect"):
            issues.append("contract-adjusted case was adjusted to itself")
    if case.get("disputed") and not case.get("dispute_note"):
        issues.append("disputed case has no dispute_note")

    expected_failure = status in {"known gap", "disputed"}
    if expected_failure and not failures:
        issues.append(
            f"{fixture.label} is marked {status} but now passes; remove the marker "
            "so the record stays honest"
        )
    elif not expected_failure and failures:
        issues.extend(failures)
    if not issues:
        return None
    return f"{fixture.label}: {'; '.join(issues)}"


def _count_results(results: Sequence[FixtureResult]) -> FixtureCounts:
    return FixtureCounts(
        total=len(results),
        pass_as_written=sum(result.status == "pass as written" for result in results),
        contract_adjusted=sum(result.status == "contract-adjusted" for result in results),
        disputed=sum(result.status == "disputed" for result in results),
        known_gap=sum(result.status == "known gap" for result in results),
    )


def run_fixtures(
    case_dir: Path = CASE_DIR, roster: Roster | None = None
) -> FixtureSummary:
    """Route all selected cases and return classifications, observations, and totals."""
    selected = discover_fixtures(case_dir)
    active_roster = load_roster() if roster is None else roster
    results: list[FixtureResult] = []

    for fixture in selected:
        decision, session = run_case(fixture.case, active_roster)
        failures = check_case(fixture.case, decision, session)
        status = classify_case(fixture.case)
        current_expectation = fixture.case.get("expect")
        original_expectation = fixture.case.get("original_expect")
        uses_original = isinstance(original_expectation, dict)
        display_expectation = (
            original_expectation
            if uses_original
            else current_expectation
        )
        if not isinstance(display_expectation, dict):
            display_expectation = {}
        results.append(
            FixtureResult(
                fixture=fixture,
                expected=display_expectation,
                expectation_source="reviewer original" if uses_original else "current",
                observed=_observed_fields(display_expectation, decision, session),
                status=status,
                expectation_failures=failures,
                validation_error=_validation_error(fixture, status, failures),
                note=_case_note(fixture.case, status),
            )
        )

    reviewer_names = sorted({result.fixture.reviewer for result in results})
    by_reviewer = {
        reviewer: _count_results(
            [result for result in results if result.fixture.reviewer == reviewer]
        )
        for reviewer in reviewer_names
    }
    return FixtureSummary(
        results=tuple(results),
        by_reviewer=by_reviewer,
        totals=_count_results(results),
    )


def _reviewer_sort_key(reviewer: str) -> tuple[int, str]:
    try:
        return REVIEWER_ORDER.index(reviewer), reviewer
    except ValueError:
        return len(REVIEWER_ORDER), reviewer


def _inline_json(value: object) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return rendered.replace("`", "\\u0060")


def render_markdown(summary: FixtureSummary) -> str:
    """Render a byte-stable Markdown report from one fixture summary."""
    lines = [
        "# Round-1 reviewer fixture results",
        "",
        "Generated by `python evals/run_fixtures.py` from recursively discovered ",
        "policy-plane case documents marked `external: true` and carrying a reviewer. ",
        "Deferred, non-policy, non-runnable, and maintainer-authored documents are not ",
        "part of these reviewer totals.",
        "",
        "Classification precedence is **known gap**, **disputed**, ",
        "**contract-adjusted**, then **pass as written**. The previous hand-assembled ",
        "page also recorded a pre-round-2 snapshot (9 passing fixtures, all from Grok); ",
        "that historical checkout is not available to this runner and is not recomputed.",
        "",
        "## Counts",
        "",
        "| Reviewer | Total | Pass as written | Contract-adjusted | Disputed | Known gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for reviewer in sorted(summary.by_reviewer, key=_reviewer_sort_key):
        counts = summary.by_reviewer[reviewer]
        label = REVIEWER_LABELS.get(reviewer, reviewer)
        lines.append(
            f"| {label} | {counts.total} | {counts.pass_as_written} | "
            f"{counts.contract_adjusted} | {counts.disputed} | {counts.known_gap} |"
        )
    totals = summary.totals
    passing_under_contract = totals.pass_as_written + totals.contract_adjusted
    dispute_noun = "expectation" if totals.disputed == 1 else "expectations"
    dispute_verb = "remains" if totals.disputed == 1 else "remain"
    gap_noun = "known gap" if totals.known_gap == 1 else "known gaps"
    gap_verb = "remains" if totals.known_gap == 1 else "remain"
    lines.extend(
        [
            f"| **Total** | **{totals.total}** | **{totals.pass_as_written}** | "
            f"**{totals.contract_adjusted}** | **{totals.disputed}** | "
            f"**{totals.known_gap}** |",
            "",
            f"Under the current contract, {passing_under_contract} of {totals.total} fixtures ",
            f"pass: {totals.pass_as_written} exactly as written and "
            f"{totals.contract_adjusted} under documented contract adjustments. "
            f"{totals.disputed} {dispute_noun} {dispute_verb} recorded disputes and "
            f"{totals.known_gap} {gap_noun} {gap_verb}.",
            "",
            "## Per fixture",
        ]
    )

    for reviewer in sorted(summary.by_reviewer, key=_reviewer_sort_key):
        lines.extend(["", f"### {REVIEWER_LABELS.get(reviewer, reviewer)}", ""])
        reviewer_results = [
            result for result in summary.results if result.fixture.reviewer == reviewer
        ]
        for result in reviewer_results:
            expectation_label = (
                "expected (reviewer original)"
                if result.expectation_source == "reviewer original"
                else "expected"
            )
            line = (
                f"- `{result.fixture.case_id}` — {expectation_label} "
                f"`{_inline_json(result.expected)}`; observed "
                f"`{_inline_json(result.observed)}`; status **{result.status}**."
            )
            if result.note:
                line += f" {result.note}"
            lines.append(line)
    lines.extend(
        [
            "",
            "## Historical context",
            "",
            "The prior hand-assembled page attributed the round-2 movement, in fixture ",
            "count order, to the two-tier latch and register cap (ADR-0015); normalization, ",
            "masking, and the Spanish pack (ADR-0018); seat/hold separation and one ",
            "eligibility gate (ADR-0016); the preference layer (ADR-0017); and the ",
            "stabilizer-by-role amendment to ADR-0011. This explanation is retained as ",
            "history and is not computed by the fixture runner.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(
    output_path: Path = DEFAULT_OUTPUT,
    case_dir: Path = CASE_DIR,
    roster: Roster | None = None,
) -> FixtureSummary:
    """Run fixtures, write the deterministic report, and return its summary."""
    summary = run_fixtures(case_dir=case_dir, roster=roster)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as report:
        report.write(render_markdown(summary))
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases-dir",
        type=Path,
        default=CASE_DIR,
        help="case tree to scan recursively (default: evals/cases)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Markdown report path",
    )
    args = parser.parse_args(argv)

    summary = write_report(output_path=args.output, case_dir=args.cases_dir)
    if summary.validation_errors:
        for error in summary.validation_errors:
            print(error, file=sys.stderr)
        return 1
    counts = summary.totals
    print(
        f"Wrote {args.output}: {counts.total} fixtures, "
        f"{counts.pass_as_written} pass as written, "
        f"{counts.contract_adjusted} contract-adjusted, "
        f"{counts.disputed} disputed, {counts.known_gap} known gap"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
