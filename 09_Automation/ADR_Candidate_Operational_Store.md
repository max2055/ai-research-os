# ADR：Candidate Operational Store（B-003）

状态：`accepted`（RCP-v03-004 approved，2026-08-06）
日期：2026-08-06
工作包：WP-200

## Context

Phase 2 需要"每日情报发现"：定时抓取候选 → 去重/评分 → Candidate Queue →
人工审阅 → 提升为正式 Source。当前所有采集是手动 WP 级操作，无法规模化。

RCP-v03-004（approved）确定：Candidate 用 SQLite 作为**可重建的 operational
store**，非权威事实源。本 ADR 确定表结构、备份与 retention。

## Decision

### 1. 存储：独立 SQLite，可重建

- Candidate DB 存放于 `09_Automation/operational/candidates.db`（gitignore）。
- 与 `research-os export --format sqlite`（Ontology 派生导出）不同：那是只读派生
  视图；Candidate DB 是**可写 operational store**。
- 事实源仍是 reviewed Markdown Source/Event；Candidate DB 可删除重建（从
  Channel 重跑恢复）。

### 2. 表结构（4 表）

```sql
candidates (
  candidate_id TEXT PRIMARY KEY,      -- ULID
  channel_id TEXT NOT NULL,
  discovered_at TEXT NOT NULL,        -- ISO-8601 UTC
  published_at_proposal TEXT,
  title TEXT NOT NULL,
  canonical_url TEXT,
  publisher TEXT,
  content_fingerprint TEXT,           -- SHA-256 of normalized content
  snippet TEXT,
  language TEXT,
  fetch_status TEXT NOT NULL DEFAULT 'new',
  duplicate_cluster_id TEXT,
  relevance_score REAL,
  novelty_score REAL,
  quality_score_proposal REAL,
  priority_score REAL,
  entity_proposals_json TEXT,
  sector_proposals_json TEXT,
  reason_codes_json TEXT,
  model_version TEXT,
  status TEXT NOT NULL DEFAULT 'new',  -- new|triaged|promoted|dismissed|expired|failed
  promoted_source_id TEXT,
  error_code TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL
)

discovery_runs (
  run_id TEXT PRIMARY KEY,            -- ULID
  channel_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  candidate_count INTEGER DEFAULT 0,
  http_errors INTEGER DEFAULT 0,
  parse_errors INTEGER DEFAULT 0,
  retries INTEGER DEFAULT 0,
  cost_estimate TEXT,
  software_version TEXT,
  status TEXT NOT NULL                 -- running|succeeded|failed
)

duplicate_clusters (
  cluster_id TEXT PRIMARY KEY,
  canonical_url TEXT,
  content_hash TEXT,
  title_similarity REAL,
  common_upstream TEXT,
  created_at TEXT NOT NULL
)

candidate_actions (
  action_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
  action TEXT NOT NULL,               -- promote|dismiss|restore|retag|merge-cluster
  reason TEXT,
  actor TEXT NOT NULL,
  acted_at TEXT NOT NULL,
  payload_json TEXT
)
```

### 3. Retention（RCP-v03-004 RP-1）

- `new` / `triaged`：保留 30 天。
- `dismissed` / `expired`：立即清理（保留 action 审计行）。
- `promoted`：永久保留（永久链接 promoted_source_id）。

### 4. Backup

- Candidate DB 为派生数据：随 Recovery_Runbook 策略备份（加密）。
- 可从 Channel 重跑重建（B-021 runbook 定义）。

### 5. 版本化

- `PRAGMA user_version` 标记 schema 版本（当前 1）。
- schema 变更走 B-004 migration engine（apply/rollback + 测试）。

## Consequences

- Candidate 数据量远大于正式对象；retention 控制增长。
- Candidate 不得成为 reviewed Evidence；promote 须人工 Review Decision。
- Agent 可写 Candidate，但不可自动提升。

## 参考

- `03_Phase_2_Intelligence_Ingestion.md` §4/§8
- RCP-v03-004（approved）
