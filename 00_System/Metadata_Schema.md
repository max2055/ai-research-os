# Metadata Schema v0.2

Structured research objects use YAML front matter.

## Common fields

```yaml
---
id:
type:
title:
created_at:
updated_at:
schema_version: 1
project_ids: []
status:
review_status:
tags: []
---
```

## Source

```yaml
id: SRC-YYYYMMDD-NNN
type: source
source_type: article|report|paper|earnings|transcript|documentation|other
publisher:
authors: []
published_at:
accessed_at:
url:
local_path:
source_grade: A|B|C|D
companies: []
technologies: []
products: []
canonical_url:
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered|captured|processed|failed
processing_error:
published_date_proposal:
```

## Event

```yaml
id: EVT-YYYYMMDD-NNN
type: event
event_date:
source_ids: []
companies: []
technologies: []
products: []
thesis_links: []
confidence:
generation_method: manual|structured|ai-assisted
generation_fingerprint:
citation_anchors: []
source_independence_groups: []
```

## Thesis

```yaml
id: THS-NNN
type: thesis
thesis_status: active|validated|invalidated|archived
confidence:
review_date:
supporting_evidence: []
contradicting_evidence: []
companies: []
technologies: []
```

## Knowledge entity

```yaml
id:
type: company|technology|product|market|person
aliases: []
related_entities: []
evidence_ids: []
version:
supersedes:
superseded_by:
generation_method: manual|structured|ai-assisted
generation_fingerprint:
baseline_snapshot:
```

## Report

```yaml
id: RPT-YYYYMMDD-<slug>
type: report
report_type: daily|weekly|topic|investment_memo
period_start:
period_end:
thesis_ids: []
evidence_ids: []
```

## Project

```yaml
id: PRJ-NNN
type: project
status: proposed|active|paused|archived
owner:
research_question:
charter_path:
queue_path:
current_report_id:
review_cadence:
next_review_date:
```

## Review Decision

```yaml
id: REV-YYYYMMDD-NNN
type: review
status: applied|superseded
target_ids: []
decision: approve|edit|reject
reviewer:
reviewed_at:
notes:
```

## Action

```yaml
id: ACT-YYYYMMDD-NNN
type: action
status: open|in_progress|done|cancelled
owner:
due_date:
success_evidence:
source_review_id:
```

## Job Run

```yaml
id: JOB-YYYYMMDDhhmmss-NNN
type: job
status: success|failed
job_name: validate|indexes|metrics|source-process|refresh
started_at:
finished_at:
target:
message:
```

## Validation requirements

- `id`、`type`、`title`、`created_at`、`schema_version` 和
  `project_ids` 是所有正式对象的必填字段。
- 核心研究对象另需 `status` 与 `review_status`。
- Evidence confidence must be between 0 and 1.
- Every Event must reference at least one Source.
- Thesis confidence changes must be accompanied by Evidence IDs.
- A reviewed report may reference only reviewed Evidence, unless exceptions are explicitly disclosed.
- Review Decision 必须追加保存，并与目标状态更新使用同一事务。
- Action 完成时必须记录可核验的 `success_evidence`。
- `captured`/`processed` Source 必须有 asset path、SHA-256 和 fetched time。
- `published_date_proposal` 不是已确认事实，不能由自动化直接覆盖 `published_at`。
- `processing_error` 仅在 `processing_status: failed` 时记录可操作的失败原因；
  成功 capture/process 时必须清空。
- generated Event 的每个 Fact 必须有可解析到 processed asset 的 citation anchor；
  source independence groups 必须完整划分 `source_ids`。
- generated Report 只能引用 reviewed Evidence，并且不能省略所选 Evidence 中的
  contradicting Thesis relationship。
- `supersedes` 只在新 Report 获得人工批准时触发旧 Report 的原子 supersession。
- Job Run 是追加的操作审计，不是研究判断；失败必须保留并在 Health 中显示。
