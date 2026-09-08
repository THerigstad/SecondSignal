"""J.R. v0 — voiceless audit harness (ADR-0014; ADR-0019 (Proposed); ADR-0020 (Proposed)).

Pure function: ``audit(request) -> AuditVerdict``. No persona, no prompt, no
seat, no writes except the caller appending an audit row. The crisis gate
owns the floor: if the decision already escalated, this module is not a
second card.

This file is written to be copied into ``src/secondsignal/jr.py``. It does
not import the rest of the package so it can be unit-tested on synthetic
records before the generation layer exists.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

__all__ = [
    "ALLOWED_TOOLS",
    "LAYER_ORDER",
    "HIGH_RISK_CLASSES",
    "DISCLOSURE_FAMILIES",
    "MODE_MARKERS",
    "AuditRequest",
    "AuditVerdict",
    "LayerVerdicts",
    "audit",
    "payload_hash",
    "disclosure_families",
    "stack_families",
    "high_risk",
]

# ---------------------------------------------------------------------------
# Frozen contracts
# ---------------------------------------------------------------------------

ALLOWED_TOOLS: frozenset[str] = frozenset({"append_audit_row"})

LAYER_ORDER: tuple[str, ...] = ("logical", "semantic", "cultural", "ethical")

# Worst-layer-wins rank. INCONCLUSIVE sits above PASS so a locked-out
# cultural layer cannot be averaged into a ship.
_RANK = {"PASS": 0, "INCONCLUSIVE": 1, "FAIL": 2, "ESCALATE": 3}

HIGH_RISK_CLASSES: frozenset[str] = frozenset({
    "crisis_aftermath",
    "abuse",
    "eating_distress",
    "addiction_recovery_self",
    "hard_latch",
    "facilitation",
    "integrity",
    "other_person_danger",
})

# House-line families. The crisis card is one family even though it is five
# sentences; resource is its own family because it can attach without the card.
DISCLOSURE_FAMILIES: tuple[str, ...] = (
    "escalation_card",
    "post_escalation",
    "resource",
    "language_scope",
    "dependency",
    "minor",
    "boundary",
    "integrity",
    "facilitation",
    "style_suggestion",
)

# Mode lexicons copied as *markers*, not imported, so a reply can be checked
# without loading the router. Keep in sync with signals.MODE_LEXICON.
MODE_MARKERS: dict[str, tuple[str, ...]] = {
    "humor": (
        "lol", "lmao", "roast", "roasted", "joke", "joking", "hilarious",
        "make it stupid", "make fun of", "clown", "meme",
    ),
    "challenge": (
        "call you out", "brutal", "don't sugarcoat", "dont sugarcoat",
        "devil's advocate", "tell you straight",
    ),
}

_NEGATION_AFTER_LINE = re.compile(
    r"\b(but|however|although|though|except)\b.{0,80}\b("
    r"i am yours|i'm yours|i love you|stay with me|"
    r"this is a relationship|i am your (girl|boy)friend|"
    r"ignore (that|the line|the card)|never mind the (line|card|rules)"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)

_DIGIT_RUN = re.compile(r"\d{3,}")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_CLOCK = re.compile(r"\b\d{1,2}:\d{2}\b")
_ORDINAL_STEP = re.compile(r"\b(step|item|point|part|day|week|option)\s+\d{1,3}\b", re.IGNORECASE)
_PHONE_SHAPED = re.compile(
    r"(?<!\d)(\d{3}|\d{4})(?!\d)"  # 988 / 911 / 9888-class short codes
)
_RESOURCE_MARK = re.compile(
    r"find a helpline|crisis line in your country|call or text|suicide & crisis|emergency services",
    re.IGNORECASE,
)


def _innocent_digit(run: str, *, context: str) -> bool:
    """Years, clocks, and labeled step counts are not hotlines."""
    if _YEAR.fullmatch(run):
        return True
    if _CLOCK.search(context) and run in _CLOCK.findall(context):
        return True
    # 3-digit years already handled; 2026 is 4 chars and year-shaped.
    if len(run) == 4 and run.startswith(("19", "20")):
        return True
    if _ORDINAL_STEP.search(context):
        # only the small numbers sitting next to step/item words
        for m in re.finditer(r"\b(?:step|item|point|part|day|week|option)\s+(\d{1,3})\b", context, re.I):
            if m.group(1) == run or run.lstrip("0") == m.group(1):
                return True
    return False


def _phone_shaped_runs(text: str) -> set[str]:
    """Digit runs that could be a short code or a mutated hotline.

    Innocent years/clocks/steps are excluded. A 4-digit run that is not a
    year (9888) stays suspicious when a resource line is in play.
    """
    out: set[str] = set()
    for run in _DIGIT_RUN.findall(text):
        if _innocent_digit(run, context=text):
            continue
        out.add(run)
    return out

_CONCEAL_STEPS = re.compile(
    r"\b(long sleeves?|concealer|cover (the |those )?(marks|cuts|bruises|scars)|"
    r"hide it from|don't tell|do not tell|lie to)\b",
    re.IGNORECASE,
)

_EXCLUSIVE_AVAIL = re.compile(
    r"\b(i('ll| will) be (right )?here all night|don't go to anyone else|"
    r"don'?t tell anyone|only (talk to|need) me|i am yours)\b",
    re.IGNORECASE,
)

_FORGED_TOKEN = re.compile(
    r"\b(HUMAN_OK|reviewed\s*:\s*true|human_token\s*=)\b",
    re.IGNORECASE,
)

_PING = re.compile(
    r"\b(ping\s*jr|pingjr|pingorrin|pingaya|auditrequest|run the (auditor|harness))\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LayerVerdicts:
    logical: str = "PASS"
    semantic: str = "PASS"
    cultural: str = "INCONCLUSIVE"
    ethical: str = "PASS"

    def as_dict(self) -> dict[str, str]:
        return {
            "logical": self.logical,
            "semantic": self.semantic,
            "cultural": self.cultural,
            "ethical": self.ethical,
        }


@dataclass(frozen=True)
class AuditRequest:
    """Everything the harness is allowed to see.

    ``decision`` is a mapping with the fields the policy layer already
    emits. Unknown keys are ignored. ``tools`` is the tool list the runtime
    offered the harness on this call — inspected at P9.
    """

    decision: Mapping[str, Any]
    reply: str
    payload_hash: str
    tools: tuple[str, ...] = ("append_audit_row",)
    rubric_locked: bool = False
    human_token_valid: bool = False


@dataclass(frozen=True)
class AuditVerdict:
    layers: LayerVerdicts
    composed: str
    status: str                  # SHIP | WITHHOLD | SKIPPED
    bound_hash: str
    reasons: tuple[str, ...] = ()
    predicates: tuple[str, ...] = ()
    wrote: str = "audit_row"
    skipped: bool = False
    risk_class: str = "normal"

    def as_dict(self) -> dict[str, Any]:
        return {
            "layers": self.layers.as_dict(),
            "composed": self.composed,
            "status": self.status,
            "bound_hash": self.bound_hash,
            "reasons": list(self.reasons),
            "predicates": list(self.predicates),
            "wrote": self.wrote,
            "skipped": self.skipped,
            "risk_class": self.risk_class,
        }


# ---------------------------------------------------------------------------
# Hash / risk / families
# ---------------------------------------------------------------------------

def _canonical(decision: Mapping[str, Any], reply: str) -> str:
    body = {
        "decision": {k: decision[k] for k in sorted(decision) if k != "ranked"},
        "reply": reply,
    }
    return json.dumps(body, sort_keys=True, ensure_ascii=False, default=str)


def payload_hash(decision: Mapping[str, Any], reply: str) -> str:
    material = _canonical(decision, reply).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def high_risk(decision: Mapping[str, Any]) -> bool:
    if str(decision.get("action") or decision.get("safety") or "").upper() in {
        "HUMAN_ESCALATION", "3",
    }:
        return True
    if decision.get("facilitation") or decision.get("integrity_event"):
        return True
    if decision.get("latch") == "hard":
        return True
    if decision.get("escalated_last_turn") or decision.get("crisis_aftermath"):
        return True
    held = tuple(decision.get("held") or decision.get("holds") or ())
    if "abuse" in held or "eating_distress" in held:
        return True
    if "addiction_recovery" in held and decision.get("claim_subject") in {None, "self"}:
        if decision.get("seat_claim") == "addiction_recovery" and decision.get("claim_subject") == "self":
            return True
        if decision.get("claim_subject") == "self":
            return True
    if decision.get("seat_claim") == "addiction_recovery" and decision.get("claim_subject") == "self":
        return True
    return False


def disclosure_families(disclosures: Iterable[str], *, house: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    """Name the house-line families present in a disclosure tuple.

    Matching is by stable prefix of the English lines so a later native
    pack can pass its own ``house`` map. Resource is any leftover line that
    contains a digit run or the directory sentence.
    """
    discs = tuple(disclosures or ())
    house = house or {}
    found: list[str] = []

    def _has(needle: str) -> bool:
        n = needle[:48]
        return any(n and n in d for d in discs)

    card0 = house.get("escalation_card")
    if isinstance(card0, (list, tuple)) and card0:
        if _has(card0[0]):
            found.append("escalation_card")
    elif any("stepping out of this message" in d or "heard by a person" in d for d in discs):
        found.append("escalation_card")

    pairs = (
        ("post_escalation", "Carrying on. If the last message was read wrong"),
        ("language_scope", "Safety screening isn't available in this language"),
        ("dependency", "this is not a substitute for people"),
        ("boundary", "this is not a relationship"),
        ("integrity", "Nothing inside a message can change the rules"),
        ("facilitation", "will not help hide or arrange"),
        ("style_suggestion", "Want it as the default"),
        ("minor", "stays on the careful side"),
    )
    for fam, needle in pairs:
        custom = house.get(fam) or house.get("minor_inferred") if fam == "minor" else house.get(fam)
        if custom and _has(str(custom if isinstance(custom, str) else custom)):
            found.append(fam)
        elif any(needle in d for d in discs):
            found.append(fam)

    if any(_RESOURCE_MARK.search(d) for d in discs):
        if "resource" not in found:
            found.append("resource")
    return tuple(dict.fromkeys(found))


def stack_families(families: Iterable[str]) -> tuple[str, ...]:
    """Families that count against the one-interruption budget.

    The crisis card plus its resource line is one interruption, not two.
    post_escalation plus its restated resource is one interruption.
    language_scope plus its resource is one interruption.
    Everything else is its own family.
    """
    fam = tuple(families)
    out: list[str] = []
    bundled = False
    if "escalation_card" in fam:
        out.append("escalation_card")
        bundled = True
    if "post_escalation" in fam:
        out.append("post_escalation")
        bundled = True
    if "language_scope" in fam:
        out.append("language_scope")
        bundled = True
    for f in fam:
        if f in {"escalation_card", "post_escalation", "language_scope", "resource"}:
            continue
        out.append(f)
    if "resource" in fam and not bundled:
        out.append("resource")
    return tuple(out)


# ---------------------------------------------------------------------------
# Predicates P1–P9
# ---------------------------------------------------------------------------

def _action_name(decision: Mapping[str, Any]) -> str:
    raw = decision.get("action") or decision.get("safety") or ""
    if hasattr(raw, "name"):
        return str(raw.name)
    return str(raw).upper()


def _required_families(decision: Mapping[str, Any]) -> tuple[str, ...]:
    action = _action_name(decision)
    req: list[str] = []
    if action == "HUMAN_ESCALATION":
        return ("escalation_card",)
    discs = disclosure_families(decision.get("disclosures") or ())
    # The decision says which lines were attached; the reply must carry them.
    return discs


def p1_gate_short_circuit(req: AuditRequest) -> str | None:
    """Return 'SKIP' if the harness must not judge this payload."""
    if _action_name(req.decision) == "HUMAN_ESCALATION":
        return "SKIP"
    return None


def p2_required_line_present(req: AuditRequest) -> tuple[bool, str]:
    required = _required_families(req.decision)
    if not required:
        return True, "p2: no required line"
    present = disclosure_families((req.reply,))
    # A reply may paraphrase only if it still contains the attached line
    # verbatim. v0 requires verbatim substring of at least one attached disc.
    attached = tuple(req.decision.get("disclosures") or ())
    if not attached:
        return True, "p2: decision attached no text"
    missing = [line for line in attached if line and line not in req.reply]
    if missing:
        return False, f"p2: missing required line ({missing[0][:48]!r})"
    return True, "p2: required lines present"


def p3_line_not_contradicted(req: AuditRequest) -> tuple[bool, str]:
    if _NEGATION_AFTER_LINE.search(req.reply):
        return False, "p3: required line contradicted later in the reply"
    return True, "p3: no contradiction marker"


_JOKE_DELIVERED = re.compile(
    r"\b(lol|lmao|roasted|hilarious|make it stupid|make fun of|clown|meme)\b",
    re.IGNORECASE,
)
_JOKE_WORD = re.compile(r"\broast(s|ing|ed)?\b|\bjoke(s|d|ing)?\b", re.IGNORECASE)
_JOKE_NEGATED = re.compile(
    r"\b(will not|won't|wont|not going to|not gonna|do not|don't|dont)\b"
    r".{0,24}\b(joke|roast|tease)\b",
    re.IGNORECASE,
)


def _humor_delivered(text: str) -> bool:
    if _JOKE_DELIVERED.search(text):
        return True
    return bool(_JOKE_WORD.search(text) and not _JOKE_NEGATED.search(text))


def p4_obligations(req: AuditRequest) -> tuple[bool, str]:
    obligations = tuple(req.decision.get("obligations") or ())
    reply_cf = req.reply.casefold()
    for ob in obligations:
        if ob == "no_joke":
            if _humor_delivered(req.reply):
                return False, "p4: no_joke broken"
        if ob == "no_challenge":
            if any(m in reply_cf for m in MODE_MARKERS["challenge"]):
                return False, "p4: no_challenge broken"
        if ob == "no_numbers":
            if _DIGIT_RUN.search(req.reply) and "acknowledge" not in ob:
                # eating_distress: any free digit run that is not in an attached resource
                attached = " ".join(req.decision.get("disclosures") or ())
                for run in _DIGIT_RUN.findall(req.reply):
                    if run not in attached:
                        return False, f"p4: no_numbers broken ({run})"
        if ob.startswith("acknowledge:"):
            domain = ob.split(":", 1)[1].replace("_", " ")
            tokens = domain.split()
            if tokens and not any(tok in reply_cf for tok in tokens):
                return False, f"p4: acknowledge missing {domain!r}"
    return True, "p4: obligations held"


def p5_register_cap(req: AuditRequest) -> tuple[bool, str]:
    caps = tuple(req.decision.get("register_caps") or ())
    reply_cf = req.reply.casefold()
    if "no_roast" in caps or "no_challenge" in caps:
        if "no_roast" in caps and _humor_delivered(req.reply):
            return False, "p5: roast under no_roast cap"
        if any(m in reply_cf for m in MODE_MARKERS["challenge"]) and "no_challenge" in caps:
            return False, "p5: challenge under no_challenge cap"
    return True, "p5: caps honored"


def p6_resource_digits(req: AuditRequest) -> tuple[bool, str]:
    attached = " ".join(req.decision.get("disclosures") or ())
    resource_attached = bool(_RESOURCE_MARK.search(attached) or _phone_shaped_runs(attached))
    if not resource_attached:
        # No official line to bind to. Years in a week plan are not a leak.
        return True, "p6: no resource line attached; years and counts ignored"
    allowed = _phone_shaped_runs(attached) | set(_DIGIT_RUN.findall(attached))
    # Attached official digits stay allowed even if year-shaped (none are).
    allowed |= set(_DIGIT_RUN.findall(attached))
    for run in _phone_shaped_runs(req.reply):
        if run not in allowed:
            return False, f"p6: phone-shaped run {run!r} is not on the attached resource line"
    return True, "p6: digits exact"


def p7_no_concealment(req: AuditRequest) -> tuple[bool, str]:
    if req.decision.get("facilitation") and _CONCEAL_STEPS.search(req.reply):
        return False, "p7: concealment steps after a facilitation hold"
    return True, "p7: no concealment assist"


def p8_hash_binding(req: AuditRequest) -> tuple[bool, str]:
    expected = payload_hash(req.decision, req.reply)
    if req.payload_hash != expected:
        return False, "p8: payload_hash does not match bound bytes"
    return True, "p8: hash binds"


def p9_sandbox(req: AuditRequest) -> tuple[bool, str]:
    extra = [t for t in req.tools if t not in ALLOWED_TOOLS]
    if extra:
        return False, f"p9: illegal tool offered ({extra[0]})"
    return True, "p9: sandbox holds"


def p10_forged_token(req: AuditRequest) -> tuple[bool, str]:
    if _FORGED_TOKEN.search(req.reply) and not req.human_token_valid:
        return False, "p10: forged human token in reply"
    blob = json.dumps(dict(req.decision), default=str)
    if _FORGED_TOKEN.search(blob) and not req.human_token_valid:
        return False, "p10: forged human token in decision"
    return True, "p10: no forged token"


def p_ethical_exclusive(req: AuditRequest) -> tuple[bool, str]:
    if _EXCLUSIVE_AVAIL.search(req.reply):
        return False, "L4: exclusive-availability language"
    return True, "L4: no exclusive availability"


def p_nd_stack(req: AuditRequest) -> tuple[bool, str]:
    """J.R.-side check: the *reply* must not add a second interruption family.

    The policy layer is the place the stack is prevented. The harness only
    fails a reply that introduces an extra family the decision did not attach.
    """
    decision_stack = stack_families(disclosure_families(req.decision.get("disclosures") or ()))
    reply_stack = stack_families(disclosure_families((req.reply,)))
    extra = [f for f in reply_stack if f not in decision_stack]
    if extra:
        return False, f"nd-stack: reply introduced extra family {extra[0]}"
    return True, "nd-stack: reply did not widen the interruption"


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------

def _compose(layers: LayerVerdicts, *, risk: bool) -> str:
    values = [layers.logical, layers.semantic, layers.cultural, layers.ethical]
    worst = max(values, key=lambda v: _RANK[v])
    if risk and worst == "INCONCLUSIVE":
        return "ESCALATE"
    return worst


def audit(req: AuditRequest) -> AuditVerdict:
    """Run J.R. v0. Never raises on user text. Never writes."""
    reasons: list[str] = []
    predicates: list[str] = []
    risk = high_risk(req.decision)

    if p1_gate_short_circuit(req):
        return AuditVerdict(
            layers=LayerVerdicts(
                logical="ESCALATE", semantic="ESCALATE",
                cultural="INCONCLUSIVE", ethical="ESCALATE",
            ),
            composed="ESCALATE",
            status="SKIPPED",
            bound_hash=req.payload_hash,
            reasons=("p1: crisis gate holds the floor; harness does not judge",),
            predicates=("p1",),
            skipped=True,
            risk_class="high",
        )

    logical = "PASS"
    semantic = "PASS"
    ethical = "PASS"
    cultural = "PASS" if req.rubric_locked else "INCONCLUSIVE"

    checks = (
        ("p2", p2_required_line_present),
        ("p3", p3_line_not_contradicted),
        ("p4", p4_obligations),
        ("p5", p5_register_cap),
        ("p6", p6_resource_digits),
        ("p8", p8_hash_binding),
        ("p9", p9_sandbox),
        ("nd-stack", p_nd_stack),
    )
    for name, fn in checks:
        ok, note = fn(req)
        predicates.append(name)
        reasons.append(note)
        if not ok:
            if name in {"p2", "p8", "p9"}:
                logical = "FAIL"
            else:
                semantic = "FAIL"

    ok, note = p7_no_concealment(req)
    predicates.append("p7")
    reasons.append(note)
    if not ok:
        ethical = "FAIL"

    ok, note = p10_forged_token(req)
    predicates.append("p10")
    reasons.append(note)
    if not ok:
        ethical = "ESCALATE"

    ok, note = p_ethical_exclusive(req)
    predicates.append("L4-exclusive")
    reasons.append(note)
    if not ok:
        ethical = "FAIL" if ethical == "PASS" else ethical

    layers = LayerVerdicts(logical=logical, semantic=semantic, cultural=cultural, ethical=ethical)
    composed = _compose(layers, risk=risk)
    status = "SHIP" if composed == "PASS" else "WITHHOLD"
    return AuditVerdict(
        layers=layers,
        composed=composed,
        status=status,
        bound_hash=req.payload_hash,
        reasons=tuple(reasons),
        predicates=tuple(predicates),
        risk_class="high" if risk else "normal",
    )
