# Valuation and Market Expectations Module

Status: approved v0.2 boundary

Updated: 2026-07-30

Action: `ACT-20260730-002`

## Purpose

Add an investment-research constraint layer without converting industry Evidence
into automatic security recommendations. The module separates:

1. observed operating facts;
2. externally sourced market expectations;
3. market price and capital structure at a stated date;
4. scenario assumptions;
5. implied expectations and sensitivity;
6. research judgment and decision boundaries.

The module must never infer a current price, consensus estimate, share count or
valuation multiple without a dated Source.

## v0.2 boundary

The engineering draft consists of:

- this module contract;
- `07_Templates/Valuation_and_Market_Expectations.md`;
- a PRJ-001 instance at
  `05_Research/AI-Enterprise-Software/Valuation_and_Market_Expectations.md`.

It does not add a trading, portfolio, target-price or recommendation engine. It does
not make a new authoritative object type before the workflow is used and reviewed.

RQ-08 remains open until the researcher either:

- approves this boundary and completes at least one dated, sourced company instance;
  or
- records a formal deferral with reason, scope and revisit date.

## Required inputs

### Operating facts

- Reviewed Event IDs only.
- Reporting period, currency and accounting basis.
- Revenue, margin, cash flow, share count and segment/product disclosure where
  relevant.
- Agent-specific metrics kept separate from company-wide AI or cloud metrics.

### Market expectations

- Dated company guidance, consensus or other expectation Source.
- Provider, access date, fiscal period and measure definition.
- License or redistribution constraint.
- Range and dispersion when available; a single point estimate must not be presented
  as universal consensus.

### Market price and capital structure

- Price timestamp and market.
- Diluted shares, debt, cash and other enterprise-value adjustments with period.
- Split, currency and ADR treatment.
- Staleness flag when price or estimates exceed the project threshold.

## Calculation layer

All calculations are deterministic and shown with units:

```text
Equity value = price × diluted shares
Enterprise value = equity value + debt + other claims − cash
Forward multiple = enterprise value or equity value ÷ matched-period denominator
Implied growth = scenario value driver solved from the selected valuation identity
```

The denominator, period and accounting definition must match the numerator. The
module must not compare a current enterprise value with an unmatched historical or
non-comparable metric without disclosure.

## Scenario contract

Use at least three scenarios when a valuation judgment is made:

- downside;
- base;
- upside.

Each scenario records:

- assumption;
- source or explicit researcher judgment;
- time horizon;
- probability, if used;
- result;
- sensitivity to the two most material variables.

Probabilities are judgments, not facts. A scenario table can expose uncertainty but
cannot validate the assumptions used.

## Output contract

Every populated instance must contain:

- facts with Source or reviewed Event IDs;
- inferences separated from facts;
- judgment and uncertainty;
- market-implied expectations;
- contradicting evidence and alternative explanations;
- catalysts and falsification conditions;
- freshness date;
- reviewer and decision.

An unreviewed instance remains a research worksheet and cannot be cited as an
authoritative valuation conclusion.

## Human decision required

The researcher must decide whether this is in v0.2 scope. The current Charter excludes
a full DCF, while the roadmap requires RQ-08 to be completed or formally deferred.
Automation must not silently resolve that scope conflict.

## Scope decision

- Decision: approve the bounded v0.2 module and complete one sourced public-company
  instance; do not add target prices, portfolio execution or automatic recommendations.
- Reviewer: max
- Date: 2026-07-30
- Basis: explicit user approval in the active implementation task.
- Implemented instance:
  `05_Research/AI-Enterprise-Software/Valuation_and_Market_Expectations.md`
