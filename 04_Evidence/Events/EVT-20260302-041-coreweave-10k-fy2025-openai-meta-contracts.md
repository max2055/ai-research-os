---
id: EVT-20260302-041
type: event
title: "CoreWeave 10-K FY2025: OpenAI $6.5B+$11.9B and Meta $14.2B committed contracts named"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-03-02
source_ids: [SRC-20260806-051]
companies: [COM-coreweave, COM-openai, COM-meta, COM-microsoft]
technologies: []
products: []
thesis_links: []
confidence: 0.80
generation_method: structured
generation_fingerprint: 3b228d0ed2ff8ba802fa49b2947a498e73f7e8991a85c99f7a4f685d2e40a0e2
citation_anchors:
- fact_id: F1
  source_id: SRC-20260806-051
  asset_path: "01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt"
  locator: L367
  quote: "In May 2025, we entered into a master services agreement with OpenAI OpCo, LLC (\"OpenAI\") and in September 2025, we entered into an order form under this master services agreement pursuant to which OpenAI has committed to pay us up to approximately $6.5 billion through May 31, 2031"
  quote_sha256: e7abe27e532e95944496210b50f03b130aec12d24db0af4d56dcc3b7e2ad2f6c
- fact_id: F2
  source_id: SRC-20260806-051
  asset_path: "01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt"
  locator: L548
  quote: "in March 2025, we entered into a master services agreement with OpenAI, a private company, pursuant to which OpenAI has committed to pay us up to approximately $11.9 billion through October 2030. Other significant customers include Microsoft and Meta."
  quote_sha256: 3df86c3312da39116dc253da027c1375ff68e10db3530b25be8b69df43d53c07
- fact_id: F3
  source_id: SRC-20260806-051
  asset_path: "01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt"
  locator: L367
  quote: "in September 2025, we entered into an order form under an existing master services agreement pursuant to which Meta Platforms, Inc. (\"Meta\") initially committed to pay us up to approximately $14.2 billion through December 2031"
  quote_sha256: d25238efba2938b2aad2e6a59d19ad77e414a93442008da6b59fb3bef0675049
source_independence_groups: [["SRC-20260806-051"]]
tags: []
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — CoreWeave 在 FY2025 10-K 披露：2025 年 5 月与 OpenAI 签订主服务协议（MSA），2025 年 9 月签订订单，OpenAI 承诺至 2031-05-31 支付约 $6.5B；2025 年 3 月另有一份 MSA，OpenAI 承诺至 2030 年 10 月支付约 $11.9B。
  - Source: `SRC-20260806-051`
  - Anchor: `01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt#L367`
  - Quote: "In May 2025, we entered into a master services agreement with OpenAI OpCo, LLC (\"OpenAI\") and in September 2025, we entered into an order form under this master services agreement pursuant to which OpenAI has committed to pay us up to approximately $6.5 billion through May 31, 2031"
- **F2** — CoreWeave 在 FY2025 10-K 披露：2025 年 3 月与 OpenAI 签订主服务协议，OpenAI 承诺至 2030 年 10 月支付约 $11.9B；其他重要客户包括 Microsoft 和 Meta。
  - Source: `SRC-20260806-051`
  - Anchor: `01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt#L548`
  - Quote: "in March 2025, we entered into a master services agreement with OpenAI, a private company, pursuant to which OpenAI has committed to pay us up to approximately $11.9 billion through October 2030. Other significant customers include Microsoft and Meta."
- **F3** — CoreWeave 在 FY2025 10-K 披露：2025 年 9 月与 Meta 签订订单，Meta 初步承诺至 2031 年 12 月支付约 $14.2B；2025 财年 67% 收入来自最大客户 Microsoft。
  - Source: `SRC-20260806-051`
  - Anchor: `01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt#L367`
  - Quote: "in September 2025, we entered into an order form under an existing master services agreement pursuant to which Meta Platforms, Inc. (\"Meta\") initially committed to pay us up to approximately $14.2 billion through December 2031"

## Inferences

- CoreWeave 向 OpenAI 提供算力（GPU 云）服务，合同金额 $6.5B + $11.9B 为双方点名的直接证据，支持 CoreWeave SUPPLIES OpenAI 关系。
- CoreWeave 向 Meta 提供算力服务，$14.2B 承诺为双方点名的直接证据，支持 CoreWeave SUPPLIES Meta 关系。
- Microsoft 是 CoreWeave 最大客户（FY2025 收入 67%），支持 CoreWeave SUPPLIES Microsoft 关系，但 Microsoft 相关 REL 不在本轮范围。

## Research judgment

CoreWeave 10-K 为 A 级来源（SEC 归档）。合同金额为硬数据，但为'承诺支付上限'而非实际收入确认；'significant customer' 披露证明供应关系存在，实际供货量与收入占比需后续季报验证。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | contextual | No Thesis relationship proposed. | 0.00 |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260806-051 | independent root |

## Alternative explanations

- 合同金额为承诺上限，实际履约可能低于披露值；CoreWeave 可能通过第三方租赁产能供货。

## Unknowns

- OpenAI/Meta 实际消耗量与收入确认节奏未披露。
- CoreWeave 向 OpenAI 供货的 GPU 型号与规模未披露。

## Follow-up indicators

- CoreWeave 后续 10-Q/10-K 的收入集中度披露。
- OpenAI 算力多元化公告。
