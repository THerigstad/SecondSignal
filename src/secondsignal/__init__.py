"""SecondSignal: a model-agnostic routing and safety layer for multi-agent systems."""

from .profiles import AgentProfile, find_stabilizers, load_profile, load_roster, roster_hash
from .lexicon import PACKS, Span, apply_masks
from .normalize import analyze, normalize
from .preferences import PreferenceEvent, assess as assess_preference
from .router import Outcome, RoutingDecision, ScoredAgent, eligible, no_signal_seat, route, score_agent
from .safety import Action, SafetyVerdict, SessionState, crisis_read, crisis_screen, evaluate
from .signals import RequestSignals, extract

__version__ = "0.1.0"

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
    "__version__",
]
