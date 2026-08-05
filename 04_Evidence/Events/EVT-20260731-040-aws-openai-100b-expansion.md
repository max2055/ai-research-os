---
id: EVT-20260731-040
type: event
title: "AWS and OpenAI expand $38B commitment by $100B over 8 years (AWS chips)"
created_at: 2026-08-05
updated_at: '2026-08-05'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-07-31
source_ids: [SRC-20260805-050]
companies: [COM-aws, COM-openai]
technologies: []
products: []
thesis_links: []
confidence: 0.85
generation_method: structured
source_independence_groups:
- - SRC-20260805-050
citation_anchors:
- fact_id: F1
  source_id: SRC-20260805-050
  asset_path: "01_Inbox/_assets/SRC-20260805-050/20260805140925-d07b8a88fa44.html.extracted.txt"
  locator: L211
  quote: "In Q1 2026, AWS and OpenAI Group PBC (“OpenAI”) announced an expansion of the existing $38.0 billion multi-year commitment and commercial arrangement with OpenAI by $100.0 billion over 8.0 years, which includes contractual obligations related to the performance of AWS chips."
  quote_sha256: eb8062c29aa39d1665df64aaa8e16a5fcb5fb421e3e71b6646598cba37502e7a
tags: []
---

# Event

## Facts

- **F1** — Amazon 在 Q2 2026 10-Q（2026-07-31）披露：AWS 与 OpenAI 于 2026
  Q1 宣布将现有 $38B 多年承诺扩大 $100B（8 年），含 AWS 芯片性能相关合同义务。
  - Source: `SRC-20260805-050`
  - Anchor: `01_Inbox/_assets/SRC-20260805-050/20260805140925-d07b8a88fa44.html.extracted.txt#L211`
  - Quote: "In Q1 2026, AWS and OpenAI Group PBC (“OpenAI”) announced an expansion of the existing $38.0 billion multi-year commitment and commercial arrangement with OpenAI by $100.0 billion over 8.0 years, which includes contractual obligations related to the performance of AWS chips."

## Inferences

- AWS 向 OpenAI 提供云算力/芯片服务的承诺总额达 $138B（$38B + $100B），
  是**双方点名的直接证据**——支持 AWS SUPPLIES OpenAI 与 AWS ENABLES
  OpenAI 的关系方向，证据强度高（合同金额披露）。
- AWS 芯片（Trainium 等）性能义务在合同中明确——AWS 在 AI 算力供给中的
  关键角色。

## Research judgment

- Amazon 10-Q（A 级来源，SEC 归档）——合同金额与条款为硬数据；"AWS 芯片
  性能义务"表明供应关系具体化。这是云→模型供应的**直接证据**。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | — | 未关联 Thesis | 无 |

Relationship must be `supporting`, `contradicting` or `contextual`.

## Alternative explanations

- 合同含 OpenAI 对 AWS 的承诺（双向），不等同于纯 AWS→OpenAI 供应。
- 具体芯片型号与交付节奏未披露。

## Unknowns

- 合同履约时间表与收入确认方式未披露。
- 其他云厂商（微软 Azure）与 OpenAI 的安排未涉及。

## Follow-up indicators

- Amazon 后续 10-Q 中 AWS-OpenAI 合同进展披露。
- OpenAI 的算力多元化公告。
