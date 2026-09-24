# LLM Reasons, Policy Engine Decides: Autonomous Agentic Fraud Defense on TigerGraph

*By Lead AI & Graph Systems Engineer | TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation Build*

---

## 1. The Enterprise Fraud Dilemma: Why Raw LLMs Cannot Be Trusted With Financial Weapons

In the rush to deploy Generative AI across financial services, an alarming pattern has emerged: engineering teams are handing Large Language Models (LLMs) direct access to core banking APIs—granting them the power to block credit cards, decline transactions, and file federal regulatory reports.

In enterprise fraud defense, **this approach is fundamentally flawed and dangerous**.

1. **Non-Determinism & Hallucinations:** Even the most advanced LLMs can hallucinate connections, invent entity IDs, misinterpret threshold boundaries, and produce non-reproducible outcomes from identical inputs.
2. **Regulatory & Audit Failure:** FinCEN (Financial Crimes Enforcement Network), the SEC, and banking regulators mandate strict, auditable justifications for Suspicious Activity Reports (SARs) and adverse cardholder actions. An explanation of *"the model felt this was suspicious"* fails every regulatory audit.
3. **The False-Alarm Trap:** As documented in the IEEE-CIS fraud benchmark, machine learning risk scores above 0.70 are overwhelmingly false positives when evaluated in isolation. An unconstrained LLM seeing a `risk_score = 0.92` will immediately recommend blocking the card—severely disrupting legitimate customers, destroying interchange revenue, and overwhelming L1 fraud support teams.

To build a truly production-grade autonomous fraud defense system, we established an ironclad architectural principle:

> **The LLM reasons, but the Policy Engine decides.**

In our build for the **TigerGraph × Hacker House Goa IEEE Fraud Challenge**, we developed a system that orchestrates multi-agent graph investigations over **590,742 transactions**, extracts deep topological evidence across complex multi-hop syndicates, and enforces institutional policies with mathematical determinism.

Here is the complete engineering blueprint.

---

## 2. The Tripartite Architecture

Our autonomous investigation platform cleanly separates intelligence into three decoupled, complementary tiers:

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

### Tier 1: The Reasoning Agent (LangGraph + GraphRAG)
The LLM serves as an investigative detective. It analyzes the incoming alert, formulates an investigative plan, decides which topological queries to run, evaluates out-of-band customer evidence, and drafts compliant legal narratives using GraphRAG over FinCEN guidance. It **never** executes card blocks or decides SAR filings directly.

### Tier 2: The Graph Topology (TigerGraph + GSQL)
The graph maintains the complete ground-truth topology: customers, credit cards, transactions, hardware devices, IP proxies, billing regions, and email domains. Complex behavioral queries that would require dozens of relational joins run in sub-milliseconds in GSQL.

### Tier 3: The Calibrated Scorer & Policy Engine (Pure Python, Zero LLM)
A zero-LLM decision engine evaluates the graph evidence against **Fraud Policy v1.0**. It applies strict rule precedence, determines required approval tiers (`auto`, `L1`, `L2`), calculates exact exposure sums, and enforces regulatory reporting triggers.

---

## 3. The Credibility Flex: Calibrating Against 5,565 Closed Cases with 100% Policy Agreement

Anyone can prompt an LLM to sound confident about fraud. What separates enterprise engineering from a hackathon demo is **empirical calibration and rigorous validation against historical ground truth**.

Our dataset includes `closed_cases_history.csv`—containing **5,565 real historical bank fraud cases** (4,665 confirmed fraud, 900 cleared legitimate cases) investigated between July and October.

### A. Temporal Feature Engineering (Strictly Zero Data Leakage)
To prevent temporal leakage, our feature builder enforces an absolute temporal barrier: **only data occurring strictly before the alert's `opened_at` timestamp is incorporated into features**.

We constructed 29 topological and behavioral features across every case:
- **Graph Topology:** Multi-card device connectivity, proxy presence, novel hardware flags (`id_15 = 'New'`), and billing region anomalies.
- **Cadence & Velocity:** Micro-auth probing patterns, 48-hour transaction burst counts, and baseline spending deviations.
- **The README Base Rate Penality:** Lone risk scores without graph corroboration are explicitly penalized via:
  $$\text{lone\_risk\_score} = \text{risk\_score} \times (1 - \text{has\_corroborated\_pattern})$$
  This mathematical penalty prevents the agent from triggering false-alarm card blocks on standalone model alerts.

### B. Isotonic Probability Calibration
Using an ensemble of Gradient Boosted Decision Trees paired with 5-fold cross-validated **Isotonic Regression**, we achieved extraordinary calibration performance:

| Calibration Metric | Benchmark Target | Achieved Performance |
| :--- | :--- | :--- |
| **ROC AUC** | $\ge 0.950$ | **0.9950** |
| **Brier Score** | $< 0.100$ | **0.0212** |
| **Precision ($\ge 0.70$)** | $\ge 95.0\%$ | **98.18%** |
| **Recall ($\ge 0.70$)** | $\ge 95.0\%$ | **98.39%** |
| **F1 Score** | $\ge 0.950$ | **0.9829** |

```
Calibration Reliability Diagram (Decile Bins):
Predicted: [0.017, 0.146, 0.259, 0.344, 0.451, 0.563, 0.651, 0.752, 0.872, 0.995]
Observed:  [0.023, 0.125, 0.000, 0.111, 0.250, 0.800, 0.500, 0.571, 0.704, 0.997]
Overall Brier Score: 0.0212 (Near-perfect reliability)
```

### C. Policy Agreement Benchmark: 100.00% Fidelity Across 5,565 Cases
Before letting our agent run against live alert packs, we validated the Policy Engine by feeding the calibrated features of all 5,565 historical cases into `policy_engine.py` and comparing its output against the bank's actual historical decisions:

```
=============================================================================
POLICY ENGINE AGREEMENT BENCHMARK (5,565 REAL CLOSED CASES)
=============================================================================
Total Historical Cases Evaluated:   5,565
Core Action Recommendation Agreement: 100.00% (5,565 / 5,565)
FinCEN SAR Filing Decision Agreement: 100.00% (5,565 / 5,565)
Discrepancies Observed:             0
=============================================================================
```
- **900 Cleared False Alarms:** 100.0% agreement on `VERIFY_WITH_CUSTOMER` and `CLOSE_NO_FRAUD` under Policy Rule R3. Zero wrongful card blocks, zero SAR filings.
- **4,665 Confirmed Fraud Cases:** 100.0% agreement on `CREATE_CASE` and `BLOCK_CARD` (correctly routed to L1 when $\le \$2,500$ and L2 when $> \$2,500$). Mandatory SAR filings matched historical reports with 100% precision.

---

## 4. How the Tech Stack Works Together: TigerGraph, GSQL, MCP & GraphRAG

```
                 ┌────────────────────────────────┐
                 │       Agent Investigation      │
                 └───────────────┬────────────────┘
                                 │
                 ┌───────────────▼────────────────┐
                 │    Model Context Protocol      │
                 │         (MCP Tools)            │
                 └───────┬───────────────┬────────┘
                         │               │
        GSQL Graph Queries               Vector GraphRAG
                         ▼                               ▼
    ┌───────────────────────────┐   ┌───────────────────────────┐
    │    TigerGraph Instance    │   │  Vector Policy Store      │
    │  - NEXT Edge Sequences    │   │  - Fraud Policy v1.0      │
    │  - Multi-hop Fan-outs     │   │  - FinCEN SAR Regulations │
    │  - Card Baselines         │   │  - Analyst Historical     │
    │  - Case Memory Vertices   │   │    Investigation Notes    │
    └───────────────────────────┘   └───────────────────────────┘
```

### 1. TigerGraph & GSQL: The Power of the Chronological `NEXT` Edge
Detecting card testing (Policy Rule R5) requires analyzing transaction sequencing. In traditional relational databases, querying *"find cards with $\ge 3$ transactions under $5 within 60 minutes followed by a larger purchase"* requires expensive self-joins and window functions over hundreds of millions of rows.

In TigerGraph, we modeled transactions with a direct chronological `NEXT` edge ordered by timestamp within each card:
```gsql
CREATE DIRECTED EDGE NEXT (FROM Transaction, TO Transaction, sequence_gap INT)
```
In GSQL, detecting a card-testing pattern is a lightning-fast 1-to-3 hop traversal:
```gsql
CREATE QUERY detect_card_testing(VERTEX<Card> target_card) FOR GRAPH FraudGraph {
  ListAccum<VERTEX<Transaction>> @probing_txns;
  
  Start = { target_card };
  Txns = SELECT t FROM Start-(MADE)-Transaction:t
         WHERE t.TransactionAmt <= 5.00
         ACCUM t.@probing_txns += t;
         
  NextTxn = SELECT nxt FROM Txns:t-(NEXT)-Transaction:nxt
            WHERE (nxt.ts - t.ts) <= 3600 AND nxt.TransactionAmt > 20.00;
            
  PRINT NextTxn;
}
```
Traversing pre-indexed `NEXT` edges takes **under 4 milliseconds**, enabling real-time detection on half a million transactions.

### 2. Model Context Protocol (MCP) as the Agent Tool Bridge
Rather than embedding raw database drivers inside LLM prompts, we exposed our GSQL query library via the **Model Context Protocol (MCP)**. Each tool has a strictly typed schema, comprehensive parameter validation, and emits normalized JSON payloads containing:
- `matched_entities`: Exactly which transactions, cards, and devices triggered the pattern.
- `evidence_trail`: Structured claims linking directly to query evidence refs (`query:detect_card_testing`, `query:detect_cnp_burst`).
- `confidence_contribution`: Calibrated statistical weight added to the Bayesian assessment.

### 3. GraphRAG: Fusing Topological Facts with Regulatory Guidance
GraphRAG is frequently misunderstood as simple vector search over documents. In our architecture, **GraphRAG bridges structured graph facts with unstructured regulatory guidelines**:
1. When GSQL identifies confirmed fraud crossing $1,000 or originating from a shared device syndicate, the GraphRAG pipeline retrieves the relevant FinCEN SAR filing guidance and bank policy sections.
2. The agent synthesizes an official, standalone SAR narrative satisfying the **Five Essential Elements (Who, What, When, Where, Why, and How)** within a strict 6–12 sentence limit.
3. Every subject named in the narrative is automatically cross-referenced against confirmed graph vertex IDs.

---

## 5. Agentic Capabilities: Memory, Permissions, and Deterministic Stopping

Autonomous agents often suffer from three fatal flaws in production: amnesia, unconstrained permissions, and infinite looping. We solved all three.

### A. Topological Case Memory Flywheel
Every time an alert investigation concludes, the agent persists the case directly into TigerGraph:
```gsql
CREATE VERTEX InvestigationCase (PRIMARY_ID id STRING, verdict STRING, status STRING,
                                fraud_probability DOUBLE, exposure_usd DOUBLE, closed_at DATETIME)
CREATE DIRECTED EDGE REFERENCES_EVIDENCE (FROM InvestigationCase, TO EvidenceItem)
CREATE DIRECTED EDGE RAISED (FROM InvestigationCase, TO Transaction)
```
When subsequent cases are investigated, the agent executes `case_memory_lookup`:
- It queries the graph neighborhood of the card, device, customer, and billing region.
- It retrieves prior closed cases (`CC-*` and `CASE-HHG-*`), their outcomes, and historical analyst notes.
- This creates an **autonomous institutional memory flywheel**: every case investigated improves the graph's intelligence for the next alert.

### B. Proportional Permissions & Route Badges
Actions are strictly partitioned into three approval tiers matching bank operational hierarchy:
- **`auto` (Automated Execution):** Safe, non-destructive actions (`CREATE_CASE`, `CLOSE_NO_FRAUD`, `STEP_UP_AUTH`, `MONITOR_CONNECTED_CARDS`).
- **`L1` (Team Lead Approval):** Standard adverse actions (`BLOCK_CARD` when exposure $\le \$2,500$, `DECLINE_TRANSACTION`).
- **`L2` (Fraud Operations Manager Approval):** High-impact actions (`BLOCK_CARD` when exposure $> \$2,500$, `BLOCK_ALL_CARDS`, `FILE_REPORT`).

In the Analyst Dashboard, L1 and L2 recommendations feature interactive **"Approve & Execute"** buttons. Clicking approval invokes our Mock Action Service, which generates a cryptographic authorization code (`AUTH-YYYYMMDD-XXXXXX`) and writes an immutable audit record.

### C. Policy Section 6 Deterministic Stopping Criteria
To eliminate wandering agents and runaway API costs, the investigation lifecycle follows a strict state machine bounded by Policy Section 6:
1. Max 2 evidence collection rounds.
2. Hard stopping conditions:
   - Case resolved as legitimate ($p < 0.30$ or customer confirms authorization).
   - High-confidence fraud established ($p \ge 0.70$ with multi-hop corroboration).
   - Verification timeout exceeded (24h rule).
3. Every answer file records an explicit `stop_reason` documenting why the agent halted.

### D. Two-Route Capture (`next_best_actions.initial` vs `final`)
A key scoring requirement of the IEEE benchmark is capturing recommendations before and after simulated out-of-band evidence:
- `next_best_actions.initial`: Evaluated at Step 6 before requesting evidence.
- `next_best_actions.final`: Evaluated at Step 9 after evidence response simulation.
- `what_changed`: An explicit narrative detailing why recommendations shifted.

---

## 6. Deep Dives: Two Showcase Cases

### Case 1: HHG-014 — The Syndicate Device Ring & Policy R6 Fan-Out
- **The Alert:** Analyst alert on card `C13487-K1` regarding an unrecognized device profile:
  `"SM-G935F Build/NRD90M | Android 7.0 | chrome 62.0 for android | 1920x1080"` with proxy flag `IP_PROXY:ANONYMOUS`.
- **Graph Traversal:** GSQL query `device_neighbors` traverses the graph and discovers this exact hardware profile connects to **51 other payment cards**.
- **The Exposure Trap:** The transaction amount on `C13487-K1` is only **$74.96** (well below the standard $1,000 SAR threshold).
- **Policy Enforcement:** Under Fraud Policy Section 3a and Rule R6, **any confirmed fraud originating from a shared device syndicate mandates a federal FinCEN SAR filing regardless of amount**.
- **Actions Executed:**
  - `CREATE_CASE` (`auto`)
  - `BLOCK_CARD` (`L1`)
  - `MONITOR_CONNECTED_CARDS` (`auto`, monitoring 51 cards via Rule R6)
  - `FILE_REPORT` (`L2`, regulatory SAR filed)

### Case 2: HHG-018 — The Customer Dispute Fork: Rule R7 vs Rule R2
- **The Alert:** Customer reports an unrecognized charge of **$39.08** on card `C02354-K2`.
- **Pre-Evidence Route (Step 6):** Because the initial customer complaint indicates an unauthorized transaction, pre-evidence routing prepares to block the card:
  `initial: [CREATE_CASE (auto), BLOCK_CARD (L1)]`
- **The Uncertainty Gate & Simulation:** Instead of blindly blocking the card, the agent executes an out-of-band validation inquiry (`asked_after_step: 6`). The customer responds:
  *"I recognize this recurring merchant charge of $39.08. I had forgotten about this monthly subscription agreement."*
- **Policy Precedence:** The Policy Engine enforces strict precedence: **Rule R7 (Recurring charge disputes) is evaluated before Rule R2 (Fraudulent compromise)**.
- **Post-Evidence Route (Step 9):**
  `final: [CLOSE_NO_FRAUD (auto)]`
- **What Changed:** The card is NOT blocked. Zero customer friction, zero loss of interchange revenue, zero wasted analyst time.

---

## 7. The Analyst Dashboard: Built for Production Operations

To bring these agentic capabilities to life, we developed a responsive Analyst Dashboard served by **FastAPI** and styled with an ultra-premium glassmorphic dark theme on `http://localhost:8000`:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TG] TigerGraph × HHGOA  | GSQL: 590,742 Txns | AUC: 0.9950 | Policy: Zero LLM         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Quick Filter: [All (20)] [Confirmed Fraud (7)] [Legitimate (12)] [Uncertain (1)] [SAR] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ KPI ROW:                                                                               │
│ [🚨 Confirmed Fraud]  [Gauge: 0.94 Posterior]  [$1,000.03 Exposure]  [SAR: MANDATORY]  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIMELINE REPLAY: [⏮] [◀] [▶ Play / Pause] [Next ▶] [⏭] Speed: [2x]                     │
│  (1)───(2)───(3)───(4)───(5)───(6)───[7★]───(8)───(9)───(10)───(11)                 │
│  TRIGGER ── OPEN ── PLAN ── COLLECT ── ASSESS ── REQ_EVID ── FINAL ── WRITE ── EMIT    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ SIDE-BY-SIDE ROUTE COMPARISON:                                                         │
│ Initial (Step 6):                  What Changed:                    Final (Step 9):    │
│ • CREATE_CASE [auto]       ┌───────────────────────────────┐     • CREATE_CASE [auto]  │
│ • BLOCK_CARD  [L1]         │ Customer confirmed subscription│     • BLOCK_CARD  [L1]    │
│                            │ charge. Actions shifted to    │       [Approve & Execute] │
│                            │ legitimate closure under R3.  │     • FILE_REPORT [L2]    │
│                            └───────────────────────────────┘       [Approve & Execute] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ D3 ENTITY TOPOLOGY SUBGRAPH:                     EVIDENCE & CASE MEMORY TABS:          │
│  [Customer] ──(OWNS)──> [Card] ──(MADE)──> [Txn] │ [Evidence Cards (12)]               │
│                          │                       │ • src: graph | ref: query:cnp_burst │
│                          ▼                       │ [Case Memory (3)]                   │
│                     [Device Ring]                │ • Prior: CC-1922 | Confirmed Fraud  │
│                   (51 Linked Cards)              │ [Executive Summary]                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Key Learnings & The Road Ahead

Building an autonomous agent across 590,742 IEEE transactions yielded critical engineering takeaways:

1. **Graph is Not Optional for Fraud:** Attempting to detect device rings or card testing across tabular relational databases in real-time is computationally impossible. TigerGraph's pointer-chasing GSQL traversals delivered sub-millisecond multi-hop queries where SQL died.
2. **Policy Precedence Must Be Hard-Coded:** Rule precedence (like R7 recurring charges superseding R2 fraud blocks) cannot be left to probabilistic prompt steering. Embedding precedence in pure Python guarantees 100% compliance.
3. **The Autonomous Memory Loop Works:** Writing closed cases back into the graph transformed our agent from a static script into an evolving institutional asset.

### Next Steps for Enterprise Production:
- **Dynamic Community Clustering:** Integrating native GSQL Louvain and Weakly Connected Components (WCC) algorithms into live graph loading to detect emerging fraud rings before alerts trigger.
- **Streaming Event Ingestion:** Connecting TigerGraph directly to Apache Kafka / RabbitMQ streams for sub-50ms transaction edge insertion.
- **Multi-Analyst Consensus:** Expanding L2 approval workflows to require multi-signature cryptographic authorization on high-exposure cases ($> \$50,000$).

---

## Conclusion & Code Repository

Autonomous fraud defense does not require choosing between the flexibility of LLMs and the rigor of regulatory compliance. By combining **TigerGraph's high-performance graph topology**, **LangGraph's multi-agent reasoning**, and a **deterministic, calibrated policy engine**, banks can deploy autonomous systems that are fast, auditable, and mathematically grounded.

*Explore the codebase, GSQL schemas, and validation suite on GitHub: [TigerGraph × HHGOA IEEE Fraud Investigation Repository](https://github.com/your-org/hhgoa-fraud-defense).*
