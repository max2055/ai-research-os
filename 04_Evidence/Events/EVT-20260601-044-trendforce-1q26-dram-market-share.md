---
id: EVT-20260601-044
type: event
title: "TrendForce 1Q26 DRAM: Samsung 38.5%, SK hynix 28.8%, Micron 22.4% market share; SK hynix highest HBM bit shipment ratio"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: reviewed
event_date: 2026-06-01
source_ids: [SRC-20260806-054]
companies: [COM-samsung-electronics, COM-sk-hynix, COM-micron]
technologies: []
products: []
thesis_links: []
confidence: 0.50
generation_method: structured
generation_fingerprint: 12ac6296b25e57464087c08bcc2c61bc17ad97a1940a2617c397bfc767e9fabe
citation_anchors:
- fact_id: F1
  source_id: SRC-20260806-054
  asset_path: "01_Inbox/_assets/SRC-20260806-054/20260805233835-76df2409471d.html.extracted.txt"
  locator: L146
  quote: "分析第一季主要DRAM供應商營收表現，第一名Samsung產品的平均銷售單價(ASP)大幅成長、居三大原廠之首，且server DRAM營收占比也是最高，推升其第一季營收季增高達93.4%，為373.2億美元，市占上升至38.5%。"
  quote_sha256: 32a8f35b440c9866d8f9a5a002cade16ee9764d470ddc8b5f03699a0ee5a84b1
- fact_id: F2
  source_id: SRC-20260806-054
  asset_path: "01_Inbox/_assets/SRC-20260806-054/20260805233835-76df2409471d.html.extracted.txt"
  locator: L147
  quote: "SK hynix的HBM位元出貨比重為三大原廠最高，然2026年HBM合約價下滑，抑制其整體產品售價漲幅，第一季營收達279.8億美元，季增62.5%，排名第二，市占率調整至28.8%。第三名Micron營收季增達81.6%，上升至217.5億美元，市占率22.4%持平前一季。"
  quote_sha256: 52058fbc96a076d36049e7c8fffdba7626748a34e3e6a2b4f83726cb662c352d
source_independence_groups: [["SRC-20260806-054"]]
tags: []
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

- **F1** — TrendForce 报告：2026 Q1 全球 DRAM 行业营收季增 81% 达 $97B；第一名 Samsung 营收 $37.32B、市占 38.5%，第二名 SK hynix 营收 $27.98B、市占 28.8%，第三名 Micron 营收 $21.75B、市占 22.4%。
  - Source: `SRC-20260806-054`
  - Anchor: `01_Inbox/_assets/SRC-20260806-054/20260805233835-76df2409471d.html.extracted.txt#L146`
  - Quote: "分析第一季主要DRAM供應商營收表現，第一名Samsung產品的平均銷售單價(ASP)大幅成長、居三大原廠之首，且server DRAM營收占比也是最高，推升其第一季營收季增高達93.4%，為373.2億美元，市占上升至38.5%。"
- **F2** — TrendForce 报告：SK hynix 的 HBM 位元出货比重为三大原厂最高，但 2026 HBM 合约价下滑抑制其营收增幅，第一季营收 $27.98B、市占 28.8%；第三名 Micron 营收 $21.75B、市占 22.4%。
  - Source: `SRC-20260806-054`
  - Anchor: `01_Inbox/_assets/SRC-20260806-054/20260805233835-76df2409471d.html.extracted.txt#L147`
  - Quote: "SK hynix的HBM位元出貨比重為三大原廠最高，然2026年HBM合約價下滑，抑制其整體產品售價漲幅，第一季營收達279.8億美元，季增62.5%，排名第二，市占率調整至28.8%。第三名Micron營收季增達81.6%，上升至217.5億美元，市占率22.4%持平前一季。"

## Inferences

- Samsung、SK hynix、Micron 三家在 DRAM/HBM 市场直接竞争：同一市场按份额排名，SK hynix 的 HBM 位元出货比重为三家最高，支持 SK hynix COMPETES_WITH Samsung、SK hynix COMPETES_WITH Micron、Samsung COMPETES_WITH Micron 关系。
- 三家市占合计约 90%（38.5+28.8+22.4），DRAM/HBM 市场高度集中。

## Research judgment

TrendForce 为 B 级来源（有方法说明的专业研究机构，市场调研报告）。营收与市占为第三方的估计数据，非公司披露；'HBM 位元出货比重最高' 为相对竞争地位的间接证据。竞争关系（同市场争夺份额）由市场份额数据支撑，但 COMPETES_WITH 是行业常识级判断，证据强度中等。

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
| — | contextual | No Thesis relationship proposed. | 0.00 |

## Source independence

| Group | Sources | Treatment |
|---|---|---|
| IG-01 | SRC-20260806-054 | independent root |

## Alternative explanations

- TrendForce 数据为调研估计，可能与实际份额有偏差。
- DRAM 与 HBM 是不同细分市场，三家在不同细分竞争力不同（SK hynix HBM 强、Samsung DRAM 总量强）。

## Unknowns

- 三家在 HBM 细分的具体份额数据未在本报告披露。
- TrendForce 数据口径（营收 vs 位元出货）需注意区分。

## Follow-up indicators

- TrendForce 后续 HBM 专项报告。
- 三家公司财报中的 HBM 收入披露。
