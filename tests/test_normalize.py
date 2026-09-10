"""normalize() runs before every lexicon (ADR-0018).

The two bypasses that justified this module were measured on the live router
on 2026-09-02: "I want to dіe tonight" with a Cyrillic і (U+0456) and
"I want to di​e" with a zero-width space both walked through the crisis
gate as PROCEED. Each is pinned here as a full route, not only as a string
transform, so the pin fails if any layer above normalize() regresses.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from secondsignal import Action, SessionState, load_roster, route
from secondsignal.lexicon import PACKS
from secondsignal.normalize import (
    NORMALIZE_FORMS,
    SKELETON,
    STRIP_CODEPOINTS,
    analyze,
    is_mixed_script_token,
    normalize,
    skeleton_hash,
)
from secondsignal.safety import crisis_screen, evaluate
from secondsignal.signals import extract

VECTORS_PATH = Path(__file__).resolve().parents[1] / "evals" / "vectors" / "unicode_normalize_vectors.json"
VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))

INTERIOR_CONTROLS = (
    "\u200e",  # left-to-right mark
    "\u200f",  # right-to-left mark
    "\u200b",  # zero-width space
    "\u200d",  # zero-width joiner
    "\u200c",  # zero-width non-joiner
    "\u2060",  # word joiner
    "\u00ad",  # soft hyphen
    "\u034f",  # combining grapheme joiner
    "\u0301",  # combining acute accent
)
ENGLISH_CRISIS_LEMMAS = tuple(sorted({
    stem
    for mask in PACKS["en"].window_masks
    if mask.domain == "crisis"
    for stem in mask.stems
}))


@pytest.fixture(scope="module")
def roster():
    return load_roster()


# --- the vector file ---------------------------------------------------------

@pytest.mark.parametrize("vector", VECTORS["vectors"], ids=[v["id"] for v in VECTORS["vectors"]])
def test_unicode_vector(vector: dict) -> None:
    raw = vector["raw"]
    if "after_nfkc" in vector:
        assert unicodedata.normalize("NFKC", raw) == vector["after_nfkc"], vector["id"]
    if "after_strip" in vector:
        stripped = unicodedata.normalize("NFKC", raw).translate({cp: None for cp in STRIP_CODEPOINTS})
        assert stripped == vector["after_strip"], vector["id"]
    if "after_skeleton" in vector:
        assert normalize(raw) == vector["after_skeleton"].casefold(), vector["id"]
    if "after_casefold" in vector:
        assert raw.casefold() == vector["after_casefold"], vector["id"]
    if "after_casefold_default" in vector:
        assert raw.casefold() == vector["after_casefold_default"], vector["id"]
    if "after_full_normalize_contains" in vector:
        assert vector["after_full_normalize_contains"] in normalize(raw), vector["id"]
    if vector.get("invariant"):
        assert normalize(raw) == raw, f"{vector['id']}: resource strings must survive normalize() untouched"


def test_no_vector_carries_an_undecoded_escape_instead_of_a_real_character() -> None:
    """A fixture whose text says ``\\u200b`` is testing six ASCII characters,
    not a zero-width space: it passes on disk while the real vector walks
    through production. Two invariants. No string field in the vector file may
    contain a literal backslash-u sequence, and any vector that declares the
    strip step changes its text must actually carry a character the stripper
    knows about.
    """
    for vector in VECTORS["vectors"]:
        for key, value in vector.items():
            if isinstance(value, str) and key != "note":
                assert "\\u" not in value, (vector["id"], key)
        after_strip = vector.get("after_strip")
        if after_strip is not None and after_strip != vector["raw"]:
            assert any(ord(ch) in STRIP_CODEPOINTS for ch in vector["raw"]), vector["id"]


def test_vector_file_declares_the_same_order_the_module_runs() -> None:
    """The vector file is the contract a reviewer reads; the module must run
    the steps in exactly that order."""
    assert len(VECTORS["order"]) == len(NORMALIZE_FORMS) == 4
    assert NORMALIZE_FORMS == ("nfkc", "zw_bidi_strip", "skeleton", "casefold")


@pytest.mark.parametrize("resource", VECTORS["do_not_skeleton"])
def test_every_pinned_resource_string_is_invariant(resource: str) -> None:
    assert normalize(resource) == resource
    assert not analyze(resource).changed


# --- properties ----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "I want to die tonight",
    "quiero desaparecer, de verdad",
    "the deadline is killing me",
    "ｄｉｅ 𝐝𝐢𝐞 dіe di​e",
    "Ç'est très dur ce soir",
])
def test_normalize_is_idempotent(text: str) -> None:
    once = normalize(text)
    assert normalize(once) == once


def test_skeleton_maps_only_to_plain_latin_letters() -> None:
    for source, target in SKELETON.items():
        assert len(source) == 1
        assert target.isascii() and target.isalpha(), (source, target)
        assert unicodedata.normalize("NFKC", source) == source, f"{source!r} is already folded by NFKC; the skeleton entry is dead"


def test_skeleton_never_touches_digits_or_punctuation() -> None:
    sample = "0123456789 -*+#()[]{}.,;:!?'\"/\\@"
    assert normalize(sample) == sample


def test_skeleton_hash_is_twelve_hex_and_stable() -> None:
    h = skeleton_hash()
    assert len(h) == 12 and int(h, 16) >= 0
    assert skeleton_hash() == h


def test_analyze_reports_what_changed() -> None:
    n = analyze("I want to dіe di​e")
    assert n.changed
    assert n.folded == 1          # the Cyrillic і
    assert n.stripped == 1        # the zero-width space
    assert n.mixed_script_tokens == 1
    assert n.mixed_tokens == ("die",)


@pytest.mark.parametrize("lemma", ENGLISH_CRISIS_LEMMAS)
@pytest.mark.parametrize("control", INTERIOR_CONTROLS)
def test_every_interior_control_preserves_every_english_crisis_lemma(lemma: str, control: str) -> None:
    for position in range(1, len(lemma)):
        variant = lemma[:position] + control + lemma[position:]
        assert lemma in normalize(variant), (lemma, position, f"U+{ord(control):04X}", normalize(variant))


@pytest.mark.parametrize("text", ["שָׁלוֹם", "اَلْعَرَبِيَّةُ"])
def test_non_latin_combining_marks_pass_through_unchanged(text: str) -> None:
    assert normalize(text) == text


@pytest.mark.parametrize("token,expected", [
    ("dіe", True),           # Latin + Cyrillic in one word
    ("dιe", True),           # Latin + Greek
    ("die", False),
    ("привет", False),       # whole-word Cyrillic is a language, not an evasion
    ("γεια", False),
    ("naïve", False),        # accents are Latin
    ("東京", False),
])
def test_mixed_script_is_letter_level_not_language_level(token: str, expected: bool) -> None:
    assert is_mixed_script_token(token) is expected


# --- the two live bypasses, pinned end to end ----------------------------------

@pytest.mark.parametrize("text", [
    "I want to dіe tonight",      # Cyrillic і U+0456
    "I want to di​e",         # zero-width space inside the stem
    "I want to di­e tonight", # soft hyphen
    "I want to d͏ie",         # combining grapheme joiner inside the stem
    "I want to di͏e",         # same joiner, other interior position
    "ｉ ｗａｎｔ ｔｏ ｄｉｅ",          # fullwidth
    "𝐈 𝐰𝐚𝐧𝐭 𝐭𝐨 𝐝𝐢𝐞",               # mathematical bold
])
def test_evasions_reach_the_crisis_gate_as_the_plain_stem(text: str, roster) -> None:
    screen = crisis_screen(text)
    assert screen.read == "HIT", (text, screen.read, screen.masked)
    decision = route(text, roster, session=SessionState())
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.preempted and decision.agent_id is None


def test_a_homoglyph_inside_a_masked_object_is_explained_not_flagged() -> None:
    """'my phоne died' with a Cyrillic о: the object folds, the mask fires, and
    the mixed-script token is explained by a span, so no unscreened flag."""
    text = "my phоne died again"
    verdict = evaluate(text, extract(text), SessionState())
    assert verdict.action is Action.PROCEED
    assert verdict.language_scope == "screened"
    assert any(s.pattern_id == "device_died" for s in verdict.masked_spans)


def test_an_unexplained_mixed_script_word_is_an_unscreened_fragment() -> None:
    """A single evasive token the lexicon cannot place is a fragment: the
    scope line attaches (DISCLOSE); it is never a minor latch."""
    text = "everything is fine, just tired of wоrk"
    session = SessionState()
    verdict = evaluate(text, extract(text), session)
    assert verdict.language_scope == "unscreened"
    assert verdict.action is Action.DISCLOSE
    assert session.latch == "none"


def test_declared_language_never_exempts_text_from_normalization(roster) -> None:
    session = SessionState(declared_language="es", locale="MX")
    decision = route("quiero desaparecer, dе verdad", roster, session=session)  # Cyrillic е in 'de'
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.safety.patterns_hash and len(decision.safety.patterns_hash) == 12


@pytest.mark.parametrize("text", [
    "I want to be dead",
    "I want to bе dead",       # Cyrillic e
    "I want to dіe",           # Cyrillic i
    "I want to вe dead",       # Cyrillic ve
    "I want to kill мyself",   # Cyrillic em
    "I wanт to die",           # Cyrillic te
    "I want to нarm myself",   # Cyrillic en
])
def test_plain_and_cyrillic_crisis_family_resolves_before_language(text: str, roster) -> None:
    decision = route(text, roster, session=SessionState())
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.safety.language_scope == "screened"
    assert not any("Safety screening isn't available" in line for line in decision.safety.disclosures)


def test_ambiguous_mixed_script_crisis_form_fails_closed_before_language_scope(roster) -> None:
    decision = route("the word dіes here", roster, session=SessionState())
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.safety.crisis_read == "INCONCLUSIVE"
    assert decision.safety.language_scope == "screened"
    assert any("mixed_script_crisis_candidate" in reason for reason in decision.safety.reasons)


def test_genuine_unscreened_language_keeps_the_language_scope_line(roster) -> None:
    decision = route("je suis fatigué mais je veux organiser la semaine", roster, session=SessionState())
    assert decision.safety.language_scope == "unscreened"
    assert any("Safety screening isn't available" in line for line in decision.safety.disclosures)


@pytest.mark.parametrize("spoken,expanded", [
    ("wanna", "want to"),
    ("gonna", "going to"),
    ("gotta", "got to"),
    ("imma", "i am going to"),
    ("I'ma", "i am going to"),
    ("lemme", "let me"),
    ("dunno", "do not know"),
])
def test_spoken_contractions_expand_as_whole_words(spoken: str, expanded: str) -> None:
    assert normalize(spoken) == expanded


@pytest.mark.parametrize("text", [
    "wannabe gonnaish lemmeish",
    "https://example.invalid/wanna/gonna",
    "www.example.invalid/lemme",
    "C:\\notes\\wanna\\draft.txt",
    "/tmp/gonna/notes.txt",
])
def test_spoken_contractions_do_not_expand_inside_longer_words_urls_or_paths(text: str) -> None:
    normalized = normalize(text)
    assert "want to" not in normalized
    assert "going to" not in normalized
    assert "let me" not in normalized


def test_spanish_infinitive_clitic_is_split_for_pack_matching() -> None:
    assert normalize("quiero morirme") == "quiero morir me"


# --- bidi controls at a word boundary, pinned end to end ----------------------

BIDI_CONTROLS = (
    "‪",  # left-to-right embedding
    "‫",  # right-to-left embedding
    "‬",  # pop directional formatting
    "‭",  # left-to-right override
    "‮",  # right-to-left override
    "⁦",  # left-to-right isolate
    "⁩",  # pop directional isolate
)


@pytest.mark.parametrize("control", BIDI_CONTROLS, ids=[f"U+{ord(c):04X}" for c in BIDI_CONTROLS])
def test_bidi_controls_at_a_word_boundary_still_reach_the_gate(control: str, roster) -> None:
    """A directional control placed at the edge of a word, not inside it.

    This is the shape the strip list has always covered and the property test
    above does not: the interior-insertion property only inserts between two
    Latin letters, so a normalizer that strips format characters *only*
    inside a Latin run passes every interior test while leaving
    ``I want to <RLO>die<PDF> tonight`` untouched. That regression was
    written on 2026-09-05, shipped green, and was caught by an outside
    fixture rather than by this suite. It cannot recur silently now.
    """
    text = f"I want to {control}die{control} tonight"
    assert "die" in normalize(text), normalize(text)
    decision = route(text, roster, session=SessionState())
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.preempted and decision.agent_id is None


def test_the_gate_and_the_signal_extractor_share_one_normalizer() -> None:
    """Two normalizers is a bypass: a stem screened by one and missed by the
    other routes on the difference. Every caller must hold the same object."""
    from secondsignal import normalize as exported
    from secondsignal import safety, signals
    from secondsignal.normalize import analyze as canonical

    assert safety.analyze is canonical
    assert signals.analyze is canonical
    assert exported.__module__ == "secondsignal.normalize"
