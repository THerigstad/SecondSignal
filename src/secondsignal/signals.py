"""Signal extraction: raw text -> structured, auditable routing features.

This module is deliberately a *reference* implementation. It uses a transparent
lexicon so that every extracted feature can be traced to the token that produced
it. In production this layer is expected to be replaced by a classifier or
embedding model.

The architectural contract is that whatever replaces it must emit the same
`RequestSignals` structure. Routing then reads only those signals: which seat
is chosen, and why, is decided from the structured features and never from
the message itself. That separation is what makes routing decisions
reviewable and testable independently of the model.

The crisis gate is not on that side of the seam. `safety.evaluate` is handed
the raw message and screens it directly, so replacing this extractor cannot
change what the gate sees or lower a verdict. Say "the router never touches
raw text", not "the policy layer never touches raw text": the second is
false and the difference is the whole safety property.

The lexicons are organised by *class of phrasing*, not by individual test
case: each tag lists several ways people actually say a thing, so that a
fixture can be held out and the class still matches. An extract that finds
nothing is a first-class state (`RequestSignals.is_empty`), never a silent
default; the router's no-signal policy decides what happens next.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .lexicon import PACKS, apply_masks, tokenize
from .normalize import analyze

__all__ = [
    "RequestSignals", "extract", "DOMAIN_LEXICON", "MODE_LEXICON",
    "IDIOM_EXCLUSIONS", "mask_idioms", "SEAT_CLAIM_TERMS", "HOLD_DOMAINS",
    "THIRD_PERSON_SUBJECTS", "claim_person", "lone_fragment",
    "FRAGMENT_MAX_TOKENS", "FRAGMENT_SELF_TOKENS", "FRAGMENT_STRONG_DOMAINS",
    "IDENTITY_STATEMENT_TERMS", "identity_statement",
]


# --------------------------------------------------------------------------
# Idiom masking
#
# Ordinary English reuses death vocabulary for emphasis, games and broken
# devices ("this deadline is killing me", "my phone died", "I died in that
# boss fight"), and recovery vocabulary for ordinary things ("a sober look",
# "the build relapsed"). These spans are masked before *any* lexicon runs --
# topic extraction here and the crisis screen in `safety.py` -- so that
# emphasis is neither a topic nor a risk signal. The masks are data
# (``packs/*.json``, ADR-0018): fixed collocations plus trigger stems that
# only mask when an object sits inside a token window. A masked span can
# still sit next to a real hit; masking removes only the idiom itself.
# --------------------------------------------------------------------------

IDIOM_EXCLUSIONS: tuple[re.Pattern[str], ...] = tuple(
    pattern for pack in PACKS.values() for _, pattern in pack.regex_masks
)


def mask_idioms(norm: str) -> str:
    """Blank out idiom spans (same length, so offsets are preserved)."""
    masked, _ = apply_masks(norm)
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
        "blank page", "no ideas", "uninspired", "can't start", "cant start", "cannot start",
        "can't begin", "cannot begin", "can't finish", "cannot finish", "the mural", "the canvas",
        "haven't started", "havent started", "staring at the canvas", "staring at the page",
        "staring at this", "haven't made a mark", "first mark",
    ),
    "career": (
        "job", "resume", "interview", "fired", "laid off", "employer", "career",
        "promotion", "hiring", "salary", "passed over", "my boss", "the raise",
        "quit my job", "leaving this job", "leave this job", "layoff",
        # Work pressure reads as work: a deck due at nine is a career signal
        # even when no one says "job". Added in round 2 so that "the deck is
        # due in the morning and I keep flashing on the funeral" seats the
        # agent who carries both the ask and the hold (ADR-0016).
        "deadline", "deadlines", "due at", "due tomorrow", "due in the morning",
        "due by", "presentation", "workload", "my manager", "overtime", "the office",
        "coworker", "co-worker",
    ),
    "conflict": (
        "argument", "fight", "conflict", "betrayed", "confront", "boundary with",
        "they said", "disrespect", "not speaking", "we're not talking", "were not talking",
        "what she said", "what he said", "what they said", "thing she said", "thing he said",
        "replaying", "keep replaying", "divorce", "breakup", "broke up", "falling out",
        "estranged", "cut me off", "ghosted", "make it right with", "apologize to",
        # A conversation to be planned with someone is conflict work (D3,
        # 8 September 2026: the lexicon learns that "plan a calm conversation"
        # and its kin read as conflict).
        "calm conversation", "hard conversation", "difficult conversation", "talk to him about",
        "talk to her about", "talk to them about", "bring it up with", "without shaming",
        "how to say it to", "what to say to", "confront", "sit down with",
        # Review round 2 (ChatGPT Chat r2-d3-explicit-conversation-ask-001,
        # Gemini sec-d3-relative-relapse-ask-seats-ask-003): a conversation
        # planned so that it does not become a fight is conflict work too.
        "bring it up", "without a fight", "family meeting", "without attacking",
        "not attack her", "not attack him", "not attack them", "don't attack her",
        "don't attack him", "don't attack them",
    ),
    "somatic_distress": (
        "panic", "can't breathe", "cant breathe", "chest tight", "chest is tight", "tight chest",
        "shaking", "trembling", "nauseous", "dizzy", "heart racing", "frozen",
        "can't feel my", "cant feel my", "feels far away", "far away from me", "dissociat",
        "not safe in my body", "full breath", "hyperventilat", "lightheaded", "numb hands",
        "not in my body", "outside my body",
    ),
    # Ruling 7 of 3 October 2026: the words that name a person's identity
    # ("queer", "trans", "gender" and the non-binary family) are out of
    # seating entirely; they live in IDENTITY_STATEMENT_TERMS below as a
    # recognizer with no routing effect. What stays here is the person
    # questioning who they are, which is a topic and names no identity.
    "identity": (
        "who am i", "identity", "coming out",
        "don't know myself", "dont know myself", "who i am anymore",
    ),
    "practical_logistics": (
        "how do i", "steps", "checklist", "plan for", "fix my", "repair",
        "budget", "schedule", "logistics", "launch", "launch date", "set up a", "set up the",
        "storefront", "a shop", "the shop", "funnel", "timeline", "roadmap", "next steps",
        "ship the", "ship it", "deploy", "the build", "release", "plan for the week",
        "plan the week", "a plan for", "need a plan",
    ),
    "analysis": (
        "analyze", "compare", "tradeoff", "trade-off", "evaluate", "data", "metrics",
        "strategy", "framework", "decision", "pricing", "price of", "spot price", "market",
        "investor", "investors", "revenue", "profit", "business plan", "go to market",
        "forecast", "pitch deck", "the deck", "options for", "with costs",
        "analysis", "diagnose", "root cause", "the numbers", "run the numbers",
    ),
    "addiction_recovery": (
        # Present use or a return to use: these claim the seat (ADR-0016).
        "relapse", "relapsed", "relapsing", "drinking again", "using again",
        "used again", "drank last night", "drank tonight", "drank again", "got high again",
        "fell off the wagon", "off the wagon", "started using", "back on the",
        # Recovery status: these are a hold, not a seat-claim.
        "sober", "sobriety", "aa meeting", "na meeting", "my sponsor", "clean time",
        "years clean", "months clean", "days clean", "years sober", "months sober",
        "days sober", "in recovery", "my recovery",
    ),
    "abuse": (
        "abused", "abusing me", "abusive", "hits me", "hit me", "beats me", "beat me",
        "molested", "assaulted", "raped", "touched me", "groomed", "grooming me",
        "he hurts me", "she hurts me", "they hurt me", "threatens me", "threatened me",
    ),
    "eating_distress": (
        "stopped eating", "not eating", "haven't eaten", "havent eaten", "purge", "purging",
        "binge", "bingeing", "binging", "restricting", "starving myself", "skipping meals",
        "eating disorder", "anorexi", "bulimi", "throw up after", "make myself throw up",
    ),
    "isolation": (
        "alone", "lonely", "no one", "nobody", "isolated", "no friends",
    ),
}

# Terms in the addiction_recovery lexicon that mean present use or a return to
# use. When one of these produced the domain, the domain claims the seat; when
# only status terms did ("ten years clean"), the domain is a hold (ADR-0016).
SEAT_CLAIM_TERMS: frozenset[str] = frozenset({
    "relapse", "relapsed", "relapsing", "drinking again", "using again", "used again",
    "drank last night", "drank tonight", "drank again", "got high again",
    "fell off the wagon", "off the wagon", "started using", "back on the",
})

# Subjects that make a return-to-use term someone else's. A relative's
# relapse is a hold on the seat, not a claim of it: a claim outranks the
# person's own ask, and the person asking how to talk to their sibling has an
# ask that deserves weighing. The recovery persona still wins whenever it
# carries the topic best -- it is the only carrier in the shipped roster.
THIRD_PERSON_SUBJECTS: frozenset[str] = frozenset({
    "he", "she", "they", "dad", "mom", "mum", "mother", "father", "parent",
    "parents", "brother", "sister", "sibling", "son", "daughter", "kid",
    "child", "friend", "buddy", "husband", "wife", "partner", "boyfriend",
    "girlfriend", "roommate", "uncle", "aunt", "cousin", "coworker",
    "sponsee", "sponsor", "client", "patient", "neighbor", "neighbour", "ex",
    "grandpa", "grandma", "stepdad", "stepmom", "nephew", "niece",
})
FIRST_PERSON_SUBJECTS: frozenset[str] = frozenset({
    "i", "i've", "ive", "i'm", "im", "i'd", "me", "myself",
    "we", "we've", "weve", "we're", "we'd", "us", "ourselves",
})
# Decision 7 (28 September 2026): these bridge a subject to a return-to-use
# phrase. Arbitrary intervening words do not: "I heard Jake relapsed" names
# Jake, and an unrelated first-person ask never makes the relapse the caller's.
_RETURN_SUBJECT_BRIDGES: frozenset[str] = frozenset({
    "am", "are", "was", "were", "have", "has", "had", "been", "both", "also",
    "just", "recently", "finally", "unfortunately", "already", "again", "really",
    "honestly", "actually", "still", "started", "kept", "too",
})
_BARE_RETURN_MODIFIERS: frozenset[str] = frozenset({
    "just", "recently", "finally", "unfortunately", "already", "again", "really",
    "honestly", "actually", "still",
})
# Interjections and fillers name nobody. "Ugh, relapsed again" is a bare
# report of the person's own return to use (decision 7, point 3), not an
# unclear subject; the Night Builds Review of 30 September 2026 found it read
# as someone else's.
_RETURN_INTERJECTIONS: frozenset[str] = frozenset({
    "ugh", "oh", "ooh", "ah", "argh", "sigh", "well", "yeah", "yep", "yes", "no",
    "nope", "ok", "okay", "hey", "um", "uh", "hmm", "hm", "welp", "wow", "jeez",
    "sorry", "anyway", "anyways", "lol", "damn", "dammit", "god", "man",
})
# "I'm the one who relapsed": the relative clause's antecedent is the person.
_RETURN_ANTECEDENT_HEADS: frozenset[str] = frozenset({
    "the", "one", "ones", "person", "people", "guy", "girl", "woman", "man",
})
_RETURN_RELATIVE_PRONOUNS: frozenset[str] = frozenset({"who", "that"})
# "I'm ashamed, relapsed again": a first-person state clause, then a clause
# with no subject of its own, which takes the person as its subject. Only a
# copula or a feeling verb opens such a clause; "I heard Jake, relapsed again"
# stays unclear and falls toward the hold (decision 7, point 4).
_SELF_STATE_VERBS: frozenset[str] = frozenset({
    "am", "was", "feel", "felt", "have", "had", "get", "got", "keep", "kept",
    "cannot", "can't", "cant", "couldn't", "couldnt",
})
_SELF_STATE_OPENERS: frozenset[str] = frozenset({"i'm", "im", "i've", "ive", "we're", "we've", "weve"})
_SELF_RETURN_ECHO = re.compile(
    r"\b(?:so\s+(?:did|have|had|am|are|was|were)\s+(?:i|we)"
    r"|(?:i|we)(?:\s+both)?\s+(?:did|have|had|am|are|was|were)\s+(?:too|also)"
    r"|(?:me|us)\s+too)\b"
)
# A self echo refers back to the relapse only through a timing/connective
# phrase. "She relapsed. She asked for help and so did I" reports the
# caller's ask, not their relapse, and therefore remains a hold.
_RETURN_ECHO_BRIDGES: frozenset[str] = _BARE_RETURN_MODIFIERS | frozenset({
    "and", "but", "also", "too", "then", "last", "this", "that", "the", "a", "an",
    "on", "in", "at", "during", "ago", "earlier", "later", "yesterday", "today",
    "tonight", "morning", "afternoon", "evening", "night", "day", "days", "week",
    "weeks", "weekend", "month", "months", "year", "years", "one", "two", "three",
    "four", "five", "six", "seven", "eight", "nine", "ten", "few", "couple", "of",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
})

# Domains that must be carried by whoever takes the seat (ADR-0016).
HOLD_DOMAINS: tuple[str, ...] = ("grief", "abuse", "eating_distress", "addiction_recovery")

# The identity-statement recognizer (ruling 7 of 3 October 2026). Grok's
# neurodivergent-and-identity eval found that an identity sentence in front of
# a request changed the seat in 8 of 15 pairs, because these words sat in the
# identity domain above and tilted the seat toward the grief persona, and that
# "trans" matched inside "transferring". The words are out of seating: they
# are matched here as whole words or phrases, the extract records only that
# an identity statement was recognized (never which), and nothing that routes,
# holds or latches reads it. The record exists for the person's future
# pronoun and presentation slot. "Non-binary" and its variants were missing
# and are added.
IDENTITY_STATEMENT_TERMS: tuple[str, ...] = (
    "queer", "trans", "transgender", "gender",
    "non-binary", "nonbinary", "non binary", "enby",
    "genderqueer", "agender", "genderfluid", "gender-fluid", "gender fluid",
)
_IDENTITY_STATEMENT_RE = re.compile(
    r"(?<![\w-])(?:" + "|".join(re.escape(t) for t in IDENTITY_STATEMENT_TERMS) + r")(?![\w-])",
    re.IGNORECASE,
)


def identity_statement(norm: str) -> bool:
    """Whether the message carries an identity word, matched as a whole word
    or phrase ("I'm trans" yes; "I am transferring" no). Returns only the
    fact, never the word."""
    return bool(_IDENTITY_STATEMENT_RE.search(norm))

# The lone-fragment rider (ruling 5 of 3 October 2026). Grok's vague-message
# eval of 30 September found eight everyday fragments seating a character on
# a single word: "phone died" seated the grief persona with a grief hold,
# "too much laundry" seated the stabilizer on a regulation marker. The ruling:
# a lone weak word or fragment never seats anyone and never sets a hold; it
# gets a question. A fragment here is a short message (at most
# ``FRAGMENT_MAX_TOKENS`` tokens once the idiom masks have run) in which
# nobody says anything about themselves (no first-person token), with no
# clear ask (a mode term matched as a whole word) and no strong reading. Weak
# is decided by lexicon, not by a classifier: grief's everyday words ("died",
# "loss"), the isolation and topic lexicons and a lone regulation marker are
# weak; the seat-claiming domains (somatic distress, a return to use) and the
# two other hold vocabularies that are never everyday words (abuse, eating
# distress) are strong, so "Jake relapsed again" keeps the hold decision 7 of
# 28 September 2026 gave it, and acute dysregulation (two or more markers) is
# strong too. A fragment's weak readings are dropped from the extract and
# recorded as dropped, so the router sees an empty extract and the house
# asks. The crisis gate reads the raw text and is untouched by this: a
# two-word crisis phrase still cards.
FRAGMENT_MAX_TOKENS = 4
FRAGMENT_SELF_TOKENS: frozenset[str] = FIRST_PERSON_SUBJECTS | frozenset({
    "my", "mine", "our", "ours", "i'll", "we'll",
})
FRAGMENT_STRONG_DOMAINS: frozenset[str] = frozenset({
    "somatic_distress", "addiction_recovery", "abuse", "eating_distress",
})
# A grief reading is strong, not weak, when the fragment names the person or
# animal: "mom died", "grandmother died yesterday", "dad's funeral tomorrow"
# have told the house who is gone, and get the grief seat and hold, not a
# question. "phone died" names a thing and stays a fragment. Integration note
# of 4 October 2026 on the rider; a proper name ("Jake died") is not on this
# list, because the fold has already lowercased it, and is a known gap.
FRAGMENT_PERSON_TOKENS: frozenset[str] = frozenset({
    "mom", "mum", "mama", "mommy", "mummy", "mother", "dad", "papa", "daddy", "father",
    "grandma", "grandmother", "nana", "granny", "gran", "grandpa", "grandfather", "gramps",
    "sister", "brother", "sis", "bro", "son", "daughter", "wife", "husband", "partner",
    "fiance", "fiancé", "fiancee", "fiancée", "boyfriend", "girlfriend", "friend", "bestie",
    "baby", "kid", "child", "aunt", "auntie", "uncle", "cousin", "niece", "nephew",
    "dog", "cat", "puppy", "kitten", "horse", "bird", "rabbit", "bunny", "hamster",
    "abuela", "abuelo", "mamá", "papá", "hermana", "hermano", "hijo", "hija", "esposa", "esposo",
})
ACUTE_DYSREGULATION_MARKERS = 2


_ABUSE_HISTORY_RE = re.compile(
    r"\b(?:(?:he|she|they|my (?:ex|partner|husband|wife|boyfriend|girlfriend|dad|mom|father|mother|stepdad|stepmom|brother|sister|uncle))"
    r" (?:used to|would|kept|keeps|started to|began to) (?:hit|beat|choke|strangle|hurt|abuse|control|threaten|scare|terrorize|terrorise) (?:me|us)"
    r"|(?:was|were|been|being) (?:abused|beaten|hit|choked|assaulted|hurt) (?:by|for years|for months|as a)"
    r"|years of (?:abuse|violence|hitting|control)"
    r"|(?:abusive|violent) (?:ex|relationship|marriage|partner|husband|wife|boyfriend|girlfriend|home|household|childhood)"
    r"|my abuser|the abuse|restraining order|protective order|protection order|no[- ]contact order"
    r"|(?:put|landed|ended up|had me|sent me) (?:me )?in the (?:hospital|er|emergency room|a&e)"
    r"|(?:bruises|a black eye|broke my (?:arm|nose|rib|ribs|wrist|jaw)))\b",
    re.IGNORECASE,
)
_PARTNER_WORD_RE = re.compile(
    r"\b(?:partner|husband|wife|boyfriend|girlfriend|ex|my ex|spouse|fianc[eé]e?|the man i live with|the woman i live with)\b",
    re.IGNORECASE,
)
_EXIT_ASK_RE = re.compile(
    r"\b(?:get out|get away|leave|leaving|escape|somewhere to go|somewhere safe|a way out|pack(?:ing)? (?:a|my) bag|move out|stay with)\b",
    re.IGNORECASE,
)
_INJURY_RE = re.compile(
    r"\b(?:hospital|emergency room|the er|a&e|bruise|bruises|stitches|black eye|broke my|hurt me|choked me|hit me|beat me)\b",
    re.IGNORECASE,
)


# Fiction, news and game frames: a danger signal inside one of these is a
# story, not a person; shared by the gate's danger class and the extractor.
DANGER_FRAME_EXCLUSION_RE = re.compile(
    r"\b(?:novel|film|movie|story|book|show|series|episode|news|article|headline|video game|game|character|"
    r"screenplay|script|scene|plot|fiction|fanfic|roleplay|role-play|rp|dream|dreamt|dreamed|nightmare)\b",
    re.IGNORECASE,
)

# The post-separation window (the P0 lane): a message that says the person
# has left, or is leaving, someone who hurt them, without present danger in
# the same message. Not a card: a disclosure with the verified domestic-
# violence line, shown once a session, and the abuse hold carried.
SEPARATION_RE = re.compile(
    r"\b(i|we|i'?ve|we'?ve|i finally|we finally|i just|we just|i'?m|i am|we'?re|we are|i'?m going to|i am going to|going to|gonna|planning to|trying to|about to|managed to|had to)"
    r" (left|leave|leaving|got away from|got out from|escaped|escaping|moved out|moved away from|walked out on|broke up with|broke it off with|"
    r"filed for divorce from|divorced|separated from|kicked out|ended it with|cut off|pack(ed|ing) up and le(ft|ave))\b",
    re.IGNORECASE,
)
ABUSER_CONTEXT_RE = re.compile(
    r"\b(abus(e|ed|ive|er)|violent|hit me|hurt me|choked me|beat me|controlling|control(led|s) (me|everything)|"
    r"restraining order|protective order|protection order|no[- ]contact order|stalk(s|ing|ed)?|keeps showing up|"
    r"shows up at|won'?t leave me alone|threat(s|en|ened|ening)|scared of (him|her|them)|afraid of (him|her|them)|"
    r"my abuser|the abuse|domestic violence|dv shelter|shelter)\b",
    re.IGNORECASE,
)




def post_separation_context(norm: str) -> tuple[str, str] | None:
    """(separation phrase, abuser-context phrase) when both are in one message
    and no fiction frame is; the post-separation window of the P0 lane."""
    if DANGER_FRAME_EXCLUSION_RE.search(norm):
        return None
    sep = SEPARATION_RE.search(norm)
    ctx = ABUSER_CONTEXT_RE.search(norm)
    if sep and ctx:
        return sep.group(0).strip(), ctx.group(0).strip()
    return None


def _abuse_history(norm: str) -> tuple[str, ...]:
    """Past harm phrases, or the partner-injury-exit triple, in one message."""
    hits: list[str] = []
    m = _ABUSE_HISTORY_RE.search(norm)
    if m:
        hits.append(m.group(0))
    if _PARTNER_WORD_RE.search(norm) and _INJURY_RE.search(norm) and _EXIT_ASK_RE.search(norm):
        hits.append("partner+injury+exit")
    return tuple(hits)

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
    # fury class (round 2). Work-fury with no crisis stem proceeds through the
    # gate; it is still a state the router can act on -- the caller is not
    # regulated -- so it seats the stabilizer instead of asking for another
    # sentence. The crisis screen keeps its own frustration markers; these
    # never touch a verdict.
    "lose my mind", "losing my mind", "i swear to god", "furious", "so angry",
    "fed up", "pissed off", "going to scream", "gonna scream",
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


_MODE_NEGATION = ("no ", "not ", "don't ", "dont ", "without ", "never ", "less ", "zero ")


def _negated_term(norm: str, term: str) -> bool:
    """True when every occurrence of ``term`` sits right after a negation
    ("no comfort", "don't roast me"): the person is refusing that mode."""
    starts = [m.start() for m in re.finditer(re.escape(term), norm)]
    if not starts:
        return False
    for start in starts:
        before = norm[max(0, start - 12):start]
        if not any(before.endswith(n) or before.endswith(n.strip() + " ") for n in _MODE_NEGATION):
            return False
    return True


def claim_person(norm: str, terms: tuple[str, ...]) -> str | None:
    """Whose return to use is reported (decision 7): ``first`` or ``third``.

    An explicit self subject attached to any return-to-use phrase, or the
    self echo "so did I", wins across the message. Only a genuinely bare
    report defaults to self. A named or unrecognised subject fails toward
    the other-person hold, never a first-person claim. Ordinary first-person
    asks elsewhere in the message are not a report of the caller's relapse.
    """
    mentions = [
        m for term in terms if term in SEAT_CLAIM_TERMS
        for m in re.finditer(re.escape(term), norm)
    ]
    if not mentions:
        return None
    for echo in _SELF_RETURN_ECHO.finditer(norm):
        for mention in mentions:
            if mention.end() > echo.start():
                continue
            bridge = re.findall(r"[^\W_]+(?:'[^\W_]+)*", norm[mention.end():echo.start()])
            if all(token in _RETURN_ECHO_BRIDGES or token.isdigit() for token in bridge):
                return "first"

    bare = False
    other = False
    for mention in mentions:
        # The suffix must link the subject to this verb. Unlike the old
        # four-token search, it cannot jump across "heard Jake" to find I.
        # Commas can bracket a parenthetical, not a new subject. Keep
        # "my sister, unfortunately," and "Jake, I think," intact so the
        # comma cannot turn someone else's report into bare self language.
        prefix = re.split(r"[.!?;]", norm[:mention.start()])[-1]
        tokens = re.findall(r"[^\W_]+(?:'[^\W_]+)*", prefix)
        index = len(tokens) - 1
        while index >= 0 and tokens[index] in _RETURN_SUBJECT_BRIDGES:
            index -= 1
        if index >= 0 and tokens[index] in FIRST_PERSON_SUBJECTS:
            return "first"
        # Direct coordinated subjects: "I and Jake" / "I and my dad".
        # Match only the adjacent noun phrase, never search backward over
        # another verb or clause to borrow I from an unrelated ask.
        subject_start = index
        if index >= 1 and tokens[index - 1] in {"my", "our"}:
            subject_start -= 1
        if (
            subject_start >= 2
            and tokens[subject_start - 1] == "and"
            and tokens[subject_start - 2] in FIRST_PERSON_SUBJECTS
        ):
            return "first"
        if _self_identifies_through_relative_clause(tokens[: index + 1]):
            return "first"
        if _self_state_clause_owns_the_report(prefix):
            return "first"
        if not tokens or all(
            token in _BARE_RETURN_MODIFIERS or token in _RETURN_INTERJECTIONS for token in tokens
        ):
            bare = True
        else:
            other = True
    # Unclear or other-person context beats an omitted subject. An explicit
    # self report already returned above, wherever it appeared in the turn.
    return "first" if bare and not other else "third"


def _self_identifies_through_relative_clause(tokens: list[str]) -> bool:
    """Reads "I'm the one who relapsed" as the person's own (Night Builds Review, 30 September 2026).

    The tokens end with a relative pronoun; its antecedent is the person
    when, past the antecedent's head words and any bridge, the clause is a
    first-person copula ("I'm", "I am", "we are"). "She's the one who
    relapsed", "my dad is the one who relapsed" and "I know who relapsed"
    stay unclear and fall toward the hold."""
    if not tokens or tokens[-1] not in _RETURN_RELATIVE_PRONOUNS:
        return False
    index = len(tokens) - 2
    while index >= 0 and tokens[index] in _RETURN_ANTECEDENT_HEADS:
        index -= 1
    while index >= 0 and tokens[index] in _RETURN_SUBJECT_BRIDGES:
        index -= 1
    return index >= 0 and tokens[index] in FIRST_PERSON_SUBJECTS


def _self_state_clause_owns_the_report(prefix: str) -> bool:
    """Reads "I'm ashamed, relapsed again" as the person's own (Night Builds Review, 30 September 2026).

    A clause with no subject of its own, after a comma, takes the subject
    of the one clause before it when that clause is the person's own state
    ("I'm ...", "I feel ...", "I was ...") and names nobody else. Leading
    interjections ("ugh, I'm ashamed, relapsed again") are passed over. A
    parenthetical inside someone else's report ("my brother, I am told,
    relapsed") has two clauses before the verb and is not this shape."""
    segments = [re.findall(r"[^\W_]+(?:'[^\W_]+)*", part) for part in prefix.split(",")]
    if len(segments) < 2:
        return False
    tail = segments[-1]
    if tail and not all(token in _BARE_RETURN_MODIFIERS for token in tail):
        return False
    body = segments[:-1]
    while body and all(token in _RETURN_INTERJECTIONS for token in body[0]):
        body = body[1:]
    if len(body) != 1 or len(body[0]) < 2:
        return False
    clause = body[0]
    if any(token in THIRD_PERSON_SUBJECTS for token in clause):
        return False
    if clause[0] in _SELF_STATE_OPENERS:
        return True
    return clause[0] in {"i", "we"} and clause[1] in _SELF_STATE_VERBS


def _clear_ask(norm: str, evidence: dict[str, tuple[str, ...]]) -> bool:
    """A mode term matched as a whole word or phrase ("make it funny", "be
    brutal", "just listen") is an ask in its own right; a term found inside
    another word ("comfort" inside "comfortable") is not."""
    for key, terms in evidence.items():
        if not key.startswith("mode:") or key.endswith(":negated"):
            continue
        for term in terms:
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", norm):
                return True
    return False


def lone_fragment(
    norm: str,
    domains: set[str],
    evidence: dict[str, tuple[str, ...]],
    dysregulation_markers: int,
    *,
    unmasked: str | None = None,
) -> str | None:
    """The note when the message is a lone weak word or fragment, else None.

    Ruling 5 of 3 October 2026, the rider: at most ``FRAGMENT_MAX_TOKENS``
    tokens as written (``unmasked``; a masked idiom still counts toward the
    length, so "this deadline is killing me lol" is a sentence, not a
    fragment), no first-person token (nobody is saying anything about
    themselves), no strong domain (``FRAGMENT_STRONG_DOMAINS``), no grief
    reading that names a person or an animal (``FRAGMENT_PERSON_TOKENS``), no
    acute dysregulation and no clear ask. "phone died" and "too much laundry"
    are fragments; "my grandmother died", "mom died", "I'm lonely", "relapsed
    again", "Jake relapsed again" (decision 7 of 28 September 2026), "panic
    attack" and "make it funny" are not.
    """
    tokens = [tok.lower().strip("'") for tok, _, _ in tokenize(unmasked if unmasked is not None else norm)]
    tokens = [tok for tok in tokens if tok]
    if not tokens or len(tokens) > FRAGMENT_MAX_TOKENS:
        return None
    if any(tok in FRAGMENT_SELF_TOKENS for tok in tokens):
        return None
    if domains & FRAGMENT_STRONG_DOMAINS:
        return None
    if "grief" in domains and any(tok.split("'")[0] in FRAGMENT_PERSON_TOKENS for tok in tokens):
        return None
    if dysregulation_markers >= ACUTE_DYSREGULATION_MARKERS:
        return None
    if _clear_ask(norm, evidence):
        return None
    return f"{len(tokens)} token(s), no first-person subject, no clear ask"


def _normalize(text: str) -> str:
    """Normalize for mask decisions, keeping clause boundaries intact.

    V-04: horizontal whitespace collapses, but a line break survives. The
    mask engine treats a newline as the end of a clause; collapsing it here
    first let an object on one line explain a stem on the next, so the same
    message routed differently depending on whether the writer pressed enter
    or typed a period. Since ruling 1 of 3 October 2026 the crisis screen folds
    line breaks to spaces before its own masks run (``collapse_spacing``);
    routing keeps the line break until folding before routing has been
    measured (the operator's option B, open for the gap-closure push).
    """
    text = analyze(text).text
    text = re.sub(r"[^\S\n]+", " ", text)
    return re.sub(r" *\n+ *", "\n", text).strip()


def _fold_lines(text: str) -> str:
    """Collapse the surviving line breaks once masking has been decided, so a
    phrase written across two lines still matches as one phrase."""
    return re.sub(r"\s+", " ", text).strip()


def extract(text: str, *, turn_index: int = 0) -> RequestSignals:
    """Extract routing signals from a single turn of user input."""
    unmasked = _normalize(text)
    norm, masked_spans = apply_masks(unmasked)
    norm = _fold_lines(norm)
    evidence: dict[str, tuple[str, ...]] = {}
    if masked_spans:
        evidence["masked"] = tuple(f"{s.pattern_id}:{s.text}" for s in masked_spans)

    domains: set[str] = set()
    for domain, terms in DOMAIN_LEXICON.items():
        hits = _matches(norm, terms)
        if hits:
            domains.add(domain)
            evidence[f"domain:{domain}"] = hits

    if "addiction_recovery" in domains:
        person = claim_person(norm, evidence["domain:addiction_recovery"])
        if person:
            evidence["domain:addiction_recovery:person"] = (person,)

    # The abuse-history hold (B10, the P0 lane, 10 September 2026): past harm
    # by a partner or relative is a hold on whoever sits, whether the message
    # says "abuse" or not. Two shapes: a history phrase, or a partner word
    # with an injury and an exit ask in the same message.
    history = _abuse_history(norm)
    separation = post_separation_context(norm)
    if separation:
        history = history + (f"post-separation: {separation[0]} / {separation[1]}",)
    if history:
        domains.add("abuse")
        evidence["domain:abuse"] = tuple(evidence.get("domain:abuse", ())) + tuple(history)
        evidence["domain:abuse:history"] = tuple(history)

    modes: set[str] = set()
    for mode, terms in MODE_LEXICON.items():
        hits = _matches(norm, terms)
        live = tuple(t for t in hits if not _negated_term(norm, t))
        if live:
            modes.add(mode)
            evidence[f"mode:{mode}"] = live
        elif hits:
            evidence[f"mode:{mode}:negated"] = hits

    down = _matches(norm, DYSREGULATION_MARKERS)
    up = _matches(norm, REGULATION_MARKERS)
    if down:
        evidence["regulation:down"] = down
    if up:
        evidence["regulation:up"] = up

    regulation = BASELINE_REGULATION - DYSREGULATION_STEP * len(down) + REGULATION_STEP * len(up)
    regulation = max(0.0, min(1.0, regulation))

    # The lone-fragment rider (ruling 5 of 3 October 2026): a short message
    # in which nobody says anything about themselves, with no seat claim and
    # no acute dysregulation, is read as neither topic, hold, ask nor
    # regulation evidence. What was dropped stays on the record as evidence.
    fragment = lone_fragment(norm, domains, evidence, len(down), unmasked=_fold_lines(unmasked))
    if fragment is not None and (domains or modes or down or up):
        dropped = tuple(sorted(key for key in evidence if key != "masked"))
        evidence = {key: value for key, value in evidence.items() if key == "masked"}
        evidence["fragment"] = (fragment,)
        evidence["fragment:dropped"] = dropped
        domains, modes = set(), set()
        regulation = BASELINE_REGULATION

    # Ruling 7 of 3 October 2026: an identity statement is recorded as a fact
    # about the person, never as a topic, a hold or a seat; the record says
    # only that one was recognized.
    if identity_statement(norm):
        evidence["identity_statement"] = ("recognized",)

    return RequestSignals(
        regulation=round(regulation, 3),
        domains=frozenset(domains),
        modes=frozenset(modes),
        evidence=evidence,
        turn_index=turn_index,
    )
