"""SecondSignal: a model-agnostic routing and safety layer for multi-agent systems."""

from .profiles import AgentProfile, load_profile, load_roster
from .router import RoutingDecision, ScoredAgent, route, score_agent
from .safety import Action, SafetyVerdict, SessionState, evaluate
from .signals import RequestSignals, extract

__version__ = "0.1.0"

__all__ = [
    "AgentProfile",
    "load_profile",
    "load_roster",
    "RoutingDecision",
    "ScoredAgent",
    "route",
    "score_agent",
    "Action",
    "SafetyVerdict",
    "SessionState",
    "evaluate",
    "RequestSignals",
    "extract",
    "__version__",
]
