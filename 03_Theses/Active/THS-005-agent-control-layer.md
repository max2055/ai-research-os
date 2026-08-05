---
id: THS-005
type: thesis
title: 跨系统 Agent 平台可能成为企业软件的新控制层
created_at: 2026-07-29
updated_at: 2026-07-30
status: active
review_status: reviewed
thesis_status: active
confidence: 0.32
review_date: 2026-07-30
supporting_evidence: [EVT-20260415-003, EVT-20260521-006, EVT-20260729-013, EVT-20260729-015]
contradicting_evidence: [EVT-20260514-026, EVT-20260513-029]
companies:
- COM-microsoft
- COM-salesforce
- COM-servicenow
- COM-palantir
- COM-openai
- COM-anthropic
technologies:
- DEV-TOOL-PROTOCOL
- DEV-MEMORY
- DEV-ORCHESTRATION
tags:
- MOAT-ECOSYSTEM
- MOAT-PERMISSION
- EV-COMPETITION
schema_version: 1
project_ids:
- PRJ-001
---

# Thesis

## Core judgment

能够跨系统理解意图、规划、调用工具、执行任务并验证结果的 Agent 平台，可能成为企业软件之上的新控制层。

## Reasoning chain

企业任务通常跨越多个应用；跨系统 Agent 若控制用户意图和任务编排，就可能把底层应用降为数据与工具提供者；控制层可以影响分发、定价和生态关系。

## Supporting evidence

已审核：

- `EVT-20260415-003`：OpenAI 把 Agent 能力扩展到执行环境和长任务状态。
- `EVT-20260521-006`：MCP 候选规范扩展跨系统任务与授权能力。
- `EVT-20260729-013`：ServiceNow 明确提出跨系统路由、第三方 Agent 管理和统一入口。
- `EVT-20260729-015`：OpenAI Workspace Agents 直接进入企业工具与任务入口。

## Contradicting evidence

已审核：

- `EVT-20260514-026`：阿里巴巴现场实验显示，控制层效果依赖任务分类、持续人工
  责任、监控质量和介入时机；迟到的情绪升级不能恢复到人工基线。
- `EVT-20260513-029`：Sinch 委托调查报告生产回滚、跨渠道上下文缺口和治理摩擦；
  方法披露不完整，因此只作为需要独立复核的风险信号。

两项 Evidence 直接约束“统一 Agent 控制层可顺畅、自治地接管工作流”的强版本，
但不排除受治理约束的控制层逐步形成。

## Alternative explanations

- 企业会限制 Agent 在单一应用域内运行。
- 应用厂商可能通过封闭权限阻止独立控制层。
- 控制层可能由云平台、身份平台或操作系统掌握，而非独立 Agent 厂商。

## Key variables

- 跨系统连接器和工具协议采用。
- 身份、权限和审计标准。
- Agent 独立入口的使用率。
- 应用厂商开放程度。
- 企业对平台集中风险的态度。

## Falsification conditions

- 安全、准确性和责任问题长期阻止跨系统执行。
- 企业坚持应用内 Agent，拒绝统一控制层。
- 应用厂商有效封闭数据和操作权限。

## Investment implications

若成立，控制 Agent 入口、身份权限、上下文和工具生态的平台可能获得新增价值；底层应用的议价权取决于数据和工作流不可替代性。

## Unknowns

- 控制层最终属于模型厂商、云厂商、现有软件平台还是新进入者。
- 开放协议会导致集中还是多平台共存。

## Review history

| Date | Old confidence | New confidence | Evidence | Reason |
|---|---:|---:|---|---|
| 2026-07-29 | — | 0.20 | — | 长期结构性假设，当前商业证据不足 |
| 2026-07-29 | 0.20 | 0.32 | EVT-20260415-003, EVT-20260521-006, EVT-20260729-013, EVT-20260729-015 | 人工批准；跨工具执行、协议与统一入口已出现，生产控制权仍未知 |
| 2026-07-30 | 0.32 | 0.32 | EVT-20260514-026, EVT-20260513-029 | 用户批准直接反证；先保留置信度，待真实 Weekly 统一评估净影响，避免自动修改判断 |
