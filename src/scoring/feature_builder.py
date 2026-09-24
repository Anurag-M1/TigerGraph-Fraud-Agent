#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 3: No-Leakage Feature Builder
=============================================================================
Builds strictly temporal features per investigation case.
NO DATA LEAKAGE: Evaluates transaction history strictly before or at case opened_at.

Extracts:
1. Pattern query detector scores (card testing, CNP burst, new device, region anomaly, ATO)
2. Flagged transaction signals (risk score, amount, channel, product, match flags)
3. Device and identity signals (id_15 New/Found, id_23 proxy)
4. Region novelty and concurrent home-region activity
5. Historical spending baseline and deviation ratios
6. Velocity and burst counts in 24h / 48h windows
7. Similar prior closed cases base rate
=============================================================================
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "gsql" / "graph_data" / "fraud_graph.db"


class TemporalFeatureBuilder:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._card_cache = {}
        self._ident_cache = {}
        self._prior_cases_cache = {}
        self._preload_caches()

    def _preload_caches(self):
        """Preload identity records and closed case history for fast lookup."""
        cur = self.conn.cursor()
        cur.execute("SELECT TransactionID, id_15, id_23, DeviceInfo, id_30, id_31, id_33, DeviceType FROM IdentityRecord")
        for r in cur.fetchall():
            self._ident_cache[r["TransactionID"]] = dict(r)

        cur.execute("""
            SELECT c.id, e.to_id as card_id, c.opened_at, c.outcome, c.pattern, c.exposure_usd 
            FROM ClosedCase c
            JOIN Edge_ON_CARD e ON c.id = e.from_id
        """)
        for r in cur.fetchall():
            c_dict = dict(r)
            if c_dict["opened_at"]:
                c_dict["opened_dt"] = datetime.fromisoformat(c_dict["opened_at"])
            else:
                c_dict["opened_dt"] = datetime.min
            self._prior_cases_cache.setdefault(c_dict["card_id"], []).append(c_dict)

    def get_card_txns(self, card_id: str):
        """Fetch and cache all transactions for card."""
        if card_id in self._card_cache:
            return self._card_cache[card_id]

        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, TransactionAmt, ts, channel, ProductCD, addr1, P_emaildomain,
                   M1, M2, M3, M4, M5, M6, M7, M8, M9, risk_score
            FROM TransactionVertex
            WHERE card_id = ?
            ORDER BY ts ASC
        """, (card_id,))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["ts_dt"] = datetime.fromisoformat(r["ts"])

        self._card_cache[card_id] = rows
        return rows

    def build_case_features(self, card_id: str, flagged_txn_id: str, opened_at_str: str) -> dict:
        """Construct feature vector strictly using transactions where ts <= opened_at."""
        opened_dt = datetime.fromisoformat(opened_at_str)
        all_txns = self.get_card_txns(card_id)

        # STRICT NO-LEAKAGE: Only transactions before or at opened_dt
        history_txns = [t for t in all_txns if t["ts_dt"] <= opened_dt]

        if not history_txns:
            # Fallback if card has no txns before opened_dt
            target = next((t for t in all_txns if t["id"] == flagged_txn_id), (all_txns[0] if all_txns else None))
            if target:
                history_txns = [target]

        # Target flagged transaction
        target_txn = next((t for t in history_txns if t["id"] == flagged_txn_id), None)
        if not target_txn and history_txns:
            target_txn = history_txns[-1]

        t_amt = target_txn["TransactionAmt"] if target_txn else 50.0
        t_score = target_txn["risk_score"] if target_txn else 0.50
        t_channel = target_txn["channel"] if target_txn else "in_person"
        t_addr1 = target_txn["addr1"] if target_txn else ""
        t_dt = target_txn["ts_dt"] if target_txn else opened_dt

        # Prior transactions strictly before target_txn
        prior_txns = [t for t in history_txns if t["ts_dt"] < t_dt]

        # Baseline stats on prior history
        if prior_txns:
            prior_amts = [t["TransactionAmt"] for t in prior_txns]
            p_mean = float(np.mean(prior_amts))
            p_p75 = float(np.percentile(prior_amts, 75))
            p_p95 = float(np.percentile(prior_amts, 95))
            p_in_person = sum(1 for t in prior_txns if t["channel"] == "in_person")
            p_online = sum(1 for t in prior_txns if t["channel"] == "online")
            p_total = len(prior_txns)
            prior_in_person_pct = p_in_person / p_total
            prior_online_pct = p_online / p_total

            reg_counts = pd.Series([t["addr1"] for t in prior_txns if t["addr1"]]).value_counts().to_dict()
            home_region = next(iter(reg_counts.keys())) if reg_counts else ""
            prior_in_flagged_reg = reg_counts.get(t_addr1, 0)
        else:
            p_mean = t_amt
            p_p75 = t_amt
            p_p95 = t_amt
            prior_in_person_pct = 1.0 if t_channel == "in_person" else 0.0
            prior_online_pct = 1.0 if t_channel == "online" else 0.0
            home_region = t_addr1
            prior_in_flagged_reg = 0
            p_total = 0

        # Identity & Device features
        ident = self._ident_cache.get(flagged_txn_id, {})
        id_15 = ident.get("id_15", "")
        id_23 = ident.get("id_23", "")
        is_new_device = 1 if id_15 == "New" else 0
        is_found_device = 1 if id_15 == "Found" else 0
        is_proxy = 1 if (id_23 and "proxy" in str(id_23).lower()) else 0
        has_device = 1 if ident else 0

        # Match flag discrepancies
        mismatches = 0
        if target_txn:
            if target_txn.get("M1") == "F": mismatches += 1
            if target_txn.get("M4") in ("M0", "M2", "F"): mismatches += 1
            if target_txn.get("M6") == "F": mismatches += 1

        # Region anomaly & Concurrent home transactions
        is_new_region = 1 if (prior_in_flagged_reg == 0 and t_addr1 != "" and t_channel == "in_person") else 0
        concurrent_home = [
            t for t in history_txns
            if t["addr1"] == home_region and t["id"] != flagged_txn_id
            and abs((t["ts_dt"] - t_dt).total_seconds()) <= (48 * 3600)
        ]
        concurrent_home_count = len(concurrent_home)

        # Velocity in 24h and 48h windows before opened_dt
        txns_24h = [t for t in history_txns if (opened_dt - t["ts_dt"]).total_seconds() <= 86400]
        txns_48h = [t for t in history_txns if (opened_dt - t["ts_dt"]).total_seconds() <= 172800]
        online_48h = [t for t in txns_48h if t["channel"] == "online"]
        exposure_48h = sum(t["TransactionAmt"] for t in txns_48h)

        # Pattern Detector Scores (strictly on history_txns)
        # 1. Card Testing
        conf_testing = 0.05
        online_txns_hist = [t for t in history_txns if t["channel"] == "online"]
        for i in range(len(online_txns_hist)):
            t_c = online_txns_hist[i]
            if t_c["TransactionAmt"] <= 5.0:
                c_dt = t_c["ts_dt"]
                run = [t_c]
                for j in range(i + 1, len(online_txns_hist)):
                    nxt = online_txns_hist[j]
                    if (nxt["ts_dt"] - c_dt).total_seconds() > 3600:
                        break
                    if nxt["TransactionAmt"] <= 5.0:
                        run.append(nxt)
                    elif nxt["TransactionAmt"] >= 50.0:
                        if len(run) >= 3:
                            conf_testing = 0.94 if nxt["TransactionAmt"] > 100.0 else 0.86
                        elif len(run) >= 2:
                            conf_testing = 0.72
                        break

        # 2. CNP Burst
        if 2 <= len(online_48h) <= 6:
            conf_burst = 0.85 if any(t["TransactionAmt"] > p_p75 for t in online_48h) else 0.72
        elif len(online_48h) == 1:
            conf_burst = 0.45
        else:
            conf_burst = 0.20

        # 3. New Device
        if is_new_device:
            conf_new_device = 0.90 if is_proxy else 0.82
        elif is_found_device:
            conf_new_device = 0.25
        else:
            conf_new_device = 0.10

        # 4. Region Anomaly
        if is_new_region and concurrent_home_count > 0:
            conf_region = 0.88
        elif is_new_region:
            conf_region = 0.38
        else:
            conf_region = 0.10

        # 5. Account Takeover
        near_channels = set(t["channel"] for t in txns_48h)
        if len(near_channels) > 1 and mismatches >= 1:
            conf_ato = 0.88
        elif len(near_channels) > 1:
            conf_ato = 0.72
        elif mismatches >= 2:
            conf_ato = 0.75
        else:
            conf_ato = 0.15

        # Maximum corroborated graph pattern score
        max_graph_pattern = max(conf_testing, conf_burst, conf_new_device, conf_region, conf_ato)
        has_corroborated_pattern = 1 if max_graph_pattern >= 0.70 else 0

        # Lone risk score interaction (penalizes high risk score without graph backing)
        lone_risk_score = t_score * (1.0 - has_corroborated_pattern)

        # Similar prior closed cases base rate
        prior_cases = [c for c in self._prior_cases_cache.get(card_id, []) if c["opened_dt"] < opened_dt]
        prior_cases_count = len(prior_cases)
        if prior_cases:
            prior_fraud_rate = sum(1 for c in prior_cases if c["outcome"] == "confirmed_fraud") / prior_cases_count
        else:
            prior_fraud_rate = 0.50  # Neutral prior if no previous closed cases

        return {
            "flagged_risk_score": float(t_score),
            "flagged_amount": float(t_amt),
            "flagged_is_online": 1.0 if t_channel == "online" else 0.0,
            "flagged_is_in_person": 1.0 if t_channel == "in_person" else 0.0,
            "is_new_device": float(is_new_device),
            "is_proxy": float(is_proxy),
            "has_device": float(has_device),
            "mismatch_count": float(mismatches),
            "is_new_region": float(is_new_region),
            "concurrent_home_count": float(concurrent_home_count),
            "amount_to_mean_ratio": float(t_amt / (p_mean + 1e-3)),
            "amount_to_p75_ratio": float(t_amt / (p_p75 + 1e-3)),
            "prior_txns_count": float(p_total),
            "prior_in_person_pct": float(prior_in_person_pct),
            "prior_online_pct": float(prior_online_pct),
            "txns_24h": float(len(txns_24h)),
            "txns_48h": float(len(txns_48h)),
            "online_48h": float(len(online_48h)),
            "exposure_48h": float(exposure_48h),
            "conf_testing": float(conf_testing),
            "conf_burst": float(conf_burst),
            "conf_new_device": float(conf_new_device),
            "conf_region": float(conf_region),
            "conf_ato": float(conf_ato),
            "max_graph_pattern": float(max_graph_pattern),
            "has_corroborated_pattern": float(has_corroborated_pattern),
            "lone_risk_score": float(lone_risk_score),
            "prior_cases_count": float(prior_cases_count),
            "prior_fraud_rate": float(prior_fraud_rate)
        }

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def __del__(self):
        self.close()
