# PRJ-001 Valuation and Market Expectations

Status: reviewed research worksheet / not an investment recommendation

Updated: 2026-07-30

Project: PRJ-001

Company: Microsoft

Ticker / market: MSFT / NasdaqGS

Price as of: 2026-07-29 regular-session close

Financial inputs as of: 2026-03-31, unless otherwise stated

Reviewer: max

Review decision: approve the bounded worksheet

## Scope and valuation identity

This first v0.2 instance tests a simple enterprise-value-to-revenue identity:

```text
Equity value = dated share price × latest disclosed diluted weighted-average shares
Enterprise value = equity value + current debt + long-term debt
                   − cash and short-term investments
FY26E revenue = FY26 nine-month reported revenue + Q4 company-guidance range
EV / FY26E revenue = enterprise value ÷ FY26E revenue
```

All currency values are USD. This is a transparent market-expectations worksheet,
not a DCF, price target or buy/sell recommendation. The share-price date and balance
sheet date differ by four months, and weighted-average diluted shares are a reporting
period measure rather than an exact current share count.

## Observed facts

| Fact | Period / timestamp | Source or reviewed Event ID | Attribution limit |
|---|---|---|---|
| MSFT regular-session close was $390.5400085 | 2026-07-29 20:00:01 UTC | `SRC-20260730-039` | C-grade third-party market-data snapshot; archived raw JSON and hash |
| Diluted weighted-average shares were 7.445 billion | FY26 Q3 | `SRC-20260429-001`, extracted lines 631–642 | Weighted average, not exact shares outstanding at the price date |
| Cash and short-term investments were $78.272 billion | 2026-03-31 | `SRC-20260429-001`, extracted lines 700–712 | Four months older than the price |
| Current and long-term debt were $8.839 billion and $31.423 billion | 2026-03-31 | `SRC-20260429-001`, extracted lines 757–789 | Excludes lease and other non-debt enterprise-value adjustments |
| FY26 nine-month revenue was $241.832 billion | Nine months ended 2026-03-31 | `SRC-20260429-001`, official income statement | Company-wide revenue, not Agent revenue |
| Q4 total-company revenue guidance was $86.7–$87.8 billion | FY26 Q4 outlook | `SRC-20260730-038`, extracted line 262 | Forward-looking company guidance |
| Paid M365 Copilot seats exceeded 20 million, while other Agent measures use different units | FY26 Q3 | `EVT-20260429-031` | Does not establish consolidated Agent revenue or unit economics |

## Market expectations

No licensed sell-side consensus dataset is used. Microsoft management guidance is
the explicit expectations input.

| Measure | Fiscal period | Point / range | Provider and Source | Access date | Limitation |
|---|---|---:|---|---|---|
| Total revenue | FY26 Q4 | $86.7–$87.8B | Microsoft, `SRC-20260730-038` | 2026-07-30 | Company guidance; actual result may differ |
| PBP revenue | FY26 Q4 | $37.0–$37.3B | Microsoft, `SRC-20260730-038` | 2026-07-30 | Includes businesses beyond Agents |
| Intelligent Cloud revenue | FY26 Q4 | $37.95–$38.25B | Microsoft, `SRC-20260730-038` | 2026-07-30 | Includes AI and non-AI Azure workloads |
| Total-company revenue growth | FY26 Q4 | 13%–15% | Microsoft, `SRC-20260730-038` | 2026-07-30 | Forward-looking; approximately one point or less FX benefit |
| FY27 revenue and operating-income growth | FY27 | “double-digit” | Microsoft, `SRC-20260730-038` | 2026-07-30 | Directional only; no point range |

## Market price and capital structure

| Input | Value | Date / period | Source | Unit / treatment |
|---|---:|---|---|---|
| Price | $390.54 | 2026-07-29 close | `SRC-20260730-039` | USD/share |
| Diluted shares | 7.445 | FY26 Q3 | `SRC-20260429-001` | billion weighted-average shares |
| Current debt | $8.839 | 2026-03-31 | `SRC-20260429-001` | USD billion |
| Long-term debt | $31.423 | 2026-03-31 | `SRC-20260429-001` | USD billion |
| Cash and short-term investments | $78.272 | 2026-03-31 | `SRC-20260429-001` | USD billion |
| Equity value | $2,907.570 | calculated | $390.54 × 7.445B | USD billion |
| Enterprise value | $2,869.560 | calculated | $2,907.570B + $40.262B − $78.272B | USD billion |
| FY26E revenue | $328.532–$329.632 | calculated | $241.832B + Q4 guidance | USD billion |
| EV / FY26E revenue | 8.71×–8.73× | calculated | EV ÷ guidance-implied FY26 revenue | Range reverses with denominator |

## Scenario assumptions

The scenarios below are sensitivities, not forecasts. FY27 revenue growth assumptions
are researcher judgments chosen around management’s unspecific “double-digit” outlook;
they are not company guidance or consensus.

| Variable | Downside | Base | Upside | Fact, inference or judgment | Source / rationale |
|---|---:|---:|---:|---|---|
| FY26E revenue midpoint | $329.082B | $329.082B | $329.082B | inference | Nine-month actual plus midpoint of Q4 guidance |
| FY27 revenue growth | 10% | 15% | 20% | judgment | Sensitivity around management’s “double-digit” direction |
| FY27E revenue | $361.990B | $378.444B | $394.898B | calculation | FY26E midpoint × (1 + growth) |
| Enterprise value | $2,869.560B | $2,869.560B | $2,869.560B | calculation | Held constant to isolate revenue sensitivity |

## Results and sensitivity

| Output | Downside | Base | Upside | Formula / unit |
|---|---:|---:|---:|---|
| EV / FY27E revenue | 7.93× | 7.58× | 7.27× | Current EV ÷ scenario revenue |

## Market-implied expectations

The current enterprise value does not imply one unique growth expectation without a
chosen future multiple, margin path, discount rate and capital-intensity assumption.
To expose rather than hide that dependency, a one-year identity gives:

```text
Implied FY27 growth = current EV ÷ (FY26E revenue midpoint × assumed FY27 EV/revenue)
                      − 1
```

| Assumed FY27 EV/revenue | Implied FY27 revenue growth | Classification |
|---:|---:|---|
| 7.0× | 24.6% | calculation from a judgmental multiple |
| 8.0× | 9.0% | calculation from a judgmental multiple |
| 9.0× | -3.1% | calculation from a judgmental multiple |

This wide result is itself the useful finding: a revenue multiple alone cannot
separate expectations for growth, margins, capital intensity and duration.

## Inferences

- At the 2026-07-29 close, Microsoft traded near 8.72× guidance-implied FY26 revenue
  under the deliberately simplified enterprise-value identity.
- A large portion of the valuation question remains outside Agent-specific evidence
  because Microsoft does not disclose consolidated Agent revenue, gross margin,
  retention or cost-to-serve.
- The seats-plus-consumption transition in `EVT-20260429-031` may change revenue
  quality and growth, but current disclosures do not quantify that effect.

## Research judgment

This worksheet establishes a reproducible baseline, not whether Microsoft is cheap
or expensive. The most material unknown is whether Agent and AI usage can sustain
revenue growth and margins sufficient to offset rapidly rising infrastructure
capital intensity. No probability weights or target price are assigned.

## Contradicting evidence and alternative explanations

- Company-wide AI ARR and Azure demand may dominate the valuation while Agent-specific
  economics remain immaterial or undisclosed.
- Growth may be strong while free-cash-flow conversion weakens because capacity and
  short-lived infrastructure investment rise.
- A high current multiple may reflect durable non-Agent franchises rather than a
  market expectation that Agents restructure the enterprise-software value chain.
- The four-month balance-sheet staleness and weighted-average share proxy can move the
  calculated enterprise value.

## Catalysts and falsification conditions

- Replace Q4 guidance with reported FY26 results after release.
- Refresh price, shares, cash and debt on the same date where possible.
- Seek Agent-specific revenue, usage, retention, gross-margin and cost-to-serve data.
- Reassess the seats-plus-consumption inference if usage fails to produce disclosed
  revenue acceleration or if infrastructure investment persistently outruns cash flow.

## Freshness and review

- Price checked: 2026-07-30; underlying close 2026-07-29.
- Expectations checked: 2026-07-30.
- Operating facts checked: 2026-07-30.
- Human review notes: max explicitly approved the bounded RQ-08 module and current
  review items. This worksheet preserves Source grades, attribution limits and
  judgment labels and is not an investment recommendation.

## Remaining public-company queue

| Company | Existing reviewed Evidence | Status |
|---|---|---|
| Oracle | `EVT-20260610-007`, `EVT-20260714-009` | not populated |
| Palantir | `EVT-20260729-014`, `EVT-20260506-025` | not populated |
| Salesforce | `EVT-20260225-002`, `EVT-20260729-012`, `EVT-20260605-030` | not populated |
| SAP | `EVT-20260611-008`, `EVT-20260723-011` | not populated |
| ServiceNow | `EVT-20260722-010`, `EVT-20260729-013` | not populated |

Anthropic and OpenAI remain excluded from public-market valuation until a reliable
private-market methodology and data license are explicitly selected.
