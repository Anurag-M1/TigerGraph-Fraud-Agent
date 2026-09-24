#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 5: Investigation Runner & Case Pack Orchestration
=============================================================================
Orchestrates running the LangGraph fraud investigation agent across:
- A single alert case (e.g. HHG-003 or HHG-010)
- All 20 alerts in Dataset/case_pack.csv
- Emits schema-compliant answer files into cases/<case_id>.json
=============================================================================
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.graph_agent import FraudInvestigationAgent

CASE_PACK_CSV = PROJECT_ROOT / "Dataset" / "case_pack.csv"
CASES_DIR = PROJECT_ROOT / "cases"
CASES_DIR.mkdir(parents=True, exist_ok=True)


class CaseRunner:
    """Manages execution and emission of case answer files."""

    def __init__(self):
        self.agent = FraudInvestigationAgent()

    def run_single_case(self, case_record: Dict[str, Any], save: bool = True) -> Dict[str, Any]:
        """Run investigation for a single alert record and optionally save to cases/<case_id>.json."""
        case_id = case_record["case_id"]
        print(f"\n[Runner] Investigating {case_id} (Trigger: {case_record.get('trigger_type')})...")
        t0 = time.time()

        answer = self.agent.run(case_record)
        elapsed = time.time() - t0

        if save:
            out_file = CASES_DIR / f"{case_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(answer, f, indent=2)
            print(f"[Runner] Saved {out_file} ({elapsed:.2f}s, {answer['tool_calls']} tool calls)")

        return answer

    def run_all_case_pack(self, case_pack_path: Path = CASE_PACK_CSV) -> List[Dict[str, Any]]:
        """Run all 20 alerts from case pack and emit 20 answer files into cases/."""
        df = pd.read_csv(case_pack_path)
        print(f"\n{'=' * 80}")
        print(f"  RUNNING AUTONOMOUS INVESTIGATION AGENT ACROSS ALL {len(df)} ALERT CASES")
        print(f"{'=' * 80}")

        results = []
        t_global = time.time()

        for idx, row in df.iterrows():
            record = row.to_dict()
            ans = self.run_single_case(record, save=True)
            results.append(ans)

        total_elapsed = time.time() - t_global
        avg_latency = total_elapsed / len(df)
        total_tools = sum(r.get("tool_calls", 0) for r in results)
        fraud_count = sum(1 for r in results if r["case"]["verdict"] == "fraud")
        legit_count = sum(1 for r in results if r["case"]["verdict"] == "legitimate")
        sar_count = sum(1 for r in results if r["sar"]["file"])

        print(f"\n{'=' * 80}")
        print(f"  BATCH INVESTIGATION COMPLETE: {len(df)} CASES")
        print(f"{'=' * 80}")
        print(f"  Total Duration:     {total_elapsed:.2f}s (Avg: {avg_latency:.2f}s / case)")
        print(f"  Total Tool Calls:   {total_tools}")
        print(f"  Fraud Verdicts:     {fraud_count}")
        print(f"  Legitimate Verdicts:{legit_count}")
        print(f"  SARs Filed:         {sar_count}")
        print(f"  Outputs Saved:      {CASES_DIR}/<case_id>.json")
        print(f"{'=' * 80}\n")

        return results


def run_case(case_id: str):
    """Convenience helper to run a specific case by ID."""
    df = pd.read_csv(CASE_PACK_CSV)
    row = df[df["case_id"] == case_id]
    if row.empty:
        raise ValueError(f"Case {case_id} not found in {CASE_PACK_CSV}")
    runner = CaseRunner()
    return runner.run_single_case(row.iloc[0].to_dict(), save=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_case(sys.argv[1])
    else:
        runner = CaseRunner()
        runner.run_all_case_pack()
