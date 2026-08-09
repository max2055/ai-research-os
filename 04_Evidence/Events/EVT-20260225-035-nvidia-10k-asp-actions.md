---
id: EVT-20260225-035
type: event
title: "NVIDIA 10-K 披露曾因渠道定价计划下调平均售价、并因供应商提价而上调部分产品价格"
created_at: 2026-08-09
updated_at: '2026-08-09'
status: active
review_status: reviewed
event_date: 2026-02-25
source_ids: [SRC-20260806-079]
companies: [COM-nvidia]
technologies: [INF-GPU]
products: []
thesis_links: []
confidence: 0.9
tags: [EV-PRICING, EV-FINANCIAL]
schema_version: 1
project_ids:
- PRJ-001
---

# Event

## Facts

NVIDIA 10-K 披露：公司曾不得不下调平均售价（ASP），包括因渠道定价计划而降价；同时因供应商提价而上调部分产品价格；并曾发生库存减记与取消费用。公司提示未来可能仍需如此。

## Inferences

GPU 定价同时受需求周期与供应链成本两端影响：渠道促销会压低 ASP，而上游（晶圆/封装/HBM）提价会向产品价格传导。NVIDIA 的 ASP 并非单向上行，存在双向波动机制。

## Research judgment

该事件是 AI 算力链价格传导的直接证据：NVIDIA 既有定价权（可上调价格转嫁供应商提价），也面临渠道去化时的降价压力。价格方向取决于供需失衡程度，而非单向涨价。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | — | 尚无直接关联 Thesis | 不调整 |

## Alternative explanations

- 该披露为风险因素回顾，不构成当期价格指引。
- 供应商提价主要来自先进封装与 HBM，而非逻辑晶圆。

## Unknowns

- 当期 ASP 实际方向与幅度。
- 渠道定价计划的规模与持续性。

## Follow-up indicators

- NVIDIA 后续季度数据中心的毛利率与 ASP 指引。
- 上游（台积电/HBM）价格调整公告。

## Review record

- Review date: 2026-08-09
- Reviewer: max
- Decision: approve
- Note: 批准
