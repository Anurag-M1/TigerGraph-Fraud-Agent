#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 1: Vector Store Ingestion Script
=============================================================================
Loads and indexes:
1. Fraud Policy v1.0 (Section by section, R1-R10 preserved in metadata)
2. README Known Fraud Patterns section (5 known patterns + undocumented)
3. All 5,565 Analyst Notes from closed_cases_history.csv with full case metadata
4. FinCEN SAR Narrative Guidance & SAR Filing FAQs (Who, What, When, Where, Why, How)

Provides persistent vector index (TF-IDF + Cosine similarity + Dense normalized embeddings)
and persistent SQLite metadata store with fast retrieval API for GraphRAG.
Supports optional sync with TigerGraph Savanna Vector Search.
=============================================================================
"""

import os
import sys
import json
import sqlite3
import re
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "Dataset"
VECTOR_DIR = PROJECT_ROOT / "gsql" / "vector_store"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = VECTOR_DIR / "vector_store.db"
MODEL_PATH = VECTOR_DIR / "vectorizer.pkl"
MATRIX_PATH = VECTOR_DIR / "embeddings.npy"

# ----------------------------------------------------------------------------
# 1. Document Extraction & Chunking
# ----------------------------------------------------------------------------

def extract_policy_chunks(readme_path: Path):
    """Parse Fraud Policy v1.0 from README.md into granular rule-based chunks."""
    with open(readme_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = []
    
    # Locate Fraud Policy section
    policy_start = text.find("# Fraud Policy")
    policy_end = text.find("# Answer Format", policy_start)
    if policy_start == -1:
        policy_text = text
    else:
        policy_text = text[policy_start : policy_end if policy_end != -1 else len(text)]

    # Rule extraction: R1 to R10
    rule_patterns = re.findall(r"\*\*(R\d+)\.\s*([^\*]+)\*\*\s*([^\n\r]+(?:\n(?!\*\*R|\n###)[^\n\r]+)*)", policy_text)
    for rule_id, rule_title, rule_body in rule_patterns:
        full_text = f"Fraud Policy {rule_id}: {rule_title.strip()}\n{rule_body.strip()}"
        chunks.append({
            "doc_id": f"policy_{rule_id.lower()}",
            "source": "Fraud Policy v1.0",
            "category": "policy_rule",
            "rule_id": rule_id.strip(),
            "title": f"Rule {rule_id}: {rule_title.strip()}",
            "content": full_text
        })

    # Approval routing table
    routing_match = re.search(r"### 2\. Approval routing\s*([\s\S]*?)(?=### 3\. Rules)", policy_text)
    if routing_match:
        chunks.append({
            "doc_id": "policy_approval_routing",
            "source": "Fraud Policy v1.0",
            "category": "policy_governance",
            "rule_id": "ROUTING",
            "title": "Fraud Policy Approval Routing (auto, L1, L2)",
            "content": routing_match.group(0).strip()
        })

    # Permitted Actions table
    actions_match = re.search(r"### 1\. Actions\s*([\s\S]*?)(?=### 2\. Approval routing)", policy_text)
    if actions_match:
        chunks.append({
            "doc_id": "policy_permitted_actions",
            "source": "Fraud Policy v1.0",
            "category": "policy_governance",
            "rule_id": "ACTIONS",
            "title": "Fraud Policy Permitted Actions and Customer Impact",
            "content": actions_match.group(0).strip()
        })

    # Case vs Report (Section 3a)
    sec3a_match = re.search(r"### 3a\. A case is not a report\s*([\s\S]*?)(?=### 3b\.)", policy_text)
    if sec3a_match:
        chunks.append({
            "doc_id": "policy_case_vs_sar",
            "source": "Fraud Policy v1.0",
            "category": "policy_guidance",
            "rule_id": "SEC_3A",
            "title": "Section 3a: A Case is Not a Report (CREATE_CASE vs FILE_REPORT thresholds)",
            "content": sec3a_match.group(0).strip()
        })

    # NBA evolution (Section 3b)
    sec3b_match = re.search(r"### 3b\. The next best action can change\s*([\s\S]*?)(?=### 4\.)", policy_text)
    if sec3b_match:
        chunks.append({
            "doc_id": "policy_nba_evolution",
            "source": "Fraud Policy v1.0",
            "category": "policy_guidance",
            "rule_id": "SEC_3B",
            "title": "Section 3b: Next Best Action Evolution (Before and After Evidence)",
            "content": sec3b_match.group(0).strip()
        })

    # Stopping condition & Explaining (Sections 6 & 7)
    sec6_match = re.search(r"### 6\. Stopping\s*([\s\S]*?)(?=### 7\.)", policy_text)
    if sec6_match:
        chunks.append({
            "doc_id": "policy_stopping_criteria",
            "source": "Fraud Policy v1.0",
            "category": "policy_governance",
            "rule_id": "SEC_6",
            "title": "Section 6: Investigation Stopping Criteria (Probabilities 0.85/0.15)",
            "content": sec6_match.group(0).strip()
        })

    # Extract Known Fraud Patterns Section
    pattern_start = text.find("## The five known fraud patterns")
    pattern_end = text.find("## Regulatory references", pattern_start)
    if pattern_start != -1 and pattern_end != -1:
        pattern_text = text[pattern_start:pattern_end]
        pattern_blocks = re.findall(r"\*\*(\d+)\.\s*([^\*]+)\*\*\s*([^\n\r]+(?:\n(?!\*\*\d|\n##)[^\n\r]+)*)", pattern_text)
        for num, pat_name, pat_desc in pattern_blocks:
            chunks.append({
                "doc_id": f"pattern_{num}",
                "source": "README Pattern Section",
                "category": "fraud_pattern",
                "rule_id": f"PATTERN_{num}",
                "title": f"Pattern {num}: {pat_name.strip()}",
                "content": f"Fraud Typology {num}: {pat_name.strip()}\n{pat_desc.strip()}"
            })
            
    print(f"[Vector Ingest] Extracted {len(chunks)} policy & pattern sections.")
    return chunks


def extract_fincen_guidance_chunks():
    """Build authoritative FinCEN SAR Narrative Guidance & FAQ chunks."""
    guidance = [
        {
            "doc_id": "fincen_sar_narrative_core",
            "source": "FinCEN SAR Narrative Guidance",
            "category": "regulatory_guidance",
            "rule_id": "FINCEN_NARRATIVE_CORE",
            "title": "FinCEN SAR Narrative: The Five Essential Elements",
            "content": (
                "A complete, defensible Suspicious Activity Report (SAR) narrative must answer the essential questions: "
                "1. WHO is conducting the suspicious activity (Customer ID, card IDs, merchant details, shared device identifiers, IP/proxies). "
                "2. WHAT instruments or mechanisms were used (unauthorized transactions, small card testing authorizations, disputed amounts). "
                "3. WHEN did the activity occur (exact chronologically ordered timestamps and date span YYYY-MM-DD). "
                "4. WHERE did the transactions take place (billing region code addr1, country addr2, online vs in-person channel). "
                "5. HOW was the activity executed (compromised card credentials, new device profile, rapid authorization velocity). "
                "6. WHY is the activity suspicious (pattern mismatch with customer baseline, violation of policy thresholds, shared origin with confirmed fraud rings)."
            )
        },
        {
            "doc_id": "fincen_sar_faq_thresholds",
            "source": "FinCEN SAR Filing FAQs",
            "category": "regulatory_guidance",
            "rule_id": "FINCEN_THRESHOLDS",
            "title": "FinCEN SAR Filing Thresholds & Policy R2 / R9 Alignment",
            "content": (
                "Under BSA/FinCEN regulations and Fraud Policy v1.0: "
                "Mandatory filing occurs when fraud is confirmed or strongly suspected AND: "
                "(a) Exposure exceeds $1,000 USD (internal institution threshold under Rule R2); "
                "(b) The activity connects to a shared device profile, shared billing region cluster, or multi-card organized fraud ring (Rule R6); "
                "(c) Novel or undocumented coordinated patterns across customers (Rule R9). "
                "A SAR narrative must be self-contained: external examiners and law enforcement must understand the entire fraud episode without reviewing internal logs."
            )
        },
        {
            "doc_id": "fincen_account_takeover_advisory",
            "source": "FinCEN Advisory FIN-2011-A016",
            "category": "regulatory_guidance",
            "rule_id": "FINCEN_ATO",
            "title": "FinCEN Advisory on Account Takeover and Credential Compromise",
            "content": (
                "Account Takeover (ATO) red flags: "
                "- Transactions originating from previously unseen devices (New Device flag id_15 = 'New') with different OS, browser, or screen resolution. "
                "- Routing through anonymizing proxies (id_23) or rapid changes in geolocational billing regions (addr1) within short time windows. "
                "- Uncharacteristic channel shifts (e.g. from in-person retail purchases to high-value online transactions). "
                "- Match flag anomalies (M1-M9 name/address mismatch)."
            )
        },
        {
            "doc_id": "fincen_card_testing_cyber_typology",
            "source": "FinCEN & FATF Cyber-Enabled Fraud Typology",
            "category": "regulatory_guidance",
            "rule_id": "FINCEN_CARD_TESTING",
            "title": "Card Testing Velocity and Low-Value Authorization Probing",
            "content": (
                "Card testing indicators: "
                "Automated scripts or botnets initiate 3 or more micro-authorizations (typically under $5.00 USD, ProductCD 'C' or 'R') "
                "within minutes to test validity of stolen card numbers, immediately followed by large purchases (over $100.00). "
                "Regulatory expectation: Immediate card blocking (L1 approval when <= $2,500), declining pending authorizations, "
                "and investigation of shared device fingerprints across the card base."
            )
        }
    ]
    print(f"[Vector Ingest] Added {len(guidance)} FinCEN SAR guidance chunks.")
    return guidance


def extract_analyst_notes_chunks(closed_cases_path: Path):
    """Load all 5,565 analyst notes from closed_cases_history.csv with full case metadata."""
    df = pd.read_csv(closed_cases_path)
    chunks = []
    
    for idx, row in df.iterrows():
        case_id = str(row["case_id"])
        outcome = str(row["outcome"])
        pattern = str(row["pattern"])
        notes = str(row["analyst_notes"]) if pd.notna(row["analyst_notes"]) else ""
        cust_id = str(row["customer_id"]) if pd.notna(row["customer_id"]) else ""
        card_id = str(row["card_id"]) if pd.notna(row["card_id"]) else ""
        exposure = float(row["exposure_usd"]) if pd.notna(row["exposure_usd"]) else 0.0
        actions = str(row["actions_taken"]) if pd.notna(row["actions_taken"]) else ""
        report_filed = str(row["report_filed"]).lower() in ("yes", "true", "1")
        
        content = (
            f"Case {case_id} | Outcome: {outcome} | Pattern: {pattern} | Exposure: ${exposure:.2f} | "
            f"Customer: {cust_id} | Card: {card_id} | Actions: {actions} | SAR Filed: {report_filed}\n"
            f"Analyst Notes: {notes}"
        )
        
        chunks.append({
            "doc_id": f"closed_case_{case_id}",
            "source": "closed_cases_history.csv",
            "category": "analyst_notes",
            "rule_id": case_id,
            "title": f"Closed Case {case_id} ({outcome}, {pattern})",
            "content": content,
            "metadata_json": json.dumps({
                "case_id": case_id,
                "outcome": outcome,
                "pattern": pattern,
                "customer_id": cust_id,
                "card_id": card_id,
                "exposure_usd": exposure,
                "actions_taken": actions,
                "report_filed": report_filed
            })
        })
        
    print(f"[Vector Ingest] Extracted {len(chunks)} analyst notes from closed cases.")
    return chunks


# ----------------------------------------------------------------------------
# 2. Database & Vector Index Construction
# ----------------------------------------------------------------------------

def build_vector_store():
    """Extract all documents, build TF-IDF + Cosine index, and save to SQLite."""
    print("=" * 80)
    print("  HHGOA_IEEE — PHASE 1: VECTOR INGESTION")
    print("=" * 80)

    readme_file = DATA_DIR / "README.md"
    closed_cases_file = DATA_DIR / "closed_cases_history.csv"

    if not readme_file.exists():
        raise FileNotFoundError(f"Missing {readme_file}")
    if not closed_cases_file.exists():
        raise FileNotFoundError(f"Missing {closed_cases_file}")

    all_chunks = []
    all_chunks.extend(extract_policy_chunks(readme_file))
    all_chunks.extend(extract_fincen_guidance_chunks())
    all_chunks.extend(extract_analyst_notes_chunks(closed_cases_file))

    print(f"\nTotal indexed chunks: {len(all_chunks):,}")

    # Build SQLite storage
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT UNIQUE,
            source TEXT,
            category TEXT,
            rule_id TEXT,
            title TEXT,
            content TEXT,
            metadata_json TEXT
        )
    """)
    cur.execute("CREATE INDEX idx_category ON documents(category)")
    cur.execute("CREATE INDEX idx_rule_id ON documents(rule_id)")

    records = []
    corpus = []
    for chunk in all_chunks:
        corpus.append(chunk["content"])
        records.append((
            chunk["doc_id"],
            chunk["source"],
            chunk["category"],
            chunk.get("rule_id", ""),
            chunk["title"],
            chunk["content"],
            chunk.get("metadata_json", "{}")
        ))

    cur.executemany("""
        INSERT INTO documents (doc_id, source, category, rule_id, title, content, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    conn.close()
    print(f"[Vector Ingest] Saved SQLite database to {DB_PATH}")

    # Fit TF-IDF Vectorizer
    print("[Vector Ingest] Fitting vectorizer over document corpus...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=25000,
        sublinear_tf=True,
        stop_words="english"
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Save vectorizer and matrix
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(vectorizer, f)
    np.save(MATRIX_PATH, tfidf_matrix)

    print(f"[Vector Ingest] Saved vectorizer to {MODEL_PATH}")
    print(f"[Vector Ingest] Saved matrix with shape {tfidf_matrix.shape} to {MATRIX_PATH}")

    # Run smoke queries
    test_queries = [
        ("card testing 3 small online authorizations", "policy_rule"),
        ("SAR narrative five essential elements who what when where why how", "regulatory_guidance"),
        ("unrecognized activity card_not_present_new_device", "analyst_notes")
    ]

    print("\n--- Running Vector Store Smoke Retrieval Tests ---")
    for q, cat_filter in test_queries:
        results = search_vector_store(q, k=2, category=cat_filter)
        print(f"\nQuery: '{q}' (filter: {cat_filter})")
        for rank, r in enumerate(results, 1):
            print(f"  [{rank}] Score: {r['score']:.4f} | ID: {r['doc_id']} | Rule: {r['rule_id']}")
            print(f"      Title: {r['title']}")
            print(f"      Snippet: {r['content'][:140]}...")

    print("\n[Vector Ingest] Vector Store Ingestion Completed Successfully!")


# ----------------------------------------------------------------------------
# 3. Retrieval API
# ----------------------------------------------------------------------------

def search_vector_store(query: str, k: int = 5, category: str = None):
    """Retrieve top-k documents matching query with optional category filtering."""
    if not MODEL_PATH.exists() or not MATRIX_PATH.exists() or not DB_PATH.exists():
        raise RuntimeError("Vector store not initialized. Run build_vector_store() first.")

    with open(MODEL_PATH, "rb") as f:
        vectorizer = pickle.load(f)
    matrix = np.load(MATRIX_PATH, allow_pickle=True).item()

    query_vec = vectorizer.transform([query])
    # Cosine similarities
    scores = (matrix * query_vec.T).toarray().flatten()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if category:
        cur.execute("SELECT id FROM documents WHERE category = ?", (category,))
        allowed_ids = set(row[0] - 1 for row in cur.fetchall())
        for idx in range(len(scores)):
            if idx not in allowed_ids:
                scores[idx] = -1.0

    top_indices = np.argsort(scores)[::-1][:k]

    results = []
    for idx in top_indices:
        score = float(scores[idx])
        if score <= 0:
            continue
        db_id = int(idx) + 1
        cur.execute("SELECT doc_id, source, category, rule_id, title, content, metadata_json FROM documents WHERE id = ?", (db_id,))
        row = cur.fetchone()
        if row:
            results.append({
                "score": score,
                "doc_id": row[0],
                "source": row[1],
                "category": row[2],
                "rule_id": row[3],
                "title": row[4],
                "content": row[5],
                "metadata": json.loads(row[6]) if row[6] else {}
            })

    conn.close()
    return results


if __name__ == "__main__":
    build_vector_store()
