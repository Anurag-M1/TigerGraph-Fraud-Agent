# Closed-Case Anatomy — HHGOA_IEEE

**Source**: `closed_cases_history.csv` — 5,565 cases, July–October 2016

## 1. Pattern Distribution

| Pattern | Count | % |
|---|---|---|
| `card_not_present_fraud` | 1,404 | 25.2% |
| `account_takeover` | 1,205 | 21.7% |
| `card_not_present_new_device` | 1,076 | 19.3% |
| `out_of_region_use` | 955 | 17.2% |
| `none` | 900 | 16.2% |
| `card_testing` | 16 | 0.3% |
| `undocumented` | 9 | 0.2% |

## 2. Outcome × Pattern Matrix

| Outcome | `account_takeover` | `card_not_present_fraud` | `card_not_present_new_device` | `card_testing` | `none` | `out_of_region_use` | `undocumented` | **Total** |
|---|---|---|---|---|---|---|---|---|
| `cleared` | 0 | 0 | 0 | 0 | 900 | 0 | 0 | **900** |
| `confirmed_fraud` | 1205 | 1404 | 1076 | 16 | 0 | 955 | 9 | **4665** |

## 3. Exposure Distribution per Outcome

| Outcome | Count | Min | P25 | Median | P75 | Max | Mean |
|---|---|---|---|---|---|---|---|
| `confirmed_fraud` | 4,665 | $1.00 | $70.08 | $170.92 | $400.01 | $35,031.56 | $444.24 |
| `cleared` | 900 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 |

## 4. Exposure by Fraud Pattern

| Pattern | Cases | Median $ | Mean $ | Max $ |
|---|---|---|---|---|
| `account_takeover` | 1,205 | $252.40 | $752.65 | $35,031.56 |
| `card_not_present_fraud` | 1,404 | $100.02 | $162.63 | $2,499.98 |
| `card_not_present_new_device` | 1,076 | $178.43 | $324.79 | $18,477.45 |
| `card_testing` | 16 | $677.72 | $1,273.16 | $4,886.18 |
| `out_of_region_use` | 955 | $234.93 | $582.96 | $19,692.61 |
| `undocumented` | 9 | $1,871.13 | $1,171.27 | $1,922.65 |

## 5. `actions_taken` Vocabulary

| Action | Frequency |
|---|---|
| `CREATE_CASE` | 4,665 |
| `BLOCK_CARD` | 4,665 |
| `VERIFY_WITH_CUSTOMER` | 900 |
| `CLOSE_NO_FRAUD` | 900 |
| `FILE_REPORT` | 397 |

### Action Combinations (top 10)

| Combo | Count |
|---|---|
| `CREATE_CASE|BLOCK_CARD` | 4,268 |
| `VERIFY_WITH_CUSTOMER|CLOSE_NO_FRAUD` | 900 |
| `CREATE_CASE|BLOCK_CARD|FILE_REPORT` | 397 |

## 6. `report_filed` Analysis

### report_filed by Outcome

| Outcome | `No` | `Yes` |
|---|---|---|
| `cleared` | 900 | 0 |
| `confirmed_fraud` | 4268 | 397 |

### Exposure threshold for report filing (confirmed_fraud only)

- Filed Yes: 397 cases, exposure min=$108.36, median=$1,800.08, mean=$2,808.16
- Filed No: 4268 cases, exposure min=$1.00, median=$150.00, mean=$224.36

### report_filed by Pattern (confirmed_fraud only)

| Pattern | `No` | `Yes` |
|---|---|---|
| `account_takeover` | 1018 | 187 |
| `card_not_present_fraud` | 1390 | 14 |
| `card_not_present_new_device` | 1020 | 56 |
| `card_testing` | 9 | 7 |
| `out_of_region_use` | 831 | 124 |
| `undocumented` | 0 | 9 |

## 7. Connected Cards Analysis

- Fraud cases with connected cards: 4 / 4665 (0.1%)
- Connected cards per case: median=23, max=23

## 8. Undocumented Pattern Cases — Analyst Notes (verbatim)

**Total undocumented cases**: 9

### Case 1: `CC-2649` — confirmed_fraud — $390.04

> Case CC-2649: cardholder C03528 reported 3 online purchase(s) they did not make. The purchases came from a Samsung SM-G935F on Chrome for Android behind an anonymous proxy, a device never seen on this account. Two other cardholders reported the same device profile this month. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C03528-K1` | **Customer**: `C03528`
- **Txns**: 3 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes
- **Connected cards**: `C00255-K1|C01935-K1|C03551-K2|C03744-K1|C04311-K1|C06197-K2|C06617-K1|C07485-K1|C07762-K1|C08112-K2|C09174-K1|C09354-K1|C09733-K1|C09998-K1|C10350-K1|C10955-K2|C11468-K2|C11687-K2|C12033-K1|C12132-K2|C12395-K2|C12574-K1|C12900-K2`

### Case 2: `CC-2971` — confirmed_fraud — $108.36

> Case CC-2971: cardholder C09998 reported 2 online purchase(s) they did not make. The purchases came from a Samsung SM-G935F on Chrome for Android behind an anonymous proxy, a device never seen on this account. Two other cardholders reported the same device profile this month. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C09998-K1` | **Customer**: `C09998`
- **Txns**: 2 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes
- **Connected cards**: `C00255-K1|C01935-K1|C03528-K1|C03551-K2|C03744-K1|C04311-K1|C06197-K2|C06617-K1|C07485-K1|C07762-K1|C08112-K2|C09174-K1|C09354-K1|C09733-K1|C10350-K1|C10955-K2|C11468-K2|C11687-K2|C12033-K1|C12132-K2|C12395-K2|C12574-K1|C12900-K2`

### Case 3: `CC-2985` — confirmed_fraud — $381.40

> Case CC-2985: cardholder C06617 reported 3 online purchase(s) they did not make. The purchases came from a Samsung SM-G935F on Chrome for Android behind an anonymous proxy, a device never seen on this account. Two other cardholders reported the same device profile this month. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C06617-K1` | **Customer**: `C06617`
- **Txns**: 3 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes
- **Connected cards**: `C00255-K1|C01935-K1|C03528-K1|C03551-K2|C03744-K1|C04311-K1|C06197-K2|C07485-K1|C07762-K1|C08112-K2|C09174-K1|C09354-K1|C09733-K1|C09998-K1|C10350-K1|C10955-K2|C11468-K2|C11687-K2|C12033-K1|C12132-K2|C12395-K2|C12574-K1|C12900-K2`

### Case 4: `CC-3035` — confirmed_fraud — $140.95

> Case CC-3035: cardholder C09733 reported 2 online purchase(s) they did not make. The purchases came from a Samsung SM-G935F on Chrome for Android behind an anonymous proxy, a device never seen on this account. Two other cardholders reported the same device profile this month. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C09733-K1` | **Customer**: `C09733`
- **Txns**: 2 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes
- **Connected cards**: `C00255-K1|C01935-K1|C03528-K1|C03551-K2|C03744-K1|C04311-K1|C06197-K2|C06617-K1|C07485-K1|C07762-K1|C08112-K2|C09174-K1|C09354-K1|C09998-K1|C10350-K1|C10955-K2|C11468-K2|C11687-K2|C12033-K1|C12132-K2|C12395-K2|C12574-K1|C12900-K2`

### Case 5: `CC-3748` — confirmed_fraud — $1,905.21

> Case CC-3748: cardholder C12267 reported four online purchases within forty minutes, each just under $500, none of which they made. Amounts appear chosen to stay under a $500 authorization threshold. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C12267-K2` | **Customer**: `C12267`
- **Txns**: 4 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes

### Case 6: `CC-3841` — confirmed_fraud — $1,899.30

> Case CC-3841: cardholder C01099 reported four online purchases within forty minutes, each just under $500, none of which they made. Amounts appear chosen to stay under a $500 authorization threshold. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C01099-K1` | **Customer**: `C01099`
- **Txns**: 4 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes

### Case 7: `CC-3907` — confirmed_fraud — $1,922.65

> Case CC-3907: cardholder C03060 reported four online purchases within forty minutes, each just under $500, none of which they made. Amounts appear chosen to stay under a $500 authorization threshold. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C03060-K1` | **Customer**: `C03060`
- **Txns**: 4 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes

### Case 8: `CC-4086` — confirmed_fraud — $1,871.13

> Case CC-4086: cardholder C13269 reported four online purchases within forty minutes, each just under $500, none of which they made. Amounts appear chosen to stay under a $500 authorization threshold. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C13269-K2` | **Customer**: `C13269`
- **Txns**: 4 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes

### Case 9: `CC-4124` — confirmed_fraud — $1,922.37

> Case CC-4124: cardholder C02838 reported four online purchases within forty minutes, each just under $500, none of which they made. Amounts appear chosen to stay under a $500 authorization threshold. Pattern not matched to a documented typology. Card blocked and reissued.

- **Card**: `C02838-K1` | **Customer**: `C02838`
- **Txns**: 4 | **Actions**: `CREATE_CASE|BLOCK_CARD|FILE_REPORT`
- **Report filed**: Yes

## 9. Date Ranges

- **opened_at**: `2016-07-02 07:17:26` → `2016-11-02 02:00:37`
- **closed_at**: `2016-07-04 02:10:20` → `2016-11-06 23:39:58`

---
*Generated by `scripts/closed_case_anatomy.py`*
