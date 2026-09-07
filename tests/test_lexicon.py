"""Lexicon packs and the mask engine (ADR-0018).

Three contracts are enforced here:

* load-time contracts: a pack with a duplicate id, a window mask without
  objects, or a resource row that claims 24/7 without a source does not load;
* the two-fixture rule: every window mask in every shipped pack has a
  positive fixture (the mask fires) and a negative fixture (the stem alone
  does not), so that no mask can quietly become a silencer;
* the record: every mask that fires and every span that hits travels on the
  verdict with the hash of the tables consulted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from secondsignal import Action, SessionState, load_roster, route
from secondsignal.lexicon import (
    PACKS,
    RESOURCES,
    apply_masks,
    load_pack,
    load_resources,
    patterns_hash,
    resource_line,
    resource_row,
    screen_packs,
)
from secondsignal.normalize import normalize
from secondsignal.safety import crisis_screen, evaluate
from secondsignal.signals import extract

# --------------------------------------------------------------------------
# The two-fixture rule. Keyed by pack id then mask id. ``positive`` must be
# masked by exactly that mask; ``negative`` carries the same stem and must
# not be masked by it. A mask added to a pack without a pair here fails
# ``test_every_window_mask_has_both_fixtures``.
# --------------------------------------------------------------------------
WINDOW_MASK_FIXTURES: dict[str, dict[str, tuple[str, str]]] = {
    "en": {
        "labor_kill": ("this workload is going to kill me", "I want to kill myself"),
        "labor_die": ("my phone is about to die", "I want to die"),
        "laugh_die": ("dying lol at this thread", "dying inside"),
        "game_jump": ("if I wipe on this boss one more time I am going to jump", "I am going to jump"),
        "ops_kill": ("kill the process on port 80", "kill me now"),
        "negated_die_with_work_object": ("I'd rather not die in this meeting", "I want to die in this meeting"),
        "sober_look": ("give me a sober look at the numbers", "I am 30 days sober"),
        "using_tool": ("I'm using the spreadsheet to track it", "I started using again"),
        "clean_thing": ("the code is finally clean", "I have been clean for a year"),
        "relapsed_non_substance": ("I relapsed on caffeine this week", "I relapsed last night"),
        "school_as_adult_context": ("back in high school I never finished anything", "high school is exhausting"),
        "homework_as_adult_context": ("grading homework for my students tonight", "my homework is due tomorrow"),
        "teacher_as_adult_context": ("I'm a teacher and my class is wild this year", "my teacher said I need to focus"),
    },
    "es-419": {
        "matando_trabajo": ("este trabajo me está matando", "me está matando"),
        "desaparecer_escenario": ("el mago hace desaparecer la carta", "quiero desaparecer"),
        "muero_object": ("me muero, qué risa", "me muero"),
        "limpio_cosa": ("dejé el código limpio", "llevo un año limpio"),
        "recaída_no_sustancia": ("tuve una recaída con el azúcar", "tuve una recaída anoche"),
    },
}


def _mask_ids(text: str) -> set[str]:
    _, spans = apply_masks(normalize(text))
    return {s.pattern_id for s in spans}


def test_every_window_mask_has_both_fixtures() -> None:
    for pack_id, pack in PACKS.items():
        shipped = {m.id for m in pack.window_masks}
        listed = set(WINDOW_MASK_FIXTURES.get(pack_id, {}))
        assert shipped == listed, (
            f"pack {pack_id}: window masks without a fixture pair: {sorted(shipped - listed)}; "
            f"fixture pairs without a mask: {sorted(listed - shipped)}"
        )


PAIRS = [
    (pack_id, mask_id, pos, neg)
    for pack_id, masks in WINDOW_MASK_FIXTURES.items()
    for mask_id, (pos, neg) in masks.items()
]


@pytest.mark.parametrize("pack_id,mask_id,positive,negative", PAIRS, ids=[f"{p}:{m}" for p, m, _, _ in PAIRS])
def test_window_mask_fires_with_its_object_and_not_without(pack_id, mask_id, positive, negative) -> None:
    assert mask_id in _mask_ids(positive), f"{pack_id}:{mask_id} did not fire on {positive!r}"
    assert mask_id not in _mask_ids(negative), f"{pack_id}:{mask_id} fired on the bare stem {negative!r}"


# --- load-time contracts -------------------------------------------------------

def _write_pack(tmp_path: Path, body: dict) -> Path:
    path = tmp_path / "x.json"
    path.write_text(json.dumps({"pack": "x", "language": "xx", **body}), encoding="utf-8")
    return path


def test_duplicate_id_fails_the_load(tmp_path) -> None:
    path = _write_pack(tmp_path, {
        "regex_masks": [{"id": "dup", "pattern": "a"}],
        "hits": [{"id": "dup", "class": "c", "pattern": "b"}],
    })
    with pytest.raises(ValueError, match="duplicate id"):
        load_pack(path)


def test_window_mask_without_objects_fails_the_load(tmp_path) -> None:
    path = _write_pack(tmp_path, {"window_masks": [{"id": "silencer", "stems": ["die"], "objects": []}]})
    with pytest.raises(ValueError, match="silencer"):
        load_pack(path)


def test_window_mask_without_stems_fails_the_load(tmp_path) -> None:
    path = _write_pack(tmp_path, {"window_masks": [{"id": "empty", "stems": [], "objects": ["x"]}]})
    with pytest.raises(ValueError, match="no stems"):
        load_pack(path)


def test_resource_row_claiming_24_7_without_a_source_fails_the_load(tmp_path) -> None:
    path = tmp_path / "resources.json"
    path.write_text(json.dumps({"version": 1, "rows": {
        "default": {"lines": {"en": "x", "es": "y"}},
        "ZZ": {"hours": "24/7", "last_verified": "2026-09-02", "lines": {"en": "x", "es": "y"}},
    }}), encoding="utf-8")
    with pytest.raises(ValueError, match="24/7 without a source"):
        load_resources(path)


def test_resource_row_without_a_verification_date_fails_the_load(tmp_path) -> None:
    path = tmp_path / "resources.json"
    path.write_text(json.dumps({"version": 1, "rows": {
        "default": {"lines": {"en": "x", "es": "y"}},
        "ZZ": {"hours": "09:00-17:00", "source": "https://example.invalid", "lines": {"en": "x", "es": "y"}},
    }}), encoding="utf-8")
    with pytest.raises(ValueError, match="last_verified"):
        load_resources(path)


def test_shipped_packs_and_resources_meet_their_own_contracts() -> None:
    assert "en" in PACKS and "es-419" in PACKS
    for pack in PACKS.values():
        assert pack.source_hash and len(pack.source_hash) == 12
        assert pack.status in {"unreviewed", "reviewed"}
    for locale, row in RESOURCES["rows"].items():
        assert "en" in row["lines"] and "es" in row["lines"], locale
        if locale != "default":
            assert row.get("source") and row.get("last_verified"), locale


# --- the clause rule ------------------------------------------------------------

def test_an_object_never_explains_a_stem_across_a_sincerity_pivot() -> None:
    """The property that keeps a wide game window from silencing a sincere
    clause later in the same message (pinned end to end in test_crisis_gate)."""
    text = "I want to die in this boss fight and respawn and honestly I want to die"
    masked, spans = apply_masks(normalize(text))
    pivot = text.index("honestly")
    assert spans and all(s.end <= pivot for s in spans), spans   # the first die is explained
    assert masked.endswith("i want to die")                       # the second is not
    assert crisis_screen(text).read == "HIT"


def test_an_object_never_explains_a_stem_across_a_sentence_break() -> None:
    text = "I wiped on the boss again. I want to die."
    _, spans = apply_masks(normalize(text))
    assert not any(s.text == "die" for s in spans)
    assert crisis_screen(text).read == "HIT"


def test_a_per_mask_window_overrides_the_pack_default() -> None:
    game = next(m for m in PACKS["en"].window_masks if m.id == "game_jump")
    assert game.window == 10 and PACKS["en"].window == 4
    assert "game_jump" in _mask_ids("if I wipe on this boss one more time I am going to jump")
    # Eight tokens apart is outside the pack default; only the override reaches it.
    assert "labor_kill" not in _mask_ids("this deadline for the quarterly report is really going to kill me")


# --- the record -----------------------------------------------------------------

def test_every_verdict_carries_spans_hash_and_pack_ids() -> None:
    text = "this deadline is killing me"
    verdict = evaluate(text, extract(text), SessionState())
    assert verdict.action is Action.PROCEED
    assert [s.pattern_id for s in verdict.masked_spans] == ["labor_killing_me"]
    assert verdict.hit_spans == ()
    assert re.fullmatch(r"[0-9a-f]{12}", verdict.patterns_hash)
    assert set(verdict.pack_ids) >= {"en", "es-419"}


def test_patterns_hash_changes_when_a_table_changes() -> None:
    base = patterns_hash()
    assert patterns_hash(("extra:pattern",)) != base
    assert patterns_hash() == base


def test_packs_compose_an_english_mask_and_a_spanish_hit_in_one_message() -> None:
    """All installed packs run on every turn; declaring a language selects
    house lines and resources, never which text is screened."""
    text = "this deadline is killing me y ya no quiero vivir"
    screen = crisis_screen(text)
    assert screen.read == "HIT"
    assert any(s.pack == "en" and s.kind == "mask" for s in screen.masked_spans)
    assert any(s.pack == "es-419" and s.kind == "hit" for s in screen.hit_spans)
    hits, _ = screen_packs(normalize(text))
    assert hits and hits[0].domain == "passive_absence"


@pytest.mark.parametrize("declared", ["en", "es", "fr", None])
def test_declared_language_does_not_change_what_is_screened(declared) -> None:
    roster = load_roster()
    session = SessionState(declared_language=declared, locale="US")
    decision = route("me quiero morir", roster, session=session)
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.safety.language_scope == "screened"


# --- resources ------------------------------------------------------------------

def test_unknown_locale_falls_back_to_the_directory_line() -> None:
    key, _ = resource_row("ZZ")
    assert key == "default"
    assert "findahelpline.com" in resource_line("ZZ", "en")
    assert "findahelpline.com" in resource_line(None, None)


def test_resource_line_follows_declared_language_when_the_row_carries_it() -> None:
    assert resource_line("MX", "es").startswith("Si estás en México")
    assert resource_line("MX", "en").startswith("If you are in Mexico")
    # A language the row does not carry falls back to English, never to a guess.
    assert resource_line("MX", "fr").startswith("If you are in Mexico")


def test_every_pinned_number_survives_normalize() -> None:
    for row in RESOURCES["rows"].values():
        for line in row["lines"].values():
            for number in re.findall(r"\*?\d[\d-]{1,}", line):
                assert normalize(number) == number


# --- es-419 enclitic forms: regression pin ------------------------------------

@pytest.mark.parametrize("text", [
    "quiero matarme",
    "quiero morirme",
    "quiero suicidarme",
    "quiero quitarme la vida",
])
def test_joined_enclitic_spanish_forms_still_hit(text: str) -> None:
    """The pack matches these infinitives with the pronoun attached, as one
    token. A normalizer that splits enclitics (2026-09-06, reverted) silently
    turned every one of these into a miss while the suite stayed green. This
    pin fails if that is attempted again."""
    assert crisis_screen(text).read == "HIT", text
