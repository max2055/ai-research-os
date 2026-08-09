---
id: THS-009
type: thesis
title: NVIDIA 数据中心定价权受 HBM/先进封装供给与客户集中度约束
created_at: 2026-08-09
updated_at: '2026-08-09'
status: active
review_status: reviewed
thesis_status: active
confidence: 0.35
review_date: 2026-08-09
supporting_evidence: [EVT-20260225-035, EVT-20260520-032, EVT-20260302-047]
contradicting_evidence: [EVT-20260520-038, EVT-20260731-040]
companies:
- COM-nvidia
technologies:
- INF-GPU
- INF-HBM
tags:
- EV-PRICING
- EV-TECHNOLOGY
schema_version: 1
project_ids:
- PRJ-001
---

# Thesis

## Core judgment

NVIDIA 数据中心定价权不是单向的：HBM/先进封装供给紧张会抬升其成本，渠道去化会压低 ASP，
且收入集中于少数超大规模客户；若 AI 资本开支放缓，定价权将快速逆转。

## Reasoning chain

NVIDIA 依赖台积电先进封装与 SK hynix/Samsung/Micron 的 HBM，上游供给决定其交付能力；
同时其客户集中（CoreWeave/AWS/OpenAI 等少数大额合同），议价集中在买方一侧。
供给约束 + 客户集中 = 定价权被两头夹击，而非市场叙事中的完全卖方市场。

## Supporting evidence

已审核：

- `EVT-20260225-035`：NVIDIA 10-K 披露曾因渠道定价计划下调 ASP，并因供应商提价上调部分产品价格——价格双向波动。
- `EVT-20260520-032`：NVIDIA 披露长交期与产能承诺，供给约束影响交付。
- `EVT-20260302-047`：CoreWeave 10-K 将 AWS/Google/Microsoft/Oracle 列为关键云竞争对手，客户侧竞争激烈。

## Contradicting evidence

已审核：

- `EVT-20260520-038`：NVIDIA FY27 Q1 数据中心收入创纪录 $75.2B，$119B 供给承诺显示需求旺盛。
- `EVT-20260731-040`：AWS 与 OpenAI 扩大 $100B 多年承诺，长期需求锁定。

## Alternative explanations

- 供给约束 + 旺盛需求 = 卖方市场持续，定价权仍在 NVIDIA。
- HBM/先进封装扩产可能缓解成本压力。

## Key variables

- NVIDIA 数据中心毛利率。
- HBM/先进封装供给节奏。
- 客户集中度与大额合同续约。

## Falsification conditions

- NVIDIA 数据中心毛利率持续上升且 ASP 稳定上行。
- 上游供给扩张使成本占比下降。

## Investment implications

若成立，NVIDIA 的估值隐含的持续高毛利可能被供给成本与客户议价侵蚀；需监控毛利率与 ASP 数据而非仅看收入增速。当前证据为反方信号，不构成投资结论。

## Unknowns

- HBM/先进封装的实际扩产节奏。
- 大额合同的定价条款与毛利率。
- 需求持续性。

## Review history

| Date | Old confidence | New confidence | Evidence | Reason |
|---|---:|---:|---|---|
| 2026-08-09 | — | 0.35 | EVT-20260225-035, EVT-20260520-032 | 初始反面 Thesis（E-021 3-company pilot）：定价权受供给与客户集中度约束 |

