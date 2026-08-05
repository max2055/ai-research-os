---
id: EVT-20260729-014
type: event
title: Palantir Foundry Agents 通过 Ontology 与范围化权限读写企业环境
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: reviewed
event_date: 2026-07-29
source_ids: [SRC-20260729-010, SRC-20260729-011, SRC-20260729-012]
companies: [COM-palantir]
technologies: [DEV-AGENT-FRAMEWORK, DEV-TOOL-PROTOCOL, DEV-ORCHESTRATION]
products: [PRD-palantir-aip, PRD-palantir-ontology, PRD-palantir-agents]
thesis_links: [THS-002, THS-005]
confidence: 0.85
tags: [EV-PRODUCT, MAT-PROTOTYPE, MOAT-DATA, MOAT-PERMISSION]
schema_version: 1
project_ids:
- PRJ-001
---

# Event

## Facts

Palantir 官方文档说明 Foundry Agents 可通过 Ontology SDK、Ontology MCP 和 Palantir MCP 读写企业数据与工具，并自动使用范围化权限；产品明确标记为 Beta。AIP 和 Ontology 文档描述数据、逻辑、动作、安全及评测的集成。

## Inferences

Ontology 为 Agent 提供可操作企业上下文和权限边界，体现“数据+动作+安全”平台架构。

## Research judgment

该事件支持 THS-002 的机制，但 Beta 状态、部署复杂度和商业采用尚未验证。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-002 | supporting | 企业上下文、动作和权限被统一 | +0.04，待生产采用 |
| THS-005 | contextual | 可作为控制层基础，但入口和跨平台采用未知 | 不调整 |

## Alternative explanations

- 复杂 Ontology 构建成本限制规模化。
- 开放协议和其他数据平台可提供类似能力。

## Unknowns

- Beta 客户数和生产任务量。
- Ontology 部署周期和维护成本。

## Follow-up indicators

- Agents 正式可用。
- 客户生产案例。
- AIP 与 Ontology 合同增长。

## Review record

- Review date: 2026-07-29
- Reviewer: max
- Decision: approve
- Note: 批准
