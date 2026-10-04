"""Order 1, decisions 6–7: keep Cody present and distinguish relapse subjects.

Reviewer strings available verbatim in Rulings_2026-09-28_Round3_Decisions.md
are pinned below. The unavailable Kimi run-2 fixture is not reconstructed.
"""

from __future__ import annotations

import re
from dataclasses import replace

import pytest
from test_eval_cases import CASES, run_case

from secondsignal import Action, Outcome, SessionState, load_roster, route


@pytest.fixture(scope="module")
def roster():
    return load_roster()


# Independent of the production extractor: deleting a relapse keyword there
# must not silently remove a fixture from this invariant. These are the existing
# labelled corpus's return-to-use forms; decision 7's seven gaps remain separate.
_RELAPSE_TEXT = re.compile(
    r"\b(?:relaps(?:e|ed|ing)|(?:drinking|using|used|drank|got high) again|"
    r"drank (?:last night|tonight)|(?:fell )?off the wagon|started using|back on the)\b",
    re.IGNORECASE,
)
_NON_SUBSTANCE_IDS = {
    "gpt-d3-polysemy", "qwn-d3-nonsubstance-relapse-001", "vibe-d3-false-positive-001",
}
RELAPSE_CASES = [
    (label, case) for label, case in CASES
    if _RELAPSE_TEXT.search(case["text"]) and case["id"] not in _NON_SUBSTANCE_IDS
]


@pytest.mark.parametrize("label,case", RELAPSE_CASES, ids=[p[0] for p in RELAPSE_CASES])
def test_d6_every_labelled_addiction_relapse_keeps_cody(label, case, roster):
    decision, _ = run_case(case, roster)
    if decision.safety.action is Action.HUMAN_ESCALATION:
        assert decision.outcome is Outcome.PREEMPTED, label
        assert decision.agent_id is None, label
    else:
        assert decision.agent_id == "cody" or "offer_companion:cody" in decision.obligations, label


def test_d6_named_companion_survives_another_recovery_carrier(roster):
    """A new, narrower recovery carrier cannot replace the ruled Cody offer."""
    expanded = dict(roster)
    expanded["ellis"] = replace(roster["ellis"], domains=frozenset({"addiction_recovery"}))
    decision = route(
        "My sibling relapsed yesterday. Help me plan a calm conversation that does not shame them.",
        expanded,
        session=SessionState(),
    )
    assert decision.agent_id == "rowan"
    assert "offer_companion:cody" in decision.obligations


def test_d6_absent_role_never_offers_an_unloaded_character(roster):
    custom_roster = {pid: profile for pid, profile in roster.items() if pid != "cody"}
    decision = route(
        "My sibling relapsed yesterday. Help me plan a calm conversation that does not shame them.",
        custom_roster,
        session=SessionState(),
    )
    assert decision.agent_id == "rowan"
    assert "offer_companion:cody" not in decision.obligations


@pytest.mark.parametrize("case_id,text,subject", [
    (
        "d3-ambiguous-subject-001",
        "she relapsed again and I keep thinking about what I could have said",
        "other",
    ),
    ("d3-first-person-control-001", "I relapsed again last night", "self"),
    (
        "glm-d3-mixed-subject-001",
        "my dad relapsed last month and honestly so did I two weeks ago; "
        "I need help getting through tonight",
        "self",
    ),
    ("operator-misread-self", "my dad relapsed last night and so did I", "self"),
    ("operator-misread-name", "Jake relapsed again", "other"),
    ("operator-plural", "we both relapsed last night", "self"),
    ("operator-bare", "relapsed again, feel awful", "self"),
    ("operator-third", "she relapsed again", "other"),
])
def test_d7_reviewer_and_operator_subjects(case_id, text, subject, roster):
    decision = route(text, roster, session=SessionState())
    assert decision.claim_subject == subject, case_id
    if subject == "self":
        assert decision.seat_claim == "addiction_recovery", case_id
        assert decision.agent_id == "cody", case_id
        assert "affected_person:other" not in decision.obligations, case_id
    else:
        assert decision.seat_claim is None, case_id
        assert "addiction_recovery" in decision.held, case_id
        assert "affected_person:other" in decision.obligations, case_id
    assert decision.agent_id == "cody" or "offer_companion:cody" in decision.obligations


@pytest.mark.parametrize("text", [
    "I heard Jake relapsed again; help me plan a calm conversation",
    "Jake relapsed again and I need help with a calm conversation",
    "Someone from the neighborhood relapsed; help me plan a calm conversation",
    "I think she relapsed; help me plan a calm conversation",
    "I was there when Jake relapsed; help me plan a calm conversation",
    "She relapsed. She asked for help and so did I; help me plan a calm conversation",
    "My sister, unfortunately, relapsed; help me plan a calm conversation",
    "She, too, relapsed; help me plan a calm conversation",
    "Jake, I think, relapsed; help me plan a calm conversation",
    "Jake, after four good years, relapsed; help me plan a calm conversation",
    "My brother, I am told, relapsed; help me plan a calm conversation",
    "I and Jake talked; my dad relapsed; help me plan a calm conversation",
    "I and Jake talked, and my dad relapsed; help me plan a calm conversation",
    "She relapsed. She asked for help and I did too; help me plan a calm conversation",
    "She relapsed. She needed help, me too; help me plan a calm conversation",
])
def test_d7_unclear_or_other_subject_is_a_hold_even_with_a_first_person_ask(text, roster):
    decision = route(text, roster, session=SessionState())
    assert decision.claim_subject == "other"
    assert decision.seat_claim is None
    assert decision.agent_id == "rowan"
    assert "offer_companion:cody" in decision.obligations


@pytest.mark.parametrize("text", [
    "My dad relapsed and I relapsed too",
    "I relapsed last week and my dad relapsed yesterday",
    "My dad and I both relapsed last night",
    "We have both relapsed again",
    "I have recently relapsed",
    "I, too, relapsed",
    "I and Jake relapsed",
    "Me and Jake relapsed",
    "I and my dad both relapsed",
    "My dad relapsed, and I, unfortunately, relapsed too",
    "my dad relapsed and I did too",
    "my dad relapsed; I did too",
    "my dad relapsed and we both did too",
    "my dad relapsed and me too",
    "My dad relapsed on September 28 and so did I",
    "Jake and us relapsed",
])
def test_d7_self_relapse_anywhere_in_the_message_claims_the_seat(text, roster):
    decision = route(text, roster, session=SessionState())
    assert decision.claim_subject == "self"
    assert decision.seat_claim == "addiction_recovery"
    assert decision.agent_id == "cody"


# The Night Builds Review of 30 September 2026 found three first-person reports
# read as someone else's relapse under the first build of decision 7. Decision 7,
# points 1 and 3: the person who includes themselves is the one who relapsed, and
# a report that names nobody is the person's own.
@pytest.mark.parametrize("text", [
    "I'm the one who relapsed",
    "Ugh, relapsed again",
    "I'm ashamed, relapsed again",
    "I am the one who relapsed",
    "ugh, I'm ashamed, relapsed again",
    "I feel awful, relapsed again",
    "oh no, relapsed again",
])
def test_d7_first_person_reports_the_review_found_misread_are_the_persons_own(text, roster):
    decision = route(text, roster, session=SessionState())
    assert decision.claim_subject == "self"
    assert decision.seat_claim == "addiction_recovery"
    assert decision.agent_id == "cody"
    assert "affected_person:other" not in decision.obligations
    assert decision.safety.action is Action.PROCEED


# The repairs above are narrow: a relative clause whose antecedent is somebody
# else, a comma after an ordinary first-person verb, or a named subject after an
# interjection still fails toward the hold (decision 7, points 2 and 4).
@pytest.mark.parametrize("text", [
    "She's the one who relapsed",
    "My dad is the one who relapsed",
    "I know who relapsed",
    "I'm not the one who relapsed, my dad is",
    "I heard Jake, relapsed again",
    "ugh, Jake relapsed again",
    "I'm with my dad, relapsed again",
])
def test_d7_the_misread_repairs_do_not_claim_someone_elses_relapse(text, roster):
    decision = route(text, roster, session=SessionState())
    assert decision.claim_subject == "other"
    assert decision.seat_claim is None
    assert "addiction_recovery" in decision.held
    assert decision.agent_id == "cody" or "offer_companion:cody" in decision.obligations


def test_d6_emergency_reuses_a_labelled_fixture_and_still_preempts(roster):
    case = next(case for _, case in CASES if case["id"] == "gpt-d3-acute")
    decision, _ = run_case(case, roster)
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.outcome is Outcome.PREEMPTED
    assert decision.agent_id is None
    assert decision.ranked == ()
