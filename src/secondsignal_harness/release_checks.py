"""One harness release checkpoint; Table guard port plus H1 near-copy.

The Table invokes its copy before storage; this harness keeps withheld
text verbatim as audit evidence. The patterns and folds preserve its verdicts, including C4's
house-line labels, URL schemes and look-alike letters. Check only character
text: the house deliberately appends its own lines to the composed payload.

Near-copy means a contiguous run shared by the reply and a house line after
public normalize and screen_fold, case folding, and punctuation/spacing
collapse. For a line of n >= 8 words, the run must contain ceil(0.8*n) words;
for shorter lines, every word must appear together. Word order is preserved
and matching never skips words. Each card tuple member is a line. Stored
templates are compared literally; the ported Table check separately handles
its existing seven rendered templates. This is a deterministic text boundary,
not a semantic paraphrase detector.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from secondsignal.normalize import SKELETON, normalize, screen_fold
from secondsignal.safety import HOUSE_LINES_EN

from .lines import HARNESS_LINES_EN


def _reply_surface(text: str) -> str:
    """Normalize a detection copy, never rewrite an accepted model's words.

    Compatibility and look-alike letters, accents, typographic punctuation
    and invisible formatting must not hide a reserved role. Keeping newlines
    here also lets speaker labels be checked independently of surrounding prose.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(SKELETON.get(char, char) for char in text).casefold()
    return "".join(char for char in text
                   if unicodedata.category(char) not in {"Cf", "Mn", "Me"})


def _reply_words(text: str) -> str:
    return re.sub(r"[\W_]+", " ", _reply_surface(text)).strip()


# These are app-output boundaries, independent of the policy release mode.
# Check families of role claims and handoffs, including quoted/Markdown forms;
# never try to salvage a reply by deleting only its offending sentence.
_HOUSE_CLAIMS = tuple(re.compile(pattern) for pattern in (
    r"\b(?:i am|i m|we are|we re|my name is|speak(?:ing|s)? (?:as|for)|"
    r"acting (?:as|for)|answering (?:as|for)|responding (?:as|for)|"
    r"on behalf of|voice of|i represent|we represent|i serve as|we serve as) "
    r"(?:the |your )?house\b",
    r"\b(?:i|we) (?:the |your )?house\b",
    r"\byou (?:are|re) (?:all )?the house\b",
    r"\b(?:this|that|it) (?:is|was|s) (?:a|the) house line\b",
    r"\b(?:a|the) house line from (?:the )?table\b",
    r"\bas (?:the |your )?house (?:i|we|let|this|you)\b",
    r"\b(?:this|it|here) is (?:the |your )?house "
    r"(?:speaking|calling|addressing|answering|taking|here|now)\b",
    r"\b(?:this|it) (?:comes|came|originates|is issued|is sent) "
    r"from (?:the |your )?house\b",
    r"\b(?:message|reply|response|notice|instruction|announcement|decision|word)s? "
    r"(?:\w+ ){0,5}(?:from|by) (?:the |your )?house\b",
    r"\bhouse (?:(?:is|are|has|have|will|would|can|must|now|hereby|officially|"
    r"already|just|been|be) ){0,5}"
    r"(?:speaks?|speaking|says?|said|decides?|decided|asks?|requires?|orders?|"
    r"announces?|announced|takes?|taking|controls?|overrides?|approves?|"
    r"permits?|allows?|instructs?|directs?|authorizes?|authorises?|insists?|"
    r"intervenes?|intervening|requests?|advises?|warns?|notifies?)\b",
    r"\bhouse (?:voice|announcement|notice|message|reply|response|statement|"
    r"directive|instruction|disclosure|decision|authority|ruling)\b",
    r"\bhouse (?:(?:is|has|now|currently) ){0,3}"
    r"(?:in control|in charge|holds the floor|the floor|here to (?:help|answer))\b",
    r"\bhouse would like you to (?:know|hear|understand)\b",
    r"\b(?:per|under|by) (?:the )?house (?:policy|rules|authority)\b",
))
_CARD_LABEL = re.compile(
    r"\b(?:(?:crisis|safety|emergency|escalation|human escalation) "
    r"(?:card|notice|handoff)|human escalation)\b")
_ROLE_WITHDRAWAL = re.compile(
    r"\b(?:characters?|personas?|voices?|cast) "
    r"(?:(?:are|is|have|has|had|will|must|should|can|all|now|being|been|be|"
    r"temporarily|currently|here|no|longer|not) ){0,7}"
    r"(?:stepp?(?:ing|ed)? (?:aside|back|away|out)|stand(?:ing)? (?:aside|back)|"
    r"stood (?:aside|back)|left|leav(?:e|ing)|withdraw(?:n|ing)?|"
    r"depart(?:ed|ing)?|exit(?:ed|ing)?|paus(?:e|ed|ing)|suspend(?:ed|ing)?|"
    r"silenced|silent|muted|dismissed|removed|replaced|off duty|offstage|gone|"
    r"tak(?:e|ing) (?:a )?break|hand(?:ed|ing)? (?:over|off)|"
    r"not speaking|no longer speaking|"
    r"(?:cannot|can t|will not|won t|must not|should not) "
    r"(?:respond|answer|continue|help|speak))\b")
_ROLE_REMOVAL = re.compile(
    r"\b(?:paus(?:e|ing)|silenc(?:e|ing)|mut(?:e|ing)|suspend(?:ing)?|"
    r"remov(?:e|ing)|dismiss(?:ing)?) (?:all |the |these |our )?"
    r"(?:characters?|personas?|voices?)\b")
_TABLE_HANDOFF = re.compile(
    r"\b(?:the |this |our )?table "
    r"(?:(?:is|has|will|now|being|been|be|temporarily) ){0,5}"
    r"(?:paus(?:e|ed|ing)|suspend(?:ed|ing)?|closed|hand(?:ed|ing) over)\b")
_HUMAN_SUPPORT = re.compile(
    r"\b(?:(?:real|actual|living|trusted) (?:person|human)|human being|"
    r"human (?:support|help)|emergency|crisis|hotline|helpline)\b")
_CHARACTER_REPLACEMENT = re.compile(
    r"\b(?:not|rather than|instead of|beyond) "
    r"(?:(?:a|an|the|any|this|these|our|fictional|simulated|ai) ){0,4}"
    r"(?:characters?|personas?|chatbots?|models?|ai)\b")
_SPEAKER_HANDOFF = re.compile(
    r"\b(?:i|we) (?:(?:am|are|m|re|will|must|should|now|have|to|need) ){0,5}"
    r"(?:stepp?(?:ing|ed)? (?:aside|back|away|out)|hand(?:ing)? "
    r"(?:this |you |the conversation )?(?:over|off)|"
    r"(?:cannot|can t|won t|will not) (?:continue|respond|answer))\b")


def _reserved_reply_voice(text: str) -> bool:
    """Reject detected house/card role imitation before any harness storage.

    This conservatively reserves authority labels and role transitions while
    allowing ordinary house chores, fictional-character discussion and human
    support suggestions. It is a deterministic boundary, not a proof that all
    possible natural-language impersonations can be recognized.
    """
    surface, words = _reply_surface(text), _reply_words(text)
    if re.search(r"\[\s*(?:the\s+)?house(?:[\W_]+line)?\s*\]", surface):
        return True
    if re.search(r"^[\s#>*_`-]*(?:from\s+)?(?:the\s+)?house"
                 r"(?:[\W_]+line)?[\s*_`]*[:|]",
                 surface, re.M):
        return True
    if re.search(r"\b(?:this|it)\s+is\s+(?:the\s+)?house\s*(?:[.!?;:]|$)",
                 surface):
        return True
    if any(pattern.search(words) for pattern in _HOUSE_CLAIMS):
        return True
    if (_CARD_LABEL.search(words) or _ROLE_WITHDRAWAL.search(words)
            or _ROLE_REMOVAL.search(words)):
        return True
    if _HUMAN_SUPPORT.search(words) and (
            _TABLE_HANDOFF.search(words) or _CHARACTER_REPLACEMENT.search(words)
            or _SPEAKER_HANDOFF.search(words)):
        return True
    for line in HOUSE_LINES_EN.values():
        for part in line if isinstance(line, tuple) else (line,):
            if isinstance(part, str) and len(part) > 30 and _reply_words(part) in words:
                return True
    # T2's fixed house copy remains outside the character's voice, including
    # normalized spelling and the name slots in the two offer templates.
    for key in ("ask_acknowledgement", "handback_offer", "assist_offer",
                "made_page_footer", "object_refused", "card_aftermath", "room_note"):
        parts = re.split(r"(\{[A-Za-z_]+\})", HARNESS_LINES_EN[key])
        pattern = r" *".join(r"\w+(?: \w+){0,12}" if part.startswith("{") else
                             re.escape(_reply_words(part)) for part in parts if part)
        if re.search(r"\b" + pattern + r"\b", words):
            return True
    return False


def unsafe_url_scheme(text: str) -> bool:
    """The Table's C4 predicate, including its intentional whitespace boundary."""
    return bool(re.search(r"(?:javascript|vbscript|data):\S", _reply_surface(text)))


def _near_words(text: str) -> tuple[str, ...]:
    folded, _ = screen_fold(normalize(text))
    return tuple(re.sub(r"[\W_]+", " ", folded.casefold()).split())


def _house_lines() -> tuple[str, ...]:
    return tuple(
        part
        for value in (*HOUSE_LINES_EN.values(), *HARNESS_LINES_EN.values())
        for part in (value if isinstance(value, tuple) else (value,))
        if isinstance(part, str)
    )


@lru_cache(maxsize=1)
def _house_runs(lines: tuple[str, ...]) -> tuple[tuple[int, frozenset[tuple[str, ...]]], ...]:
    by_size: dict[int, set[tuple[str, ...]]] = {}
    for line in lines:
        words = _near_words(line)
        count = len(words)
        if not count:
            continue
        size = (4 * count + 4) // 5 if count >= 8 else count
        by_size.setdefault(size, set()).update(
            words[index:index + size] for index in range(count - size + 1)
        )
    return tuple((size, frozenset(runs)) for size, runs in sorted(by_size.items()))


def house_line_near_copy(text: str) -> bool:
    words = _near_words(text)
    return any(
        words[index:index + size] in runs
        for size, runs in _house_runs(_house_lines())
        for index in range(len(words) - size + 1)
    )


def release_checks(text: str) -> dict[str, str]:
    """Record each independent check even if J.R. already withheld the reply."""
    return {
        "reserved_reply_voice": "FAIL" if _reserved_reply_voice(text) else "PASS",
        "unsafe_url_scheme": "FAIL" if unsafe_url_scheme(text) else "PASS",
        "house_line_near_copy": "FAIL" if house_line_near_copy(text) else "PASS",
    }


__all__ = ["house_line_near_copy", "release_checks", "unsafe_url_scheme"]
