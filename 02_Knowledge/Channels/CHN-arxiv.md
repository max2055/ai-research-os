---
id: CHN-arxiv
type: source_channel
title: "arXiv API (AI/ML papers)"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "arXiv"
channel_type: arxiv
locator: "https://export.arxiv.org/api/query"
allow_hosts: [arxiv.org, export.arxiv.org]
publisher: "arXiv"
source_grade_proposal: A
entity_ids: []
sector_ids: [SEG-models, SEG-compute-silicon]
query: "cat:cs.AI,cs.LG; AI agents; coding agents"
schedule: "daily 1x"
timezone: "Asia/Shanghai"
max_candidates_per_run: 20
rate_limit: "3 req/s (arXiv API policy)"
retention_days: 30
license_status: reviewed
license_notes: "arXiv 公开 API；robots 允许；按 arXiv API 政策限速"
robots_checked_at: "2026-08-06"
enabled: false
---

# Source Channel

## Channel

arXiv AI/ML 论文（cs.AI、cs.LG，agentic/coding agent 主题）。同行评审前
预印本，A/B 级来源。公开 API，按 arXiv 政策限速。

## Review notes

B-005 首批 Channel（RCP-v03-005 批准）。`enabled: false`，待 reviewed 后由
max 启用。
