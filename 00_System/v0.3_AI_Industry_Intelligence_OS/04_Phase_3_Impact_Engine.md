# Phase 3：Impact Assertion 与跨板块影响引擎

状态：`proposed`  
建议周期：4–6 周  
前置：Phase 1 Universe；Phase 2 有真实 reviewed Event；RCP-v03-006 获批  

## 1. 阶段目标

将当前“对象有关系”升级为“事件通过明确机制影响哪些实体和变量”：

- 区分 Ontology 关系和事件影响；
- 表达方向、强度、时间、滞后、置信度和适用范围；
- 支持一跳直接影响和最多三跳的候选传导路径；
- 每一跳可回到 reviewed Event/Source；
- 显式保留反向影响、冲突、替代机制和未知事项；
- 通过真实事件人工评估 Impact precision。

## 2. 核心原则

1. `RELATED_TO` 不等于影响。
2. 影响路径中的每一跳必须有作用机制。
3. 方向和强度不能从图距离自动推出。
4. 供应关系不自动意味着对收入重要。
5. Event 影响可以是 positive、negative、mixed、uncertain。
6. 公司经营影响与证券价格影响分开。
7. 长期结构性影响与短期市场反应分开。
8. 多跳路径默认是 proposal，只有逐跳审核后才可进入 Report。
9. 不把模型 confidence 当作客观概率。
10. 冲突 Impact Assertion 同时保留。

## 3. Impact Assertion Schema 草案

```yaml
id: IMP-YYYYMMDD-NNN
type: impact_assertion
trigger_event_ids: []
subject_id:
impact_type: demand|supply|price|cost|revenue|margin|capex|capacity|
  competition|technology|regulation|valuation|other
target_id:
direction: positive|negative|mixed|uncertain
magnitude: immaterial|low|medium|high|unknown
horizon: immediate|quarter|year|multi_year|unknown
lag_start:
lag_end:
mechanism:
conditions: []
countervailing_factors: []
alternative_explanations: []
evidence_ids: []
confidence:
valid_from:
valid_to:
review_date:
generation_method:
review_status: pending
```

`subject_id` 通常是 Event 或首先受影响实体，`target_id` 可以是 Sector、Company、
Product、Technology、Metric 或 Security。Security/valuation 影响必须额外满足 Phase 5
规则，Phase 3 默认不生成价格方向。

## 4. 传导路径模型

```text
Path ID
Trigger Event
Step 1: target + mechanism + direction + horizon
Step 2: target + mechanism + direction + horizon
Step 3: target + mechanism + direction + horizon
Conditions
Countervailing paths
Terminal company/metric impact
Confidence by step
Overall weakest-link confidence
```

整体置信度不能高于最弱关键一跳；不能简单将每跳分数相乘后伪装成精确概率。

### 示例

```text
先进封装扩产延期
→ GPU 模组可交付量受限（supply / quarter / medium）
→ 云厂商 AI 集群上线延后（capacity / quarter-year / medium）
→ 模型训练算力价格下降速度放缓（cost / quarter-year / low）
```

需要同时保留替代路径，如其他封装产能、库存、设计优化或需求下降。

## 5. Impact 生成流程

```text
Reviewed Event
→ identify direct affected entities/metrics
→ retrieve reviewed Ontology assertions
→ propose first-hop assertions
→ retrieve eligible next-hop relations
→ bounded path proposal
→ dedup and contradiction check
→ pending Impact Assertions
→ human review
→ reviewed impact graph
→ Report/Analysis Mode input
```

只有 reviewed Event 可以生成供权威使用的 Impact；pending Event 可以用于 sandbox，
但输出必须标记 experimental 且不得进入 reviewed Report。

## 6. 传播约束

- 默认最大深度 3；
- 每跳最大 fan-out 可配置，默认 10；
- 只使用 as-of 时点有效的 reviewed Ontology Assertion；
- 禁止在同一路径循环回到已访问节点；
- 必须记录剪枝原因；
- 关系 predicate 到允许 impact type 的映射必须由规则表定义；
- 任何 LLM 生成的机制不能补写未在 Evidence 中出现的事实；
- 对同 target 的正负路径不得静默净额合并；
- 路径排名只用于审阅优先级，不是投资评分。

## 7. 工作包

| ID | 任务 | 交付 | 验收 |
|---|---|---|---|
| C-001 | Impact 语义 RCP | RCP-v03-006 | predicate/impact/magnitude/horizon 获批 |
| C-002 | Impact Schema | schemas | round-trip + validation |
| C-003 | relation→impact rule map | domain policy | 每个 map 有方向和限制 |
| C-004 | direct impact proposal | service | reviewed Event→pending IMP |
| C-005 | mechanism validator | validation | 空泛机制/TODO 被拒绝 |
| C-006 | path expansion | impact service | max depth/fan-out/cycle control |
| C-007 | temporal filter | service | as-of/valid_from/valid_to 正确 |
| C-008 | contradiction detector | service | 正负/不同 horizon 并存可见 |
| C-009 | path dedup | service | 同机制同路径不重复 |
| C-010 | confidence policy | domain | weakest-link/unknown 规则明确 |
| C-011 | impact spec contract | template + JSON Schema | 模型与确定性 renderer 分离 |
| C-012 | impact review workflow | review service | approve/edit/reject 有 Decision |
| C-013 | impact index/export | indexing/ontology | 按 Event/Entity/Sector/Horizon 查询 |
| C-014 | CLI | propose/list/path/review | dry-run/apply |
| C-015 | Impact Dashboard | UI | 图、表、机制、反向路径、Evidence |
| C-016 | report integration | workflow | 只用 reviewed IMP；反面路径必保留 |
| C-017 | impact metrics | metrics | precision/edit/conflict/path depth |
| C-018 | 20-event field gate | review packet | 真实跨板块事件人工评估 |
| C-019 | performance benchmark | benchmark | 50k edges、3-hop 在目标内 |
| C-020 | acceptance/recovery | docs/tests | export/rebuild/rollback 通过 |

## 8. 建议 CLI/API

```text
research-os impact propose --event EVT-ID [--depth 1] [--apply]
research-os impact list --target COM-ID --as-of YYYY-MM-DD
research-os impact path --from EVT-ID --to COM-ID --depth 3
research-os impact conflicts --target COM-ID
research-os impact review --targets IMP-ID ...
research-os impact explain IMP-ID
```

API read model：

- `/api/impact/events/{id}`
- `/api/impact/entities/{id}`
- `/api/impact/paths?from=&to=&as_of=`
- `/api/impact/conflicts?target=`

Web 继续只读，review 由 CLI/Markdown 流程完成，除非未来单独批准 Web mutation。

## 9. UI 要求

Impact 页面至少显示：

- trigger Event 和日期；
- 每一跳 subject/predicate/target；
- mechanism 原文；
- direction、magnitude、horizon；
- confidence 与 review status；
- Evidence/Source 链接；
- conditions 和 countervailing factors；
- contradicting paths；
- stale/expired 标记；
- 图与可访问表格两种表示。

不得只显示节点连线而隐藏机制。

## 10. 测试要求

- Schema 枚举、日期、confidence、引用；
- pending Event 不进入 authoritative flow；
- invalid/stale relation 不用于 as-of path；
- cycle、fan-out 和 max-depth；
- 正负路径冲突；
- mixed/unknown 传播；
- weakest-link confidence；
- duplicate path；
- rollback；
- reviewed Report 拒绝 pending Impact；
- contradicting path omission validation；
- 50k edge synthetic benchmark；
- Dashboard HTML escape 和不存在对象。

## 11. 真实 20-event Gate

样本至少包含：

- 5 个 supply/capacity Event；
- 3 个 pricing Event；
- 3 个 product/technology Event；
- 3 个 customer/demand Event；
- 2 个 financial/capex Event；
- 2 个 competition Event；
- 2 个 regulation/other Event；
- 至少 5 个直接反面或 mixed 路径。

人工逐条记录：

- direct target precision；
- mechanism 是否由 Evidence 支持；
- direction 是否合理；
- horizon 是否合理；
- magnitude 是否过度；
- 关键反向路径是否遗漏；
- 1/2/3 hop 的保留率和编辑率。

建议 Gate：

- 直接影响 precision ≥85%；
- 机制无来源外事实 ≥95%；
- 二跳路径人工保留率 ≥60%；
- 三跳只作为探索，不设置高权威阈值；
- 所有重大反面路径遗漏必须修复后通过；
- 未知项不得被强制赋方向或强度。

## 12. 回滚

- Impact Assertion 是新增对象，不反向修改 Event/Company；
- 可禁用 path expansion，只保留 reviewed direct assertion；
- 派生图可删除重建；
- 算法版本升级保留旧 Analysis/Impact run fingerprint；
- 误生成对象使用 reject/supersede，不物理删除；
- 若真实 Gate 不通过，系统退回“人工 direct impact only”，不扩大自动传播。

