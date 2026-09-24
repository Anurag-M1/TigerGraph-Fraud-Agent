#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 5: Graph Memory Writer
=============================================================================
Persists completed case investigations into TigerGraph / SQLite graph memory:
1. Inserts or replaces InvestigationCase vertex
2. Inserts EvidenceItem vertices and links via Edge_REFERENCES_EVIDENCE
3. Links affected transactions via Edge_RAISED
4. Links similar prior ClosedCase records via Edge_SIMILAR_TO
5. Returns graph_case_id and sets written_to_graph = True
=============================================================================
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "gsql" / "graph_data" / "fraud_graph.db"


class GraphMemoryWriter:
    """Manages writing case investigation artifacts to persistent graph memory."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure necessary edge tables exist for full memory linkages."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Edge_SIMILAR_TO (
                from_id TEXT,
                to_id TEXT,
                PRIMARY KEY (from_id, to_id)
            )
        """)
        conn.commit()
        conn.close()

    def write_case_to_graph(
        self,
        case_id: str,
        status: str,
        verdict: str,
        fraud_probability: float,
        pattern: str,
        pattern_description: str,
        exposure_usd: float,
        summary: str,
        sar_filed: bool,
        sar_narrative: str,
        evidence_items: List[Dict[str, Any]],
        affected_txn_ids: List[str],
        similar_prior_cases: List[str]
    ) -> Dict[str, Any]:
        """Write complete investigation case memory into the graph database."""
        graph_case_id = f"CASE-{case_id}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # 1. Upsert InvestigationCase vertex
        cur.execute("""
            INSERT OR REPLACE INTO InvestigationCase (
                id, opened_at, status, verdict, fraud_probability,
                pattern, pattern_description, exposure_usd, summary,
                sar_filed, sar_narrative
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            graph_case_id, now_str, status, verdict, float(fraud_probability),
            pattern, pattern_description, float(exposure_usd), summary,
            1 if sar_filed else 0, sar_narrative
        ))

        # 2. Upsert EvidenceItem vertices & link references
        for idx, ev in enumerate(evidence_items, 1):
            ev_id = f"EV-{case_id}-{idx}"
            claim = ev.get("claim", "")
            source = ev.get("source", "graph")
            ref = ev.get("ref", "")

            cur.execute("""
                INSERT OR REPLACE INTO EvidenceItem (id, claim, source, ref)
                VALUES (?, ?, ?, ?)
            """, (ev_id, claim, source, ref))

            cur.execute("""
                INSERT OR IGNORE INTO Edge_REFERENCES_EVIDENCE (from_id, to_id)
                VALUES (?, ?)
            """, (graph_case_id, ev_id))

        # 3. Link affected transactions via Edge_RAISED
        for tid in affected_txn_ids:
            cur.execute("""
                INSERT OR IGNORE INTO Edge_RAISED (from_id, to_id)
                VALUES (?, ?)
            """, (graph_case_id, str(tid)))

        # 4. Link similar prior closed cases via Edge_SIMILAR_TO
        for cc_id in similar_prior_cases:
            cur.execute("""
                INSERT OR IGNORE INTO Edge_SIMILAR_TO (from_id, to_id)
                VALUES (?, ?)
            """, (graph_case_id, str(cc_id)))

        conn.commit()
        conn.close()

        return {
            "graph_case_id": graph_case_id,
            "written_to_graph": True,
            "evidence_count": len(evidence_items),
            "linked_txns_count": len(affected_txn_ids),
            "similar_cases_count": len(similar_prior_cases)
        }
