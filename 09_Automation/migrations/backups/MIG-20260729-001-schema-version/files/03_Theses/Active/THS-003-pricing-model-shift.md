---
id: THS-003
type: thesis
title: Agent 将推动企业软件定价从席位转向用量、任务或结果
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: reviewed
thesis_status: active
confidence: 0.28
review_date: 2026-07-29
supporting_evidence: [EVT-20260729-012]
contradicting_evidence: [EVT-20260219-001]
companies:
  - COM-microsoft
  - COM-salesforce
  - COM-servicenow
  - COM-oracle
  - COM-sap
technologies:
  - DEV-AGENT-FRAMEWORK
tags:
  - BM-SEAT
  - BM-USAGE
  - BM-TASK
  - BM-OUTCOME
  - EV-PRICING
---

# Thesis

## Core judgment

随着 Agent 承担更多人工操作，传统按用户席位收费会逐步受到按使用量、任务量或结果收费模式的挑战。

## Reasoning chain

Agent 可能减少直接操作软件的人数；席位数与客户获得的价值逐渐脱钩；厂商需要采用更接近算力消耗、任务执行或业务结果的计价单位。

## Supporting evidence

已审核：`EVT-20260729-012` 显示 Salesforce 已同时采用按 Action、Conversation 和用户席位收费。

## Contradicting evidence

已审核：`EVT-20260219-001` 显示 Microsoft Copilot 的特定促销仍围绕企业席位和组织覆盖率。

## Alternative explanations

- 厂商可能将 Agent 作为高价席位附加功能。
- 企业偏好可预测预算，限制纯用量定价。
- 新定价与席位制可能长期并存。

## Key variables

- 主要厂商 Agent SKU 的计价单位。
- Agent 收入与席位收入的构成。
- 客户人均席位和 Agent 用量变化。
- 推理成本与毛利率。

## Falsification conditions

- 主要厂商长期维持席位模式且增长不受影响。
- 客户不接受任务或结果定价。
- Agent 使用未造成席位数量或软件操作方式变化。

## Investment implications

定价迁移可能扩大总收入，也可能冲击现有经常性收入质量。需要分别判断收入增量、替代效应、毛利率和可预测性。

## Unknowns

- 哪种定价单位最能平衡客户价值和厂商成本。
- 计价变化是增量收入还是存量收入重新包装。

## Review history

| Date | Old confidence | New confidence | Evidence | Reason |
|---|---:|---:|---|---|
| 2026-07-29 | — | 0.20 | — | 初始假设，商业证据高度不足 |
| 2026-07-29 | 0.20 | 0.28 | EVT-20260729-012, EVT-20260219-001 | 人工批准；混合计价已出现，但席位模式仍延续且收入影响未知 |
