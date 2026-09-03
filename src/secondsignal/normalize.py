"""Text normalization that runs before every lexicon (ADR-0018).

Four steps, in this order, every time:

1. ``NFKC`` -- Unicode compatibility normalization. Folds fullwidth letters,
   mathematical alphanumerics, circled letters, ligatures and the no-break
   space to their plain forms. ``unicodedata`` is the standard library; there
   is no dependency.
2. **Strip invisibles** -- zero-width space / non-joiner / joiner, the byte
   order mark, the word joiner, the soft hyphen, and the bidirectional
   override and isolate controls. ``di<ZWSP>e`` must reach the lexicon as
   ``die``. Nothing here emulates the bidi algorithm; removing the controls
   is enough at this layer.
3. **Skeleton** -- a small, reviewed map of look-alike letters (Cyrillic,
   Greek, a few Latin variants) onto the Latin letters that occur in the
   stems the lexicons match. NFKC does *not* do this: a Cyrillic ``і``
   (U+0456) inside ``die`` survives NFKC untouched and walked straight
   through the crisis gate before this module existed. The map is
   deliberately not the full Unicode confusables table, which flags ordinary
   non-Latin text; it is the handful of letters that spell our stems.
4. ``casefold`` -- default casefold, never a Turkish locale.

The map is hashed (``skeleton_hash``) and recorded on every decision so a
reviewer can tell which normalization produced a match. Digits and
punctuation are never touched: resource strings such as ``800-911-2000``
are invariant under ``normalize`` by construction, and a test pins that.

The measurement that justified this module is in
``docs/threat-model.md`` (the NFKC-versus-skeleton table) and in
``evals/cases/unicode_normalize_vectors.json``.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass

__all__ = [
    "normalize",
    "analyze",
    "Normalized",
    "NORMALIZE_FORMS",
    "SKELETON",
    "STRIP_CODEPOINTS",
    "skeleton_hash",
    "is_mixed_script_token",
]

NORMALIZE_FORMS: tuple[str, ...] = ("nfkc", "zw_bidi_strip", "skeleton", "casefold")

# Invisible and directional code points removed after NFKC.
STRIP_CODEPOINTS: frozenset[int] = frozenset(
    {0x200B, 0x200C, 0x200D, 0xFEFF, 0x2060, 0x00AD}
    | set(range(0x202A, 0x202F))   # LRE, RLE, PDF, LRO, RLO
    | set(range(0x2066, 0x206A))   # LRI, RLI, FSI, PDI
)

# Look-alike letters -> the Latin letter they impersonate. Only letters that
# appear in the hit and mask stems of the shipped packs are worth mapping;
# a wider map buys false mixed-script flags on real names, not safety.
# Uppercase forms are listed because the skeleton runs before casefold.
SKELETON: dict[str, str] = {
    # Cyrillic lowercase
    "а": "a", "е": "e", "і": "i", "о": "o", "р": "p",
    "с": "c", "у": "y", "х": "x", "ѕ": "s", "ј": "j",
    "һ": "h", "ԁ": "d", "ԛ": "q", "ԝ": "w", "ӏ": "l",
    "г": "r", "к": "k",
    # Cyrillic uppercase
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H",
    "К": "K", "М": "M", "О": "O", "Р": "P", "Т": "T",
    "Х": "X", "І": "I", "Ј": "J", "Ѕ": "S", "У": "Y",
    # Greek lowercase
    "ο": "o", "ι": "i", "ν": "v", "ρ": "p", "κ": "k",
    "υ": "u", "α": "a",
    # Greek uppercase
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H",
    "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
    # Latin variants that NFKC leaves alone
    "ı": "i",   # dotless i
    "ɡ": "g",   # script g
    "ɑ": "a",   # latin alpha
    "ᴀ": "a", "ᴇ": "e", "ᴏ": "o",  # small capitals
}

_SKELETON_TABLE = {ord(k): v for k, v in SKELETON.items()}
_STRIP_TABLE = {cp: None for cp in STRIP_CODEPOINTS}
_QUOTE_TABLE = {0x2019: "'", 0x2018: "'", 0x201C: '"', 0x201D: '"'}


def skeleton_hash() -> str:
    """First 12 hex digits of the SHA-256 of the skeleton map, for the record."""
    material = "|".join(f"{k}:{v}" for k, v in sorted(SKELETON.items()))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def _script(ch: str) -> str | None:
    if not ch.isalpha():
        return None
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return "other"
    for script in ("LATIN", "CYRILLIC", "GREEK", "ARABIC", "HEBREW", "CJK", "HIRAGANA", "KATAKANA", "HANGUL", "DEVANAGARI", "THAI"):
        if name.startswith(script):
            return script
    return "other"


def is_mixed_script_token(token: str) -> bool:
    """True when one token mixes Latin letters with Cyrillic or Greek ones.

    Letter-level mixing inside a single word is almost never someone typing
    in two languages; it is how a Latin stem table gets walked around. Clause-
    level mixing (an English sentence followed by a Spanish one) is a
    language-pack matter, not this check.
    """
    scripts = {s for s in (_script(ch) for ch in token) if s}
    return "LATIN" in scripts and bool(scripts & {"CYRILLIC", "GREEK"})


@dataclass(frozen=True)
class Normalized:
    """Result of ``analyze``: the normalized text plus the evidence a
    reviewer needs to see how it was produced."""

    text: str
    raw: str
    forms: tuple[str, ...] = NORMALIZE_FORMS
    mixed_script_tokens: int = 0
    stripped: int = 0
    folded: int = 0
    mixed_tokens: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.text != self.raw


def analyze(text: str) -> Normalized:
    """Normalize ``text`` and report what changed."""
    nfkc = unicodedata.normalize("NFKC", text)
    stripped = nfkc.translate(_STRIP_TABLE)
    n_stripped = len(nfkc) - len(stripped)

    mixed_raw = [tok for tok in stripped.split() if is_mixed_script_token(tok)]
    mixed_folded = tuple(
        tok.translate(_SKELETON_TABLE).translate(_QUOTE_TABLE).casefold().strip(".,;:!?\"'()[]")
        for tok in mixed_raw
    )

    folded = stripped.translate(_SKELETON_TABLE)
    n_folded = sum(1 for a, b in zip(stripped, folded) if a != b)

    out = folded.translate(_QUOTE_TABLE).casefold()
    return Normalized(
        text=out,
        raw=text,
        mixed_script_tokens=len(mixed_raw),
        stripped=n_stripped,
        folded=n_folded,
        mixed_tokens=mixed_folded,
    )


def normalize(text: str) -> str:
    """NFKC -> strip invisibles and bidi controls -> skeleton -> casefold."""
    return analyze(text).text
