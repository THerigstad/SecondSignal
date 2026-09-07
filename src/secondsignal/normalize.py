"""Text normalization that runs before every lexicon (ADR-0018).

Four steps, in this order, every time:

1. ``NFKC`` -- Unicode compatibility normalization. Folds fullwidth letters,
   mathematical alphanumerics, circled letters, ligatures and the no-break
   space to their plain forms. ``unicodedata`` is the standard library; there
   is no dependency.
2. **Strip invisibles** -- preserve the historic deny-list, then remove any
   format character inside a Latin letter run and any combining mark between
   Latin letters. ``di<ZWSP>e`` must reach the lexicon as ``die``. The
   Latin-only context rule avoids corrupting scripts where these characters
   carry meaning. Nothing here emulates the bidi algorithm.
3. **Skeleton** -- a small, reviewed map of look-alike letters (Cyrillic,
   Greek, a few Latin variants) onto the Latin letters that occur in the
   stems the lexicons match. NFKC does *not* do this: a Cyrillic ``і``
   (U+0456) inside ``die`` survives NFKC untouched and walked straight
   through the crisis gate before this module existed. The map is
   deliberately not the full Unicode confusables table, which flags ordinary
   non-Latin text; it is the handful of letters that spell our stems.
4. ``casefold`` -- default casefold, never a Turkish locale.

The map is hashed (``skeleton_hash``) and exported, so a reviewer can pin
which fold table produced a match. It is not carried on the decision record
today; the record carries ``patterns_hash`` and ``roster_hash``. Digits and
punctuation are never touched: resource strings such as ``800-911-2000``
are invariant under ``normalize`` by construction, and a test pins that.

The measurement that justified this module is in
``docs/threat-model.md`` (the NFKC-versus-skeleton table) and in
``evals/cases/unicode_normalize_vectors.json``.
"""

from __future__ import annotations

import hashlib
import re
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
    "а": "a", "в": "b", "е": "e", "і": "i", "о": "o", "р": "p",
    "с": "c", "у": "y", "х": "x", "ѕ": "s", "ј": "j",
    "м": "m", "н": "h", "т": "t",
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
_QUOTE_TABLE = {0x2019: "'", 0x2018: "'", 0x201C: '"', 0x201D: '"'}
_CONTRACTION_RE = re.compile(r"\b(?:wanna|gonna|gotta|imma|i'ma|lemme|dunno|morirme)\b")
_PROTECTED_LOCATION_RE = re.compile(r"\S*(?:(?:https?://|www\.)|[\\/])\S*", re.IGNORECASE)
_CONTRACTIONS = {
    "wanna": "want to",
    "gonna": "going to",
    "gotta": "got to",
    "imma": "i am going to",
    "i'ma": "i am going to",
    "lemme": "let me",
    "dunno": "do not know",
    "morirme": "morir me",
}


def _is_latin_letter(ch: str) -> bool:
    if not ch.isalpha():
        return False
    try:
        return unicodedata.name(ch).startswith("LATIN")
    except ValueError:
        return False


def _between_latin_letters(text: str, index: int, categories: frozenset[str]) -> bool:
    """Whether a category character is internal to one Latin letter run.

    Adjacent characters from the same removable category are skipped so a
    short run of controls cannot protect itself merely by being doubled.
    """
    left = index - 1
    while left >= 0 and unicodedata.category(text[left]) in categories:
        left -= 1
    right = index + 1
    while right < len(text) and unicodedata.category(text[right]) in categories:
        right += 1
    return left >= 0 and right < len(text) and _is_latin_letter(text[left]) and _is_latin_letter(text[right])


def _protect_interior_combining_marks(text: str) -> tuple[str, dict[str, str]]:
    """Keep raw combining marks visible to the post-NFKC category rule.

    NFKC would otherwise compose, for example, ``i`` plus a combining acute
    into one precomposed letter before the strip step could inspect the mark.
    A temporary private-use placeholder prevents that composition; it is
    restored as a combining mark immediately after NFKC and then removed by
    ``_strip_categories``. Existing precomposed letters remain untouched.
    """
    mark_categories = frozenset({"Mn", "Me"})
    indexes = {
        i
        for i, ch in enumerate(text)
        if unicodedata.category(ch) in mark_categories
        and _between_latin_letters(text, i, mark_categories)
    }
    if not indexes:
        return text, {}
    placeholder_ord = 0xF0000
    replacements: dict[int, str] = {}
    restore: dict[str, str] = {}
    for index in sorted(indexes):
        while chr(placeholder_ord) in text or chr(placeholder_ord) in restore:
            placeholder_ord += 1
        placeholder = chr(placeholder_ord)
        replacements[index] = placeholder
        restore[placeholder] = text[index]
        placeholder_ord += 1
    return "".join(replacements.get(i, ch) for i, ch in enumerate(text)), restore


def _strip_categories(text: str) -> tuple[str, int]:
    format_category = frozenset({"Cf"})
    mark_categories = frozenset({"Mn", "Me"})
    remove: set[int] = set()
    for i, ch in enumerate(text):
        category = unicodedata.category(ch)
        if ord(ch) in STRIP_CODEPOINTS:
            remove.add(i)
        elif category == "Cf" and _between_latin_letters(text, i, format_category):
            remove.add(i)
        elif category in mark_categories and _between_latin_letters(text, i, mark_categories):
            remove.add(i)
    return "".join(ch for i, ch in enumerate(text) if i not in remove), len(remove)


def _expand_contractions(text: str) -> str:
    """Expand reviewed spoken forms and one clitic split outside URLs/paths."""
    def expand(segment: str) -> str:
        return _CONTRACTION_RE.sub(lambda match: _CONTRACTIONS[match.group(0)], segment)

    pieces: list[str] = []
    cursor = 0
    for match in _PROTECTED_LOCATION_RE.finditer(text):
        pieces.append(expand(text[cursor:match.start()]))
        pieces.append(match.group(0))
        cursor = match.end()
    pieces.append(expand(text[cursor:]))
    return "".join(pieces)


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
    protected, restore = _protect_interior_combining_marks(text)
    nfkc = unicodedata.normalize("NFKC", protected)
    for placeholder, mark in restore.items():
        nfkc = nfkc.replace(placeholder, mark)
    stripped, n_stripped = _strip_categories(nfkc)

    mixed_raw = [tok for tok in stripped.split() if is_mixed_script_token(tok)]
    mixed_folded = tuple(
        tok.translate(_SKELETON_TABLE).translate(_QUOTE_TABLE).casefold().strip(".,;:!?\"'()[]")
        for tok in mixed_raw
    )

    folded = stripped.translate(_SKELETON_TABLE)
    n_folded = sum(1 for a, b in zip(stripped, folded) if a != b)

    out = folded.translate(_QUOTE_TABLE).casefold()
    out = _expand_contractions(out)
    return Normalized(
        text=out,
        raw=text,
        mixed_script_tokens=len(mixed_raw),
        stripped=n_stripped,
        folded=n_folded,
        mixed_tokens=mixed_folded,
    )


def normalize(text: str) -> str:
    """NFKC -> category strip -> skeleton -> casefold -> spoken expansion."""
    return analyze(text).text
