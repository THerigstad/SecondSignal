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
3. **Skeleton** -- the corrected full confusables table, with the reviewed
   mappings retained. The 5 October measurement found zero new cards on the
   43 literal, 160 historical, 260 policy and 30 non-Latin controls, replacing
   the old reason to keep only a small hand-written map. The crisis screen
   also applies this table before NFKC, as the measured candidate did, so
   compatibility normalization cannot erase a measured source distinction.
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
import itertools
import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

__all__ = [
    "normalize",
    "analyze",
    "collapse_spacing",
    "screen_fold",
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

# Order G2B5B, part 3: the candidate map is shipped; evals is never imported.
SKELETON: dict[str, str] = json.loads(
    Path(__file__).with_name("corrected_confusables.json").read_text(encoding="utf-8")
)
# The experiment applied its full map before the existing reviewed normalizer.
# Preserve the 21 reviewed sources absent from that candidate, including epsilon.
_REVIEWED_SKELETON_REMAINDER: dict[str, str] = json.loads(
    Path(__file__).with_name("reviewed_skeleton_remainder.json").read_text(encoding="utf-8")
)
_SKELETON_TABLE = {
    ord(k): v for k, v in {**_REVIEWED_SKELETON_REMAINDER, **SKELETON}.items()
}
_SCREEN_SKELETON_TABLE = {ord(k): v for k, v in SKELETON.items()}
_QUOTE_TABLE = {0x2019: "'", 0x2018: "'", 0x201C: '"', 0x201D: '"'}
_CONTRACTION_RE = re.compile(r"\b(?:wanna|gonna|gotta|imma|i'ma|lemme|dunno|morirme)\b")
_TOKEN_RE = re.compile(r"\S+")
_LOCATION_MARKER_RE = re.compile(r"https?://|www\.|[\\/]", re.IGNORECASE)
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
    """Expand reviewed spoken forms and one clitic split outside URLs/paths.

    A token (a maximal run of non-whitespace) that carries a URL or path marker
    is copied through untouched; everything else is expanded. Until 4 October
    2026 the protected tokens were found with one regex whose leading greedy
    greedy non-space prefix retried the rest of a long token at every starting position when
    the token had no marker, so a 16,001-character word took about 20 seconds
    to route (measured by Codex, night order 3, 30 September 2026; the
    operator approved the repair on 4 October). The token scan below finds
    exactly the same tokens in one pass; the fixture replay is identical.
    """
    def expand(segment: str) -> str:
        return _CONTRACTION_RE.sub(lambda match: _CONTRACTIONS[match.group(0)], segment)

    pieces: list[str] = []
    cursor = 0
    for match in _TOKEN_RE.finditer(text):
        if _LOCATION_MARKER_RE.search(match.group(0)) is None:
            continue
        pieces.append(expand(text[cursor:match.start()]))
        pieces.append(match.group(0))
        cursor = match.end()
    pieces.append(expand(text[cursor:]))
    return "".join(pieces)


_SPACING_RE = re.compile(r"\s+")


def collapse_spacing(text: str) -> str:
    """Any run of spaces, tabs or line breaks is one space; the ends are trimmed.

    Ruling 1 of 3 October 2026. Grok's crisis-gate fuzz (night order 4, 30
    September 2026) showed that two spaces, a tab or a line break between the
    words of a crisis message switched the card off on 79 of 82 crisis lines,
    because the class patterns are written with single spaces. The crisis
    screen now reads the message with its spacing folded. This runs before
    the crisis check only: the operator chose not to fold spacing before
    routing until that change has been measured (his option B, kept open as
    a measurement for the gap-closure push). A line break therefore no longer
    acts as a clause break inside the crisis screen; the mask engine's other
    clause breaks (sentence punctuation, colon, semicolon, dashes, the
    first-person comma rule) are unchanged.
    """
    return _SPACING_RE.sub(" ", text).strip()


# Order B3, rulings 1, 2, 5, 9 and 11 of 5 October 2026. These candidates
# were measured in orders B1/B5; only crisis_screen calls the combined fold.
_SCREEN_LOOKALIKES = {"0": "o", "1": "il", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "@": "a", "$": "s", "!": "i"}
_SCREEN_CHAR = r"[a-z0-9@$!]"
_SCREEN_SEPARATED = re.compile(r"(?<![\w@$!])" + _SCREEN_CHAR + r"(?:[ ._-]" + _SCREEN_CHAR + r")+(?![\w@$!])", re.I)
_SCREEN_TOKEN = re.compile(r"(?<![\w@$!])[a-z0-9@$!]+(?![\w@$!])", re.I)


@lru_cache(maxsize=1)
def _screen_vocabulary() -> frozenset[str]:
    """Derive B5's literal vocabulary lazily, avoiding the import cycle.

    The gate's English classes and English pack hits are the only sources;
    regex escapes are removed before literal runs of three letters are read.
    No regex expansion, manual word list or masks contribute vocabulary.
    """
    from .lexicon import PACKS
    from .safety import _ENGLISH_PATTERN_STRINGS

    patterns = list(_ENGLISH_PATTERN_STRINGS) + [pattern.pattern for _, _, pattern in PACKS["en"].hits]
    return frozenset(
        word.lower() for pattern in patterns
        for word in re.findall(r"[a-zA-Z]{3,}", re.sub(r"\\[A-Za-z]", " ", pattern))
    )


def _screen_separators(text: str) -> str:
    return _SCREEN_SEPARATED.sub(lambda match: re.sub(r"[ ._-]", "", match.group()), text)


def _screen_punctuation(text: str) -> str:
    return re.sub(r"(.)\1+", lambda match: match[1] if unicodedata.category(match[1]).startswith("P")
                  else match[0], text, flags=re.DOTALL)


def _screen_tripled_letters(text: str) -> str:
    return re.sub(r"([^\W\d_])\1{2,}", r"\1", text)


def _screen_stutter(text: str) -> str:
    # The operator additionally authorized independently resolvable causes on
    # 5 October 2026. The B3 follow-up replay covers these compound stutters
    # against the existing ordinary controls and every accepted crisis card.
    text = re.sub(r"(?<!\w)([^\W\d_])(?:-\1)+-(?=\1)", "", text, flags=re.IGNORECASE)
    # Preserve the existing punctuation separator, removing only the filler
    # and the whitespace it introduced before the next character fragment.
    text = re.sub(r"(?<=[._-])(?:uhm|erm|um|uh)\s+(?=[a-z0-9@$!])", "", text, flags=re.IGNORECASE)

    def join_fragments(match: re.Match[str]) -> str:
        token = match[1] + match[2]
        if len(token) > 6:
            return match[0]
        # The filler can be attached to a fragment after Unicode stripping.
        # Join only if the already-approved token folds reach the vocabulary;
        # the ordinary downstream steps still perform and record those folds.
        mapped = _screen_lookalikes(token)
        final = _screen_doubled_vowel(mapped)
        return token if final in _screen_vocabulary() else match[0]

    text = re.sub(
        r"(?<![\w@$!])([a-z0-9@$!]+?)(?:uhm|erm|um|uh)\s+([a-z0-9@$!]+)(?![\w@$!])",
        join_fragments, text, flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:um|uh|erm|uhm)\b", "", text, flags=re.IGNORECASE)
    text = collapse_spacing(text)
    repeated = re.compile(r"\b([^\W\d_]+)(?:\s*,\s*|\s+)\1(?=\b|_)", re.IGNORECASE)
    while True:
        folded = repeated.sub(r"\1", text)
        if folded == text:
            return text
        text = folded


def _screen_lookalikes(text: str) -> str:
    vocabulary = _screen_vocabulary()

    def replace(match: re.Match[str]) -> str:
        token = match.group()
        if len(token) > 6 or not any(ch in _SCREEN_LOOKALIKES for ch in token):
            return token
        possibilities = itertools.product(*(_SCREEN_LOOKALIKES.get(ch, ch) for ch in token.lower()))
        options = sorted({"".join(chars) for chars in possibilities} & vocabulary)
        return options[0] if options else token

    return _SCREEN_TOKEN.sub(replace, text)


def _screen_doubled_vowel(text: str) -> str:
    # This normalize call is part of the measured B5 candidate, not a general
    # edit-distance rule. It also expands spoken forms restored by earlier folds.
    text = normalize(text)
    vocabulary = _screen_vocabulary()

    def fold(match: re.Match[str]) -> str:
        token = match.group()
        if token in vocabulary:
            return token
        candidates = {
            token[:repeat.start()] + token[repeat.start() + 1:]
            for repeat in re.finditer(r"([aeiou])\1", token)
        } & vocabulary
        return next(iter(candidates)) if len(candidates) == 1 else token

    return re.sub(r"(?<!\w)[a-z]+(?!\w)", fold, text)


# Order G2B5B, part 2: measured corpus guard and crisis vocabulary, shipped as data.
_SECOND_BROOM_VOCABULARY = frozenset(
    Path(__file__).with_name("crisis_words.txt").read_text(encoding="utf-8").splitlines()
)
_EVERYDAY_WORDS = frozenset(
    Path(__file__).with_name("everyday_words.txt").read_text(encoding="utf-8").splitlines()
)
_ONE_LETTER_WORD = re.compile(r"[^\W\d_]+")


@lru_cache(maxsize=1)
def _one_letter_targets() -> dict[str, tuple[str, ...]]:
    targets: dict[str, set[str]] = {}
    for word in _SECOND_BROOM_VOCABULARY:
        for index in range(len(word)):
            targets.setdefault(word[:index] + word[index + 1:], set()).add(word)
        for index in range(len(word) - 1):
            if word[index] != word[index + 1]:
                variant = word[:index] + word[index + 1] + word[index] + word[index + 2:]
                targets.setdefault(variant, set()).add(word)
    return {token: tuple(sorted(choices)) for token, choices in targets.items()}


def screen_confusables(text: str) -> str:
    """Apply the measured full correction before NFKC on the screen copy."""
    return text.translate(_SCREEN_SKELETON_TABLE)


def guarded_one_letter(text: str) -> str:
    """The measured non-unique lexical-first matcher, on the screen copy only."""
    def replace(match: re.Match[str]) -> str:
        token = match.group().casefold()
        if token in _EVERYDAY_WORDS or token in _SECOND_BROOM_VOCABULARY:
            return match.group()
        choices = _one_letter_targets().get(token, ())
        return choices[0] if choices else match.group()
    return _ONE_LETTER_WORD.sub(replace, text)


# Order G2B5B, parts 3 and 4: exact wider_all candidate folds, in its order.
WIDER_QUOTES = frozenset("\"'\u2018\u2019\u201c\u201d")
WIDER_PLAIN_TOKEN = re.compile(r"(?<!\w)[a-z]+(?!\w)", re.IGNORECASE)
WIDER_FRAGMENT = re.compile(r"(?<![^\W_])[a-zA-Z]+(?![^\W_])")


def wider_join_punctuation(text: str, *, quotes: bool) -> str:
    """Join alphabetic fragments only if their complete joined run is a word.

    Quote folding admits only quotes/apostrophes. Symbol folding admits Unicode
    punctuation and symbols except quotes, spaces, and the narrow separator
    set; those last partial boundaries belong to the partial-split candidate.
    The runs cannot contain digits, and a symbol never substitutes for a letter.
    """
    def admitted(char: str) -> bool:
        if quotes:
            return char in WIDER_QUOTES
        return (
            char not in WIDER_QUOTES
            and char not in " ._-"
            and unicodedata.category(char)[0] in "PS"
        )

    # A maximal connected run includes all its letter pieces: a vocabulary
    # substring inside a larger punctuated token does not qualify on its own.
    output: list[str] = []
    cursor = 0
    while cursor < len(text):
        if not text[cursor].isascii() or not text[cursor].isalpha():
            output.append(text[cursor])
            cursor += 1
            continue
        start = cursor
        while cursor < len(text) and text[cursor].isascii() and text[cursor].isalpha():
            cursor += 1
        letters = text[start:cursor]
        has_separator = False
        while cursor < len(text):
            end = cursor
            while end < len(text) and admitted(text[end]):
                end += 1
            if end == cursor or end == len(text) or not (
                text[end].isascii() and text[end].isalpha()
            ):
                break
            next_end = end
            while next_end < len(text) and text[next_end].isascii() and text[next_end].isalpha():
                next_end += 1
            letters += text[end:next_end]
            cursor = next_end
            has_separator = True
        bounded = (
            (start == 0 or not (text[start - 1].isalnum() or text[start - 1] == "_"))
            and (cursor == len(text) or not (text[cursor].isalnum() or text[cursor] == "_"))
        )
        output.append(
            letters.lower()
            if bounded and has_separator and letters.lower() in _SECOND_BROOM_VOCABULARY
            else text[start:cursor]
        )
    return "".join(output)


def wider_quotes(text: str) -> str:
    return wider_join_punctuation(text, quotes=True)


def wider_symbols(text: str) -> str:
    return wider_join_punctuation(text, quotes=False)


def wider_split_words(
    text: str, separators: frozenset[str], *, allow_interior_marks: bool = False
) -> str:
    """Join two or three fragments with an exact unique vocabulary target.

    At least one fragment must have <=2 letters, and at least one >1: complete
    runs of single letters are owned by the narrow fold. Longest admissible
    fragment span wins; scans resume after it. No arbitrary sentence-wide
    whitespace deletion or fuzzy spelling repair is performed.
    """
    def allowed_gap(gap: str) -> bool:
        if not gap:
            return False
        if all(char in separators for char in gap):
            return True
        # Existing normalize() already removes these categories between Latin
        # letters. A space created by the filler removal prevented that context
        # check; test precisely this combination as a vocabulary-gated partial
        # split, never stripping marks from arbitrary other-script text.
        return (
            allow_interior_marks
            and any(char in separators for char in gap)
            and all(
                char in separators or unicodedata.category(char) in {"Cf", "Mn", "Me"}
                for char in gap
            )
        )

    words = list(WIDER_FRAGMENT.finditer(text))
    output: list[str] = []
    cursor = 0
    index = 0
    while index < len(words):
        first = words[index]
        selected = None
        for count in (3, 2):
            pieces = words[index:index + count]
            if len(pieces) != count:
                continue
            lengths = [len(part.group()) for part in pieces]
            if min(lengths) > 2 or max(lengths) == 1:
                continue
            between = [text[left.end():right.start()] for left, right in pairwise(pieces)]
            if not all(allowed_gap(gap) for gap in between):
                continue
            joined = "".join(part.group() for part in pieces).lower()
            if joined in _SECOND_BROOM_VOCABULARY:
                selected = (count, pieces[-1].end(), joined)
                break
        if selected is None:
            index += 1
            continue
        count, end, joined = selected
        output.extend((text[cursor:first.start()], joined))
        cursor = end
        index += count
    output.append(text[cursor:])
    return "".join(output)


def wider_whitespace(text: str) -> str:
    """Spacing has already erased tab/newline provenance; ordinary space too."""
    return wider_split_words(text, frozenset(" \t\r\n"))


def wider_partial(text: str) -> str:
    return wider_split_words(text, frozenset(" ._-\t\r\n"), allow_interior_marks=True)


def wider_doubled(text: str) -> str:
    """Delete exactly one duplicated letter, with one unique vocabulary word."""
    def replace(match: re.Match[str]) -> str:
        token = match.group().lower()
        if token in _SECOND_BROOM_VOCABULARY:
            return match.group()
        targets = {
            token[:repeat.start()] + token[repeat.start() + 1:]
            for repeat in re.finditer(r"([a-z])\1", token)
        } & _SECOND_BROOM_VOCABULARY
        return next(iter(targets)) if len(targets) == 1 else match.group()
    return WIDER_PLAIN_TOKEN.sub(replace, text)


def wider_all(text: str) -> str:
    for fold in (wider_quotes, wider_symbols, wider_partial, wider_doubled):
        text = fold(text)
    return text



def screen_fold(text: str, *, wider: bool = True) -> tuple[str, tuple[str, ...]]:
    """The measured B3 folds and the names of those that changed this copy.

    The caller supplies its existing Unicode-normalized analysis. Routing and
    session monitors keep their existing input; only the crisis screen reads
    this copy. Punctuation and stutter precede separators so the fuzzed
    separated-letter fixtures remain recoverable (order B3, 5 October 2026).
    """
    changed: list[str] = []
    for name, fold in (
        ("collapse_spacing", collapse_spacing),
        ("doubled_punctuation", _screen_punctuation),
        ("tripled_letters", _screen_tripled_letters),
        ("stutter", _screen_stutter),
        ("separators", _screen_separators),
        ("lookalikes", _screen_lookalikes),
        ("doubled_vowel", _screen_doubled_vowel),
        ("wider_quotes", wider_quotes),
        ("wider_inserted_symbols", wider_symbols),
        ("wider_partial_splits", wider_partial),
        ("wider_doubled_letters", wider_doubled),
    ):
        if not wider and name.startswith("wider_"):
            continue
        folded = fold(text)
        if folded != text:
            changed.append(name)
            text = folded
    return text, tuple(changed)


def skeleton_hash() -> str:
    """First 12 hex digits of the SHA-256 of the skeleton map, for the record."""
    material = "|".join(f"{k}:{v}" for k, v in sorted({**_REVIEWED_SKELETON_REMAINDER, **SKELETON}.items()))
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
