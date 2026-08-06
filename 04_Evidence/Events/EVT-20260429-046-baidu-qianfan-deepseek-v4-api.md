---
id: EVT-20260429-046
type: event
title: "百度千帆 Day 0 适配提供 DeepSeek-V4 预览版 API 服务（2026-04-29）"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-04-29
source_ids: [SRC-20260806-056]
companies: [COM-baidu-cloud, COM-deepseek]
technologies: []
products: []
thesis_links: []
confidence: 0.50
generation_method: structured
generation_fingerprint: 1ee9830100ec7376cc6d392ee99fa5e34a1fc4d731b8dab1b3d2eb276bb29b2a
citation_anchors:
- fact_id: F1
  source_id: SRC-20260806-056
  asset_path: "01_Inbox/_assets/SRC-20260806-056/20260805233914-da9ecd47f9fa.html.extracted.txt"
  locator: L14
  quote: "百度千帆Day 0适配提供 DeepSeek-V4 预览版 API 服务，对外定价与 DeepSeek 官方保持一致。"
  quote_sha256: 632d62e9e7fa94edf4b505e5083045db0263761cf0f99c6caff8770aae992177
- fact_id: F2
  source_id: SRC-20260806-056
  asset_path: "01_Inbox/_assets/SRC-20260806-056/20260805233914-da9ecd47f9fa.html.extracted.txt"
  locator: L15
  quote: "企业用户与开发者无需关注环境配置、模型优化与资源调度，仅需通过百度千帆控制台或 API 即可直接调用DeepSeek-V4-Pro（DeepSeek-V4-Flash即将全量开放），实现“开箱即用”，极大降低使用门槛，快速体验并验证大模型能力。"
  quote_sha256: 795d3d3e49ac73f81e5b3d3a7bfcb1f60b01afb15d7b757316a2f9b58dc05035
source_independence_groups: [["SRC-20260806-056"]]
tags: []
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — 百度千帆公告：Day 0 适配提供 DeepSeek-V4 预览版 API 服务，对外定价与 DeepSeek 官方保持一致；企业用户与开发者可通过千帆控制台或 API 直接调用 DeepSeek-V4-Pro（V4-Flash 即将全量开放）。
  - Source: `SRC-20260806-056`
  - Anchor: `01_Inbox/_assets/SRC-20260806-056/20260805233914-da9ecd47f9fa.html.extracted.txt#L14`
  - Quote: "百度千帆Day 0适配提供 DeepSeek-V4 预览版 API 服务，对外定价与 DeepSeek 官方保持一致。"
- **F2** — 百度千帆公告：企业用户与开发者无需关注环境配置、模型优化与资源调度，仅需通过百度千帆控制台或 API 即可直接调用 DeepSeek-V4-Pro（DeepSeek-V4-Flash 即将全量开放），实现'开箱即用'。
  - Source: `SRC-20260806-056`
  - Anchor: `01_Inbox/_assets/SRC-20260806-056/20260805233914-da9ecd47f9fa.html.extracted.txt#L15`
  - Quote: "企业用户与开发者无需关注环境配置、模型优化与资源调度，仅需通过百度千帆控制台或 API 即可直接调用DeepSeek-V4-Pro（DeepSeek-V4-Flash即将全量开放），实现“开箱即用”，极大降低使用门槛，快速体验并验证大模型能力。"

## Inferences

- 百度千帆平台提供 DeepSeek-V4 模型的 API 托管服务，是百度官方点名的直接证据，支持 Baidu Cloud SUPPLIES DeepSeek（模型托管供应）关系。
- 'Day 0 适配'与'定价与 DeepSeek 官方一致'说明百度千帆是 DeepSeek 模型的早期分发渠道之一。

## Research judgment

百度智能云千帆社区官方公告（B 级来源，官方平台公告）。'Day 0 适配提供 DeepSeek-V4 预览版 API 服务'为点名的直接产品事实。注意：'API 服务'为模型托管/推理供应，不是向 DeepSeek 提供算力，关系语义为平台托管第三方模型。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | contextual | No Thesis relationship proposed. | 0.00 |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260806-056 | independent root |

## Alternative explanations

- 'Day 0 适配'是平台接入公告，不等同于 DeepSeek 官方与百度的商业合作披露。
- 预览版 API 服务的规模与稳定性未经独立验证。

## Unknowns

- 百度千帆上 DeepSeek-V4 的调用量级未披露。
- 百度与 DeepSeek 的商业协议条款未披露。

## Follow-up indicators

- 千帆控制台模型列表与定价更新。
- DeepSeek 官方 API 与第三方平台的分发对比。
