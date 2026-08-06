---
id: CHN-company-ir
type: source_channel
title: "Company official IR newsrooms (per-company)"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "Company IR Newsrooms"
channel_type: web_page
locator: "per-company IR pages"
allow_hosts: [news.samsung.com, semiconductor.samsung.com, investors.micron.com, news.skhynix.com]
publisher: "Company IR"
source_grade_proposal: B
entity_ids: [COM-samsung-electronics, COM-micron, COM-sk-hynix, COM-asml]
sector_ids: [SEG-memory-storage, SEG-semiconductor-materials-equipment]
query: ""
schedule: "every 6 hours"
timezone: "Asia/Shanghai"
max_candidates_per_run: 20
rate_limit: ""
retention_days: 30
license_status: pending
license_notes: "公司官方 IR 公开；各站需逐一核验 robots（Samsung/Micron/ASML 分站），本 Channel 挂 pending 待核验"
robots_checked_at: ""
enabled: false
---

# Source Channel

## Channel

各公司官方 IR 新闻室（Samsung、Micron、SK hynix、ASML 等）。公司披露 B 级
来源。因涉及多站 robots 核验，license_status 挂 pending。

## Review notes

B-005 首批 Channel（RCP-v03-005 批准）。`license_status: pending`（多站
robots 未全部核验），`enabled: false`。待逐站核验 + reviewed 后由 max 启用。
