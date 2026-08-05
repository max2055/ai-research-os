---
id: EVT-20260520-038
type: event
title: "NVIDIA FY27 Q1: record Data Center revenue $75.2B, $119B supply commitments"
created_at: 2026-08-05
updated_at: '2026-08-05'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-05-20
source_ids: [SRC-20260805-048]
companies: [COM-nvidia, COM-supermicro, COM-dell]
technologies: []
products: []
thesis_links: []
confidence: 0.80
generation_method: structured
source_independence_groups:
- - SRC-20260805-048
citation_anchors:
- fact_id: F1
  source_id: SRC-20260805-048
  asset_path: "01_Inbox/_assets/SRC-20260805-048/20260805135918-08d93b6aa1c2.html.extracted.txt"
  locator: L23
  quote: "Data Center revenue for the first quarter was a record $75.2 billion, up 92% from a year ago and up 21% sequentially, driven by the ramp of our Blackwell 300 products and demand for our InfiniBand, Spectrum-X™ Ethernet, and NVLink™ solutions. Hyperscale revenue increased sequentially and remained at approximately 50% of Data Center revenue, while the remaining 50% came from a continued diversification of customers, including AI Clouds, industrial, enterprise, and sovereign customers. No shipments of Data Center Hopper products to China occurred during the quarter, compared with $4.6 billion in the first quarter of fiscal year 2026."
  quote_sha256: 74d70511a12896972de1f60f141ef79a21b21404a72b658edacf4a3a59fa71f5
- fact_id: F2
  source_id: SRC-20260805-048
  asset_path: "01_Inbox/_assets/SRC-20260805-048/20260805135918-08d93b6aa1c2.html.extracted.txt"
  locator: L37
  quote: "Inventory was $25.8 billion, up from $21.4 billion sequentially, and total supply-related commitments were $119.0 billion. We have strategically secured inventory and capacity to meet demand beyond the next several quarters."
  quote_sha256: d74f1a2d6b962d1827c2104dda035be414f13a1ebb8305a32ca45b7e37857476
tags: []
---

# Event

## Facts

- **F1** — NVIDIA 于 2026-05-20 披露 FY27 Q1：数据中心收入创纪录 $75.2B
  （同比 +92%），由 Blackwell 300 产品爬坡与 InfiniBand/Spectrum-X/NVLink
  需求驱动；Hyperscale 约占数据中心收入 50%。
  - Source: `SRC-20260805-048`
  - Anchor: `01_Inbox/_assets/SRC-20260805-048/20260805135918-08d93b6aa1c2.html.extracted.txt#L23`
  - Quote: "Data Center revenue for the first quarter was a record $75.2 billion, up 92% from a year ago..."
- **F2** — NVIDIA 披露总供应链相关承诺 $119B（库存 $25.8B），已战略性锁定
  库存与产能以应对未来数个季度需求。
  - Source: `SRC-20260805-048`
  - Anchor: `01_Inbox/_assets/SRC-20260805-048/20260805135918-08d93b6aa1c2.html.extracted.txt#L37`
  - Quote: "total supply-related commitments were $119.0 billion. We have strategically secured inventory and capacity to meet demand beyond the next several quarters."

## Inferences

- NVIDIA 数据中心产品（Blackwell 300）是 AI 算力核心，其收入规模（$75.2B）
  反映 AI 基础设施需求——支持 NVIDIA 在算力链中的关键地位（环3→5 服务器、
  环7 云的需求源头）。
- $119B 供应链承诺进一步印证 NVIDIA 对上游（代工/HBM）的产能锁定依赖
  （与 EVT-032 互相印证）。

## Research judgment

- NVIDIA CFO 注释（A 级来源，公司披露）——FY27 Q1 财务为硬数据；"需求驱动"
  是公司归因。Supermicro/Dell 未点名（推断的服务器整机客户）。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | — | 未关联 Thesis | 无 |

Relationship must be `supporting`, `contradicting` or `contextual`.

## Alternative explanations

- 数据中心收入高增长可能含网络/软件（非纯 GPU 硬件）。
- Supermicro/Dell 客户关系为推断（未点名）。

## Unknowns

- 具体服务器整机客户未点名。
- 中国收入（Q2 指引明确不含）对供应链的影响。

## Follow-up indicators

- NVIDIA 后续季度数据中心收入与供应链承诺。
- 服务器整机厂商（Supermicro/Dell）的 AI 服务器收入披露。
