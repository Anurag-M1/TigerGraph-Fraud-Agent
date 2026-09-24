#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 2: Graph Query Engine Implementation
=============================================================================
Provides Python/GSQL interface executing the 13 fraud investigation queries:
1. card_window(card_id, hours, center_ts)
2. detect_card_testing(card_id, window_minutes, max_auth_amt, large_purchase_amt)
3. card_baseline(card_id)
4. detect_cnp_burst(card_id, flagged_txn_id, window_hours)
5. detect_new_device(txn_id)
6. detect_region_anomaly(card_id, flagged_txn_id)
7. detect_account_takeover(card_id, flagged_txn_id)
8. device_neighbors(device_profile_id, window_days)
9. region_cluster(addr1) & email_cluster(email_domain)
10. case_memory_lookup(card_id, customer_id, device_id, addr1)
11. undocumented_sweep(min_card_fanout, structured_range)
12. upsert_investigation_case, add_evidence, link_case_entities
13. device_fanout_ranking, shared_device_components

All queries return structured JSON with:
- matched_entities: list of IDs
- evidence_trail: list of structured claims
- confidence_contribution: float 0.0 - 1.0
=============================================================================
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "gsql" / "graph_data" / "fraud_graph.db"


class GraphQueryEngine:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}. Run gsql/load_graph.py first.")

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------------
    # 1. card_window
    # ------------------------------------------------------------------------
    def card_window(self, card_id: str, hours: int = 24, center_ts: str = None):
        """Walk transaction sequence for card_id via NEXT edges within time window."""
        conn = self.get_conn()
        cur = conn.cursor()

        query = """
            SELECT id, TransactionAmt, ts, channel, risk_score, ProductCD, addr1
            FROM TransactionVertex
            WHERE card_id = ?
            ORDER BY ts ASC
        """
        cur.execute(query, (card_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not rows:
            return {
                "matched_entities": [],
                "evidence_trail": [f"No transactions found for card {card_id}"],
                "confidence_contribution": 0.0,
                "window_txns": []
            }

        if center_ts:
            c_dt = pd.to_datetime(center_ts)
            filtered = [
                r for r in rows
                if abs((pd.to_datetime(r["ts"]) - c_dt).total_seconds()) <= (hours * 3600)
            ]
        else:
            filtered = rows

        matched_ids = [r["id"] for r in filtered]
        total_amt = sum(r["TransactionAmt"] for r in filtered)

        return {
            "matched_entities": matched_ids,
            "evidence_trail": [
                f"Retrieved {len(filtered)} transactions on card {card_id} in {hours}h window totaling ${total_amt:.2f}"
            ],
            "confidence_contribution": 0.50 if len(filtered) > 1 else 0.10,
            "window_txns": filtered
        }

    # ------------------------------------------------------------------------
    # 2. detect_card_testing (Policy R5)
    # ------------------------------------------------------------------------
    def detect_card_testing(self, card_id: str, window_minutes: int = 60, max_auth_amt: float = 5.0, large_purchase_amt: float = 50.0):
        """Policy R5: >= 3 online authorizations <= $5.00 within 60 min followed by larger purchase."""
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, TransactionAmt, ts, channel, ProductCD
            FROM TransactionVertex
            WHERE card_id = ?
            ORDER BY ts ASC
        """, (card_id,))
        txns = [dict(r) for r in cur.fetchall()]
        conn.close()

        if len(txns) < 2:
            return {
                "matched_entities": [],
                "evidence_trail": ["Insufficient transactions to evaluate card testing sequence"],
                "confidence_contribution": 0.0,
                "pattern": "none",
                "cleared_over_100": False
            }

        # Pre-parse timestamps
        ts_list = [datetime.fromisoformat(t["ts"]) for t in txns]
        n = len(txns)
        testing_runs = []

        for i in range(n):
            t_curr = txns[i]
            if t_curr["channel"] == "online" and t_curr["TransactionAmt"] <= max_auth_amt:
                curr_dt = ts_list[i]
                curr_run = [t_curr]
                for j in range(i + 1, n):
                    if (ts_list[j] - curr_dt).total_seconds() > (window_minutes * 60):
                        break
                    nxt = txns[j]
                    if nxt["channel"] == "online" and nxt["TransactionAmt"] <= max_auth_amt:
                        curr_run.append(nxt)
                    elif nxt["TransactionAmt"] >= large_purchase_amt:
                        if len(curr_run) >= 3:
                            testing_runs.append((curr_run, nxt))
                        break

        if testing_runs:
            probes, large = testing_runs[0]
            matched_ids = [p["id"] for p in probes] + [large["id"]]
            exposure = sum(p["TransactionAmt"] for p in probes) + large["TransactionAmt"]
            cleared_100 = (large["TransactionAmt"] > 100.0)

            claims = [
                f"Card testing sequence confirmed: {len(probes)} micro-authorizations under ${max_auth_amt:.2f} within {window_minutes}m, followed by ${large['TransactionAmt']:.2f} purchase",
                f"Policy R5 triggered: large purchase ${large['TransactionAmt']:.2f} (cleared > $100: {cleared_100})"
            ]
            return {
                "matched_entities": matched_ids,
                "evidence_trail": claims,
                "confidence_contribution": 0.94 if cleared_100 else 0.86,
                "pattern": "card_testing",
                "cleared_over_100": cleared_100,
                "probe_count": len(probes),
                "large_txn_id": large["id"],
                "exposure_usd": exposure
            }

        # Check for probes without large purchase
        online_low = [t for t in txns if t["channel"] == "online" and t["TransactionAmt"] <= max_auth_amt]
        if len(online_low) >= 3:
            return {
                "matched_entities": [t["id"] for t in online_low],
                "evidence_trail": [f"{len(online_low)} small online authorizations observed without immediate large purchase"],
                "confidence_contribution": 0.55,
                "pattern": "card_testing",
                "cleared_over_100": False,
                "probe_count": len(online_low),
                "large_txn_id": "",
                "exposure_usd": sum(t["TransactionAmt"] for t in online_low)
            }

        return {
            "matched_entities": [],
            "evidence_trail": ["No card testing sequence detected"],
            "confidence_contribution": 0.05,
            "pattern": "none",
            "cleared_over_100": False
        }

    # ------------------------------------------------------------------------
    # 3. card_baseline
    # ------------------------------------------------------------------------
    def card_baseline(self, card_id: str):
        """Historical baseline profiling for the card (cached)."""
        if not hasattr(self, "_baseline_cache"):
            self._baseline_cache = {}
        if card_id in self._baseline_cache:
            return self._baseline_cache[card_id]

        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT TransactionAmt, channel, ProductCD, addr1, P_emaildomain, ts
            FROM TransactionVertex
            WHERE card_id = ?
        """, (card_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not rows:
            res = {"error": f"Card {card_id} not found"}
            self._baseline_cache[card_id] = res
            return res

        amounts = [r["TransactionAmt"] for r in rows]
        df_amt = pd.Series(amounts)

        channels = pd.Series([r["channel"] for r in rows]).value_counts().to_dict()
        products = pd.Series([r["ProductCD"] for r in rows if r["ProductCD"]]).value_counts().to_dict()
        regions = pd.Series([r["addr1"] for r in rows if r["addr1"]]).value_counts().to_dict()
        emails = pd.Series([r["P_emaildomain"] for r in rows if r["P_emaildomain"]]).value_counts().to_dict()

        home_region = next(iter(regions.keys())) if regions else ""

        res = {
            "card_id": card_id,
            "total_txns": len(rows),
            "amount_stats": {
                "mean": float(df_amt.mean()),
                "median": float(df_amt.median()),
                "p25": float(df_amt.quantile(0.25)),
                "p75": float(df_amt.quantile(0.75)),
                "p95": float(df_amt.quantile(0.95)),
                "min": float(df_amt.min()),
                "max": float(df_amt.max()),
                "std": float(df_amt.std()) if len(df_amt) > 1 else 0.0
            },
            "home_region": home_region,
            "channel_distribution": channels,
            "product_distribution": products,
            "region_distribution": regions,
            "email_distribution": emails,
            "confidence_contribution": 1.0
        }
        self._baseline_cache[card_id] = res
        return res

    # ------------------------------------------------------------------------
    # 4. detect_cnp_burst (Pattern 2)
    # ------------------------------------------------------------------------
    def detect_cnp_burst(self, card_id: str, flagged_txn_id: str = None, window_hours: int = 48):
        """Pattern 2: 2–4 online transactions within 48h inconsistent with baseline."""
        baseline = self.card_baseline(card_id)
        if "error" in baseline:
            return {"confidence_contribution": 0.0, "matched_entities": []}

        p75 = baseline["amount_stats"]["p75"]
        mean_amt = baseline["amount_stats"]["mean"]

        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, TransactionAmt, ts, channel, ProductCD, risk_score
            FROM TransactionVertex
            WHERE card_id = ? AND channel = 'online'
            ORDER BY ts ASC
        """, (card_id,))
        online_txns = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not online_txns:
            return {
                "matched_entities": [],
                "evidence_trail": ["No online transactions found on this card"],
                "confidence_contribution": 0.0,
                "pattern": "none"
            }

        ts_list = [datetime.fromisoformat(t["ts"]) for t in online_txns]

        # If flagged_txn_id provided, anchor window around it
        if flagged_txn_id:
            flagged_idx = next((i for i, t in enumerate(online_txns) if t["id"] == flagged_txn_id), None)
            if flagged_idx is not None:
                f_dt = ts_list[flagged_idx]
                cluster = [
                    online_txns[i] for i, dt in enumerate(ts_list)
                    if abs((dt - f_dt).total_seconds()) <= (window_hours * 3600)
                ]
            else:
                cluster = [online_txns[-1]]
        else:
            # Linear O(N) sliding window to find highest exposure cluster
            max_cnt = 0
            best_start = 0
            r = 0
            n_tx = len(online_txns)
            for l in range(n_tx):
                while r < n_tx and (ts_list[r] - ts_list[l]).total_seconds() <= (window_hours * 3600):
                    r += 1
                if (r - l) > max_cnt:
                    max_cnt = r - l
                    best_start = l
            cluster = online_txns[best_start : best_start + max_cnt]

        burst_count = len(cluster)
        burst_exposure = sum(t["TransactionAmt"] for t in cluster)
        matched_ids = [t["id"] for t in cluster]

        # Inconsistency criteria: amounts exceed p75 or mean * 1.5
        is_anomalous_amt = any(t["TransactionAmt"] > p75 or t["TransactionAmt"] > (mean_amt * 1.5) for t in cluster)

        if 2 <= burst_count <= 6:
            conf = 0.84 if is_anomalous_amt else 0.70
            claims = [
                f"Card-not-present burst detected: {burst_count} online transactions within {window_hours}h totaling ${burst_exposure:.2f}",
                f"Amounts deviate from cardholder baseline (baseline mean: ${mean_amt:.2f}, p75: ${p75:.2f})"
            ]
        elif burst_count == 1:
            conf = 0.45  # Single unusual online purchase -> R1 verify
            claims = [f"Single isolated online transaction of ${burst_exposure:.2f} (verify with customer under R1)"]
        else:
            conf = 0.60
            claims = [f"High volume online activity ({burst_count} txns in {window_hours}h)"]

        return {
            "matched_entities": matched_ids,
            "evidence_trail": claims,
            "confidence_contribution": conf,
            "pattern": "card_not_present_fraud",
            "burst_count": burst_count,
            "exposure_usd": burst_exposure
        }

    # ------------------------------------------------------------------------
    # 5. detect_new_device (Pattern 3)
    # ------------------------------------------------------------------------
    def detect_new_device(self, txn_id: str):
        """Pattern 3: identity id_15=New, id_23 proxy flag, DeviceProfile details."""
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT t.id, t.card_id, t.channel, t.TransactionAmt, t.risk_score,
                   i.id_15, i.id_23, i.DeviceInfo, i.id_30, i.id_31, i.id_33, i.DeviceType
            FROM TransactionVertex t
            LEFT JOIN IdentityRecord i ON t.id = i.TransactionID
            WHERE t.id = ?
        """, (txn_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return {"error": f"Transaction {txn_id} not found", "confidence_contribution": 0.0}

        row_dict = dict(row)
        is_online = (row_dict["channel"] == "online")
        id_15 = row_dict["id_15"]
        id_23 = row_dict["id_23"]
        dev_info = row_dict["DeviceInfo"]

        dp_parts = [row_dict[c] for c in ["DeviceInfo", "id_30", "id_31", "id_33"] if row_dict[c]]
        dp_str = " | ".join(dp_parts) if dp_parts else "unknown"

        is_new = (id_15 == "New")
        is_proxy = bool(id_23 and "proxy" in id_23.lower())

        claims = []
        conf = 0.10

        if is_online:
            if is_new:
                conf = 0.85 if is_proxy else 0.78
                claims.append(f"Transaction originated from a new device profile: {dp_str} (id_15 = 'New')")
                if is_proxy:
                    claims.append(f"Connection utilized anonymizing proxy: {id_23}")
            elif id_15 == "Found":
                conf = 0.30
                claims.append(f"Device profile {dp_str} previously recognized on account (id_15 = 'Found')")
            else:
                conf = 0.50
                claims.append(f"Online transaction with device profile: {dp_str}")
        else:
            conf = 0.0
            claims.append("In-person transaction (no device profile)")

        return {
            "matched_entities": [txn_id] + ([dp_str] if dp_str != "unknown" else []),
            "evidence_trail": claims,
            "confidence_contribution": conf,
            "pattern": "card_not_present_new_device" if (is_online and is_new) else "none",
            "device_profile": dp_str,
            "id_15": id_15,
            "id_23": id_23
        }

    # ------------------------------------------------------------------------
    # 6. detect_region_anomaly (Pattern 4)
    # ------------------------------------------------------------------------
    def detect_region_anomaly(self, card_id: str, flagged_txn_id: str = None):
        """Pattern 4: in_person txns in addr1 with no card history while home activity continues."""
        conn = self.get_conn()
        cur = conn.cursor()

        baseline = self.card_baseline(card_id)
        if "error" in baseline:
            conn.close()
            return {"confidence_contribution": 0.0, "matched_entities": []}

        home_region = baseline["home_region"]
        region_dist = baseline["region_distribution"]

        if flagged_txn_id:
            cur.execute("SELECT id, addr1, channel, ts, TransactionAmt FROM TransactionVertex WHERE id = ?", (flagged_txn_id,))
            target = cur.fetchone()
        else:
            cur.execute("""
                SELECT id, addr1, channel, ts, TransactionAmt
                FROM TransactionVertex
                WHERE card_id = ? AND channel = 'in_person'
                ORDER BY ts DESC LIMIT 1
            """, (card_id,))
            target = cur.fetchone()

        if not target:
            conn.close()
            return {
                "matched_entities": [],
                "evidence_trail": ["No in-person transactions to evaluate regional anomaly"],
                "confidence_contribution": 0.0,
                "pattern": "none"
            }

        target_dict = dict(target)
        t_reg = target_dict["addr1"]
        t_channel = target_dict["channel"]
        t_dt = pd.to_datetime(target_dict["ts"])

        # Prior count in target region
        prior_in_target = region_dist.get(t_reg, 0)
        # If flagged txn is included in region_dist, subtract 1
        prior_in_target = max(0, prior_in_target - 1)

        # Check for concurrent transactions in home region within +/- 48h
        cur.execute("""
            SELECT id, ts, addr1, TransactionAmt
            FROM TransactionVertex
            WHERE card_id = ? AND addr1 = ? AND id != ?
        """, (card_id, home_region, target_dict["id"]))
        home_txns = [dict(r) for r in cur.fetchall()]
        conn.close()

        concurrent_home = [
            h for h in home_txns
            if abs((pd.to_datetime(h["ts"]) - t_dt).total_seconds()) <= (48 * 3600)
        ]

        claims = []
        if prior_in_target == 0 and t_channel == "in_person" and t_reg:
            if concurrent_home:
                conf = 0.88
                claims.append(
                    f"Out-of-region compromise: in-person transaction in region {t_reg} (0 prior history), "
                    f"while cardholder made {len(concurrent_home)} concurrent transactions in home region {home_region} within 48h"
                )
                pattern = "out_of_region_use"
            else:
                conf = 0.38
                claims.append(
                    f"In-person transaction in new region {t_reg} without concurrent home transactions; consistent with cardholder travel/trip"
                )
                pattern = "none"
        elif prior_in_target >= 10:
            conf = 0.10
            claims.append(
                f"Region {t_reg} is cardholder's established location ({prior_in_target} prior transactions); legitimate physical presence"
            )
            pattern = "none"
        else:
            conf = 0.25
            claims.append(f"Region {t_reg} previously visited ({prior_in_target} prior transactions)")
            pattern = "none"

        return {
            "matched_entities": [target_dict["id"], t_reg, home_region],
            "evidence_trail": claims,
            "confidence_contribution": conf,
            "pattern": pattern,
            "flagged_region": t_reg,
            "home_region": home_region,
            "prior_in_target_region": prior_in_target,
            "concurrent_home_txns": len(concurrent_home)
        }

    # ------------------------------------------------------------------------
    # 7. detect_account_takeover (Pattern 5)
    # ------------------------------------------------------------------------
    def detect_account_takeover(self, card_id: str, flagged_txn_id: str = None):
        """Pattern 5: mixed-channel inconsistency + M1-M9 match-flag anomalies."""
        conn = self.get_conn()
        cur = conn.cursor()

        baseline = self.card_baseline(card_id)
        if "error" in baseline:
            conn.close()
            return {"confidence_contribution": 0.0, "matched_entities": []}

        ch_dist = baseline["channel_distribution"]
        in_person_hist = ch_dist.get("in_person", 0)
        online_hist = ch_dist.get("online", 0)

        if flagged_txn_id:
            cur.execute("""
                SELECT id, channel, TransactionAmt, M1, M2, M3, M4, M5, M6, M7, M8, M9
                FROM TransactionVertex
                WHERE id = ?
            """, (flagged_txn_id,))
        else:
            cur.execute("""
                SELECT id, channel, TransactionAmt, M1, M2, M3, M4, M5, M6, M7, M8, M9
                FROM TransactionVertex
                WHERE card_id = ?
                ORDER BY ts DESC LIMIT 1
            """, (card_id,))

        target = cur.fetchone()
        conn.close()

        if not target:
            return {"confidence_contribution": 0.0, "matched_entities": []}

        t_dict = dict(target)
        mismatches = 0
        if t_dict.get("M1") == "F": mismatches += 1
        if t_dict.get("M4") in ("M2", "F"): mismatches += 1
        if t_dict.get("M6") == "F": mismatches += 1

        claims = []
        conf = 0.20
        pattern = "none"

        is_sudden_online = (t_dict["channel"] == "online" and online_hist <= 1 and in_person_hist >= 15)

        if is_sudden_online and mismatches >= 1:
            conf = 0.88
            pattern = "account_takeover"
            claims.append(
                f"Account Takeover indicators: 100% in-person spending history ({in_person_hist} txns) abruptly interrupted by online transaction with {mismatches} identity match flag discrepancies"
            )
        elif mismatches >= 2:
            conf = 0.78
            pattern = "account_takeover"
            claims.append(f"Multiple identity match discrepancies observed ({mismatches} mismatches in M1-M9 flags)")
        else:
            claims.append("No abnormal channel shifts or severe identity mismatch flags detected")

        return {
            "matched_entities": [t_dict["id"]],
            "evidence_trail": claims,
            "confidence_contribution": conf,
            "pattern": pattern,
            "mismatch_count": mismatches,
            "historical_in_person": in_person_hist,
            "historical_online": online_hist
        }

    # ------------------------------------------------------------------------
    # 8. device_neighbors (Policy R6)
    # ------------------------------------------------------------------------
    def device_neighbors(self, device_profile_id: str, window_days: int = 30):
        """Policy R6: every other card using the same device profile."""
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT t.card_id, c.customer_id, t.id AS txn_id, t.TransactionAmt, t.ts
            FROM Edge_FROM_DEVICE e
            JOIN TransactionVertex t ON e.from_id = t.id
            JOIN Card c ON t.card_id = c.id
            WHERE e.to_id = ?
            ORDER BY t.ts ASC
        """, (device_profile_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        cards = list(set(r["card_id"] for r in rows))
        custs = list(set(r["customer_id"] for r in rows))
        total_exp = sum(r["TransactionAmt"] for r in rows)

        if len(cards) >= 3:
            conf = 0.95
            claim = f"Shared device ring confirmed: Device profile '{device_profile_id}' used across {len(cards)} distinct cards ({len(custs)} customers) totaling ${total_exp:.2f}"
        elif len(cards) == 2:
            conf = 0.82
            claim = f"Cross-card device link: Device profile '{device_profile_id}' shared between cards {cards}"
        else:
            conf = 0.20
            claim = f"Device profile '{device_profile_id}' associated with single card {cards}"

        return {
            "matched_entities": cards + [device_profile_id],
            "connected_cards": cards,
            "connected_customers": custs,
            "distinct_card_count": len(cards),
            "total_shared_exposure_usd": total_exp,
            "evidence_trail": [claim],
            "confidence_contribution": conf,
            "pattern": "shared_origin_ring"
        }

    # ------------------------------------------------------------------------
    # 9. region_cluster & email_cluster (Policy R6)
    # ------------------------------------------------------------------------
    def region_cluster(self, addr1: str, window_days: int = 30):
        """Cards whose fraud/closed cases share billing region."""
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT cc.id AS case_id, cc.card_id, cc.outcome, cc.pattern, cc.exposure_usd
            FROM TransactionVertex t
            JOIN Edge_INVOLVES ei ON t.id = ei.to_id
            JOIN ClosedCase cc ON ei.from_id = cc.id
            WHERE t.addr1 = ? AND cc.outcome = 'confirmed_fraud'
        """, (str(addr1),))
        cases = [dict(r) for r in cur.fetchall()]
        conn.close()

        unique_cards = list(set(c["card_id"] for c in cases))
        total_exp = sum(c["exposure_usd"] for c in cases)

        conf = 0.88 if len(unique_cards) >= 3 else (0.70 if len(unique_cards) >= 1 else 0.15)
        claim = f"Geographic fraud cluster in region {addr1}: {len(cases)} confirmed fraud cases across {len(unique_cards)} cards totaling ${total_exp:.2f}"

        return {
            "matched_entities": unique_cards,
            "billing_region": addr1,
            "fraud_card_count": len(unique_cards),
            "linked_cases": [c["case_id"] for c in cases],
            "total_exposure_usd": total_exp,
            "evidence_trail": [claim],
            "confidence_contribution": conf
        }

    def email_cluster(self, email_domain: str, window_days: int = 30):
        """Cards whose fraud/closed cases share purchaser email domain."""
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT cc.id AS case_id, cc.card_id, cc.outcome, cc.exposure_usd
            FROM TransactionVertex t
            JOIN Edge_INVOLVES ei ON t.id = ei.to_id
            JOIN ClosedCase cc ON ei.from_id = cc.id
            WHERE t.P_emaildomain = ? AND cc.outcome = 'confirmed_fraud'
        """, (str(email_domain),))
        cases = [dict(r) for r in cur.fetchall()]
        conn.close()

        unique_cards = list(set(c["card_id"] for c in cases))
        conf = 0.82 if len(unique_cards) >= 3 else 0.35

        return {
            "matched_entities": unique_cards,
            "email_domain": email_domain,
            "fraud_card_count": len(unique_cards),
            "linked_cases": [c["case_id"] for c in cases],
            "evidence_trail": [f"Email domain {email_domain} linked to {len(unique_cards)} confirmed fraud cards"],
            "confidence_contribution": conf
        }

    # ------------------------------------------------------------------------
    # 10. case_memory_lookup
    # ------------------------------------------------------------------------
    def case_memory_lookup(self, card_id: str = None, customer_id: str = None, device_id: str = None, addr1: str = None):
        """Retrieve prior ClosedCases sharing card, customer, device, or region."""
        conn = self.get_conn()
        cur = conn.cursor()

        cases = {}
        if card_id:
            cur.execute("""
                SELECT cc.* FROM ClosedCase cc
                JOIN Edge_ON_CARD e ON cc.id = e.from_id
                WHERE e.to_id = ?
            """, (card_id,))
            for r in cur.fetchall():
                cases[r["id"]] = dict(r)

            cur.execute("""
                SELECT cc.* FROM ClosedCase cc
                JOIN Edge_CONNECTED_TO e ON cc.id = e.from_id
                WHERE e.to_id = ?
            """, (card_id,))
            for r in cur.fetchall():
                cases[r["id"]] = dict(r)

        if customer_id and not cases:
            cur.execute("SELECT id FROM Card WHERE customer_id = ?", (customer_id,))
            for c_row in cur.fetchall():
                cur.execute("SELECT cc.* FROM ClosedCase cc JOIN Edge_ON_CARD e ON cc.id = e.from_id WHERE e.to_id = ?", (c_row["id"],))
                for r in cur.fetchall():
                    cases[r["id"]] = dict(r)

        conn.close()

        case_list = list(cases.values())
        confirmed = [c for c in case_list if c["outcome"] == "confirmed_fraud"]
        cleared = [c for c in case_list if c["outcome"] == "cleared"]

        claims = [
            f"Case memory lookup found {len(case_list)} prior investigations ({len(confirmed)} confirmed fraud, {len(cleared)} cleared false alarms)"
        ]

        return {
            "matched_entities": [c["id"] for c in case_list],
            "similar_prior_cases": [c["id"] for c in case_list],
            "confirmed_count": len(confirmed),
            "cleared_count": len(cleared),
            "cases": case_list,
            "evidence_trail": claims,
            "confidence_contribution": 0.85 if confirmed else (0.20 if cleared else 0.50)
        }

    # ------------------------------------------------------------------------
    # 11. undocumented_sweep (Policy R9 & Innovation)
    # ------------------------------------------------------------------------
    def undocumented_sweep(self, min_card_fanout: int = 3):
        """Cross-customer sweep for novel coordinated patterns."""
        conn = self.get_conn()
        cur = conn.cursor()

        # 1. Device fanout
        cur.execute("""
            SELECT e.to_id AS device_profile, COUNT(DISTINCT t.card_id) AS card_cnt, SUM(t.TransactionAmt) AS exp
            FROM Edge_FROM_DEVICE e
            JOIN TransactionVertex t ON e.from_id = t.id
            GROUP BY e.to_id
            HAVING card_cnt >= ?
            ORDER BY card_cnt DESC
        """, (min_card_fanout,))
        high_fanout = [dict(r) for r in cur.fetchall()]

        # 2. Structured amounts evasion ($99.00 - $99.99)
        cur.execute("""
            SELECT COUNT(*) AS cnt, SUM(TransactionAmt) AS total_amt
            FROM TransactionVertex
            WHERE TransactionAmt >= 99.00 AND TransactionAmt <= 99.99 AND channel = 'online'
        """)
        structured = dict(cur.fetchone())
        conn.close()

        claims = [
            f"Undocumented pattern sweep identified {len(high_fanout)} high-fanout device profiles linking >= {min_card_fanout} cards",
            f"Structured amounts monitoring: {structured['cnt']:,} online authorizations between $99.00 and $99.99 totaling ${structured['total_amt']:,.2f}"
        ]

        return {
            "matched_entities": [d["device_profile"] for d in high_fanout],
            "high_fanout_devices": high_fanout,
            "structured_count": structured["cnt"],
            "evidence_trail": claims,
            "confidence_contribution": 0.88,
            "pattern": "undocumented"
        }

    # ------------------------------------------------------------------------
    # 12. Case Mutations (Case Memory)
    # ------------------------------------------------------------------------
    def upsert_investigation_case(self, case_id: str, status: str, verdict: str, fraud_probability: float,
                                 pattern: str, pattern_description: str, exposure_usd: float,
                                 summary: str, sar_filed: bool, sar_narrative: str):
        """Persist agent investigation case into graph memory."""
        graph_case_id = f"CASE-{case_id}"
        conn = self.get_conn()
        cur = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            INSERT OR REPLACE INTO InvestigationCase (
                id, opened_at, status, verdict, fraud_probability,
                pattern, pattern_description, exposure_usd, summary,
                sar_filed, sar_narrative
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            graph_case_id, now_str, status, verdict, fraud_probability,
            pattern, pattern_description, exposure_usd, summary,
            1 if sar_filed else 0, sar_narrative
        ))
        conn.commit()
        conn.close()

        return {
            "graph_case_id": graph_case_id,
            "status": "persisted",
            "written_to_graph": True
        }

    def add_evidence(self, case_id: str, evidence_id: str, claim: str, source: str, ref: str):
        """Attach evidence claim to investigation case."""
        graph_case_id = f"CASE-{case_id}"
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO EvidenceItem (id, claim, source, ref)
            VALUES (?, ?, ?, ?)
        """, (evidence_id, claim, source, ref))

        cur.execute("""
            INSERT OR IGNORE INTO Edge_REFERENCES_EVIDENCE (from_id, to_id)
            VALUES (?, ?)
        """, (graph_case_id, evidence_id))

        conn.commit()
        conn.close()
        return {"evidence_id": evidence_id, "graph_case_id": graph_case_id, "status": "linked"}

    def link_case_entities(self, case_id: str, transaction_ids: list):
        """Link investigation case to affected transaction entities."""
        graph_case_id = f"CASE-{case_id}"
        conn = self.get_conn()
        cur = conn.cursor()

        links = [(graph_case_id, tid) for tid in transaction_ids]
        cur.executemany("INSERT OR IGNORE INTO Edge_RAISED (from_id, to_id) VALUES (?, ?)", links)
        conn.commit()
        conn.close()
        return {"graph_case_id": graph_case_id, "linked_txns": len(links)}

    # ------------------------------------------------------------------------
    # 13. Graph Algorithms: Fan-out & Community Detection
    # ------------------------------------------------------------------------
    def device_fanout_ranking(self, top_k: int = 20):
        """Rank DeviceProfiles by distinct payment card degree."""
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT e.to_id AS device_profile, COUNT(DISTINCT t.card_id) AS card_degree,
                   COUNT(t.id) AS txn_count, SUM(t.TransactionAmt) AS total_amt
            FROM Edge_FROM_DEVICE e
            JOIN TransactionVertex t ON e.from_id = t.id
            GROUP BY e.to_id
            ORDER BY card_degree DESC
            LIMIT ?
        """, (top_k,))
        results = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"top_fanout_devices": results}

    def shared_device_components(self, min_size: int = 2):
        """Discover connected components over Card <-> Device bipartite graph."""
        import networkx as nx
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT t.card_id, e.to_id AS device_id
            FROM Edge_FROM_DEVICE e
            JOIN TransactionVertex t ON e.from_id = t.id
            WHERE e.to_id != 'unknown'
        """)
        edges = cur.fetchall()
        conn.close()

        G = nx.Graph()
        for r in edges:
            G.add_edge(r[0], f"DEV:{r[1]}")

        communities = []
        for comp in nx.connected_components(G):
            cards = [n for n in comp if not n.startswith("DEV:")]
            devs = [n[4:] for n in comp if n.startswith("DEV:")]
            if len(cards) >= min_size:
                communities.append({
                    "card_count": len(cards),
                    "device_count": len(devs),
                    "cards": cards[:15],
                    "devices": devs[:5]
                })

        communities.sort(key=lambda x: x["card_count"], reverse=True)
        return {"communities_count": len(communities), "communities": communities[:10]}


# Singleton instance
engine = GraphQueryEngine()

if __name__ == "__main__":
    print("Testing GraphQueryEngine:")
    # Test card_baseline
    res_b = engine.card_baseline("C08623-K2")
    print(f"Card C08623-K2 Baseline: Home Region={res_b['home_region']}, Mean Amount=${res_b['amount_stats']['mean']:.2f}")

    # Test detect_card_testing on CC-0001
    res_t = engine.detect_card_testing("C00259-K1")
    print(f"Card C00259-K1 Testing: Pattern={res_t['pattern']}, Conf={res_t['confidence_contribution']}")

    # Test device fanout
    res_dev = engine.device_fanout_ranking(top_k=3)
    print(f"Top fanout device: {res_dev['top_fanout_devices'][0]['device_profile']} (degree: {res_dev['top_fanout_devices'][0]['card_degree']})")
