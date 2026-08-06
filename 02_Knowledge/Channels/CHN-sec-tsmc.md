---
id: CHN-sec-tsmc
type: source_channel
title: "SEC EDGAR: TSMC filings"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "TSMC SEC"
channel_type: sec
locator: "https://www.sec.gov/cgi-bin/browse-edgar?cik=1046179"
allow_hosts: [sec.gov]
publisher: "U.S. SEC EDGAR"
source_grade_proposal: A
entity_ids: [COM-tsmc]
sector_ids: [SEG-foundry-packaging-test]
query: "20-F,6-K"
schedule: "every 6 hours"
timezone: "Asia/Shanghai"
max_candidates_per_run: 20
rate_limit: "10 req/s"
retention_days: 30
license_status: reviewed
license_notes: "SEC public domain; robots allow; UA header required per EDGAR policy"
robots_checked_at: "2026-08-06"
enabled: true
---

# Source Channel

## Channel

SEC EDGAR: TSMC filings

## Review notes

Pilot channel batch (B-025 G1): per-company/repo split + arXiv research areas.
