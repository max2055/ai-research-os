---
id: EVT-20260520-032
type: event
title: NVIDIA discloses long lead times and capacity commitments in AI supply chain
created_at: 2026-08-05
updated_at: '2026-08-05'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-05-20
source_ids: [SRC-20260805-040]
companies: [COM-nvidia, COM-tsmc, COM-sk-hynix]
technologies: []
products: []
thesis_links: []
confidence: 0.70
generation_method: structured
source_independence_groups:
- - SRC-20260805-040
citation_anchors:
- fact_id: F1
  source_id: SRC-20260805-040
  asset_path: "01_Inbox/_assets/SRC-20260805-040/20260805092726-1b5de37b973d.html.extracted.txt"
  locator: L581
  quote: "We have long manufacturing lead times and build finished products and maintain inventory in advance of anticipated demand. In periods of shortages impacting the semiconductor industry and/or limited supply or capacity in our supply chain, the lead times for certain supply may be extended. We have previously experienced and may continue to experience extended lead times of more than 12 months. To secure future supply and capacity, we have paid premiums, provided deposits, and entered into long-term supply agreements and capacity commitments, which have increased our product costs and this may continue. We may still be unable to secure sufficient commitments for capacity to address our business needs."
  quote_sha256: 49030c7a90dbceb05fde5fe96a740fc3f33eade4402ad9f1fb69869aaa4ca57c
- fact_id: F2
  source_id: SRC-20260805-040
  asset_path: "01_Inbox/_assets/SRC-20260805-040/20260805092726-1b5de37b973d.html.extracted.txt"
  locator: L605
  quote: "We continue to increase our supply and capacity purchases with existing and new suppliers to support our demand projections and increasing complexity of our data center products. We have also entered and may continue to enter into prepaid manufacturing and capacity agreements to supply both current and future products. The increased purchase volumes and integration of new suppliers and contract manufacturers into our supply chain creates more complexity in managing multiple suppliers with variations in production planning, execution and logistics. Our expanding product portfolio and varying component compatibility and quality may lead to increased inventory levels. We have incurred and may in the future incur inventory provisions or impairments if our inventory or supply or capacity commitments exceed demand for our products or demand declines. We are increasing our U.S.-based manufacturing and investing in specialized equipment and processes to support domestic production. We may experience delays or difficulties in scaling production as planned. Our ability to increase manufacturing capabilities will depend on the domestic manufacturing ecosystem's capacity to ramp production supply to the required volume timely. Delays or shortfalls could impact our ability to meet demand."
  quote_sha256: 93b2c6bccf18271f639da5cf85a354201cbbccb0431b27663a37dc674228e0c3
tags: []
---

# Event

## Facts

- **F1** — NVIDIA 在 2026-05-20 的 10-Q 中披露：半导体短缺时期部分供应 lead time
  可超过 12 个月；为锁定供应与产能已支付溢价、提供押金并签订长期供应协议与
  产能承诺，并称可能仍无法确保足够的产能承诺。
  - Source: `SRC-20260805-040`
  - Anchor: `01_Inbox/_assets/SRC-20260805-040/20260805092726-1b5de37b973d.html.extracted.txt#L581`
  - Quote: "We have long manufacturing lead times and build finished products and maintain inventory in advance of anticipated demand. ... extended lead times of more than 12 months. To secure future supply and capacity, we have paid premiums, provided deposits, and entered into long-term supply agreements and capacity commitments..."
- **F2** — NVIDIA 披露为支持数据中心产品的需求与复杂度，持续增加对现有与新
  供应商的供应与产能采购，并可能签订预付制造与产能协议。
  - Source: `SRC-20260805-040`
  - Anchor: `01_Inbox/_assets/SRC-20260805-040/20260805092726-1b5de37b973d.html.extracted.txt#L605`
  - Quote: "We continue to increase our supply and capacity purchases with existing and new suppliers to support our demand projections and increasing complexity of our data center products..."

## Inferences

- NVIDIA 依赖外部供应商的产能承诺（10-Q 明确"供应 lead time >12 个月"、"产能承诺"），
  支持 NVIDIA DEPENDS_ON 其上游供应商（晶圆代工、HBM）的关系方向。
- 供应链依赖是 AI 算力供应的关键约束——为锁定产能而支付溢价/预付，反映上游
  供给稀缺。

## Research judgment

- NVIDIA 10-Q 是公司披露（A 级来源），证明"公司披露了什么"，不等于供应链关系
  已被独立验证。HBM/代工的具体供应商名单未在引用段落点名。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | — | 未关联 Thesis | 无 |

Relationship must be `supporting`, `contradicting` or `contextual`.

## Alternative explanations

- NVIDIA 可能通过多供应商策略分散依赖，而非依赖单一供应商——供应链依赖的
  具体强度需逐供应商证据。
- "产能承诺"可能指向多家供应商（含非 TSMC/SK hynix 者），引用段落未点名。

## Unknowns

- 10-Q 未点名具体供应商（TSMC/SK hynix 为 Agent 推断的引用，非来源直接声明）。
- 产能承诺的金额与期限未披露。

## Follow-up indicators

- NVIDIA 后续 10-Q/10-K 中供应链与产能承诺表述。
- HBM/代工供应商的官方公告。
