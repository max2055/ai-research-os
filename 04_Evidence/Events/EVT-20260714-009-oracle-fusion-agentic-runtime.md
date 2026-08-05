---
id: EVT-20260714-009
type: event
title: Oracle 将 Agentic Applications 放入 Fusion 原生运行时
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: reviewed
event_date: 2026-07-14
source_ids: [SRC-20260714-006, SRC-20260729-007]
companies: [COM-oracle]
technologies: [DEV-AGENT-FRAMEWORK, DEV-ORCHESTRATION, APP-ERP]
products: [PRD-oracle-ai-agent-studio]
thesis_links: [THS-002, THS-004, THS-005]
confidence: 0.9
tags: [EV-PRODUCT, MOAT-DATA, MOAT-WORKFLOW, MOAT-PERMISSION]
schema_version: 1
project_ids:
- PRJ-001
---

# Event

## Facts

Oracle 宣布 Fusion Agentic Applications 在 Fusion 运行时内执行，继承业务对象、工作流、安全、审批和审计；支持 Oracle、合作伙伴和第三方 Agent。官方文档说明 Agent Studio 与 Fusion 知识库、工具和 API 集成。

## Inferences

Oracle 试图利用 ERP 原生数据、权限和工作流把 Agent 从外部自动化转为应用运行时的一部分。

## Research judgment

这是 THS-002 和 THS-004 的强产品设计证据，但没有客户使用和商业结果，暂不构成护城河验证。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-002 | supporting | 数据、权限、审批与工作流原生结合 | +0.04，待采用 |
| THS-004 | supporting | 现有 ERP 厂商利用既有运行时优势 | +0.03 |
| THS-005 | contextual | 支持第三方 Agent，但控制层仍在 Fusion 内 | 不调整 |

## Alternative explanations

- 原生集成可能强化封闭应用，而不是形成跨系统控制层。
- 产品数量和功能不等于生产采用。

## Unknowns

- 客户数、任务量、成功率和续费影响。
- 外部 Agent 实际拥有的权限范围。

## Follow-up indicators

- 生产客户案例。
- Agent Studio 活跃组织数。
- Fusion 增量收入与使用数据。

## Review record

- Review date: 2026-07-29
- Reviewer: max
- Decision: approve
- Note: 批准
