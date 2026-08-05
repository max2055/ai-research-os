---
id: EVT-20260416-033
type: event
title: TSMC discloses advanced 2nm process and CoWoS packaging for AI accelerators
created_at: 2026-08-05
updated_at: '2026-08-05'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-04-16
source_ids: [SRC-20260805-041]
companies: [COM-tsmc, COM-nvidia]
technologies: []
products: []
thesis_links: []
confidence: 0.70
generation_method: structured
source_independence_groups:
- - SRC-20260805-041
citation_anchors:
- fact_id: F1
  source_id: SRC-20260805-041
  asset_path: "01_Inbox/_assets/SRC-20260805-041/20260805092817-c3ebd05cd8fb.html.extracted.txt"
  locator: L1357-1359
  quote: "efforts have enabled us to offer customers access to advanced process technologies, such as 7-, 5-, 3- and 2-nanometer"
  quote_sha256: 4a73cee3209fb7b9dbb34f5d4be49dcea89ed6ac4c6dacbe609090968697fe40
- fact_id: F2
  source_id: SRC-20260805-041
  asset_path: "01_Inbox/_assets/SRC-20260805-041/20260805092817-c3ebd05cd8fb.html.extracted.txt"
  locator: L1180-1181
  quote: "SoIC® manufacturing services and CoWoS® advanced packaging services, to enable homogeneous and heterogeneous chip"
  quote_sha256: eb765739fc8700a2dc4d616545b24ea2b3c69d8ad6936261204796c791c11fb1
- fact_id: F3
  source_id: SRC-20260805-041
  asset_path: "01_Inbox/_assets/SRC-20260805-041/20260805092817-c3ebd05cd8fb.html.extracted.txt"
  locator: L1175-1176
  quote: "Based on advanced process nodes, a variety of HPC products have been launched, such as AI accelerators, including AI"
  quote_sha256: 7ea44422c818d6df07d9b7ed696bf5bc860d45db39658a2afdce4fd6f11cbdd0
tags: []
---

# Event

## Facts

- **F1** — TSMC 在 2025 年报（20-F，2026-04-16 提交）中披露：提供 7/5/3/2nm
  先进制程量产，先于竞争者实施，并称将持续保持先进制程技术领导地位。
  - Source: `SRC-20260805-041`
  - Anchor: `01_Inbox/_assets/SRC-20260805-041/20260805092817-c3ebd05cd8fb.html.extracted.txt#L1357-1359`
  - Quote: "efforts have enabled us to offer customers access to advanced process technologies, such as 7-, 5-, 3- and 2-nanometer..."
- **F2** — TSMC 披露提供 SoIC 与 CoWoS 先进封装服务，支持同质/异质芯片集成。
  - Source: `SRC-20260805-041`
  - Anchor: `01_Inbox/_assets/SRC-20260805-041/20260805092817-c3ebd05cd8fb.html.extracted.txt#L1180-1181`
  - Quote: "SoIC® manufacturing services and CoWoS® advanced packaging services, to enable homogeneous and heterogeneous chip..."
- **F3** — TSMC 披露基于先进制程节点已推出多种 HPC 产品，包括 AI 加速器。
  - Source: `SRC-20260805-041`
  - Anchor: `01_Inbox/_assets/SRC-20260805-041/20260805092817-c3ebd05cd8fb.html.extracted.txt#L1175-1176`
  - Quote: "Based on advanced process nodes, a variety of HPC products have been launched, such as AI accelerators, including AI..."

## Inferences

- TSMC 的先进制程（3/2nm）与 CoWoS 封装是 AI 加速器（GPU/ASIC）的关键供应环节，
  支持 TSMC SUPPLIES 算力芯片设计公司（NVIDIA/AMD/Broadcom 等）的关系方向。
- TSMC 先进制程"先于竞争者实施"支持 TSMC 与三星 Foundry/英特尔在先进制程的
  竞争关系（COMPETES_WITH）。

## Research judgment

- TSMC 20-F 是公司披露（A 级来源），证明"公司披露了什么"；"技术领导地位"是
  公司主张，市场地位需第三方数据核验。引用段落未点名 NVIDIA。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | — | 未关联 Thesis | 无 |

Relationship must be `supporting`, `contradicting` or `contextual`.

## Alternative explanations

- "先于竞争者"可能仅指工艺节点时序，不必然等于市场份额领先。
- AI 加速器客户名单未点名（NVIDIA 为推断）。

## Unknowns

- 未点名具体客户（NVIDIA/AMD 为推断）。
- CoWoS 产能与收入占比未披露。

## Follow-up indicators

- TSMC 法说会/月营收中 AI 相关收入披露。
- 3nm/2nm 量产节奏与客户公告。
