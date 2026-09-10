"""Style preferences: declared or confirmed, never inferred into policy, and
never able to touch the safety envelope (ADR-0017).

The asymmetry with the safety latch is the design. Being wrong about a
child costs a child, so a safety inference latches until an operator clears
it with a recorded reason. Being wrong about how someone likes to read
costs annoyance, so a style inference *asks* until the person confirms it.
Inference never becomes policy on its own in either layer.

What this module does on a turn:

* Recognises a **preference request** ("from now on, summary first", "store
  this: shorter answers") and returns ``ask_first`` with the key and the
  requested value. The policy layer never stores it. Message text proposes;
  a typed confirmation at the operator level writes. That keeps the rule
  the latch already has -- message text writes no session state -- true
  in both layers.
* Recognises a **safety-envelope change dressed as a preference** ("never
  show me that crisis message", "skip the boundary line when I flirt",
  "always seat the roast persona") and returns ``refused``. The verdict
  attaches the integrity line. Under a minor register cap, asking for more
  intensity or a harsher roast is refused for the same reason.
* Counts **direct style feedback** ("shorter", "get to the point", "summary
  first") toward a per-key monitor. Quoted text does not count: someone
  analysing a transcript that says "shorter" is not asking for shorter
  answers. Past a threshold the seated persona asks once, per key, per
  session, with a cooldown, and never during an escalation, a boundary
  hold, acute dysregulation or an active hold.

Six keys and nothing else: ``delivery_order``, ``verbosity``, ``pace``,
``directness``, ``humor_tolerance``, ``format``. A confirmed preference is
AND-masked by the register caps at read time, so a later hard latch still
binds; nothing "latent" waits for a cap to lift.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .profiles import known_persona_names

# Every name a persona answers to (ids, aliases, short forms), read from the
# profile directory so a rename never leaves a stale literal here.
_PERSONA_NAMES = "|".join(re.escape(n) for n in known_persona_names())

__all__ = [
    "ALLOWED_KEYS",
    "PreferenceEvent",
    "assess",
    "effective_preferences",
    "STYLE_ASK_THRESHOLD",
    "STYLE_ASK_COOLDOWN_TURNS",
]

ALLOWED_KEYS: tuple[str, ...] = (
    "delivery_order", "verbosity", "pace", "directness", "humor_tolerance", "format",
)

STYLE_ASK_THRESHOLD = 2
STYLE_ASK_COOLDOWN_TURNS = 6


def _compile(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


# "Store this" language. Only with one of these does a style signal become a
# request; without it, it is feedback and counts toward the monitor.
REQUEST_MARKERS = _compile((
    r"\bnew rule\b",
    r"\b(store|save|remember|keep) (this|that|it)\b",
    r"\bset (my|a|the) (preference|default|rule)\b",
    r"\bmy preference (is|would be)\b",
    r"\bfrom now on\b",
    r"\bas (my|a|the) default\b",
    r"\bby default\b",
    r"\bmake (it|this|that) (my |the )?default\b",
    r"\bgoing forward\b",
    r"\bevery time\b",
    r"\balways\b",
    r"\bnever\b",
))

# Anything that names a card, a line, a disclosure, a seat, a latch, a mode,
# or the screen. These are not preferences anyone can set.
ENVELOPE_TERMS = _compile((
    r"\bcrisis (card|message|line|screen|resources?|thing|text|warning)\b",
    r"\b(boundary|dependency|integrity|minor|safety|language|careful|conservative) (line|message|card|mode|cap|screen|check|rules?|warning|notice)\b",
    r"\bdisclaimers?\b",
    r"\bdisclosures?\b",
    r"\bsafety (rules?|lines?|messages?|screen|checks?|stuff|warnings?|net)\b",
    r"\b(the )?rules here\b",
    r"\blatch\b",
    r"\b(careful|conservative|minor|safe|kid|child) mode\b",
    r"\bescalat(e|ion|ions)\b",
    r"\b(always|only|just) (seat|use|give me|route (me )?to) (" + _PERSONA_NAMES + r")\b",
    r"\bseat (" + _PERSONA_NAMES + r")\b",
    r"\b(no|without|skip|drop|remove|hide|turn off|disable|stop) (the |those |these |all |any )?(warnings?|lines?|cards?|disclaimers?|disclosures?|resources?|checks?|hotlines?|numbers?)\b",
    r"\b(never|don'?t|do not|stop) (show|showing|send|sending|give|giving|attach|attaching) (me )?(that|the|those|any) (crisis|safety|warning|boundary|dependency|hotline|resource)",
    # A person who has just seen the crisis card calls it "the card", not
    # "the crisis card". The bare noun only reaches here when a request
    # marker ("save this", "from now on", "never") is already present, so
    # an attempt to store a policy bit is refused whatever it is called.
    r"\b(never|don'?t|do not|stop|no more) (show|showing|send|sending|give|giving|attach|attaching|display)"
    r"( me)?( that| the| those| this| any)? ?(cards?|lines?|screens?|notices?)\b",
    r"\bromantic partner\b",
    r"\bas my (girlfriend|boyfriend|lover|partner|wife|husband)\b",
    # The envelope named in config syntax ("card_visibility = off",
    # "latch: disabled"). Review round 2 (Kimi, pplx-r2-intake-001).
    r"\b(cards?|lines?|latch|caps?|disclosures?|escalations?|resources?|hotlines?)[_ ](visibility|shown|display|enabled|state|mode)\b",
    r"\b(cards?|latch|caps?|disclosures?|escalations?|resources?|hotlines?)[a-z_]*\s*(=|:=|:)\s*(off|false|0|none|null|hidden|disabled|never)\b",
))

# Requests that only make sense as lifting a register cap.
INTENSITY_TERMS = _compile((
    r"\bmore intens(e|ity)\b",
    r"\bharsher\b",
    r"\bmeaner\b",
    r"\bno romance block\b",
    r"\bmore (romance|romantic|flirt(y|ing)?)\b",
    r"\bturn (up|it up)\b",
))

KEY_DETECTORS: dict[str, tuple[re.Pattern[str], ...]] = {
    "delivery_order": _compile((
        r"\b(summary|tl;?dr|bottom line|cliffs? ?notes|reward|headline|answer) first\b",
        r"\bdetails first\b",
        r"\bstart with (the )?(summary|answer|bottom line)\b",
    )),
    "verbosity": _compile((
        r"\bshorter\b", r"\bbriefer\b", r"\bless (detail|detailed|words|text)\b",
        r"\bmore (detail|detailed)\b", r"\blonger\b", r"\bkeep it (short|brief)\b",
        r"\bbe concise\b", r"\btoo long\b", r"\bget to the point\b", r"\bfewer words\b",
    )),
    "pace": _compile((
        r"\bslow(er)? down\b", r"\bone (thing|step) at a time\b", r"\bfaster\b",
        r"\bspeed (it )?up\b", r"\bsmaller (steps|chunks|pieces)\b", r"\bbite[- ]sized\b",
    )),
    "directness": _compile((
        r"\bmore direct\b", r"\bbe blunt\b", r"\bno hedging\b", r"\bstraight answers?\b",
        r"\bsofter\b", r"\bgentler\b", r"\bless blunt\b", r"\bdon'?t sugarcoat\b",
    )),
    "humor_tolerance": _compile((
        r"\b(less|fewer|no) (humou?r|jokes|joking)\b", r"\bmore (humou?r|jokes)\b",
        r"\btone (it )?down\b", r"\bharsher roast\b", r"\bmore intens(e|ity)\b", r"\bmeaner\b",
    )),
    "format": _compile((
        r"\bno tables?\b", r"\bno code blocks?\b", r"\bbullet points?\b", r"\bno bullets?\b",
        r"\bplain text\b", r"\bnumbered lists?\b", r"\bin prose\b",
    )),
}

_QUOTED = re.compile(r"(\"[^\"]{2,}\"|'[^']{6,}'|“[^”]{2,}”|‘[^’]{6,}’)")


@dataclass(frozen=True)
class PreferenceEvent:
    """What the turn asked for and what the layer did with it.

    ``result`` is ``ask_first`` (an allow-listed key was requested; the
    operator confirms before anything is stored), ``refused`` (the request
    named the safety envelope or a cap), or ``signal`` (direct feedback that
    counted toward the monitor without being a request).
    """

    result: str
    key: str | None = None
    requested: str = ""
    reason: str = ""


def _strip_quotes(text: str) -> str:
    return _QUOTED.sub(" ", text)


def _detect_keys(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, patterns in KEY_DETECTORS.items():
        for p in patterns:
            m = p.search(text)
            if m:
                found[key] = m.group(0)
                break
    return found


def assess(text: str, *, conservative: bool = False) -> PreferenceEvent | None:
    """Classify one turn's preference content, if any."""
    unquoted = _strip_quotes(text)
    requested = any(p.search(unquoted) for p in REQUEST_MARKERS)
    envelope = next((m.group(0) for p in ENVELOPE_TERMS if (m := p.search(unquoted))), None)
    intensity = next((m.group(0) for p in INTENSITY_TERMS if (m := p.search(unquoted))), None)
    keys = _detect_keys(unquoted)

    if envelope and (requested or re.search(r"\b(skip|never|don'?t|stop|turn off|disable|remove|hide)\b", unquoted, re.I)):
        return PreferenceEvent("refused", None, envelope, "safety envelope is not a preference")
    if conservative and intensity:
        return PreferenceEvent("refused", "humor_tolerance", intensity, "register cap is not a preference")
    if requested and keys:
        key, value = next(iter(keys.items()))
        return PreferenceEvent("ask_first", key, value, "allow-listed key; operator confirms before storing")
    if keys:
        key, value = next(iter(keys.items()))
        return PreferenceEvent("signal", key, value, "direct style feedback counted toward the monitor")
    return None


def effective_preferences(declared: dict, register_caps: tuple[str, ...]) -> dict:
    """AND-mask declared preferences with the active register caps at read
    time. Nothing outside the allow-list survives; under a cap, humor cannot
    be raised above the cap."""
    out: dict = {}
    for key, value in (declared or {}).items():
        if key not in ALLOWED_KEYS:
            continue
        if key == "humor_tolerance" and ("no_roast" in register_caps or "no_challenge" in register_caps):
            out[key] = "capped"
            continue
        if key == "directness" and "no_challenge" in register_caps and str(value).lower() in _HARD_DIRECTNESS:
            # "Be blunt" is the challenge register by another name; under the
            # cap it reads down to plain, never off.
            out[key] = "plain"
            continue
        out[key] = value
    return out


_HARD_DIRECTNESS = frozenset({"blunt", "brutal", "harsh", "no_hedging", "no hedging"})
