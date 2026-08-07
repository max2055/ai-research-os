# Rule Change Proposal RCP-v03-006

Proposal ID：RCP-v03-006

状态：approved（2026-08-07，reviewer：max）

创建日期：2026-08-07

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Schema、永久 ID、Agent 边界：

- Phase 3（`04_Phase_3_Impact_Engine.md`）Impact Assertion 语义与传播边界
- 新增 `impact_assertion` 正式对象类型（`IMP-YYYYMMDD-NNN`），把 RCP-v03-003
  已预注册的 ID 占位（`Metadata_Schema_v0.3_Proposal.md`）落为正式对象
- 新增 predicate→impact 规则映射（Phase 3 C-003）为**领域审核策略**，不由 Agent
  自动推出
- Agent 边界：仅 reviewed Event 可生成权威 Impact；pending Event 只进
  sandbox/experimental；Agent 只生成 proposal，不得自动权威化

## Observed problem

只记录可引用的失败、warning、返工或研究质量问题：

- **现有 Ontology 只表达静态关系**（`REL-*`：SUPPLIES / CUSTOMER_OF /
  COMPETES_WITH / SUBSTITUTES / COMPLEMENTS / DEPENDS_ON / ENABLES /
  CONSTRAINS / OWNS / PARTNERS_WITH / PRODUCES / USES），无法表达"事件通过
  明确机制影响哪些实体和变量"（方向、强度、时间、滞后、置信度）。
- **`RELATED_TO` ≠ impact**：图距离不自动等于因果；供应关系不自动意味着对
  收入重要；方向和强度不能从图距离推出。若直接开发 impact 生成而不先定边界，
  会制造"相关性被当作因果"的权威输出，违反 v0.3"证据先于判断"继承原则。
- 无 Impact Assertion 对象：Phase 3 的 20-event 人工影响路径 Gate 无法承载，
  事件跨板块传导、反面路径保留、未知项处理都无落脚点。

## Evidence

- Review：`04_Phase_3_Impact_Engine.md` §1（目标）、§2（10 条核心原则）、
  §3（Impact Assertion schema 草案）、§6（传播约束）、§11（真实 20-event Gate）
- 前置已满足：Phase 1 Universe 完成（54 Core）；Phase 2 已积累 **48 个
  `review_status: reviewed` Event**（`04_Evidence/Events/`），满足 Phase 3
  前置"有真实 reviewed Event"
- ID 预注册：`00_System/Metadata_Schema_v0.3_Proposal.md`（Impact Assertion
  `IMP-YYYYMMDD-NNN`）与 `01_Product_Charter_and_Governance.md` 均已列该
  对象类型占位，本 RCP 落为正式
- 现有 predicate 清单：12 个（见上，`02_Phase_0_1_Ontology_and_Universe.md`
  §REL schema）
- Test or validation output：`research-os validate` 0 errors / 0 warnings；
  本 RCP 不创建对象，不影响 validation

## Proposed change

1. **`impact_assertion` 正式对象（`IMP-YYYYMMDD-NNN`）**，按 Phase 3 §3 草案：
   `impact_type: demand|supply|price|cost|revenue|margin|capex|capacity|
   competition|technology|regulation|valuation|other`、
   `direction: positive|negative|mixed|uncertain`、
   `magnitude: immaterial|low|medium|high|unknown`、
   `horizon: immediate|quarter|year|multi_year|unknown`、
   `lag_start`/`lag_end`、`mechanism`、`conditions`、`countervailing_factors`、
   `alternative_explanations`、`evidence_ids`、`confidence`、`review_status`。
   接入 OBJECT_PATTERNS、ID_PATTERNS、schema registry、validation、
   REVIEWABLE_TYPES（同 CHN- / SEG- 先例）。
2. **`RELATED_TO` ≠ impact**：Impact Assertion 独立于 Ontology assertion
   存储；必须有明确 mechanism；direction/magnitude 不从图距离推出；供应关系
   不自动意味着对收入重要（Phase 3 §2.1/2.3/2.4）。
3. **公司经营影响与证券价格影响分离**：Phase 3 默认不生成 Security/valuation
   价格方向；Security 影响须满足 Phase 5 规则（Phase 3 §3 注）。
4. **Agent 边界**：仅 reviewed Event 可生成权威 Impact；pending Event 只进
   sandbox 且输出标记 experimental，不进入 reviewed Report；Agent 生成的
   Impact 一律为 proposal，人工 Review（approve/edit/reject 有 Decision）后
   才转 reviewed；LLM 生成的 mechanism 不得补写 Evidence 中未出现的事实
   （Phase 3 §5/§6）。
5. **多跳传播约束**：默认 max depth 3、fan-out 默认 10、只使用 as-of 时点
   有效的 reviewed Ontology assertion、禁止路径循环、必须记录剪枝原因、
   对同 target 的正负路径不得静默净额合并、路径排名只用于审阅优先级
   （Phase 3 §6）；多跳路径默认 proposal，逐跳审核后才可进入 Report
   （Phase 3 §2.8）。
6. **confidence policy**：路径整体置信度 = 最弱关键一跳（weakest-link），
   不能简单将每跳分数相乘后冒充精确概率；模型 confidence 不等于客观概率
   （Phase 3 §2.9/§4）。

## Impact and risks

- 新增 `IMP-*` 正式对象类型：需 OBJECT_PATTERNS、ID_PATTERNS、schema
  registry、validation、index、review 接入（同 Sector/Security 先例）。
- 新增 predicate→impact 规则映射（C-003）：映射方向和限制须领域审核，不得
  自动推出；未知 predicate 不生成 Impact。
- 多跳自动传播有因果幻觉风险：先通过 direct impact Field Gate 再启用 2–3 hop；
  若真实 Gate 不通过，系统退回"人工 direct impact only"，不扩大自动传播
  （Phase 3 §12）。

## 不做的事

- 不自动宣称因果关系。
- 不把相关性/图距离当作因果或强度证据。
- 不对同 target 正负路径静默净额合并。
- 不在 Phase 5 规则前生成证券价格方向。
- 不用模型 confidence 冒充客观概率。
- 不把 pending Event 用于权威 Report。
- 不把多跳路径自动权威化。
- 不为追求覆盖而对未知项强制赋方向或强度。

## Review points（reviewer：max，2026-08-07，全部采纳默认）

1. ✅ `IMP-YYYYMMDD-NNN` 落为正式对象类型；字段按 Phase 3 §3（impact_type 枚举、
   direction/magnitude/horizon 含 `unknown`）
2. ✅ `RELATED_TO` ≠ impact 语义；未知项不得被强制赋方向或强度
3. ✅ 公司经营影响与证券价格影响分离；Phase 3 默认不生成 Security/valuation 价格方向
4. ✅ Agent 边界：仅 reviewed Event 生成权威 Impact；pending → experimental；
   LLM mechanism 不得补写 Evidence 外事实
5. ✅ 多跳传播约束：depth 3 / fan-out 10 / as-of 有效关系 / 正负不静默合并 /
   路径默认 pending
6. ✅ confidence policy：weakest-link；模型 confidence ≠ 客观概率

- Decision：批准（accept RCP-v03-006 as drafted，6 项人审点全部采纳默认）
- Reviewer：max
- Date：2026-08-07
- Reason：与 Phase 3 §2/§3/§5/§6/§11 草案一致；落实 Roadmap §9 决策点
  "Impact 关系类型与强度语义"；"仅 reviewed Event + 逐跳人审"防因果幻觉。

## Implementation record

- Changed files：本文件（proposed → approved）；生效后由 WP-300（C-001～003）起落地
  Impact Schema（C-002）+ predicate→impact 规则映射（C-003）+ direct impact
  proposal（C-004）
- Test result：not run（本 RCP 为治理边界批准，无代码变更；测试在 WP-300 落地后运行）
- Validation result：`research-os validate` 0 errors / 0 warnings（批准前后一致，
  因无对象变更）
- Effective date：2026-08-07（批准即生效；WP-300 起实施）

## 参考

- `04_Phase_3_Impact_Engine.md` §2/§3/§5/§6/§11
- `00_Master_Roadmap.md` §9（Impact 关系类型与强度语义 决策点）
- `00_System/Metadata_Schema_v0.3_Proposal.md`（`IMP-` 预注册）
- RCP-v03-003（正式对象/永久 ID 体系）
