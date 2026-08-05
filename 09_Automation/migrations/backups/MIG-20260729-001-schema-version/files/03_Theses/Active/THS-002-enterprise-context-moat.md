---
id: THS-002
type: thesis
title: 企业数据、权限和工作流将成为 Agent 时代的主要护城河
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: reviewed
thesis_status: active
confidence: 0.4
review_date: 2026-07-29
supporting_evidence: [EVT-20260714-009, EVT-20260722-010, EVT-20260729-013, EVT-20260729-014]
contradicting_evidence: [EVT-20260521-006]
companies:
  - COM-microsoft
  - COM-salesforce
  - COM-servicenow
  - COM-oracle
  - COM-sap
  - COM-palantir
technologies:
  - DEV-MEMORY
  - DEV-TOOL-PROTOCOL
  - DEV-ORCHESTRATION
tags:
  - MOAT-DATA
  - MOAT-PERMISSION
  - MOAT-WORKFLOW
---

# Thesis

## Core judgment

随着通用模型能力扩散，企业数据访问、权限治理、业务流程嵌入和系统集成将比单纯模型能力更能决定企业 Agent 的持续竞争力。

## Reasoning chain

企业任务需要私有上下文和真实系统操作；真实操作必须遵守身份、权限、审计和流程规则；控制这些资源的平台更容易提供可靠结果并形成迁移成本。

## Supporting evidence

已审核：

- `EVT-20260714-009`：Oracle 将业务对象、工作流、权限、审批和审计置于 Agent 原生运行时。
- `EVT-20260722-010`：ServiceNow 把 CMDB、治理与 Agent 平台结合。
- `EVT-20260729-013`：ServiceNow 以数据、工作流和权限构建 Agent Fabric。
- `EVT-20260729-014`：Palantir Ontology 为 Agent 统一数据、动作和范围化权限。

## Contradicting evidence

已审核：`EVT-20260521-006` 显示 MCP 正在标准化工具、长任务和授权接口，可能降低接口层锁定。

## Alternative explanations

- 模型厂商可能通过标准协议快速获得企业上下文。
- 数据和权限层可能标准化，无法形成超额价值。
- 企业客户可能采用多平台架构，降低单一厂商锁定。

## Key variables

- 企业连接器覆盖率。
- 权限继承和审计能力。
- 私有数据调用频率。
- 生产工作流集成数量。
- 客户迁移和多平台采用情况。

## Falsification conditions

- 通用 Agent 无需深度企业集成即可完成核心任务。
- 企业不愿为上下文、治理和集成支付溢价。
- 标准化显著降低数据和工作流的控制价值。

## Investment implications

若成立，拥有企业数据模型、权限体系和关键工作流的平台可能受益。技术优势仍需转化为客户采用、收入和单位经济性。

## Unknowns

- 标准协议会增强现有平台还是削弱平台锁定。
- 数据治理价值最终由应用、云还是独立 Agent 平台获取。

## Review history

| Date | Old confidence | New confidence | Evidence | Reason |
|---|---:|---:|---|---|
| 2026-07-29 | — | 0.30 | — | 初始机制较清晰，但尚无正式 Evidence |
| 2026-07-29 | 0.30 | 0.40 | EVT-20260714-009, EVT-20260722-010, EVT-20260729-013, EVT-20260729-014, EVT-20260521-006 | 人工批准；多平台证据支持，MCP 标准化构成反面约束 |
