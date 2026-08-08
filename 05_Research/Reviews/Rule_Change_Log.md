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
| RCP-v03-001 | `Proposals/RCP-v03-001_Product_Boundary_Candidate_Source_Authority.md` | 2026-08-05 | 产品定位、Source_Policy 权威边界、Schema/Agent 边界 | approved | v0.2 Evidence Kernel → v0.3 AI Industry Intelligence & Decision OS；Candidate 非权威源、AI 产物默认 pending、投资/研究边界 | 0 error；0 warning（无对象变更）|
| RCP-v03-002 | `Proposals/RCP-v03-002_Taxonomy_v2_Stable_Sector_IDs.md` | 2026-08-05 | Taxonomy v1→v2、Sector 扇区 | approved | 13 L1 扇区 SEG-ID、5 横向维度前缀（REG/SUP/CAP/CYC/RGT）、v1→v2 权威映射、边界项 R1–R5 | 0 error；0 warning（无对象变更）|
| RCP-v03-003 | `Proposals/RCP-v03-003_Entity_Schema_and_Permanent_IDs.md` | 2026-08-05 | 新正式对象类型、永久 ID、schema_version | approved | 5 实体 Schema（Sector/Security/Product/Technology/Metric）、14 新前缀 + parser 歧义 D1–D7、Company/Security 分离、MIG-001→002→003 | 0 error；0 warning（无对象变更）|
| RCP-v03-004 | `Proposals/RCP-v03-004_Candidate_SQLite_and_Retention.md` | 2026-08-06 | Candidate Operational Store 事实边界 | approved | 4-table SQLite（candidates/discovery_runs/duplicate_clusters/candidate_actions）、30 天 retention、Agent 可写不自动 promote、B-004 migration 并入 | 0 error；0 warning（无对象变更）|
| RCP-v03-005 | `Proposals/RCP-v03-005_Source_Channel_and_Scheduler.md` | 2026-08-06 | source_channel 对象、Source_Policy 采集边界 | approved | CHN-<slug> 正式对象、reviewed+enabled 才调度、许可分级 restricted 不采集、调度频率/上限、Company source_channel_ids | 0 error；0 warning（无对象变更）|
| RCP-v03-006 | `Proposals/RCP-v03-006_Impact_Assertion_and_Propagation.md` | 2026-08-07 | impact_assertion 对象、Phase 3 传播边界 | approved | IMP-YYYYMMDD-NNN 正式对象、RELATED_TO ≠ impact、经营/价格影响分离、仅 reviewed Event 权威化、多跳约束、weakest-link confidence | 0 error；0 warning（无对象变更）|
| RCP-v03-007 | `Proposals/RCP-v03-007_Analysis_Mode_Framework.md` | 2026-08-08 | analysis_mode/analysis_run 对象、模式契约 | approved | MOD-ANL-<slug>-vN + ANL-YYYYMMDD-NNN 正式对象、版本化契约、Run 冻结、Run ≠ Thesis/Rec、Open Discovery 候选化、9 模式 | 0 error；0 warning（无对象变更）|
