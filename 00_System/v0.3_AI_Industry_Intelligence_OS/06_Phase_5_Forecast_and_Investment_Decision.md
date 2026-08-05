# Phase 5：Forecast、Valuation 与投资决策支持

状态：`proposed`  
建议周期：5–7 周，之后持续解析  
前置：Phase 4；RCP-v03-008～009 获批  

## 1. 阶段目标

把开放式“看好/不看好”变成可证伪、可按期解析和可校准的决策记录：

- Forecast 有明确问题、期限、结果定义和概率；
- Scenario 有驱动、条件、敏感性和反面路径；
- Valuation 使用有日期、有来源、口径匹配的数据；
- Recommendation Draft 区分公司价值、证券价格和组合适配；
- 到期 Forecast 不可后见修改，必须用 Resolution 解析；
- 模式和研究过程按长期 calibration 评估；
- 所有正式建议需人工批准，系统不交易。

## 2. 非目标

- 不自动下单；
- 不自动计算最终仓位；
- 不承诺目标价精度；
- 不用短期股价验证长期产业 Thesis；
- 不把 Forecast 数量当作能力；
- 不允许到期后修改原问题、概率或期限；
- 不使用未许可或无时间戳市场数据；
- v0.3 首版不建设完整组合优化器。

## 3. Forecast Schema 草案

```yaml
id: FCT-YYYYMMDD-NNN
type: forecast
title:
project_ids: []
scope_ids: []
question:
outcome_type: binary|categorical|numeric_range
outcome_definition:
base_rate:
probability:
range_low:
range_high:
unit:
created_at:
forecast_as_of:
horizon:
resolution_date:
resolution_source_requirements: []
evidence_ids: []
analysis_run_ids: []
assumptions: []
alternative_outcomes: []
falsification_conditions: []
status: draft|open|resolved|void|superseded
review_status: pending
```

规则：

- `open` 必须是 reviewed；
- probability 仅适用于定义明确的结果；
- base rate 缺失时写 unknown，不伪造；
- 范围预测必须说明 measure、period、unit 和数据来源；
- 修改问题必须创建新 Forecast，旧对象 superseded；
- resolution criteria 在 open 后不可改变。

## 4. Forecast Resolution Schema

```yaml
id: RES-YYYYMMDD-NNN
type: forecast_resolution
forecast_id:
resolved_at:
outcome:
observed_value:
source_ids: []
decision: correct|incorrect|partial|void|ambiguous
resolution_reason:
scoring_method:
score:
reviewer:
review_status: pending
```

`ambiguous` 和 `void` 必须说明原因，不能为了改善准确率排除失败预测。

## 5. Scenario Contract

每个投资级分析至少包含：

- Downside；
- Base；
- Upside；
- 可选 tail risk。

每个情景记录：

- time horizon；
- starting state；
- 3–5 个关键驱动；
- 来源或明确 Judgment；
- 传导机制；
- operating result；
- financial result；
- valuation implication；
- probability（若使用）；
- catalysts；
- falsifiers；
- two-variable sensitivity；
- countervailing factors。

情景结果不能验证输入假设。

## 6. Valuation Snapshot

扩展现有 v0.2 模块：

```yaml
id: VAL-YYYYMMDD-NNN
type: valuation_snapshot
company_id:
security_id:
as_of:
market_price:
currency:
shares:
debt:
cash:
other_adjustments:
valuation_identity:
denominator_period:
source_ids: []
event_ids: []
scenario_set:
freshness_threshold:
review_status: pending
```

必须确定性计算 Equity Value、Enterprise Value 和 matched-period multiple。外部 consensus
必须记录 provider、access date、range、fiscal period、definition 和 license。

## 7. Recommendation Schema 草案

```yaml
id: REC-YYYYMMDD-NNN
type: recommendation
company_id:
security_id:
as_of:
time_horizon:
research_posture: avoid|watch|research|investment_candidate
direction: positive|neutral|negative|uncertain
conviction: low|medium|high
valuation_snapshot_id:
forecast_ids: []
thesis_ids: []
evidence_ids: []
analysis_run_ids: []
expected_case:
downside_case:
upside_case:
catalysts: []
falsification_conditions: []
key_risks: []
unknowns: []
freshness_date:
status: draft|active|closed|superseded
review_status: pending
```

首版最高默认等级建议为 `investment_candidate`，不直接产生 `buy/sell`。若研究者要求
增加 buy/sell/position size，必须另建 Portfolio & Execution RCP。

## 8. 决策流程

```text
Reviewed Evidence/Impact
→ Analysis Runs
→ human-selected assumptions
→ Forecast proposals
→ Scenario + Valuation Snapshot
→ Recommendation Draft
→ deterministic completeness/freshness checks
→ human review
→ active recommendation
→ catalysts/falsifiers monitoring
→ Forecast Resolution
→ recommendation close/supersede
→ calibration review
```

模型可以准备 structured spec；确定性 service 负责校验和渲染；人工决定是否 open/active。

## 9. Calibration

建议指标：

- binary Forecast Brier Score；
- calibration buckets；
- categorical log score（样本足够后）；
- numeric interval coverage；
- resolution timeliness；
- void/ambiguous rate；
- Forecast edit/supersede rate；
- 按 Analysis Mode、Sector、horizon 和 researcher 分组；
- recommendation thesis hit/miss attribution。

注意：

- 小样本不排名模式；
- calibration 只在相同 outcome 类型和合理样本量下比较；
- 股价表现不等于产业预测正确；
- 结果归因要区分 Thesis、valuation、timing 和外生冲击。

## 10. 工作包

| ID | 任务 | 交付 | 验收 |
|---|---|---|---|
| E-001 | Forecast RCP | RCP-v03-008 | open/resolution/calibration 语义批准 |
| E-002 | Recommendation RCP | RCP-v03-009 | 最高等级与人工边界批准 |
| E-003 | Forecast Schema | schemas | outcome/horizon/probability validation |
| E-004 | Resolution Schema | schemas | append-only、source/reviewer |
| E-005 | Valuation Snapshot Schema | schemas | price/period/source/freshness |
| E-006 | Recommendation Schema | schemas | Company/Security 分离 |
| E-007 | forecast spec/renderer | workflow | proposal→pending object |
| E-008 | open transition | lifecycle/review | reviewed 才能 open |
| E-009 | due/stale service | services | due/overdue/unresolved query |
| E-010 | resolution workflow | services | 原 Forecast 不修改 |
| E-011 | deterministic valuation | services | formulas/units/matched periods |
| E-012 | scenario workflow | services/templates | 三情景+敏感性 |
| E-013 | recommendation renderer | workflow | completeness/freshness Gate |
| E-014 | supersession/close | lifecycle | 新旧指针原子更新 |
| E-015 | calibration engine | metrics | Brier/buckets/interval coverage |
| E-016 | CLI | forecast/valuation/recommendation | dry-run/apply/review |
| E-017 | Decision Dashboard | UI | forecasts、valuation、risks、history |
| E-018 | alerts | jobs | due forecast/catalyst/falsifier |
| E-019 | security/data license tests | validation | provider/timestamp/license |
| E-020 | 10-forecast field Gate | review packet | 人工审核 open Forecast |
| E-021 | 3-company decision Pilot | real objects | 完整建议但不交易 |
| E-022 | first resolutions | resolution packet | 到期后真实解析 |
| E-023 | acceptance/recovery | docs/tests | immutable history/rebuild |

## 11. 建议 CLI

```text
research-os forecast draft --spec <json> [--apply]
research-os forecast list --status open --due-before <date>
research-os forecast resolve --id FCT-ID --spec <json> [--apply]
research-os forecast calibration [--mode MODE-ID] [--sector SEG-ID]
research-os valuation draft --spec <json> [--apply]
research-os valuation freshness --id VAL-ID
research-os recommendation draft --spec <json> [--apply]
research-os recommendation list --status active
research-os recommendation close --id REC-ID --reason ... [--apply]
```

## 12. Validation

必须检查：

- Forecast outcome 可解析；
- open Forecast 有人工 Review Decision；
- resolution date 晚于 as-of；
- 概率范围；
- numeric unit/range；
- Resolution 引用 reviewed Source；
- Forecast 原文在 Resolution 后未改变；
- Valuation price、shares、debt、cash 均有日期和来源；
- numerator/denominator period 匹配；
- Recommendation 引用 reviewed Thesis/Evidence；
- contradicting Evidence、unknowns、falsifier 不为空；
- stale Valuation 不能支持 active Recommendation；
- Recommendation 不包含未经批准的 buy/sell/position size；
- supersession 双向一致。

## 13. Field Gate

### 10 个 Forecast

- 至少 4 binary、3 categorical、3 numeric range；
- 覆盖 supply、technology、company operating、adoption 和 financial；
- 全部人工检查 outcome definition 和 resolution source；
- 不要求为赶 Gate 选择容易预测的问题。

### 3 家公司

- 至少来自两个不同板块；
- 完整 Company/Security/Valuation/Scenario/Forecast/Recommendation Draft；
- 每家公司至少一个核心反面 Thesis；
- 价格和市场预期 freshness 合格；
- 人工批准最高到 `investment_candidate`；
- 不自动交易。

### 解析 Gate

至少等首批 Forecast 自然到期后再评价；不得预填未来结果。记录 ambiguous 和 void，
形成第一份 calibration report。Phase 工程能力可以先 accepted，但 v0.3 final release 必须
包含真实 resolution。

## 14. 回滚

- Recommendation Draft 不修改 Thesis/Forecast；
- 市场数据错误时 supersede Valuation Snapshot，不覆盖；
- Forecast 问题错误时 void/supersede 并保留原因；
- calibration 算法升级保存版本和旧结果；
- 自动提醒可禁用，不改变对象；
- 若 Recommendation Field Gate 不通过，产品退回 Forecast/Valuation worksheet，停止
  active Recommendation 能力。

