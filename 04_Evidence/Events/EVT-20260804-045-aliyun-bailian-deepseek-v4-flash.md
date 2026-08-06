---
id: EVT-20260804-045
type: event
title: "阿里云百炼 Token Plan 上新 DeepSeek-V4-Flash 模型（2026-08-04）"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-08-04
source_ids: [SRC-20260806-055]
companies: [COM-aliyun, COM-deepseek]
technologies: []
products: []
thesis_links: []
confidence: 0.50
generation_method: structured
generation_fingerprint: 8dba02137229645524cc64c2f703f03f2970ccc129a52e885d9ff5b238e452fb
citation_anchors:
- fact_id: F1
  source_id: SRC-20260806-055
  asset_path: "01_Inbox/_assets/SRC-20260806-055/20260805233843-5ba1f84389a3.html.extracted.txt"
  locator: L36
  quote: "本次更新最令人振奋的是模型能力的全面跃升。用户现在可以首发尝鲜Qwen3.8-Max，这是通义千问系列的最新旗舰，具备强大的原生多模态处理能力。同时，计划内新增了HappyHorse 1.1系列，支持高质量的文本生成视频和图像生成视频，以及DeepSeek-V4-Flash模型，为开发者提供了更多样化的选择。"
  quote_sha256: 734a151f8fa695085221983e8d800fa90479d5f78762326646abf93fcf834502
- fact_id: F2
  source_id: SRC-20260806-055
  asset_path: "01_Inbox/_assets/SRC-20260806-055/20260805233843-5ba1f84389a3.html.extracted.txt"
  locator: L77
  quote: "集成使用：将API Key集成到您的应用或智能体中，即可开始调用Qwen3.8-Max、DeepSeek等全量模型。"
  quote_sha256: 36c3870ac4c64c42ab9d74ad27667faaea04305b31301ba04c3e455ee01ef645
source_independence_groups: [["SRC-20260806-055"]]
tags: []
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — 阿里云百炼 Token Plan 升级公告：新增 DeepSeek-V4-Flash 模型，与 Qwen3.8-Max 旗舰、HappyHorse 1.1 视频生成模型共同构成订阅服务模型池。
  - Source: `SRC-20260806-055`
  - Anchor: `01_Inbox/_assets/SRC-20260806-055/20260805233843-5ba1f84389a3.html.extracted.txt#L36`
  - Quote: "本次更新最令人振奋的是模型能力的全面跃升。用户现在可以首发尝鲜Qwen3.8-Max，这是通义千问系列的最新旗舰，具备强大的原生多模态处理能力。同时，计划内新增了HappyHorse 1.1系列，支持高质量的文本生成视频和图像生成视频，以及DeepSeek-V4-Flash模型，为开发者提供了更多样化的选择。"
- **F2** — 阿里云百炼 Token Plan 使用说明：用户集成 API Key 后即可调用 Qwen3.8-Max、DeepSeek 等全量模型。
  - Source: `SRC-20260806-055`
  - Anchor: `01_Inbox/_assets/SRC-20260806-055/20260805233843-5ba1f84389a3.html.extracted.txt#L77`
  - Quote: "集成使用：将API Key集成到您的应用或智能体中，即可开始调用Qwen3.8-Max、DeepSeek等全量模型。"

## Inferences

- 阿里云百炼平台提供 DeepSeek-V4-Flash 模型的托管/订阅服务，是阿里云官方点名的直接证据，支持 Aliyun SUPPLIES DeepSeek（模型托管供应）关系。
- 阿里云百炼同时提供自研 Qwen 系列与第三方 DeepSeek，说明其为多模型聚合平台。

## Research judgment

阿里云开发者社区文章（B 级来源）。注意：文章版权声明为'阿里云实名注册用户自发贡献'，非阿里云官方直发文档，权威性弱于官方产品文档；但内容为产品功能公告，且平台为阿里云官方域名。'新增 DeepSeek-V4-Flash 模型' 为点名的产品事实。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | contextual | No Thesis relationship proposed. | 0.00 |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260806-055 | independent root |

## Alternative explanations

- 文章由社区用户发布，可能存在信息偏差；应以百炼控制台实际模型列表为准。
- 模型'上架'不等同于大规模商业化供货。

## Unknowns

- DeepSeek-V4-Flash 在百炼的调用量与商业规模未披露。
- 阿里云是否向 DeepSeek 采购模型权重的商业安排未披露。

## Follow-up indicators

- 百炼控制台模型列表更新。
- 阿里云官方产品文档对 DeepSeek 模型的正式收录。
