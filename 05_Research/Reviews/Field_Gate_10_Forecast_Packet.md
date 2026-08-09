# Field Gate: 10 Forecasts（E-020，WP-520）

**日期**: 2026-08-09  **评审人**: max（待人工审核后勾选）
**规则**: RCP-v03-008 Phase 5 §13 — 至少 4 binary、3 categorical、3 numeric_range；
覆盖 supply、technology、company operating、adoption、financial；
全部人工检查 outcome definition 和 resolution source；不要求为赶 Gate 选择容易预测的问题。

## 分布

- Binary: 4/4 · Categorical: 3/3 · Numeric range: 3/3
- 主题覆盖: financial（NVIDIA 收入/DRAM ASP/capex/Azure）、technology（TSMC N2/先进节点/HBM4）、
  adoption（HBM4 量产/HBM 世代）、company operating（超大规模 capex 榜首）、supply（TSMC 节点）、
  regulation（BIS，附加）。

## 判定表

| ID | Type | 参数 | 标题 | Resolution date | 判定 |
|---|---|---|---|---|---|
| FCT-20260809-001 | binary | 0.6 | NVIDIA FY2027 数据中心收入同比增长 ≥40% | 2027-06-30 | ⬜ |
| FCT-20260809-002 | binary | 0.4 | TSMC N2(2nm)占 2026 Q4 收入 >10% | 2027-01-31 | ⬜ |
| FCT-20260809-003 | binary | 0.7 | SK hynix 2026 Q4 前 HBM4 量产出货 | 2027-01-31 | ⬜ |
| FCT-20260809-004 | binary | 0.5 | BIS 2026 年内将出口许可要求扩展至新国家组 | 2027-01-15 | ⬜ |
| FCT-20260809-005 | categorical | — | FY2027 Micron DRAM 平均售价方向 | 2027-10-31 | ⬜ |
| FCT-20260809-006 | categorical | — | 2026 年超大规模厂商资本开支榜首 | 2027-02-28 | ⬜ |
| FCT-20260809-007 | categorical | — | 2026 年底 NVIDIA 旗舰 GPU 主用 HBM 世代 | 2027-04-30 | ⬜ |
| FCT-20260809-008 | numeric_range | [150.0,200.0] billion USD | Amazon 2026 全年现金资本开支区间 | 2027-02-28 | ⬜ |
| FCT-20260809-009 | numeric_range | [20.0,35.0] % y/y | Microsoft FY2027 Q1 Azure 收入增速区间 | 2026-10-31 | ⬜ |
| FCT-20260809-010 | numeric_range | [60.0,70.0] % of revenue | TSMC 2026 Q4 先进节点收入占比区间 | 2027-01-31 | ⬜ |

## 逐项明细（outcome definition + resolution source 核验）


### FCT-20260809-001 — NVIDIA FY2027 数据中心收入同比增长 ≥40%

- **question**: NVIDIA FY2027 数据中心收入是否同比增长 ≥40%？
- **outcome_definition**: NVIDIA FY2027 Form 10-K 报告 Data Center 分部收入较 FY2026 增长 ≥40%。
- **probability**: 0.6
- **horizon**: year
- **resolution_date**: 2027-06-30
- **resolution_source_requirements**: NVIDIA FY2027 10-K
- **evidence_ids**: EVT-20260520-038, EVT-20260302-041
- **assumptions**: AI 资本开支维持扩张, HBM/先进封装供给不成为硬约束
- **alternative_outcomes**: 增长 20-40%, 增长 <20%
- **falsification_conditions**: NVIDIA FY2027 数据中心收入同比增速 <40%

---

### FCT-20260809-002 — TSMC N2(2nm)占 2026 Q4 收入 >10%

- **question**: TSMC 是否在 2026 Q4 财报披露 N2(2nm)贡献季度收入 >10%？
- **outcome_definition**: TSMC 2026 Q4 财报披露 N2(2nm)占季度收入比重 >10%。
- **probability**: 0.4
- **horizon**: quarter
- **resolution_date**: 2027-01-31
- **resolution_source_requirements**: TSMC 2026 Q4 财报
- **evidence_ids**: EVT-20260416-033, EVT-20260716-037
- **assumptions**: N2 良率爬坡按计划, AI 客户 N2 需求如期放量
- **alternative_outcomes**: N2 占比 5-10%, N2 占比 <5%
- **falsification_conditions**: TSMC 披露 N2 收入占比 ≤10%

---

### FCT-20260809-003 — SK hynix 2026 Q4 前 HBM4 量产出货

- **question**: SK hynix 是否在 2026 Q4 前实现 HBM4 量产出货？
- **outcome_definition**: SK hynix 2026 Q4 财报或官方披露确认 HBM4 已量产/出货。
- **probability**: 0.7
- **horizon**: quarter
- **resolution_date**: 2027-01-31
- **resolution_source_requirements**: SK hynix 2026 Q4 财报, 官方新闻稿
- **evidence_ids**: EVT-20260728-036, EVT-20260725-035, EVT-20260316-042
- **assumptions**: NVIDIA Vera Rubin 平台按计划, HBM4 良率达到量产阈值
- **alternative_outcomes**: HBM4 送样但未量产, HBM4 推迟到 2027
- **falsification_conditions**: 2026 Q4 前 SK hynix 未确认 HBM4 量产

---

### FCT-20260809-004 — BIS 2026 年内将出口许可要求扩展至新国家组

- **question**: BIS 是否在 2026-12-31 前将先进计算出口许可要求扩展到新的国家组？
- **outcome_definition**: BIS 在 Federal Register 发布规则,将先进 AI 芯片出口许可要求扩展至当前未受限的国家组。
- **probability**: 0.5
- **horizon**: year
- **resolution_date**: 2027-01-15
- **resolution_source_requirements**: BIS Federal Register 规则
- **evidence_ids**: EVT-20260531-049, EVT-20260407-050
- **assumptions**: 出口管制政策延续当前收紧方向
- **alternative_outcomes**: 仅调整现有国家组清单, 无新规则
- **falsification_conditions**: 2026 年内 BIS 未将许可要求扩展至新国家组

---

### FCT-20260809-005 — FY2027 Micron DRAM 平均售价方向

- **question**: FY2027 年 Micron 的 DRAM 平均售价(ASP)年度方向是上涨、持平还是下跌？
- **outcome_definition**: 类别={up, flat, down}:Micron FY2027 10-K 披露 DRAM ASP 同比变化 up(>0)、flat(≈0)或 down(<0)。
- **horizon**: year
- **resolution_date**: 2027-10-31
- **resolution_source_requirements**: Micron FY2027 10-K, TrendForce 价格报告
- **evidence_ids**: EVT-20251003-001, EVT-20260601-044
- **assumptions**: AI 内存需求持续, HBM 挤占通用 DRAM 产能
- **alternative_outcomes**: 方向取决于供需缺口
- **falsification_conditions**: 需第三方(如 TrendForce)与 Micron 披露交叉确认方向

---

### FCT-20260809-006 — 2026 年超大规模厂商资本开支榜首

- **question**: 2026 全年现金资本开支最高的是哪家超大规模厂商？
- **outcome_definition**: 类别={Microsoft, Amazon, Meta, Google}:按 FY2026 年报披露的全年现金资本开支排序取榜首。
- **horizon**: year
- **resolution_date**: 2027-02-28
- **resolution_source_requirements**: 各家 FY2026 年报 10-K
- **evidence_ids**: EVT-20260430-001, EVT-20260429-039, EVT-20260731-040
- **assumptions**: AI 基础设施投资继续为主要开支方向
- **alternative_outcomes**: 榜首可能为 Microsoft 或 Amazon 之一
- **falsification_conditions**: 以各家 FY2026 10-K 现金资本开支数字为准, 不以后续修订为准

---

### FCT-20260809-007 — 2026 年底 NVIDIA 旗舰 GPU 主用 HBM 世代

- **question**: 2026 年底 NVIDIA 旗舰数据中心 GPU 主用内存是 HBM4 还是 HBM3e？
- **outcome_definition**: 类别={HBM4, HBM3e, both}:以 NVIDIA FY2027 Q1 10-Q 产品披露为准。
- **horizon**: quarter
- **resolution_date**: 2027-04-30
- **resolution_source_requirements**: NVIDIA FY2027 Q1 10-Q, 产品发布资料
- **evidence_ids**: EVT-20260725-035, EVT-20260728-036, EVT-20260316-042
- **assumptions**: Vera Rubin 平台采用 HBM4
- **alternative_outcomes**: 过渡期两代并存
- **falsification_conditions**: 以 NVIDIA 官方产品规格披露为准

---

### FCT-20260809-008 — Amazon 2026 全年现金资本开支区间

- **question**: Amazon 2026 全年现金资本开支落在哪个区间？
- **outcome_definition**: Amazon FY2026 10-K 披露的全年现金资本开支(十亿美元)。
- **range_low**: 150.0
- **range_high**: 200.0
- **unit**: billion USD
- **horizon**: year
- **resolution_date**: 2027-02-28
- **resolution_source_requirements**: Amazon FY2026 10-K
- **evidence_ids**: EVT-20260430-001
- **assumptions**: 2026 单季 capex 维持 $40B+ 水平
- **alternative_outcomes**: Q1 $43.2B 若全年四个季度相当则约 $170B
- **falsification_conditions**: 全年现金资本开支 <$150B 或 >$200B 即证伪

---

### FCT-20260809-009 — Microsoft FY2027 Q1 Azure 收入增速区间

- **question**: Microsoft FY2027 Q1(截至 2026-09-30 季度)Azure 收入同比增速落在哪个区间？
- **outcome_definition**: Microsoft FY2027 Q1 财报披露 Azure 收入同比增速(%)。
- **range_low**: 20.0
- **range_high**: 35.0
- **unit**: % y/y
- **horizon**: quarter
- **resolution_date**: 2026-10-31
- **resolution_source_requirements**: Microsoft FY2027 Q1 财报
- **evidence_ids**: EVT-20260429-039, EVT-20260429-004
- **assumptions**: Azure AI 需求持续但基数增大导致增速回落
- **alternative_outcomes**: 若加速可能超 35%
- **falsification_conditions**: Azure 同比增速 <20% 或 >35% 即证伪

---

### FCT-20260809-010 — TSMC 2026 Q4 先进节点收入占比区间

- **question**: TSMC 2026 Q4 先进节点(3nm/5nm)占收入比重落在哪个区间？
- **outcome_definition**: TSMC 2026 Q4 财报披露先进节点(3nm/5nm)占季度收入比重(%)。
- **range_low**: 60.0
- **range_high**: 70.0
- **unit**: % of revenue
- **horizon**: quarter
- **resolution_date**: 2027-01-31
- **resolution_source_requirements**: TSMC 2026 Q4 财报
- **evidence_ids**: EVT-20260716-037, EVT-20260416-033
- **assumptions**: AI 加速器先进节点需求延续 2Q26 的 63% 水平
- **alternative_outcomes**: 若成熟节点回暖占比可能回落
- **falsification_conditions**: 占比 <60% 或 >70% 即证伪

---


## 解析 Gate 说明

- 首批 Forecast 自然到期后再评价（WP-530）；不得预填未来结果。
- ambiguous/void 必须记录原因；形成第一份 calibration report。
- Phase 工程能力可先 accepted；v0.3 final release 必须包含真实 resolution。
