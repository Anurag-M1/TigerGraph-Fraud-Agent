# TigerGraph × HHGOA IEEE Fraud Investigation: Demo Video Script
**Target Duration:** 3:30 – 4:45 minutes  
**Format:** Video Screen Recording + Voiceover & Camera PiP  
**System URL:** `http://localhost:8000` (Analyst Dashboard)  
**Lead Engineer / Presenter:** Autonomous Fraud Intelligence Lead  

---

## Storyboard & Timing Overview

| Timestamp | Phase / Scene | Screen / Focus | Key Talking Points |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:45** | **1. System Architecture & The Core Rule** | Dashboard Hero View (`http://localhost:8000`), System Status Pills | *"LLM Reasons, Policy Engine Decides"*: 590,742 transactions, GSQL topology, calibrated GBDT (0.995 AUC), Zero-LLM deterministic policy engine. |
| **0:45 – 2:05** | **2. Star Case 1: HHG-014 (Syndicate Ring & Rule R6)** | Case Selector $\to$ `HHG-014`, Live D3 Subgraph, 11-Step Stepper, SAR Modal | GSQL `device_neighbors` unmasks 51 connected cards; SAR §3a triggered by syndicate origin; "Approve & Execute" hitting mock action service. |
| **2:05 – 3:15** | **3. Star Case 2: HHG-018 (The Customer Dispute Fork)** | Case Selector $\to$ `HHG-018`, Route Diff Grid, Step 7 Out-of-Band Simulation | Rule R7 vs Rule R2 precedence: customer dispute starts with card block prior, flips to `CLOSE_NO_FRAUD` after subscription verification; zero customer disruption. |
| **3:15 – 4:05** | **4. The Graph Memory Flywheel** | Case Memory Tab, Graph Read-Back, Next Case Run | Case landing in graph as `InvestigationCase` and `EvidenceItem`; subsequent alerts retrieve prior decisions as topological memory. |
| **4:05 – 4:35** | **5. Credibility & Conclusion** | Benchmark Ledger, Summary KPIs | Validated against 5,565 closed bank cases (100% Action & SAR Agreement); production-ready autonomous defense. |

---

## Detailed Spoken Script & Screen Actions

### Scene 1: System Introduction & "LLM Reasons, Policy Engine Decides" (0:00 – 0:45)

**[VISUAL CUE]:**
- Open browser to `http://localhost:8000`.
- Mouse hovers over top navigation status pills:
  - `GSQL Graph: 590,742 Txns`
  - `GBDT Calibrated: AUC 0.9950`
  - `Policy v1.0: Zero LLM`
- Pan camera across the clean, dark-mode glassmorphic dashboard.

**[SPEAKER NOTES]:**
> *"Welcome to the TigerGraph Autonomous Fraud Defense Intelligence system, built for Hacker House Goa.
>
> In high-stakes banking, you cannot let an LLM directly block credit cards or file federal Suspicious Activity Reports. LLMs hallucinate, produce non-deterministic outputs, and fail regulatory audits.
>
> Our solution is built on a fundamental architectural principle: **The LLM reasons, but the Policy Engine decides.**
>
> Over 590,000 transactions and 5,500 historical cases live inside our TigerGraph database. An intelligent LangGraph multi-agent loop formulates hypotheses, executes GSQL graph queries, and gathers objective topological evidence. But when it comes to containment actions and FinCEN SAR filings, our pure Python policy engine evaluates Fraud Policy v1.0 with mathematical determinism."*

---

### Scene 2: Star Case 1 — HHG-014 (The Syndicate Device Ring & Policy R6 Fan-Out) (0:45 – 2:05)

**[VISUAL CUE]:**
- In the top dropdown or Quick Filter strip, click **"Confirmed Fraud"** and select **`HHG-014`**.
- The screen updates immediately:
  - Top Trigger Badge: `analyst_request` on device profile `SM-G935F Build/NRD90M`.
  - KPI 1 (Verdict): `🚨 Confirmed Fraud · CLOSED_FRAUD`
  - KPI 2 (Gauge): Calibrated Fraud Probability: `0.92` (Rose arc)
  - KPI 3 (Exposure): `$74.96 USD` (Sub-$1,000, 1 affected transaction)
  - KPI 5 (FinCEN SAR): `MANDATORY §3a (Shared Origin Ring)`
- Scroll down slightly to showcase the **11-step numbered timeline stepper**.
- Click **"▶ Play"** on the VCR replay controls; watch the stepper advance from Step 1 (`TRIGGER`) through Step 6 (`POLICY_EVAL`), pause briefly on Step 7 (`REQUEST_EVIDENCE` highlighted in amber), and complete at Step 11 (`EMIT_ANSWER`).
- Point to the **D3.js Entity Neighborhood Subgraph** on the bottom left:
  - Hover over the Central Card `C13487-K1`, the device node `SM-G935F`, and the cluster of connected ring cards.

**[SPEAKER NOTES]:**
> *"Let's look at our first star case: **HHG-014**.
>
> This case started from an analyst alert regarding an unusual Android device profile. Watch what happens when our agent executes the GSQL query `device_neighbors`:
>
> In sub-milliseconds, the graph topology reveals that this exact device fingerprint—running an anonymized proxy—connects to **51 other payment cards** across the bank!
>
> Now notice the financial exposure: it's only **$74.96**. Under standard bank rules, a $74 charge would never trigger a regulatory filing because it is well below the $1,000 FinCEN threshold.
>
> But look at the SAR KPI: it reads **MANDATORY §3a**.
>
> Our policy engine correctly enforced Fraud Policy Rule R6 and Section 3a: any confirmed fraud originating from a shared device syndicate mandates an immediate federal SAR filing, regardless of dollar amount."*

**[VISUAL CUE]:**
- Scroll to Row 3 (Route Comparison):
  - Point to the final recommendations list: `CREATE_CASE` (auto), `BLOCK_CARD` (L1), `MONITOR_CONNECTED_CARDS` (auto, Rule R6), and `FILE_REPORT` (L2).
- Click the green **"✓ Approve & Execute (L1)"** button next to `BLOCK_CARD`.
  - Button transitions to `✓ Approved & Executed` showing an authorization token like `AUTH-20260924-E821B0`.
- Click the top navigation **"SAR Preview"** button:
  - The FinCEN SAR modal opens.
  - Highlight the 5 essential elements standalone narrative (Who, What, When, Where, Why, How), subject IDs (`C13487`, `C13487-K1`, `3478561`, `SM-G935F...`), and exact dates.
- Click **"📋 Copy Narrative"** (button flashes `✓ Copied!`), then close modal.

**[SPEAKER NOTES]:**
> *"Here in the route comparison, the policy engine recommends:
> 1. Automated internal case creation,
> 2. L1-approved card block,
> 3. Automated sensitivity elevation across all 51 connected cards (`MONITOR_CONNECTED_CARDS`), and
> 4. L2 supervisory approval for the FinCEN report.
>
> With one click on 'Approve & Execute', our mock action service generates an immutable banking authorization code and logs the containment action.
>
> And opening the SAR Preview, our GraphRAG generator drafts a 6-to-12 sentence compliant narrative with all five essential elements ready for FinCEN submission."*

---

### Scene 3: Star Case 2 — HHG-018 (The Customer Dispute Fork: Rule R7 vs Rule R2) (2:05 – 3:15)

**[VISUAL CUE]:**
- In the filter strip, click **"Legitimate Clearances"** and select **`HHG-018`**.
- Screen instantly transitions:
  - Trigger: `customer_report` on card `C02354-K2` ($39.08 charge).
  - KPI 1: `🛡️ Legitimate Clearance · CLEARED`
  - KPI 2: Calibrated Probability drops to `0.18` (Emerald arc)
  - KPI 3: Total Financial Exposure: `$0.00 USD` (Zero loss)
  - KPI 5: SAR Status: `NOT REQUIRED`
- Focus on Row 3: **Dual Route Comparison Grid (Initial vs. Final)**:
  - Zoom in on Initial Recommendations: `[CREATE_CASE (auto), BLOCK_CARD (L1)]` evaluated at Step 6.
  - Read the Center **What Changed Highlight**:
    `"Customer confirmation resolved the unverified alert. Recommended actions shifted from pre-investigation verification (CREATE_CASE, BLOCK_CARD) to immediate legitimate closure (CLOSE_NO_FRAUD) under Rule R3. Zero financial loss sustained."`
  - Point to Final Recommendations: `[CLOSE_NO_FRAUD (auto)]` evaluated at Step 9.
- Click on Step 7 in the horizontal stepper:
  - Show active step card: `REQUEST_EVIDENCE (asked_after_step: 6)`.
  - Show simulated response: *"Customer confirms — recurring subscription: 'I recognize this recurring merchant charge of $39.08. I had forgotten about this monthly subscription service agreement.'"*

**[SPEAKER NOTES]:**
> *"Now let's examine our second star case: **HHG-018**, showcasing the critical customer dispute fork between Rule R7 and Rule R2.
>
> When a customer reports an unrecognized charge, the initial signal looks like fraud.
>
> Notice the pre-evidence recommendation at Step 6: the engine initially prepared to block the card under Rule R2 to prevent further loss.
>
> But our agent hits the **Uncertainty Gate**. Instead of blindly executing a destructive block, it formulates an out-of-band customer verification request after Step 6.
>
> The simulated customer response arrives: the cardholder remembers that the $39 charge is their legitimate monthly subscription!
>
> Look at what happens side-by-side:
> Our policy engine enforces strict precedence: **Rule R7 for recurring subscriptions is checked before Rule R2**.
>
> The recommendation immediately shifts from a destructive card block to `CLOSE_NO_FRAUD`. The customer's card remains active, legitimate business revenue is protected, and zero unnecessary customer friction occurs."*

---

### Scene 4: The Graph Memory Flywheel (3:15 – 4:05)

**[VISUAL CUE]:**
- Switch to the bottom-right panel and click the **"Case Memory"** tab.
- Hover over the case memory cards showing retrieved prior closed cases (`similar_prior_cases`), outcomes (`closed_fraud` / `cleared`), and topological match reasons.
- Point to the active case record:
  - `written_to_graph: true`
  - `graph_case_id: CASE-HHG-018`
- Open the terminal or click the **"Run Live Agent"** button on `HHG-010`:
  - Show the live agent running, querying `case_memory_lookup`, matching against `fraud_graph.db`, and retrieving historical case vertices.

**[SPEAKER NOTES]:**
> *"Every time an investigation finishes, our agent does not discard the finding—it persists the case directly back into TigerGraph.
>
> It creates an `InvestigationCase` vertex with linked `EvidenceItem` nodes and topology relationships.
>
> When the NEXT case arrives—whether it's five seconds or five weeks later—the agent executes GSQL query `case_memory_lookup`. It queries the local entity neighborhood and instantly retrieves prior case outcomes, patterns, and historical analyst notes.
>
> This creates an autonomous memory flywheel: every investigation enriches the institutional graph, continuously lowering uncertainty for future cases."*

---

### Scene 5: Credibility & Conclusion (4:05 – 4:35)

**[VISUAL CUE]:**
- Return to the full dashboard overview on `HHG-010`.
- Open the **Audit Log** drawer from the top nav to show real executed authorization codes.
- Display the validation summary: 20/20 case-pack files valid, 8/8 exploration files valid, 5,565 closed cases validated.

**[SPEAKER NOTES]:**
> *"How do we know this system is production-ready?
>
> We benchmarked our probability calibration and policy engine against **all 5,565 historical closed cases** from the bank:
> - Our isotonic model achieved an **ROC AUC of 0.9950** and a **Brier score of 0.0212**.
> - And our Policy Engine achieved **100.00% Action Agreement** and **100.00% SAR Agreement** with zero discrepancies against actual historical bank decisions.
>
> All 20 case-pack alerts and 8 newly discovered exploration cases are 100% validated against the strict IEEE schema.
>
> TigerGraph provides the sub-second graph speed, LangGraph provides the reasoning, and our Policy Engine provides the deterministic control.
>
> Thank you."*

---

## Technical Setup & Demo Checklist

Before hitting record on OBS / Loom:
1. Ensure the backend server is running: `python3 ui/server.py` on `http://localhost:8000`.
2. Clear any browser zoom; set resolution to 1080p (1920x1080) for crisp typography.
3. Test audio levels on microphone.
4. Verify that clicking "Approve & Execute" on an action generates an `AUTH-...` token in real time.
5. Have `HHG-014` loaded initially as the primary fraud case, ready to transition to `HHG-018` for the recurring dispute fork.
