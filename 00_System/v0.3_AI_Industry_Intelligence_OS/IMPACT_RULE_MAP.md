# Impact 规则映射（C-003）：predicate → impact_type allowlist

状态：`approved`（2026-08-07，reviewer：max）

依据：RCP-v03-006（2026-08-07 approved）；`04_Phase_3_Impact_Engine.md` §2/§6

## 复核记录

- Decision：批准（2026-08-07，max 逐 predicate 复核方向/限制，全部采纳默认；allowlist
  语义、机制必填、valuation 门禁沿用 RCP-v03-006 已批准边界，未改动）
- 生效：批准即生效；C-004 direct impact proposal 可引用本表
- Revisit trigger：任一 predicate 的机制映射遇实施困难，或 20-event Field Gate 暴露
  方向判断偏差时，提修订并记录

## 用途与语义

这张表是**允许清单（allowlist）**，不是算法推导。它定义：从 Ontology 关系
predicate（`REL-*` 的 12 个值）可以产生哪些 `impact_type`（13 个值）。

1. **未列出的 predicate × impact_type 组合不生成 Impact**（RCP-v03-006："未知
   predicate 不生成 Impact"）。
2. **每个允许项都必须有显式 mechanism**（Phase 3 §2.2：影响路径每一跳必须有
   作用机制）；`mechanism` 为空或纯 TODO 被 schema/validator 拒绝。
3. **方向/强度不从图距离自动推出**（§2.3）。表中"默认方向"只是领域默认倾向，
   实际方向必须由 mechanism 与 Evidence 支撑，不得由本表单独决定。
4. **供应关系不自动意味着对收入重要**（§2.4）——因此 `SUPPLIES → revenue` 未列出。
5. **valuation / Security 价格方向**：Phase 3 默认不生成（RCP-v03-006 review
   point 3）。表中 `valuation` 全部标为 C（conditional），且仅限非价格方向或
   由 Phase 5 规则承载。
6. **经营影响与证券价格影响分离**（§2.6）：本表只覆盖经营/基本面影响；价格方向
   不在 Phase 3 范围。
7. 本表是**人工审核的领域策略**，Agent 不得自行增删条目；修改需 max 复核并记录。

## 逐 predicate 详情

每个 predicate 小节列出**允许**的 impact_type（allowlist）。未列出的 13 值中的
其余组合均为 ✗（不生成）。符号：`✓` 允许（机制显式即可）、`C` 条件允许
（需额外条件）、`✗` 不允许。

### SUPPLIES（A 供应 B）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| supply | mixed（供给扩张→正；中断→负）| 需 mechanism 指明供给变化 |
| capacity | positive | 仅当机制涉及产能增减（扩产/停产/爬坡）|
| cost | mixed（供给充足→B 成本下行=正）| 需 mechanism 链接到 B 的成本结构 |
| price | mixed | 需 mechanism 显式（供需失衡→价格）|
| capex | C | 仅当机制明确 A 的资本开支计划（扩产投资）|
| revenue | ✗ | §2.4：供应关系不自动意味着对收入重要 |

### CUSTOMER_OF（A 是 B 的客户）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| demand | positive | 需 mechanism 指明 A 的需求变化 |
| revenue | positive | 需 mechanism 链接到 B 的收入（客户规模/集中度/采购量）|
| capex | C | 仅当机制明确 A 的下单/资本开支信号 |
| margin | ✗ | 需显式 pricing，不自动派生 |
| price | ✗ | 客户议价需 mechanism 显式 |

### COMPETES_WITH（A 与 B 竞争）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| competition | mixed | 需 mechanism（价格战/份额/进入退出）|
| price | negative | 需 mechanism（竞争压价）|
| margin | negative | 需 mechanism（竞争侵蚀毛利）|
| revenue | negative | 需 mechanism（份额流失）|
| demand | ✗ | 竞争不改整体需求，只改分配 |
| capex | ✗ | 无直接机制 |

### SUBSTITUTES（A 替代 B）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| competition | mixed | 需 mechanism |
| demand | negative（对 B）| 需 mechanism（替代侵蚀 B 的需求）|
| revenue | negative（对 B）| 需 mechanism |
| price | negative（对 B）| 需 mechanism |

### COMPLEMENTS（A 互补 B）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| demand | positive | 需 mechanism（互补品扩散带动）|
| revenue | positive | 需 mechanism |
| technology | positive | 需 mechanism（互补生态）|

### DEPENDS_ON（A 依赖 B）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| supply | mixed | 需 mechanism（对上游供给的暴露）|
| cost | negative | 需 mechanism（依赖 → 成本暴露）|
| technology | C | 仅当依赖本质是技术依赖 |
| capacity | ✗ | 需 mechanism 显式 |

### ENABLES（A 使能 B）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| technology | positive | 需 mechanism（技术使能）|
| capacity | positive | 需 mechanism（解锁产能）|
| demand | positive | 需 mechanism（使能新需求）|
| revenue | C | 需 mechanism 显式（使能→商业变现）|

### CONSTRAINS（A 约束 B）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| capacity | negative | 需 mechanism（约束产能）|
| supply | negative | 需 mechanism |
| technology | negative | 需 mechanism（技术瓶颈）|
| regulation | C | 仅当约束本质是监管/合规 |
| price | C | 需 mechanism 显式 |

### OWNS（A 拥有 B）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| capex | C | 并购/剥离/内部投资，需 mechanism |
| technology | C | 需 mechanism（内部技术资产）|
| revenue | C | 并表/整合，需 mechanism |
| valuation | C | 仅非价格方向；价格方向留 Phase 5 |
| margin | ✗ | 不自动派生 |

### PARTNERS_WITH（A 与 B 合作）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| technology | positive | 需 mechanism（联合技术）|
| supply | positive | 需 mechanism（联合供给）|
| demand | positive | 需 mechanism（合作拓展市场）|
| revenue | C | 需 mechanism 显式 |

### PRODUCES（A 生产 B 产品）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| capacity | positive | 需 mechanism（产能/良率）|
| supply | positive | 需 mechanism（产出供给）|
| technology | positive | 需 mechanism（产品技术代际）|
| price | mixed | 需 mechanism（产品定价/供需）|
| revenue | positive | 需 mechanism（产品收入）|
| margin | C | 需 mechanism 显式 |

### USES（A 使用 B）

| impact_type | 默认方向 | 限制/条件 |
|---|---|---|
| cost | mixed | 需 mechanism（采用成本）|
| technology | positive | 需 mechanism（技术采用）|
| demand | C | 仅当使用行为推动下游需求，需 mechanism |
| capacity | C | 需 mechanism 显式 |
| revenue | ✗ | 不自动派生 |

## 通用规则

1. **`other` 不默认允许**：仅当无任何其他 impact_type 适用，且 mechanism 明确、
   `conditions` 说明为何无更精确类型时，可标 `other`。C-004 生成器不得把 `other`
   当作兜底逃生口。
2. **同一 predicate × impact_type 的反向方向**：表中"默认方向"只是倾向；若机制
   支撑反向，可用 `mixed`/`uncertain` 或直接记反向，但必须在 mechanism 中显式。
3. **正负路径并存**：对同 target 的正向与负向 Impact 不得静默净额合并
   （§6），两条都保留为独立 Assertion（§2.10）。
4. **传播 vs 直接**：本表对直接（1-hop）与传播（2–3 hop）统一适用。传播路径的
   每一跳都必须能落到本表某一行 + 显式 mechanism；落不到的跳直接剪枝并记录
   剪枝原因（§6）。
5. **as-of 有效性**：路径只使用 as-of 时点有效的 reviewed Ontology Assertion
   （§6）；`valid_to` 已关闭或被 superseded 的关系不参与。
6. **本表变更流程**：任何增删条目 = 领域策略修改，需 max 复核；按
   `09_Master_Backlog.md` §11，若涉及已批准 RCP 边界则需新 RCP/修订记录。

## 参考

- RCP-v03-006（Impact Assertion 语义与传播边界，2026-08-07 approved）
- `04_Phase_3_Impact_Engine.md` §2（核心原则）、§6（传播约束）、§11（20-event Gate）
- `02_Phase_0_1_Ontology_and_Universe.md` §REL（12 个 predicate 定义）
- `src/research_os/schemas/impact_assertion.py`（13 个 impact_type 枚举）
