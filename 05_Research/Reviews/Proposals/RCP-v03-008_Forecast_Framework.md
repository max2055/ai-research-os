# Rule Change Proposal RCP-v03-008

Proposal ID：RCP-v03-008

状态：approved（2026-08-09，reviewer：max）

创建日期：2026-08-09

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Schema、永久 ID、Agent 边界：

- Phase 5（`06_Phase_5_Forecast_and_Investment_Decision.md`）Forecast / Resolution / Calibration 语义
- 新增 `forecast`（`FCT-YYYYMMDD-NNN`）与 `forecast_resolution`（`RES-YYYYMMDD-NNN`）两个正式对象类型
- Agent 边界：模型可准备 structured spec，确定性 service 校验渲染，人工决定 open/active

## Observed problem

- 当前研究只有"看好/不看好"的开放判断，无可证伪、可按期解析、可校准的决策记录。
- Forecast 无统一契约：问题、期限、结果定义、概率、base rate 缺版本化载体，无法校准。
- 到期 Forecast 无解析机制：无法区分预测对错，也无 Brier/calibration 度量。

## Proposed change

1. **`forecast` 正式对象（`FCT-YYYYMMDD-NNN`）**：Phase 5 §3 草案。字段含 question、outcome_type（binary/categorical/numeric_range）、outcome_definition、base_rate、probability、range_low/high、unit、forecast_as_of、horizon、resolution_date、resolution_source_requirements、evidence_ids、analysis_run_ids、assumptions、alternative_outcomes、falsification_conditions、status（draft/open/resolved/void/superseded）、review_status。
2. **`forecast_resolution` 正式对象（`RES-YYYYMMDD-NNN`）**：Phase 5 §4 草案。字段含 forecast_id、resolved_at、outcome、observed_value、source_ids、decision（correct/incorrect/partial/void/ambiguous）、resolution_reason、scoring_method、score、reviewer、review_status。**append-only**：到期 Forecast 不可后见修改，必须用 Resolution 解析。
3. **开仓与解析规则**：`open` 必须是 `reviewed`；probability 仅适用于定义明确的结果；base rate 缺失写 unknown 不伪造；**resolution criteria 在 open 后不可改变**；修改问题必须创建新 Forecast、旧对象 superseded。
4. **Calibration**：Phase 5 §9——binary Brier Score、calibration buckets、categorical log score、numeric interval coverage、resolution timeliness、void/ambiguous rate、edit/supersede rate；按 Analysis Mode/Sector/horizon/researcher 分组。**小样本不排名模式**；calibration 只在相同 outcome 类型和合理样本量下比较；股价表现不等于产业预测正确；结果归因区分 Thesis/valuation/timing/外生冲击。
5. **Agent 边界**：模型可准备 structured spec 和 Forecast 提案（pending），确定性 service 校验/渲染；`open`/`active` 由人工批准；到期 Forecast 只能由人工/系统按已冻结 criteria 解析，不能静默改期。

## 不做的事

- 不自动下单或计算最终仓位。
- 不承诺目标价精度。
- 不用短期股价验证长期产业 Thesis。
- 不把 Forecast 数量当作能力。
- 不允许到期后修改原问题、概率或期限。
- 不使用未许可或无时间戳市场数据。
- 首版不建设完整组合优化器。

## Review points（reviewer：max）

1. `forecast`（FCT-*）与 `forecast_resolution`（RES-*）落为正式对象类型
2. open 必须 reviewed；probability 仅用于定义明确结果；base rate 缺失写 unknown
3. 到期 Forecast 不可后见修改，必须用 Resolution 解析（append-only）
4. resolution criteria 在 open 后不可改变；修改问题=新 Forecast + superseded
5. Calibration 指标集 + 小样本不排名 + 分组口径
6. Agent 边界：提案 pending，open/active/解析由人工批准

- Decision：批准（accept RCP-v03-008 as drafted，6 项人审点全部采纳默认）
- Reviewer：max
- Date：2026-08-09
- Reason：与 Phase 5 §1-§4、§9 草案一致；"可证伪、按期解析、可校准、到期不可后见修改"防止预测无法归因。

## Implementation record

- Changed files：本文件（proposed → approved）；生效后由 WP-500（E-003~004）落地 forecast/resolution schema
- Test result：not run（治理边界批准，无代码变更）
- Validation result：`research-os validate` 0 errors / 0 warnings（无对象变更）
- Effective date：2026-08-09（批准即生效；WP-500 起实施）

## 参考

- `06_Phase_5_Forecast_and_Investment_Decision.md` §1-§4、§9
- RCP-v03-003（正式对象/永久 ID 体系）、RCP-v03-007（Analysis Mode 先例）
