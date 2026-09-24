# Social Media Announcements: TigerGraph × HHGOA Autonomous Fraud Defense

---

## 1. X (Twitter) Thread

### Tweet 1 (Hook / Announcement) 🧵👇
Can an autonomous AI agent fight financial fraud without hallucinating, blocking legitimate cards, or failing federal audits?

We built the answer for @TigerGraphDB × Hacker House Goa: An autonomous multi-agent defense system across 590,742 transactions.

Our core rule: **The LLM reasons, but the Policy Engine decides.** 🛡️⚡

Here’s how it works 🧵👇

---

### Tweet 2 (The Architecture Problem)
Most AI fraud demos hand LLMs direct access to blocking APIs. In enterprise banking, this is reckless:
- LLMs hallucinate entity links
- They fail FinCEN regulatory audits
- Lone ML risk scores >0.70 are overwhelmingly FALSE ALARMS

We separated intelligence into 3 decoupled tiers:
1️⃣ Reasoning (LangGraph)
2️⃣ Topology (TigerGraph & GSQL)
3️⃣ Deterministic Decision (Pure Python, Zero LLM)

---

### Tweet 3 (The Credibility Flex)
Before deploying on live alerts, we benchmarked our calibrator & policy engine against **all 5,565 historical closed cases** from the bank:

📈 5-Fold Isotonic Calibration: **0.9950 ROC AUC** & **0.0212 Brier Score**
🎯 Policy Action Agreement: **100.00% (5,565 / 5,565)**
📋 FinCEN SAR Filing Agreement: **100.00%**
⚖️ Discrepancies: **0**

Mathematical determinism where it matters most.

---

### Tweet 4 (GSQL Multi-Hop Topology)
Why is @TigerGraphDB mandatory? Pointer-chasing speed on multi-hop syndicates.

In case **HHG-014**, an alert flagged a single $74.96 charge from an unrecognized Android device.

Our GSQL `device_neighbors` query traversed the topology in <4ms and uncovered **51 other payment cards** tied to that exact hardware fingerprint!

Even at $74, Section 3a mandated a FinCEN SAR because of the shared syndicate origin (Rule R6).

---

### Tweet 5 (The Customer Dispute Fork)
Customer complains about an unrecognized charge? Raw LLMs panic and block the card.

In **HHG-018** ($39.08 charge), the initial route was `BLOCK_CARD`.
Then the agent hit our Uncertainty Gate, verified with the customer, and discovered a forgotten monthly subscription.

Our engine enforces strict precedence: **Rule R7 precedes Rule R2**.
Route flipped to `CLOSE_NO_FRAUD`. Zero card block. Zero customer disruption.

---

### Tweet 6 (The Graph Memory Flywheel)
The agent never forgets:
1. Every resolved case is written back into @TigerGraphDB as an `InvestigationCase` vertex with linked `EvidenceItem` nodes.
2. The NEXT alert runs `case_memory_lookup` and retrieves historical precedents & analyst notes in real-time.

An autonomous institutional memory loop that gets smarter with every alert.

---

### Tweet 7 (Conclusion & Links)
Built with:
⚡ @TigerGraphDB (GSQL Schema, NEXT chains, graph algorithms)
🧠 LangGraph (State machine & GraphRAG)
📊 Model Context Protocol (MCP Tools)
🖥️ FastAPI + D3.js Analyst Dashboard

Read the full technical deep-dive and watch the demo:
📝 Blog: https://github.com/your-org/hhgoa-fraud-defense/blob/main/blog/draft.md
🎥 Demo: https://github.com/your-org/hhgoa-fraud-defense/blob/main/demo/script.md
💻 Code: https://github.com/your-org/hhgoa-fraud-defense

#TigerGraph #FraudDetection #GraphAI #LangGraph #FinTech #MachineLearning #AutonomousAgents

---

## 2. LinkedIn Long-Form Article / Post

### Title:
**LLM Reasons, Policy Engine Decides: How We Built an Autonomous Fraud Defense Agent on 590,000+ Transactions with TigerGraph**

### Post Body:
In high-stakes enterprise banking, handing a generative Large Language Model direct execution authority over card blocks and federal regulatory filings is an unacceptable operational risk. 

LLMs hallucinate entity relationships, produce non-reproducible outcomes, and fail regulatory scrutiny under FinCEN and SEC audit standards. Worse, when evaluated in isolation, machine learning fraud scores above 0.70 are overwhelmingly false positives.

For the **TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation Build**, our engineering team set out to solve this fundamental dilemma.

Our architectural thesis:
👉 **The LLM reasons, but the Policy Engine decides.**

Here is what we engineered across 590,742 transactions, 144,432 digital identities, and 5,565 historical closed cases:

### 1. Tripartite Autonomous Architecture
- **Reasoning Tier (LangGraph + GraphRAG):** The LLM acts as an investigative detective—formulating hypotheses, planning topological queries, evaluating simulated customer evidence, and drafting compliant 6–12 sentence FinCEN SAR narratives.
- **Topology Tier (TigerGraph & GSQL):** Native pointer-chasing graph engine maintaining pre-indexed chronological `NEXT` edge chains across payment cards, sub-millisecond card-testing detection (Rule R5), and multi-hop syndicate ring traversals (Rule R6).
- **Decision Tier (Pure Python, Zero LLM):** A deterministic Fraud Policy Engine executing Rules R1–R10 with role-based approval routing (`auto`, `L1 Team Lead`, `L2 Operations Manager`).

### 2. The Credibility Flex: Calibrated Against 5,565 Closed Bank Cases
We didn’t just build a prompt; we empirically calibrated and validated our system against 5,565 historical bank investigations:
- **Zero-Leakage Temporal Splitting:** Features strictly engineered before case `opened_at`.
- **Isotonic Probability Calibration:** Achieved **0.9950 ROC AUC** and a **0.0212 Brier Score**.
- **100.00% Policy Engine Agreement:** Evaluated across all 5,565 historical ground-truth cases, our engine achieved **100.00% Action Agreement** and **100.00% SAR Filing Agreement** with zero discrepancies.

### 3. Key Operational Highlights
- **Unmasking 51-Card Syndicates (Case HHG-014):** When an alert flagged a single $74.96 transaction on an unusual Android profile, GSQL query `device_neighbors` traversed the topology to reveal 51 other cards tied to the exact same device. Even at $74, Policy Section 3a mandated a FinCEN SAR filing due to shared syndicate origin.
- **Preventing False Alarm Card Blocks (Case HHG-018):** On a customer dispute for a $39 charge, the engine avoided a destructive card block by pausing at the Uncertainty Gate. Once customer verification confirmed an active subscription, Rule R7 took precedence over Rule R2, resolving the alert with zero customer friction.
- **The Graph Memory Flywheel:** Every completed case lands back in @TigerGraphDB as an `InvestigationCase` vertex, allowing subsequent alerts to retrieve topological memory and historical precedents in real-time.

Check out our full open-source repository, GSQL schemas, and interactive Analyst Dashboard!

🔗 **GitHub Repository:** https://github.com/your-org/hhgoa-fraud-defense  
📹 **Video Demo Script:** https://github.com/your-org/hhgoa-fraud-defense/blob/main/demo/script.md  
📄 **Technical Deep-Dive Blog:** https://github.com/your-org/hhgoa-fraud-defense/blob/main/blog/draft.md  

Special thanks to the @TigerGraphDB team for hosting the Hacker House Goa build!

#GraphDatabase #TigerGraph #GSQL #FraudPrevention #AutonomousAgents #GenerativeAI #FinTech #MachineLearning #RiskManagement

---

## 3. Short-Form Discord / Slack / Community Blast

**🚀 Autonomous Fraud Defense Agent on TigerGraph (590k+ Transactions)**

Just dropped our complete build for the **TigerGraph × HHGOA IEEE Fraud Investigation Challenge**!

Key engineering takeaways:
- **"LLM Reasons, Policy Engine Decides":** Zero-LLM pure Python policy engine enforces Rules R1–R10, while LangGraph + GraphRAG orchestrates topological evidence gathering.
- **GSQL at Scale:** Chronological `NEXT` chains detect card testing in <4ms; multi-hop traversals uncover 51-card device syndicates.
- **Rigorous Ground-Truth Validation:** 5-fold isotonic calibrator hits **0.9950 ROC AUC** & **0.0212 Brier score** against 5,565 closed bank cases with **100.00% Action & SAR Agreement**.
- **One-Screen Analyst Dashboard:** Interactive D3 topology subgraph, 11-step timeline stepper, route diffing, and mock action execution service.

Check out the code, blog, and demo script:
👉 https://github.com/your-org/hhgoa-fraud-defense
