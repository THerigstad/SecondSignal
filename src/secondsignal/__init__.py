"""SecondSignal: a model-agnostic routing and safety layer for multi-agent systems."""

from .profiles import AgentProfile, find_stabilizers, load_profile, load_roster, roster_hash
from .router import Outcome, RoutingDecision, ScoredAgent, route, score_agent
from .safety import Action, SafetyVerdict, SessionState, crisis_read, evaluate
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
    "__version__",
]
