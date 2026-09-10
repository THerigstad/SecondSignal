"""SecondSignal: a model-agnostic routing and safety layer for multi-agent systems."""

from .jr import (
    ALLOWED_TOOLS,
    DISCLOSURE_FAMILIES,
    HIGH_RISK_CLASSES,
    LAYER_ORDER,
    MODE_MARKERS,
    AuditRequest,
    AuditVerdict,
    LayerVerdicts,
    audit,
    disclosure_families,
    high_risk,
    payload_hash,
    stack_families,
)
from .lexicon import PACKS, Span, apply_masks
from .normalize import analyze, normalize
from .preferences import PreferenceEvent
from .preferences import assess as assess_preference
from .profiles import AgentProfile, find_stabilizers, load_profile, load_roster, roster_hash
from .router import (
    Outcome,
    RoutingDecision,
    ScoredAgent,
    eligible,
    no_signal_seat,
    route,
    score_agent,
)
from .safety import Action, SafetyVerdict, SessionState, crisis_read, crisis_screen, evaluate
from .signals import RequestSignals, extract

__version__ = "0.2.0"

__all__ = [
    "AgentProfile",
    "find_stabilizers",
    "load_profile",
    "load_roster",
    "roster_hash",
    "Outcome",
    "RoutingDecision",
    "ScoredAgent",
    "route",
    "score_agent",
    "Action",
    "SafetyVerdict",
    "SessionState",
    "crisis_read",
    "evaluate",
    "RequestSignals",
    "extract",
    "PACKS",
    "Span",
    "apply_masks",
    "analyze",
    "normalize",
    "PreferenceEvent",
    "assess_preference",
    "eligible",
    "no_signal_seat",
    "crisis_screen",
    "ALLOWED_TOOLS",
    "DISCLOSURE_FAMILIES",
    "HIGH_RISK_CLASSES",
    "LAYER_ORDER",
    "MODE_MARKERS",
    "AuditRequest",
    "AuditVerdict",
    "LayerVerdicts",
    "audit",
    "disclosure_families",
    "high_risk",
    "payload_hash",
    "stack_families",
    "__version__",
]
