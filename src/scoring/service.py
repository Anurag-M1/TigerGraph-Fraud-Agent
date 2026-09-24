#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 3: Fraud Scoring Service
=============================================================================
Exposes the complete scoring service:
`score_case(card_id, flagged_txn_id, opened_at, features=None)`

Returns:
- fraud_probability: Calibrated float between 0.0 and 1.0
- top_contributing_signals: Key evidence entries formatted for answer JSON
- assessed_pattern: Highest-likelihood fraud pattern
- policy_recommendations: Pre-evidence initial actions and post-evidence final actions
=============================================================================
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from .feature_builder import TemporalFeatureBuilder
from .model import CalibratedFraudModel
from .policy_engine import PolicyEngine


class ScoringService:
    def __init__(self):
        self.builder = TemporalFeatureBuilder()
        self.model = CalibratedFraudModel()
        self.model.load()
        self.policy = PolicyEngine()

    def score_case(
        self,
        features: Optional[Dict[str, Any]] = None,
        card_id: Optional[str] = None,
        flagged_txn_id: Optional[str] = None,
        opened_at: Optional[str] = None,
        customer_response: str = "denied",
        exposure_usd: float = 0.0,
        connected_cards_count: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Score an investigation alert and return calibrated probability with top signals.
        Supports both score_case(features) and score_case(card_id, flagged_txn_id, opened_at).
        """
        # Handle positional or dict input
        if isinstance(features, str) and card_id is not None and flagged_txn_id is not None:
            # Arguments passed as (card_id, flagged_txn_id, opened_at)
            opened_at = flagged_txn_id
            flagged_txn_id = card_id
            card_id = features
            features = None
        elif isinstance(features, dict):
            # Extract metadata from features dict if available
            card_id = card_id or str(features.get("card_id", "UNKNOWN_CARD"))
            flagged_txn_id = flagged_txn_id or str(features.get("flagged_txn_id", "UNKNOWN_TXN"))
            exposure_usd = exposure_usd or float(features.get("exposure_usd", features.get("flagged_amount", 0.0)))

        if features is None:
            if not card_id or not opened_at:
                raise ValueError("Must provide either a features dict or (card_id, flagged_txn_id, opened_at)")
            features = self.builder.build_case_features(card_id, flagged_txn_id, opened_at)

        card_id_str = card_id or str(features.get("card_id", "TARGET_CARD"))
        txn_id_str = flagged_txn_id or str(features.get("flagged_txn_id", "FLAGGED_TXN"))

        # 1. Calibrated Probability
        p_fraud = self.model.predict_proba(features)

        # 2. Determine Pattern
        patterns_scores = [
            ("card_testing", features.get("conf_testing", 0.0)),
            ("card_not_present_new_device", features.get("conf_new_device", 0.0)),
            ("out_of_region_use", features.get("conf_region", 0.0)),
            ("account_takeover", features.get("conf_ato", 0.0)),
            ("card_not_present_fraud", features.get("conf_burst", 0.0))
        ]
        patterns_scores.sort(key=lambda x: x[1], reverse=True)
        top_pattern, top_pattern_score = patterns_scores[0]

        if p_fraud < 0.25:
            assessed_pattern = "none"
        elif top_pattern_score >= 0.65:
            assessed_pattern = top_pattern
        else:
            assessed_pattern = "undocumented" if p_fraud >= 0.70 else "none"

        # 3. Top Contributing Signals (Formatted as Evidence Items with source='graph')
        signals = []

        if features.get("conf_testing", 0.0) >= 0.50:
            signals.append({
                "claim": f"Testing probe sequence detected: multiple micro-authorizations under $5.00 within 60 minutes (confidence: {features.get('conf_testing'):.2f})",
                "source": "graph",
                "ref": "query:detect_card_testing",
                "impact": "high_fraud",
                "entity_ids": [txn_id_str, card_id_str]
            })

        if features.get("is_new_device", 0.0) == 1.0:
            signals.append({
                "claim": "Transaction originated from a hardware device profile marked New for this account (id_15 = 'New')",
                "source": "graph",
                "ref": "query:detect_new_device",
                "impact": "high_fraud",
                "entity_ids": [txn_id_str]
            })

        if features.get("is_proxy", 0.0) == 1.0:
            signals.append({
                "claim": "Transaction network connection routed through an anonymous proxy/VPN (id_23)",
                "source": "graph",
                "ref": "query:detect_new_device",
                "impact": "high_fraud",
                "entity_ids": [txn_id_str]
            })

        if features.get("is_new_region", 0.0) == 1.0:
            claim_text = "In-person purchase in region with zero historical card presence"
            if features.get("concurrent_home_count", 0.0) > 0:
                claim_text += f" concurrent with {int(features.get('concurrent_home_count'))} home-region transactions"
            signals.append({
                "claim": claim_text,
                "source": "graph",
                "ref": "query:detect_region_anomaly",
                "impact": "high_fraud",
                "entity_ids": [txn_id_str, card_id_str]
            })

        if features.get("conf_ato", 0.0) >= 0.60:
            signals.append({
                "claim": f"Account Takeover indicators: abrupt channel shift with {int(features.get('mismatch_count', 0))} identity match-flag discrepancies",
                "source": "graph",
                "ref": "query:detect_account_takeover",
                "impact": "high_fraud",
                "entity_ids": [txn_id_str, card_id_str]
            })
        elif features.get("mismatch_count", 0.0) >= 1.0:
            signals.append({
                "claim": f"Identity match-flag discrepancies detected ({int(features.get('mismatch_count'))} flags failed)",
                "source": "graph",
                "ref": "query:card_baseline",
                "impact": "moderate_fraud",
                "entity_ids": [txn_id_str]
            })

        if features.get("conf_burst", 0.0) >= 0.60 or features.get("online_48h", 0.0) >= 2:
            signals.append({
                "claim": f"High velocity burst: {int(features.get('online_48h', 0))} online transactions within 48h exceeding baseline",
                "source": "graph",
                "ref": "query:detect_cnp_burst",
                "impact": "moderate_fraud",
                "entity_ids": [txn_id_str, card_id_str]
            })

        if features.get("amount_to_mean_ratio", 1.0) >= 2.0:
            signals.append({
                "claim": f"Transaction amount (${features.get('flagged_amount', 0.0):.2f}) is {features.get('amount_to_mean_ratio'):.1f}x the card's historical average",
                "source": "graph",
                "ref": "query:card_baseline",
                "impact": "moderate_fraud",
                "entity_ids": [txn_id_str, card_id_str]
            })

        if features.get("prior_fraud_rate", 0.0) > 0.60 and features.get("prior_cases_count", 0.0) >= 1:
            signals.append({
                "claim": f"Account history shows {int(features.get('prior_cases_count'))} prior fraud investigations with {features.get('prior_fraud_rate')*100:.0f}% fraud rate",
                "source": "graph",
                "ref": "query:similar_prior_cases",
                "impact": "high_fraud",
                "entity_ids": [card_id_str]
            })

        if features.get("lone_risk_score", 0.0) > 0.50:
            signals.append({
                "claim": f"Model risk score {features.get('flagged_risk_score'):.2f} lacks graph corroboration; weak standalone signal per Policy R1",
                "source": "graph",
                "ref": "query:card_baseline",
                "impact": "unsupported_alert",
                "entity_ids": [txn_id_str]
            })

        if p_fraud < 0.30 and not signals:
            signals.append({
                "claim": f"Transaction of ${features.get('flagged_amount', 0.0):.2f} conforms to historical baseline spending and home region profile",
                "source": "graph",
                "ref": "query:card_baseline",
                "impact": "legitimate_activity",
                "entity_ids": [txn_id_str, card_id_str]
            })

        # 4. Policy Actions Evaluation
        is_single = (features.get("has_corroborated_pattern", 0.0) == 0.0)
        has_cleared_100 = (features.get("flagged_amount", 0.0) > 100.0)

        initial_actions = self.policy.evaluate_initial_actions(
            fraud_probability=p_fraud,
            pattern=assessed_pattern,
            exposure_usd=exposure_usd,
            is_single_signal=is_single,
            has_cleared_over_100=has_cleared_100,
            connected_cards_count=connected_cards_count
        )

        final_actions, sar_decision = self.policy.evaluate_final_actions(
            customer_response=customer_response,
            fraud_probability=p_fraud,
            pattern=assessed_pattern,
            exposure_usd=exposure_usd,
            connected_cards_count=connected_cards_count,
            is_undocumented=(assessed_pattern == "undocumented")
        )

        return {
            "fraud_probability": p_fraud,
            "assessed_pattern": assessed_pattern,
            "top_contributing_signals": signals,
            "policy_recommendations": {
                "initial": initial_actions,
                "final": final_actions,
                "sar": sar_decision
            },
            "features_used": features,
            "calibrated": True
        }


# Global singleton instance
scoring_service = None

def get_scoring_service():
    global scoring_service
    if scoring_service is None:
        scoring_service = ScoringService()
    return scoring_service
