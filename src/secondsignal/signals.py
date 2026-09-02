"""Signal extraction: raw text -> structured, auditable routing features.

This module is deliberately a *reference* implementation. It uses a transparent
lexicon so that every extracted feature can be traced to the token that produced
it. In production this layer is expected to be replaced by a classifier or
embedding model.

The architectural contract is that whatever replaces it must emit the same
`RequestSignals` structure. The policy layer (`router.py`, `safety.py`) never
touches raw text -- it only consumes signals. That separation is what makes
routing decisions reviewable and testable independently of the model.

The lexicons are organised by *class of phrasing*, not by individual test
case: each tag lists several ways people actually say a thing, so that a
fixture can be held out and the class still matches. An extract that finds
nothing is a first-class state (`RequestSignals.is_empty`), never a silent
default; the router's no-signal policy decides what happens next.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["RequestSignals", "extract", "DOMAIN_LEXICON", "MODE_LEXICON", "IDIOM_EXCLUSIONS", "mask_idioms"]


# --------------------------------------------------------------------------
# Idiom masking
#
# Ordinary English reuses death vocabulary for emphasis, games and broken
# devices ("this deadline is killing me", "my phone died", "I died in that
# boss fight"). These spans are masked before *any* lexicon runs -- topic
# extraction here and the crisis screen in `safety.py` -- so that emphasis is
# neither a topic nor a risk signal. A masked span can still sit next to a
# real hit; masking removes only the idiom itself.
# --------------------------------------------------------------------------

IDIOM_EXCLUSIONS: tuple[re.Pattern[str], ...] = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\bkilling (me|it|him|her|them|us|my \w+|the \w+)\b",
    r"\bkilled it\b",
    r"\bkill (it|time|the (lights|mood|vibe|engine)|two birds)\b",
    r"\bdying (to|of laughter|laughing|of embarrassment)\b",
    r"\bdie laughing\b",
    r"\bdie of embarrassment\b",
    r"\bto die for\b",
    r"\bdead (tired|serious|end|ends|on|set|wrong|silent|quiet|last|centre|center|weight|zone)\b",
    r"\bdrop[- ]dead\b",
    r"\b(dead|kill)(line|lines|pan|lock|bolt|switch|beat|heat)\b",
    r"\b(my|the) (phone|battery|car|engine|laptop|computer|app|server|wifi|internet|plant|fish|screen|mic)"
    r" (just |finally |again )?(died|is dead|dies|keeps dying)( again)?\b",
    r"\b(die|died|dying|dead|kill(ed)?|killing|unalived?) (in|on|at|during) (this|the|a|that|my|every)"
    r" (boss fight|boss|game|level|raid|match|round|run|campaign|dungeon|pvp|mission)\b",
    r"\bmy (character|guy|hero|avatar|team|squad|party) (died|is dead|got killed|keeps dying)\b",
    r"\b(done|finished|through) with (the|this|that|my|these|those|it|him|her|them|work|school)\b",
    r"\bgive up on\b",
    r"\bi'?m dead\b(?! inside)",
    r"\bsuicide (prevention|hotline|lifeline|awareness|research|rate|rates|squad|mission)\b",
    r"\bdisappear (for|on|over) (a|the|one|two|three) (week|weekend|day|days|while|bit|month|vacation|trip)\b",
    r"\bend (of )?(this|the) (meeting|call|session|chapter|year|day|week|sprint|quarter)\b",
    r"\bend of the (quarter|year|day|week|month)\b",
))


def mask_idioms(norm: str) -> str:
    """Blank out idiom spans (same length, so offsets are preserved)."""
    masked = norm
    for pattern in IDIOM_EXCLUSIONS:
        masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
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
    ),
    "analysis": (
        "analyze", "compare", "tradeoff", "trade-off", "evaluate", "data", "metrics",
        "strategy", "framework", "decision", "pricing", "price of", "spot price", "market",
        "investor", "investors", "revenue", "profit", "business plan", "go to market",
        "forecast", "pitch deck", "the deck", "options for", "with costs",
    ),
    "addiction_recovery": (
        "sober", "sobriety", "relapse", "drinking again", "aa meeting",
        "clean time", "using again",
    ),
    "isolation": (
        "alone", "lonely", "no one", "nobody", "isolated", "no friends",
    ),
}

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


def _normalize(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").lower()
    # Collapse whitespace so multi-word phrases match across line breaks.
    return re.sub(r"\s+", " ", text).strip()


def extract(text: str, *, turn_index: int = 0) -> RequestSignals:
    """Extract routing signals from a single turn of user input."""
    norm = mask_idioms(_normalize(text))
    evidence: dict[str, tuple[str, ...]] = {}

    domains: set[str] = set()
    for domain, terms in DOMAIN_LEXICON.items():
        hits = _matches(norm, terms)
        if hits:
            domains.add(domain)
            evidence[f"domain:{domain}"] = hits

    modes: set[str] = set()
    for mode, terms in MODE_LEXICON.items():
        hits = _matches(norm, terms)
        if hits:
            modes.add(mode)
            evidence[f"mode:{mode}"] = hits

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
