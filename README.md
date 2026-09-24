# TigerGraph × Hacker House Goa: Autonomous Fraud Defense Intelligence

[![TigerGraph](https://img.shields.io/badge/TigerGraph-GSQL-orange.svg)](https://www.tigergraph.com/)
[![LangGraph](https://img.shields.io/badge/Agent-LangGraph-blue.svg)](https://langchain-ai.github.io/langgraph/)
[![Dataset](https://img.shields.io/badge/Dataset-IEEE--CIS%20Fraud%20(590k)-green.svg)](https://www.kaggle.com/c/ieee-fraud-detection)
[![Validation](https://img.shields.io/badge/Validation-100%25%20Passed%20(28%20Cases)-brightgreen.svg)](cases/)
[![Tests](https://img.shields.io/badge/Unit%20Tests-68%2F68%20Passing-success.svg)](tests/)
[![Policy Agreement](https://img.shields.io/badge/Policy%20Agreement-100.00%25%20(5%2C565%20Cases)-blueviolet.svg)](docs/policy_agreement_report.md)

An enterprise-grade autonomous fraud investigation platform built for the **TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation Challenge**. 

The system investigates real-time alerts across **590,742 transactions**, unmasks multi-hop device and identity syndicates, enforces **Fraud Policy v1.0** with mathematical determinism, and writes resolved cases back into TigerGraph as active institutional memory.

---

## ⚡ Core Architectural Thesis

> **The LLM reasons, but the Policy Engine decides.**

In high-stakes enterprise banking, raw LLMs cannot be trusted with execution APIs. They hallucinate connections, fail FinCEN audits, and trigger wrongful card blocks on uncorroborated alerts. 

Our tripartite architecture cleanly decouples responsibilities:
1. **Reasoning Tier (LangGraph + GraphRAG):** The LLM acts as an investigative detective—formulating hypotheses, planning GSQL query execution, evaluating out-of-band customer evidence, and drafting 6–12 sentence FinCEN SAR narratives.
2. **Topology Tier (TigerGraph & GSQL):** Pointer-chasing graph engine maintaining pre-indexed chronological `NEXT` edge chains across payment cards, sub-4ms card-testing detection (Rule R5), and multi-hop syndicate ring traversals (Rule R6).
3. **Decision Tier (Pure Python, Zero LLM):** A deterministic Fraud Policy Engine executing Rules R1–R10 with role-based approval routing (`auto`, `L1 Team Lead`, `L2 Operations Manager`).

```
┌────────────────────────────────────────────────────────────────────────┐
│                      1. REASONING TIER (LangGraph)                     │
│  - Hypothesis Formulation        - Evidence Planning & Tool Calling   │
│  - Multi-hop Investigation Plan  - Standalone FinCEN SAR Generation   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │  MCP Tools (JSON Payloads)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   2. TOPOLOGY TIER (TigerGraph & GSQL)                 │
│  - 590,742 Transactions          - Chronological NEXT Chains           │
│  - 144,432 Device Identities     - Multi-hop Syndicate Traversals      │
│  - 5,565 Historical Closed Cases - Active Case Memory Persistence      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │  Topological Features & Graph Facts
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│         3. CALIBRATED ML & DECISION TIER (Pure Python, Zero LLM)       │
│  - 5-Fold Isotonic Probability Calibrator (AUC 0.9950, Brier 0.0212)   │
│  - Fraud Policy v1.0 Deterministic Engine (Rules R1–R10, SAR §3a)      │
│  - Role-Based Approval Routing (Automated, L1 Team Lead, L2 Manager)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🏆 Benchmark & Credibility Flex

We benchmarked our probability calibration and policy decision engine against **all 5,565 historical closed cases** from the bank (`Dataset/closed_cases_history.csv`):

| Evaluation Metric | Benchmark Target | Achieved Performance |
| :--- | :--- | :--- |
| **ROC AUC** | $\ge 0.950$ | **0.9950** |
| **Brier Score** | $< 0.100$ | **0.0212** |
| **Precision ($\ge 0.70$)** | $\ge 95.0\%$ | **98.18%** |
| **Recall ($\ge 0.70$)** | $\ge 95.0\%$ | **98.39%** |
| **Core Action Recommendation Agreement** | $\ge 95.0\%$ | **100.00% (5,565 / 5,565)** |
| **FinCEN SAR Filing Agreement** | $\ge 98.0\%$ | **100.00% (5,565 / 5,565)** |
| **Discrepancies Observed** | 0 | **0 Discrepancies** |

*See full reports: [`docs/calibration_report.md`](docs/calibration_report.md) and [`docs/policy_agreement_report.md`](docs/policy_agreement_report.md).*

---

## 🔍 Showcase Case Studies

### 1. `HHG-014` — The 51-Card Syndicate Device Ring (Policy Rule R6 & Section 3a)
- **The Alert:** Analyst alert on card `C13487-K1` regarding an unrecognized device profile running an anonymizing proxy.
- **Graph Traversal:** GSQL query `device_neighbors` traversed the topology and uncovered **51 other payment cards** tied to that exact device hardware fingerprint.
- **The Policy Override:** Although the card's individual exposure was only **$74.96** (sub-$1,000), Section 3a mandates a **FinCEN SAR filing** due to the multi-card syndicate origin.
- **Actions Executed:** `CREATE_CASE` (`auto`), `BLOCK_CARD` (`L1`), `MONITOR_CONNECTED_CARDS` (`auto`), `FILE_REPORT` (`L2`).

### 2. `HHG-018` — The Customer Dispute Fork (Rule R7 vs Rule R2 Precedence)
- **The Alert:** Customer reports an unrecognized charge of **$39.08** on card `C02354-K2`.
- **Pre-Evidence Route:** Initial prior prepared to block the card under Rule R2 (`[CREATE_CASE, BLOCK_CARD]`).
- **Simulated Verification:** Cardholder recognized the charge as a forgotten monthly subscription agreement.
- **Strict Precedence:** The Policy Engine evaluated **Rule R7 before Rule R2**, dynamically flipping the route to **`[CLOSE_NO_FRAUD]`** with zero card disruption.

### 3. `HHG-010` — Exact Exposure Boundary & Regulatory Precision
- **Exposure Calculation:** Computed dynamically from the graph as **$1,000.03**, crossing the FinCEN regulatory threshold by three cents (`sar.file = true`).

---

## 🖥️ Analyst Dashboard (Interactive Demo)

The system includes a production-grade Analyst Dashboard served via **FastAPI** with a **D3.js** interactive topology graph:

- **URL:** `http://localhost:8000`
- **One Screen Per Case:** Designed specifically for video demo recording.
- **Features:**
  - 11-step numbered timeline stepper with VCR replay controls (matching `asked_after_step: 6` highlighted on Step 7).
  - Interactive D3 entity subgraph (Customer, Card, Txn, DeviceProfile, Region, ClosedCase) with drag, zoom, and tooltips.
  - Side-by-side route comparison (`initial` vs `final`) with `what_changed` callout.
  - Interactive **"Approve & Execute"** buttons hitting the Mock Action Service (generating `AUTH-YYYYMMDD-XXXXXX` tokens).
  - FinCEN SAR modal with standalone 5-element narrative (copy to clipboard & JSON download).
  - Graph memory panel displaying retrieved prior closed cases.

---

## 🚀 Quickstart & Execution Guide

### 1. Prerequisites & Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # FastAPI, uvicorn, scikit-learn, pandas, numpy
```

### 2. Launch the Analyst Dashboard
```bash
python3 ui/server.py
# Open http://localhost:8000 in your browser
```

### 3. Run Autonomous Agent Across All 20 Alert Cases
```bash
python3 src/agent/runner.py
# Completes in ~9.5s (avg 0.48s/case, 202 tool calls)
# Outputs saved to cases/HHG-*.json
```

### 4. Run the Innovation Exploration Sweep
```bash
python3 scripts/run_exploration.py
# Discovers 8 un-alerted Nov-Dec high-risk cases
# Outputs saved to exploration/EXP-*.json
```

### 5. Run Verification & Test Suite
```bash
# Validate 22 case files against the strict 10-point hard-fail checklist
python3 src/reporting/validate.py cases/

# Validate 8 exploration case files
python3 src/reporting/validate.py exploration/

# Run the complete unit test suite (68 tests)
python3 -m unittest discover tests
```

---

## 📂 Repository Layout

```
├── Dataset/                     # IEEE-CIS transactions (590k), identities, closed cases (5,565), case pack
├── gsql/                        # GSQL graph schema, loading jobs, vector ingest & 10 analytical queries
├── src/
│   ├── scoring/                 # Feature builder, calibrated GBDT, policy agreement benchmark
│   ├── policy/                  # Pure Python Fraud Policy v1.0 engine (Rules R1-R10, zero LLM)
│   ├── agent/                   # LangGraph state machine, simulator, GraphRAG SAR generator, runner
│   └── reporting/               # Answer file generator & strict validator
├── cases/                       # 20 validated alert case answers (HHG-001.json to HHG-020.json)
├── exploration/                 # 8 bonus exploration case answers (EXP-001.json to EXP-008.json)
├── ui/                          # Analyst Dashboard: FastAPI server + D3.js frontend (port 8000)
├── demo/                        # 3-5 min video demo script (demo/script.md)
├── blog/                        # In-depth technical blog post (blog/draft.md)
├── social/                      # X (Twitter) thread & LinkedIn article (social/post.md)
├── docs/                        # Run audit report, calibration report, policy agreement, profiling
└── tests/                       # 68 comprehensive unit and regression tests
```

---

## 👥 Hackathon Submission Deliverables

- **Demo Video Script:** [`demo/script.md`](demo/script.md)
- **Technical Deep-Dive Blog:** [`blog/draft.md`](blog/draft.md)
- **Social Media Thread (tagging @TigerGraphDB):** [`social/post.md`](social/post.md)
- **Comprehensive Run Audit Ledger:** [`docs/run_audit.md`](docs/run_audit.md)
- **20 Validated Case JSONs:** [`cases/`](cases/)
- **8 Innovation Exploration JSONs:** [`exploration/`](exploration/)
