# Rule Change Proposal RCP-v03-009

Proposal ID：RCP-v03-009

状态：approved（2026-08-09，reviewer：max）

创建日期：2026-08-09

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Schema、永久 ID、Agent 边界：

- Phase 5（`06_Phase_5_Forecast_and_Investment_Decision.md`）Valuation / Recommendation 语义
- 新增 `valuation_snapshot`（`VAL-YYYYMMDD-NNN`）与 `recommendation`（`REC-YYYYMMDD-NNN`）两个正式对象类型
- Agent 边界：Recommendation Draft 最高默认等级 `investment_candidate`；正式建议需人工批准

## Observed problem

- 开放式"看好/不看好"未区分公司价值、证券价格与组合适配，无法形成可审计的建议。
- Valuation 无日期/来源/口径匹配约束，无法保证 matched-period 比较。
- 无最高建议等级与人工边界，无法防止模型/系统自动产生 buy/sell。

## Proposed change

1. **`valuation_snapshot` 正式对象（`VAL-YYYYMMDD-NNN`）**：Phase 5 §6 草案。字段含 company_id、security_id、as_of、market_price、currency、shares、debt、cash、other_adjustments、valuation_identity、denominator_period、source_ids、event_ids、scenario_set、freshness_threshold、review_status。**确定性计算** Equity Value、Enterprise Value、matched-period multiple；外部 consensus 记录 provider/access date/range/fiscal period/definition/license。
2. **`recommendation` 正式对象（`REC-YYYYMMDD-NNN`）**：Phase 5 §7 草案。字段含 company_id、security_id、as_of、time_horizon、research_posture（avoid/watch/research/investment_candidate）、direction（positive/neutral/negative/uncertain）、conviction（low/medium/high）、valuation_snapshot_id、forecast_ids、thesis_ids、evidence_ids、analysis_run_ids、expected/downside/upside_case、catalysts、falsification_conditions、key_risks、unknowns、freshness_date、status（draft/active/closed/superseded）、review_status。
3. **Company/Security 分离**：company-level 建议（价值/研究姿态）与 security-level 建议（价格方向/估值）分开建模，不混用。
4. **最高默认等级 `investment_candidate`**：v0.3 首版不直接产生 buy/sell。若研究者要求 buy/sell/position size，必须另建 Portfolio & Execution RCP。
5. **决策流程**：Reviewed Evidence/Impact → Analysis Runs → 人工选假设 → Forecast proposals → Scenario + Valuation Snapshot → Recommendation Draft → 确定性 completeness/freshness 校验 → 人工 review → active recommendation → catalysts/falsifiers 监控 → Forecast Resolution → close/supersede → calibration review。
6. **Agent 边界**：模型可准备 Recommendation Draft（pending），确定性 service 校验渲染；`active` 由人工批准；系统不交易。

## 不做的事

- 不自动下单。
- 不自动计算最终仓位。
- 不承诺目标价精度。
- 首版不产生 buy/sell/position size。
- 不使用无时间戳或未许可市场数据。

## Review points（reviewer：max）

1. `valuation_snapshot`（VAL-*）与 `recommendation`（REC-*）落为正式对象类型
2. Valuation 确定性计算 Equity/Enterprise Value + matched-period multiple；consensus 记录来源
3. Company/Security 分离（公司价值 vs 证券价格不混用）
4. **最高默认等级 investment_candidate**，buy/sell 需另建 Portfolio & Execution RCP
5. 决策流程 + 确定性校验 → 人工 review → active；系统不交易
6. Agent 边界：Draft pending，active 人工批准

- Decision：批准（accept RCP-v03-009 as drafted，6 项人审点全部采纳默认）
- Reviewer：max
- Date：2026-08-09
- Reason：与 Phase 5 §1-§2、§6-§8 草案一致；"Company/Security 分离 + investment_candidate 最高默认等级 + 人工批准"防止模型/系统自动产生 buy/sell。

## Implementation record

- Changed files：本文件（proposed → approved）；生效后由 WP-500（E-005~006）落地 valuation/recommendation schema
- Test result：not run（治理边界批准，无代码变更）
- Validation result：`research-os validate` 0 errors / 0 warnings（无对象变更）
- Effective date：2026-08-09（批准即生效；WP-500 起实施）

## 参考

- `06_Phase_5_Forecast_and_Investment_Decision.md` §1-§2、§6-§8
- RCP-v03-007（Analysis Mode 先例）、RCP-v03-008（Forecast 先例）
