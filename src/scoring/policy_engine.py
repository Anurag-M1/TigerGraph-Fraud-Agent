"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Policy Engine Interface for Scoring Service (Points to authoritative src.policy)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.policy.policy_engine import (
    PolicyEngine,
    CaseAssessment,
    ActionItem,
    ActionList,
    evaluate_policy,
    get_action_route,
    PERMITTED_ACTIONS,
    ROUTE_TABLE,
    ACTION_EXECUTION_ORDER
)

__all__ = [
    "PolicyEngine",
    "CaseAssessment",
    "ActionItem",
    "ActionList",
    "evaluate_policy",
    "get_action_route",
    "PERMITTED_ACTIONS",
    "ROUTE_TABLE",
    "ACTION_EXECUTION_ORDER"
]
