---
id: SRC-20260809-155
type: source
title: "NVDA market price quote NVIDIA"
created_at: 2026-08-09
updated_at: '2026-08-09'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
source_type: other
publisher: "Yahoo Finance"
authors: []
published_at: 2026-08-07
accessed_at: 2026-08-09
url: "https://finance.yahoo.com/quote/NVDA"
local_path: ""
source_grade: B
companies: [COM-nvidia]
technologies: []
products: []
canonical_url: "https://finance.yahoo.com/quote/NVDA"
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered
processing_error:
published_date_proposal:
tags: []
---
# Source

## Source summary

Observed market price for NVDA: $223.96 USD, as of 2026-08-07 (regular session close), quoted by Yahoo Finance.

## Why it matters

Freezes a dated, sourced price observation for the COM-nvidia valuation snapshot (Phase 5 §6).

## Relevant sections

- Regular market price: $223.96 USD (2026-08-07)
- Currency: USD
- Provider: Yahoo Finance (query1.finance.yahoo.com/v8/finance/chart/NVDA)
- Access date: 2026-08-07
- License: Yahoo Finance free delayed market data (public API, non-commercial)

## Reliability notes

Free delayed quote, not real-time; single observation, no intraday range captured. For valuation use, freshness_threshold 7d applies.

## Processing status

- [x] Event extraction completed
- [ ] Entity links reviewed
- [ ] Thesis links reviewed
