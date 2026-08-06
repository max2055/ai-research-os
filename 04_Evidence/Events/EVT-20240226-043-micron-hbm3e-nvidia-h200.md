---
id: EVT-20240226-043
type: event
title: "Micron: HBM3E volume production will be part of NVIDIA H200 Tensor Core GPUs"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2024-02-26
source_ids: [SRC-20260806-053]
companies: [COM-micron, COM-nvidia]
technologies: []
products: []
thesis_links: []
confidence: 0.60
generation_method: structured
generation_fingerprint: 50d638c86afc582dd76090b16352834c6ef2c6f4d560db176c50648153dd4b29
citation_anchors:
- fact_id: F1
  source_id: SRC-20260806-053
  asset_path: "01_Inbox/_assets/SRC-20260806-053/20260805233824-6466a5afc5ae.html.extracted.txt"
  locator: L6
  quote: "Micron’s 24GB 8H HBM3E will be part of NVIDIA H200 Tensor Core GPUs, which will begin shipping in the second calendar quarter of 2024."
  quote_sha256: 535c956b5b09e540270bfcfc945b429e8b4dd57546de67f3443daf475a42a057
- fact_id: F2
  source_id: SRC-20260806-053
  asset_path: "01_Inbox/_assets/SRC-20260806-053/20260805233824-6466a5afc5ae.html.extracted.txt"
  locator: L10
  quote: "Micron’s HBM3E leads the industry with ~30% lower power consumption compared to competitive offerings."
  quote_sha256: 16114e2a0a284784acfcf142aded6e598f6b76da74e4ebc2594dc34edd8be717
source_independence_groups: [["SRC-20260806-053"]]
tags: []
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — Micron 宣布开始量产 HBM3E 方案，24GB 8H HBM3E 将成为 NVIDIA H200 Tensor Core GPU 的一部分，H200 将于 2024 Q2 开始出货。
  - Source: `SRC-20260806-053`
  - Anchor: `01_Inbox/_assets/SRC-20260806-053/20260805233824-6466a5afc5ae.html.extracted.txt#L6`
  - Quote: "Micron’s 24GB 8H HBM3E will be part of NVIDIA H200 Tensor Core GPUs, which will begin shipping in the second calendar quarter of 2024."
- **F2** — Micron 称其 HBM3E 功耗比竞品低约 30%，并提及 36GB 12-High HBM3E 样品于 2024 年 3 月推出。
  - Source: `SRC-20260806-053`
  - Anchor: `01_Inbox/_assets/SRC-20260806-053/20260805233824-6466a5afc5ae.html.extracted.txt#L10`
  - Quote: "Micron’s HBM3E leads the industry with ~30% lower power consumption compared to competitive offerings."

## Inferences

- Micron 官方点名 HBM3E 供应 NVIDIA H200 GPU，是双方点名的直接证据，支持 Micron SUPPLIES NVIDIA 关系。
- Micron 声称功耗比竞品低 30% 并强调时间领先，说明其在 HBM3E 早期与 SK hynix/Samsung 存在竞争。

## Research judgment

Micron 官方新闻稿（B 级来源，公司披露）。'will be part of NVIDIA H200 Tensor Core GPUs' 为点名式供应证据；'~30% lower power consumption compared to competitive offerings' 为营销声明，需独立验证。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | contextual | No Thesis relationship proposed. | 0.00 |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260806-053 | independent root |

## Alternative explanations

- 2024-02 的 H200 供应承诺是早期状态，后续份额与供货量可能有变化。
- 功耗优势为厂商自述，未经第三方基准验证。

## Unknowns

- Micron 在 NVIDIA HBM 中的实际份额与后续 HBM3E/HBM4 供货量未披露。
- 与 SK hynix/Samsung 的具体竞争格局数据未披露。

## Follow-up indicators

- Micron 财报中 HBM 收入与 AI 存储披露。
- NVIDIA 下一代 GPU 的 HBM 供应商结构。
