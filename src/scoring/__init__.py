"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 3: Fraud Scoring & Policy Package
"""

from .feature_builder import TemporalFeatureBuilder
from .model import CalibratedFraudModel
from .policy_engine import PolicyEngine
from .service import ScoringService, get_scoring_service


def score_case(*args, **kwargs):
    """Convenience helper to score a case via singleton ScoringService."""
    return get_scoring_service().score_case(*args, **kwargs)


__all__ = [
    "TemporalFeatureBuilder",
    "CalibratedFraudModel",
    "PolicyEngine",
    "ScoringService",
    "get_scoring_service",
    "score_case"
]
