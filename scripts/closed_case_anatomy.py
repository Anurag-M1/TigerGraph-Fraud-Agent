#!/usr/bin/env python3
"""Phase 0 – Closed-case anatomy from closed_cases_history.csv.
Writes docs/closed_case_anatomy.md.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import io, sys

DATA = Path("Dataset")
OUT = Path("docs/closed_case_anatomy.md")

def main():
    md = io.StringIO()
    w = lambda s="": print(s, file=md)

    cc = pd.read_csv(DATA / "closed_cases_history.csv")

    w("# Closed-Case Anatomy — HHGOA_IEEE")
    w()
    w(f"**Source**: `closed_cases_history.csv` — {len(cc):,} cases, July–October 2016")
    w()

    # ── 1. Pattern Distribution ─────────────────────────────────────────
    w("## 1. Pattern Distribution")
    w()
    w("| Pattern | Count | % |")
    w("|---|---|---|")
    for k, v in cc["pattern"].value_counts().items():
        w(f"| `{k}` | {v:,} | {100*v/len(cc):.1f}% |")
    w()

    # ── 2. Outcome × Pattern Matrix ─────────────────────────────────────
    w("## 2. Outcome × Pattern Matrix")
    w()
    ct = pd.crosstab(cc["outcome"], cc["pattern"])
    cols = sorted(ct.columns)
    w("| Outcome | " + " | ".join(f"`{c}`" for c in cols) + " | **Total** |")
    w("|---" * (len(cols) + 2) + "|")
    for idx in ct.index:
        vals = " | ".join(str(ct.loc[idx, c]) if c in ct.columns else "0" for c in cols)
        w(f"| `{idx}` | {vals} | **{ct.loc[idx].sum()}** |")
    w()

    # ── 3. Exposure Distribution per Outcome ────────────────────────────
    w("## 3. Exposure Distribution per Outcome")
    w()
    w("| Outcome | Count | Min | P25 | Median | P75 | Max | Mean |")
    w("|---|---|---|---|---|---|---|---|")
    for outcome in ["confirmed_fraud", "cleared"]:
        sub = cc[cc["outcome"] == outcome]["exposure_usd"]
        if len(sub) == 0:
            continue
        w(f"| `{outcome}` | {len(sub):,} | ${sub.min():,.2f} | ${sub.quantile(0.25):,.2f} | "
          f"${sub.median():,.2f} | ${sub.quantile(0.75):,.2f} | ${sub.max():,.2f} | ${sub.mean():,.2f} |")
    w()

    # ── 4. Exposure distribution for confirmed fraud by pattern ─────────
    w("## 4. Exposure by Fraud Pattern")
    w()
    w("| Pattern | Cases | Median $ | Mean $ | Max $ |")
    w("|---|---|---|---|---|")
    fraud = cc[cc["outcome"] == "confirmed_fraud"]
    for pat, grp in fraud.groupby("pattern"):
        e = grp["exposure_usd"]
        w(f"| `{pat}` | {len(grp):,} | ${e.median():,.2f} | ${e.mean():,.2f} | ${e.max():,.2f} |")
    w()

    # ── 5. actions_taken Vocabulary ─────────────────────────────────────
    w("## 5. `actions_taken` Vocabulary")
    w()
    # Actions are pipe-separated within each cell
    all_actions = []
    for val in cc["actions_taken"].dropna():
        all_actions.extend(str(val).split("|"))
    action_counts = pd.Series(all_actions).value_counts()
    w("| Action | Frequency |")
    w("|---|---|")
    for k, v in action_counts.items():
        w(f"| `{k}` | {v:,} |")
    w()

    # Unique action combos
    w("### Action Combinations (top 10)")
    w()
    combo_counts = cc["actions_taken"].value_counts().head(10)
    w("| Combo | Count |")
    w("|---|---|")
    for k, v in combo_counts.items():
        w(f"| `{k}` | {v:,} |")
    w()

    # ── 6. report_filed vs (outcome, exposure) ─────────────────────────
    w("## 6. `report_filed` Analysis")
    w()
    w("### report_filed by Outcome")
    w()
    rf_ct = pd.crosstab(cc["outcome"], cc["report_filed"])
    cols_rf = sorted(rf_ct.columns)
    w("| Outcome | " + " | ".join(f"`{c}`" for c in cols_rf) + " |")
    w("|---" * (len(cols_rf) + 1) + "|")
    for idx in rf_ct.index:
        vals = " | ".join(str(rf_ct.loc[idx, c]) for c in cols_rf)
        w(f"| `{idx}` | {vals} |")
    w()

    # report_filed=Yes: what's the exposure threshold?
    filed_yes = cc[(cc["report_filed"] == "Yes") & (cc["outcome"] == "confirmed_fraud")]
    filed_no = cc[(cc["report_filed"] == "No") & (cc["outcome"] == "confirmed_fraud")]
    w("### Exposure threshold for report filing (confirmed_fraud only)")
    w()
    if len(filed_yes):
        w(f"- Filed Yes: {len(filed_yes)} cases, exposure min=${filed_yes['exposure_usd'].min():,.2f}, "
          f"median=${filed_yes['exposure_usd'].median():,.2f}, mean=${filed_yes['exposure_usd'].mean():,.2f}")
    if len(filed_no):
        w(f"- Filed No: {len(filed_no)} cases, exposure min=${filed_no['exposure_usd'].min():,.2f}, "
          f"median=${filed_no['exposure_usd'].median():,.2f}, mean=${filed_no['exposure_usd'].mean():,.2f}")
    w()

    # report_filed by pattern
    w("### report_filed by Pattern (confirmed_fraud only)")
    w()
    rf_pat = pd.crosstab(fraud["pattern"], fraud["report_filed"])
    cols_rfp = sorted(rf_pat.columns)
    w("| Pattern | " + " | ".join(f"`{c}`" for c in cols_rfp) + " |")
    w("|---" * (len(cols_rfp) + 1) + "|")
    for idx in rf_pat.index:
        vals = " | ".join(str(rf_pat.loc[idx, c]) if c in rf_pat.columns else "0" for c in cols_rfp)
        w(f"| `{idx}` | {vals} |")
    w()

    # ── 7. connected_card_ids analysis ──────────────────────────────────
    w("## 7. Connected Cards Analysis")
    w()
    has_connected = fraud["connected_card_ids"].notna() & (fraud["connected_card_ids"] != "")
    w(f"- Fraud cases with connected cards: {has_connected.sum()} / {len(fraud)} ({100*has_connected.sum()/len(fraud):.1f}%)")
    if has_connected.sum() > 0:
        connected_counts = fraud.loc[has_connected, "connected_card_ids"].apply(
            lambda x: len(str(x).split("|")) if pd.notna(x) else 0)
        w(f"- Connected cards per case: median={connected_counts.median():.0f}, max={connected_counts.max():.0f}")
    w()

    # ── 8. 10 sample analyst_notes for "undocumented" cases ─────────────
    w("## 8. Undocumented Pattern Cases — Analyst Notes (verbatim)")
    w()
    undoc = cc[cc["pattern"] == "undocumented"]
    w(f"**Total undocumented cases**: {len(undoc)}")
    w()
    samples = undoc.head(10)
    for i, (_, row) in enumerate(samples.iterrows(), 1):
        w(f"### Case {i}: `{row['case_id']}` — {row['outcome']} — ${row['exposure_usd']:,.2f}")
        w()
        w(f"> {row['analyst_notes']}")
        w()
        w(f"- **Card**: `{row['card_id']}` | **Customer**: `{row['customer_id']}`")
        w(f"- **Txns**: {row['n_txns']} | **Actions**: `{row['actions_taken']}`")
        w(f"- **Report filed**: {row['report_filed']}")
        if pd.notna(row.get("connected_card_ids")) and row["connected_card_ids"]:
            w(f"- **Connected cards**: `{row['connected_card_ids']}`")
        w()

    # ── 9. Date ranges ──────────────────────────────────────────────────
    w("## 9. Date Ranges")
    w()
    w(f"- **opened_at**: `{cc['opened_at'].min()}` → `{cc['opened_at'].max()}`")
    w(f"- **closed_at**: `{cc['closed_at'].min()}` → `{cc['closed_at'].max()}`")
    w()

    w("---")
    w("*Generated by `scripts/closed_case_anatomy.py`*")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md.getvalue(), encoding="utf-8")
    print(f"\n✓ Wrote {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
