---
id: CHN-github-releases
type: source_channel
title: "GitHub Releases (allowlisted repos)"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "GitHub Releases"
channel_type: github_release
locator: "https://api.github.com/repos/{owner}/{repo}/releases"
allow_hosts: [github.com, api.github.com]
publisher: "GitHub"
source_grade_proposal: A
entity_ids: [COM-openai, COM-anthropic, COM-meta, COM-deepseek, COM-microsoft]
sector_ids: [SEG-models]
query: "allowlisted repos (MCP, agent SDKs)"
schedule: "daily 2x"
timezone: "Asia/Shanghai"
max_candidates_per_run: 20
rate_limit: "60 req/h unauthenticated (GitHub API)"
retention_days: 30
license_status: reviewed
license_notes: "公开 API；robots 允许；allowlist 限定 repos（不抓任意 repo）"
robots_checked_at: "2026-08-06"
enabled: true
---

# Source Channel

## Channel

GitHub Releases（allowlist 限定的官方 repo：模型 SDK、MCP 协议、agent
框架）。公开 API，限速按 GitHub 政策。

## Review notes

B-005 首批 Channel（RCP-v03-005 批准）。`enabled: false`，待 reviewed 后由
max 启用。
