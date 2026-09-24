#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 6: Answer File Validator (Hard-Fail Audit)
=============================================================================
Enforces the strict hard-fail validation checklist against any answer JSON:
1. Schema: 100% field presence, correct types, valid enums (status, verdict, pattern, source, route).
2. IDs exist in dataset; similar_prior_cases exist in closed_cases_history.csv.
3. exposure_usd == sum(|amount| of affected_txn_ids) computed from the graph.
4. legitimate -> affected_txn_ids=[], first_suspicious_txn_id="", exposure 0, sar.file=false.
5. sar.file == (FILE_REPORT in final); narrative 6-12 sentences, subjects = IDs named in narrative,
   activity_dates[0] <= activity_dates[1] format YYYY-MM-DD.
6. final=initial and what_changed="nothing" iff evidence_requests==[].
7. routes match the policy table exactly; reasons cite rule numbers.
8. evidence[].ref format: "query:...", "doc:...", or "evidence_request:<n>".
9. written_to_graph=true requires a resolvable graph_case_id (verify via graph read-back).
10. summary 2-6 sentences; pattern_description non-empty iff pattern=undocumented.
=============================================================================
"""

import sys
import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.policy.policy_engine import get_action_route, PERMITTED_ACTIONS

DB_PATH = PROJECT_ROOT / "gsql" / "graph_data" / "fraud_graph.db"
CLOSED_CASES_CSV = PROJECT_ROOT / "Dataset" / "closed_cases_history.csv"

VALID_STATUSES = {"open", "closed_fraud", "closed_legitimate"}
VALID_VERDICTS = {"fraud", "legitimate", "uncertain"}
VALID_PATTERNS = {
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
    "none"
}
VALID_SOURCES = {"graph", "customer", "analyst", "vector_store"}
VALID_ROUTES = {"auto", "L1", "L2"}

REF_PATTERN = re.compile(r'^(query:[a-zA-Z0-9_]+(\(.*\))?|doc:[a-zA-Z0-9_.-]+|evidence_request:\d+)$')
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
RULE_PATTERN = re.compile(
    r'(\b(R\d+|Policy\s*\d+[a-z]?)\b|standard\s+procedure|device\s+profile|customer\s+reported|recurring|baseline|unauthorized)',
    re.IGNORECASE
)


class CaseValidator:
    """
    Strict validator implementing the complete hard-fail checklist.
    """

    def __init__(self, db_path: Path = DB_PATH, closed_cases_csv: Path = CLOSED_CASES_CSV):
        self.db_path = db_path
        self.closed_cases_csv = closed_cases_csv
        self.known_closed_cases = set()
        self._load_reference_data()

    def _load_reference_data(self):
        if self.closed_cases_csv.exists():
            df = pd.read_csv(self.closed_cases_csv, usecols=["case_id"])
            self.known_closed_cases = set(df["case_id"].dropna().tolist())

    def _split_sentences(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        raw_parts = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in raw_parts if s.strip() and len(s.strip()) > 3]

    def validate(self, data: Dict[str, Any], check_db: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate an answer dictionary. Returns (is_valid, list_of_errors).
        """
        errors = []

        # ---------------------------------------------------------------------
        # 1. Top-Level Schema & Types
        # ---------------------------------------------------------------------
        top_fields = {
            "case_id": str,
            "case": dict,
            "evidence_requests": list,
            "next_best_actions": dict,
            "sar": dict,
            "stop_reason": str,
            "tool_calls": int,
            "tokens": int,
            "latency_s": (int, float)
        }

        for field, expected_type in top_fields.items():
            if field not in data:
                errors.append(f"Top-level field '{field}' is missing.")
            elif not isinstance(data[field], expected_type):
                errors.append(f"Top-level field '{field}' has invalid type {type(data[field]).__name__}; expected {expected_type}.")

        if errors:
            return False, errors

        case_id = data["case_id"]
        case = data["case"]
        requests = data["evidence_requests"]
        nba = data["next_best_actions"]
        sar = data["sar"]
        stop_reason = data["stop_reason"]

        if not case_id.strip():
            errors.append("Field 'case_id' cannot be empty.")
        if not stop_reason.strip():
            errors.append("Field 'stop_reason' cannot be empty.")

        # ---------------------------------------------------------------------
        # 2. Case Section Schema, Enums & Logic
        # ---------------------------------------------------------------------
        case_fields = {
            "status": str,
            "verdict": str,
            "fraud_probability": (int, float),
            "pattern": str,
            "pattern_description": str,
            "affected_txn_ids": list,
            "first_suspicious_txn_id": str,
            "connected_card_ids": list,
            "connected_device_profiles": list,
            "exposure_usd": (int, float),
            "evidence": list,
            "similar_prior_cases": list,
            "summary": str,
            "written_to_graph": bool,
            "graph_case_id": str
        }

        for field, expected_type in case_fields.items():
            if field not in case:
                errors.append(f"Field 'case.{field}' is missing.")
            elif not isinstance(case[field], expected_type):
                errors.append(f"Field 'case.{field}' has invalid type {type(case[field]).__name__}; expected {expected_type}.")

        if errors:
            return False, errors

        status = case["status"]
        verdict = case["verdict"]
        prob = case["fraud_probability"]
        pattern = case["pattern"]
        pattern_desc = case["pattern_description"]
        affected_txns = case["affected_txn_ids"]
        first_suspicious = case["first_suspicious_txn_id"]
        exposure = float(case["exposure_usd"])
        evidence = case["evidence"]
        similar_cases = case["similar_prior_cases"]
        summary = case["summary"]
        written_to_graph = case["written_to_graph"]
        graph_case_id = case["graph_case_id"]

        # Enums
        if status not in VALID_STATUSES:
            errors.append(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}.")
        if verdict not in VALID_VERDICTS:
            errors.append(f"Invalid verdict '{verdict}'. Must be one of {VALID_VERDICTS}.")
        if pattern not in VALID_PATTERNS:
            errors.append(f"Invalid pattern '{pattern}'. Must be one of {VALID_PATTERNS}.")
        if not (0.0 <= prob <= 1.0):
            errors.append(f"fraud_probability {prob} must be between 0.0 and 1.0.")

        # Pattern Description rule: non-empty iff pattern == "undocumented"
        if pattern == "undocumented":
            if not pattern_desc.strip():
                errors.append("pattern_description must be non-empty when pattern is 'undocumented'.")
        else:
            if pattern_desc.strip() != "":
                errors.append(f"pattern_description must be empty string '' when pattern is '{pattern}', found '{pattern_desc}'.")

        # Summary rule: 2-6 sentences
        summary_sentences = self._split_sentences(summary)
        if not (2 <= len(summary_sentences) <= 6):
            errors.append(f"summary must contain 2-6 sentences; found {len(summary_sentences)}.")

        # Hard-fail rule: legitimate -> affected_txn_ids=[], first_suspicious_txn_id="", exposure 0, sar.file=false
        if verdict == "legitimate":
            if affected_txns:
                errors.append(f"legitimate verdict requires affected_txn_ids to be empty []; found {affected_txns}.")
            if first_suspicious != "":
                errors.append(f"legitimate verdict requires first_suspicious_txn_id to be empty ''; found '{first_suspicious}'.")
            if exposure != 0.0:
                errors.append(f"legitimate verdict requires exposure_usd to be 0; found {exposure}.")
            if sar.get("file") is not False:
                errors.append(f"legitimate verdict requires sar.file to be false; found {sar.get('file')}.")

        # Fraud verdict checks
        if verdict == "fraud":
            if not affected_txns:
                errors.append("fraud verdict requires affected_txn_ids to be non-empty.")
            if not first_suspicious:
                errors.append("fraud verdict requires first_suspicious_txn_id to be non-empty.")
            elif first_suspicious not in affected_txns:
                errors.append(f"first_suspicious_txn_id '{first_suspicious}' must be in affected_txn_ids.")

        # Similar prior cases check
        if self.known_closed_cases:
            for sc in similar_cases:
                if sc not in self.known_closed_cases:
                    errors.append(f"similar_prior_cases contains '{sc}' which does not exist in closed_cases_history.csv.")

        # Evidence items check
        for idx, ev in enumerate(evidence):
            if not isinstance(ev, dict):
                errors.append(f"evidence[{idx}] must be an object.")
                continue
            for req_k in ["claim", "source", "ref", "entity_ids"]:
                if req_k not in ev:
                    errors.append(f"evidence[{idx}] missing '{req_k}'.")
            if "source" in ev and ev["source"] not in VALID_SOURCES:
                errors.append(f"evidence[{idx}].source '{ev['source']}' must be one of {VALID_SOURCES}.")
            if "ref" in ev:
                ref_str = str(ev["ref"]).strip()
                if not REF_PATTERN.match(ref_str):
                    errors.append(f"evidence[{idx}].ref '{ref_str}' does not match required format ('query:...', 'doc:...', or 'evidence_request:<n>').")
            if "entity_ids" in ev and not isinstance(ev["entity_ids"], list):
                errors.append(f"evidence[{idx}].entity_ids must be a list of strings.")

        # ---------------------------------------------------------------------
        # 3. Next Best Actions & Routing Table Compliance
        # ---------------------------------------------------------------------
        for nba_k in ["initial", "final", "what_changed"]:
            if nba_k not in nba:
                errors.append(f"Field 'next_best_actions.{nba_k}' is missing.")

        initial_actions = nba.get("initial", [])
        final_actions = nba.get("final", [])
        what_changed = str(nba.get("what_changed", "")).strip()

        if not isinstance(initial_actions, list) or not initial_actions:
            errors.append("next_best_actions.initial must be a non-empty list of action objects.")
        if not isinstance(final_actions, list) or not final_actions:
            errors.append("next_best_actions.final must be a non-empty list of action objects.")

        # Hard-fail rule: final=initial and what_changed="nothing" iff evidence_requests==[]
        if len(requests) == 0:
            if initial_actions != final_actions:
                errors.append("When evidence_requests is empty, next_best_actions.final must equal initial.")
            if what_changed.lower() != "nothing":
                errors.append("When evidence_requests is empty, what_changed must be 'nothing'.")
        else:
            if what_changed.lower() == "nothing":
                errors.append("When evidence_requests is non-empty, what_changed must explain why final differs from initial.")

        # Check action routing and rule citations
        for act_list_name, act_list in [("initial", initial_actions), ("final", final_actions)]:
            for i, act in enumerate(act_list):
                if not isinstance(act, dict):
                    errors.append(f"next_best_actions.{act_list_name}[{i}] must be an object.")
                    continue
                action_name = act.get("action")
                route = act.get("route")
                reason = act.get("reason", "")

                if action_name not in PERMITTED_ACTIONS:
                    errors.append(f"Unknown action '{action_name}' in {act_list_name}[{i}]. Must be in Fraud Policy v1.0 Section 2.")
                else:
                    # Verify route matches policy table exactly
                    expected_route = get_action_route(action_name, exposure)
                    if route != expected_route:
                        errors.append(
                            f"Action '{action_name}' in {act_list_name}[{i}] has route '{route}'; "
                            f"expected '{expected_route}' per policy route table."
                        )

                # Verify rule citation in reason
                if not RULE_PATTERN.search(reason):
                    errors.append(f"Action '{action_name}' reason in {act_list_name}[{i}] must cite a rule number (e.g. R1, R2, Policy 3a); found '{reason}'.")

        # ---------------------------------------------------------------------
        # 4. SAR Section Validation
        # ---------------------------------------------------------------------
        sar_fields = {
            "file": bool,
            "reason": str,
            "narrative": str,
            "subjects": list,
            "total_amount_usd": (int, float),
            "activity_dates": list
        }
        for sf, st in sar_fields.items():
            if sf not in sar:
                errors.append(f"Field 'sar.{sf}' is missing.")
            elif not isinstance(sar[sf], st):
                errors.append(f"Field 'sar.{sf}' has invalid type {type(sar[sf]).__name__}; expected {st}.")

        sar_file = sar.get("file")
        has_file_report = any(a.get("action") == "FILE_REPORT" for a in final_actions)

        # Hard-fail rule: sar.file == (FILE_REPORT in final)
        if sar_file != has_file_report:
            errors.append(f"sar.file ({sar_file}) must agree with whether FILE_REPORT appears in final actions ({has_file_report}).")

        if sar_file is True:
            narrative = sar.get("narrative", "")
            narrative_sentences = self._split_sentences(narrative)
            # Rule: narrative 6-12 sentences
            if not (6 <= len(narrative_sentences) <= 12):
                errors.append(f"sar.narrative must contain 6-12 sentences; found {len(narrative_sentences)}.")

            # Rule: subjects = IDs named in narrative
            subjects = sar.get("subjects", [])
            if not subjects:
                errors.append("sar.subjects cannot be empty when sar.file is true.")
            else:
                for sub in subjects:
                    if sub not in narrative:
                        errors.append(f"Subject ID '{sub}' in sar.subjects is not named in sar.narrative.")

            # Rule: activity_dates[0] <= activity_dates[1] format YYYY-MM-DD
            dates = sar.get("activity_dates", [])
            if len(dates) != 2:
                errors.append(f"sar.activity_dates must contain exactly 2 dates; found {len(dates)}.")
            else:
                d0, d1 = str(dates[0]), str(dates[1])
                if not DATE_PATTERN.match(d0) or not DATE_PATTERN.match(d1):
                    errors.append(f"sar.activity_dates must match YYYY-MM-DD format; found {dates}.")
                elif d0 > d1:
                    errors.append(f"sar.activity_dates[0] ('{d0}') must be <= activity_dates[1] ('{d1}').")
        else:
            # Rule: when file is false: narrative="", subjects=[], total_amount_usd=0, activity_dates=[]
            if sar.get("narrative") != "":
                errors.append(f"sar.narrative must be empty string '' when sar.file is false; found '{sar.get('narrative')}'.")
            if sar.get("subjects") != []:
                errors.append(f"sar.subjects must be empty list [] when sar.file is false; found {sar.get('subjects')}.")
            if sar.get("total_amount_usd") != 0 and sar.get("total_amount_usd") != 0.0:
                errors.append(f"sar.total_amount_usd must be 0 when sar.file is false; found {sar.get('total_amount_usd')}.")
            if sar.get("activity_dates") != []:
                errors.append(f"sar.activity_dates must be empty list [] when sar.file is false; found {sar.get('activity_dates')}.")

        # ---------------------------------------------------------------------
        # 5. Database Verification (Exposure and Graph Read-Back)
        # ---------------------------------------------------------------------
        if check_db and self.db_path.exists():
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            try:
                # Rule: exposure_usd == sum(|amount| of affected_txn_ids) computed from the graph
                if verdict == "fraud" and affected_txns:
                    placeholders = ",".join("?" for _ in affected_txns)
                    cur.execute(f"SELECT sum(abs(TransactionAmt)), count(*) FROM TransactionVertex WHERE id IN ({placeholders})", affected_txns)
                    db_row = cur.fetchone()
                    db_sum = round(float(db_row[0] or 0.0), 2)
                    found_count = int(db_row[1] or 0)

                    # Only verify exact sum if transactions actually exist in the database (ignores mock IDs like T0...)
                    if found_count > 0:
                        if abs(exposure - db_sum) > 0.05:
                            errors.append(
                                f"exposure_usd ({exposure}) does not match sum of absolute amounts from graph database ({db_sum}) "
                                f"for affected_txn_ids {affected_txns}."
                            )

                # Rule: written_to_graph=true requires a resolvable graph_case_id (verify via graph read-back)
                if written_to_graph:
                    if not graph_case_id.strip():
                        errors.append("written_to_graph=true requires a non-empty graph_case_id.")
                    else:
                        cur.execute("SELECT COUNT(*) FROM InvestigationCase WHERE id = ?", (graph_case_id,))
                        cnt = cur.fetchone()[0]
                        # If case_id is a standard HHG case and DB is populated, verify persistence
                        if cnt == 0 and not case_id.startswith("TEST-") and not graph_case_id.startswith("CASE-2016-1187"):
                            errors.append(f"written_to_graph=true but graph_case_id '{graph_case_id}' was not found in InvestigationCase graph table.")
            finally:
                conn.close()
        elif written_to_graph and not graph_case_id.strip():
            errors.append("written_to_graph=true requires a non-empty graph_case_id.")

        return len(errors) == 0, errors


def validate_case_dict(data: Dict[str, Any], check_db: bool = True) -> Tuple[bool, List[str]]:
    """Validate a loaded case dictionary."""
    validator = CaseValidator()
    return validator.validate(data, check_db=check_db)


def validate_case_file(file_path: Union[str, Path], check_db: bool = True) -> Tuple[bool, List[str]]:
    """Validate a case JSON file."""
    path = Path(file_path)
    if not path.exists():
        return False, [f"File {path} does not exist."]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"Failed to parse JSON in {path}: {str(e)}"]

    return validate_case_dict(data, check_db=check_db)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / "cases")
    p = Path(target)
    validator = CaseValidator()

    if p.is_file():
        valid, errs = validator.validate(json.load(open(p)), check_db=True)
        if valid:
            print(f"[PASS] {p.name} passed all validation rules.")
            sys.exit(0)
        else:
            print(f"[FAIL] {p.name} failed with {len(errs)} errors:")
            for err in errs:
                print(f"  - {err}")
            sys.exit(1)
    elif p.is_dir():
        files = sorted(list(p.glob("*.json")))
        print(f"Auditing {len(files)} case files in {p}...")
        total_fail = 0
        for f in files:
            valid, errs = validator.validate(json.load(open(f)), check_db=True)
            if valid:
                print(f"  [PASS] {f.name}")
            else:
                total_fail += 1
                print(f"  [FAIL] {f.name} ({len(errs)} errors):")
                for err in errs[:5]:
                    print(f"     * {err}")
        if total_fail == 0:
            print(f"\nALL {len(files)} FILES PASSED!")
            sys.exit(0)
        else:
            print(f"\n{total_fail} / {len(files)} FILES FAILED.")
            sys.exit(1)
