---
id: CHN-sec-meta
type: source_channel
title: "SEC EDGAR: Meta filings"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "Meta SEC"
channel_type: sec
locator: "https://www.sec.gov/cgi-bin/browse-edgar?cik=1326801"
allow_hosts: [sec.gov]
publisher: "U.S. SEC EDGAR"
source_grade_proposal: A
entity_ids: [COM-meta]
sector_ids: [SEG-enterprise-applications]
query: "10-K,10-Q,8-K"
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

SEC EDGAR: Meta filings

## Review notes

Pilot channel batch (B-025 G1): per-company/repo split + arXiv research areas.
