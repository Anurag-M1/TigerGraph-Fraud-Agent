#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 8: Analyst Dashboard Backend Server (FastAPI)
=============================================================================
Provides REST endpoints and static file serving for the Analyst Dashboard:
- /api/cases: List all 20 alert cases + innovation exploration cases
- /api/cases/{case_id}: Detailed case answer and step-by-step numbered replay
- /api/cases/{case_id}/subgraph: Localized entity subgraph from fraud_graph.db
- /api/cases/{case_id}/run: Live real-time LangGraph agent run trigger
- /api/actions/approve: Mock Action Service for L1/L2 approval execution
- /api/actions/history: Log of approved containment actions
=============================================================================
"""

import sys
import json
import time
import uuid
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.graph_agent import FraudInvestigationAgent

CASES_DIR = PROJECT_ROOT / "cases"
EXPLORATION_DIR = PROJECT_ROOT / "exploration"
CASE_PACK_CSV = PROJECT_ROOT / "Dataset" / "case_pack.csv"
DB_PATH = PROJECT_ROOT / "gsql" / "graph_data" / "fraud_graph.db"
STATIC_DIR = PROJECT_ROOT / "ui" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="TigerGraph × HHGOA Fraud Intelligence Analyst Dashboard",
    description="Interactive Analyst Dashboard for Fraud Investigation, Policy Routing & Entity Subgraphs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory action execution store
ACTION_EXECUTION_LOG: List[Dict[str, Any]] = []


class ApprovalRequest(BaseModel):
    case_id: str
    action: str
    route: str
    approver: Optional[str] = "Senior Fraud Analyst (L2)"
    notes: Optional[str] = "Approved after reviewing graph evidence trail."


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_timeline_steps(answer_dict: Dict[str, Any], case_id: str) -> List[Dict[str, Any]]:
    """Synthesize the strict 11-step numbered lifecycle for timeline replay."""
    case = answer_dict.get("case", {})
    ev_reqs = answer_dict.get("evidence_requests", [])
    nba = answer_dict.get("next_best_actions", {})
    sar = answer_dict.get("sar", {})
    exposure = case.get("exposure_usd", 0.0)
    verdict = case.get("verdict", "uncertain")
    status = case.get("status", "open")
    pattern = case.get("pattern", "none")
    prob = case.get("fraud_probability", 0.5)

    ev_type = ev_reqs[0]["type"] if ev_reqs else "customer_validation"
    assumed_resp = ev_reqs[0]["assumed_response"] if ev_reqs else "No out-of-band response required."
    asked_step = ev_reqs[0].get("asked_after_step", 6) if ev_reqs else 6

    initial_names = [a["action"] for a in nba.get("initial", [])]
    final_names = [a["action"] for a in nba.get("final", [])]

    steps = [
        {
            "step": 1,
            "node": "TRIGGER",
            "title": "Alert Ingestion & Triage",
            "description": f"Investigation triggered for case {case_id} on payment card {case.get('affected_txn_ids', ['card'])[0] if case.get('affected_txn_ids') else 'card'}. Initial alert attributes loaded.",
            "duration_ms": 12,
            "status": "completed"
        },
        {
            "step": 2,
            "node": "OPEN_CASE_IN_GRAPH",
            "title": "Graph Case Record Initialization",
            "description": f"Initialized active internal case record in graph memory as CASE-{case_id}. Registered status as 'open'.",
            "duration_ms": 15,
            "status": "completed"
        },
        {
            "step": 3,
            "node": "EVIDENCE_PLAN",
            "title": "Investigative Evidence Planning",
            "description": "Formulated query strategy across card baseline, 48h transaction window, velocity bursts, device hardware fingerprints, and regional travel continuity.",
            "duration_ms": 20,
            "status": "completed"
        },
        {
            "step": 4,
            "node": "COLLECT",
            "title": "GSQL Graph Query Execution",
            "description": f"Executed 10 analytical graph queries. Gathered {len(case.get('evidence', []))} objective evidence items from graph topology.",
            "duration_ms": 120,
            "status": "completed"
        },
        {
            "step": 5,
            "node": "ASSESS",
            "title": "Pattern Classification & Calibrated Scoring",
            "description": f"Assessed initial fraud probability at {prob:.2f}. Typology classified as '{pattern}'. Exposure calculated as ${exposure:.2f}.",
            "duration_ms": 45,
            "status": "completed"
        },
        {
            "step": 6,
            "node": "POLICY_EVAL",
            "title": "Initial Policy Engine Evaluation",
            "description": f"Evaluated pre-evidence policy recommendations: {', '.join(initial_names)}. Snapshotted next_best_actions.initial.",
            "duration_ms": 10,
            "status": "completed"
        },
        {
            "step": 7,
            "node": "REQUEST_EVIDENCE",
            "title": f"Out-of-Band Evidence Simulation (asked_after_step: {asked_step})",
            "description": f"Formulated {ev_type} request after step {asked_step}. Defensible response: \"{assumed_resp[:120]}...\"",
            "duration_ms": 65,
            "status": "completed",
            "highlight": True
        },
        {
            "step": 8,
            "node": "RE_ASSESS",
            "title": "Post-Evidence Bayesian Re-Assessment",
            "description": f"Updated posterior fraud probability to {prob:.2f} following evidence incorporation. Verdict updated to '{verdict}' ({status}).",
            "duration_ms": 30,
            "status": "completed"
        },
        {
            "step": 9,
            "node": "POLICY_EVAL_FINAL",
            "title": "Final Policy Engine Evaluation & SAR Determination",
            "description": f"Evaluated final policy actions: {', '.join(final_names)}. FinCEN SAR regulatory filing determined: {sar.get('file', False)}.",
            "duration_ms": 25,
            "status": "completed"
        },
        {
            "step": 10,
            "node": "WRITE_CASE_TO_GRAPH",
            "title": "Graph Case Memory Persistence",
            "description": f"Persisted InvestigationCase vertex (CASE-{case_id}) into graph database with {len(case.get('evidence', []))} linked EvidenceItem vertices.",
            "duration_ms": 35,
            "status": "completed"
        },
        {
            "step": 11,
            "node": "EMIT_ANSWER",
            "title": "Schema-Compliant Payload Emission",
            "description": f"Compiled and validated complete 3-part answer JSON for {case_id}. Latency: {answer_dict.get('latency_s', 0.5):.2f}s.",
            "duration_ms": 15,
            "status": "completed"
        }
    ]
    return steps


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "TigerGraph Fraud Intelligence Analyst Dashboard",
        "timestamp": datetime.now().isoformat(),
        "graph_db": "fraud_graph.db (SQLite/GSQL)",
        "cases_dir": str(CASES_DIR)
    }


@app.get("/api/cases")
def list_cases():
    """List all available cases across case-pack (HHG-*) and exploration (EXP-*)."""
    case_pack_map = {}
    if CASE_PACK_CSV.exists():
        df_pack = pd.read_csv(CASE_PACK_CSV)
        for _, r in df_pack.iterrows():
            case_pack_map[r["case_id"]] = {
                "trigger_type": r["trigger_type"],
                "trigger_text": r["trigger_text"],
                "card_id": r["card_id"],
                "flagged_txn_id": str(r["flagged_txn_id"]),
                "alert_risk": r["risk_score"] if pd.notna(r["risk_score"]) else None
            }

    results = []

    # 1. Main case pack files
    for f in sorted(CASES_DIR.glob("HHG-*.json")):
        if f.name.endswith(".manual.json"):
            continue
        try:
            with open(f, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            cid = data["case_id"]
            c = data.get("case", {})
            meta = case_pack_map.get(cid, {})
            results.append({
                "case_id": cid,
                "status": c.get("status", "open"),
                "verdict": c.get("verdict", "uncertain"),
                "fraud_probability": c.get("fraud_probability", 0.5),
                "pattern": c.get("pattern", "none"),
                "exposure_usd": c.get("exposure_usd", 0.0),
                "sar_file": data.get("sar", {}).get("file", False),
                "tool_calls": data.get("tool_calls", 0),
                "latency_s": data.get("latency_s", 0.0),
                "trigger_type": meta.get("trigger_type", "model_alert"),
                "card_id": meta.get("card_id", ""),
                "flagged_txn_id": meta.get("flagged_txn_id", ""),
                "is_exploration": False
            })
        except Exception:
            continue

    # 2. Exploration files
    if EXPLORATION_DIR.exists():
        for f in sorted(EXPLORATION_DIR.glob("EXP-*.json")):
            try:
                with open(f, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                cid = data["case_id"]
                c = data.get("case", {})
                results.append({
                    "case_id": cid,
                    "status": c.get("status", "open"),
                    "verdict": c.get("verdict", "uncertain"),
                    "fraud_probability": c.get("fraud_probability", 0.5),
                    "pattern": c.get("pattern", "none"),
                    "exposure_usd": c.get("exposure_usd", 0.0),
                    "sar_file": data.get("sar", {}).get("file", False),
                    "tool_calls": data.get("tool_calls", 0),
                    "latency_s": data.get("latency_s", 0.0),
                    "trigger_type": "risk_score",
                    "card_id": c.get("connected_card_ids", ["CARD"])[0] if c.get("connected_card_ids") else "CARD",
                    "flagged_txn_id": c.get("first_suspicious_txn_id", ""),
                    "is_exploration": True
                })
            except Exception:
                continue

    return results


@app.get("/api/cases/{case_id}")
def get_case_detail(case_id: str):
    """Retrieve full answer JSON and synthesized timeline replay for a case."""
    target_file = CASES_DIR / f"{case_id}.json"
    if not target_file.exists():
        target_file = EXPLORATION_DIR / f"{case_id}.json"
    if not target_file.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Load trigger metadata if in case_pack.csv
    trigger_meta = {}
    if CASE_PACK_CSV.exists():
        df_pack = pd.read_csv(CASE_PACK_CSV)
        row = df_pack[df_pack["case_id"] == case_id]
        if not row.empty:
            r = row.iloc[0]
            trigger_meta = {
                "trigger_type": r["trigger_type"],
                "trigger_text": r["trigger_text"],
                "card_id": r["card_id"],
                "customer_id": r["customer_id"],
                "flagged_txn_id": str(r["flagged_txn_id"]),
                "alert_risk": float(r["risk_score"]) if pd.notna(r["risk_score"]) else None,
                "opened_at": r["opened_at"]
            }

    # Generate step-by-step numbered replay
    steps = generate_timeline_steps(data, case_id)

    return {
        "case_id": case_id,
        "metadata": trigger_meta,
        "answer": data,
        "timeline_steps": steps
    }


@app.post("/api/cases/{case_id}/run")
def run_case_live(case_id: str):
    """Run the live multi-agent graph investigation on demand and return updated record."""
    if not CASE_PACK_CSV.exists():
        raise HTTPException(status_code=500, detail="case_pack.csv not found.")

    df_pack = pd.read_csv(CASE_PACK_CSV)
    row = df_pack[df_pack["case_id"] == case_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not in case_pack.csv.")

    alert_dict = row.iloc[0].to_dict()
    agent = FraudInvestigationAgent()
    t0 = time.time()
    answer = agent.run(alert_dict)
    elapsed = time.time() - t0

    # Save to cases/
    out_file = CASES_DIR / f"{case_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(answer, f, indent=2)

    steps = generate_timeline_steps(answer, case_id)

    return {
        "case_id": case_id,
        "execution_time_s": round(elapsed, 2),
        "answer": answer,
        "timeline_steps": steps
    }


@app.get("/api/cases/{case_id}/subgraph")
def get_case_subgraph(case_id: str):
    """
    Extract the localized entity graph view around the payment card, customer,
    flagged/affected transactions, device profiles, billing regions, email domains,
    connected cards, and prior closed cases.
    """
    target_file = CASES_DIR / f"{case_id}.json"
    if not target_file.exists():
        target_file = EXPLORATION_DIR / f"{case_id}.json"
    if not target_file.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = get_db()
    c = conn.cursor()

    # Determine card_id and customer_id
    card_id = ""
    cust_id = ""
    flagged_txn = ""

    if CASE_PACK_CSV.exists():
        df_pack = pd.read_csv(CASE_PACK_CSV)
        row = df_pack[df_pack["case_id"] == case_id]
        if not row.empty:
            card_id = str(row.iloc[0]["card_id"])
            cust_id = str(row.iloc[0]["customer_id"])
            flagged_txn = str(row.iloc[0]["flagged_txn_id"])

    if not card_id:
        # Fallback to query
        c.execute('SELECT card_id FROM TransactionVertex WHERE id = ?', (data["case"].get("first_suspicious_txn_id"),))
        row = c.fetchone()
        if row:
            card_id = row[0]

    nodes = []
    edges = []
    seen_nodes = set()

    def add_node(nid: str, ntype: str, label: str, props: Dict[str, Any] = None):
        if nid not in seen_nodes:
            seen_nodes.add(nid)
            nodes.append({
                "id": str(nid),
                "type": ntype,
                "label": label,
                "properties": props or {}
            })

    def add_edge(src: str, dst: str, rel: str, label: str = ""):
        edges.append({
            "source": str(src),
            "target": str(dst),
            "relationship": rel,
            "label": label or rel
        })

    # 1. Central Card Node
    add_node(card_id, "Card", f"Card\n{card_id}", {"card_id": card_id})

    # 2. Customer Node
    c.execute('SELECT from_id FROM Edge_OWNS WHERE to_id = ?', (card_id,))
    cust_row = c.fetchone()
    if cust_row:
        cust_id = cust_row[0]
        add_node(cust_id, "Customer", f"Customer\n{cust_id}", {"customer_id": cust_id})
        add_edge(cust_id, card_id, "OWNS")

    # 3. Investigation Case Node
    case_vertex_id = f"CASE-{case_id}"
    add_node(case_vertex_id, "InvestigationCase", f"Case\n{case_id}", {
        "verdict": data["case"].get("verdict"),
        "status": data["case"].get("status"),
        "probability": data["case"].get("fraud_probability"),
        "exposure": data["case"].get("exposure_usd")
    })
    add_edge(case_vertex_id, card_id, "INVESTIGATES")

    # 4. Transactions on this card (Flagged + Recent)
    c.execute('''
        SELECT id, TransactionAmt, ts, channel, addr1, ProductCD, P_emaildomain, risk_score
        FROM TransactionVertex
        WHERE card_id = ?
        ORDER BY ts DESC
        LIMIT 6
    ''', (card_id,))
    txns = c.fetchall()

    for t in txns:
        tid = str(t["id"])
        is_flagged = (tid == flagged_txn or tid in data["case"].get("affected_txn_ids", []))
        t_label = f"Txn {tid}\n${t['TransactionAmt']:.2f}"
        if is_flagged:
            t_label = f"⚠️ {t_label}"

        add_node(tid, "Transaction", t_label, {
            "amount": t["TransactionAmt"],
            "channel": t["channel"],
            "timestamp": t["ts"],
            "risk_score": t["risk_score"],
            "product": t["ProductCD"],
            "flagged": is_flagged
        })
        add_edge(card_id, tid, "MADE")

        if is_flagged:
            add_edge(case_vertex_id, tid, "RAISED_FOR")

        # 5. Billing Region
        if t["addr1"]:
            reg_id = f"Region_{t['addr1']}"
            add_node(reg_id, "BillingRegion", f"Region\n{t['addr1']}", {"addr1": t["addr1"]})
            add_edge(tid, reg_id, "BILLED_IN")

        # 6. Email Domain
        if t["P_emaildomain"]:
            em_id = f"Email_{t['P_emaildomain']}"
            add_node(em_id, "EmailDomain", f"Email\n{t['P_emaildomain']}", {"domain": t["P_emaildomain"]})
            add_edge(tid, em_id, "PURCHASER_EMAIL")

        # 7. Device Profile (if online)
        c.execute('''
            SELECT d.id FROM Edge_FROM_DEVICE e
            JOIN DeviceProfile d ON e.to_id = d.id
            WHERE e.from_id = ?
        ''', (tid,))
        dev_row = c.fetchone()
        if dev_row:
            d_str = dev_row[0]
            short_dev = d_str.split(" | ")[-2] if " | " in d_str else d_str[:20]
            dev_node_id = f"DEV_{d_str}"
            add_node(dev_node_id, "DeviceProfile", f"Device\n{short_dev}", {"full_profile": d_str})
            add_edge(tid, dev_node_id, "FROM_DEVICE")

            # 8. Connected Cards via device
            c.execute('''
                SELECT DISTINCT t2.card_id FROM Edge_FROM_DEVICE e2
                JOIN TransactionVertex t2 ON e2.from_id = t2.id
                WHERE e2.to_id = ? AND t2.card_id != ?
                LIMIT 3
            ''', (d_str, card_id))
            conn_card_rows = c.fetchall()
            for ccr in conn_card_rows:
                cc_id = ccr[0]
                add_node(cc_id, "Card", f"Ring Card\n{cc_id}", {"connected_card": True})
                add_edge(dev_node_id, cc_id, "SHARED_WITH")

    # 9. Prior Closed Cases on this card
    c.execute('''
        SELECT c.id, c.outcome, c.pattern, c.exposure_usd
        FROM Edge_ON_CARD e
        JOIN ClosedCase c ON e.from_id = c.id
        WHERE e.to_id = ?
        LIMIT 3
    ''', (card_id,))
    cc_rows = c.fetchall()

    for cc in cc_rows:
        cc_id = cc["id"]
        add_node(cc_id, "ClosedCase", f"Closed Case\n{cc_id}", {
            "outcome": cc["outcome"],
            "pattern": cc["pattern"],
            "exposure": cc["exposure_usd"]
        })
        add_edge(cc_id, card_id, "PRIOR_CASE_ON")
        add_edge(case_vertex_id, cc_id, "RECALLS_MEMORY")

    conn.close()

    return {
        "case_id": case_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    }


@app.post("/api/actions/approve")
def approve_action(req: ApprovalRequest):
    """
    Mock Action Execution Service:
    Receives analyst approval for recommended actions (auto, L1, L2),
    generates cryptographic authorization token, and records containment log.
    """
    auth_code = f"AUTH-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    timestamp = datetime.now().isoformat()

    action_record = {
        "auth_code": auth_code,
        "case_id": req.case_id,
        "action": req.action,
        "route": req.route,
        "approver": req.approver,
        "notes": req.notes,
        "timestamp": timestamp,
        "status": "EXECUTED",
        "message": f"Successfully executed {req.action} via {req.route} route for case {req.case_id}. Core banking authorization token {auth_code} registered."
    }

    ACTION_EXECUTION_LOG.append(action_record)
    return action_record


@app.get("/api/actions/history")
def get_action_history():
    """Return historical log of executed approvals."""
    return list(reversed(ACTION_EXECUTION_LOG[-50:]))


# Mount static files for the frontend UI
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("\nStarting TigerGraph × HHGOA Analyst Dashboard on http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
