# Phase 2：每日情报发现与 Candidate Pipeline

状态：`proposed`  
建议周期：5–7 周  
前置：Phase 1 Gate；RCP-v03-004～005 获批  

## 1. 阶段目标

建立可长期运行的每日情报系统：

- 按 Sector、Company、Technology 和 Channel 定时发现资讯；
- 接收网页、公告、财报、GitHub、arXiv、论文期刊和监管材料；
- 去重、聚类、分类、实体解析、相关性与新颖性评分；
- 形成可审阅的 Candidate Queue 和 Daily Brief；
- 由研究者或明确规则选择 Candidate 提升为正式 Source；
- 保留运行、失败、许可、重试、成本和数据新鲜度记录。

目标不是“全部抓取”，而是每天把数百候选压缩成 10–30 个可审阅信号。

## 2. 非目标

- 不自动批准 Source；
- 不自动根据新闻更新 Thesis confidence；
- 不抓取未配置来源；
- 不绕过登录、付费墙或 robots；
- 不默认下载候选链接中的所有子链接；
- 不用 LLM 摘要替代原始 Source；
- 不把 Candidate SQLite 当作权威研究事实源；
- 不在本阶段生成投资建议。

## 3. Source Channel Schema 草案

```yaml
id: CHN-<slug>
type: source_channel
name:
channel_type: rss|web_page|github_release|arxiv|sec|journal|api|manual
locator:
allow_hosts: []
publisher:
source_grade_proposal:
entity_ids: []
sector_ids: []
query:
schedule:
timezone: Asia/Shanghai
max_candidates_per_run: 20
rate_limit:
retention_days:
license_status: reviewed|pending|restricted
license_notes:
robots_checked_at:
enabled: false
review_status: pending
```

只有 reviewed 且 `enabled: true` 的 Channel 可以被 scheduler 调用。

## 4. Candidate Operational Schema

建议表：

### candidates

```text
candidate_id
channel_id
discovered_at
published_at_proposal
title
canonical_url
publisher
content_fingerprint
snippet
language
fetch_status
duplicate_cluster_id
relevance_score
novelty_score
quality_score_proposal
priority_score
entity_proposals_json
sector_proposals_json
reason_codes_json
model_version
status: new|triaged|promoted|dismissed|expired|failed
promoted_source_id
error_code
error_message
```

### discovery_runs

保存 run ID、Channel、开始/结束时间、candidate count、HTTP/parse 错误、重试、成本和
软件版本。

### duplicate_clusters

保存 canonical URL、内容 hash、标题相似和共同上游。重复聚类只减少审阅量，不证明
来源独立性。

### candidate_actions

追加记录 promote、dismiss、restore、retag、merge-cluster 等决定，避免静默改状态。

## 5. Pipeline

```text
Schedule
→ Channel preflight
→ Bounded discover
→ Normalize URL/date/title
→ Exact dedup
→ Near-duplicate cluster
→ Entity/Sector proposal
→ Relevance/Novelty/Quality proposal
→ Priority ranking
→ Candidate Queue
→ Human triage
→ Source capture dry-run
→ Source apply + permanent candidate link
```

### 5.1 Preflight

- Channel reviewed/enabled；
- host/query 与 allowlist 一致；
- robots/license 未过期；
- rate limit 和本次上限合法；
- 凭证从安全 secret store/env 读取；
- 同 Channel 没有重叠运行锁；
- operational store schema 版本正确。

### 5.2 去重

顺序：

1. canonical URL；
2. exact content hash；
3. provider item ID；
4. normalized title/date；
5. near-duplicate text similarity；
6. 已有 Source canonical URL/hash；
7. 共同上游来源 proposal。

近似重复只形成 cluster，不自动删除候选。

### 5.3 评分

评分必须保存分项和 reason code，不能只保存一个不可解释总分。

建议维度：

- `scope_relevance`：是否属于已覆盖 Entity/Sector；
- `source_quality`：来源类型与历史可靠性；
- `novelty`：相对最近 Candidate/Event 是否新增信息；
- `materiality`：对产能、价格、产品、客户、财务、竞争、监管的潜在重要性；
- `time_sensitivity`：是否需要当日处理；
- `evidence_potential`：是否可能形成可锚定 Fact；
- `duplication_penalty`；
- `uncertainty_penalty`。

权重必须配置化、版本化，并用历史 triage 数据评估；LLM 分数始终是 proposal。

## 6. Adapter 优先级

### P0

- 现有 RSS；
- SEC；
- GitHub Release；
- arXiv；
- 公司 IR/press release RSS 或明确列表页；
- 官方产品/定价文档的定期变化检查；
- 本地手工文件 dropbox。

### P1

- Crossref/OpenAlex 等论文元数据；
- 期刊 TOC RSS；
- 监管和交易所公告；
- 财报日历与正式 transcript locator；
- 专利元数据；
- 官方博客和工程博客。

### P2

- 许可明确的专业媒体 API；
- 招聘、资本开支、供应链或市场数据；
- 需要浏览器渲染但许可允许的页面；
- 付费数据源。

P2 必须单独评估许可、成本和凭证安全。

## 7. Scheduler 设计

初期使用 macOS `launchd` 调用 `research-os jobs`，产品内新增：

- Channel schedule parser；
- per-channel lock；
- retry with bounded exponential backoff；
- timeout；
- concurrency limit；
- failure/dead-letter status；
- daily run summary；
- missed-run detection；
- manual replay with original config version；
- clock/timezone test。

不应立即引入复杂分布式任务队列。只有单机 scheduler 无法满足吞吐或可靠性时再评估。

## 8. Daily Brief

Daily Brief 必须区分：

1. 新增高优先级 Candidate；
2. 已提升正式 Source；
3. 新 reviewed Event；
4. 可能影响 Core Company/Thesis 的候选；
5. 反面或冲突信号；
6. 论文与技术信号；
7. 抓取失败、stale Channel 和 coverage gap；
8. 今日建议处理顺序。

Candidate 摘要必须标记 `unreviewed candidate`，不能与 reviewed Fact 混排。

## 9. 工作包

| ID | 任务 | 交付 | Gate |
|---|---|---|---|
| B-001 | Candidate/Source 边界 RCP | RCP-v03-004 | 人工批准 |
| B-002 | Channel/scheduler/许可 RCP | RCP-v03-005 | 人工批准 |
| B-003 | Candidate DB ADR | architecture decision | SQLite、backup、retention 明确 |
| B-004 | Candidate migration engine | operational repository | schema upgrade/rollback tests |
| B-005 | Channel Schema/validator | formal config | 未审核/禁用 Channel 不运行 |
| B-006 | Channel Registry CLI | list/check/enable/disable | enable 必须人工 apply |
| B-007 | Discovery run service | bounded orchestration | lock、timeout、retry、audit |
| B-008 | Adapter contract v2 | adapter interface | P0 adapters 行为一致 |
| B-009 | RSS hardening | adapter/tests | Atom/RSS/date/host/limit |
| B-010 | SEC hardening | adapter/tests | CIK/form/user-agent/rate |
| B-011 | arXiv + paper metadata | adapter/tests | query/limit/version/dedup |
| B-012 | GitHub/official release | adapter/tests | repo identity/tag/date |
| B-013 | IR/list-page adapter | bounded page parser | 无递归 crawler |
| B-014 | exact/near dedup | dedup service | cluster 不丢记录 |
| B-015 | entity resolution proposal | classifier | alias、ambiguous、unknown |
| B-016 | sector classification proposal | classifier | multi-label + reason |
| B-017 | scoring v1 | ranking service | 分项、版本、可解释 |
| B-018 | Candidate Queue CLI/API | list/filter/detail/action | 无权威写入旁路 |
| B-019 | promote-to-Source | transaction service | Candidate↔Source 永久关联 |
| B-020 | dismiss/expire/restore | append-only action | 不物理删除审计历史 |
| B-021 | launchd runbook | scheduler docs/config | 重启后恢复、无重叠 |
| B-022 | Daily Brief generator | pending operational report | candidate/reviewed 分区 |
| B-023 | Metrics/observability | dashboard/metrics | freshness、yield、noise、failure |
| B-024 | secret redaction | logging tests | token/cookie 不落盘 |
| B-025 | 14-day Pilot | real run records | 连续运行与人工 triage |
| B-026 | Phase acceptance | acceptance doc | 所有 Gate 通过 |

## 10. 建议 CLI

```text
research-os channels list|check|enable|disable
research-os discover run --channel CHN-ID [--apply]
research-os discover due --as-of <timestamp>
research-os candidates list --status new --tier core
research-os candidates show CND-ID
research-os candidates promote CND-ID [--apply]
research-os candidates dismiss CND-ID --reason ... [--apply]
research-os candidates restore CND-ID [--apply]
research-os brief daily --date YYYY-MM-DD [--apply]
research-os jobs run discover --target CHN-ID
research-os jobs run daily-brief --as-of YYYY-MM-DD
```

Candidate ID 可为 DB-local UUID/ULID；一旦提升必须记录永久 Source ID。

## 11. Metrics

必须按 Channel、Sector、Entity、日期统计：

- discovered count；
- exact/near duplicate rate；
- fetch/parse failure rate；
- median discovery latency；
- Core entity coverage；
- promoted rate；
- dismissed rate及理由；
- human edit rate；
- high-priority precision（人工判定）；
- stale Channel count；
- cost、请求量和模型 token；
- Candidate 到 Source/Event 的转化时间。

不以候选数量作为成功指标。

## 12. 测试与真实 Gate

### 自动测试

- DB migration/rollback；
- crash-safe transaction；
- Channel lock 和重复运行；
- retry/timeout/rate limit；
- RSS/SEC/arXiv/GitHub fixtures；
- exact/near duplicate；
- ambiguous entity；
- scoring version；
- secret redaction；
- promote 幂等；
- Daily Brief 分区；
- scheduler 时区和 missed run。

### 真实 14 天 Gate

- 至少 20 个 reviewed/enabled Channel；
- 每日任务按计划完成或留下明确失败；
- 不出现静默漏跑；
- 同一内容重复进入审阅队列的比例可测且目标 <15%；
- Top-20 Candidate 人工相关性目标 ≥75%；
- 至少 20 个 Candidate 被提升为正式 Source；
- 所有提升 Source 通过资产/hash 检查；
- Candidate 摘要未被当作 reviewed Fact；
- 每日人工 triage 中位耗时目标 ≤45 分钟；
- 失败和许可限制写入 Known Limitations。

## 13. 回滚与故障处理

- operational DB 每日 snapshot；
- migration 前备份并记录 schema version；
- scheduler 可全局 pause，已存在 Candidate 保留；
- 单 Channel 可 disable，不删除配置；
- Adapter 失败不得创建 processed Source；
- promote transaction 失败不得留下半个 Source/asset；
- near-duplicate 模型升级不得覆盖旧 cluster 结果，记录版本；
- secrets 泄露时立即停用 Channel、轮换凭证并清理日志，不继续运行；
- 许可状态变为 restricted 时停止新抓取并保留合规记录。

