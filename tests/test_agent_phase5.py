#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 5: Agent Loop, Evidence Simulation, and Instrumentation Unit & Integration Tests
=============================================================================
Tests:
1. Numbered Step Sequence & Step Log Integrity (asked_after_step traceability)
2. Two-Route Capture (next_best_actions.initial vs final + what_changed)
3. Defensible Evidence Simulator (customer_validation, step_up_auth, analyst_info)
4. GraphRAG Policy Retrieval & FinCEN Standalone SAR Narrative Generation (6-12 sentences)
5. Policy Section 6 Stop Criteria Enforcement & Rationale
6. Graph Memory Persistence (InvestigationCase & EvidenceItem in SQLite)
7. Performance Instrumentation (tool_calls, tokens, latency_s)
=============================================================================
"""

import sys
import unittest
import sqlite3
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.graph_agent import FraudInvestigationAgent
from src.agent.simulator import EvidenceSimulator
from src.agent.rag import GraphRAGService, SARNarrativeGenerator
from src.agent.graph_writer import GraphMemoryWriter
from src.agent.runner import run_case


class TestAgentPhase5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = FraudInvestigationAgent()
        cls.db_path = PROJECT_ROOT / "gsql" / "graph_data" / "fraud_graph.db"

    def test_01_numbered_step_sequence(self):
        """Verify the LangGraph execution follows the strict numbered step log sequence."""
        alert = {
            "case_id": "TEST-STEP-001",
            "opened_at": "2016-12-05 01:55:28",
            "trigger_type": "risk_score",
            "trigger_text": "Real-time model scored transaction 3514030 ($77.07) at 0.61.",
            "flagged_txn_id": "3514030",
            "card_id": "C12382-K1",
            "customer_id": "C12382",
            "risk_score": 0.61
        }
        initial_state = {
            "case_id": alert["case_id"],
            "opened_at": alert["opened_at"],
            "trigger_type": alert["trigger_type"],
            "trigger_text": alert["trigger_text"],
            "flagged_txn_id": alert["flagged_txn_id"],
            "card_id": alert["card_id"],
            "customer_id": alert["customer_id"],
            "risk_score": alert["risk_score"],
            "current_step": 0,
            "step_log": [],
            "round_count": 0,
            "need_more_evidence": False,
            "tool_calls": 0,
            "tokens": 0,
            "customer_response": "none"
        }
        final_state = self.agent.graph.invoke(initial_state)
        step_log = final_state["step_log"]
        self.assertGreaterEqual(len(step_log), 10)
        
        # Verify strict numbering 1, 2, 3...
        step_numbers = [entry["step"] for entry in step_log]
        self.assertEqual(step_numbers, list(range(1, len(step_log) + 1)))

        # Verify node progression
        node_names = [entry["node"] for entry in step_log]
        self.assertIn("TRIGGER", node_names)
        self.assertIn("OPEN_CASE_IN_GRAPH", node_names)
        self.assertIn("EVIDENCE_PLAN", node_names)
        self.assertIn("COLLECT", node_names)
        self.assertIn("ASSESS", node_names)
        self.assertIn("POLICY_EVAL", node_names)
        self.assertIn("REQUEST_EVIDENCE", node_names)
        self.assertIn("RE_ASSESS", node_names)
        self.assertIn("POLICY_EVAL_FINAL", node_names)
        self.assertIn("WRITE_CASE_TO_GRAPH", node_names)
        self.assertIn("EMIT_ANSWER", node_names)

    def test_02_two_route_capture_legitimate_closure(self):
        """Verify two-route capture on legitimate case (HHG-003): initial requires verification, final is CLOSE_NO_FRAUD."""
        res = run_case("HHG-003")
        self.assertEqual(res["case"]["status"], "closed_legitimate")
        self.assertEqual(res["case"]["verdict"], "legitimate")
        self.assertEqual(res["case"]["exposure_usd"], 0.0)

        nba = res["next_best_actions"]
        init_acts = [a["action"] for a in nba["initial"]]
        final_acts = [a["action"] for a in nba["final"]]

        self.assertIn("VERIFY_WITH_CUSTOMER", init_acts)
        self.assertEqual(final_acts, ["CLOSE_NO_FRAUD"])
        self.assertTrue(len(nba["what_changed"]) > 20)
        self.assertIn("Rule R3", nba["what_changed"])

        # Check evidence request
        reqs = res["evidence_requests"]
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0]["type"], "customer_validation")
        self.assertEqual(reqs[0]["asked_after_step"], 6)
        self.assertIn("Customer confirms", reqs[0]["assumed_response"])

    def test_03_two_route_capture_confirmed_fraud(self):
        """Verify two-route capture on high-exposure fraud case (HHG-010): escalates to containment + SAR."""
        res = run_case("HHG-010")
        self.assertEqual(res["case"]["status"], "closed_fraud")
        self.assertEqual(res["case"]["verdict"], "fraud")
        self.assertGreaterEqual(res["case"]["exposure_usd"], 1000.0)

        nba = res["next_best_actions"]
        final_acts = [a["action"] for a in nba["final"]]
        self.assertIn("BLOCK_CARD", final_acts)
        self.assertIn("FILE_REPORT", final_acts)

        # Check SAR
        sar = res["sar"]
        self.assertTrue(sar["file"])
        self.assertIn("1,000", sar["reason"])
        sentences = [s.strip() for s in re.split(r'\.\s+', sar["narrative"]) if s.strip()]
        self.assertGreaterEqual(len(sentences), 6)
        self.assertLessEqual(len(sentences), 12)
        self.assertIn("C10434", sar["subjects"])

    def test_04_analyst_request_evidence_simulation(self):
        """Verify analyst_request trigger (HHG-014) dispatches analyst_info evidence request."""
        res = run_case("HHG-014")
        reqs = res["evidence_requests"]
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0]["type"], "analyst_info")
        self.assertEqual(reqs[0]["asked_after_step"], 6)
        self.assertIn("analyst", reqs[0]["assumed_response"].lower())

    def test_05_fincen_sar_narrative_guidance_structure(self):
        """Verify SAR narrative satisfies FinCEN structure answering who/what/when/where/how/why."""
        generator = SARNarrativeGenerator()
        sar = generator.generate_sar(
            case_id="TEST-SAR-001",
            customer_id="C99999",
            card_id="C99999-K1",
            flagged_txn_id="9999999",
            opened_at="2016-12-01 12:00:00",
            pattern="card_not_present_fraud",
            exposure_usd=2500.50,
            affected_txns=["9999999"],
            connected_cards=["C99999-K2"],
            device_profiles=["Test Device Profile"],
            evidence_items=[{"claim": "Test claim", "source": "graph", "ref": "ref", "entity_ids": []}],
            shared_origin="device"
        )
        self.assertTrue(sar["file"])
        narrative = sar["narrative"]
        self.assertIn("C99999", narrative)  # Who
        self.assertIn("card-not-present", narrative.lower())  # What
        self.assertIn("2016-12-01", narrative)  # When
        self.assertIn("Test Device Profile", narrative)  # Where
        self.assertIn("2,500.50", narrative)  # Why
        sentences = [s.strip() for s in re.split(r'\.\s+', narrative) if s.strip()]
        self.assertGreaterEqual(len(sentences), 6)
        self.assertLessEqual(len(sentences), 12)

    def test_06_graph_memory_persistence(self):
        """Verify case vertex and evidence items are persisted to SQLite graph database."""
        res = run_case("HHG-003")
        self.assertTrue(res["case"]["written_to_graph"])
        graph_case_id = res["case"]["graph_case_id"]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status, verdict, exposure_usd FROM InvestigationCase WHERE id = ?", (graph_case_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row, f"Case {graph_case_id} not found in InvestigationCase table")
        self.assertEqual(row[0], "closed_legitimate")
        self.assertEqual(row[1], "legitimate")
        self.assertEqual(row[2], 0.0)

        # Check evidence edges
        cursor.execute("SELECT COUNT(*) FROM Edge_REFERENCES_EVIDENCE WHERE from_id = ?", (graph_case_id,))
        edge_count = cursor.fetchone()[0]
        self.assertGreaterEqual(edge_count, 1)
        conn.close()

    def test_07_instrumentation_metrics(self):
        """Verify wall-clock latency, tool call counters, and token usage are tracked."""
        res = run_case("HHG-001")
        self.assertGreater(res["tool_calls"], 0)
        self.assertGreaterEqual(res["tokens"], 0)
        self.assertGreater(res["latency_s"], 0.0)
        self.assertLess(res["latency_s"], 15.0)


if __name__ == "__main__":
    unittest.main()
