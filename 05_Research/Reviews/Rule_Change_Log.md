# Rule Change Log

## 使用规则

Research Rules、Source Policy、Taxonomy、Metadata Schema、Agent 边界或自动化安全规则的修改，必须先建立 Rule Change Proposal 并由研究者批准。

| Change ID | Proposal | Date | Target | Decision | Summary | Validation |
|---|---|---|---|---|---|---|
| RCP-20260729-001 | `Proposals/RCP-20260729-001-source-event-review-semantics.md` | 2026-07-29 | Source/Event review 与 processing | approved | 三层独立状态；保留人工 Source 审核与 REV003 治理 warning | 33 tests；0 error；0 drift |
| RCP-20260729-002 | `Proposals/RCP-20260729-002-productization-runtime-and-schema.md` | 2026-07-29 | Runtime、package、Schema、YAML | approved | Python package、Pydantic、ruamel.yaml、Typer 与质量工具 | 44 tests；89.88% core coverage；0 error；0 drift |
| RCP-20260729-003 | `Proposals/RCP-20260729-003-multi-project-review-action-schema.md` | 2026-07-29 | Project、Review、Action、project_ids | approved | 正式对象、项目作用域、通用审核与结构化 Action | 56 tests；81.97% coverage；56/56 Schema；0 error；0 drift |
| RCP-20260729-004 | `Proposals/RCP-20260729-004-source-assets-and-ingestion.md` | 2026-07-29 | Source assets、provenance、ingestion/discovery adapters | approved | 显式采集、不可覆盖版本、hash 去重、日期 proposal、受限 RSS/GitHub/arXiv/SEC discovery | 73 tests；83% coverage；0 error；0 drift |
| RCP-20260729-005 | `Proposals/RCP-20260729-005-generated-research-workflow.md` | 2026-07-29 | generated Event/Report、citation、independence、supersession | approved | 结构化草稿、reviewed-only synthesis、增量报告、Company proposal 与人审 Gate | 80 tests；83% coverage；0 error；field Gate 0/10 pending |
| RCP-20260729-006 | `Proposals/RCP-20260729-006-local-dashboard-and-jobs.md` | 2026-07-29 | local Dashboard、Home index、Job Run | approved | loopback/read-only UI、Markdown rebuild、failure health、idempotent scheduler jobs | 86 tests；83% coverage；0 error；8/8 indexes |
