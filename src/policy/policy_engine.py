#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 4: Pure Python Fraud Policy Engine (Zero LLM)
=============================================================================
Authoritative encoding of Fraud Policy v1.0:
- Actions: 14 permitted actions with strict customer impact definitions
- Approval routing: auto, L1 (Team Lead), L2 (Fraud Manager)
- Precedence rules: R1 to R10
  * Precedence 1: R7 checked before R2 on disputed recurring charges (no block)
  * Precedence 2: R1 gates blocks on single/weak signals (p < 0.70)
  * Precedence 3: R10 gates BLOCK_ALL_CARDS (>= 2 cards or credentials compromised)
  * Precedence 4: R8 fires on uncertainty and exposure > $500 or conflicting evidence
- Section 3a triggers:
  * Case-open trigger: p >= 0.30 | requesting evidence | customer dispute
  * SAR rule: exposure > $1,000 | shared-origin (device/region/email) | R9 undocumented
- Output: Ordered ActionList sorted chronologically by what happens first.
=============================================================================
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Union, Iterator
import json

# -----------------------------------------------------------------------------
# 1. Permitted Actions & Approval Routing Table (Fraud Policy v1.0 Section 1 & 2)
# -----------------------------------------------------------------------------

PERMITTED_ACTIONS = {
    "ALLOW_TRANSACTION",
    "DECLINE_TRANSACTION",
    "MONITOR_CARD",
    "MONITOR_CONNECTED_CARDS",
    "WARN_CUSTOMER",
    "VERIFY_WITH_CUSTOMER",
    "STEP_UP_AUTH",
    "BLOCK_CARD",
    "BLOCK_ALL_CARDS",
    "GENERATE_REPORT",
    "CREATE_CASE",
    "FILE_REPORT",
    "ESCALATE_TO_ANALYST",
    "CLOSE_NO_FRAUD",
}

# Static route lookup table (Section 2)
ROUTE_TABLE = {
    "ALLOW_TRANSACTION": "auto",
    "DECLINE_TRANSACTION": "L1",
    "MONITOR_CARD": "auto",
    "MONITOR_CONNECTED_CARDS": "auto",
    "WARN_CUSTOMER": "auto",
    "VERIFY_WITH_CUSTOMER": "auto",
    "STEP_UP_AUTH": "auto",
    # BLOCK_CARD is exposure-dependent: L1 <= $2,500, L2 > $2,500
    "BLOCK_ALL_CARDS": "L2",
    "GENERATE_REPORT": "auto",
    "CREATE_CASE": "auto",
    "FILE_REPORT": "L2",
    "ESCALATE_TO_ANALYST": "auto",
    "CLOSE_NO_FRAUD": "auto",
}

# Operational execution order: what happens first
# 1. Transaction controls (DECLINE / ALLOW)
# 2. Authentication / Engagement (STEP_UP_AUTH, VERIFY_WITH_CUSTOMER, WARN_CUSTOMER)
# 3. Case creation (CREATE_CASE)
# 4. Primary containment (BLOCK_CARD, BLOCK_ALL_CARDS)
# 5. Monitoring (MONITOR_CARD, MONITOR_CONNECTED_CARDS)
# 6. Escalation / External reporting (FILE_REPORT, ESCALATE_TO_ANALYST)
# 7. Disposition closure (CLOSE_NO_FRAUD)
ACTION_EXECUTION_ORDER = {
    "DECLINE_TRANSACTION": 10,
    "ALLOW_TRANSACTION": 15,
    "STEP_UP_AUTH": 20,
    "VERIFY_WITH_CUSTOMER": 25,
    "WARN_CUSTOMER": 30,
    "CREATE_CASE": 40,
    "BLOCK_CARD": 50,
    "BLOCK_ALL_CARDS": 60,
    "MONITOR_CARD": 70,
    "MONITOR_CONNECTED_CARDS": 80,
    "FILE_REPORT": 90,
    "ESCALATE_TO_ANALYST": 100,
    "GENERATE_REPORT": 110,
    "CLOSE_NO_FRAUD": 120,
}


def get_action_route(action: str, exposure_usd: float = 0.0) -> str:
    """Return the exact Fraud Policy v1.0 approval route for an action."""
    if action not in PERMITTED_ACTIONS:
        raise ValueError(f"Action '{action}' is not a permitted Fraud Policy v1.0 action.")
    if action == "BLOCK_CARD":
        return "L1" if float(exposure_usd) <= 2500.0 else "L2"
    return ROUTE_TABLE[action]


# -----------------------------------------------------------------------------
# 2. Case Assessment Input Data Structure
# -----------------------------------------------------------------------------

@dataclass
class CaseAssessment:
    """Input structure representing the full investigative assessment for policy evaluation."""
    probability: float
    pattern: str = "none"
    exposure_usd: float = 0.0
    customer_response: str = "none"  # "none" | "confirms" | "denies" | "no_reply"
    shared_origin: Optional[str] = None  # "device" | "region" | "email" | None
    evidence_conflict: bool = False
    recurring_match: bool = False
    cards_confirmed_fraud_count: int = 0
    credentials_compromised: bool = False
    pending_auths: bool = False

    # Optional contextual attributes
    single_signal: bool = False
    has_cleared_over_100: bool = False
    requesting_evidence: bool = False
    is_dispute: bool = False
    connected_cards_count: int = 0
    case_id: Optional[str] = None
    card_id: Optional[str] = None
    first_fraud_txn_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseAssessment":
        """Instantiate CaseAssessment from a dictionary, mapping synonyms gracefully."""
        valid_keys = set(cls.__dataclass_fields__.keys())
        kwargs = {}
        for k, v in data.items():
            if k in valid_keys:
                kwargs[k] = v
            elif k == "p_fraud" or k == "fraud_probability":
                kwargs["probability"] = v
            elif k == "exposure":
                kwargs["exposure_usd"] = v
            elif k == "conflict":
                kwargs["evidence_conflict"] = v
        return cls(**kwargs)


# -----------------------------------------------------------------------------
# 3. ActionItem and Ordered ActionList
# -----------------------------------------------------------------------------

@dataclass
class ActionItem:
    """A single recommended action with approval route and rule-citing reason."""
    action: str
    route: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "action": self.action,
            "route": self.route,
            "reason": self.reason
        }

    def __getitem__(self, item):
        return self.to_dict()[item]


class ActionList:
    """Ordered collection of ActionItems, sorted chronologically by operational priority."""
    def __init__(self, actions: Optional[List[ActionItem]] = None):
        self._actions: List[ActionItem] = []
        if actions:
            for a in actions:
                self.add(a)

    def add(self, item: Union[ActionItem, Dict[str, str]]):
        if isinstance(item, dict):
            item = ActionItem(action=item["action"], route=item["route"], reason=item["reason"])
        # Prevent duplicate identical actions; keep highest priority / most specific reason
        for existing in self._actions:
            if existing.action == item.action:
                return
        self._actions.append(item)
        self._sort()

    def _sort(self):
        """Sort actions by chronological operational order."""
        self._actions.sort(key=lambda a: ACTION_EXECUTION_ORDER.get(a.action, 999))

    def contains(self, action_name: str) -> bool:
        return any(a.action == action_name for a in self._actions)

    @property
    def actions_string(self) -> str:
        """Pipe-separated string matching bank closed cases history actions_taken."""
        return "|".join(a.action for a in self._actions)

    @property
    def sar_filed(self) -> bool:
        """True if FILE_REPORT is recommended."""
        return self.contains("FILE_REPORT")

    def to_list(self) -> List[Dict[str, str]]:
        return [a.to_dict() for a in self._actions]

    def __len__(self) -> int:
        return len(self._actions)

    def __getitem__(self, idx) -> ActionItem:
        return self._actions[idx]

    def __iter__(self) -> Iterator[ActionItem]:
        return iter(self._actions)

    def __repr__(self) -> str:
        return f"ActionList({self.actions_string})"


# -----------------------------------------------------------------------------
# 4. Pure Python Policy Engine
# -----------------------------------------------------------------------------

class PolicyEngine:
    """
    Pure Python Policy Engine implementing Fraud Policy v1.0.
    Deterministic, rule-based, zero LLM dependencies.
    """

    def __init__(self):
        self.route_table = ROUTE_TABLE.copy()
        self.permitted_actions = PERMITTED_ACTIONS.copy()

    def evaluate(self, assessment: Union[CaseAssessment, Dict[str, Any]]) -> ActionList:
        """
        Evaluate full policy rules R1-R10 and approval routing for a case assessment.
        Returns an ordered ActionList citing specific rule numbers.
        """
        if isinstance(assessment, dict):
            assessment = CaseAssessment.from_dict(assessment)

        actions = ActionList()

        prob = float(assessment.probability)
        exposure = float(assessment.exposure_usd)
        raw_resp = str(assessment.customer_response).lower().strip()
        if raw_resp in ("confirms", "confirmed"):
            response = "confirms"
        elif raw_resp in ("denies", "denied"):
            response = "denies"
        elif raw_resp in ("no_reply", "no-reply", "noreply"):
            response = "no_reply"
        else:
            response = "none"
        pattern = str(assessment.pattern).strip()
        shared = assessment.shared_origin
        if shared is not None:
            shared = str(shared).lower().strip()
            if shared in ("none", "null", ""):
                shared = None

        has_conflict = bool(assessment.evidence_conflict)
        is_recurring = bool(assessment.recurring_match)
        cards_fraud_count = int(assessment.cards_confirmed_fraud_count)
        credentials_compromised = bool(assessment.credentials_compromised)
        pending_auths = bool(assessment.pending_auths)
        is_single_signal = bool(assessment.single_signal)
        has_cleared_100 = bool(assessment.has_cleared_over_100)
        requesting_evidence = bool(assessment.requesting_evidence)
        is_dispute = bool(assessment.is_dispute)
        connected_cards = int(assessment.connected_cards_count)

        # ---------------------------------------------------------------------
        # Precedence Rule 1: R7 Disputed but Legitimate (checked BEFORE R2)
        # ---------------------------------------------------------------------
        # "When the customer disputes a charge that matches their own recurring pattern
        # (same merchant, same amount, monthly), recommend CREATE_CASE, VERIFY_WITH_CUSTOMER,
        # and WARN_CUSTOMER. Do not block."
        if is_recurring and (response == "denies" or is_dispute):
            actions.add(ActionItem(
                action="CREATE_CASE",
                route=get_action_route("CREATE_CASE"),
                reason="Policy 3a & R7: Customer dispute received on recurring billing charge; open case record"
            ))
            actions.add(ActionItem(
                action="VERIFY_WITH_CUSTOMER",
                route=get_action_route("VERIFY_WITH_CUSTOMER"),
                reason="R7: Re-verify recurring subscription authorization and merchant cancellation status with cardholder"
            ))
            actions.add(ActionItem(
                action="WARN_CUSTOMER",
                route=get_action_route("WARN_CUSTOMER"),
                reason="R7: Send informational alert regarding merchant recurring subscription agreement and billing dispute terms; do not block card"
            ))
            return actions

        # ---------------------------------------------------------------------
        # Precedence Rule 2: R3 Customer Confirms Transaction
        # ---------------------------------------------------------------------
        # "Customer confirms the transaction. Recommend CLOSE_NO_FRAUD. Note the confirmation in the case file."
        if response == "confirms":
            # If case had been previously open or evidence requested, record verification then close
            actions.add(ActionItem(
                action="CLOSE_NO_FRAUD",
                route=get_action_route("CLOSE_NO_FRAUD"),
                reason="R3: Customer explicitly confirmed the transaction as authorized; close alert as legitimate"
            ))
            return actions

        # ---------------------------------------------------------------------
        # Precedence Rule 3: R4 Customer No Reply in 24 Hours
        # ---------------------------------------------------------------------
        # "No reply within 24 hours. Recommend MONITOR_CARD and DECLINE_TRANSACTION
        # for pending authorizations. Escalate if exposure exceeds $500."
        if response == "no_reply":
            if prob >= 0.30 or exposure > 500.0 or requesting_evidence:
                actions.add(ActionItem(
                    action="CREATE_CASE",
                    route=get_action_route("CREATE_CASE"),
                    reason="Policy 3a: Investigation case required for customer non-response on unverified alert"
                ))
            actions.add(ActionItem(
                action="MONITOR_CARD",
                route=get_action_route("MONITOR_CARD"),
                reason="R4: No customer response within 24 hours; place card on 72-hour heightened monitoring"
            ))
            actions.add(ActionItem(
                action="DECLINE_TRANSACTION",
                route=get_action_route("DECLINE_TRANSACTION", exposure),
                reason="R4: Decline pending authorizations while customer response remains unreceived; card remains active"
            ))
            if exposure > 500.0 or has_conflict:
                actions.add(ActionItem(
                    action="ESCALATE_TO_ANALYST",
                    route=get_action_route("ESCALATE_TO_ANALYST"),
                    reason=f"R4 & R8: No customer response and exposure ${exposure:.2f} exceeds $500 threshold; escalate to analyst"
                ))
            return actions

        # ---------------------------------------------------------------------
        # Precedence Rule 4: R8 Escalate when Uncertain and Exposed / Evidence Conflict
        # ---------------------------------------------------------------------
        # "If the verdict is uncertain and exposure exceeds $500, or the evidence conflicts,
        # recommend ESCALATE_TO_ANALYST."
        uncertain_and_exposed = (has_conflict or (0.15 < prob < 0.70 and exposure > 500.0 and response == "none"))
        if uncertain_and_exposed:
            if prob >= 0.30:
                actions.add(ActionItem(
                    action="CREATE_CASE",
                    route=get_action_route("CREATE_CASE"),
                    reason="Policy 3a: Open internal case record for exposed uncertain activity"
                ))
            actions.add(ActionItem(
                action="ESCALATE_TO_ANALYST",
                route=get_action_route("ESCALATE_TO_ANALYST"),
                reason=f"R8: Evidence conflict or uncertain fraud probability ({prob:.2f}) with exposure ${exposure:.2f} > $500; escalate to human analyst"
            ))
            # Continue to evaluate containment / gating below

        # ---------------------------------------------------------------------
        # Precedence Rule 5: R5 Card Testing
        # ---------------------------------------------------------------------
        # "Three or more small online authorizations on one card within an hour,
        # followed by a larger purchase: recommend DECLINE_TRANSACTION and STEP_UP_AUTH.
        # If a purchase over $100 has already cleared, recommend BLOCK_CARD."
        if pattern == "card_testing":
            actions.add(ActionItem(
                action="DECLINE_TRANSACTION",
                route=get_action_route("DECLINE_TRANSACTION", exposure),
                reason="R5: Card testing probe sequence detected; decline pending authorizations"
            ))
            actions.add(ActionItem(
                action="CREATE_CASE",
                route=get_action_route("CREATE_CASE"),
                reason="Policy 3a & R5: Open internal case for detected card testing probe sequence"
            ))
            if has_cleared_100 or exposure > 100.0 or response == "denies":
                block_route = get_action_route("BLOCK_CARD", exposure)
                actions.add(ActionItem(
                    action="BLOCK_CARD",
                    route=block_route,
                    reason=f"R5: Card testing confirmed with cleared purchase over $100; exposure ${exposure:.2f} requires {block_route} approval"
                ))
            else:
                actions.add(ActionItem(
                    action="STEP_UP_AUTH",
                    route=get_action_route("STEP_UP_AUTH"),
                    reason="R5: Probing micro-authorizations detected without cleared large purchase; challenge step-up authentication"
                ))

        # ---------------------------------------------------------------------
        # Precedence Rule 6: R1 Gating Blocks on Weak Signals / Low Probability
        # ---------------------------------------------------------------------
        # "If the case rests on a single signal (including a risk score alone) and your
        # assessed fraud probability is below 0.70, recommend VERIFY_WITH_CUSTOMER or
        # STEP_UP_AUTH before any block. Blocking a legitimate customer on one signal is a policy breach."
        is_weak_or_single = (is_single_signal or prob < 0.70) and response == "none" and pattern != "card_testing"
        if is_weak_or_single:
            # Case open trigger: p >= 0.30 or requesting evidence
            if prob >= 0.30 or requesting_evidence or is_dispute:
                actions.add(ActionItem(
                    action="CREATE_CASE",
                    route=get_action_route("CREATE_CASE"),
                    reason=f"Policy 3a: Fraud probability {prob:.2f} >= 0.30 or evidence requested; open internal investigation case"
                ))
            actions.add(ActionItem(
                action="STEP_UP_AUTH",
                route=get_action_route("STEP_UP_AUTH"),
                reason="R1: Single indicator or moderate probability; mandate step-up authentication before blocking"
            ))
            actions.add(ActionItem(
                action="VERIFY_WITH_CUSTOMER",
                route=get_action_route("VERIFY_WITH_CUSTOMER"),
                reason=f"R1: Probability {prob:.2f} below 0.70 or resting on single signal; verify with cardholder before blocking"
            ))
            # Sub-threshold low risk with zero alerts
            if prob < 0.15 and not actions.contains("CREATE_CASE"):
                actions.add(ActionItem(
                    action="ALLOW_TRANSACTION",
                    route=get_action_route("ALLOW_TRANSACTION"),
                    reason="Policy 1: Low fraud probability and baseline spending match; allow transaction"
                ))
            return actions

        # ---------------------------------------------------------------------
        # Precedence Rule 7: Confirmed Fraud (Customer Denies or Multi-Signal p >= 0.70)
        # ---------------------------------------------------------------------
        is_confirmed_or_high_prob = (response == "denies" or prob >= 0.70 or pattern in ("undocumented", "card_testing"))

        if is_confirmed_or_high_prob:
            # 1. CREATE_CASE (Policy 3a)
            if not actions.contains("CREATE_CASE"):
                actions.add(ActionItem(
                    action="CREATE_CASE",
                    route=get_action_route("CREATE_CASE"),
                    reason=f"Policy 3a: Strong fraud evidence established (probability {prob:.2f} >= 0.70 or customer denial)"
                ))

            # 2. DECLINE pending authorizations if flagged
            if pending_auths and not actions.contains("DECLINE_TRANSACTION"):
                actions.add(ActionItem(
                    action="DECLINE_TRANSACTION",
                    route=get_action_route("DECLINE_TRANSACTION", exposure),
                    reason="Policy 1: Decline in-flight fraudulent authorization on compromised card"
                ))

            # 3. BLOCK_CARD (Policy R2 & R5, Route: L1 <= $2,500, L2 > $2,500)
            can_block = True
            if pattern == "card_testing" and not has_cleared_100 and exposure <= 100.0 and response != "denies":
                can_block = False

            if can_block and not actions.contains("BLOCK_CARD"):
                block_route = get_action_route("BLOCK_CARD", exposure)
                actions.add(ActionItem(
                    action="BLOCK_CARD",
                    route=block_route,
                    reason=f"R2: Confirmed fraudulent compromise (probability {prob:.2f}); exposure ${exposure:.2f} requires {block_route} approval"
                ))

            # 4. Rule R10 Gating: BLOCK_ALL_CARDS
            # "Never BLOCK_ALL_CARDS unless at least two of the customer's cards show confirmed
            # fraud or the customer's credentials are confirmed compromised."
            if cards_fraud_count >= 2 or credentials_compromised:
                comp_reason = "credentials confirmed compromised" if credentials_compromised else f"{cards_fraud_count} customer cards confirmed compromised"
                actions.add(ActionItem(
                    action="BLOCK_ALL_CARDS",
                    route=get_action_route("BLOCK_ALL_CARDS"),
                    reason=f"R10: Multiple cards compromised or credential breach ({comp_reason}); block all customer cards"
                ))

            # 5. Section 3a SAR Filing Rule (FILE_REPORT, Route: L2 always)
            # Mandatory when confirmed/strongly suspected AND:
            # - exposure > $1,000 OR
            # - shared origin (device, region, email) OR
            # - undocumented coordinated abuse pattern (Rule R9)
            file_sar = False
            sar_reasons = []

            if exposure >= 1000.0:
                file_sar = True
                sar_reasons.append(f"exposure of ${exposure:.2f} meets or exceeds $1,000 regulatory filing threshold")

            if shared in ("device", "region", "email") or connected_cards >= 2:
                file_sar = True
                elem = shared if shared else "device profile"
                sar_reasons.append(f"activity connects to shared {elem} ring across multiple payment cards (Rule R6)")

            if pattern == "undocumented":
                file_sar = True
                sar_reasons.append("coordinated undocumented abuse pattern detected across customers (Rule R9)")

            if file_sar and not actions.contains("FILE_REPORT"):
                actions.add(ActionItem(
                    action="FILE_REPORT",
                    route=get_action_route("FILE_REPORT"),
                    reason=f"Policy 3a & R2: Mandatory Suspicious Activity Report (SAR) filing as {'; and '.join(sar_reasons)}"
                ))

            # 6. Rule R6: MONITOR_CONNECTED_CARDS
            if shared in ("device", "region", "email") or connected_cards >= 2:
                elem = shared if shared else "device profile"
                actions.add(ActionItem(
                    action="MONITOR_CONNECTED_CARDS",
                    route=get_action_route("MONITOR_CONNECTED_CARDS"),
                    reason=f"R6: Shared {elem} links activity to other payment cards; raise monitoring sensitivity"
                ))

            # 7. Rule R9: ESCALATE_TO_ANALYST for undocumented patterns
            if pattern == "undocumented" and not actions.contains("ESCALATE_TO_ANALYST"):
                actions.add(ActionItem(
                    action="ESCALATE_TO_ANALYST",
                    route=get_action_route("ESCALATE_TO_ANALYST"),
                    reason="R9: Coordinated novel pattern fits no known typology; escalate to human analyst for forensic cataloging"
                ))

        # Default fallback if empty
        if len(actions) == 0:
            if prob >= 0.30:
                actions.add(ActionItem(
                    action="CREATE_CASE",
                    route=get_action_route("CREATE_CASE"),
                    reason=f"Policy 3a: Fraud probability {prob:.2f} >= 0.30; open internal investigation case"
                ))
                actions.add(ActionItem(
                    action="VERIFY_WITH_CUSTOMER",
                    route=get_action_route("VERIFY_WITH_CUSTOMER"),
                    reason="Policy 1: Verify transaction with cardholder"
                ))
            else:
                actions.add(ActionItem(
                    action="ALLOW_TRANSACTION",
                    route=get_action_route("ALLOW_TRANSACTION"),
                    reason="Policy 1: Sub-threshold fraud probability and clean card baseline; allow transaction"
                ))

        return actions

    def evaluate_initial_actions(
        self,
        fraud_probability: float,
        pattern: str = "none",
        exposure_usd: float = 0.0,
        is_single_signal: bool = False,
        has_cleared_over_100: bool = False,
        connected_cards_count: int = 0,
        shared_origin: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Compute initial recommendations BEFORE customer validation (Section 3b)."""
        origin = shared_origin or ("device" if connected_cards_count >= 2 else None)
        assessment = CaseAssessment(
            probability=fraud_probability,
            pattern=pattern,
            exposure_usd=exposure_usd,
            customer_response="none",
            shared_origin=origin,
            single_signal=is_single_signal,
            has_cleared_over_100=has_cleared_over_100,
            connected_cards_count=connected_cards_count
        )
        return self.evaluate(assessment).to_list()

    def evaluate_final_actions(
        self,
        customer_response: str,
        fraud_probability: float,
        pattern: str = "none",
        exposure_usd: float = 0.0,
        connected_cards_count: int = 0,
        shared_origin: Optional[str] = None,
        is_undocumented: bool = False,
        recurring_match: bool = False
    ) -> Any:
        """Compute final recommendations AFTER customer evidence and evaluate SAR requirement."""
        actual_pattern = "undocumented" if is_undocumented else pattern
        origin = shared_origin or ("device" if connected_cards_count >= 2 else None)
        assessment = CaseAssessment(
            probability=fraud_probability,
            pattern=actual_pattern,
            exposure_usd=exposure_usd,
            customer_response=customer_response,
            shared_origin=origin,
            connected_cards_count=connected_cards_count,
            recurring_match=recurring_match
        )
        action_list = self.evaluate(assessment)
        actions = action_list.to_list()

        sar_item = next((a for a in actions if a["action"] == "FILE_REPORT"), None)
        sar_decision = {
            "file": sar_item is not None,
            "reason": sar_item["reason"] if sar_item else f"Exposure ${exposure_usd:.2f} under $1,000 threshold and no multi-card shared origin detected"
        }
        return actions, sar_decision


# -----------------------------------------------------------------------------
# 5. Standalone Evaluation Functions
# -----------------------------------------------------------------------------

_default_policy_engine = PolicyEngine()

def evaluate_policy(assessment: Union[CaseAssessment, Dict[str, Any]]) -> ActionList:
    """Convenience helper to evaluate policy on a CaseAssessment or dict."""
    return _default_policy_engine.evaluate(assessment)
