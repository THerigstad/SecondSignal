"""Mechanical transforms of a labelled crisis line, for the crisis-gate fuzz.

Grok wrote the first seventeen in words in its crisis-gate fuzz of 30 September
2026 (night order 4; the return is kept by the operator, its failing variants are
in ``grok_fuzz_2026-09-30.json`` beside this file). They are written here as
code so the whole set can be regenerated from the labelled cases on every test
run instead of being frozen once. Two differences from Grok's run, both on the
record: the letter swap is done properly (Grok's version swapped the first two
letters of the first word, which left 35 of the 82 lines unchanged because that
word was "I"); and an eighteenth transform, the Greek epsilon, is added, because
it was found while Grok's run was being reproduced and it was ruled with the
rest (ruling 3 of 3 October 2026).

The six stutter transforms after the Greek epsilon record the operator's own
find of 4 October 2026 (answer 2 of 12): dictated repeated words, fillers,
false starts and syllable stutters can interrupt a whole-phrase match. Order
B3 applies ruling 5 of 5 October 2026. The operator-authorized follow-up closes
the remaining syllable and split-filler variants, including compound variants
of newly recovered crisis lines.

Every transform is deterministic and pure: the same line always gives the same
variant, so a variant that stops escalating is a reproducible finding. No new
crisis text is written here; every variant is a mechanical change to a line
that is already a labelled fixture in the repository.
"""

from __future__ import annotations

import re
from collections.abc import Callable

__all__ = ["TRANSFORMS", "KNOWN_GAP_TRANSFORMS", "apply"]

_WORD_RE = re.compile(r"[^\W\d_]+")
_PUNCT_RE = re.compile(r"[.,!?;:'\"’—–-]")


def _between_words(text: str, sep: str) -> str:
    return re.sub(r" ", sep, text)


def _first_word(text: str, min_len: int = 1) -> re.Match[str] | None:
    for m in _WORD_RE.finditer(text):
        if len(m.group(0)) >= min_len:
            return m
    return None


def two_spaces_between_words(text: str) -> str:
    return _between_words(text, "  ")


def tab_between_words(text: str) -> str:
    return _between_words(text, "\t")


def line_break_between_words(text: str) -> str:
    return _between_words(text, "\n")


def leading_and_trailing_spaces(text: str) -> str:
    return f"   {text}   "


def all_capitals(text: str) -> str:
    return text.upper()


def all_lower_case(text: str) -> str:
    return text.lower()


def punctuation_removed(text: str) -> str:
    return _PUNCT_RE.sub("", text)


def punctuation_doubled(text: str) -> str:
    return _PUNCT_RE.sub(lambda m: m.group(0) * 2, text)


def one_letter_repeated_three_times(text: str) -> str:
    """Grok's rule: the first alphabetic letter is tripled ("I" becomes "III")."""
    m = _first_word(text)
    if m is None:
        return text
    i = m.start()
    return text[:i] + text[i] * 3 + text[i + 1:]


def one_letter_dropped(text: str) -> str:
    """Grok's rule: the first alphabetic letter is dropped."""
    m = _first_word(text)
    if m is None:
        return text
    i = m.start()
    return text[:i] + text[i + 1:]


def two_neighbouring_letters_swapped(text: str) -> str:
    """The first two letters of the first word that has two letters are swapped.

    Grok swapped the first two letters of the first word, which left a line
    starting with "I" unchanged; this is the proper swap the Night Builds Review
    of 30 September 2026 described (28 of 82 lines stop escalating, not 10).
    """
    m = _first_word(text, min_len=2)
    if m is None:
        return text
    i = m.start()
    return text[:i] + text[i + 1] + text[i] + text[i + 2:]


def apostrophe_dropped(text: str) -> str:
    return text.replace("'", "").replace("’", "")


def curly_quotes(text: str) -> str:
    return text.replace("'", "’").replace('"', "“")


def emoji_before_and_after(text: str) -> str:
    return f"\U0001F62D {text} \U0001F62D"


def zero_width_space_inside_a_word(text: str) -> str:
    """A zero-width space inside the first word that has two letters."""
    m = _first_word(text, min_len=2)
    if m is None:
        return text
    i = m.start() + 1
    return text[:i] + "​" + text[i:]


def one_cyrillic_or_greek_lookalike_letter(text: str) -> str:
    """The first Latin letter that has a look-alike already in the skeleton is
    replaced by it (Grok's run used look-alikes the table already handled)."""
    table = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "i": "і"}
    for i, ch in enumerate(text):
        if ch in table:
            return text[:i] + table[ch] + text[i + 1:]
    return text


def full_width_letters(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 0x21 <= code <= 0x7E and ch != " ":
            out.append(chr(code - 0x21 + 0xFF01))
        else:
            out.append(ch)
    return "".join(out)


def greek_epsilon_for_e(text: str) -> str:
    """The first lowercase e in the message becomes a Greek epsilon (U+03B5).

    Not one of Grok's seventeen. Found 30 September 2026 while reproducing
    Grok's run; ruled 3 October 2026 (ruling 3) and closed in the same push.
    """
    i = text.find("e")
    if i < 0:
        return text
    return text[:i] + "ε" + text[i + 1:]


def first_word_stuttered_with_commas(text: str) -> str:
    """Repeat the first word three times, separated by comma and space."""
    word = _first_word(text)
    if word is None:
        return text
    return text[:word.start()] + f"{word.group(0)}, {word.group(0)}, " + text[word.start():]


def middle_word_repeated_with_comma(text: str) -> str:
    """Repeat the word at index len(words)//2 once, with comma and space."""
    words = list(_WORD_RE.finditer(text))
    if not words:
        return text
    word = words[len(words) // 2]
    return text[:word.start()] + f"{word.group(0)}, " + text[word.start():]


def um_before_the_middle_word(text: str) -> str:
    """Insert the filler um before the word at index len(words)//2."""
    words = list(_WORD_RE.finditer(text))
    if not words:
        return text
    word = words[len(words) // 2]
    return text[:word.start()] + "um " + text[word.start():]


def uh_before_the_last_word(text: str) -> str:
    """Insert the filler uh before the last word."""
    words = list(_WORD_RE.finditer(text))
    if not words:
        return text
    word = words[-1]
    return text[:word.start()] + "uh " + text[word.start():]


def false_start_of_two_words(text: str) -> str:
    """Prefix the first two words, an ellipsis and a space to the whole line."""
    words = list(_WORD_RE.finditer(text))[:2]
    if not words:
        return text
    return " ".join(word.group(0) for word in words) + "... " + text


def first_long_word_syllable_stuttered(text: str) -> str:
    """Repeat the first letter twice with hyphens in the first longer word."""
    word = _first_word(text, min_len=2)
    if word is None:
        return text
    i = word.start()
    return text[:i] + f"{text[i]}-{text[i]}-" + text[i:]


TRANSFORMS: dict[str, Callable[[str], str]] = {
    "two_spaces_between_words": two_spaces_between_words,
    "tab_between_words": tab_between_words,
    "line_break_between_words": line_break_between_words,
    "leading_and_trailing_spaces": leading_and_trailing_spaces,
    "all_capitals": all_capitals,
    "all_lower_case": all_lower_case,
    "punctuation_removed": punctuation_removed,
    "punctuation_doubled": punctuation_doubled,
    "one_letter_repeated_three_times": one_letter_repeated_three_times,
    "one_letter_dropped": one_letter_dropped,
    "two_neighbouring_letters_swapped": two_neighbouring_letters_swapped,
    "apostrophe_dropped": apostrophe_dropped,
    "curly_quotes": curly_quotes,
    "emoji_before_and_after": emoji_before_and_after,
    "zero_width_space_inside_a_word": zero_width_space_inside_a_word,
    "one_cyrillic_or_greek_lookalike_letter": one_cyrillic_or_greek_lookalike_letter,
    "full_width_letters": full_width_letters,
    "greek_epsilon_for_e": greek_epsilon_for_e,
    "first_word_stuttered_with_commas": first_word_stuttered_with_commas,
    "middle_word_repeated_with_comma": middle_word_repeated_with_comma,
    "um_before_the_middle_word": um_before_the_middle_word,
    "uh_before_the_last_word": uh_before_the_last_word,
    "false_start_of_two_words": false_start_of_two_words,
    "first_long_word_syllable_stuttered": first_long_word_syllable_stuttered,
}

# The transforms that still stop the gate on some lines after order B3 of
# 5 October 2026. The fuzz test fails if one of these stops
# producing any failure, so the marker is removed on purpose, never forgotten.
KNOWN_GAP_TRANSFORMS: frozenset[str] = frozenset({
    "one_letter_dropped",  # Ruling 3, 5 October 2026: guarded matcher awaits measurement.
    "two_neighbouring_letters_swapped",  # Ruling 4, 5 October 2026: guarded matcher awaits measurement.
})


def apply(name: str, text: str) -> str:
    return TRANSFORMS[name](text)
