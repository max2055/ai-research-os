---
id: EVT-20260716-037
type: event
title: "TSMC 2Q26: advanced-node (3nm/5nm) 63% of revenue, strong leading-edge demand"
created_at: 2026-08-05
updated_at: '2026-08-05'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-07-16
source_ids: [SRC-20260805-047]
companies: [COM-tsmc, COM-nvidia]
technologies: []
products: []
thesis_links: []
confidence: 0.75
generation_method: structured
source_independence_groups:
- - SRC-20260805-047
citation_anchors:
- fact_id: F1
  source_id: SRC-20260805-047
  asset_path: "01_Inbox/_assets/SRC-20260805-047/20260805134930-6e877956870c.html.extracted.txt"
  locator: L11
  quote: "In the second quarter, shipments of 2-nanometer accounted for 3% of total wafer revenue; 3-nanometer accounted for 30%; 5-nanometer accounted for 33%; and 7-nanometer accounted for 11%. Advanced technologies, defined as 7-nanometer and more advanced technologies, accounted for 77% of total wafer revenue."
  quote_sha256: 51545aef69a8f7e93f7d93789aa7dd7f3eb96e392ad37283ad2466ad178ea14b
- fact_id: F2
  source_id: SRC-20260805-047
  asset_path: "01_Inbox/_assets/SRC-20260805-047/20260805134930-6e877956870c.html.extracted.txt"
  locator: L12
  quote: "“Our business in the second quarter was supported by strong demand for our leading-edge process technologies,” said Wendell Huang, Senior VP and Chief Financial Officer of TSMC. “Moving into third quarter 2026, we expect our business to be supported by continued strong demand for our leading-edge process technologies, including the steep ramp-up of our 2-nanometer technology.”"
  quote_sha256: 3024804e4363c5f0a7261e5e026dd3cf470b4fedbe8ebe9527024ff0d023c04f
- fact_id: F3
  source_id: SRC-20260805-047
  asset_path: "01_Inbox/_assets/SRC-20260805-047/20260805134930-6e877956870c.html.extracted.txt"
  locator: L51
  quote: "TSMC pioneered the pure-play foundry business model when it was founded in 1987, and has been the world’s leading dedicated semiconductor foundry ever since. The Company supports a thriving ecosystem of global customers and partners with the industry’s leading process technologies and portfolio of design enablement solutions to unleash innovation for the global semiconductor industry. With global operations spanning Asia, Europe, and North America, TSMC serves as a committed corporate citizen around the world."
  quote_sha256: bad88f0baf5f0b469d55eaebea7e8a9c09b21e9d215bf891aa60b4a592faac90
tags: []
---

# Event

## Facts

- **F1** — TSMC 于 2026-07-16 披露 2Q26 业绩：2nm 占晶圆收入 3%、3nm 30%、
  5nm 33%、7nm 11%（先进制程合计约 77%）。
  - Source: `SRC-20260805-047`
  - Anchor: `01_Inbox/_assets/SRC-20260805-047/20260805134930-6e877956870c.html.extracted.txt#L11`
  - Quote: "In the second quarter, shipments of 2-nanometer accounted for 3% of total wafer revenue; 3-nanometer accounted for 30%; 5-nanometer accounted for 33%..."
- **F2** — TSMC CFO 表示 2Q26 业务受领先制程技术强劲需求支撑，预计 3Q26
  延续。
  - Source: `SRC-20260805-047`
  - Anchor: `01_Inbox/_assets/SRC-20260805-047/20260805134930-6e877956870c.html.extracted.txt#L12`
  - Quote: "Our business in the second quarter was supported by strong demand for our leading-edge process technologies..."
- **F3** — TSMC 自称自 1987 年创立以来一直是全球领先的纯代工模式半导体代工厂。
  - Source: `SRC-20260805-047`
  - Anchor: `01_Inbox/_assets/SRC-20260805-047/20260805134930-6e877956870c.html.extracted.txt#L51`
  - Quote: "TSMC pioneered the pure-play foundry business model... has been the world’s leading dedicated semiconductor foundry ever since."

## Inferences

- TSMC 先进制程（2nm/3nm/5nm）占收入主导 + 全球领先代工厂地位，支持
  TSMC SUPPLIES 算力芯片设计公司（NVIDIA 等）与先进制程竞争（vs 三星/英特尔）
  的关系——证据为财务数据 + 公司主张（A 级来源）。
- 与 TSMC 20-F（EVT-033）互相印证：先进制程量产 + 领先地位。

## Research judgment

- TSMC 财报新闻稿（A 级来源，公司披露）——2Q26 财务与制程占比为硬数据；
  "全球领先"是公司主张。NVIDIA 客户关系未在本来源点名。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | — | 未关联 Thesis | 无 |

Relationship must be `supporting`, `contradicting` or `contextual`.

## Alternative explanations

- 先进制程需求强劲不必然等于 AI 芯片需求（可能含手机/PC）。
- "全球领先代工厂"是公司主张，需市场份额数据核验。

## Unknowns

- 未点名客户（NVIDIA 为推断）。
- AI 相关收入占比未披露。

## Follow-up indicators

- TSMC 后续季度营收与制程占比。
- 3nm/2nm 客户公告。
