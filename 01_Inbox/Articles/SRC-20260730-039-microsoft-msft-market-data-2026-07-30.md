---
id: SRC-20260730-039
type: source
title: "Microsoft MSFT market-data snapshot: 2026-07-30"
created_at: 2026-07-30
updated_at: '2026-07-30'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
source_type: report
publisher: "Yahoo Finance chart API"
authors: []
published_at: 2026-07-30
accessed_at: 2026-07-30
url: "https://query1.finance.yahoo.com/v8/finance/chart/MSFT?events=history&interval=1d&period1=1785369600&period2=1785542400"
local_path: ""
source_grade: C
companies: [COM-microsoft]
technologies: []
products: []
canonical_url: https://query1.finance.yahoo.com/v8/finance/chart/MSFT?events=history&interval=1d&period1=1785369600&period2=1785542400
asset_paths:
- 01_Inbox/_assets/SRC-20260730-039/20260730110535-67355aec4ce9.json
- 01_Inbox/_assets/SRC-20260730-039/20260730110535-67355aec4ce9.metadata.json
- 01_Inbox/_assets/SRC-20260730-039/20260730110535-67355aec4ce9.json.extracted.txt
- 01_Inbox/_assets/SRC-20260730-039/20260730110535-67355aec4ce9.json.extraction.json
content_sha256: 67355aec4ce9107fa163f94bb7a015ac6ac90606e1687ff58f5477acb95a97b6
fetched_at: 2026-07-30T11:05:35.466588+00:00
upstream_source_ids: []
processing_status: processed
processing_error:
published_date_proposal:
tags: [MAT-RESEARCH]
---

# Source

## Source summary

The archived Yahoo Finance chart response identifies Microsoft (`MSFT`) as a
NasdaqGS equity denominated in USD. Its daily record timestamp is
2026-07-29 20:00:01 UTC and reports a close of $390.5400085, with an open of
$393.3999939, a high of $401.25, a low of $388.7430115 and volume of 42,418,496.

## Why it matters

Provides the date-stamped market-price input for the first PRJ-001 valuation and
market-expectations worksheet.

## Relevant sections

- `meta.symbol`, `meta.currency`, `meta.fullExchangeName`
- `timestamp[0]`
- `indicators.quote[0]`
- `indicators.adjclose[0]`

## Reliability notes

C-grade third-party market-data API, archived with raw bytes and SHA-256. The API
does not disclose its exchange-feed latency or correction policy in this response.
The timestamp is the 2026-07-29 regular-session close, although the Source was
accessed on 2026-07-30. Use it as a dated snapshot, not a live quote; do not combine
it with financial inputs from a different period without an explicit staleness note.

## Processing status

- [ ] Event extraction completed
- [x] Entity links reviewed
- [ ] Thesis links reviewed
