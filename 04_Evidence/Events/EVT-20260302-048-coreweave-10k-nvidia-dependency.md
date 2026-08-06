---
id: EVT-20260302-048
type: event
title: "CoreWeave 10-K: deploys NVIDIA GB200/GB300 NVL72, among first to deploy NVIDIA Rubin platform"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-03-02
source_ids: [SRC-20260806-051]
companies: [COM-coreweave, COM-nvidia]
technologies: []
products: []
thesis_links: []
confidence: 0.70
generation_method: structured
generation_fingerprint: 789deca588aeec1dbf95b05d8219466113bee1b2f9ffb016f07068f4e295ba17
citation_anchors:
- fact_id: F1
  source_id: SRC-20260806-051
  asset_path: "01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt"
  locator: L198
  quote: "deploy the industry's most advanced hardware and architectures first—including NVIDIA GB200 and GB300 NVL72 systems for mission-critical AI—gives our customers a measurable edge in performance, efficiency, and scale. CoreWeave clusters also use cutting edge CPUs, including AMD and Intel chips, to power compute-intensive projects and to help our customers get more out of GPU compute."
  quote_sha256: d5dc5c8893b892efee9ea8ac6949a3b5737320a4f79d23c2979ab0e1426e7824
- fact_id: F2
  source_id: SRC-20260806-051
  asset_path: "01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt"
  locator: L201
  quote: "We continue to extend and enhance our foundational infrastructure with the latest GPU and CPU innovations, and expect to be among the first cloud providers to deploy the NVIDIA Rubin platform, expanding our support for large-scale inference, reasoning, and agentic AI."
  quote_sha256: 5b356e6c4a9f77e6d5a1e87f4854179dd4703daeba5f78dc6d523d787d56b61e
source_independence_groups: [["SRC-20260806-051"]]
tags: []
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — CoreWeave 在 FY2025 10-K 披露：其数据中心部署 NVIDIA GB200 和 GB300 NVL72 系统（mission-critical AI），并预计成为首批部署 NVIDIA Rubin 平台的云厂商。
  - Source: `SRC-20260806-051`
  - Anchor: `01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt#L198`
  - Quote: "deploy the industry's most advanced hardware and architectures first—including NVIDIA GB200 and GB300 NVL72 systems for mission-critical AI—gives our customers a measurable edge in performance, efficiency, and scale. CoreWeave clusters also use cutting edge CPUs, including AMD and Intel chips, to power compute-intensive projects and to help our customers get more out of GPU compute."
- **F2** — CoreWeave 10-K 披露：预计成为首批部署 NVIDIA Rubin 平台的云厂商，扩大对大规模推理、推理与 agentic AI 的支持。
  - Source: `SRC-20260806-051`
  - Anchor: `01_Inbox/_assets/SRC-20260806-051/20260805233758-c796cf3da3de.html.extracted.txt#L201`
  - Quote: "We continue to extend and enhance our foundational infrastructure with the latest GPU and CPU innovations, and expect to be among the first cloud providers to deploy the NVIDIA Rubin platform, expanding our support for large-scale inference, reasoning, and agentic AI."

## Inferences

- CoreWeave 云服务高度依赖 NVIDIA GPU 平台（GB200/GB300 NVL72 为 mission-critical，Rubin 为下一代核心），支持 CoreWeave DEPENDS_ON NVIDIA 关系。

## Research judgment

CoreWeave 10-K（A 级 SEC）。'deploy the industry's most advanced hardware ... including NVIDIA GB200 and GB300 NVL72 systems for mission-critical AI' 直接证明其对 NVIDIA 平台的依赖；NVIDIA 是其核心基础设施供应商。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | contextual | No Thesis relationship proposed. | 0.00 |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260806-051 | independent root |

## Alternative explanations

- CoreWeave 也使用 AMD/Intel CPU，GPU 供应商依赖并非完全单一。

## Unknowns

- CoreWeave 对 NVIDIA GPU 的采购金额与合同安排未在本段披露。

## Follow-up indicators

- CoreWeave 财报中 NVIDIA GPU 采购与供应商集中度披露。
