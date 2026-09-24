# Defensible Evidence Simulation Policy

**TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation**  
**Phase 5: Out-of-Band Evidence Simulation & Assumption Governance**

---

## 1. Executive Summary & Purpose

Fraud Policy v1.0 Section 5 explicitly authorizes the autonomous agent to gather further evidence:
> *"The agent may, without approval, ask the customer to validate a transaction, request step-up authentication, or request information from an analyst. In this round those responses are not provided. Simulate them in your own system and state the assumption you made in the case file's `evidence_requests`."*

Because real cardholders and human compliance analysts cannot be queried interactively in a production-batch benchmark, this **Defensible Evidence Simulation Policy** governs how our agent simulates external evidence. Rather than generating random or arbitrary answers, every simulated response is strictly anchored in empirical graph signals, historical baseline distributions, and authoritative policy rules (Rules R1, R2, R3, R4, R5, R6, R7, R8, R9, and R10).

Every simulated interaction is recorded verbatim in the answer file's `evidence_requests` array with the exact `asked_after_step` counter, satisfying scoring requirements.

---

## 2. Core Simulation Principles

1. **Principle of Empirical Conservation**: Never assume customer denial unless objective graph evidence (unrecognized hardware profile, anonymous proxy, multi-region cloning, rapid velocity burst, or testing probe sequence) indicates a high probability of compromise ($p \ge 0.70$).
2. **Principle of Non-Interference with Legitimate Cardholders (Policy R1)**: If a transaction occurs within the cardholder's historical billing region, aligns with spending percentiles, and lacks credential anomalies, the simulation must reflect authorized activity to prevent policy breaches (false-positive card blocks).
3. **Precedence of Recurring Subscription History (Policy R7)**: When a disputed transaction matches the merchant, monthly periodicity, and historical dollar amount of previous recurring billing cycles, the simulation assumes customer confirmation of an overlooked recurring agreement rather than card compromise.
4. **Verbatim Audit Traceability**: Every simulated assumption is captured verbatim in `evidence_requests.assumed_response` and cited in the final investigation summary.

---

## 3. Typology-Specific Assumption Matrix

| Scenario / Typology | Empirical Graph Trigger | Simulated Evidence Type | Assumed Response Recorded | Impact on Verdict & Actions |
|---|---|---|---|---|
| **A. Recurring Subscription Dispute** | Charge amount and merchant match historical monthly cadence (Rule R7) | `customer_validation` | `"Customer confirms — recurring subscription: 'I recognize this recurring merchant charge of $... I had forgotten about this monthly subscription service agreement.'"` | Verdict: `legitimate`<br>Actions: `CREATE_CASE`, `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER`<br>**No card block (Rule R7)** |
| **B. Legitimate Travel Footprint** | Out-of-region in-person purchase with continuous regional stay and zero concurrent home activity | `customer_validation` | `"Customer confirms — was traveling: 'I was traveling out of state during that time and made this in-person purchase of $... myself. My card was not compromised.'"` | Verdict: `legitimate`<br>Actions: `CLOSE_NO_FRAUD` (Rule R3)<br>No card block, no SAR |
| **C. Home Baseline False Alarm** | Transaction in primary region (`addr1`), amount $\le 75\text{th}$ percentile, no new device | `customer_validation` | `"Customer confirms — authorized purchase: 'Yes, I made this purchase. It was me shopping locally at my normal merchant.'"` | Verdict: `legitimate`<br>Actions: `CLOSE_NO_FRAUD` (Rule R3)<br>Exposure: $0.00 |
| **D. High-Confidence Digital Fraud** | New hardware profile (`id_15='New'`), proxy (`id_23`), ATO channel switch, testing sequence, or $p \ge 0.70$ | `customer_validation` | `"Customer denies and still has card: 'I never made or authorized any purchase for $... I still have my physical card with me in my wallet right now. Please block it immediately.'"` | Verdict: `fraud`<br>Actions: `BLOCK_CARD` (L1/L2), `CREATE_CASE`<br>SAR evaluation if $> \$1,000$ |
| **E. 24-Hour Timeout Non-Response** | Simulated cardholder unresponsiveness across SMS/email channels | `customer_validation` | `"Customer verification request timed out after 24 hours with no reply across registered mobile SMS, email, and automated voice channels (Policy R4)."` | Verdict: `uncertain`<br>Actions: `MONITOR_CARD`, `DECLINE_TRANSACTION` (L1), `ESCALATE_TO_ANALYST` if $> \$500$ |
| **F. Step-Up Authentication (Testing/Burst)** | Micro-authorization probe sequence or sudden online velocity spike | `step_up_auth` | **Fraudster**: `"Step-up authentication challenge failed: SMS one-time passcode was not entered within the 5-minute validity window."`<br>**Cardholder**: `"Step-up authentication completed successfully via registered mobile banking authenticator app."` | Failed: confirms compromise $\to$ `BLOCK_CARD`<br>Success: clears alert $\to$ `ALLOW_TRANSACTION` |
| **G. Forensic Analyst Information** | Complex syndicate ring, multi-card fanout, or undocumented pattern | `analyst_info` | `"Senior fraud analyst reviewed forensic memory: confirms device profile and merchant descriptor align directly with confirmed fraud cases CC-XXXX and CC-YYYY. Recommended card block and regulatory escalation."` | Links prior closed cases via `SIMILAR_TO`<br>Triggers `ESCALATE_TO_ANALYST` & SAR |

---

## 4. Two-Route Capture & Next Best Action Evolution

Fraud Policy v1.0 Section 3b requires recording recommendations both before and after evidence gathering:
- **`next_best_actions.initial`**: Computed during Node 6 (`POLICY_EVAL`) strictly based on the initial alert data and graph query findings. For alerts with weak signals or unconfirmed customer status, this route mandates verification (`VERIFY_WITH_CUSTOMER`) or challenge (`STEP_UP_AUTH`), strictly gating irreversible card blocks under Rule R1.
- **`next_best_actions.final`**: Computed during Node 9 (`POLICY_EVAL_FINAL`) after incorporating the simulated customer/analyst evidence.
- **`what_changed`**: Explains the exact evidence delta (e.g. how customer denial confirmed unauthorized physical possession of the card, shifting the recommendation from verification to L1 `BLOCK_CARD` and L2 `FILE_REPORT`).

---

## 5. Stopping Criteria Enforcement (Policy Section 6)

The simulation engine halts further questioning whenever:
1. **Verification Settles the Question**: An explicit customer confirmation (legitimate) or denial (fraud) establishes conclusive ground truth.
2. **Definitive Probability Extremes**: Fraud probability reaches $\ge 0.85$ (strongly suspected fraud) or $\le 0.15$ (cleared legitimate) supported by $\ge 2$ independent pieces of evidence.
3. **Maximum Evidence Rounds Reached**: Gated at a maximum of 2 rounds to prevent endless execution loops.
4. Every investigation records its exact rationale in the top-level `stop_reason` field.
