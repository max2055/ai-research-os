---
id: THS-004
type: thesis
title: 现有企业软件厂商同时拥有分发优势和自我颠覆约束
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: reviewed
thesis_status: active
confidence: 0.4
review_date: 2026-07-29
supporting_evidence: [EVT-20260225-002, EVT-20260611-008, EVT-20260714-009, EVT-20260722-010]
contradicting_evidence: [EVT-20260514-005, EVT-20260729-015]
companies:
- COM-microsoft
- COM-salesforce
- COM-servicenow
- COM-oracle
- COM-sap
- COM-palantir
- COM-openai
- COM-anthropic
technologies:
- DEV-AGENT-FRAMEWORK
tags:
- MOAT-DISTRIBUTION
- MOAT-DATA
- MOAT-WORKFLOW
- EV-COMPETITION
schema_version: 1
project_ids:
- PRJ-001
---

# Thesis

## Core judgment

现有企业软件厂商拥有客户、数据、权限、工作流和分发优势，但既有产品架构与收入模式可能限制其 Agent 化重构。

## Reasoning chain

现有厂商更容易把 Agent 推向存量客户；同时，真正的任务自动化可能减少席位、弱化现有界面或跨越产品边界，从而与存量收入和组织边界冲突。

## Supporting evidence

已审核：

- `EVT-20260225-002`：Salesforce 披露 Agentforce 商业指标和现有客户扩展。
- `EVT-20260611-008`：SAP 利用既有客户门户分发 Joule。
- `EVT-20260714-009`：Oracle 利用 Fusion 运行时嵌入 Agent。
- `EVT-20260722-010`：ServiceNow 披露 AI ACV 和 Agentic deployment 增长。

## Contradicting evidence

已审核：

- `EVT-20260514-005`：Anthropic 通过 PwC 等伙伴进入复杂企业工作流。
- `EVT-20260729-015`：OpenAI 直接提供 Workspace Agents 企业入口。

## Alternative explanations

- 现有厂商可以通过价格升级捕获 Agent 增量价值。
- 企业采购壁垒可能使 AI Native 竞争者难以进入。
- 大厂可以通过收购和平台开放解决创新约束。

## Key variables

- 存量客户的 Agent 转化速度。
- Agent 新收入与存量收入替代关系。
- 产品跨模块执行能力。
- AI Native 厂商进入大型企业的速度。
- 合作、开放与封闭生态策略。

## Falsification conditions

- 现有厂商顺利完成 Agent 化且未出现收入或组织冲突。
- AI Native 厂商长期无法跨越采购、安全和集成壁垒。

## Investment implications

不能简单判断“大厂必胜”或“新公司颠覆”。需要比较分发速度、自我替代程度、产品架构和新收入质量。

## Unknowns

- 现有厂商是否愿意主动牺牲席位收入。
- 模型厂商将成为供应商、合作伙伴还是直接竞争者。

## Review history

| Date | Old confidence | New confidence | Evidence | Reason |
|---|---:|---:|---|---|
| 2026-07-29 | — | 0.30 | — | 机制合理但缺少公司级验证 |
| 2026-07-29 | 0.30 | 0.40 | EVT-20260225-002, EVT-20260611-008, EVT-20260714-009, EVT-20260722-010, EVT-20260514-005, EVT-20260729-015 | 人工批准；incumbent 分发优势与模型厂商直接进入的反面证据并存 |
