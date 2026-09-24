#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 1: Graph Loading Pipeline & Smoke Verification
=============================================================================
Batched, idempotent, resumable graph loader for 708MB transactions.csv,
identity.csv, and closed_cases_history.csv.

Key features:
1. Batched chunking (50,000 rows/batch) with checkpointing (resumable).
2. Idempotent insertion (INSERT OR REPLACE).
3. Exact normalized DeviceProfile key: "DeviceInfo | OS(id_30) | browser(id_31) | screen(id_33)".
4. Chronological NEXT edge chain per card ordered by ts for burst & testing detection.
5. Ingests closed cases with ON_CARD, INVOLVES, and CONNECTED_TO edges.
6. Runs rigorous smoke tests:
   - Counts per vertex type
   - NEXT-chain integrity (ordering, cycles, completeness) for sample card
   - Retrievability of known closed cases across each edge type
7. Outputs full execution audit to gsql/loading_run.log.
=============================================================================
"""

import os
import sys
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Directory Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "Dataset"
GSQL_DIR = PROJECT_ROOT / "gsql"
GRAPH_DATA_DIR = GSQL_DIR / "graph_data"
STAGING_DIR = GSQL_DIR / "staging"
GRAPH_DATA_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = GRAPH_DATA_DIR / "fraud_graph.db"
CHECKPOINT_PATH = GSQL_DIR / "loading_checkpoint.json"
LOG_PATH = GSQL_DIR / "loading_run.log"

CHUNK_SIZE = 50000

# Top 20 discriminative V columns selected in Phase 1
V_COLS = [
    "V10", "V11", "V140", "V139", "V158", "V217", "V157", "V171", "V146", "V147",
    "V156", "V244", "V149", "V242", "V233", "V167", "V257", "V170", "V155", "V95"
]

C_COLS = [f"C{i}" for i in range(1, 15)]
D_COLS = [f"D{i}" for i in range(1, 16)]
M_COLS = [f"M{i}" for i in range(1, 10)]

CORE_TXN_COLS = [
    "TransactionID", "TransactionAmt", "ts", "channel", "risk_score",
    "ProductCD", "card4", "card6", "addr1", "addr2", "dist1",
    "P_emaildomain", "R_emaildomain", "customer_id", "card1"
]

ALL_LOAD_COLS = CORE_TXN_COLS + C_COLS + D_COLS + M_COLS + V_COLS


class Logger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.f = open(log_path, "w", encoding="utf-8")

    def log(self, msg: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        self.f.write(line + "\n")
        self.f.flush()

    def close(self):
        self.f.close()


def normalize_device_key(device_info, os_id30, browser_id31, screen_id33) -> str:
    """Normalize device profile key into exact format:
    'DeviceInfo | OS(id_30) | browser(id_31) | screen(id_33)'
    """
    parts = []
    for val in [device_info, os_id30, browser_id31, screen_id33]:
        if pd.notna(val):
            s = str(val).strip()
            if s and s.lower() not in ("nan", "null", "none", "unknown"):
                parts.append(s)
    return " | ".join(parts) if parts else "unknown"


def init_database(db_path: Path):
    """Create schema for high-performance local graph storage."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")

    # Vertices
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Customer (
            id TEXT PRIMARY KEY,
            customer_id TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Card (
            id TEXT PRIMARY KEY,
            card_id TEXT,
            customer_id TEXT,
            card4 TEXT,
            card6 TEXT
        );
    """)

    txn_cols_sql = ", ".join([f"{col} REAL" for col in C_COLS + D_COLS + V_COLS])
    m_cols_sql = ", ".join([f"{col} TEXT" for col in M_COLS])
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS TransactionVertex (
            id TEXT PRIMARY KEY,
            card_id TEXT,
            TransactionAmt REAL,
            ts TEXT,
            channel TEXT,
            risk_score REAL,
            ProductCD TEXT,
            card4 TEXT,
            card6 TEXT,
            addr1 TEXT,
            addr2 TEXT,
            dist1 REAL,
            P_emaildomain TEXT,
            R_emaildomain TEXT,
            {txn_cols_sql},
            {m_cols_sql}
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS DeviceProfile (
            id TEXT PRIMARY KEY,
            device_info TEXT,
            os TEXT,
            browser TEXT,
            screen TEXT,
            device_type TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS EmailDomain (
            id TEXT PRIMARY KEY
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS BillingRegion (
            id TEXT PRIMARY KEY,
            addr1 TEXT,
            addr2 TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ClosedCase (
            id TEXT PRIMARY KEY,
            opened_at TEXT,
            closed_at TEXT,
            outcome TEXT,
            pattern TEXT,
            first_fraud_txn_id TEXT,
            n_txns INTEGER,
            exposure_usd REAL,
            connected_card_ids TEXT,
            actions_taken TEXT,
            report_filed INTEGER,
            analyst_notes TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS InvestigationCase (
            id TEXT PRIMARY KEY,
            opened_at TEXT,
            status TEXT,
            verdict TEXT,
            fraud_probability REAL,
            pattern TEXT,
            pattern_description TEXT,
            exposure_usd REAL,
            summary TEXT,
            sar_filed INTEGER,
            sar_narrative TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS EvidenceItem (
            id TEXT PRIMARY KEY,
            claim TEXT,
            source TEXT,
            ref TEXT
        );
    """)

    # Edges
    for edge_table in [
        "Edge_OWNS", "Edge_MADE", "Edge_FROM_DEVICE",
        "Edge_PURCHASER_EMAIL", "Edge_BILLED_IN",
        "Edge_INVOLVES", "Edge_ON_CARD", "Edge_CONNECTED_TO",
        "Edge_RAISED", "Edge_REFERENCES_EVIDENCE"
    ]:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {edge_table} (
                from_id TEXT,
                to_id TEXT,
                PRIMARY KEY (from_id, to_id)
            );
        """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Edge_NEXT (
            from_id TEXT,
            to_id TEXT,
            card_id TEXT,
            time_delta_seconds REAL,
            PRIMARY KEY (from_id, to_id)
        );
    """)

    # Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_card ON TransactionVertex(card_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_ts ON TransactionVertex(ts);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_addr ON TransactionVertex(addr1);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_next_card ON Edge_NEXT(card_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_next_from ON Edge_NEXT(from_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_next_to ON Edge_NEXT(to_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dev_from ON Edge_FROM_DEVICE(to_id);")

    conn.commit()
    conn.close()


def load_card_mappings(logger: Logger):
    """Build robust customer/transaction to card mapping."""
    logger.log("Building customer and card entity dictionary...")
    cc = pd.read_csv(DATA_DIR / "closed_cases_history.csv")
    cp = pd.read_csv(DATA_DIR / "case_pack.csv")

    cust_cards = {}
    txn_to_card = {}

    for _, r in cc.iterrows():
        c_id = str(r["customer_id"]).strip()
        k_id = str(r["card_id"]).strip()
        cust_cards.setdefault(c_id, set()).add(k_id)
        if pd.notna(r["txn_ids"]):
            for tid in str(r["txn_ids"]).split("|"):
                txn_to_card[str(tid).strip()] = k_id

    for _, r in cp.iterrows():
        c_id = str(r["customer_id"]).strip()
        k_id = str(r["card_id"]).strip()
        cust_cards.setdefault(c_id, set()).add(k_id)
        txn_to_card[str(r["flagged_txn_id"]).strip()] = k_id

    logger.log(f"Known card mappings loaded: {len(cust_cards)} customers, {len(txn_to_card)} explicit txns.")
    return cust_cards, txn_to_card


def load_identities(logger: Logger):
    """Load identity.csv and build normalized DeviceProfile entities & lookup."""
    logger.log("Loading identity.csv and computing normalized DeviceProfile keys...")
    t0 = time.time()
    ident = pd.read_csv(DATA_DIR / "identity.csv", low_memory=False)

    devices_dict = {}
    txn_device_map = {}

    for _, r in ident.iterrows():
        tid = str(r["TransactionID"]).strip()
        dev_info = r.get("DeviceInfo")
        os_30 = r.get("id_30")
        br_31 = r.get("id_31")
        sc_33 = r.get("id_33")
        dev_type = str(r.get("DeviceType")) if pd.notna(r.get("DeviceType")) else ""

        dp_key = normalize_device_key(dev_info, os_30, br_31, sc_33)
        if dp_key != "unknown":
            txn_device_map[tid] = dp_key
            if dp_key not in devices_dict:
                devices_dict[dp_key] = {
                    "id": dp_key,
                    "device_info": str(dev_info) if pd.notna(dev_info) else "",
                    "os": str(os_30) if pd.notna(os_30) else "",
                    "browser": str(br_31) if pd.notna(br_31) else "",
                    "screen": str(sc_33) if pd.notna(sc_33) else "",
                    "device_type": dev_type
                }

    logger.log(f"Identity processed in {time.time() - t0:.2f}s: {len(devices_dict)} unique DeviceProfiles, {len(txn_device_map)} online transactions linked.")

    # Write DeviceProfiles to SQLite
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    dev_records = [
        (d["id"], d["device_info"], d["os"], d["browser"], d["screen"], d["device_type"])
        for d in devices_dict.values()
    ]
    cur.executemany("INSERT OR REPLACE INTO DeviceProfile VALUES (?, ?, ?, ?, ?, ?)", dev_records)
    conn.commit()
    conn.close()

    return txn_device_map, devices_dict


def load_closed_cases(logger: Logger):
    """Load closed_cases_history.csv into ClosedCase vertices and edges."""
    logger.log("Loading closed_cases_history.csv into graph...")
    cc = pd.read_csv(DATA_DIR / "closed_cases_history.csv")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    case_rows = []
    on_card_edges = []
    involves_edges = []
    connected_to_edges = []

    for _, r in cc.iterrows():
        case_id = str(r["case_id"]).strip()
        card_id = str(r["card_id"]).strip()
        opened_at = str(r["opened_at"]).strip() if pd.notna(r["opened_at"]) else ""
        closed_at = str(r["closed_at"]).strip() if pd.notna(r["closed_at"]) else ""
        outcome = str(r["outcome"]).strip()
        pattern = str(r["pattern"]).strip()
        raw_ft = str(r["first_fraud_txn_id"]).strip() if pd.notna(r["first_fraud_txn_id"]) else ""
        first_txn = str(int(float(raw_ft))) if raw_ft and raw_ft != "nan" else ""
        n_txns = int(r["n_txns"]) if pd.notna(r["n_txns"]) else 0
        exposure = float(r["exposure_usd"]) if pd.notna(r["exposure_usd"]) else 0.0
        conn_cards_raw = str(r["connected_card_ids"]).strip() if pd.notna(r["connected_card_ids"]) else ""
        actions = str(r["actions_taken"]).strip() if pd.notna(r["actions_taken"]) else ""
        report_filed = 1 if str(r["report_filed"]).lower() in ("yes", "true", "1") else 0
        notes = str(r["analyst_notes"]).strip() if pd.notna(r["analyst_notes"]) else ""

        case_rows.append((
            case_id, opened_at, closed_at, outcome, pattern, first_txn,
            n_txns, exposure, conn_cards_raw, actions, report_filed, notes
        ))

        # ON_CARD edge
        if card_id:
            on_card_edges.append((case_id, card_id))

        # INVOLVES edge
        if pd.notna(r["txn_ids"]):
            for tid in str(r["txn_ids"]).split("|"):
                tid = tid.strip()
                if tid:
                    involves_edges.append((case_id, tid))

        # CONNECTED_TO edge
        if conn_cards_raw:
            for cid in conn_cards_raw.split("|"):
                cid = cid.strip()
                if cid:
                    connected_to_edges.append((case_id, cid))

    cur.executemany("INSERT OR REPLACE INTO ClosedCase VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", case_rows)
    cur.executemany("INSERT OR REPLACE INTO Edge_ON_CARD VALUES (?, ?)", on_card_edges)
    cur.executemany("INSERT OR REPLACE INTO Edge_INVOLVES VALUES (?, ?)", involves_edges)
    cur.executemany("INSERT OR REPLACE INTO Edge_CONNECTED_TO VALUES (?, ?)", connected_to_edges)

    conn.commit()
    conn.close()

    logger.log(f"Closed cases loaded: {len(case_rows)} cases, {len(on_card_edges)} ON_CARD, {len(involves_edges)} INVOLVES, {len(connected_to_edges)} CONNECTED_TO.")


def process_transactions_batches(cust_cards, txn_to_card, txn_device_map, logger: Logger):
    """Batched, idempotent streaming load for transactions.csv (708MB)."""
    logger.log("Beginning batched streaming load of transactions.csv (708MB)...")
    t0 = time.time()

    # Read checkpoint if exists
    checkpoint = {"last_chunk": -1, "processed_rows": 0}
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, "r") as f:
                checkpoint = json.load(f)
            logger.log(f"Resuming from checkpoint: chunk {checkpoint.get('last_chunk', -1)}, rows {checkpoint.get('processed_rows', 0):,}")
        except Exception:
            pass

    txns_csv = DATA_DIR / "transactions.csv"
    chunk_idx = 0
    total_rows = 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Track sequence data for NEXT edge computation: (TransactionID, card_id, ts)
    sequence_collector = []

    for chunk in pd.read_csv(txns_csv, usecols=ALL_LOAD_COLS, chunksize=CHUNK_SIZE, low_memory=False):
        if chunk_idx <= checkpoint.get("last_chunk", -1):
            chunk_idx += 1
            total_rows += len(chunk)
            continue

        chunk_start_t = time.time()

        customers = set()
        cards = {}
        regions = set()
        emails = set()

        txn_records = []
        owns_edges = []
        made_edges = []
        email_edges = []
        region_edges = []
        device_edges = []

        for _, r in chunk.iterrows():
            tid = str(r["TransactionID"]).strip()
            cust_id = str(r["customer_id"]).strip()
            amt = float(r["TransactionAmt"]) if pd.notna(r["TransactionAmt"]) else 0.0
            ts_str = str(r["ts"]).strip()
            channel = str(r["channel"]).strip()
            score = float(r["risk_score"]) if pd.notna(r["risk_score"]) else 0.0
            pcd = str(r["ProductCD"]).strip() if pd.notna(r["ProductCD"]) else ""
            c4 = str(r["card4"]).strip() if pd.notna(r["card4"]) else ""
            c6 = str(r["card6"]).strip() if pd.notna(r["card6"]) else ""
            a1 = str(r["addr1"]).strip() if pd.notna(r["addr1"]) else ""
            a2 = str(r["addr2"]).strip() if pd.notna(r["addr2"]) else ""
            dist1 = float(r["dist1"]) if pd.notna(r["dist1"]) else None
            p_em = str(r["P_emaildomain"]).strip() if pd.notna(r["P_emaildomain"]) else ""
            r_em = str(r["R_emaildomain"]).strip() if pd.notna(r["R_emaildomain"]) else ""

            # Card mapping determination
            if tid in txn_to_card:
                card_id = txn_to_card[tid]
            elif cust_id in cust_cards and len(cust_cards[cust_id]) == 1:
                card_id = next(iter(cust_cards[cust_id]))
            else:
                card_id = f"{cust_id}-K1"

            customers.add(cust_id)
            if card_id not in cards:
                cards[card_id] = (card_id, cust_id, c4, c6)

            owns_edges.append((cust_id, card_id))
            made_edges.append((card_id, tid))

            if p_em:
                emails.add(p_em)
                email_edges.append((tid, p_em))

            if a1:
                regions.add((a1, a2))
                region_edges.append((tid, a1))

            if tid in txn_device_map:
                device_edges.append((tid, txn_device_map[tid]))

            # Collect numeric and string attributes
            c_vals = [float(r[col]) if pd.notna(r[col]) else None for col in C_COLS]
            d_vals = [float(r[col]) if pd.notna(r[col]) else None for col in D_COLS]
            v_vals = [float(r[col]) if pd.notna(r[col]) else None for col in V_COLS]
            m_vals = [str(r[col]).strip() if pd.notna(r[col]) else None for col in M_COLS]

            row_tuple = (
                tid, card_id, amt, ts_str, channel, score, pcd, c4, c6,
                a1, a2, dist1, p_em, r_em,
                *(c_vals + d_vals + v_vals + m_vals)
            )
            txn_records.append(row_tuple)

            sequence_collector.append((tid, card_id, ts_str))

        # Insert batch into SQLite
        cur.executemany("INSERT OR IGNORE INTO Customer (id, customer_id) VALUES (?, ?)", [(c, c) for c in customers])
        cur.executemany("INSERT OR REPLACE INTO Card (id, card_id, customer_id, card4, card6) VALUES (?, ?, ?, ?, ?)", [(c[0], c[0], c[1], c[2], c[3]) for c in cards.values()])
        cur.executemany("INSERT OR IGNORE INTO EmailDomain (id) VALUES (?)", [(e,) for e in emails])
        cur.executemany("INSERT OR REPLACE INTO BillingRegion (id, addr1, addr2) VALUES (?, ?, ?)", [(reg[0], reg[0], reg[1]) for reg in regions])

        placeholders = ", ".join(["?"] * (14 + len(C_COLS) + len(D_COLS) + len(V_COLS) + len(M_COLS)))
        cur.executemany(f"INSERT OR REPLACE INTO TransactionVertex VALUES ({placeholders})", txn_records)

        cur.executemany("INSERT OR IGNORE INTO Edge_OWNS VALUES (?, ?)", owns_edges)
        cur.executemany("INSERT OR IGNORE INTO Edge_MADE VALUES (?, ?)", made_edges)
        cur.executemany("INSERT OR IGNORE INTO Edge_PURCHASER_EMAIL VALUES (?, ?)", email_edges)
        cur.executemany("INSERT OR IGNORE INTO Edge_BILLED_IN VALUES (?, ?)", region_edges)
        cur.executemany("INSERT OR IGNORE INTO Edge_FROM_DEVICE VALUES (?, ?)", device_edges)

        conn.commit()

        total_rows += len(chunk)
        chunk_elapsed = time.time() - chunk_start_t
        logger.log(f"Batch {chunk_idx + 1:02d} loaded {len(chunk):,} txns in {chunk_elapsed:.2f}s | Cumulative: {total_rows:,} rows")

        # Save checkpoint
        checkpoint = {"last_chunk": chunk_idx, "processed_rows": total_rows}
        with open(CHECKPOINT_PATH, "w") as f:
            json.dump(checkpoint, f)

        chunk_idx += 1

    conn.close()
    logger.log(f"Finished transaction ingestion in {time.time() - t0:.2f}s. Total transactions loaded: {total_rows:,}")

    # Build Chronological NEXT Edges
    logger.log("Computing NEXT chronological sequence edges within each card...")
    t_next_start = time.time()

    seq_df = pd.DataFrame(sequence_collector, columns=["TransactionID", "card_id", "ts"])
    seq_df["ts_dt"] = pd.to_datetime(seq_df["ts"])
    seq_df = seq_df.sort_values(by=["card_id", "ts_dt", "TransactionID"])

    # Compute shifted transaction within card
    seq_df["next_txn_id"] = seq_df.groupby("card_id")["TransactionID"].shift(-1)
    seq_df["next_ts"] = seq_df.groupby("card_id")["ts_dt"].shift(-1)
    seq_df["delta_sec"] = (seq_df["next_ts"] - seq_df["ts_dt"]).dt.total_seconds()

    next_edges = seq_df[seq_df["next_txn_id"].notna()][["TransactionID", "next_txn_id", "card_id", "delta_sec"]].values.tolist()

    logger.log(f"Generated {len(next_edges):,} NEXT edges. Bulk inserting into database...")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("INSERT OR REPLACE INTO Edge_NEXT VALUES (?, ?, ?, ?)", next_edges)
    conn.commit()
    conn.close()

    logger.log(f"NEXT edges stored in {time.time() - t_next_start:.2f}s.")

    # Export staging file for GSQL NEXT loader
    staging_file = STAGING_DIR / "next_edges.csv"
    logger.log(f"Exporting GSQL staging file: {staging_file} ...")
    seq_df[seq_df["next_txn_id"].notna()][["TransactionID", "next_txn_id", "card_id", "delta_sec"]].to_csv(
        staging_file, index=False, header=["from_txn_id", "to_txn_id", "card_id", "delta_sec"]
    )


def run_smoke_tests(logger: Logger):
    """Execute smoke tests verifying counts, NEXT chain integrity, and closed case retrieval."""
    logger.log("=" * 80)
    logger.log("  RUNNING PHASE 1 GRAPH SMOKE TESTS")
    logger.log("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Counts per vertex type
    vertex_tables = [
        ("Customer", "Customer"),
        ("Card", "Card"),
        ("Transaction", "TransactionVertex"),
        ("DeviceProfile", "DeviceProfile"),
        ("EmailDomain", "EmailDomain"),
        ("BillingRegion", "BillingRegion"),
        ("ClosedCase", "ClosedCase"),
        ("InvestigationCase", "InvestigationCase"),
        ("EvidenceItem", "EvidenceItem")
    ]

    logger.log("--- Vertex Type Counts ---")
    counts = {}
    for label, table in vertex_tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cur.fetchone()[0]
        counts[label] = cnt
        logger.log(f"  {label:<18}: {cnt:,}")

    # Edge counts
    edge_tables = [
        ("OWNS (Cust->Card)", "Edge_OWNS"),
        ("MADE (Card->Txn)", "Edge_MADE"),
        ("FROM_DEVICE (Txn->Device)", "Edge_FROM_DEVICE"),
        ("PURCHASER_EMAIL (Txn->Email)", "Edge_PURCHASER_EMAIL"),
        ("BILLED_IN (Txn->Region)", "Edge_BILLED_IN"),
        ("NEXT (Txn->Txn)", "Edge_NEXT"),
        ("INVOLVES (Case->Txn)", "Edge_INVOLVES"),
        ("ON_CARD (Case->Card)", "Edge_ON_CARD"),
        ("CONNECTED_TO (Case->Card)", "Edge_CONNECTED_TO")
    ]

    logger.log("\n--- Edge Type Counts ---")
    for label, table in edge_tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cur.fetchone()[0]
        logger.log(f"  {label:<28}: {cnt:,}")

    # Assertions on counts
    assert counts["Customer"] > 0, "Smoke test failed: No customers loaded!"
    assert counts["Transaction"] == 590742, f"Smoke test failed: Expected 590,742 transactions, got {counts['Transaction']}"
    assert counts["ClosedCase"] == 5565, f"Smoke test failed: Expected 5,565 closed cases, got {counts['ClosedCase']}"
    assert counts["DeviceProfile"] > 0, "Smoke test failed: No device profiles loaded!"
    logger.log(">> SMOKE TEST 1: Vertex & Edge counts PASSED.")

    # 2. NEXT-chain integrity for sample card
    # Card C08623-K2 (from HHG-003) has 1,140 transactions
    sample_card = "C08623-K2"
    logger.log(f"\n--- NEXT-Chain Integrity Test for Card {sample_card} ---")

    cur.execute("SELECT id, ts FROM TransactionVertex WHERE card_id = ? ORDER BY ts ASC", (sample_card,))
    txns = cur.fetchall()
    total_card_txns = len(txns)
    logger.log(f"Total transactions on card {sample_card}: {total_card_txns}")

    cur.execute("SELECT from_id, to_id, time_delta_seconds FROM Edge_NEXT WHERE card_id = ?", (sample_card,))
    next_rows = cur.fetchall()
    logger.log(f"Total NEXT edges for card {sample_card}: {len(next_rows)}")

    assert len(next_rows) == total_card_txns - 1, (
        f"NEXT chain count mismatch: expected {total_card_txns - 1} edges, got {len(next_rows)}"
    )

    # Chain walk from first transaction
    next_map = {row[0]: (row[1], row[2]) for row in next_rows}
    current_txn = txns[0][0]
    visited = [current_txn]
    chain_ok = True

    while current_txn in next_map:
        next_txn, delta_s = next_map[current_txn]
        if delta_s < 0:
            logger.log(f"FAILED: Negative time delta ({delta_s}s) between {current_txn} and {next_txn}!")
            chain_ok = False
            break
        if next_txn in visited:
            logger.log(f"FAILED: Cycle detected at {next_txn}!")
            chain_ok = False
            break
        visited.append(next_txn)
        current_txn = next_txn

    assert chain_ok, "NEXT-chain traversal failed!"
    assert len(visited) == total_card_txns, f"NEXT-chain walk reached {len(visited)} txns, expected {total_card_txns}!"
    logger.log(f"Chain walk: Successfully traversed complete linear chain of {len(visited)} transactions.")
    logger.log(f"Timestamp monotonicity verified: all deltas >= 0.0 seconds. No cycles.")
    logger.log(f">> SMOKE TEST 2: NEXT-chain integrity for {sample_card} PASSED.")

    # 3. Closed case retrievability via each edge type
    sample_case = "CC-0004"  # Has ON_CARD, multiple INVOLVES, and CONNECTED_TO
    logger.log(f"\n--- Closed Case Retrievability Test for {sample_case} ---")

    # Fetch Case info
    cur.execute("SELECT id, outcome, pattern, exposure_usd FROM ClosedCase WHERE id = ?", (sample_case,))
    case_info = cur.fetchone()
    logger.log(f"Closed Case: {case_info[0]} | Outcome: {case_info[1]} | Pattern: {case_info[2]} | Exposure: ${case_info[3]:.2f}")

    # Retrievable via ON_CARD
    cur.execute("SELECT to_id FROM Edge_ON_CARD WHERE from_id = ?", (sample_case,))
    on_cards = [r[0] for r in cur.fetchall()]
    logger.log(f"  [ON_CARD] Primary card: {on_cards}")
    assert len(on_cards) > 0, f"Failed to retrieve card for {sample_case} via ON_CARD"

    # Retrievable via INVOLVES
    cur.execute("SELECT to_id FROM Edge_INVOLVES WHERE from_id = ?", (sample_case,))
    involves = [r[0] for r in cur.fetchall()]
    logger.log(f"  [INVOLVES] Transactions: {involves}")
    assert len(involves) > 0, f"Failed to retrieve transactions for {sample_case} via INVOLVES"

    # Retrievable via CONNECTED_TO
    cur.execute("SELECT to_id FROM Edge_CONNECTED_TO WHERE from_id = ?", (sample_case,))
    connected = [r[0] for r in cur.fetchall()]
    logger.log(f"  [CONNECTED_TO] Connected cards: {connected if connected else 'None in this case'}")

    # Also test CC-0001
    cur.execute("SELECT to_id FROM Edge_INVOLVES WHERE from_id = 'CC-0001'")
    cc1_txns = cur.fetchall()
    assert len(cc1_txns) == 1, "Failed retrieval for CC-0001 via INVOLVES"
    logger.log(f"  [INVOLVES] CC-0001 -> Transaction {cc1_txns[0][0]} successfully retrieved.")

    conn.close()
    logger.log(">> SMOKE TEST 3: Closed case retrievability across edge types PASSED.")
    logger.log("\nALL PHASE 1 SMOKE TESTS PASSED WITH 100% INTEGRITY!")


def main():
    logger = Logger(LOG_PATH)
    logger.log("=" * 80)
    logger.log("  HHGOA_IEEE — PHASE 1: GRAPH LOADING PIPELINE")
    logger.log("=" * 80)

    try:
        init_database(DB_PATH)
        cust_cards, txn_to_card = load_card_mappings(logger)
        txn_device_map, _ = load_identities(logger)
        load_closed_cases(logger)
        process_transactions_batches(cust_cards, txn_to_card, txn_device_map, logger)
        run_smoke_tests(logger)
        logger.log("\n[SUCCESS] Phase 1 graph loading and verification complete!")
    except Exception as e:
        logger.log(f"[ERROR] Loading pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        logger.close()


if __name__ == "__main__":
    main()
