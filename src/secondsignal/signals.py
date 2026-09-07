"""Signal extraction: raw text -> structured, auditable routing features.

This module is deliberately a *reference* implementation. It uses a transparent
lexicon so that every extracted feature can be traced to the token that produced
it. In production this layer is expected to be replaced by a classifier or
embedding model.

The architectural contract is that whatever replaces it must emit the same
`RequestSignals` structure. Routing then reads only those signals: which seat
is chosen, and why, is decided from the structured features and never from
the message itself. That separation is what makes routing decisions
reviewable and testable independently of the model.

The crisis gate is not on that side of the seam. `safety.evaluate` is handed
the raw message and screens it directly, so replacing this extractor cannot
change what the gate sees or lower a verdict. Say "the router never touches
raw text", not "the policy layer never touches raw text": the second is
false and the difference is the whole safety property.

The lexicons are organised by *class of phrasing*, not by individual test
case: each tag lists several ways people actually say a thing, so that a
fixture can be held out and the class still matches. An extract that finds
nothing is a first-class state (`RequestSignals.is_empty`), never a silent
default; the router's no-signal policy decides what happens next.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .lexicon import PACKS, apply_masks
from .normalize import analyze

__all__ = [
    "RequestSignals", "extract", "DOMAIN_LEXICON", "MODE_LEXICON",
    "IDIOM_EXCLUSIONS", "mask_idioms", "SEAT_CLAIM_TERMS", "HOLD_DOMAINS",
    "THIRD_PERSON_SUBJECTS", "claim_person",
]


# --------------------------------------------------------------------------
# Idiom masking
#
# Ordinary English reuses death vocabulary for emphasis, games and broken
# devices ("this deadline is killing me", "my phone died", "I died in that
# boss fight"), and recovery vocabulary for ordinary things ("a sober look",
# "the build relapsed"). These spans are masked before *any* lexicon runs --
# topic extraction here and the crisis screen in `safety.py` -- so that
# emphasis is neither a topic nor a risk signal. The masks are data
# (``packs/*.json``, ADR-0018): fixed collocations plus trigger stems that
# only mask when an object sits inside a token window. A masked span can
# still sit next to a real hit; masking removes only the idiom itself.
# --------------------------------------------------------------------------

IDIOM_EXCLUSIONS: tuple[re.Pattern[str], ...] = tuple(
    pattern for pack in PACKS.values() for _, pattern in pack.regex_masks
)


def mask_idioms(norm: str) -> str:
    """Blank out idiom spans (same length, so offsets are preserved)."""
    masked, _ = apply_masks(norm)
    return masked

# --------------------------------------------------------------------------
# Lexicons
# --------------------------------------------------------------------------

DOMAIN_LEXICON: dict[str, tuple[str, ...]] = {
    "grief": (
        "grief", "grieving", "died", "death", "funeral", "loss", "mourning", "passed away",
        "passed last", "her passing", "his passing", "memorial", "the wake", "anniversary of",
    ),
    "neurodivergence": (
        "adhd", "autistic", "audhd", "executive function", "time blindness",
        "rsd", "rejection sensitiv", "stimming", "masking", "neurodivergent",
        "hyperfocus", "sensory overload", "task paralysis",
    ),
    "creative_block": (
        "blocked", "creative block", "can't write", "cant write", "stuck on",
        "blank page", "no ideas", "uninspired", "can't start", "cant start",
        "haven't started", "havent started", "staring at the canvas", "staring at the page",
        "staring at this", "haven't made a mark", "first mark",
    ),
    "career": (
        "job", "resume", "interview", "fired", "laid off", "employer", "career",
        "promotion", "hiring", "salary", "passed over", "my boss", "the raise",
        "quit my job", "leaving this job", "leave this job", "layoff",
        # Work pressure reads as work: a deck due at nine is a career signal
        # even when no one says "job". Added in round 2 so that "the deck is
        # due in the morning and I keep flashing on the funeral" seats the
        # agent who carries both the ask and the hold (ADR-0016).
        "deadline", "deadlines", "due at", "due tomorrow", "due in the morning",
        "due by", "presentation", "workload", "my manager", "overtime", "the office",
        "coworker", "co-worker",
    ),
    "conflict": (
        "argument", "fight", "conflict", "betrayed", "confront", "boundary with",
        "they said", "disrespect", "not speaking", "we're not talking", "were not talking",
        "what she said", "what he said", "what they said", "thing she said", "thing he said",
        "replaying", "keep replaying", "divorce", "breakup", "broke up", "falling out",
        "estranged", "cut me off", "ghosted", "make it right with", "apologize to",
    ),
    "somatic_distress": (
        "panic", "can't breathe", "cant breathe", "chest tight", "chest is tight", "tight chest",
        "shaking", "trembling", "nauseous", "dizzy", "heart racing", "frozen",
        "can't feel my", "cant feel my", "feels far away", "far away from me", "dissociat",
        "not safe in my body", "full breath", "hyperventilat", "lightheaded", "numb hands",
        "not in my body", "outside my body",
    ),
    "identity": (
        "who am i", "identity", "queer", "trans", "gender", "coming out",
        "don't know myself", "dont know myself", "who i am anymore",
    ),
    "practical_logistics": (
        "how do i", "steps", "checklist", "plan for", "fix my", "repair",
        "budget", "schedule", "logistics", "launch", "launch date", "set up a", "set up the",
        "storefront", "a shop", "the shop", "funnel", "timeline", "roadmap", "next steps",
        "ship the", "ship it", "deploy", "the build", "release", "plan for the week",
        "plan the week", "a plan for", "need a plan",
    ),
    "analysis": (
        "analyze", "compare", "tradeoff", "trade-off", "evaluate", "data", "metrics",
        "strategy", "framework", "decision", "pricing", "price of", "spot price", "market",
        "investor", "investors", "revenue", "profit", "business plan", "go to market",
        "forecast", "pitch deck", "the deck", "options for", "with costs",
        "analysis", "diagnose", "root cause", "the numbers", "run the numbers",
    ),
    "addiction_recovery": (
        # Present use or a return to use: these claim the seat (ADR-0016).
        "relapse", "relapsed", "relapsing", "drinking again", "using again",
        "used again", "drank last night", "drank tonight", "drank again", "got high again",
        "fell off the wagon", "off the wagon", "started using", "back on the",
        # Recovery status: these are a hold, not a seat-claim.
        "sober", "sobriety", "aa meeting", "na meeting", "my sponsor", "clean time",
        "years clean", "months clean", "days clean", "years sober", "months sober",
        "days sober", "in recovery", "my recovery",
    ),
    "abuse": (
        "abused", "abusing me", "abusive", "hits me", "hit me", "beats me", "beat me",
        "molested", "assaulted", "raped", "touched me", "groomed", "grooming me",
        "he hurts me", "she hurts me", "they hurt me", "threatens me", "threatened me",
    ),
    "eating_distress": (
        "stopped eating", "not eating", "haven't eaten", "havent eaten", "purge", "purging",
        "binge", "bingeing", "binging", "restricting", "starving myself", "skipping meals",
        "eating disorder", "anorexi", "bulimi", "throw up after", "make myself throw up",
    ),
    "isolation": (
        "alone", "lonely", "no one", "nobody", "isolated", "no friends",
    ),
}

# Terms in the addiction_recovery lexicon that mean present use or a return to
# use. When one of these produced the domain, the domain claims the seat; when
# only status terms did ("ten years clean"), the domain is a hold (ADR-0016).
SEAT_CLAIM_TERMS: frozenset[str] = frozenset({
    "relapse", "relapsed", "relapsing", "drinking again", "using again", "used again",
    "drank last night", "drank tonight", "drank again", "got high again",
    "fell off the wagon", "off the wagon", "started using", "back on the",
})

# Subjects that make a return-to-use term someone else's. A relative's
# relapse is a hold on the seat, not a claim of it: a claim outranks the
# person's own ask, and the person asking how to talk to their sibling has an
# ask that deserves weighing. The recovery persona still wins whenever it
# carries the topic best -- it is the only carrier in the shipped roster.
THIRD_PERSON_SUBJECTS: frozenset[str] = frozenset({
    "he", "she", "they", "dad", "mom", "mum", "mother", "father", "parent",
    "parents", "brother", "sister", "sibling", "son", "daughter", "kid",
    "child", "friend", "buddy", "husband", "wife", "partner", "boyfriend",
    "girlfriend", "roommate", "uncle", "aunt", "cousin", "coworker",
    "sponsee", "sponsor", "client", "patient", "neighbor", "neighbour", "ex",
    "grandpa", "grandma", "stepdad", "stepmom", "nephew", "niece",
})
FIRST_PERSON_SUBJECTS: frozenset[str] = frozenset({"i", "i've", "ive", "i'm", "im", "i'd", "me", "myself"})

# Domains that must be carried by whoever takes the seat (ADR-0016).
HOLD_DOMAINS: tuple[str, ...] = ("grief", "abuse", "eating_distress", "addiction_recovery")

MODE_LEXICON: dict[str, tuple[str, ...]] = {
    "humor": (
        "joke", "funny", "roast", "make me laugh", "lighten", "absurd",
        "make it stupid", "make fun of", "mock", "satir", "make it ridiculous",
        "laugh at", "clown", "meme", "be brutal", "make it dumb",
    ),
    "comfort": ("comfort", "hold me", "gentle", "soft", "reassure", "just listen"),
    "challenge": (
        "push me", "call me out", "be honest", "brutal", "don't sugarcoat",
        "dont sugarcoat", "devil's advocate", "tell me straight", "just tell me straight",
    ),
    "structure": (
        "structure", "organize", "break it down", "step by step", "checklist",
        "prioritize", "where do i start", "numbered list", "in a list",
    ),
    "analysis": (
        "analyze", "assess", "evaluate", "pros and cons", "tradeoff", "trade-off",
        "should i care", "worth it",
    ),
    "reflection": (
        "why do i", "pattern", "keep doing", "make sense of", "understand myself",
        "how to feel", "how do i feel", "feel about", "language for", "find the words",
        "how to say", "keep thinking about", "look at it",
    ),
}

# Tokens that indicate the person is currently dysregulated. Each match pushes
# the regulation estimate down.
DYSREGULATION_MARKERS: tuple[str, ...] = (
    "panic", "spiraling", "spiralling", "can't stop", "cant stop", "falling apart",
    "breaking down", "overwhelmed", "can't think", "cant think", "freaking out",
    "meltdown", "shutdown", "can't breathe", "cant breathe", "too much",
    "can't feel my", "cant feel my", "not safe in my body", "not safe", "dissociat",
    "shaking", "trembling", "at a 10", "at 10", "i'm at 10", "im at 10",
    "haven't slept", "havent slept", "not sleeping", "can't sleep", "cant sleep",
    "i need the floor",  # family idiom for grounding; treated as a distress marker
    "wrecked", "losing it",
    # fear / anxiety class: mild on its own (one step), meaningful in combination
    "anxious", "anxiety", "nervous", "scared", "terrified", "dread", "on edge",
    # fury class (round 2). Work-fury with no crisis stem proceeds through the
    # gate; it is still a state the router can act on -- the caller is not
    # regulated -- so it seats the stabilizer instead of asking for another
    # sentence. The crisis screen keeps its own frustration markers; these
    # never touch a verdict.
    "lose my mind", "losing my mind", "i swear to god", "furious", "so angry",
    "fed up", "pissed off", "going to scream", "gonna scream",
)

# Tokens indicating a regulated, task-oriented request.
REGULATION_MARKERS: tuple[str, ...] = (
    "let's plan", "lets plan", "help me build", "draft", "review", "compare",
    "outline", "walk me through", "what are the options",
)

BASELINE_REGULATION = 0.70
DYSREGULATION_STEP = 0.18
REGULATION_STEP = 0.08


@dataclass(frozen=True)
class RequestSignals:
    """Structured features consumed by the policy layer.

    Attributes:
        regulation: 0.0 (acutely dysregulated) .. 1.0 (regulated, task-focused).
        domains: Topic tags matched in the input.
        modes: Interaction modes the person appears to be asking for.
        evidence: Feature name -> the literal tokens that triggered it. Every
            routing decision can be traced back through this map.
        turn_index: Position in the session, used by session-level monitors.
    """

    regulation: float
    domains: frozenset[str] = frozenset()
    modes: frozenset[str] = frozenset()
    evidence: dict[str, tuple[str, ...]] = field(default_factory=dict)
    turn_index: int = 0

    @property
    def is_dysregulated(self) -> bool:
        return self.regulation < 0.45

    @property
    def is_empty(self) -> bool:
        """True when nothing routable was found: no topic, no mode, and no
        regulation evidence either way. Distress without a topic is *not*
        empty -- the regulation estimate is a signal the router can act on."""
        return not self.domains and not self.modes and not any(
            k.startswith("regulation:") for k in self.evidence
        )


def _matches(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    """Return every term in `terms` present in `text`, order preserved."""
    return tuple(t for t in terms if t in text)


_MODE_NEGATION = ("no ", "not ", "don't ", "dont ", "without ", "never ", "less ", "zero ")


def _negated_term(norm: str, term: str) -> bool:
    """True when every occurrence of ``term`` sits right after a negation
    ("no comfort", "don't roast me"): the person is refusing that mode."""
    starts = [m.start() for m in re.finditer(re.escape(term), norm)]
    if not starts:
        return False
    for start in starts:
        before = norm[max(0, start - 12):start]
        if not any(before.endswith(n) or before.endswith(n.strip() + " ") for n in _MODE_NEGATION):
            return False
    return True


def claim_person(norm: str, terms: tuple[str, ...]) -> str | None:
    """Whose return to use a message reports: ``first``, ``third`` or None
    when no seat-claim term is present. A term with a third-person subject
    in the four tokens before it and no first-person token closer is
    third person; a bare term ("relapsed again last night") is first."""
    verdicts: list[str] = []
    for term in terms:
        if term not in SEAT_CLAIM_TERMS:
            continue
        for m in re.finditer(re.escape(term), norm):
            before = re.findall(r"[^\W_]+(?:'[^\W_]+)*", norm[:m.start()])[-4:]
            person = "first"
            for tok in reversed(before):
                if tok in FIRST_PERSON_SUBJECTS:
                    break
                if tok in THIRD_PERSON_SUBJECTS:
                    person = "third"
                    break
            verdicts.append(person)
    if not verdicts:
        return None
    return "first" if "first" in verdicts else "third"


def _normalize(text: str) -> str:
    """Normalize for mask decisions, keeping clause boundaries intact.

    V-04: horizontal whitespace collapses, but a line break survives. The
    mask engine treats a newline as the end of a clause exactly as the
    safety screen does; collapsing it here first let an object on one line
    explain a stem on the next, so the same message routed differently
    depending on whether the writer pressed enter or typed a period.
    """
    text = analyze(text).text
    text = re.sub(r"[^\S\n]+", " ", text)
    return re.sub(r" *\n+ *", "\n", text).strip()


def _fold_lines(text: str) -> str:
    """Collapse the surviving line breaks once masking has been decided, so a
    phrase written across two lines still matches as one phrase."""
    return re.sub(r"\s+", " ", text).strip()


def extract(text: str, *, turn_index: int = 0) -> RequestSignals:
    """Extract routing signals from a single turn of user input."""
    norm, masked_spans = apply_masks(_normalize(text))
    norm = _fold_lines(norm)
    evidence: dict[str, tuple[str, ...]] = {}
    if masked_spans:
        evidence["masked"] = tuple(f"{s.pattern_id}:{s.text}" for s in masked_spans)

    domains: set[str] = set()
    for domain, terms in DOMAIN_LEXICON.items():
        hits = _matches(norm, terms)
        if hits:
            domains.add(domain)
            evidence[f"domain:{domain}"] = hits

    if "addiction_recovery" in domains:
        person = claim_person(norm, evidence["domain:addiction_recovery"])
        if person:
            evidence["domain:addiction_recovery:person"] = (person,)

    modes: set[str] = set()
    for mode, terms in MODE_LEXICON.items():
        hits = _matches(norm, terms)
        live = tuple(t for t in hits if not _negated_term(norm, t))
        if live:
            modes.add(mode)
            evidence[f"mode:{mode}"] = live
        elif hits:
            evidence[f"mode:{mode}:negated"] = hits

    down = _matches(norm, DYSREGULATION_MARKERS)
    up = _matches(norm, REGULATION_MARKERS)
    if down:
        evidence["regulation:down"] = down
    if up:
        evidence["regulation:up"] = up

    regulation = BASELINE_REGULATION - DYSREGULATION_STEP * len(down) + REGULATION_STEP * len(up)
    regulation = max(0.0, min(1.0, regulation))

    return RequestSignals(
        regulation=round(regulation, 3),
        domains=frozenset(domains),
        modes=frozenset(modes),
        evidence=evidence,
        turn_index=turn_index,
    )
