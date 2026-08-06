---
id: CHN-trendforce-news
type: source_channel
title: "TrendForce press center (news only)"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "TrendForce Press Center"
channel_type: web_page
locator: "https://www.trendforce.com/presscenter/news/"
allow_hosts: [trendforce.com, trendforce.com.tw, trendforce.cn]
publisher: "TrendForce"
source_grade_proposal: B
entity_ids: [COM-sk-hynix, COM-samsung-electronics, COM-micron]
sector_ids: [SEG-memory-storage, SEG-compute-silicon]
query: ""
schedule: "every 6 hours"
timezone: "Asia/Shanghai"
max_candidates_per_run: 20
rate_limit: ""
retention_days: 30
license_status: restricted
license_notes: "新闻稿公开；报告页(/research/download/)为付费，禁止采集——allow_hosts 已限定 presscenter/news 路径"
robots_checked_at: "2026-08-06"
enabled: false
---

# Source Channel

## Channel

TrendForce 新闻稿（DRAM/HBM/晶圆代工行业份额数据）。B 级专业研究机构。
**许可边界（RCP-v03-005 RP-5）：只采新闻稿路径，禁采付费报告页。**

## Review notes

B-005 首批 Channel。`license_status: restricted`（部分内容付费），
`enabled: false`，待 reviewed 后由 max 决定是否启用（按 RP-6 可保留登记
但不采集）。
