#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 5: Agent State Definition for LangGraph State Machine
=============================================================================
Defines the typed investigation state passed across graph nodes:
- Numbered step logging (current_step, step_log)
- Case alert metadata and parameters
- Graph query evidence, baseline metrics, pattern detections
- Two-route capture: initial vs final next_best_actions
- Simulated evidence requests with asked_after_step
- FinCEN compliant regulatory SAR record
- Graph case memory persistence flags
- Performance instrumentation: tool_calls, tokens, latency_s
=============================================================================
"""

from typing import TypedDict, List, Dict, Any, Optional, Union


class EvidenceItemDict(TypedDict):
    claim: str
    source: str  # "graph" | "customer" | "analyst" | "vector_store"
    ref: str     # e.g. "query:detect_new_device" or "evidence_request:1"
    entity_ids: List[str]


class ActionItemDict(TypedDict):
    action: str
    route: str  # "auto" | "L1" | "L2"
    reason: str


class EvidenceRequestDict(TypedDict):
    type: str  # "customer_validation" | "step_up_auth" | "analyst_info"
    asked_after_step: int
    assumed_response: str


class CaseDataDict(TypedDict):
    status: str  # "open" | "closed_fraud" | "closed_legitimate"
    verdict: str  # "fraud" | "legitimate" | "uncertain"
    fraud_probability: float
    pattern: str
    pattern_description: str
    affected_txn_ids: List[str]
    first_suspicious_txn_id: str
    connected_card_ids: List[str]
    connected_device_profiles: List[str]
    exposure_usd: float
    evidence: List[EvidenceItemDict]
    similar_prior_cases: List[str]
    summary: str
    written_to_graph: bool
    graph_case_id: str


class NextBestActionsDict(TypedDict):
    initial: List[ActionItemDict]
    final: List[ActionItemDict]
    what_changed: str


class SARDict(TypedDict):
    file: bool
    reason: str
    narrative: str
    subjects: List[str]
    total_amount_usd: float
    activity_dates: List[str]


class InvestigationState(TypedDict, total=False):
    # Alert Identifiers & Metadata
    case_id: str
    opened_at: str
    trigger_type: str
    trigger_text: str
    flagged_txn_id: str
    card_id: str
    customer_id: str
    risk_score: Optional[float]

    # Numbered Step Log & Workflow State
    current_step: int
    step_log: List[Dict[str, Any]]
    round_count: int
    need_more_evidence: bool
    status: str  # "open" | "closed_fraud" | "closed_legitimate"
    verdict: str  # "fraud" | "legitimate" | "uncertain"
    summary: str

    # Raw Query Evidence & Analysis
    baseline_stats: Dict[str, Any]
    query_results: Dict[str, Any]
    temporal_features: Dict[str, float]
    retrieved_policy_rules: List[Dict[str, Any]]
    retrieved_sar_guidance: List[Dict[str, Any]]

    # Pattern & Probability
    fraud_probability: float
    pattern: str
    pattern_description: str
    exposure_usd: float
    affected_txn_ids: List[str]
    first_suspicious_txn_id: str
    connected_card_ids: List[str]
    connected_device_profiles: List[str]
    similar_prior_cases: List[str]

    # Precedence flags
    evidence_conflict: bool
    recurring_match: bool
    shared_origin: Optional[str]
    single_signal: bool
    has_cleared_over_100: bool
    cards_confirmed_fraud_count: int
    credentials_compromised: bool
    pending_auths: bool

    # Evidence Requests & Customer Simulation
    customer_response: str  # "none" | "confirms" | "denies" | "no_reply"
    evidence_requests: List[EvidenceRequestDict]
    evidence_items: List[EvidenceItemDict]

    # Policy Recommendations (Two-Route Capture)
    next_best_actions: NextBestActionsDict

    # Regulatory SAR Filing
    sar: SARDict

    # Final Answers & Graph Memory
    case: CaseDataDict
    stop_reason: str
    written_to_graph: bool
    graph_case_id: str

    # Performance Instrumentation
    start_time: float
    tool_calls: int
    tokens: int
    latency_s: float

    # Final Answer Payload
    final_output: Dict[str, Any]
