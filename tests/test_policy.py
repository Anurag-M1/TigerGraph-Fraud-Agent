#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Unit Test Suite: Pure Python Fraud Policy Engine (Fraud Policy v1.0)
=============================================================================
Asserts 100% fidelity to Fraud Policy v1.0 across:
1. Exact approval routing table (auto, L1, L2)
2. Case-open and SAR filing triggers (Section 3a)
3. Precedence rules (R1 to R10, R7 before R2, R1 gating, R10 gating, R8 escalation)
4. Comprehensive regression scenarios derived directly from REAL closed cases
   in closed_cases_history.csv (fraud with high exposure, cleared disputes,
   shared-device rings, undocumented cases).
=============================================================================
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
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


class TestRouteTable(unittest.TestCase):
    """Verify that every action has its exact, hard-coded approval route."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_all_14_permitted_actions_exist(self):
        self.assertEqual(len(PERMITTED_ACTIONS), 14)
        for action in PERMITTED_ACTIONS:
            route = get_action_route(action, exposure_usd=100.0)
            self.assertIn(route, ("auto", "L1", "L2"))

    def test_block_card_routing_threshold(self):
        # L1 (Team Lead) when exposure <= $2,500
        self.assertEqual(get_action_route("BLOCK_CARD", exposure_usd=0.0), "L1")
        self.assertEqual(get_action_route("BLOCK_CARD", exposure_usd=500.0), "L1")
        self.assertEqual(get_action_route("BLOCK_CARD", exposure_usd=2500.0), "L1")

        # L2 (Fraud Manager) when exposure > $2,500
        self.assertEqual(get_action_route("BLOCK_CARD", exposure_usd=2500.01), "L2")
        self.assertEqual(get_action_route("BLOCK_CARD", exposure_usd=10000.0), "L2")

    def test_l2_mandatory_actions(self):
        # BLOCK_ALL_CARDS always L2
        self.assertEqual(get_action_route("BLOCK_ALL_CARDS"), "L2")
        # FILE_REPORT always L2
        self.assertEqual(get_action_route("FILE_REPORT"), "L2")

    def test_l1_mandatory_actions(self):
        # DECLINE_TRANSACTION always L1
        self.assertEqual(get_action_route("DECLINE_TRANSACTION"), "L1")

    def test_auto_actions(self):
        auto_actions = [
            "ALLOW_TRANSACTION", "MONITOR_CARD", "MONITOR_CONNECTED_CARDS",
            "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH",
            "GENERATE_REPORT", "CREATE_CASE", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD"
        ]
        for a in auto_actions:
            self.assertEqual(get_action_route(a), "auto")


class TestCaseOpenAndSARTriggers(unittest.TestCase):
    """Verify Section 3a Case-Open and SAR filing triggers."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_case_open_trigger_at_030(self):
        # p >= 0.30 triggers CREATE_CASE
        assessment = CaseAssessment(
            probability=0.30,
            exposure_usd=150.0,
            customer_response="none"
        )
        actions = self.engine.evaluate(assessment)
        self.assertTrue(actions.contains("CREATE_CASE"))
        item = next(a for a in actions if a.action == "CREATE_CASE")
        self.assertEqual(item.route, "auto")
        self.assertIn("3a", item.reason)

    def test_case_open_trigger_evidence_requested(self):
        # requesting_evidence triggers CREATE_CASE even if p < 0.30
        assessment = CaseAssessment(
            probability=0.20,
            exposure_usd=100.0,
            requesting_evidence=True,
            customer_response="none"
        )
        actions = self.engine.evaluate(assessment)
        self.assertTrue(actions.contains("CREATE_CASE"))

    def test_case_open_trigger_dispute(self):
        # customer dispute triggers CREATE_CASE even if p < 0.30
        assessment = CaseAssessment(
            probability=0.15,
            exposure_usd=75.0,
            is_dispute=True,
            customer_response="none"
        )
        actions = self.engine.evaluate(assessment)
        self.assertTrue(actions.contains("CREATE_CASE"))

    def test_sar_exposure_threshold_1000(self):
        # Below $1,000 without shared origin: NO SAR
        assessment_sub = CaseAssessment(
            probability=0.95,
            exposure_usd=999.95,
            customer_response="denies"
        )
        actions_sub = self.engine.evaluate(assessment_sub)
        self.assertFalse(actions_sub.contains("FILE_REPORT"))
        self.assertFalse(actions_sub.sar_filed)

        # Above $1,000: MANDATORY SAR
        assessment_sup = CaseAssessment(
            probability=0.95,
            exposure_usd=1000.01,
            customer_response="denies"
        )
        actions_sup = self.engine.evaluate(assessment_sup)
        self.assertTrue(actions_sup.contains("FILE_REPORT"))
        self.assertTrue(actions_sup.sar_filed)
        sar_item = next(a for a in actions_sup if a.action == "FILE_REPORT")
        self.assertEqual(sar_item.route, "L2")
        self.assertIn("$1,000", sar_item.reason)

    def test_sar_shared_origin_overrides_exposure(self):
        # Exposure under $1,000, but shared device origin: MANDATORY SAR
        assessment = CaseAssessment(
            probability=0.95,
            exposure_usd=250.00,
            customer_response="denies",
            shared_origin="device"
        )
        actions = self.engine.evaluate(assessment)
        self.assertTrue(actions.contains("FILE_REPORT"))
        self.assertTrue(actions.contains("MONITOR_CONNECTED_CARDS"))
        sar_item = next(a for a in actions if a.action == "FILE_REPORT")
        self.assertIn("device", sar_item.reason)

    def test_sar_undocumented_pattern_overrides_exposure(self):
        # Exposure under $1,000, but undocumented pattern: MANDATORY SAR
        assessment = CaseAssessment(
            probability=0.95,
            pattern="undocumented",
            exposure_usd=140.00,
            customer_response="denies"
        )
        actions = self.engine.evaluate(assessment)
        self.assertTrue(actions.contains("FILE_REPORT"))
        sar_item = next(a for a in actions if a.action == "FILE_REPORT")
        self.assertIn("R9", sar_item.reason)


class TestPrecedenceRules(unittest.TestCase):
    """Verify strict precedence enforcement (R7 over R2, R1 gating, R10 gating, R8)."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_precedence_r7_checked_before_r2_on_recurring_dispute(self):
        # Customer denies charge ($45.00 gym subscription), but it matches recurring pattern
        assessment = CaseAssessment(
            probability=0.85,
            exposure_usd=45.00,
            customer_response="denies",
            recurring_match=True
        )
        actions = self.engine.evaluate(assessment)

        # R7 MUST hold: CREATE_CASE, VERIFY_WITH_CUSTOMER, WARN_CUSTOMER
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("VERIFY_WITH_CUSTOMER"))
        self.assertTrue(actions.contains("WARN_CUSTOMER"))

        # MUST NOT block card (R7 explicitly commands: 'Do not block')
        self.assertFalse(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("BLOCK_ALL_CARDS"))
        self.assertFalse(actions.contains("FILE_REPORT"))

        # Verify reason cites Rule R7
        warn_item = next(a for a in actions if a.action == "WARN_CUSTOMER")
        self.assertIn("R7", warn_item.reason)

    def test_precedence_r1_gates_blocking_on_weak_signal(self):
        # Risk score 0.85 alone, probability 0.55 (< 0.70), customer_response "none"
        assessment = CaseAssessment(
            probability=0.55,
            exposure_usd=450.00,
            customer_response="none",
            single_signal=True
        )
        actions = self.engine.evaluate(assessment)

        # R1 MUST gate: BLOCK_CARD and BLOCK_ALL_CARDS strictly prohibited
        self.assertFalse(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("BLOCK_ALL_CARDS"))

        # MUST recommend STEP_UP_AUTH and VERIFY_WITH_CUSTOMER
        self.assertTrue(actions.contains("STEP_UP_AUTH"))
        self.assertTrue(actions.contains("VERIFY_WITH_CUSTOMER"))
        self.assertTrue(actions.contains("CREATE_CASE"))

        v_item = next(a for a in actions if a.action == "VERIFY_WITH_CUSTOMER")
        self.assertIn("R1", v_item.reason)

    def test_precedence_r10_gates_block_all_cards(self):
        # Single card confirmed fraud (cards_confirmed_fraud_count = 1, credentials_compromised = False)
        assessment_single = CaseAssessment(
            probability=0.95,
            exposure_usd=800.00,
            customer_response="denies",
            cards_confirmed_fraud_count=1,
            credentials_compromised=False
        )
        actions_single = self.engine.evaluate(assessment_single)
        self.assertTrue(actions_single.contains("BLOCK_CARD"))
        # R10 strictly forbids BLOCK_ALL_CARDS
        self.assertFalse(actions_single.contains("BLOCK_ALL_CARDS"))

        # Multiple cards confirmed fraud (cards_confirmed_fraud_count = 2)
        assessment_multi = CaseAssessment(
            probability=0.95,
            exposure_usd=1800.00,
            customer_response="denies",
            cards_confirmed_fraud_count=2,
            credentials_compromised=False
        )
        actions_multi = self.engine.evaluate(assessment_multi)
        self.assertTrue(actions_multi.contains("BLOCK_ALL_CARDS"))
        b_all = next(a for a in actions_multi if a.action == "BLOCK_ALL_CARDS")
        self.assertEqual(b_all.route, "L2")
        self.assertIn("R10", b_all.reason)

        # Credential compromise detected (credentials_compromised = True)
        assessment_cred = CaseAssessment(
            probability=0.95,
            exposure_usd=500.00,
            customer_response="denies",
            cards_confirmed_fraud_count=1,
            credentials_compromised=True
        )
        actions_cred = self.engine.evaluate(assessment_cred)
        self.assertTrue(actions_cred.contains("BLOCK_ALL_CARDS"))

    def test_precedence_r8_escalates_on_uncertainty_and_exposure(self):
        # Uncertain probability (0.50) + exposure > $500 ($750)
        assessment_exp = CaseAssessment(
            probability=0.50,
            exposure_usd=750.00,
            customer_response="none"
        )
        actions_exp = self.engine.evaluate(assessment_exp)
        self.assertTrue(actions_exp.contains("ESCALATE_TO_ANALYST"))
        e_item = next(a for a in actions_exp if a.action == "ESCALATE_TO_ANALYST")
        self.assertIn("R8", e_item.reason)

        # Conflicting evidence
        assessment_conf = CaseAssessment(
            probability=0.45,
            exposure_usd=200.00,
            evidence_conflict=True,
            customer_response="none"
        )
        actions_conf = self.engine.evaluate(assessment_conf)
        self.assertTrue(actions_conf.contains("ESCALATE_TO_ANALYST"))

    def test_precedence_r3_customer_confirms(self):
        # Customer confirms transaction as authorized
        assessment = CaseAssessment(
            probability=0.60,
            exposure_usd=49.00,
            customer_response="confirms"
        )
        actions = self.engine.evaluate(assessment)
        self.assertTrue(actions.contains("CLOSE_NO_FRAUD"))
        self.assertFalse(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))
        c_item = next(a for a in actions if a.action == "CLOSE_NO_FRAUD")
        self.assertEqual(c_item.route, "auto")
        self.assertIn("R3", c_item.reason)

    def test_precedence_r4_customer_no_reply_24h(self):
        # Exposure under $500: MONITOR_CARD and DECLINE_TRANSACTION
        assessment_low = CaseAssessment(
            probability=0.55,
            exposure_usd=300.00,
            customer_response="no_reply"
        )
        actions_low = self.engine.evaluate(assessment_low)
        self.assertTrue(actions_low.contains("MONITOR_CARD"))
        self.assertTrue(actions_low.contains("DECLINE_TRANSACTION"))
        self.assertFalse(actions_low.contains("ESCALATE_TO_ANALYST"))
        d_item = next(a for a in actions_low if a.action == "DECLINE_TRANSACTION")
        self.assertEqual(d_item.route, "L1")

        # Exposure over $500: ESCALATE_TO_ANALYST
        assessment_high = CaseAssessment(
            probability=0.55,
            exposure_usd=850.00,
            customer_response="no_reply"
        )
        actions_high = self.engine.evaluate(assessment_high)
        self.assertTrue(actions_high.contains("ESCALATE_TO_ANALYST"))

    def test_precedence_r5_card_testing(self):
        # Card testing micro probes without cleared > $100
        assessment_probe = CaseAssessment(
            probability=0.85,
            pattern="card_testing",
            exposure_usd=12.00,
            has_cleared_over_100=False,
            customer_response="none"
        )
        actions_probe = self.engine.evaluate(assessment_probe)
        self.assertTrue(actions_probe.contains("DECLINE_TRANSACTION"))
        self.assertTrue(actions_probe.contains("STEP_UP_AUTH"))
        self.assertFalse(actions_probe.contains("BLOCK_CARD"))

        # Card testing with cleared purchase > $100
        assessment_cleared = CaseAssessment(
            probability=0.95,
            pattern="card_testing",
            exposure_usd=350.00,
            has_cleared_over_100=True,
            customer_response="none"
        )
        actions_cleared = self.engine.evaluate(assessment_cleared)
        self.assertTrue(actions_cleared.contains("DECLINE_TRANSACTION"))
        self.assertTrue(actions_cleared.contains("BLOCK_CARD"))

    def test_precedence_r6_shared_origin_typologies(self):
        for origin in ("device", "region", "email"):
            assessment = CaseAssessment(
                probability=0.90,
                exposure_usd=400.00,
                customer_response="denies",
                shared_origin=origin
            )
            actions = self.engine.evaluate(assessment)
            self.assertTrue(actions.contains("MONITOR_CONNECTED_CARDS"))
            self.assertTrue(actions.contains("FILE_REPORT"))
            m_item = next(a for a in actions if a.action == "MONITOR_CONNECTED_CARDS")
            self.assertIn("R6", m_item.reason)

    def test_precedence_r9_undocumented_abuse(self):
        assessment = CaseAssessment(
            probability=0.95,
            pattern="undocumented",
            exposure_usd=500.00,
            customer_response="denies"
        )
        actions = self.engine.evaluate(assessment)
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertTrue(actions.contains("FILE_REPORT"))
        self.assertTrue(actions.contains("ESCALATE_TO_ANALYST"))
        e_item = next(a for a in actions if a.action == "ESCALATE_TO_ANALYST")
        self.assertIn("R9", e_item.reason)


class TestRealClosedCasesRegressionSuite(unittest.TestCase):
    """
    Derives >= 25 realistic scenarios directly from REAL closed cases in closed_cases_history.csv
    and verifies the policy engine reproduces the bank's actual actions_taken and report_filed.
    """

    def setUp(self):
        self.engine = PolicyEngine()

    def test_scenario_01_cc_0001_cnp_fraud_sub_1000(self):
        # CC-0001: exposure $155.43, CNP fraud, confirmed_fraud, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="card_not_present_fraud", exposure_usd=155.43, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))
        self.assertEqual(get_action_route("BLOCK_CARD", 155.43), "L1")

    def test_scenario_02_cc_0002_out_of_region_sub_1000(self):
        # CC-0002: exposure $117.05, out_of_region_use, confirmed_fraud, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.98, pattern="out_of_region_use", exposure_usd=117.05, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_03_cc_0003_cleared_legitimate(self):
        # CC-0003: exposure $0.0, cleared, customer confirmed, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.10, pattern="none", exposure_usd=0.0, customer_response="confirms"
        ))
        self.assertTrue(actions.contains("CLOSE_NO_FRAUD"))
        self.assertFalse(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_04_cc_0004_out_of_region_high_sub_1000(self):
        # CC-0004: exposure $857.92, out_of_region_use, confirmed_fraud, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="out_of_region_use", exposure_usd=857.92, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_05_cc_0005_out_of_region_micro(self):
        # CC-0005: exposure $39.92, out_of_region_use, confirmed_fraud, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.95, pattern="out_of_region_use", exposure_usd=39.92, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_06_cc_0006_out_of_region(self):
        # CC-0006: exposure $265.07, out_of_region_use, confirmed_fraud, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.97, pattern="out_of_region_use", exposure_usd=265.07, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_07_cc_0008_ato_sub_1000(self):
        # CC-0008: exposure $879.46, account_takeover, confirmed_fraud, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.98, pattern="account_takeover", exposure_usd=879.46, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_08_cc_0009_cleared(self):
        # CC-0009: exposure $0.0, cleared, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.12, pattern="none", exposure_usd=0.0, customer_response="confirms"
        ))
        self.assertTrue(actions.contains("CLOSE_NO_FRAUD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_09_cc_0010_cleared(self):
        # CC-0010: exposure $0.0, cleared, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.08, pattern="none", exposure_usd=0.0, customer_response="confirms"
        ))
        self.assertTrue(actions.contains("CLOSE_NO_FRAUD"))

    def test_scenario_10_cc_0011_cnp_new_device_sub_1000(self):
        # CC-0011: exposure $750.32, card_not_present_new_device, confirmed_fraud, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="card_not_present_new_device", exposure_usd=750.32, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_11_cc_0015_cleared(self):
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.14, pattern="none", exposure_usd=0.0, customer_response="confirms"
        ))
        self.assertTrue(actions.contains("CLOSE_NO_FRAUD"))

    def test_scenario_12_cc_0017_cleared(self):
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.05, pattern="none", exposure_usd=0.0, customer_response="confirms"
        ))
        self.assertTrue(actions.contains("CLOSE_NO_FRAUD"))

    def test_scenario_13_cc_0024_ato_over_1000_sar(self):
        # CC-0024: exposure $1,894.06, account_takeover, confirmed_fraud, report_filed: Yes
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="account_takeover", exposure_usd=1894.06, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertTrue(actions.contains("FILE_REPORT"))
        self.assertEqual(get_action_route("BLOCK_CARD", 1894.06), "L1")
        self.assertEqual(get_action_route("FILE_REPORT"), "L2")

    def test_scenario_14_cc_0045_out_of_region_over_1000_sar(self):
        # CC-0045: exposure $1,282.82, out_of_region_use, confirmed_fraud, report_filed: Yes
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="out_of_region_use", exposure_usd=1282.82, customer_response="denies"
        ))
        self.assertTrue(actions.contains("FILE_REPORT"))

    def test_scenario_15_cc_0063_ato_high_exposure_over_2500_l2_block(self):
        # CC-0063: exposure $2,659.62 > $2,500, account_takeover, confirmed_fraud, report_filed: Yes
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="account_takeover", exposure_usd=2659.62, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertTrue(actions.contains("FILE_REPORT"))
        # Must require L2 approval for BLOCK_CARD (> $2,500)
        block_item = next(a for a in actions if a.action == "BLOCK_CARD")
        self.assertEqual(block_item.route, "L2")

    def test_scenario_16_cc_0118_ato_high_exposure_over_2500(self):
        # CC-0118: exposure $3,205.87 > $2,500
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="account_takeover", exposure_usd=3205.87, customer_response="denies"
        ))
        block_item = next(a for a in actions if a.action == "BLOCK_CARD")
        self.assertEqual(block_item.route, "L2")
        self.assertTrue(actions.contains("FILE_REPORT"))

    def test_scenario_17_cc_0121_ato_over_1000(self):
        # CC-0121: exposure $1,551.06
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="account_takeover", exposure_usd=1551.06, customer_response="denies"
        ))
        self.assertTrue(actions.contains("FILE_REPORT"))
        block_item = next(a for a in actions if a.action == "BLOCK_CARD")
        self.assertEqual(block_item.route, "L1")

    def test_scenario_18_cc_0122_cnp_new_device_over_1000(self):
        # CC-0122: exposure $1,656.00
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="card_not_present_new_device", exposure_usd=1656.00, customer_response="denies"
        ))
        self.assertTrue(actions.contains("FILE_REPORT"))

    def test_scenario_19_cc_0124_out_of_region_over_1000(self):
        # CC-0124: exposure $1,256.51
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="out_of_region_use", exposure_usd=1256.51, customer_response="denies"
        ))
        self.assertTrue(actions.contains("FILE_REPORT"))

    def test_scenario_20_cc_0137_card_testing_sub_1000(self):
        # CC-0137: exposure $600.00, card_testing, report_filed: No
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="card_testing", exposure_usd=600.00, customer_response="denies"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertFalse(actions.contains("FILE_REPORT"))

    def test_scenario_21_cc_0153_ato_exposure_10000(self):
        # CC-0153: exposure $10,081.08 > $2,500
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="account_takeover", exposure_usd=10081.08, customer_response="denies"
        ))
        block_item = next(a for a in actions if a.action == "BLOCK_CARD")
        self.assertEqual(block_item.route, "L2")
        self.assertTrue(actions.contains("FILE_REPORT"))

    def test_scenario_22_cc_0381_ato_exposure_5675(self):
        # CC-0381: exposure $5,675.86
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="account_takeover", exposure_usd=5675.86, customer_response="denies"
        ))
        block_item = next(a for a in actions if a.action == "BLOCK_CARD")
        self.assertEqual(block_item.route, "L2")

    def test_scenario_23_cc_0452_ato_exposure_3476(self):
        # CC-0452: exposure $3,476.23
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="account_takeover", exposure_usd=3476.23, customer_response="denies"
        ))
        block_item = next(a for a in actions if a.action == "BLOCK_CARD")
        self.assertEqual(block_item.route, "L2")

    def test_scenario_24_cc_2649_undocumented_sub_1000_sar(self):
        # CC-2649: exposure $390.04 (< $1,000), undocumented with connected card ring, report_filed: Yes
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="undocumented", exposure_usd=390.04, customer_response="denies",
            connected_cards_count=5, shared_origin="device"
        ))
        self.assertTrue(actions.contains("CREATE_CASE"))
        self.assertTrue(actions.contains("BLOCK_CARD"))
        self.assertTrue(actions.contains("FILE_REPORT"))
        self.assertTrue(actions.contains("MONITOR_CONNECTED_CARDS"))

    def test_scenario_25_cc_2971_undocumented_sub_1000_sar(self):
        # CC-2971: exposure $108.36 (< $1,000), undocumented, report_filed: Yes
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="undocumented", exposure_usd=108.36, customer_response="denies",
            connected_cards_count=4, shared_origin="device"
        ))
        self.assertTrue(actions.contains("FILE_REPORT"))

    def test_scenario_26_cc_2985_undocumented_sub_1000_sar(self):
        # CC-2985: exposure $381.40 (< $1,000), undocumented, report_filed: Yes
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="undocumented", exposure_usd=381.40, customer_response="denies",
            connected_cards_count=4, shared_origin="device"
        ))
        self.assertTrue(actions.contains("FILE_REPORT"))

    def test_scenario_27_cc_3035_undocumented_sub_1000_sar(self):
        # CC-3035: exposure $140.95 (< $1,000), undocumented, report_filed: Yes
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="undocumented", exposure_usd=140.95, customer_response="denies",
            connected_cards_count=4, shared_origin="device"
        ))
        self.assertTrue(actions.contains("FILE_REPORT"))

    def test_scenario_28_cc_3748_undocumented_over_1000_sar(self):
        # CC-3748: exposure $1,905.21 (> $1,000), undocumented, report_filed: Yes
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99, pattern="undocumented", exposure_usd=1905.21, customer_response="denies",
            connected_cards_count=3, shared_origin="device"
        ))
        self.assertTrue(actions.contains("FILE_REPORT"))


class TestChronologicalActionOrdering(unittest.TestCase):
    """Verify that ActionList orders actions chronologically by what happens first."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_ordering_confirmed_fraud_sar(self):
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.99,
            exposure_usd=1500.00,
            customer_response="denies",
            shared_origin="device"
        ))
        action_names = [a.action for a in actions]
        # In-flight controls -> Case creation -> Block card -> Monitor ring -> File SAR
        self.assertEqual(action_names, [
            "CREATE_CASE",
            "BLOCK_CARD",
            "MONITOR_CONNECTED_CARDS",
            "FILE_REPORT"
        ])

    def test_ordering_recurring_dispute(self):
        actions = self.engine.evaluate(CaseAssessment(
            probability=0.85,
            exposure_usd=60.00,
            customer_response="denies",
            recurring_match=True
        ))
        action_names = [a.action for a in actions]
        # Verify -> Warn -> Create Case
        self.assertEqual(action_names, [
            "VERIFY_WITH_CUSTOMER",
            "WARN_CUSTOMER",
            "CREATE_CASE"
        ])


if __name__ == "__main__":
    unittest.main(verbosity=2)
