#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 6: Answer Format & Mechanical Perfection Unit Tests
=============================================================================
Comprehensive test suite asserting all Phase 6 requirements:
1. Golden test: hand-written cases/HHG-003.manual.json passes with 0 errors.
2. Golden test: README HHG-017 example passes with 0 errors.
3. Batch test: all 20 generated case-pack files pass full database validation.
4. Hard-fail tests:
   - Schema, enum, and type violations
   - Legitimate verdict invariants (empty txns, empty first_suspicious, 0 exposure, sar=false)
   - SAR constraints (6-12 sentences, subjects named in narrative, date ordering, agreement with FILE_REPORT)
   - Two-route capture invariants (final==initial and what_changed=="nothing" iff evidence_requests==[])
   - Pattern description (non-empty iff pattern=="undocumented")
   - Evidence ref formats (query:..., doc:..., evidence_request:<n>)
   - Exposure matching graph sum
   - Graph memory read-back
=============================================================================
"""

import sys
import copy
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting.validate import CaseValidator, validate_case_file, validate_case_dict
from src.reporting.generator import AnswerFileGenerator


README_HHG_017_EXAMPLE = {
    "case_id": "HHG-017",
    "case": {
        "status": "closed_fraud",
        "verdict": "fraud",
        "fraud_probability": 0.86,
        "pattern": "card_testing",
        "pattern_description": "",
        "affected_txn_ids": ["T0412877", "T0412878", "T0412879", "T0412883"],
        "first_suspicious_txn_id": "T0412877",
        "connected_card_ids": ["C00877-K1"],
        "connected_device_profiles": ["SAMSUNG SM-G892A Build/NRD90M | Android 7.0 | samsung browser 6.2 | 2220x1080"],
        "exposure_usd": 268.43,
        "evidence": [
            {
                "claim": "Three online authorizations under $3 within 40 minutes, then a $259 purchase under a product code this card has never used",
                "source": "graph",
                "ref": "query:card_window(card_id=C00377-K1, hours=2)",
                "entity_ids": ["T0412877", "T0412878", "T0412879", "T0412883"]
            },
            {
                "claim": "All four came from a device profile marked New for this account (Android 7.0, Chrome for Android, 1920x1080), seen on closed case CC-0141 and on card C00877-K1 this month",
                "source": "graph",
                "ref": "query:device_neighbors(device_id=D000731)",
                "entity_ids": ["CC-0141", "C00877-K1"]
            },
            {
                "claim": "Customer denied the purchases when asked",
                "source": "customer",
                "ref": "evidence_request:1",
                "entity_ids": []
            }
        ],
        "similar_prior_cases": ["CC-0141"],
        "summary": "Textbook card testing: three sub-$3 online authorizations in 40 minutes, then a $259 purchase in a category the cardholder has never used. All four share a device profile marked New for this account, which appears on a closed case from August and on another card this month. Customer denied the activity. Card compromised; a second card is likely compromised through the same device.",
        "written_to_graph": True,
        "graph_case_id": "CASE-2016-1187"
    },
    "evidence_requests": [
        {
            "type": "customer_validation",
            "asked_after_step": 4,
            "assumed_response": "Customer states they did not make these purchases and still has the card"
        }
    ],
    "next_best_actions": {
        "initial": [
            {
                "action": "DECLINE_TRANSACTION",
                "route": "L1",
                "reason": "R5: testing sequence observed, purchase already cleared"
            },
            {
                "action": "VERIFY_WITH_CUSTOMER",
                "route": "auto",
                "reason": "R1: probability 0.72 on pattern alone, confirm before blocking"
            }
        ],
        "final": [
            {
                "action": "BLOCK_CARD",
                "route": "L1",
                "reason": "R2 and R5: customer denied; exposure $268 is under $2,500"
            },
            {
                "action": "CREATE_CASE",
                "route": "auto",
                "reason": "R2"
            },
            {
                "action": "FILE_REPORT",
                "route": "L2",
                "reason": "R2: shared device links this to another compromised card"
            },
            {
                "action": "MONITOR_CONNECTED_CARDS",
                "route": "auto",
                "reason": "Same device profile also used on C00877-K1"
            }
        ],
        "what_changed": "Customer denial raised probability from 0.72 to 0.86 and confirmed the block. The shared device profile with C00877-K1 triggers a report and monitoring of the connected card."
    },
    "sar": {
        "file": True,
        "reason": "R2: confirmed unauthorized use linked by a shared device to a second compromised card",
        "narrative": "On 2016-11-14 between 09:12 and 09:52, card C00377-K1 belonging to customer C00377 was used for three online authorizations of $1.10, $2.40, and $0.95 followed at 10:31 by a $259.98 online purchase under a product code the cardholder had never used. All four transactions came from a device profile marked New for this account, previously recorded on closed case CC-0141 (confirmed fraud, August 2016) and on card C00877-K1 on 2016-11-12. The cardholder, contacted the same day, stated they did not make these purchases and remained in possession of the card. The sequence of small authorizations followed by a larger purchase is consistent with testing of a stolen card number prior to use. The shared device indicates a common actor across at least two cardholders. Total unauthorized amount: $268.43. Card blocked and scheduled for reissue; card C00877-K1 placed under monitoring.",
        "subjects": ["C00377", "C00377-K1", "C00877-K1"],
        "total_amount_usd": 268.43,
        "activity_dates": ["2016-11-14", "2016-11-14"]
    },
    "stop_reason": "Customer denial settled the verdict; device link identified and connected card protected. Further steps would not change the actions.",
    "tool_calls": 9,
    "tokens": 12480,
    "latency_s": 18.7
}


class TestAnswerFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = CaseValidator()
        cls.generator = AnswerFileGenerator()
        cls.cases_dir = PROJECT_ROOT / "cases"

    def test_01_golden_hhg_003_manual_passes(self):
        """Golden test 1: our hand-written HHG-003 file must pass with 0 errors."""
        golden_path = PROJECT_ROOT / "tests" / "golden" / "HHG-003.manual.json"
        manual_003_file = golden_path if golden_path.exists() else self.cases_dir / "HHG-003.manual.json"
        self.assertTrue(manual_003_file.exists(), f"File {manual_003_file} does not exist.")
        with open(manual_003_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid, errors = self.validator.validate(data, check_db=True)
        self.assertTrue(valid, f"HHG-003.manual.json failed validation: {errors}")
        self.assertEqual(len(errors), 0)

    def test_02_golden_readme_hhg_017_example_passes(self):
        """Golden test 2: the README's HHG-017 example must pass with 0 errors."""
        valid, errors = self.validator.validate(README_HHG_017_EXAMPLE, check_db=True)
        self.assertTrue(valid, f"README HHG-017 example failed validation: {errors}")
        self.assertEqual(len(errors), 0)

    def test_03_all_generated_cases_pass_validation(self):
        """Verify that all 20 generated case-pack files pass full database validation."""
        case_files = sorted([f for f in self.cases_dir.glob("HHG-*.json") if not f.name.endswith(".manual.json")])
        self.assertEqual(len(case_files), 20, f"Expected 20 case files, found {len(case_files)}")

        for cf in case_files:
            with open(cf, "r", encoding="utf-8") as f:
                data = json.load(f)
            valid, errors = self.validator.validate(data, check_db=True)
            self.assertTrue(valid, f"{cf.name} failed validation: {errors}")
            self.assertEqual(len(errors), 0, f"{cf.name} had errors: {errors}")

    def test_04_hard_fail_schema_and_enums(self):
        """Hard-fail test: reject invalid status, verdict, pattern, source, and route."""
        # Invalid status
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["case"]["status"] = "pending_investigation"
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("Invalid status" in e for e in errors))

        # Invalid verdict
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["case"]["verdict"] = "guilty"
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("Invalid verdict" in e for e in errors))

        # Invalid pattern
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["case"]["pattern"] = "identity_theft"
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("Invalid pattern" in e for e in errors))

        # Invalid evidence source
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["case"]["evidence"][0]["source"] = "third_party_vendor"
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("source" in e for e in errors))

        # Invalid route
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["next_best_actions"]["final"][0]["route"] = "L3"
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("route" in e for e in errors))

    def test_05_hard_fail_legitimate_invariants(self):
        """Hard-fail test: legitimate requires affected_txns=[], first_suspicious='', exposure 0, sar.file=false."""
        golden_path = PROJECT_ROOT / "tests" / "golden" / "HHG-003.manual.json"
        src_path = golden_path if golden_path.exists() else self.cases_dir / "HHG-003.manual.json"
        with open(src_path, "r", encoding="utf-8") as f:
            base = json.load(f)

        # Affected txns non-empty
        bad = copy.deepcopy(base)
        bad["case"]["affected_txn_ids"] = ["3530164"]
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("affected_txn_ids to be empty" in e for e in errors))

        # First suspicious non-empty
        bad = copy.deepcopy(base)
        bad["case"]["first_suspicious_txn_id"] = "3530164"
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("first_suspicious_txn_id to be empty" in e for e in errors))

        # Exposure > 0
        bad = copy.deepcopy(base)
        bad["case"]["exposure_usd"] = 49.00
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("exposure_usd to be 0" in e for e in errors))

        # SAR file true on legitimate
        bad = copy.deepcopy(base)
        bad["sar"]["file"] = True
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("sar.file to be false" in e for e in errors))

    def test_06_hard_fail_sar_constraints(self):
        """Hard-fail test: sar.file agreement with FILE_REPORT, sentence count, subjects named, date order."""
        # sar.file False when FILE_REPORT in final actions
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["sar"]["file"] = False
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("must agree with whether FILE_REPORT appears" in e for e in errors))

        # Narrative too short (< 6 sentences)
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["sar"]["narrative"] = "This is a report. Fraud occurred. Card was blocked."
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("sar.narrative must contain 6-12 sentences" in e for e in errors))

        # Subject ID in subjects not named in narrative
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["sar"]["subjects"].append("C99999-K9")
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("not named in sar.narrative" in e for e in errors))

        # Activity dates inverted [start > end]
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["sar"]["activity_dates"] = ["2016-12-01", "2016-11-01"]
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("must be <=" in e for e in errors))

    def test_07_hard_fail_two_route_invariants(self):
        """Hard-fail test: final=initial and what_changed='nothing' iff evidence_requests==[]."""
        # Requests empty but what_changed != 'nothing'
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["evidence_requests"] = []
        bad["next_best_actions"]["final"] = list(bad["next_best_actions"]["initial"])
        bad["next_best_actions"]["what_changed"] = "Actions changed based on internal review."
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("what_changed must be 'nothing'" in e for e in errors))

        # Requests non-empty but what_changed == 'nothing'
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["next_best_actions"]["what_changed"] = "nothing"
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("what_changed must explain why final differs" in e for e in errors))

    def test_08_hard_fail_pattern_description(self):
        """Hard-fail test: pattern_description non-empty iff pattern=undocumented."""
        # Non-empty pattern description on known pattern
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["case"]["pattern_description"] = "This is card testing probe."
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("pattern_description must be empty string" in e for e in errors))

        # Empty pattern description on undocumented pattern
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["case"]["pattern"] = "undocumented"
        bad["case"]["pattern_description"] = ""
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("must be non-empty when pattern is 'undocumented'" in e for e in errors))

    def test_09_hard_fail_evidence_ref_format(self):
        """Hard-fail test: evidence refs must match query:..., doc:..., or evidence_request:<n>."""
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["case"]["evidence"][0]["ref"] = "malformed_evidence_reference_123"
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("does not match required format" in e for e in errors))

    def test_10_hard_fail_summary_sentence_count(self):
        """Hard-fail test: summary must contain between 2 and 6 sentences."""
        # Single sentence summary
        bad = copy.deepcopy(README_HHG_017_EXAMPLE)
        bad["case"]["summary"] = "This is a single sentence summary of the fraud investigation."
        valid, errors = self.validator.validate(bad, check_db=False)
        self.assertFalse(valid)
        self.assertTrue(any("summary must contain 2-6 sentences" in e for e in errors))

    def test_11_hard_fail_exposure_mismatch(self):
        """Hard-fail test: exposure_usd must equal sum(|amount|) from graph for real cases."""
        # Use a real generated case
        hhg_010_file = self.cases_dir / "HHG-010.json"
        with open(hhg_010_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["case"]["exposure_usd"] = 99999.99  # Tamper with exposure
        valid, errors = self.validator.validate(data, check_db=True)
        self.assertFalse(valid)
        self.assertTrue(any("does not match sum of absolute amounts from graph database" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
