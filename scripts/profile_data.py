#!/usr/bin/env python3
"""Phase 0 – Data profiling across all 4 CSVs.
Writes docs/profiling.md with structured findings.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys, io

DATA = Path("Dataset")
OUT = Path("docs/profiling.md")

def pct(n, total):
    return f"{n:,} ({100*n/total:.1f}%)" if total else "0"

def null_report(df, cols, label):
    lines = [f"| Column | Null count | Null % | Non-null unique |",
             f"|---|---|---|---|"]
    for c in cols:
        if c in df.columns:
            nn = df[c].isna().sum()
            lines.append(f"| `{c}` | {nn:,} | {100*nn/len(df):.1f}% | {df[c].nunique():,} |")
        else:
            lines.append(f"| `{c}` | *column not found* | — | — |")
    return "\n".join(lines)

def main():
    md = io.StringIO()
    w = lambda s="": print(s, file=md)

    w("# Data Profile — HHGOA_IEEE")
    w()

    # ── 1. Row / column counts ──────────────────────────────────────────
    w("## 1. File Dimensions")
    w()
    w("| File | Rows | Columns | Size |")
    w("|---|---|---|---|")
    for name in ["transactions.csv", "identity.csv", "closed_cases_history.csv", "case_pack.csv"]:
        p = DATA / name
        size_mb = p.stat().st_size / 1e6
        # fast row count
        with open(p, "r") as f:
            n_lines = sum(1 for _ in f) - 1
        with open(p, "r") as f:
            n_cols = len(f.readline().split(","))
        w(f"| `{name}` | {n_lines:,} | {n_cols} | {size_mb:.1f} MB |")
    w()

    # ── 2. transactions.csv deep profile ────────────────────────────────
    w("## 2. Transactions Profile")
    w()
    print("  Loading transactions.csv ...", file=sys.stderr)
    txn = pd.read_csv(DATA / "transactions.csv", low_memory=False)
    w(f"- **Rows**: {len(txn):,}")
    w(f"- **Customers**: {txn['customer_id'].nunique():,}")
    w(f"- **Unique cards** (card1): {txn['card1'].nunique():,}")
    w(f"- **Date range**: `{txn['ts'].min()}` → `{txn['ts'].max()}`")
    w()

    # Channel split
    w("### Channel Split")
    w()
    ch = txn["channel"].value_counts()
    for k, v in ch.items():
        w(f"- `{k}`: {pct(v, len(txn))}")
    w()

    # ProductCD distribution
    w("### ProductCD Distribution")
    w()
    w("| ProductCD | Count | % |")
    w("|---|---|---|")
    for k, v in txn["ProductCD"].value_counts().items():
        w(f"| `{k}` | {v:,} | {100*v/len(txn):.1f}% |")
    w()

    # Null rates on key columns
    w("### Key Column Null Rates (transactions)")
    w()
    key_cols_txn = ["addr1", "addr2", "dist1", "dist2",
                    "P_emaildomain", "R_emaildomain", "risk_score"]
    w(null_report(txn, key_cols_txn, "transactions"))
    w()

    # risk_score distribution
    w("### Risk Score Distribution")
    w()
    rs = txn["risk_score"].dropna()
    w(f"- **Non-null**: {len(rs):,} / {len(txn):,} ({100*len(rs)/len(txn):.1f}%)")
    w(f"- **Mean**: {rs.mean():.4f}  **Median**: {rs.median():.4f}")
    w(f"- **Std**: {rs.std():.4f}  **Min**: {rs.min():.4f}  **Max**: {rs.max():.4f}")
    w()
    w("#### Decile Histogram")
    w()
    w("| Bucket | Count | % |")
    w("|---|---|---|")
    bins = np.arange(0, 1.1, 0.1)
    labels = [f"{bins[i]:.1f}–{bins[i+1]:.1f}" for i in range(len(bins)-1)]
    cuts = pd.cut(rs, bins=bins, labels=labels, right=False, include_lowest=True)
    for lbl in labels:
        cnt = (cuts == lbl).sum()
        w(f"| {lbl} | {cnt:,} | {100*cnt/len(rs):.1f}% |")
    w()

    # Precision proxy above 0.7 using closed cases
    w("### Precision Proxy: risk_score > 0.7 vs Closed Cases")
    w()
    print("  Loading closed_cases_history.csv ...", file=sys.stderr)
    cc = pd.read_csv(DATA / "closed_cases_history.csv")
    # Expand txn_ids
    fraud_txn_ids = set()
    for _, row in cc[cc["outcome"] == "confirmed_fraud"].iterrows():
        if pd.notna(row["txn_ids"]):
            fraud_txn_ids.update(str(row["txn_ids"]).split("|"))
    cleared_txn_ids = set()
    for _, row in cc[cc["outcome"] == "cleared"].iterrows():
        if pd.notna(row["txn_ids"]):
            cleared_txn_ids.update(str(row["txn_ids"]).split("|"))

    high_rs = txn[txn["risk_score"] > 0.7]
    high_rs_ids = set(high_rs["TransactionID"].astype(str))
    tp = len(high_rs_ids & fraud_txn_ids)
    fp = len(high_rs_ids & cleared_txn_ids)
    w(f"- Transactions with `risk_score > 0.7`: **{len(high_rs):,}**")
    w(f"- Of those, in confirmed_fraud closed cases: **{tp}**")
    w(f"- Of those, in cleared closed cases: **{fp}**")
    if tp + fp > 0:
        w(f"- **Precision proxy** (among those with a closed-case label): {100*tp/(tp+fp):.1f}%")
    w(f"- Remaining {len(high_rs) - tp - fp:,} high-score txns have no closed-case label (Nov–Dec exam period)")
    w()

    # addr2 == 87 (home country)
    w("### Billing Country (addr2)")
    w()
    a2 = txn["addr2"].dropna()
    home = (a2 == 87.0).sum()
    w(f"- Home country (addr2=87): {pct(home, len(a2))}")
    w(f"- Other countries: {pct(len(a2) - home, len(a2))}")
    w()

    # ── 3. identity.csv profile ─────────────────────────────────────────
    w("## 3. Identity Profile")
    w()
    print("  Loading identity.csv ...", file=sys.stderr)
    ident = pd.read_csv(DATA / "identity.csv", low_memory=False)
    w(f"- **Rows**: {len(ident):,}")
    w()
    key_cols_id = ["DeviceType", "DeviceInfo", "id_15", "id_23",
                   "id_30", "id_31", "id_33", "id_34"]
    w("### Key Column Null Rates (identity)")
    w()
    w(null_report(ident, key_cols_id, "identity"))
    w()

    # DeviceType distribution
    w("### DeviceType Distribution")
    w()
    for k, v in ident["DeviceType"].value_counts(dropna=False).head(5).items():
        w(f"- `{k}`: {v:,}")
    w()

    # id_15 (New / Found)
    w("### id_15 (Device New/Found)")
    w()
    for k, v in ident["id_15"].value_counts(dropna=False).head(5).items():
        w(f"- `{k}`: {v:,}")
    w()

    # Join coverage
    w("### Identity Join Coverage")
    w()
    online_txns = txn[txn["channel"] == "online"]
    joined = online_txns["TransactionID"].isin(ident["TransactionID"])
    w(f"- Online transactions: {len(online_txns):,}")
    w(f"- With identity record: {pct(joined.sum(), len(online_txns))}")
    w(f"- Without identity record: {pct((~joined).sum(), len(online_txns))}")
    w()

    # ── 4. case_pack summary ────────────────────────────────────────────
    w("## 4. Case Pack Summary")
    w()
    cp = pd.read_csv(DATA / "case_pack.csv")
    w(f"- **Cases**: {len(cp)}")
    w(f"- **Date range**: `{cp['opened_at'].min()}` → `{cp['opened_at'].max()}`")
    w()
    w("### Trigger Type Distribution")
    w()
    for k, v in cp["trigger_type"].value_counts().items():
        w(f"- `{k}`: {v}")
    w()

    w("---")
    w("*Generated by `scripts/profile_data.py`*")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md.getvalue(), encoding="utf-8")
    print(f"\n✓ Wrote {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
