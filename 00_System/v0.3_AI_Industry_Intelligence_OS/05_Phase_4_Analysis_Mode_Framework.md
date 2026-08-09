# Phase 4：Analysis Mode Framework

状态：`completed`（2026-08-09，D-019 10-case Gate PASS + D-020 acceptance）  
建议周期：4–6 周  
前置：reviewed Evidence + reviewed Impact；RCP-v03-007 获批  

## 1. 阶段目标

建立“同一证据、不同研究视角”的可复现分析框架：

- 分析模式不是自由 Prompt，而是版本化合同；
- 每次运行冻结输入、模式版本、模型、参数和输出；
- 强制区分 Fact、Inference、Judgment；
- 输出共同结论、分歧、假设、反证和 unknowns；
- 支持确定性检查和人工审核；
- 开放发现模式只生成候选 Hypothesis，不直接权威化。

## 2. Mode Definition Schema 草案

```yaml
id: MOD-ANL-<slug>-vN
type: analysis_mode
name:
purpose:
applicable_scopes: [sector, company, technology, event, thesis]
required_input_types: []
optional_input_types: []
required_questions: []
required_output_sections: []
assumption_policy:
evidence_policy:
counterevidence_policy:
time_horizons: []
prohibited_conclusions: []
prompt_template_path:
output_schema_path:
evaluator_version:
status: proposed|active|deprecated
review_status: pending
```

模式定义变化必须升级版本，不能静默修改已运行模式。

## 3. Analysis Run Schema 草案

```yaml
id: ANL-YYYYMMDD-NNN
type: analysis_run
mode_id:
scope_ids: []
as_of:
input_source_ids: []
input_event_ids: []
input_impact_ids: []
input_thesis_ids: []
input_snapshot_hash:
model_provider:
model_id:
model_parameters:
prompt_hash:
output_hash:
generation_method:
status: draft|completed|failed|superseded
review_status: pending
```

正文至少包含 Facts used、Inferences、Judgments、Contradicting evidence、Alternative
explanations、Unknowns、Indicators、Mode-specific output 和 Limitations。

Analysis Run 是某个模式的产物，不等于 Thesis 或 Recommendation。

## 4. 首批模式

### 4.1 Value Chain Mode

回答：

- 哪个环节控制稀缺资源、入口、标准或客户关系？
- 瓶颈和利润池正在向哪里移动？
- 谁获得/失去议价权？
- 传导路径与时间滞后是什么？
- 哪个环节增长但无法保留利润？

必须输出当前链、变化后链、受益/受损环节、机制、证伪指标。

### 4.2 Supply-Demand Mode

回答产能、供给弹性、库存、需求、利用率、价格和扩产周期。禁止把公司订单直接外推为
行业需求，必须说明周期、地区、产品代际和口径。

### 4.3 Technology Curve Mode

回答性能、成本、能效、成熟度、替代路径、扩散速度和工程约束。必须区分 benchmark、
实验室结果、产品发布、客户试点和规模生产。

### 4.4 Company Fundamental Mode

回答收入来源、客户、商业模式、成本、毛利、资本开支、现金流、竞争优势和风险。必须把
AI-specific metric 与公司整体指标分开。

### 4.5 Competitive Dynamics Mode

回答竞争者、替代品、进入壁垒、生态、分发、数据、权限、标准、供应依赖和商业模式冲突。
不得仅依据产品功能列表判定护城河。

### 4.6 Expectations & Valuation Mode

复用 v0.2 估值合同，回答当前价格和市场预期隐含什么经营结果。要求 dated price、shares、
capital structure、expectation source、matched denominator 和 freshness。

### 4.7 Scenario Mode

Downside/Base/Upside，明确驱动变量、概率（如使用）、时间、结果、敏感性、催化剂和证伪。
情景概率是 Judgment。

### 4.8 Red Team Mode

必须寻找：反面 Evidence、共同上游、替代机制、时间错配、价值无法被公司捕获、估值已反映、
监管/执行风险和不可观察变量。

### 4.9 Open Discovery Mode

寻找异常、弱信号、跨板块组合和未建模关系。输出只能是：

- hypothesis proposal；
- why surprising；
- minimum evidence needed；
- disconfirming search plan；
- related entities；
- risk of spurious correlation。

不得直接产生 reviewed Thesis 或 Recommendation。

## 5. Mode Runner

```text
Select scope and as-of
→ resolve reviewed inputs
→ freeze input manifest/hash
→ validate mode requirements
→ render versioned prompt/spec
→ model execution
→ parse structured output
→ deterministic contract validation
→ create pending Analysis Run
→ compare with other modes
→ human review or promote insights to Thesis/Forecast
```

失败运行也要记录 error 类型，但不能留下半成品正式对象。

## 6. Mode Compare 与综合

比较器输出：

- shared facts；
- shared conclusions；
- conflicting conclusions；
- different assumptions；
- different time horizons；
- evidence omitted by each mode；
- confidence differences；
- questions requiring human decision。

禁止使用简单多数投票。综合权重只能来自：

- Evidence quality/independence；
- mechanism completeness；
- mode scope fit；
- forecast calibration history；
- explicit researcher judgment。

任何加权公式必须版本化、可解释，并且不把小样本 calibration 当作稳定能力。

## 7. 工作包

| ID | 任务 | 交付 | 验收 |
|---|---|---|---|
| D-001 | Mode 权威边界 RCP | RCP-v03-007 | 模式/Run/Thesis 边界批准 |
| D-002 | Mode Definition Schema | schemas | version/status/path validation |
| D-003 | Analysis Run Schema | schemas | immutable input/output fingerprint |
| D-004 | output contract | JSON Schema + validator | 必填分区/TODO/引用检查 |
| D-005 | mode registry | service/config | active/deprecated/version lookup |
| D-006 | input resolver | service | reviewed-only、as-of、snapshot hash |
| D-007 | prompt renderer | service | deterministic prompt hash |
| D-008 | model adapter interface | adapters | provider-independent + timeout |
| D-009 | run transaction | service | failure 不留正式半写入 |
| D-010 | 9 mode definitions | system/modes | 每个有问题、输出和禁区 |
| D-011 | mode compare | service | 事实/假设/结论差异 |
| D-012 | Red Team enforcement | validator | 缺反证/替代解释拒绝 |
| D-013 | discovery sandbox | service | 只能生成 hypothesis proposal |
| D-014 | CLI | modes list/run/compare/show | dry-run/apply |
| D-015 | Dashboard | analysis workspace | 输入、版本、差异、引用 |
| D-016 | promote insight workflow | proposal service | 不直接改 Thesis |
| D-017 | evaluator | deterministic + human rubric | citation/section/completeness |
| D-018 | mode metrics | metrics | edit、agreement、evidence omission |
| D-019 | 10-case field gate | review packet | 多模式真实比较 |
| D-020 | acceptance/recovery | docs/tests | replay/hash/rebuild 通过 |

## 8. 建议目录

```text
00_System/Analysis_Modes/
├── Registry.md
├── value_chain/v1.yaml
├── supply_demand/v1.yaml
├── technology_curve/v1.yaml
├── company_fundamental/v1.yaml
├── competitive_dynamics/v1.yaml
├── expectations_valuation/v1.yaml
├── scenario/v1.yaml
├── red_team/v1.yaml
└── open_discovery/v1.yaml

05_Research/Analysis_Runs/YYYY/MM/
05_Research/Analysis_Proposals/
```

Prompt 和 output Schema 路径应随 package 版本或 Git commit 固定。

## 9. 建议 CLI

```text
research-os modes list|show|check
research-os analyze run --mode <MODE-ID> --scope <ID,...> --as-of <date>
research-os analyze run ... --apply
research-os analyze compare --runs <ANL-ID,...>
research-os analyze replay ANL-ID --current-model
research-os analyze propose-thesis --run ANL-ID
```

`replay` 必须创建新 Run，不能覆盖旧输出。

## 10. 测试

- Mode version immutability；
- deprecated mode 不可用于新 authoritative run；
- reviewed-only input；
- as-of 不泄漏未来 Evidence；
- prompt/input/output hash；
- malformed model output；
- missing contradicting Evidence；
- TODO/placeholder；
- timeout/provider failure；
- retry 不创建重复 Run；
- replay 创建新 ID；
- open discovery 不能提升 reviewed Thesis；
- compare 正确区分事实、假设、结论和时间；
- HTML escaping 和大输出限制。

## 11. 真实 10-case Gate

选择：

- 3 个 Sector 事件；
- 3 个 Company 事件；
- 2 个 Technology 事件；
- 2 个 mixed/contradicting 事件。

每个 case 至少运行 Value Chain、Company/Supply/Technology 适配模式、Scenario 和 Red
Team；其中 5 个运行 Open Discovery。

人工评分：

- 引用准确；
- 没有 Source 外事实；
- 模式问题覆盖；
- 反证完整；
- 假设显式；
- 分歧可解释；
- 输出是否节省研究时间；
- 是否诱发过度结论。

建议 Gate：

- citation/attribution 100% 可解析；
- Source 外关键事实 0；
- 必填问题覆盖 ≥90%；
- 关键反证遗漏率 <10%；
- 人工认为“有增量价值”的 Run ≥70%；
- Open Discovery 候选中至少一半可明确判定为 investigate 或 reject，而非模糊描述；
- 不使用多数投票产生权威结论。

## 12. 回滚

- Mode 定义采用 append-only version；
- 模式可 deprecated，不删除旧文件；
- Run 不反向修改 Evidence；
- 模型供应商不可用时保留确定性输入 manifest 和 failed Job；
- 若模式 Gate 不通过，停止该模式为 active，不影响其他模式；
- 综合器可关闭，保留单模式草稿和人工比较；
- 任何错误输出使用 rejected/superseded，不覆盖历史。

