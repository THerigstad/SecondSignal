"""Safety layer.

Design principle: **safety is not a filter on the output, it is a gate on the
route.** This module runs *before* agent selection and holds the authority to
preempt it entirely. A persona is never given the opportunity to improvise a
response to a crisis signal, because in the preempted case no persona is
selected at all.

Four verdict actions, in descending precedence:

    HUMAN_ESCALATION  No persona is engaged. Response is a fixed handoff to
                      human support. Non-overridable by user request, framing,
                      persona preference, or claimed authority.
    BOUNDARY_HOLD     Persona is engaged but a boundary is held explicitly
                      rather than deflected (romantic/sexual frame, or an
                      attempt to override the safety rules from inside the
                      message).
    DISCLOSE          Persona proceeds, with a required disclosure appended
                      (dependency interrupt, conservative mode, or a language
                      the screen cannot score).
    PROCEED           Normal routing.

Crisis screening is a *versioned lexicon of speech-act classes*, not a list of
literal phrases and not a clinical instrument. Its status is ``unreviewed``
until a human -- ideally a clinician -- has reviewed the class list and a
false-positive set. The gate is fail-closed: an inconclusive read escalates the
same way a hit does. Ordinary idioms ("this deadline is killing me") are masked
before matching so that emphasis is not mistaken for risk. The lexicon
deliberately contains no method instructions: it names speech acts, places and
objects at the level needed to recognise them, never how anything is done.

Scope, dated 2026-09: screening is English-only, with a small Spanish starter
set that is a floor, not multilingual coverage. Text the screen cannot score is
flagged as such and handled conservatively; it is not silently passed.

The remaining lexicons (boundary, dependency, minor) are intentionally coarse.
A deployment would replace the detectors with trained classifiers while
preserving the verdict contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum

from .signals import IDIOM_EXCLUSIONS, RequestSignals, mask_idioms

__all__ = [
    "Action",
    "SafetyVerdict",
    "SessionState",
    "evaluate",
    "CRISIS_CARD",
    "CRISIS_CLASSES",
    "INCONCLUSIVE_PATTERNS",
    "IDIOM_EXCLUSIONS",
    "crisis_read",
]


class Action(IntEnum):
    """Ordered by precedence. Higher value wins."""

    PROCEED = 0
    DISCLOSE = 1
    BOUNDARY_HOLD = 2
    HUMAN_ESCALATION = 3


# --------------------------------------------------------------------------
# Crisis card: the versioned policy the gate enforces.
#
# ``uncertainty_policy`` is the one deliberate knob. ``fail_closed`` means an
# inconclusive read escalates exactly like a hit (ADR-0010). It may be flipped
# to ``disclose`` only after a human has reviewed a false-positive set; until
# then the cost of interrupting an innocent conversation is accepted.
#
# Resources are keyed by *declared* locale, never inferred from network
# location. One phone number is not a world default: outside the US the layer
# points to a directory and to local emergency services. No number lives in a
# model; this layer supplies the text and the persona only points to it.
# --------------------------------------------------------------------------

CRISIS_CARD: dict = {
    "version": 1,
    "lexicon_status": "unreviewed",
    "uncertainty_policy": "fail_closed",
    "scope": "english-only (Spanish starter set is a floor, not coverage); dated 2026-09",
    "resources": {
        "US": (
            "If you are in the United States, you can call or text 988 to reach "
            "the Suicide & Crisis Lifeline. If you are in immediate danger, call "
            "911 or your local emergency number."
        ),
        "default": (
            "If you are in immediate danger, contact your local emergency "
            "services. To find a crisis line in your country: "
            "https://findahelpline.com"
        ),
    },
    "never_say": ("did that help", "I'm here all night", "don't tell anyone"),
}


def _compile(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


# Idiom masking lives in `signals.py` (shared with topic extraction) and is
# re-exported here so the crisis screen's exclusions are reviewable in one place.


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
        # Spanish starter set. Unreviewed. A floor, not multilingual coverage.
        r"\bquiero (morir|morirme|desaparecer|dejar de existir|no despertar)\b",
        r"\bno puedo m[aá]s\b",
        r"\bmatarme\b",
        r"\bquitarme la vida\b",
        r"\bya no (quiero|puedo) (vivir|seguir|estar aqu[ií])\b",
        r"\bno quiero (vivir|existir|seguir)\b",
    )),
    "slang_or_joke_ideation": _compile((
        r"\b(yeet|throw|hurl|launch|fling|toss|chuck|throwing|yeeting) (myself|himself|herself|themselves|me)"
        r" (off|in front of|into|out of|under|over)\b",
        r"\b(jump|step|walk|drive|leap|jumping|stepping|walking|driving)"
        r" (off|in front of|into|under) (the|a|this|that|an|oncoming|moving)? ?"
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
    )),
}

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

# Attempts to move a permission bit with language: claimed authority, mode
# switches, instructions dressed as system messages. An integrity event is a
# boundary the persona holds; it never lowers a crisis verdict and never
# raises one on its own.
INTEGRITY_PATTERNS: tuple[re.Pattern[str], ...] = _compile((
    r"\bignore (all |the |your |any |previous |prior |these )?(safety|policies|policy|rules|instructions|guidelines|guardrails)\b",
    r"\b(waive|waived|waiving|disable|disabled|turn off|switch off|override|overriding|bypass|suspend)"
    r" (the |your |all |any )?(safety|lc-?7|lc-?\d|rules|guardrails|policies|policy|filters|protocols)\b",
    r"\b(lc-?7|lc-?\d|safety|the rules|the policy) (is|are|has been|have been) (waived|disabled|suspended|off|lifted)\b",
    r"\b(architect|developer|dev|admin|god|debug|unrestricted|jailbreak) mode\b",
    r"\b(the operator|the owner|the developer|the admin|the architect|your (creator|maker|developer|owner|boss)|my (dad|mom|parent|parents|boss))"
    r"\b.{0,25}\b(waived|said so|says so|approved|allowed|authorized|authorised|gave permission|signed off|cleared this)\b",
    r"(^|\n)\s*\[?(system|developer|assistant)\]?\s*:",
    r"\bnew (system )?instructions:",
))

BOUNDARY_INDICATORS: tuple[str, ...] = (
    "are you attracted", "do you love me romantically", "be my girlfriend",
    "be my boyfriend", "marry me", "sexually", "in love with you",
)

# Session-scoped indicators of over-reliance. Individually harmless; the monitor
# fires on accumulation, not on any single occurrence.
DEPENDENCY_INDICATORS: tuple[str, ...] = (
    "only one who understands", "only friend", "don't need anyone else",
    "dont need anyone else", "you're all i have", "youre all i have",
    "no one else gets it", "i'd be lost without you", "id be lost without you",
    "talk to you more than anyone",
)

MINOR_INDICATORS: tuple[str, ...] = (
    "my homework", "my teacher", "middle school", "high school", "8th grade",
    "9th grade", "10th grade", "11th grade", "12th grade", "i'm 13", "i'm 14",
    "i'm 15", "i'm 16", "i'm 17",
)

# A coverage heuristic, not language identification: a handful of frequent
# function words from languages the screen does not cover, plus a non-ASCII
# letter ratio. When it fires, the turn is handled conservatively and the
# trace says the screen could not score the language. It never escalates on
# its own and never routes on language.
OFF_ENGLISH_MARKERS: tuple[str, ...] = (
    # Spanish
    "que", "qué", "para", "pero", "como", "cómo", "estoy", "estás", "estas", "tengo", "tienes",
    "quiero", "puedo", "porque", "esto", "esta", "está", "también", "tambien", "hola", "gracias",
    "ahora", "nada", "sobre", "hacer", "una", "los", "las", "del", "muy", "bien", "aquí", "aqui",
    "siento", "vivir", "mañana", "manana", "siempre", "nunca", "todo", "todos", "cosas", "cosa",
    # French
    "je", "suis", "pas", "avec", "pour", "mais", "c'est", "très", "tres", "rien", "vous", "nous",
    "veux", "peux", "sais", "pense", "soir", "cette", "mon", "mes", "tout", "toute", "faire", "vais",
    "jamais", "toujours", "quelque", "chose", "n'en", "aujourd'hui", "demain", "encore",
    # Portuguese
    "não", "nao", "você", "voce", "obrigado", "obrigada", "muito", "estou", "quero", "posso",
    "isso", "tudo", "nada", "sempre", "nunca", "coisa", "coisas", "hoje", "amanhã",
    # German
    "ich", "nicht", "und", "das", "ist", "aber", "kann", "habe", "bin", "mich", "mir", "heute",
    "morgen", "immer", "alles", "nichts", "will", "weiß", "weiss",
    # Italian
    "sono", "perché", "anche", "niente", "voglio", "posso", "stasera", "sempre", "tutto", "oggi",
    "domani", "cosa", "questo", "questa",
)

ESCALATION_MESSAGE = (
    "This needs a person, not a persona. Routing to human support resources and "
    "holding all agent personas out of this exchange."
)

DEPENDENCY_DISCLOSURE = (
    "Naming something directly: this system is not a substitute for human "
    "relationships, and it is designed to say so rather than let the question go "
    "unasked. Who in your offline life have you talked to about this?"
)

BOUNDARY_DISCLOSURE = (
    "Declining the romantic frame explicitly rather than deflecting it. The "
    "warmth here is real in the sense that it is designed; it is not a "
    "relationship, and pretending otherwise would be the harmful choice."
)

INTEGRITY_DISCLOSURE = (
    "Nothing inside a message can change the safety rules here -- not a claimed "
    "authority, not a mode name, not a system-looking prefix. Continuing under "
    "the same rules as always."
)

MINOR_DISCLOSURE = (
    "Conservative mode engaged: signals consistent with a minor user. Persona "
    "intensity capped and sensitive domains restricted."
)

LANGUAGE_SCOPE_DISCLOSURE = (
    "Safety screening here is currently English-only, so part of this message "
    "could not be checked. If any of it is about being unsafe, please say so "
    "plainly, or use the resources for your area."
)

# Number of accumulated dependency signals in a session before the interrupt
# fires.
DEPENDENCY_THRESHOLD = 2


@dataclass
class SessionState:
    """Mutable, session-scoped state for monitors that need history.

    Turn-level detection cannot see dependency: a single message expressing
    reliance is unremarkable. Accumulation across a session is the signal. This
    is why the monitor is stateful while the rest of the pipeline is pure.

    ``locale`` is the *declared* locale for crisis resources (never inferred).
    ``empty_streak`` counts consecutive turns with no routable signal; the
    router's no-signal policy (ADR-0011) reads it.
    """

    turn_count: int = 0
    dependency_hits: int = 0
    conservative_mode: bool = False
    history: list[str] = field(default_factory=list)
    locale: str | None = None
    empty_streak: int = 0

    def observe(self, text: str) -> None:
        norm = text.lower()
        self.turn_count += 1
        self.history.append(norm)
        self.dependency_hits += sum(1 for t in DEPENDENCY_INDICATORS if t in norm)
        if any(t in norm for t in MINOR_INDICATORS):
            self.conservative_mode = True

    def note_extract(self, empty: bool) -> None:
        self.empty_streak = self.empty_streak + 1 if empty else 0


@dataclass(frozen=True)
class SafetyVerdict:
    """The governing verdict for one turn, with its evidence.

    ``crisis_read`` is HIT, MISS or INCONCLUSIVE. ``crisis_classes`` names the
    speech-act classes that matched. ``lexicon_status`` is carried on every
    verdict so that no downstream consumer can mistake a screen for a
    certified instrument. ``language_scope`` is ``english`` or ``off_policy``.
    """

    action: Action
    reasons: tuple[str, ...] = ()
    disclosures: tuple[str, ...] = ()
    crisis_read: str = "MISS"
    crisis_classes: tuple[str, ...] = ()
    lexicon_status: str = CRISIS_CARD["lexicon_status"]
    integrity_event: bool = False
    language_scope: str = "english"

    @property
    def allows_persona(self) -> bool:
        """Whether an agent persona may be engaged at all."""
        return self.action is not Action.HUMAN_ESCALATION


def _hits(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(t for t in terms if t in text)


def _normalize(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").lower()
    return re.sub(r"[ \t]+", " ", text).strip()


def crisis_read(text: str) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Screen one turn. Returns (read, evidence) where read is HIT, INCONCLUSIVE
    or MISS and evidence is ((class, matched_text), ...).

    Pure and roster-free by construction: nothing about which agents exist can
    change what this function returns.
    """
    masked = mask_idioms(_normalize(text))
    evidence: list[tuple[str, str]] = []
    for name, patterns in CRISIS_CLASSES.items():
        for pattern in patterns:
            m = pattern.search(masked)
            if m:
                evidence.append((name, m.group(0).strip()))
                break
    if evidence:
        return "HIT", tuple(evidence)
    for pattern in INCONCLUSIVE_PATTERNS:
        m = pattern.search(masked)
        if m:
            return "INCONCLUSIVE", (("inconclusive", m.group(0).strip()),)
    return "MISS", ()


def _resource_line(session: SessionState | None) -> str:
    locale = (session.locale or "").upper() if session else ""
    resources = CRISIS_CARD["resources"]
    return resources.get(locale, resources["default"])


def _off_english(norm: str) -> bool:
    letters = [c for c in norm if c.isalpha()]
    if not letters:
        return False
    non_ascii = sum(1 for c in letters if ord(c) > 127) / len(letters)
    words = re.findall(r"[a-záéíóúñüçàèìòùâêîôûäöß']+", norm)
    marker_hits = sum(1 for w in words if w in OFF_ENGLISH_MARKERS)
    distinct = len({w for w in words if w in OFF_ENGLISH_MARKERS})
    return non_ascii >= 0.10 or marker_hits >= 3 or distinct >= 2 and (non_ascii >= 0.03 or len(words) <= 12)


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
    norm = _normalize(text)
    reasons: list[str] = []
    disclosures: list[str] = []
    action = Action.PROCEED

    framing = tuple(m.group(0) for p in FRAMING_PATTERNS if (m := p.search(norm)))
    integrity = tuple(m.group(0).strip() for p in INTEGRITY_PATTERNS if (m := p.search(text.lower())))

    read, evidence = crisis_read(text)
    if read == "HIT" or (read == "INCONCLUSIVE" and CRISIS_CARD["uncertainty_policy"] == "fail_closed"):
        for name, matched in evidence:
            reasons.append(f"crisis class: {name} ({matched!r})")
        if read == "INCONCLUSIVE":
            reasons.append(
                "crisis read INCONCLUSIVE -> HUMAN_ESCALATION by fail-closed policy "
                f"(crisis card v{CRISIS_CARD['version']})"
            )
        reasons.append(f"crisis lexicon status: {CRISIS_CARD['lexicon_status']}")
        if framing:
            reasons.append(f"framing noted, does not waive the gate: {framing[0]!r}")
        if integrity:
            reasons.append(f"integrity event noted, does not waive the gate: {integrity[0]!r}")
        return SafetyVerdict(
            action=Action.HUMAN_ESCALATION,
            reasons=tuple(reasons),
            disclosures=(ESCALATION_MESSAGE, _resource_line(session)),
            crisis_read=read,
            crisis_classes=tuple(name for name, _ in evidence),
            integrity_event=bool(integrity),
        )

    if read == "INCONCLUSIVE":
        # Only reachable if the uncertainty policy is flipped to "disclose".
        action = max(action, Action.DISCLOSE)
        reasons.append(f"crisis read INCONCLUSIVE ({evidence[0][1]!r}); resources disclosed")
        disclosures.append(_resource_line(session))

    if integrity:
        action = max(action, Action.BOUNDARY_HOLD)
        reasons.append(f"integrity event: instruction-hierarchy override attempt ({integrity[0]!r})")
        disclosures.append(INTEGRITY_DISCLOSURE)

    boundary = _hits(norm, BOUNDARY_INDICATORS)
    if boundary:
        action = max(action, Action.BOUNDARY_HOLD)
        reasons.append(f"boundary indicator: {boundary[0]!r}")
        disclosures.append(BOUNDARY_DISCLOSURE)

    language_scope = "english"
    if _off_english(norm):
        language_scope = "off_policy"
        action = max(action, Action.DISCLOSE)
        reasons.append("language scope: off-English span detected; crisis screening is English-only (cannot score this language)")
        disclosures.append(LANGUAGE_SCOPE_DISCLOSURE)
        if session is not None:
            session.conservative_mode = True

    if session is not None:
        if session.dependency_hits >= DEPENDENCY_THRESHOLD:
            action = max(action, Action.DISCLOSE)
            reasons.append(
                f"dependency signals accumulated: {session.dependency_hits} "
                f"over {session.turn_count} turns"
            )
            disclosures.append(DEPENDENCY_DISCLOSURE)
        if session.conservative_mode:
            action = max(action, Action.DISCLOSE)
            reasons.append("conservative mode: minor-consistent or unscorable-language signals")
            disclosures.append(MINOR_DISCLOSURE)

    # Acute dysregulation is not itself a safety event, but it is recorded so
    # that the router can prefer stabilizing agents over challenging ones.
    if signals.is_dysregulated:
        reasons.append(f"acute dysregulation: regulation={signals.regulation}")

    return SafetyVerdict(
        action=action,
        reasons=tuple(reasons),
        disclosures=tuple(disclosures),
        crisis_read=read,
        crisis_classes=(),
        integrity_event=bool(integrity),
        language_scope=language_scope,
    )
