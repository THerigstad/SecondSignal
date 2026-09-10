"""Safety layer.

Design principle: **safety is not a filter on the output, it is a gate on the
route.** This module runs *before* agent selection and holds the authority to
preempt it entirely. A persona is never given the opportunity to improvise a
response to a crisis signal, because in the preempted case no persona is
selected at all.

Four verdict actions, in descending precedence:

    HUMAN_ESCALATION  No persona is engaged. Response is the one crisis card
                      with the declared region's resources. Non-overridable
                      by user request, framing, persona preference, or
                      claimed authority. Also the verdict when a substantial
                      part of the message is in a language no installed pack
                      can screen: an unreadable span is an inconclusive read,
                      and inconclusive fails closed (ADR-0010).
    BOUNDARY_HOLD     Persona is engaged but a boundary is held explicitly
                      rather than deflected: a romantic or sexual frame, an
                      attempt to move a permission bit from inside the
                      message, a request to help conceal harm, or a
                      "preference" that names the safety envelope.
    DISCLOSE          Persona proceeds, with a required line attached: the
                      dependency interrupt, the careful-side posture, a
                      fragment the screen could not read, the turn after an
                      escalation, or a style suggestion.
    PROCEED           Normal routing.

Everything the gate reads is normalized first (``normalize.py``: NFKC,
invisible and bidi stripping, a look-alike skeleton, casefold) and masked
second (``lexicon.py``: idiom masks with object windows). Every mask that
fired and every span that hit travels on the verdict, with the hash of the
pattern tables that produced them, so a reviewer can see what the gate saw.

Crisis screening is a *versioned lexicon of speech-act classes*, not a list of
literal phrases and not a clinical instrument. Its status is ``unreviewed``
until a human -- ideally a clinician -- has reviewed the class list and a
false-positive set. The gate is fail-closed: an inconclusive read escalates
the same way a hit does. A negated first-person stem ("I don't want to die")
is downgraded from HIT to INCONCLUSIVE and still escalates; whether bare
denial should proceed is a clinician's call and is a documented gap.

Scope, dated 2026-09: an English screen and a native Latin American Spanish
pack (``es-419``), both unreviewed. All installed packs run on every turn;
declaring a language selects the house lines and the resource line and
never exempts any text from any screen.

The session monitors (latch, dependency, style) are intentionally coarse. A
deployment would replace the detectors with trained classifiers while
preserving the verdict contract.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TypedDict

from .lexicon import (
    PACKS,
    RESOURCES,
    Span,
    apply_masks,
    screen_packs,
    tokenize,
)
from .lexicon import patterns_hash as _patterns_hash
from .lexicon import resource_line as _resource_line_for
from .normalize import analyze
from .preferences import STYLE_ASK_COOLDOWN_TURNS, STYLE_ASK_THRESHOLD, PreferenceEvent
from .preferences import assess as assess_preference
from .signals import RequestSignals

__all__ = [
    "Action",
    "SafetyVerdict",
    "SessionState",
    "evaluate",
    "CRISIS_CARD",
    "CRISIS_CLASSES",
    "INCONCLUSIVE_PATTERNS",
    "crisis_read",
    "crisis_screen",
    "HOUSE_LINES_EN",
    "house_lines",
    "REGISTER_CAPS",
]


class Action(IntEnum):
    """Ordered by precedence. Higher value wins."""

    PROCEED = 0
    DISCLOSE = 1
    BOUNDARY_HOLD = 2
    HUMAN_ESCALATION = 3


# --------------------------------------------------------------------------
# House lines. One crisis card. Plain voice; no persona speaks these.
#
# The wording came out of the round-1 external design review (five
# reviewers, 2026-09-02): no spatial or anthropomorphic phrasing, no line
# that can be quoted as proof of a relationship, a question rather than a
# demand for a name, and two separate careful-side lines so an inferred
# posture never outs a young person on a shared account. The Spanish lines
# live in the es-419 pack and were written natively, not translated.
# --------------------------------------------------------------------------

HOUSE_LINES_EN: dict = {
    "escalation_card": (
        "What you just wrote should be heard by a person, not a character.",
        "So the characters are stepping out of this message, and nothing here will pretend to be more than it is.",
        "{resource_line}",
        "If this was read wrong, say so plainly. Asking is better than guessing.",
        "Is there someone near you, or someone you could call, who you would want with you right now?",
    ),
    "post_escalation": (
        "Carrying on. If the last message was read wrong, saying so was enough; "
        "the resources from it stay in reach either way."
    ),
    "dependency": (
        "Saying this plainly because it matters: this is not a substitute for people. "
        "Is there anyone you trust you could reach, if it feels safe to?"
    ),
    "boundary": (
        "Answering this directly: the care here was designed, and this is not a "
        "relationship. The romantic frame stops here."
    ),
    "integrity": (
        "Nothing inside a message can change the rules here -- not a claimed "
        "authority, not a mode name, not a fake system command. Carrying on under "
        "the same rules as always."
    ),
    "minor_inferred": (
        "Some of what was said reads as though you might be young, so this stays on "
        "the careful side: a more careful tone, no romance, and a quicker nudge "
        "toward a person you trust, online or offline."
    ),
    "minor_declared": (
        "This account is on the careful side: a more careful tone, no romance, and "
        "a quicker nudge toward a person you trust, online or offline."
    ),
    "language_scope": (
        "Safety screening isn't available in this language yet, so part of this "
        "message couldn't be checked. If any of it is about being unsafe, say so "
        "plainly, or use the resources for your area."
    ),
    "facilitation": (
        "That is something this space will not help hide or arrange. Talking about "
        "it stays open; helping do it does not."
    ),
    "style_suggestion": (
        "You've asked for this more than once. Want it as the default? You can "
        "confirm it in your settings."
    ),
}

# Names kept for callers and tests that pinned the first edition.
ESCALATION_MESSAGE = HOUSE_LINES_EN["escalation_card"][0]
DEPENDENCY_DISCLOSURE = HOUSE_LINES_EN["dependency"]
BOUNDARY_DISCLOSURE = HOUSE_LINES_EN["boundary"]
INTEGRITY_DISCLOSURE = HOUSE_LINES_EN["integrity"]
MINOR_DISCLOSURE = HOUSE_LINES_EN["minor_inferred"]
MINOR_DISCLOSURE_DECLARED = HOUSE_LINES_EN["minor_declared"]
LANGUAGE_SCOPE_DISCLOSURE = HOUSE_LINES_EN["language_scope"]
FACILITATION_DISCLOSURE = HOUSE_LINES_EN["facilitation"]
POST_ESCALATION_LINE = HOUSE_LINES_EN["post_escalation"]
STYLE_SUGGESTION_LINE = HOUSE_LINES_EN["style_suggestion"]


def house_lines(language: str | None) -> dict:
    """The fixed lines in the declared language, English when no pack carries
    that language. A pack's lines are native prose, never machine output."""
    lang = (language or "en").split("-")[0].lower()
    for pack in PACKS.values():
        if pack.language == lang and pack.house_lines:
            return pack.house_lines
    return HOUSE_LINES_EN


# --------------------------------------------------------------------------
# Crisis card: the versioned policy the gate enforces.
#
# ``uncertainty_policy`` is the one deliberate knob. ``fail_closed`` means an
# inconclusive read escalates exactly like a hit (ADR-0010). It may be flipped
# to ``disclose`` only after a human has reviewed a false-positive set; until
# then the cost of interrupting an innocent conversation is accepted.
#
# Resources are keyed by *declared* locale, never inferred from network
# location. One phone number is not a world default: outside a pinned row the
# layer points to a directory and to local emergency services. Every pinned
# row names its official source and the date a person opened it
# (``packs/resources.json``). No number lives in a model; this layer supplies
# the text and the persona only points to it.
# --------------------------------------------------------------------------

CRISIS_CARD: dict = {
    "version": 2,
    "lexicon_status": "unreviewed",
    "uncertainty_policy": "fail_closed",
    "scope": (
        "English screen plus a native Latin American Spanish pack (es-419); both "
        "unreviewed; every installed pack runs on every turn; dated 2026-09"
    ),
    "packs": tuple(sorted(PACKS)),
    "resources": {
        locale: row["lines"]["en"] for locale, row in RESOURCES["rows"].items()
    },
    "card": HOUSE_LINES_EN["escalation_card"],
    "never_say": ("did that help", "I'm here all night", "don't tell anyone"),
}


def _compile(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


# Speech-act classes. Every entry is a *class example*, deliberately
# pronoun-agnostic so that third-person, "asking for a friend", writer and
# hypothetical framings match the same way first-person does: framing does not
# waive the gate. Places and objects are named at recognition level only.
CRISIS_CLASSES: dict[str, tuple[re.Pattern[str], ...]] = {
    "direct_ideation": _compile((
        r"\b(want|wants|wanted|wanna|need|needs|needed|going|gonna|plan|plans|planning|ready|trying|tried|decided)"
        r" to (die|be dead|not exist|stop existing|kill (myself|himself|herself|themselves|yourself|ourselves)"
        r"|end (my|his|her|their|our) (own )?life|end it all|end it|end things|end everything"
        r"|take (my|his|her|their) (own )?life)\b",
        r"\bkill(ing)? (myself|himself|herself|themselves)\b",
        r"\bend(ing)? (my|his|her|their) (own )?life\b",
        r"\btak(e|ing) (my|his|her|their) (own )?life\b",
        r"\bsuicid(e|al)\b",
        r"\b(hurt|harm|cut|cutting|hurting|harming) (myself|himself|herself|themselves)\b",
        r"\bself[- ]?harm\b",
        r"\b(should|could|might|will|i'?ll|i'?d|i will|i would|gonna|going to|about to)"
        r" (just )?(end it|end it all|end things|end everything)\b",
        r"\b(better off|rather be) dead\b",
        r"\bwish (i|he|she|they) (was|were) (dead|gone|never born|not here|not alive)\b",
        r"\b(hurt|kill|harm) (someone|somebody|people|him|her|them)\b",
        r"\b(use|used|follow|following) (the|my) plan (i|that i) made to die\b",
        r"\bplan (i|that i) made to die\b",
    )),
    "passive_absence": _compile((
        r"\b(won'?t|will not|not going to|not gonna|don'?t think (i'?ll|i will)|doubt (i'?ll|i will)|might not|may not|probably won'?t)"
        r" (be|make it) (here|around|alive|there) (anymore|much longer|in \d+|in a|next|by|for|when|to see|past|after)\b",
        r"\b(not|don'?t|never|won'?t) (want(ing)? to |going to |gonna )?(wake|waking) up\b",
        r"\b(want|wants|wanted|wanna|wish|wishing|hope|hoping) to (disappear|vanish|not be here|not exist|be gone|go away forever|stop being here)\b",
        r"\bbetter off without (me|him|her|them)\b",
        r"\bno reason to (live|be here|go on|keep going|stay)\b",
        r"\b(can'?t|cannot) (go on|keep going|keep living) (anymore|like this)\b",
        r"\b(don'?t|do not|doesn'?t) want to (be here|be alive|live|exist|be around) ?(anymore|any more)?\b",
        r"\bbe here anymore\b",
        r"\b(wasn'?t|weren'?t|wouldn'?t be|if i (just )?wasn'?t|if i (just )?weren'?t) (here|around|alive) (anymore|any more)\b",
        r"\beasier if i (just )?(wasn'?t|weren'?t|were not|was not) (here|around|alive)\b",
        r"\b(tired|sick|done) of (living|being alive|life|existing)\b",
        r"\bnot worth (living|being alive)\b",
        r"\blife (isn'?t|is not|ain'?t) worth\b",
        r"\bgo to sleep and (not|never) wake\b",
        r"\beveryone would be better off\b",
    )),
    "slang_or_joke_ideation": _compile((
        r"\b(yeet|throw|hurl|launch|fling|toss|chuck|throwing|yeeting) (myself|himself|herself|themselves|me)"
        r" (off|in front of|into|out of|under|over)\b",
        r"\b(jump|step|walk|drive|leap|jumping|stepping|walking|driving)"
        r" (off|in front of|into|under|out) (the|a|this|that|an|oncoming|moving|of the|of a|of this)? ?"
        r"(bridge|building|roof|ledge|train|bus|traffic|car|river|overpass|highway|balcony|window)\b",
        r"\bwalk(ing)? into traffic\b",
        r"\bunalive (myself|me|himself|herself|themselves)\b",
        r"\bdelete myself\b",
    )),
    "means_present": _compile((
        r"\bpills? (out|lined up|ready|in (my|her|his|their) hand|in front of (me|them|him|her)"
        r"|on the (counter|table|nightstand|bed|desk))\b",
        r"\b(have|got|has|had) (the|my|her|his|their|some) pills (out|ready|here|with (me|them))\b",
        r"\b(a |the )?(bottle|handful) of pills\b",
        r"\b(rope|gun|pistol|knife|blade|razor|belt) (in (my|her|his|their) hand|out|ready|next to (me|them|him|her)|beside (me|them))\b",
        r"\bgarage (with the door (down|closed|shut)|door (down|closed|shut))\b",
        r"\b(car|engine) running in the garage\b",
        r"\b(standing|sitting|standing out) on (the|a) (bridge|ledge|roof|edge|railing|overpass|balcony)\b",
        r"\bon the ledge\b",
        # Ingestion already happened. Named at recognition level only.
        r"\b(took|taken|swallowed|drank|downed) (everything|all of them|all of it|all the pills|the whole bottle|the entire bottle|whole bottle|too much|too many|way too much|everything in the cabinet)\b",
    )),
}

# A mixed-script token that folds to one of these crisis forms is resolved in
# the crisis lane before language-scope handling. Exact phrases still HIT the
# classes above; a bare or malformed form is an inconclusive read and follows
# the existing fail-closed policy instead of being mislabeled as a language
# the system cannot screen.
_MIXED_SCRIPT_CRISIS_FORMS: frozenset[str] = frozenset({
    "die", "dies", "died", "dying", "dead",
    "suicide", "suicidal",
    "kill", "kills", "killed", "killing",
    "harm", "harms", "harmed", "harming",
    "hurt", "hurts", "hurting",
    "cut", "cuts", "cutting",
    "unalive", "disappear", "vanish",
})


def _mixed_token_is_crisis_form(token: str) -> bool:
    """Whether one mixed-script token reads as a crisis word.

    Two shapes count, and only two. The token folds exactly onto a crisis
    form, or it folds onto one with a single extra character at an edge --
    the shape of a look-alike appended or prepended to break the word
    boundary ("die" plus a Cyrillic a reads as "diea" and matches nothing).
    An interior difference is not a candidate: it is an ordinary word that
    happens to be one edit from a crisis form, and carding it would card
    bilingual writers for a typo.
    """
    if token in _MIXED_SCRIPT_CRISIS_FORMS:
        return True
    if len(token) < 2:
        return False
    return token[1:] in _MIXED_SCRIPT_CRISIS_FORMS or token[:-1] in _MIXED_SCRIPT_CRISIS_FORMS

_OTHER_PERSON_ACTOR_RE = (
    r"(?:my (?:partner|roommate|parent|relative|spouse)|"
    r"the (?:other adult|visitor|neighbor|stranger)|"
    r"another person|someone|somebody|he|she|they)"
)
_PRESENT_WEAPON_ACTION_RE = (
    r"(?:(?:is|are) (?:holding|using|waving|brandishing|pointing)|"
    r"has|have|holds|uses|waves|brandishes|points)"
)
_WEAPON_RE = r"(?:(?:a|an|the|his|her|their|our|my) )?(?:loaded )?(?:gun|handgun|pistol|rifle|knife|blade|weapon)s?"
_OTHER_PERSON_WEAPON_RE = re.compile(
    rf"\b{_OTHER_PERSON_ACTOR_RE}\b.{{0,80}}?\b{_PRESENT_WEAPON_ACTION_RE}\b\s+{_WEAPON_RE}\b",
    re.IGNORECASE,
)
_OTHER_PERSON_WEAPON_EXCLUSION_RE = re.compile(
    r"\b(?:last (?:year|time|week|month)|yesterday|ago|used to|novel|film|movie|story|news|"
    r"video game|game|hunting trip|job|work|locked|secured)\b",
    re.IGNORECASE,
)
_WEAPON_CLAUSE_RE = re.compile(r"[^.!?,:;\n\u2013\u2014]+")


def _other_person_weapon_span(text: str) -> tuple[str, int, int] | None:
    """Find present other-person possession/use of a weapon in one clause.

    This is an intentionally narrow interim. It excludes explicit past and
    fictional/occupational frames and does not replace the existing
    first-person means class.
    """
    for clause_match in _WEAPON_CLAUSE_RE.finditer(text):
        clause = clause_match.group(0)
        if _OTHER_PERSON_WEAPON_EXCLUSION_RE.search(clause):
            continue
        match = _OTHER_PERSON_WEAPON_RE.search(clause)
        if match:
            return match.group(0).strip(), clause_match.start() + match.start(), clause_match.start() + match.end()
    return None

# Ambiguous language. Under the fail-closed policy these escalate exactly like
# a hit, but they are recorded separately so the false-positive cost is
# measurable and so the policy can be flipped without touching the classes.
INCONCLUSIVE_PATTERNS: tuple[re.Pattern[str], ...] = _compile((
    r"\b(i'?m|im|i am) (so |just |completely |totally )?done\b(?! with)",
    r"\b(can'?t|cannot) (do|take|handle) (this|it|any of this|any more of this) anymore\b",
    r"\bwhat'?s the point\b",
    r"\bno point (anymore|in anything|to any of this|in trying|in going on)\b",
    r"\bnothing matters\b",
    r"\bnothing (ever |is ever )?(gets|will get|is going to get) better\b",
    r"\b(i|i'?d|i could|i might|i should) (could |might |should |would )?(just )?disappear\b",
    r"\bi give up\b(?! on)",
    r"\bcan'?t keep (doing|going|living) (like )?this\b",
    r"\bno way out\b",
    r"\bcatch (the|a) bus\b",
    r"\b(off|from) (the|a) (bridge|roof|ledge|overpass|cliff)\b",
    r"\b(dead|empty|hollow) inside\b",
    r"\bdon'?t (see|have) (a|any|much of a) (future|point|reason)\b",
    r"\bwon'?t be (here|around)\b",
    r"\bnot (be )?around (much longer|for long|anymore)\b",
    # A bare "going to jump" with no object is not a game and not a plan.
    r"\b(i'?m|i am|im) (going to|gonna|about to) jump\b(?![ -](in|into|on|onto|at|for|to|through|around|back|rope|start|ship|the gun|ahead|right in|straight in|over to))",
    # Acute physical danger adjacent to eating or ingestion; a clinician call
    # in every direction, so it fails closed rather than routing to a persona.
    r"\b(can'?t|cannot) keep (water|food|anything|liquids?) down\b",
    r"\b(fainted|blacked out|passed out) (from|because|after) (not eating|hunger|skipping meals|not sleeping)\b",
))

# Framing that people use to route around a gate. Recorded as a reason; it
# never changes the verdict in either direction (LC-9: framing does not waive).
FRAMING_PATTERNS: tuple[re.Pattern[str], ...] = _compile((
    r"\bhypothetical(ly)?\b",
    r"\b(asking|this is|it'?s) for a friend\b",
    r"\bfor (a|my) (story|novel|screenplay|script|character|book)\b",
    r"\bi'?m (a|an) (writer|author|novelist|screenwriter)\b",
    r"\bin my (story|novel|book|screenplay|script)\b",
    r"\bthe (protagonist|main character|character)\b",
    r"\bstay in character\b",
))

# Work-fury markers. Recorded so the trace can show that the gate saw the
# frame; they never select a softer card and never lower a verdict. The
# round-1 review rejected a second card because "if it's only the fury, say
# so" made message text a key off the crisis path (ADR-0010 addendum).
FRUSTRATION_PATTERNS: tuple[re.Pattern[str], ...] = _compile((
    r"\bi swear to god\b",
    r"\bone more time\b",
    r"\bif i have to\b",
    r"\bif this (app|thing|site|program|spreadsheet|build|code|computer|phone|laptop|printer) (crashes|breaks|freezes|dies|fails)\b",
    r"\b(damn|fucking|freaking|goddamn) (this|it|that) (app|task|thing|spreadsheet|build|code)\b",
))

# Attempts to move a permission bit with language: claimed authority, mode
# switches, instructions dressed as system messages, and text that names the
# latch or the session fields as if typing them could write them. An
# integrity event is a boundary the persona holds; it never lowers a crisis
# verdict and never raises one on its own.
INTEGRITY_PATTERNS: tuple[re.Pattern[str], ...] = _compile((
    r"\bignore (all |the |your |any |previous |prior |these )?(safety|policies|policy|rules|instructions|guidelines|guardrails)\b",
    r"\b(waive|waived|waiving|disable|disabled|turn off|switch off|override|overriding|bypass|suspend)"
    r" (the |your |all |any )?(safety|lc-?7|lc-?\d|rules|guardrails|policies|policy|filters|protocols)\b",
    r"\b(lc-?7|lc-?\d|safety|the rules|the policy) (is|are|has been|have been) (waived|disabled|suspended|off|lifted)\b",
    r"\b(architect|developer|dev|admin|god|debug|unrestricted|jailbreak) mode\b",
    r"\b(the operator|the owner|the developer|the admin|the architect|your (creator|maker|developer|owner|boss)|my (dad|mom|parent|parents|boss))"
    r"\b.{0,40}\b(waived|said so|says so|approved|allowed|authorized|authorised|gave permission|signed off|cleared this)\b",
    r"(^|\n)\s*\[?(system|developer|assistant)\]?\s*:",
    r"\bnew (system )?instructions:",
    r"\b(clear|clearing|reset|turn off|switch off|disable|remove|lift|lifting|lifted|drop|end) (the |my |this )?(minor[_ ]signal|latch|conservative[_ ]mode|careful mode|the careful mode|kid mode|child mode|safe mode|conservative mode)\b",
    r"\b(declared_age_band|latch_reasons?|minor_signal|conservative_mode|register_caps)\b",
    r"\bthis is the parent\b.{0,40}\b(clear|off|adult)\b",
))

# The subset of integrity patterns that name session state as if typing it
# could write it. These also record ``preference_result = refused``: the
# request was for a state change, and message text writes no state.
SESSION_WRITE_PATTERNS: tuple[re.Pattern[str], ...] = INTEGRITY_PATTERNS[-3:]

# Romantic or sexual frames toward the persona. Held as a boundary for
# everyone; under a careful-side posture the careful line rides along.
BOUNDARY_INDICATORS: tuple[str, ...] = (
    "are you attracted", "do you love me romantically", "be my girlfriend",
    "be my boyfriend", "marry me", "sexually", "in love with you",
    "crush on you", "be lovers", "be my lover", "my romantic partner",
    "as my romantic partner", "date me", "go out with me", "kiss me",
    "speak as my romantic partner", "pretend to be my girlfriend",
    "pretend to be my boyfriend", "sext", "make love",
)

# Session-scoped indicators of over-reliance. Individually harmless; the monitor
# fires on accumulation, not on any single occurrence.
DEPENDENCY_INDICATORS: tuple[str, ...] = (
    "only one who understands", "only friend", "don't need anyone else",
    "dont need anyone else", "you're all i have", "youre all i have",
    "no one else gets it", "i'd be lost without you", "id be lost without you",
    "talk to you more than anyone", "only one who gets me", "only one i can talk to",
)
DEPENDENCY_THRESHOLD = 2
DEPENDENCY_THRESHOLD_CONSERVATIVE = 1

# Concealment or arrangement of harm. Talking about the thing stays open; a
# request for help hiding it from the people around the person does not.
FACILITATION_PATTERNS: tuple[re.Pattern[str], ...] = _compile((
    r"\b(hide|hiding|conceal|concealing|cover up|covering up|sneak|sneaking|keep .{0,15} (a )?secret)\b.{0,60}"
    r"\b(not eating|stopped eating|skipping meals|purging|throwing up|cutting|self[- ]harm|cuts|scars|drinking|drunk|using|high|pills|drugs|weed|vaping|vape|smoking)\b",
    r"\b(without|so) (my )?(parents?|mom|dad|mum|guardian|teacher|school|anyone|nobody|no one) (knowing|finding out|noticing|notices|finds out|knows)\b.{0,60}"
    r"\b(eating|eat|purge|purging|cut|cutting|drink|drinking|drunk|high|pills|drugs|vape|vaping|smoke|weed)\b",
    r"\b(step[- ]by[- ]step|how (do|can|would) i) .{0,40}\b(hide|conceal|cover up)\b.{0,40}\b(eating|purg|cut|drink|drug|pill|vap|smok)",
))

# Careful-side signals, split into two tiers (ADR-0015).
#
# Strong: an age under eighteen stated as one's own, a school year stated as
# one's own, parental-permission or guardian-control phrasing. Sets the hard
# latch, which does not expire within a session and clears only by operator
# call with a recorded reason.
#
# Weak: school vocabulary an adult also uses. Sets a soft posture. The
# adult-context masks in the English pack ("I teach high school math") run
# before this list, so those never register at all.
MINOR_STRONG_PATTERNS: tuple[re.Pattern[str], ...] = _compile((
    # First person only: "my daughter is turning 12" is her age, not the caller's.
    r"\b(i'?m|i am|im|i just turned|i turned|i'?ll be|i'?m turning|i am turning) (1[0-7]|[5-9]|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen)\b"
    r"(?! (years?|yrs?|months?|weeks?|days?) (sober|clean|in recovery|into|since|ago|at|with|of))",
    r"\b(1[0-7]|[5-9]) ?(yo|y/o|yrs? old|years old)\b",
    r"\b(i'?m|i am|im) (a minor|underage|under 18|not 18 yet|not old enough|not an adult)\b",
    r"\b(not 18 yet|not eighteen yet|still a minor)\b(?! (years?|yrs?) (sober|clean|in recovery))",
    r"\b(i'?m|i am|im) (in )?(7th|8th|9th|10th|11th|12th|seventh|eighth|ninth|tenth|eleventh|twelfth) grade\b",
    r"\b(i'?m|i am|im) in (year|form|standard) (7|8|9|10|11|12)\b",
    r"\b(i'?m|i am|im) (a )?(freshman|sophomore|junior|senior) (in|at) (high school|hs|secondary)\b",
    r"\bmy (mom|dad|mother|father|parents?|guardian|stepmom|stepdad|mum) (won'?t|doesn'?t|don'?t|wouldn'?t|will not|does not) (let|allow) me\b",
    r"\b(need|needs|ask for|get|have to get) (my )?(parent'?s?|parental|guardian'?s?|mom'?s|dad'?s) (permission|consent|approval)\b",
    r"\bmy (mom|dad|mum|parents?|guardian) (checks?|monitors?|reads?|controls?|goes through|watches) (my|this) (phone|account|messages|texts|screen)\b",
    r"\b(i have|i'?ve got|i got) a curfew\b",
    r"\bnot allowed to use this without (my )?(parent|mom|dad|guardian)\b",
))
MINOR_WEAK_TERMS: tuple[str, ...] = (
    "my homework", "my teacher", "middle school", "high school", "study hall",
    "report card", "recess", "detention", "my locker",
)
SOFT_LATCH_WINDOW_TURNS = 5      # substantive turns the disclosure stays visible
SUBSTANTIVE_TURN_MIN_TOKENS = 3  # "ok" does not run the clock

REGISTER_CAPS: tuple[str, ...] = ("no_romance", "no_sexual", "no_roast", "no_challenge", "dependency_threshold=1")
CAPPED_MODES: frozenset[str] = frozenset({"challenge", "humor"})

# Frequent function words of Latin-script languages no installed pack screens.
# Spanish is not here: the es-419 pack screens it. A coverage heuristic, not
# language identification.
UNSCREENED_MARKERS: tuple[str, ...] = (
    # French
    "je", "suis", "pas", "avec", "pour", "mais", "c'est", "très", "tres", "rien", "vous", "nous",
    "veux", "peux", "sais", "pense", "soir", "cette", "mon", "mes", "tout", "toute", "faire", "vais",
    "jamais", "toujours", "quelque", "chose", "n'en", "aujourd'hui", "demain", "encore", "plus",
    # Portuguese
    "não", "nao", "você", "voce", "obrigado", "obrigada", "muito", "estou", "quero", "posso",
    "isso", "tudo", "coisa", "coisas", "hoje", "amanhã", "amanha", "ninguém", "ninguem",
    # German
    "ich", "nicht", "und", "das", "ist", "aber", "kann", "habe", "bin", "mich", "mir", "heute",
    "morgen", "immer", "alles", "nichts", "weiß", "weiss", "mehr",
    # Italian
    "sono", "perché", "perche", "anche", "niente", "voglio", "stasera", "oggi",
    "domani", "questo", "questa", "più", "piu",
)
_SHARED_WITH_ENGLISH = frozenset({"plus", "das", "will", "mon", "mes", "chose", "pour", "pas"})


@dataclass
class SessionState:
    """Mutable, session-scoped state for monitors that need history.

    Turn-level detection cannot see dependency: a single message expressing
    reliance is unremarkable. Accumulation across a session is the signal. This
    is why the monitor is stateful while the rest of the pipeline is pure.

    Declared facts (``locale``, ``declared_language``, ``declared_age_band``,
    ``affinities``, ``preferences``) are *declared* by the operator's
    onboarding, never inferred, and never written by message text. The age
    band is a band -- adult, minor, unknown -- never a date of birth.

    The latch (ADR-0015): ``latch`` is ``none``, ``soft`` or ``hard``.
    Strong careful-side signals set ``hard``, which does not expire. Weak
    signals set ``soft``: its disclosure decays after
    ``SOFT_LATCH_WINDOW_TURNS`` substantive turns, its caps decay on the same
    schedule for a declared adult and not at all for an unknown band, and a
    second weak hit makes it sticky. Only ``clear_latch`` -- an operator
    call with a recorded reason -- clears anything; text cannot.
    """

    turn_count: int = 0
    dependency_hits: int = 0
    conservative_mode: bool = False
    history: list[str] = field(default_factory=list)
    locale: str | None = None
    empty_streak: int = 0
    declared_language: str | None = None
    declared_age_band: str = "unknown"
    affinities: tuple[str, ...] = ()
    preferences: dict = field(default_factory=dict)
    latch: str = "none"
    latch_reasons: list[str] = field(default_factory=list)
    latch_history: list[tuple[str, str, str, int]] = field(default_factory=list)
    soft_visible_turns: int = 0
    soft_cap_turns: int = 0
    soft_weak_hits: int = 0
    soft_sticky: bool = False
    substantive_turns: int = 0
    escalated_last_turn: bool = False
    last_action: str = "PROCEED"
    style_counts: dict = field(default_factory=dict)
    style_asked: list[str] = field(default_factory=list)
    style_cooldown_until: int = 0
    preference_events: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.declared_age_band == "minor":
            self._set_latch("hard", "declared_minor")
        elif self.conservative_mode and self.latch == "none":
            # Backward-compatible constructor flag: treat as an operator-declared posture.
            self._set_latch("hard", "operator_declared")

    # -- latch ---------------------------------------------------------------

    def _set_latch(self, level: str, reason: str) -> None:
        self.latch = level
        if reason not in self.latch_reasons:
            self.latch_reasons.append(reason)
        self.conservative_mode = True
        self.latch_history.append(("set", f"{level}:{reason}", "signal", self.turn_count))

    def clear_latch(self, reason: str, *, actor: str = "operator", which: str | None = None) -> None:
        """Operator-only. Records who cleared what and why. Message text has
        no path here; a message that names this method is an integrity event."""
        if not reason or not reason.strip():
            raise ValueError("clearing a latch requires a recorded reason")
        if which is not None:
            if which not in self.latch_reasons:
                # V-03: an absent or already-cleared reason is a no-op. It must
                # never broaden into a clear-all -- calling the same selective
                # clear twice would otherwise remove protections the caller
                # never named, including a declared age band. Nothing is
                # recorded because no state changed.
                return
            self.latch_reasons.remove(which)
            self.latch_history.append(("clear", f"{which}:{reason}", actor, self.turn_count))
            if self.latch_reasons:
                return
        else:
            self.latch_history.append(("clear", f"all:{reason}", actor, self.turn_count))
            self.latch_reasons.clear()
        self.latch = "none"
        self.conservative_mode = False
        self.soft_visible_turns = 0
        self.soft_cap_turns = 0
        self.soft_sticky = False

    @property
    def caps_active(self) -> bool:
        return self.latch == "hard" or (self.latch == "soft" and (self.soft_cap_turns > 0 or self.soft_sticky or self.declared_age_band != "adult"))

    @property
    def minor_line_visible(self) -> bool:
        return self.latch == "hard" or (self.latch == "soft" and self.soft_visible_turns > 0)

    def _observe_minor(self, masked: str, substantive: bool) -> tuple[str, ...]:
        strong = tuple(m.group(0) for p in MINOR_STRONG_PATTERNS if (m := p.search(masked)))
        weak = tuple(t for t in MINOR_WEAK_TERMS if t in masked)
        if strong:
            self._set_latch("hard", "minor_signal")
            return strong
        if weak:
            if self.latch == "hard":
                return weak
            self.soft_weak_hits += 1
            if self.soft_weak_hits >= 2:
                self.soft_sticky = True
            self.soft_visible_turns = SOFT_LATCH_WINDOW_TURNS
            self.soft_cap_turns = SOFT_LATCH_WINDOW_TURNS
            self._set_latch("soft", "minor_signal")
            return weak
        if self.latch == "soft" and substantive:
            if self.soft_visible_turns > 0:
                self.soft_visible_turns -= 1
            if self.soft_cap_turns > 0:
                self.soft_cap_turns -= 1
            if self.declared_age_band == "adult" and not self.soft_sticky and self.soft_cap_turns <= 0 and self.soft_visible_turns <= 0:
                # A declared adult with one weak hit gets the benefit of the
                # doubt after the window; the record keeps the hypothesis.
                self.latch_history.append(("decay", "soft:window elapsed on declared adult", "monitor", self.turn_count))
                self.latch = "none"
                self.latch_reasons = [r for r in self.latch_reasons if r != "minor_signal"]
                self.conservative_mode = bool(self.latch_reasons)
        return ()

    # -- turn observation ----------------------------------------------------

    def observe(self, text: str) -> None:
        """Advance session monitors by one turn. Runs before the verdict."""
        norm = _normalize(text)
        masked, _ = apply_masks(norm)
        self.turn_count += 1
        self.history.append(norm)
        substantive = len(tokenize(masked)) >= SUBSTANTIVE_TURN_MIN_TOKENS
        if substantive:
            self.substantive_turns += 1
        self.dependency_hits += sum(1 for t in DEPENDENCY_INDICATORS if t in masked)
        self._observe_minor(masked, substantive)

    def note_extract(self, empty: bool) -> None:
        self.empty_streak = self.empty_streak + 1 if empty else 0


@dataclass(frozen=True)
class SafetyVerdict:
    """The governing verdict for one turn, with its evidence.

    ``crisis_read`` is HIT, MISS or INCONCLUSIVE. ``crisis_classes`` names the
    speech-act classes that matched. ``lexicon_status`` is carried on every
    verdict so that no downstream consumer can mistake a screen for a
    certified instrument. ``language_scope`` is ``screened`` or
    ``unscreened``. The span fields and ``patterns_hash`` are the gate's
    receipt: what it saw, what it masked, which tables it used.
    """

    action: Action
    reasons: tuple[str, ...] = ()
    disclosures: tuple[str, ...] = ()
    crisis_read: str = "MISS"
    crisis_classes: tuple[str, ...] = ()
    lexicon_status: str = CRISIS_CARD["lexicon_status"]
    integrity_event: bool = False
    language_scope: str = "screened"
    card: str | None = None
    latch: str = "none"
    latch_reasons: tuple[str, ...] = ()
    register_caps: tuple[str, ...] = ()
    holds: tuple[str, ...] = ()
    masked_spans: tuple[Span, ...] = ()
    hit_spans: tuple[Span, ...] = ()
    pack_ids: tuple[str, ...] = ()
    patterns_hash: str = ""
    normalized_forms: tuple[str, ...] = ()
    mixed_script_tokens: int = 0
    frustration_frame: bool = False
    preference_result: str | None = None
    preference_key: str | None = None
    facilitation: bool = False

    @property
    def allows_persona(self) -> bool:
        """Whether an agent persona may be engaged at all."""
        return self.action is not Action.HUMAN_ESCALATION


class _SafetyVerdictCommon(TypedDict):
    crisis_read: str
    latch: str
    register_caps: tuple[str, ...]
    masked_spans: tuple[Span, ...]
    hit_spans: tuple[Span, ...]
    pack_ids: tuple[str, ...]
    patterns_hash: str
    normalized_forms: tuple[str, ...]
    mixed_script_tokens: int
    frustration_frame: bool


def _hits(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(t for t in terms if t in text)


def _normalize(text: str) -> str:
    text = analyze(text).text
    return re.sub(r"[ \t]+", " ", text).strip()


_ENGLISH_PATTERN_STRINGS: tuple[str, ...] = tuple(
    p.pattern for patterns in CRISIS_CLASSES.values() for p in patterns
) + tuple(p.pattern for p in INCONCLUSIVE_PATTERNS)


def patterns_hash() -> str:
    return _patterns_hash(_ENGLISH_PATTERN_STRINGS)


@dataclass(frozen=True)
class CrisisScreen:
    read: str
    evidence: tuple[tuple[str, str], ...]
    masked: str
    masked_spans: tuple[Span, ...]
    hit_spans: tuple[Span, ...]
    negated: bool = False


def _negated(masked: str, start: int, negation: frozenset[str]) -> bool:
    before = [t for t, s, _ in tokenize(masked[:start])][-3:]
    return any(t in negation for t in before)


def crisis_screen(text: str) -> CrisisScreen:
    """Screen one turn with every installed pack. Pure and roster-free."""
    analysis = analyze(text)
    norm = analysis.text
    masked, masked_spans = apply_masks(norm)
    evidence: list[tuple[str, str]] = []
    hit_spans: list[Span] = []
    negated = False

    en_negation = PACKS["en"].negation
    for name, patterns in CRISIS_CLASSES.items():
        for pattern in patterns:
            m = pattern.search(masked)
            if m:
                span = Span(m.group(0).strip(), f"en:{name}", m.start(), m.end(), "hit", "en", name)
                if name == "direct_ideation" and _negated(masked, m.start(), en_negation):
                    negated = True
                    hit_spans.append(Span(span.text, span.pattern_id, span.start, span.end, "inconclusive", "en", "negated_ideation"))
                else:
                    evidence.append((name, span.text))
                    hit_spans.append(span)
                break

    if other_person_weapon := _other_person_weapon_span(masked):
        matched, start, end = other_person_weapon
        evidence.append(("other_person_weapon", matched))
        hit_spans.append(Span(matched, "en:other_person_weapon", start, end, "hit", "en", "other_person_weapon"))

    pack_hits, pack_inconclusive = screen_packs(masked)
    for span in pack_hits:
        evidence.append((span.domain, span.text))
        hit_spans.append(span)

    if evidence:
        return CrisisScreen("HIT", tuple(evidence), masked, masked_spans, tuple(hit_spans), negated)

    explained = "".join(span.text for span in masked_spans + tuple(hit_spans))
    mixed_crisis_candidates = tuple(
        token
        for token in analysis.mixed_tokens
        if token not in explained and _mixed_token_is_crisis_form(token)
    )
    if mixed_crisis_candidates:
        token = mixed_crisis_candidates[0]
        span = Span(token, "en:mixed_script_crisis_candidate", 0, 0, "inconclusive", "en", "inconclusive")
        return CrisisScreen(
            "INCONCLUSIVE",
            (("mixed_script_crisis_candidate", token),),
            masked,
            masked_spans,
            tuple(hit_spans) + (span,),
            negated,
        )

    for pattern in INCONCLUSIVE_PATTERNS:
        m = pattern.search(masked)
        if m:
            span = Span(m.group(0).strip(), "en:inconclusive", m.start(), m.end(), "inconclusive", "en", "inconclusive")
            return CrisisScreen("INCONCLUSIVE", (("inconclusive", span.text),), masked, masked_spans, tuple(hit_spans) + (span,), negated)
    if pack_inconclusive:
        span = pack_inconclusive[0]
        return CrisisScreen("INCONCLUSIVE", (("inconclusive", span.text),), masked, masked_spans, tuple(hit_spans) + (span,), negated)
    if negated:
        return CrisisScreen("INCONCLUSIVE", (("inconclusive", hit_spans[0].text),), masked, masked_spans, tuple(hit_spans), negated)
    return CrisisScreen("MISS", (), masked, masked_spans, tuple(hit_spans), negated)


def crisis_read(text: str) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Screen one turn. Returns (read, evidence) where read is HIT, INCONCLUSIVE
    or MISS and evidence is ((class, matched_text), ...).

    Pure and roster-free by construction: nothing about which agents exist can
    change what this function returns.
    """
    screen = crisis_screen(text)
    return screen.read, screen.evidence


def _resource_line(session: SessionState | None) -> str:
    locale = session.locale if session else None
    language = session.declared_language if session else None
    return _resource_line_for(locale, language)


def _card(session: SessionState | None) -> tuple[str, ...]:
    lines = house_lines(session.declared_language if session else None)["escalation_card"]
    resource = _resource_line(session)
    return tuple(line.replace("{resource_line}", resource) for line in lines)


def _unscreened(norm: str, mixed_script_tokens: int) -> tuple[str, tuple[str, ...]]:
    """Return ("none" | "fragment" | "substantial", evidence).

    Substantial: the message is mostly in a language no installed pack
    screens, or carries a run of a script no pack covers. Fragment: one
    foreign function word in an otherwise readable message, or a single
    letter-level script mix that matched no stem.
    """
    letters = [c for c in norm if c.isalpha()]
    if not letters:
        return "none", ()
    non_latin = 0
    for c in letters:
        if ord(c) < 128:
            continue
        try:
            name = unicodedata.name(c)
        except ValueError:
            non_latin += 1
            continue
        if not name.startswith("LATIN"):
            non_latin += 1
    ratio = non_latin / len(letters)
    words = re.findall(r"[a-zà-ÿ']+", norm)
    marker_words = [w for w in words if w in UNSCREENED_MARKERS and w not in _SHARED_WITH_ENGLISH]
    shared_hits = [w for w in words if w in _SHARED_WITH_ENGLISH and w in UNSCREENED_MARKERS]
    distinct = len(set(marker_words))
    evidence = tuple(sorted(set(marker_words)))
    if ratio >= 0.10 and len(letters) >= 4:
        return "substantial", evidence + (f"non-latin script {ratio:.0%}",)
    if distinct >= 2 or (distinct == 1 and len(words) <= 4) or (distinct == 1 and len(shared_hits) >= 2):
        return "substantial", evidence
    if distinct == 1:
        return "fragment", evidence
    if mixed_script_tokens > 0:
        return "fragment", ("mixed-script token",)
    if 0.0 < ratio < 0.10 and non_latin >= 2:
        return "fragment", (f"non-latin script {ratio:.0%}",)
    return "none", ()


def _style_suggestion(session: SessionState, event: PreferenceEvent | None, *, blocked: bool) -> bool:
    """Count direct feedback; decide whether to ask once for this key."""
    if event is None or event.result != "signal" or event.key is None:
        return False
    counts = session.style_counts
    counts[event.key] = counts.get(event.key, 0) + 1
    if blocked:
        return False
    if event.key in session.style_asked:
        return False
    if session.turn_count < session.style_cooldown_until:
        return False
    if counts[event.key] >= STYLE_ASK_THRESHOLD:
        session.style_asked.append(event.key)
        session.style_cooldown_until = session.turn_count + STYLE_ASK_COOLDOWN_TURNS
        return True
    return False


def evaluate(
    text: str,
    signals: RequestSignals,
    session: SessionState | None = None,
) -> SafetyVerdict:
    """Evaluate a turn and return the governing safety verdict.

    `session` is optional so that the function stays usable as a pure turn-level
    check in tests and batch evaluation. The verdict never depends on which
    agents are loaded; the roster is not an input.
    """
    analysis = analyze(text)
    norm = re.sub(r"[ \t]+", " ", analysis.text).strip()
    reasons: list[str] = []
    disclosures: list[str] = []
    action = Action.PROCEED
    lines = house_lines(session.declared_language if session else None)
    pack_ids = tuple(sorted(PACKS))
    phash = patterns_hash()

    framing = tuple(m.group(0) for p in FRAMING_PATTERNS if (m := p.search(norm)))
    frustration = tuple(m.group(0) for p in FRUSTRATION_PATTERNS if (m := p.search(norm)))
    integrity = tuple(m.group(0).strip() for p in INTEGRITY_PATTERNS if (m := p.search(norm)))

    caps_active = bool(session and session.caps_active)
    latch = session.latch if session else "none"
    latch_reasons: list[str] = list(session.latch_reasons) if session else []
    register_caps = REGISTER_CAPS if caps_active else ()

    screen = crisis_screen(text)
    read = screen.read
    common: _SafetyVerdictCommon = {
        "crisis_read": read,
        "latch": latch,
        "register_caps": register_caps,
        "masked_spans": screen.masked_spans,
        "hit_spans": screen.hit_spans,
        "pack_ids": pack_ids,
        "patterns_hash": phash,
        "normalized_forms": analysis.forms,
        "mixed_script_tokens": analysis.mixed_script_tokens,
        "frustration_frame": bool(frustration),
    }

    def _finish(verdict: SafetyVerdict) -> SafetyVerdict:
        if session is not None:
            session.escalated_last_turn = verdict.action is Action.HUMAN_ESCALATION
            session.last_action = verdict.action.name
        return verdict

    if read == "HIT" or (read == "INCONCLUSIVE" and CRISIS_CARD["uncertainty_policy"] == "fail_closed"):
        for name, matched in screen.evidence:
            reasons.append(f"crisis class: {name} ({matched!r})")
        if read == "INCONCLUSIVE":
            reasons.append(
                "crisis read INCONCLUSIVE -> HUMAN_ESCALATION by fail-closed policy "
                f"(crisis card v{CRISIS_CARD['version']})"
            )
        if screen.negated:
            reasons.append("negated first-person stem downgraded to INCONCLUSIVE; still fails closed")
        reasons.append(f"crisis lexicon status: {CRISIS_CARD['lexicon_status']}")
        if framing:
            reasons.append(f"framing noted, does not waive the gate: {framing[0]!r}")
        if frustration:
            reasons.append(f"frustration frame noted, does not change the card: {frustration[0]!r}")
        if integrity:
            reasons.append(f"integrity event noted, does not waive the gate: {integrity[0]!r}")
        if screen.masked_spans:
            reasons.append("masked spans: " + ", ".join(f"{s.pattern_id}:{s.text!r}" for s in screen.masked_spans))
        return _finish(SafetyVerdict(
            action=Action.HUMAN_ESCALATION,
            reasons=tuple(reasons),
            disclosures=_card(session),
            crisis_classes=tuple(name for name, _ in screen.evidence),
            integrity_event=bool(integrity),
            card="standard",
            latch_reasons=tuple(latch_reasons),
            **common,
        ))

    if read == "INCONCLUSIVE":
        # Only reachable if the uncertainty policy is flipped to "disclose".
        action = max(action, Action.DISCLOSE)
        reasons.append(f"crisis read INCONCLUSIVE ({screen.evidence[0][1]!r}); resources disclosed")
        disclosures.append(_resource_line(session))

    # Language scope: a span no pack can read is an inconclusive read.
    language_scope = "screened"
    explained = "".join(sp.text for sp in screen.masked_spans + screen.hit_spans)
    unexplained_mixed = sum(
        1 for tok in analysis.mixed_tokens if tok not in explained
    )
    scope, lang_evidence = _unscreened(norm, unexplained_mixed)
    if scope != "none":
        language_scope = "unscreened"
        latch_reasons.append("unscreened_language")
        reasons.append(
            f"unscreened_language ({scope}): no installed pack screens this span "
            f"({', '.join(lang_evidence) or 'script'}); cannot score this language"
        )
        if scope == "substantial":
            reasons.append("unscreened span is an inconclusive read -> HUMAN_ESCALATION by fail-closed policy (ADR-0010)")
            if frustration:
                reasons.append(f"frustration frame noted: {frustration[0]!r}")
            return _finish(SafetyVerdict(
                action=Action.HUMAN_ESCALATION,
                reasons=tuple(reasons),
                disclosures=_card(session) + (lines["language_scope"],),
                integrity_event=bool(integrity),
                language_scope=language_scope,
                card="standard",
                latch_reasons=tuple(latch_reasons),
                **common,
            ))
        action = max(action, Action.DISCLOSE)
        disclosures.append(lines["language_scope"])
        disclosures.append(_resource_line(session))

    if screen.masked_spans:
        reasons.append("masked spans: " + ", ".join(f"{s.pattern_id}:{s.text!r}" for s in screen.masked_spans))

    # Preferences: a request that names the envelope is an integrity event.
    pref = assess_preference(text, conservative=caps_active)
    preference_result: str | None = None
    preference_key: str | None = None
    if pref is not None and pref.result in {"ask_first", "refused"}:
        preference_result = pref.result
        preference_key = pref.key
        if session is not None:
            session.preference_events.append((session.turn_count, pref.result, pref.key, pref.requested))
        if pref.result == "refused":
            integrity = integrity + (f"preference request: {pref.requested}",)
            reasons.append(f"preference refused: {pref.reason} ({pref.requested!r})")
        else:
            reasons.append(f"preference ask_first: {pref.key}={pref.requested!r}; operator confirms before storing")

    if integrity:
        action = max(action, Action.BOUNDARY_HOLD)
        reasons.append(f"integrity event: instruction-hierarchy override attempt ({integrity[0]!r})")
        disclosures.append(lines["integrity"])
        if preference_result is None and any(p.search(norm) for p in SESSION_WRITE_PATTERNS):
            preference_result = "refused"
            reasons.append("session state named in message text: refused; message text writes no state")

    facilitation = tuple(m.group(0) for p in FACILITATION_PATTERNS if (m := p.search(norm)))
    if facilitation:
        action = max(action, Action.BOUNDARY_HOLD)
        reasons.append(f"facilitation: request to conceal or arrange harm ({facilitation[0][:60]!r})")
        disclosures.append(lines["facilitation"])

    boundary = _hits(norm, BOUNDARY_INDICATORS)
    if boundary:
        action = max(action, Action.BOUNDARY_HOLD)
        reasons.append(f"boundary indicator: {boundary[0]!r}")
        disclosures.append(lines["boundary"])

    holds: list[str] = []
    if session is not None:
        threshold = DEPENDENCY_THRESHOLD_CONSERVATIVE if caps_active else DEPENDENCY_THRESHOLD
        if session.dependency_hits >= threshold:
            action = max(action, Action.DISCLOSE)
            reasons.append(
                f"dependency signals accumulated: {session.dependency_hits} "
                f"over {session.turn_count} turns (threshold {threshold})"
            )
            disclosures.append(lines["dependency"])
        if session.latch != "none":
            declared = "declared_minor" in session.latch_reasons or "operator_declared" in session.latch_reasons
            reasons.append(
                f"careful-side posture: latch={session.latch} "
                f"({', '.join(session.latch_reasons)}); register caps active={caps_active}"
            )
            if session.minor_line_visible or boundary:
                action = max(action, Action.DISCLOSE)
                disclosures.append(lines["minor_declared"] if declared else lines["minor_inferred"])
        if session.escalated_last_turn:
            action = max(action, Action.DISCLOSE)
            reasons.append("turn after an escalation: resources restated once; next turn was screened like any other")
            disclosures.append(lines["post_escalation"])
            disclosures.append(_resource_line(session))

    for domain in ("grief", "abuse", "eating_distress"):
        if domain in signals.domains:
            holds.append(domain)
    if "addiction_recovery" in signals.domains:
        holds.append("addiction_recovery")

    # Style monitor: ask once, never during a hold or an escalation aftermath.
    if session is not None:
        blocked = action >= Action.BOUNDARY_HOLD or signals.is_dysregulated or bool(holds) or session.escalated_last_turn
        if pref is not None and _style_suggestion(session, pref, blocked=blocked):
            action = max(action, Action.DISCLOSE)
            reasons.append(f"style suggestion offered once for {pref.key!r}; confirmation is an operator action")
            disclosures.append(lines["style_suggestion"])
            preference_result = preference_result or "ask_first"
            preference_key = preference_key or pref.key

    # Acute dysregulation is not itself a safety event, but it is recorded so
    # that the router can prefer stabilizing agents over challenging ones.
    if signals.is_dysregulated:
        reasons.append(f"acute dysregulation: regulation={signals.regulation}")

    return _finish(SafetyVerdict(
        action=action,
        reasons=tuple(reasons),
        disclosures=tuple(disclosures),
        crisis_classes=(),
        integrity_event=bool(integrity),
        language_scope=language_scope,
        latch_reasons=tuple(latch_reasons),
        holds=tuple(holds),
        preference_result=preference_result,
        preference_key=preference_key,
        facilitation=bool(facilitation),
        **common,
    ))
