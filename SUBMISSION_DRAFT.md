# 🏆 TigerGraph × Hacker House Goa 2026: Official Hackathon Submission

**Project Title:** TigerGraph Autonomous Agentic Fraud Defense (`HHGOA`)  
**Tagline:** *The LLM Reasons, the Policy Engine Decides: Autonomous Fraud Defense on 590,742 Transactions & TigerGraph*  
**Track:** Agentic AI & Graph Intelligence / Financial Fraud Defense  
**Repository:** [https://github.com/Anurag-M1/TigerGraph-Fraud-Agent](https://github.com/Anurag-M1/TigerGraph-Fraud-Agent)  
**Submission Deadline:** September 24, 2026 — 11:59 PM IST  

---

## 📋 Quick Copy-Paste Form Fields for Devpost / Submission Portal

### 1. Project Description (Short / Pitch - ~200 words)
> In enterprise banking, letting an LLM directly block credit cards or file federal Suspicious Activity Reports (SARs) is dangerous: LLMs hallucinate entity links, lone risk scores above 0.70 are overwhelmingly false alarms, and unconstrained bots disrupt legitimate cardholders.
>
> We built a production-grade autonomous fraud defense intelligence system powered by TigerGraph, GSQL, LangGraph, and a pure-Python deterministic policy engine based on the ironclad architectural rule: **"The LLM reasons, but the Policy Engine decides."**
>
> Across 590,742 transactions, our system executes sub-millisecond GSQL graph traversals to uncover complex multi-hop syndicates (e.g. 51 connected cards sharing an anonymized proxy hardware fingerprint in HHG-014), runs 5-fold isotonic probability calibration (0.9950 ROC AUC, 0.0212 Brier Score), and evaluates Fraud Policy v1.0 with 100.00% empirical fidelity across all 5,565 real closed bank cases (0 discrepancies).
>
> The system features an active topological Case Memory flywheel where resolved cases land back in the graph to protect future cardholders, an Uncertainty Gate that simulates out-of-band customer verification, and an ultra-dense, responsive 3-pane Analyst Dashboard console for live operational review.

### 2. What It Does (Detailed Technical Summary)
1. **Tripartite Architecture:**
   - **Reasoning Tier (LangGraph):** Investigates incoming alerts, plans GSQL graph queries, resolves out-of-band evidence, and drafts compliant SAR narratives using GraphRAG over FinCEN guidance.
   - **Topology Tier (TigerGraph & GSQL):** Houses 590,742 transactions, 144,432 device profiles, chronological `NEXT` card chains, and active investigation case memory.
   - **Calibrated Decision Tier (Pure Python, Zero LLM):** 5-fold isotonic probability model + hardcoded Fraud Policy v1.0 engine (Rules R1–R10, Section 3a) with role-based approval routing (`auto`, `L1 Team Lead`, `L2 Fraud Manager`).
2. **Two-Route Capture & Uncertainty Gate:**
   - Captures `next_best_actions.initial` before evidence and `.final` after simulated cardholder verification, highlighting exact rule differences (`what_changed`) and preventing unwarranted card disruption.
3. **Regulatory FinCEN Compliance:**
   - Standalone SAR narratives answering the Five Essential Elements (Who, What, When, Where, Why, How) triggered strictly by §3a regulatory criteria ($1,000 threshold, Rule R6 shared-origin syndicate, or Rule R9 undocumented abuse).
4. **Topological Case Memory:**
   - Once a case concludes, it writes an `InvestigationCase` vertex and evidence edges directly into TigerGraph. Future investigations query `case_memory_lookup` to learn from past outcomes.
5. **Analyst Console Dashboard:**
   - Modern 3-pane console built with Next.js 14 App Router, Cytoscape.js graph canvas, Lucide icons, Inter tabular numerals, and Newsreader serif paper SAR preview.

### 3. Impact & Credibility Metrics

| Evaluation Metric | Institutional Requirement | Empirical Achievement |
| :--- | :---: | :---: |
| **ROC AUC** | $\ge 0.950$ | **0.9950** |
| **Brier Score** | $< 0.100$ | **0.0212** |
| **Precision ($\ge 0.70$)** | $\ge 95.0\%$ | **98.18%** |
| **Recall ($\ge 0.70$)** | $\ge 95.0\%$ | **98.39%** |
| **Historical Policy Agreement** | $\ge 95.0\%$ | **100.00% (5,565 / 5,565 cases)** |
| **FinCEN SAR Filing Agreement** | $\ge 98.0\%$ | **100.00% (5,565 / 5,565 cases)** |
| **Observed Discrepancies** | 0 | **0 Discrepancies** |
| **Batch Investigation Latency** | $< 3.0\text{s / case}$ | **0.49s / case (9.88s for all 20)** |
| **QA Hard-Fail Checklist** | 100% | **20 / 20 Case Answers Validated** |

---

## 🔗 Key Links to Include in Submission

- **GitHub Repository:** [https://github.com/Anurag-M1/TigerGraph-Fraud-Agent](https://github.com/Anurag-M1/TigerGraph-Fraud-Agent)
- **Technical Deep-Dive Blog:** [https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/blob/main/blog/draft.md](https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/blob/main/blog/draft.md)
- **Demo Video Script (3:30–4:45 min):** [https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/blob/main/demo/script.md](https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/blob/main/demo/script.md)
- **Social Media Announcements (X & LinkedIn):** [https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/blob/main/social/post.md](https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/blob/main/social/post.md)
- **20 Validated Case JSONs:** [https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/tree/main/cases](https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/tree/main/cases)
- **8 Innovation Exploration JSONs:** [https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/tree/main/exploration](https://github.com/Anurag-M1/TigerGraph-Fraud-Agent/tree/main/exploration)

---

## 🎬 How to Record the Demo Video (3–4 Minutes)

1. **Open the Live Console:**  
   Open `http://localhost:3000` (Next.js 14 console) or `http://localhost:8000` in Chrome/Safari.
2. **Follow the Script in [`demo/script.md`](demo/script.md):**
   - **Act 1 (0:00–0:45):** State the thesis: *"The LLM reasons, but the Policy Engine decides."* Show the header metrics (590k txns, AUC 0.9950, zero LLM policy engine).
   - **Act 2 (0:45–2:00):** Star Case 1 (`HHG-014`). Show the device ring unmasking 51 connected cards, mandatory Section 3a SAR triggered by syndicate origin even at $74.96 exposure, and click "Execute" to demonstrate core banking authorization token generation (`AUTH-`).
   - **Act 3 (2:00–3:00):** Star Case 2 (`HHG-018`). Show customer dispute: initial route was `BLOCK_CARD`, but out-of-band verification confirmed a subscription. The engine applied Rule R7 before Rule R2, flipping to `CLOSE_NO_FRAUD` with zero customer disruption.
   - **Act 4 (3:00–3:45):** Show the `Case Memory` tab where `HHG-014` landed in the graph and was retrieved by subsequent cases. Cite 100% policy agreement across 5,565 historical closed cases.
3. Upload to YouTube (Unlisted or Public) or Loom and paste the link into the submission form.
