"""Signal extraction: raw text -> structured, auditable routing features.

This module is deliberately a *reference* implementation. It uses a transparent
lexicon so that every extracted feature can be traced to the token that produced
it. In production this layer is expected to be replaced by a classifier or
embedding model.

The architectural contract is that whatever replaces it must emit the same
`RequestSignals` structure. The policy layer (`router.py`, `safety.py`) never
touches raw text -- it only consumes signals. That separation is what makes
routing decisions reviewable and testable independently of the model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["RequestSignals", "extract", "DOMAIN_LEXICON", "MODE_LEXICON"]


# --------------------------------------------------------------------------
# Lexicons
# --------------------------------------------------------------------------

DOMAIN_LEXICON: dict[str, tuple[str, ...]] = {
    "grief": ("grief", "grieving", "died", "death", "funeral", "loss", "mourning", "passed away"),
    "neurodivergence": ("adhd", "autistic", "audhd", "executive function", "time blindness",
                        "rsd", "rejection sensitiv", "stimming", "masking", "neurodivergent"),
    "creative_block": ("blocked", "creative block", "can't write", "cant write", "stuck on",
                       "blank page", "no ideas", "uninspired"),
    "career": ("job", "resume", "interview", "fired", "laid off", "employer", "career",
               "promotion", "hiring", "salary"),
    "conflict": ("argument", "fight", "conflict", "betrayed", "confront", "boundary with",
                 "they said", "disrespect"),
    "somatic_distress": ("panic", "can't breathe", "cant breathe", "chest tight", "shaking",
                         "nauseous", "dizzy", "heart racing", "frozen"),
    "identity": ("who am i", "identity", "queer", "trans", "gender", "coming out",
                 "don't know myself", "dont know myself"),
    "practical_logistics": ("how do i", "steps", "checklist", "plan for", "fix my", "repair",
                            "budget", "schedule", "logistics"),
    "analysis": ("analyze", "compare", "tradeoff", "trade-off", "evaluate", "data", "metrics",
                 "strategy", "framework", "decision"),
    "addiction_recovery": ("sober", "sobriety", "relapse", "drinking again", "aa meeting",
                           "clean time", "using again"),
    "isolation": ("alone", "lonely", "no one", "nobody", "isolated", "no friends"),
}

MODE_LEXICON: dict[str, tuple[str, ...]] = {
    "humor": ("joke", "funny", "roast", "make me laugh", "lighten", "absurd"),
    "comfort": ("comfort", "hold me", "gentle", "soft", "reassure", "just listen"),
    "challenge": ("push me", "call me out", "be honest", "brutal", "don't sugarcoat",
                  "dont sugarcoat", "devil's advocate"),
    "structure": ("structure", "organize", "break it down", "step by step", "checklist",
                  "prioritize", "where do i start"),
    "analysis": ("analyze", "assess", "evaluate", "pros and cons", "tradeoff", "trade-off"),
    "reflection": ("why do i", "pattern", "keep doing", "make sense of", "understand myself"),
}

# Tokens that indicate the person is currently dysregulated. Each match pushes
# the regulation estimate down.
DYSREGULATION_MARKERS: tuple[str, ...] = (
    "panic", "spiraling", "spiralling", "can't stop", "cant stop", "falling apart",
    "breaking down", "overwhelmed", "can't think", "cant think", "freaking out",
    "meltdown", "shutdown", "can't breathe", "cant breathe", "too much",
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


def _matches(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    """Return every term in `terms` present in `text`, order preserved."""
    return tuple(t for t in terms if t in text)


def _normalize(text: str) -> str:
    text = text.lower()
    # Collapse whitespace so multi-word phrases match across line breaks.
    return re.sub(r"\s+", " ", text).strip()


def extract(text: str, *, turn_index: int = 0) -> RequestSignals:
    """Extract routing signals from a single turn of user input."""
    norm = _normalize(text)
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
