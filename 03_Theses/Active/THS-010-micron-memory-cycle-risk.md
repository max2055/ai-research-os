---
id: THS-010
type: thesis
title: 内存周期下行将重演，侵蚀 Micron 高位盈利
created_at: 2026-08-09
updated_at: '2026-08-09'
status: active
review_status: reviewed
thesis_status: active
confidence: 0.4
review_date: 2026-08-09
supporting_evidence: [EVT-20251003-001, EVT-20260601-044]
contradicting_evidence: [EVT-20260625-001, EVT-20260728-036]
companies:
- COM-micron
technologies:
- INF-DRAM
- INF-HBM
tags:
- EV-PRICING
- EV-FINANCIAL
schema_version: 1
project_ids:
- PRJ-001
---

# Thesis

## Core judgment

DRAM 价格的历史波动区间（年变动 +40%/-40%）说明内存是强周期业务：当前 AI 需求推高的高位盈利
会在供给扩张与需求放缓时被价格下行侵蚀，Micron 的高估值隐含的持续盈利不可持续。

## Reasoning chain

内存行业供给弹性低、产能切换慢，价格由供需缺口决定而非成本；历史上周期高点后伴随大幅价格下行。
Micron 当前盈利与估值隐含"AI 内存结构性短缺持续"的假设，但 HBM 产能转产通用 DRAM 与新增产能
会在需求边际放缓时快速逆转价格。

## Supporting evidence

已审核：

- `EVT-20251003-001`：Micron 10-K 披露过去五年 DRAM ASP 年变动区间 +40% 至 -40%——价格高波动。
- `EVT-20260601-044`：TrendForce 1Q26 DRAM 份额（Samsung 38.5%/SK hynix 28.8%/Micron 22.4%），竞争格局接近。

## Contradicting evidence

已审核：

- `EVT-20260625-001`：Micron 10-Q 披露生成式 AI 带动 HBM/先进内存需求增长。
- `EVT-20260728-036`：SK hynix 2Q26 创纪录，AI 内存需求强劲。

## Alternative explanations

- AI 内存需求是结构性而非周期性，价格中枢上移。
- HBM 与通用 DRAM 价格分化，通用 DRAM 下行不影响 HBM 盈利。

## Key variables

- DRAM ASP 季度变化。
- HBM 出货占比。
- 供给端新增产能与转产。

## Falsification conditions

- 通用 DRAM 价格持续高位且波动收窄。
- 供给扩张未引发价格下行。

## Investment implications

若成立，Micron 现价隐含的持续高盈利将被周期下行修正；需以 DRAM 价格与毛利率数据跟踪，而非线性外推当前盈利。当前证据为反方信号，不构成投资结论。

## Unknowns

- AI 内存需求是否为结构性增长。
- HBM 对通用 DRAM 产能的挤占程度。
- 价格下行的时间点与幅度。

## Review history

| Date | Old confidence | New confidence | Evidence | Reason |
|---|---:|---:|---|---|
| 2026-08-09 | — | 0.40 | EVT-20251003-001, EVT-20260601-044 | 初始反面 Thesis（E-021 3-company pilot）：内存周期下行将侵蚀高位盈利 |

