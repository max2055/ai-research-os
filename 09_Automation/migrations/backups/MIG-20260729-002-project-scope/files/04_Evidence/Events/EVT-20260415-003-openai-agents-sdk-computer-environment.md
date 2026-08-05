---
id: EVT-20260415-003
type: event
title: OpenAI Agents SDK 增加计算机环境、沙箱和状态恢复
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: reviewed
event_date: 2026-04-15
source_ids: [SRC-20260415-014]
companies: [COM-openai]
technologies: [DEV-AGENT-FRAMEWORK, DEV-ORCHESTRATION]
products: [PRD-openai-agents-sdk]
thesis_links: [THS-005]
confidence: 0.85
tags: [EV-PRODUCT]
schema_version: 1
---

# Event

## Facts

OpenAI 官方宣布 Agents SDK 提供面向文件、工具和计算机工作的 Agent harness、原生沙箱执行，以及状态快照和恢复能力；使用按标准 API token 和工具计费。

## Inferences

模型厂商正在将 Agent 执行环境、长任务状态和运行安全标准化，产品边界从模型调用扩展到 Agent 运行时。

## Research judgment

该事件支持 THS-005 的方向，但只能证明平台能力扩展，不能证明 OpenAI 已成为企业控制层。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| THS-005 | supporting | 模型厂商向执行和编排层扩展 | +0.03，待采用证据 |

## Alternative explanations

- SDK 可能只服务开发者，不控制最终企业入口。
- 企业应用仍掌握数据、权限和工作流。

## Unknowns

- 企业生产采用规模。
- 与现有企业软件运行时的责任边界。

## Follow-up indicators

- 企业客户案例。
- SDK 调用和工具运行规模。
- 与主流企业软件的连接深度。

## Review record

- Review date: 2026-07-29
- Reviewer: max
- Decision: approve
- Note: 批准
