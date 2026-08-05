---
id: EVT-20260729-013
type: event
title: ServiceNow 以 Agent Fabric、Control Tower 和 Otto 争夺控制层
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: reviewed
event_date: 2026-07-29
source_ids: [SRC-20260729-005]
companies: [COM-servicenow]
technologies: [DEV-TOOL-PROTOCOL, DEV-ORCHESTRATION]
products: [PRD-servicenow-ai-platform]
thesis_links: [THS-002, THS-005]
confidence: 0.85
tags: [EV-PRODUCT, MOAT-WORKFLOW, MOAT-PERMISSION]
---

# Event

## Facts

ServiceNow 官方产品页面描述 Agent Fabric 支持 MCP 和 A2A、Control Tower 管理内部与第三方 Agent、Otto 跨系统路由并完成任务；Agent 可使用 CMDB、知识、记录和外部系统数据。

## Inferences

ServiceNow 的产品方向不仅是应用内 Agent，而是以治理、上下文和工作流成为跨系统协调层。

## Research judgment

产品设计支持 THS-002 和 THS-005，但缺乏产品采用、控制权和客户付费证据。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-002 | supporting | 数据、权限、工作流是产品核心 | +0.03 |
| THS-005 | supporting | 明确提出跨系统路由与第三方 Agent 管理 | +0.04 |

## Alternative explanations

- 产品可能主要用于治理，不控制用户入口。
- 企业可能同时采用多个控制层。

## Unknowns

- Otto 活跃用户和任务量。
- 第三方 Agent 实际可执行权限。

## Follow-up indicators

- 生产案例和使用数据。
- 第三方 Agent 连接数量。
- 控制层产品独立收入。

## Review record

- Review date: 2026-07-29
- Reviewer: max
- Decision: approve
- Note: 批准
