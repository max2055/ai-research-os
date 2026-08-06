---
id: CHN-sec-edgar
type: source_channel
title: "SEC EDGAR filings"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "SEC EDGAR"
channel_type: sec
locator: "https://www.sec.gov/cgi-bin/browse-edgar"
allow_hosts: [sec.gov]
publisher: "U.S. SEC EDGAR"
source_grade_proposal: A
entity_ids: [COM-nvidia, COM-tsmc, COM-micron, COM-microsoft, COM-meta, COM-aws, COM-coreweave]
sector_ids: [SEG-compute-silicon, SEG-memory-storage, SEG-cloud-ai-infrastructure]
query: "10-K,10-Q,20-F; CIK allowlist"
schedule: "every 6 hours"
timezone: "Asia/Shanghai"
max_candidates_per_run: 20
rate_limit: "10 req/s"
retention_days: 30
license_status: reviewed
license_notes: "SEC data is public domain; robots allow; requires User-Agent header per EDGAR policy"
robots_checked_at: "2026-08-06"
enabled: true
---

# Source Channel

## Channel

U.S. SEC EDGAR 归档（10-K/10-Q/20-F）。公开数据，robots 允许，需按 EDGAR
政策提供 User-Agent。采集时用 CIK allowlist 限定到已注册 Core Company。

## Review notes

B-005 首批 Channel（RCP-v03-005 批准）。`enabled: false`，待 reviewed 后由
max 启用。
