---
id: THS-001
type: thesis
title: Agent 将削弱传统企业软件界面的部分价值
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: reviewed
thesis_status: active
confidence: 0.29
review_date: 2026-07-29
supporting_evidence: [EVT-20260611-008]
contradicting_evidence: []
companies:
  - COM-microsoft
  - COM-salesforce
  - COM-servicenow
  - COM-oracle
  - COM-sap
technologies:
  - DEV-AGENT-FRAMEWORK
  - DEV-ORCHESTRATION
tags:
  - APP-ENTERPRISE
  - EV-PRODUCT
---

# Thesis

## Core judgment

Agent 将逐步成为企业软件的新入口，并削弱传统图形界面在部分高频任务中的价值。

## Reasoning chain

自然语言入口降低操作复杂度；Agent 如果能够理解上下文、调用工具并完成任务，用户将减少在多个应用界面之间切换；控制用户意图和任务执行的入口可能获得更高价值。

## Supporting evidence

已审核：`EVT-20260611-008` 显示 SAP 将部分客户门户交互从点击和搜索迁移到 Joule 对话入口。

## Contradicting evidence

尚无已审核的直接反面 Event。当前 Event 的替代解释包括：Agent 可能只是界面补充，高风险操作仍返回传统界面。

## Alternative explanations

- Agent 可能只是现有界面的补充，而不是替代。
- 高风险任务仍需要可视化界面和人工确认。
- 用户采用阻力可能使传统交互长期存在。

## Key variables

- Agent 任务完成率。
- 生产环境活跃使用率。
- 跨应用执行能力。
- 人工介入比例。
- 原有界面的使用变化。

## Falsification conditions

- Agent 长期停留在问答和辅助层。
- 企业核心工作流仍主要通过传统界面完成。
- 试点后的使用率和留存率持续偏低。

## Investment implications

若成立，拥有 Agent 入口、企业上下文和跨系统执行能力的平台可能获得价值；仅依赖界面和席位的产品可能承压。当前证据不足，尚不构成投资结论。

## Unknowns

- 企业是否愿意将核心操作委托给 Agent。
- 界面使用下降是否会导致软件收入下降。
- 应用厂商还是独立 Agent 平台控制入口。

## Review history

| Date | Old confidence | New confidence | Evidence | Reason |
|---|---:|---:|---|---|
| 2026-07-29 | — | 0.25 | — | 初始研究假设，尚无正式 Evidence |
| 2026-07-29 | 0.25 | 0.29 | EVT-20260611-008 | 人工批准；有明确入口迁移，但只有单一厂商产品证据且缺少使用数据 |
