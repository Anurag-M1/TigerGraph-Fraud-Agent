#!/usr/bin/env python3
"""Phase 0 – Manual case investigation helper.
Usage: python scripts/investigate_case.py HHG-003 HHG-010
Loads all data once, then prints a structured investigation report per case.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys, json
from datetime import timedelta

DATA = Path("Dataset")

def load_data():
    print("Loading transactions.csv ...", file=sys.stderr)
    txn = pd.read_csv(DATA / "transactions.csv", low_memory=False)
    txn["ts"] = pd.to_datetime(txn["ts"])
    txn["TransactionID"] = txn["TransactionID"].astype(str)

    print("Loading identity.csv ...", file=sys.stderr)
    ident = pd.read_csv(DATA / "identity.csv", low_memory=False)
    ident["TransactionID"] = ident["TransactionID"].astype(str)

    print("Loading closed_cases_history.csv ...", file=sys.stderr)
    cc = pd.read_csv(DATA / "closed_cases_history.csv")

    print("Loading case_pack.csv ...", file=sys.stderr)
    cp = pd.read_csv(DATA / "case_pack.csv")

    return txn, ident, cc, cp


def get_device_profile(ident_row):
    """Build a device profile string from identity record."""
    parts = []
    if pd.notna(ident_row.get("DeviceInfo")):
        parts.append(str(ident_row["DeviceInfo"]))
    if pd.notna(ident_row.get("id_30")):
        parts.append(str(ident_row["id_30"]))
    if pd.notna(ident_row.get("id_31")):
        parts.append(str(ident_row["id_31"]))
    if pd.notna(ident_row.get("id_33")):
        parts.append(str(ident_row["id_33"]))
    return " | ".join(parts) if parts else "unknown"


def investigate(case_id, txn, ident, cc, cp):
    """Run a full investigation on a case and print structured report."""
    case = cp[cp["case_id"] == case_id].iloc[0]
    flagged_txn_id = str(case["flagged_txn_id"])
    card_id = case["card_id"]
    customer_id = case["customer_id"]

    sep = "=" * 80
    print(f"\n{sep}")
    print(f"  INVESTIGATION: {case_id}")
    print(f"  Trigger: {case['trigger_type']} | Card: {card_id} | Customer: {customer_id}")
    print(f"  {case['trigger_text']}")
    print(sep)

    # ── Flagged Transaction ───────────────────────────────────────────
    flagged = txn[txn["TransactionID"] == flagged_txn_id]
    if flagged.empty:
        print(f"\n⚠ Flagged transaction {flagged_txn_id} NOT FOUND in transactions.csv!")
        return
    ft = flagged.iloc[0]
    print(f"\n── Flagged Transaction ──")
    print(f"  TxnID: {flagged_txn_id}")
    print(f"  Amount: ${ft['TransactionAmt']:.2f}")
    print(f"  Time: {ft['ts']}")
    print(f"  Channel: {ft['channel']}")
    print(f"  ProductCD: {ft['ProductCD']}")
    print(f"  Risk Score: {ft['risk_score']}")
    print(f"  Card1: {ft['card1']} | Card4 (network): {ft.get('card4','?')} | Card6 (type): {ft.get('card6','?')}")
    print(f"  Billing region (addr1): {ft.get('addr1','?')} | Country (addr2): {ft.get('addr2','?')}")
    print(f"  P_emaildomain: {ft.get('P_emaildomain','?')} | R_emaildomain: {ft.get('R_emaildomain','?')}")

    # Identity for flagged txn
    flagged_ident = ident[ident["TransactionID"] == flagged_txn_id]
    if not flagged_ident.empty:
        fi = flagged_ident.iloc[0]
        print(f"\n  Device Profile:")
        print(f"    DeviceType: {fi.get('DeviceType','?')}")
        print(f"    DeviceInfo: {fi.get('DeviceInfo','?')}")
        print(f"    id_15 (New/Found): {fi.get('id_15','?')}")
        print(f"    id_23 (Proxy): {fi.get('id_23','?')}")
        print(f"    id_30 (OS): {fi.get('id_30','?')}")
        print(f"    id_31 (Browser): {fi.get('id_31','?')}")
        print(f"    id_33 (Screen): {fi.get('id_33','?')}")
        print(f"    id_34 (Match): {fi.get('id_34','?')}")
        flagged_device_profile = get_device_profile(fi)
        print(f"    Full profile: {flagged_device_profile}")
    else:
        print(f"\n  No identity record (in_person transaction)")
        flagged_device_profile = None

    # ── Customer History ──────────────────────────────────────────────
    cust_txns = txn[txn["customer_id"] == customer_id].sort_values("ts")
    print(f"\n── Customer History ({customer_id}) ──")
    print(f"  Total transactions: {len(cust_txns)}")
    print(f"  Date range: {cust_txns['ts'].min()} → {cust_txns['ts'].max()}")
    print(f"  Channels: {dict(cust_txns['channel'].value_counts())}")
    print(f"  ProductCDs: {dict(cust_txns['ProductCD'].value_counts())}")

    # Card-level stats
    card_prefix = card_id.split("-")[0]
    card_txns = cust_txns  # all transactions for this customer
    print(f"\n  Typical amounts:")
    print(f"    Mean: ${card_txns['TransactionAmt'].mean():.2f}")
    print(f"    Median: ${card_txns['TransactionAmt'].median():.2f}")
    print(f"    Std: ${card_txns['TransactionAmt'].std():.2f}")
    print(f"    Max: ${card_txns['TransactionAmt'].max():.2f}")

    # Check if flagged amount is unusual
    amt = ft["TransactionAmt"]
    amt_pct = (card_txns["TransactionAmt"] <= amt).mean() * 100
    print(f"    Flagged ${amt:.2f} is at percentile {amt_pct:.1f}%")

    # Billing regions
    regions = card_txns["addr1"].dropna().value_counts()
    print(f"\n  Billing regions used: {dict(regions.head(5))}")
    flagged_region = ft.get("addr1")
    if pd.notna(flagged_region) and flagged_region in regions.index:
        print(f"    Flagged region {flagged_region}: used {regions[flagged_region]} times")
    elif pd.notna(flagged_region):
        print(f"    ⚠ Flagged region {flagged_region}: NEVER USED BEFORE")

    # ── Recent Activity Window (±7 days around flagged) ───────────────
    flagged_ts = ft["ts"]
    window_start = flagged_ts - timedelta(days=7)
    window_end = flagged_ts + timedelta(days=7)
    window = cust_txns[(cust_txns["ts"] >= window_start) & (cust_txns["ts"] <= window_end)]
    print(f"\n── Activity Window (±7 days) ──")
    print(f"  Transactions in window: {len(window)}")
    for _, w in window.iterrows():
        marker = " <<<< FLAGGED" if w["TransactionID"] == flagged_txn_id else ""
        rs_str = f"rs={w['risk_score']:.2f}" if pd.notna(w["risk_score"]) else "rs=?"
        print(f"    {w['ts']}  ${w['TransactionAmt']:>10.2f}  {w['channel']:<10}  {w['ProductCD']}  "
              f"addr1={w.get('addr1','?'):<6}  {rs_str}{marker}")

    # ── Suspicious burst detection (same card, within 48h) ────────────
    print(f"\n── Burst Detection (48h window) ──")
    burst_start = flagged_ts - timedelta(hours=48)
    burst_end = flagged_ts + timedelta(hours=48)
    online_burst = cust_txns[
        (cust_txns["ts"] >= burst_start) &
        (cust_txns["ts"] <= burst_end) &
        (cust_txns["channel"] == "online")
    ]
    if len(online_burst) > 0:
        print(f"  Online txns within 48h of flagged: {len(online_burst)}")
        for _, b in online_burst.iterrows():
            marker = " <<<< FLAGGED" if b["TransactionID"] == flagged_txn_id else ""
            print(f"    {b['ts']}  ${b['TransactionAmt']:>10.2f}  rs={b['risk_score']:.2f}{marker}")
    else:
        print(f"  No online transactions in 48h window")

    # ── Card testing detection (3+ small online txns within 1h) ───────
    print(f"\n── Card Testing Check ──")
    small_online = cust_txns[
        (cust_txns["channel"] == "online") &
        (cust_txns["TransactionAmt"] < 5)
    ].sort_values("ts")
    if len(small_online) >= 3:
        # Check if any 3+ are within 1 hour
        for i in range(len(small_online) - 2):
            if (small_online.iloc[i+2]["ts"] - small_online.iloc[i]["ts"]) <= timedelta(hours=1):
                print(f"  ⚠ CARD TESTING PATTERN: 3+ small online txns within 1h")
                for j in range(i, min(i+5, len(small_online))):
                    print(f"    {small_online.iloc[j]['ts']}  ${small_online.iloc[j]['TransactionAmt']:.2f}")
                break
        else:
            print(f"  No card testing pattern (small online txns exist but not clustered)")
    else:
        print(f"  No card testing pattern (< 3 small online txns)")

    # ── Device analysis ───────────────────────────────────────────────
    print(f"\n── Device Analysis ──")
    cust_online_ids = set(cust_txns[cust_txns["channel"] == "online"]["TransactionID"])
    cust_idents = ident[ident["TransactionID"].isin(cust_online_ids)]
    if not cust_idents.empty:
        devices = cust_idents.apply(get_device_profile, axis=1).value_counts()
        print(f"  Unique device profiles for this customer: {len(devices)}")
        for dev, cnt in devices.head(5).items():
            marker = " <<<< FLAGGED DEVICE" if flagged_device_profile and dev == flagged_device_profile else ""
            print(f"    [{cnt}x] {dev}{marker}")

        # Check if flagged device is new for this customer
        if flagged_device_profile:
            if flagged_device_profile not in devices.index:
                print(f"  ⚠ Flagged device NEVER seen on this customer's account!")
            else:
                # Check if it was first seen recently
                flagged_dev_txns = cust_idents[cust_idents.apply(get_device_profile, axis=1) == flagged_device_profile]
                flagged_dev_txn_ids = flagged_dev_txns["TransactionID"].tolist()
                flagged_dev_dates = txn[txn["TransactionID"].isin(flagged_dev_txn_ids)]["ts"]
                print(f"  Flagged device first seen: {flagged_dev_dates.min()}")
    else:
        print(f"  No identity records for this customer")

    # ── Cross-card device search ──────────────────────────────────────
    if flagged_device_profile and flagged_device_profile != "unknown":
        print(f"\n── Cross-Card Device Search ──")
        # Find all identity records with same DeviceInfo
        if not flagged_ident.empty:
            device_info_val = flagged_ident.iloc[0].get("DeviceInfo")
            if pd.notna(device_info_val):
                same_device = ident[ident["DeviceInfo"] == device_info_val]
                same_device_txn_ids = same_device["TransactionID"].tolist()
                same_device_txns = txn[txn["TransactionID"].isin(same_device_txn_ids)]
                other_customers = same_device_txns[same_device_txns["customer_id"] != customer_id]["customer_id"].unique()
                print(f"  Transactions from same DeviceInfo ({device_info_val}): {len(same_device_txns)}")
                print(f"  Other customers using this device: {list(other_customers[:10])}")
                if len(other_customers) > 0:
                    print(f"  ⚠ SHARED DEVICE — potential ring or compromised device")
            else:
                print(f"  DeviceInfo is null")
    else:
        print(f"\n  Skipping cross-card device search (no device profile)")

    # ── Closed case lookup ────────────────────────────────────────────
    print(f"\n── Similar Closed Cases ──")
    # Same customer
    cust_cases = cc[cc["customer_id"] == customer_id]
    if not cust_cases.empty:
        print(f"  Cases for customer {customer_id}: {len(cust_cases)}")
        for _, c in cust_cases.iterrows():
            print(f"    {c['case_id']}: {c['outcome']} | {c['pattern']} | ${c['exposure_usd']:.2f} | {c['analyst_notes'][:100]}...")
    else:
        print(f"  No closed cases for customer {customer_id}")

    # Same card
    card_cases = cc[cc["card_id"] == card_id]
    if not card_cases.empty:
        print(f"  Cases for card {card_id}: {len(card_cases)}")
        for _, c in card_cases.iterrows():
            print(f"    {c['case_id']}: {c['outcome']} | {c['pattern']} | ${c['exposure_usd']:.2f}")
    else:
        print(f"  No closed cases for card {card_id}")

    # Connected via device
    if flagged_device_profile and flagged_device_profile != "unknown" and not flagged_ident.empty:
        device_info_val = flagged_ident.iloc[0].get("DeviceInfo")
        if pd.notna(device_info_val):
            # Find customers sharing this device
            same_dev_ident = ident[ident["DeviceInfo"] == device_info_val]
            same_dev_txn_ids = same_dev_ident["TransactionID"].tolist()
            same_dev_txns = txn[txn["TransactionID"].isin(same_dev_txn_ids)]
            connected_custs = same_dev_txns["customer_id"].unique()
            connected_cases = cc[cc["customer_id"].isin(connected_custs)]
            if not connected_cases.empty:
                print(f"  Cases connected via shared device ({device_info_val[:40]}...): {len(connected_cases)}")
                for _, c in connected_cases.head(5).iterrows():
                    print(f"    {c['case_id']}: {c['customer_id']} | {c['outcome']} | {c['pattern']} | ${c['exposure_usd']:.2f}")

    # ── Match flag anomalies ──────────────────────────────────────────
    print(f"\n── Match Flag Analysis (M1-M9) ──")
    m_cols = [c for c in txn.columns if c.startswith("M") and c[1:].isdigit()]
    for mc in m_cols:
        val = ft.get(mc)
        if pd.notna(val):
            # Compare to customer baseline
            cust_vals = cust_txns[mc].value_counts(normalize=True)
            if val in cust_vals.index and cust_vals[val] < 0.1:
                print(f"  ⚠ {mc}={val} — unusual for this customer (only {cust_vals[val]*100:.1f}% of their txns)")
            elif val not in cust_vals.index:
                print(f"  ⚠ {mc}={val} — NEVER seen on this customer")

    # ── V-feature outliers (simplified) ───────────────────────────────
    print(f"\n── Risk-relevant V-features ──")
    v_cols = [c for c in txn.columns if c.startswith("V") and c[1:].isdigit()]
    for vc in v_cols[:20]:  # sample first 20
        val = ft.get(vc)
        if pd.notna(val):
            cust_mean = cust_txns[vc].mean()
            cust_std = cust_txns[vc].std()
            if cust_std > 0 and abs(val - cust_mean) > 3 * cust_std:
                print(f"  ⚠ {vc}={val:.2f} — {abs(val-cust_mean)/cust_std:.1f}σ from customer mean")

    print(f"\n{'='*80}\n")


def main():
    cases = sys.argv[1:]
    if not cases:
        print("Usage: python scripts/investigate_case.py HHG-003 HHG-010", file=sys.stderr)
        sys.exit(1)

    txn, ident, cc, cp = load_data()

    for case_id in cases:
        if case_id not in cp["case_id"].values:
            print(f"⚠ {case_id} not in case_pack.csv!", file=sys.stderr)
            continue
        investigate(case_id, txn, ident, cc, cp)


if __name__ == "__main__":
    main()
