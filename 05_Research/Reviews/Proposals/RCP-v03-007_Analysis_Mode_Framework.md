# Rule Change Proposal RCP-v03-007

Proposal ID：RCP-v03-007

状态：proposed（草稿，待 max 批准）

创建日期：2026-08-08

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Schema、永久 ID、Agent 边界：

- Phase 4（`05_Phase_4_Analysis_Mode_Framework.md`）Mode Definition 与 Analysis Run 语义
- 新增 `analysis_mode`（`MOD-ANL-<slug>-vN`）与 `analysis_run`（`ANL-YYYYMMDD-NNN`）两个正式对象类型
- Agent 边界：Analysis Run 默认 pending，不自动权威化；Open Discovery 模式只产候选 Hypothesis，不直接权威化

## Observed problem

- 当前分析无统一契约：同一证据的不同研究视角（价值链 / 供需 / 技术曲线 / 基本面 / 竞争 / 估值 / 情景 / 红队 / 开放发现）缺乏版本化、可复现、可比较的载体。
- 无 Run 冻结机制：无法保证"同输入 + 同模式版本 + 同模型参数 → 同输出"，跨模式结论差异无法定位到假设/时间/证据权重。
- 自由 Prompt 产出不可审计：不强制 Fact / Inference / Judgment 分离，无 prohibited_conclusions，AI 判断可能与证据混排。

## Proposed change

1. **`analysis_mode` 正式对象（`MOD-ANL-<slug>-vN`）**：模式定义是**版本化契约**（Phase 4 §2 草案）。字段：purpose、applicable_scopes、required/optional_input_types、required_questions、required_output_sections、assumption_policy、evidence_policy、counterevidence_policy、time_horizons、prohibited_conclusions、prompt_template_path、output_schema_path、evaluator_version、status、review_status。**模式变化必须升级版本，不静默修改已运行模式**（§2）。
2. **`analysis_run` 正式对象（`ANL-YYYYMMDD-NNN`）**：单次运行冻结 mode_id、scope_ids、as_of、inputs（source/event/impact/thesis）、snapshot hash、model_provider/model_id/parameters、prompt_hash、output_hash、generation_method、status、review_status（§3 草案）。正文含 Facts used / Inferences / Judgments / Contradicting evidence / Alternative explanations / Unknowns / Indicators / Mode-specific output / Limitations。
3. **Analysis Run ≠ Thesis/Recommendation**：Run 是某模式的产物，不自动成为权威研究结论（§3）。仅 reviewed run 可进入 Report。
4. **Open Discovery 模式边界**：只生成候选 Hypothesis（pending），不直接权威化（§1）。
5. **首批 9 模式**（§4）：Value Chain / Supply-Demand / Technology Curve / Company Fundamental / Competitive Dynamics / Expectations & Valuation / Scenario / Red Team / Open Discovery。
6. **Agent 边界**：Agent 可起草 mode 定义与生成 run，但 mode 的 active 状态与 run 的 reviewed 状态均须人工批准；run 不自动改 Thesis confidence。

## 不做的事

- 不自动生成投资建议或买卖指令。
- 不把 run 输出当权威事实。
- 不静默修改已运行模式定义。
- 不用自由 Prompt 冒充版本化契约。
- 不用模型 confidence 冒充客观概率。

## Review points（reviewer：max，待批准）

1. `analysis_mode`（MOD-ANL-<slug>-vN）与 `analysis_run`（ANL-YYYYMMDD-NNN）落为正式对象类型
2. 模式版本化契约（升级版本、不静默修改已运行模式）
3. Run 冻结输入/模式/模型/参数/输出（snapshot + prompt_hash + output_hash）
4. Analysis Run ≠ Thesis/Recommendation；仅 reviewed run 可进 Report
5. Open Discovery 只产候选 Hypothesis，不直接权威化
6. 首批 9 模式清单

- Decision：待 max 批准
- Reviewer：max
- Date：2026-08-08
- Reason：与 Phase 4 §1-§4 草案一致；"版本化契约 + Run 冻结 + 非权威化"防分析不可复现与 AI 判断混排。

## Implementation record

- Changed files：本文件（proposed）；生效后由 WP-400（D-001~004）起落地 schema + registry + contract
- Test result：not run（治理边界批准，无代码变更）
- Validation result：`research-os validate` 0 errors / 0 warnings（无对象变更）
- Effective date：待 max 批准

## 参考

- `05_Phase_4_Analysis_Mode_Framework.md` §1-§4
- `00_Master_Roadmap.md` §9（Analysis Mode 权威边界 决策点）
- RCP-v03-003（正式对象/永久 ID 体系）、RCP-v03-006（Impact 先例）
