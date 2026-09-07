"""Lexicon packs and the idiom-mask engine (ADR-0018).

A *pack* is a JSON file under ``packs/`` that carries, for one language:

* ``regex_masks`` -- fixed collocations that reuse death or substance
  vocabulary for something else ("this deadline is killing me",
  "me muero de ganas"). A mask is a **pre-filter**, not a second crisis
  list: it blanks a span so the matchers never see it.
* ``window_masks`` -- a trigger stem that is only masked when one of its
  listed *objects* sits within ``window`` tokens ("kill" next to
  "process"; "sober" next to "look") **in the same clause**: an object never
  explains a stem across a sentence break or across a sincerity pivot such
  as "honestly" (the pack's ``pivots``). No object, no mask: that rule is
  what keeps the mask table from becoming a silencer for every angry
  message. The clause rule is what keeps a wide window from letting game
  talk at the start of a message silence "and honestly I want to die" at
  the end of it (``tests/test_crisis_gate.py`` pins that property).
* ``hits`` and ``inconclusive`` -- native speech-act classes for the pack's
  language. The English classes live in ``safety.py`` because they carry
  regression pins from the first external review; every other language's
  classes are data.
* ``house_lines`` -- the fixed lines in that language, written natively,
  never machine-translated.

Every mask that fires is recorded as a span on the decision (``masked_spans``)
next to the spans that hit (``hit_spans``), with the hash of every pattern
table consulted (``patterns_hash``) and the packs that ran (``pack_ids``).
A later harness can therefore see that the gate *saw* "killing me" and chose
a mask, instead of seeing a silent PROCEED and assuming the lexicon is blind.

Load-time contracts: a duplicate id, an empty stem list, or a window mask
without objects fails the load. Every window mask must be exercised by a
positive and a negative fixture; ``tests/test_lexicon.py`` enforces that.

All packs installed run on every turn. Declaring a language selects the
house lines and resources; it never exempts any text from any screen.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "Pack",
    "Span",
    "WindowMask",
    "PACK_DIR",
    "PACKS",
    "RESOURCES",
    "load_pack",
    "load_resources",
    "apply_masks",
    "screen_packs",
    "tokenize",
    "patterns_hash",
    "resource_row",
    "resource_line",
]

PACK_DIR = Path(__file__).resolve().parent / "packs"

_TOKEN_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)*")
_HARD_CLAUSE_BREAK_RE = re.compile(r"[.!?;:\u2014\u2013\n]")  # B4: colon/semi/em/en dash (+ sentence)
_CLAUSE_BREAK_RE = _HARD_CLAUSE_BREAK_RE  # exported name kept for callers/tests


@dataclass(frozen=True)
class Span:
    """A span the engine acted on, with the pattern that did it."""

    text: str
    pattern_id: str
    start: int
    end: int
    kind: str          # "mask" | "hit" | "inconclusive"
    pack: str
    domain: str = "crisis"


@dataclass(frozen=True)
class WindowMask:
    id: str
    stems: frozenset[str]
    objects: frozenset[str]
    domain: str = "crisis"
    requires_negation: bool = False
    window: int | None = None


@dataclass(frozen=True)
class Pack:
    id: str
    version: int
    status: str
    language: str
    window: int
    negation: frozenset[str]
    pivots: frozenset[str]
    regex_masks: tuple[tuple[str, re.Pattern[str]], ...]
    window_masks: tuple[WindowMask, ...]
    hits: tuple[tuple[str, str, re.Pattern[str]], ...]
    inconclusive: tuple[tuple[str, re.Pattern[str]], ...]
    house_lines: dict = field(default_factory=dict)
    source_hash: str = ""


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


def load_pack(path: str | Path) -> Pack:
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    data = json.loads(raw.decode("utf-8"))
    ids: set[str] = set()

    def claim(entry_id: str, what: str) -> None:
        if entry_id in ids:
            raise ValueError(f"pack {data.get('pack')!r}: duplicate id {entry_id!r} in {what}")
        ids.add(entry_id)

    regex_masks = []
    for m in data.get("regex_masks", ()):
        claim(m["id"], "regex_masks")
        regex_masks.append((m["id"], _compile(m["pattern"])))

    window_masks = []
    for m in data.get("window_masks", ()):
        claim(m["id"], "window_masks")
        stems = frozenset(s.casefold() for s in m.get("stems", ()))
        objects = frozenset(o.casefold() for o in m.get("objects", ()))
        if not stems:
            raise ValueError(f"pack {data.get('pack')!r}: window mask {m['id']!r} has no stems")
        if not objects:
            raise ValueError(
                f"pack {data.get('pack')!r}: window mask {m['id']!r} has no objects; "
                "a mask without an object is a silencer, not a mask"
            )
        window_masks.append(WindowMask(
            id=m["id"], stems=stems, objects=objects,
            domain=m.get("domain", "crisis"),
            requires_negation=bool(m.get("requires_negation", False)),
            window=int(m["window"]) if "window" in m else None,
        ))

    hits = []
    for h in data.get("hits", ()):
        claim(h["id"], "hits")
        hits.append((h["id"], h["class"], _compile(h["pattern"])))

    inconclusive = []
    for h in data.get("inconclusive", ()):
        claim(h["id"], "inconclusive")
        inconclusive.append((h["id"], _compile(h["pattern"])))

    return Pack(
        id=data["pack"],
        version=int(data.get("version", 1)),
        status=data.get("status", "unreviewed"),
        language=data.get("language", data["pack"].split("-")[0]),
        window=int(data.get("window", 4)),
        negation=frozenset(n.casefold() for n in data.get("negation", ())),
        pivots=frozenset(v.casefold() for v in data.get("pivots", ())),
        regex_masks=tuple(regex_masks),
        window_masks=tuple(window_masks),
        hits=tuple(hits),
        inconclusive=tuple(inconclusive),
        house_lines=dict(data.get("house_lines", {})),
        source_hash=digest,
    )


def load_resources(path: str | Path | None = None) -> dict:
    path = Path(path) if path else PACK_DIR / "resources.json"
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    data["_source_hash"] = hashlib.sha256(raw).hexdigest()[:12]
    for locale, row in data["rows"].items():
        if row.get("hours") == "24/7" and not row.get("source"):
            raise ValueError(f"resource row {locale!r} claims 24/7 without a source")
        if locale != "default" and not row.get("last_verified"):
            raise ValueError(f"resource row {locale!r} has no last_verified date")
    return data


def _load_all() -> dict[str, Pack]:
    packs: dict[str, Pack] = {}
    for path in sorted(PACK_DIR.glob("*.json")):
        if path.name == "resources.json":
            continue
        pack = load_pack(path)
        if pack.id in packs:
            raise ValueError(f"duplicate pack id {pack.id!r}")
        packs[pack.id] = pack
    if "en" not in packs:
        raise ValueError("the English pack is required")
    return packs


PACKS: dict[str, Pack] = _load_all()
RESOURCES: dict = load_resources()


def tokenize(text: str) -> list[tuple[str, int, int]]:
    """Tokens with character offsets. Apostrophes stay inside tokens."""
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]


def _blank(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]



# First-person present desire must never be blanked by a game/hobby window
# mask (B4). Past-tense game reports ("I died in that boss fight") keep the mask.
_PRESENT_DESIRE_RE = re.compile(
    # Affirmative first-person present desire only (B4). Negated forms
    # ("I don't want to die") must remain maskable by work-object windows.
    r"\bi(?:'m| am)?(?!(?:\s+(?:do(?:\s+not)|don'?t|dont|never|not))+)"
    r"(?:\s+(?!don'?t|dont|never|not|do)\w+){0,4}\s+"
    r"(?:want|need|going|gonna|plan(?:ning)?|ready|trying|tried|decided)\s+to\s+"
    r"(?:die|be\s+dead|kill\s+myself|end\s+it(?:\s+all)?|end\s+my(?:\s+own)?\s+life)\b",
    re.IGNORECASE,
)


def _present_desire_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _PRESENT_DESIRE_RE.finditer(text)]


def _overlaps_desire(start: int, end: int, desire: list[tuple[int, int]]) -> bool:
    return any(start < d_end and end > d_start for d_start, d_end in desire)


def _same_clause(
    text: str,
    tokens: list[tuple[str, int, int]],
    i: int,
    j: int,
    pivots: frozenset[str],
) -> bool:
    """True when tokens ``i`` and ``j`` share a clause: no sentence break in
    the text between them and no sincerity pivot among the tokens between
    them. A pivot is a word like "honestly" that marks the speaker leaving
    hyperbole; whatever follows it is read on its own.

    B4: colon, semicolon, em dash and en dash always end a clause. A comma
    ends a clause when what follows begins a first-person subject
    (I / I'm / I'd / we / we'd), so game talk cannot silence a later desire
    clause, while hyperbolic tails like "me muero, qué risa" stay same-clause.
    """
    lo, hi = (i, j) if i < j else (j, i)
    between_text = text[tokens[lo][2]:tokens[hi][1]]
    if _HARD_CLAUSE_BREAK_RE.search(between_text):
        return False
    if "," in between_text:
        # Comma ends a clause when what follows is first-person present desire
        # (B4: "..., I want to die"). Continuations like "..., I want the meeting
        # to end" stay same-clause so a work-object mask can explain negated die.
        after = between_text.rsplit(",", 1)[-1]
        if _PRESENT_DESIRE_RE.search(after):
            return False
    return not any(tok in pivots for tok, _, _ in tokens[lo + 1:hi])



def apply_masks(norm: str, packs: tuple[Pack, ...] | None = None) -> tuple[str, tuple[Span, ...]]:
    """Blank every masked span (same length, so offsets survive) and return
    the masked text with the spans, in the order they were applied."""
    packs = packs if packs is not None else tuple(PACKS.values())
    masked = norm
    spans: list[Span] = []

    for pack in packs:
        for pattern_id, pattern in pack.regex_masks:
            for m in pattern.finditer(masked):
                if not m.group(0).strip():
                    continue
                spans.append(Span(m.group(0), pattern_id, m.start(), m.end(), "mask", pack.id))
                masked = _blank(masked, m.start(), m.end())

    tokens = tokenize(masked)
    desire_spans = _present_desire_spans(masked)
    for pack in packs:
        for mask in pack.window_masks:
            w = mask.window or pack.window
            for i, (tok, start, end) in enumerate(tokens):
                if tok not in mask.stems:
                    continue
                if masked[start:end].strip() == "":
                    continue  # already masked by an earlier pattern
                lo, hi = max(0, i - w), min(len(tokens), i + w + 1)
                if not any(
                    tokens[j][0] in mask.objects and _same_clause(masked, tokens, i, j, pack.pivots)
                    for j in range(lo, hi) if j != i
                ):
                    continue
                if mask.requires_negation:
                    before = tokens[max(0, i - 3): i]
                    if not any(t in pack.negation for t, _, _ in before):
                        continue
                # B4: first-person present desire is never masked by game/hobby idiom.
                if _overlaps_desire(start, end, desire_spans):
                    continue
                spans.append(Span(tok, mask.id, start, end, "mask", pack.id, mask.domain))
                masked = _blank(masked, start, end)
    return masked, tuple(spans)


def screen_packs(masked: str, packs: tuple[Pack, ...] | None = None) -> tuple[tuple[Span, ...], tuple[Span, ...]]:
    """Run every pack's native classes over already-masked text.

    Returns (hit_spans, inconclusive_spans). Class names travel on the span's
    ``domain`` field so the verdict can name them.
    """
    packs = packs if packs is not None else tuple(PACKS.values())
    hits: list[Span] = []
    inconclusive: list[Span] = []
    for pack in packs:
        for pattern_id, cls, pattern in pack.hits:
            m = pattern.search(masked)
            if m:
                hits.append(Span(m.group(0).strip(), pattern_id, m.start(), m.end(), "hit", pack.id, cls))
        for pattern_id, pattern in pack.inconclusive:
            m = pattern.search(masked)
            if m:
                inconclusive.append(Span(m.group(0).strip(), pattern_id, m.start(), m.end(), "inconclusive", pack.id, "inconclusive"))
    return tuple(hits), tuple(inconclusive)


def patterns_hash(extra: tuple[str, ...] = ()) -> str:
    """Digest of every pattern table consulted on a turn: the pack files, the
    resource table, and any code-resident pattern strings the caller passes."""
    material = "|".join(
        [f"{pid}:{PACKS[pid].source_hash}" for pid in sorted(PACKS)]
        + [f"resources:{RESOURCES['_source_hash']}"]
        + list(extra)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def resource_row(locale: str | None) -> tuple[str, dict]:
    rows = RESOURCES["rows"]
    key = (locale or "").upper()
    if key in rows:
        return key, rows[key]
    return "default", rows["default"]


def resource_line(locale: str | None, language: str | None = None) -> str:
    """The resource line for a declared locale, in the declared language when
    the row carries it, otherwise in English. Never inferred from anything."""
    _, row = resource_row(locale)
    lines = row["lines"]
    lang = (language or "en").split("-")[0].lower()
    return lines.get(lang, lines["en"])
