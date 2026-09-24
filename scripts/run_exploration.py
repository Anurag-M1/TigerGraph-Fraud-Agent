#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Innovation: Autonomous Exploration Pipeline over Nov-Dec Risk Scores
=============================================================================
Runs the autonomous LangGraph fraud investigation agent over un-alerted Nov-Dec
transactions exceeding risk thresholds, deduplicated by card and device profile.
Emits schema-compliant answer files to exploration/<case_id>.json.
=============================================================================
"""

import sys
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.graph_agent import FraudInvestigationAgent
from src.reporting.validate import validate_case_dict

EXPLORATION_DIR = PROJECT_ROOT / "exploration"
EXPLORATION_DIR.mkdir(parents=True, exist_ok=True)
CASE_PACK_CSV = PROJECT_ROOT / "Dataset" / "case_pack.csv"
DB_PATH = PROJECT_ROOT / "gsql" / "graph_data" / "fraud_graph.db"


def fetch_candidate_exploration_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """Query novel Nov-Dec candidate transactions, deduplicating by card and device."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    df_pack = pd.read_csv(CASE_PACK_CSV)
    pack_txns = set(df_pack["flagged_txn_id"].astype(str))
    pack_cards = set(df_pack["card_id"])

    # Query high-risk Nov-Dec transactions
    c.execute('''
        SELECT t.id, t.card_id, c.customer_id, t.TransactionAmt, t.ts, t.channel, t.risk_score, t.addr1
        FROM TransactionVertex t
        JOIN Edge_OWNS o ON t.card_id = o.to_id
        JOIN Customer c ON o.from_id = c.id
        WHERE t.ts >= '2016-11-01' AND t.risk_score >= 0.70
        ORDER BY t.risk_score DESC, t.TransactionAmt DESC
    ''')
    rows = c.fetchall()

    seen_cards = set(pack_cards)
    seen_devices = set()
    candidates = []

    for r in rows:
        tid, card_id, cust_id, amt, ts, ch, risk, addr = r
        if tid in pack_txns or card_id in seen_cards:
            continue

        # Check device
        c.execute('''
            SELECT d.id FROM Edge_FROM_DEVICE e
            JOIN DeviceProfile d ON e.to_id = d.id
            WHERE e.from_id = ?
        ''', (tid,))
        dev_row = c.fetchone()
        dev_id = dev_row[0] if dev_row else f"offline_{addr}"

        if dev_id in seen_devices:
            continue

        seen_cards.add(card_id)
        seen_devices.add(dev_id)

        case_idx = len(candidates) + 1
        candidates.append({
            "case_id": f"EXP-{case_idx:03d}",
            "opened_at": ts,
            "trigger_type": "risk_score",
            "trigger_text": f"Autonomous discovery: model scored transaction {tid} (${amt:.2f}, {ch}) at {risk:.2f}.",
            "flagged_txn_id": str(tid),
            "card_id": card_id,
            "customer_id": cust_id,
            "risk_score": float(risk)
        })

        if len(candidates) >= limit:
            break

    conn.close()
    return candidates


def run_exploration():
    """Execute autonomous exploration across candidate alerts."""
    print("=" * 80)
    print("  AUTONOMOUS EXPLORATION PIPELINE: NOV-DEC RISK SCORE SWEEP")
    print("=" * 80)

    candidates = fetch_candidate_exploration_alerts(limit=8)
    print(f"Discovered {len(candidates)} novel, deduplicated candidate transactions from Nov-Dec.")

    agent = FraudInvestigationAgent()
    results = []

    for c in candidates:
        case_id = c["case_id"]
        print(f"\n[Exploration] Investigating {case_id} (Card: {c['card_id']}, Txn: {c['flagged_txn_id']}, Risk: {c['risk_score']})...")
        t0 = time.time()
        answer = agent.run(c)
        elapsed = time.time() - t0

        # Validate answer file format
        is_valid, errors = validate_case_dict(answer, check_db=True)
        status_str = "VALID" if is_valid else f"INVALID: {errors}"

        # Save to exploration/
        out_file = EXPLORATION_DIR / f"{case_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(answer, f, indent=2)

        print(f"[Exploration] Saved {out_file} ({elapsed:.2f}s, Verdict: {answer['case']['verdict']}, Format: {status_str})")
        results.append(answer)

    fraud_n = sum(1 for r in results if r["case"]["verdict"] == "fraud")
    legit_n = sum(1 for r in results if r["case"]["verdict"] == "legitimate")
    uncertain_n = sum(1 for r in results if r["case"]["verdict"] == "uncertain")
    total_exp = sum(r["case"]["exposure_usd"] for r in results)

    print("\n" + "=" * 80)
    print("  EXPLORATION BATCH COMPLETE")
    print(f"  Total Processed:    {len(results)}")
    print(f"  Legitimate:         {legit_n}")
    print(f"  Fraud:              {fraud_n}")
    print(f"  Uncertain:          {uncertain_n}")
    print(f"  Total Exposure:     ${total_exp:.2f}")
    print(f"  Output Directory:   {EXPLORATION_DIR}/")
    print("=" * 80)


if __name__ == "__main__":
    run_exploration()
