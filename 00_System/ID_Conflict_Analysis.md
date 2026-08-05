# 永久 ID 冲突检查（A-006）

状态：`analysis / feeds RCP-v03-003`
创建日期：2026-08-05
工作包：WP-101 / A-006（只读分析，不改代码）
依赖：`Metadata_Schema.md`（v0.2）、`Metadata_Schema_v0.3_Proposal.md`（A-005）、`02_Phase_0_1_Ontology_and_Universe.md` §7

## 1. 既有 v0.2 前缀（实际研究对象 id: 行，排除 migrations/backups 与 07_Templates）

| 前缀 | 用次 | 示例 | 含义 |
|---|---:|---|---|
| SRC | 40 | SRC-20260730-034 | Source |
| EVT | 32 | EVT-20260729-015 | Event |
| REV | 66 | REV-20260730-020 | Review Decision |
| ACT | 14 | ACT-20260729-001 | Action |
| COM | 10 | COM-oracle | Company（含 2 个 PRJ-001/PRJ-002 重复在 sub-index） |
| THS | 9 | THS-007 | Thesis |
| PRJ | 4 | PRJ-001, PRJ-002 | Project |
| RPT | 3 | RPT-20260730-ai-coding-agent-value-chain-v0-1 | Report |
| JOB | 2 | JOB-YYYYMMDDhhmmss-NNN | Job Run |

> v0.2 实际对象噪音：grep 命中 `type:`、`title:` 等误匹配已在脚本过滤，不计。

## 2. v0.3 新增前缀提案

`SEG / TEC / PRD / INS / MET / CHN / REL / IMP / MOD-ANL / ANL / FCT / RES / VAL / REC`

## 3. 扫描方法

用脚本扫所有 `id: <value>` 行（排除 `migrations/backups`、`07_Templates`），
按前缀切分。报告出现位置。

## 4. 结果：v0.2 实际对象无任何新前缀

合并扫描中 5 个 `SEG-<slug>` / `INS-<market>-<ticker>` / `MOD-ANL-...` 等命中，
**全部出现在 v0.3 规划/Schema 草案的示例行**（`02_Phase_0_1_...md`、`01_Product_Charter`、
`05_Phase_4_...md`），即字面 placeholder，**不是 v0.2 research object 的 id:**。

**结论**：新前缀与 v0.2 实际对象前缀**零冲突**。v0.2 现存只有
SRC/EVT/REV/ACT/COM/THS/PRJ/RPT/JOB，新前缀集（SEG/TEC/PRD/INS/MET/CHN/REL/IMP/MOD-ANL/ANL/FCT/RES/VAL/REC）与之完全不相交。

## 5. 重点歧义点（WP-102 parser 落地须处理）

| # | 前缀 | 风险 | 处理方案（落地 WP-102） |
|---|---|---|---|
| D1 | `MOD-ANL-` | 双段前缀，与单段 `MOD-`（如未来引入 Model 对象前缀）易混 | parser 锚定 `^MOD-ANL-`；Analysis Mode 不复用单段 `MOD-`；现阶段 v0.2 无 `MOD-` 对象 |
| D2 | `INS-<market>-<ticker>` | 连字符歧义：market 与 ticker 都可能带 `-` | market 定长 `[A-Z]{2,6}`（如 NASDAQ=6），剩余为 ticker；ticker 内允许连字符；parser 用 `^INS-[A-Z]{2,6}-[A-Z0-9.\-]+$` 切分（A-005 §5） |
| D3 | `MET-` (Metric) vs "metric" 语义 | 命名直观但前缀短 | v0.2 无 `MET-` 对象（本扫描确认），`MET-` 唯一表 Metric Definition；validator 用 `^MET-[a-z0-9]+(?:-[a-z0-9]+)*$` |
| D4 | `ANL-` (Analysis Run) vs `MOD-ANL-` (Analysis Mode) | 易读混 | ID parser 用前缀严格匹配；文档显式区分 Run（日期型 `ANL-YYYYMMDD-NNN`）与 Mode（`MOD-ANL-<slug>-vN`）；两者 type 不同 |
| D5 | `REL-` (Ontology Assertion) vs v0.2 `REV-` (Review) | 字母近但前缀不同 | 无冲突；parser 按前缀分派 |
| D6 | 日期型 ID `YYYYMMDD-NNN` 与 frontmatter 日期字段 | ID 内含日期易误匹配 | ID parser 只从 `id:` 行读整数；不全文匹配 |
| D7 | `RPT-<slug>` 现用 slug-连字符格式 vs `REC-/RES-/FCT-` 日期型 | RPT 用 slug，新实体用日期 | 不冲突；各前缀 parser 各自定义；slug 格式 vs 日期格式由前缀决定 |

## 6. 待定：REST API 与冲突防护（WP-102/103）

- 不允许新建 ID 与现存对象（同前缀+同 slug）二次分配。
- ID 删除退役用 `retired_at` / `superseded_by`，不覆盖、不重用。
- ID 不能内含连字符以外的特殊字符；slug 仅 `[a-z0-9-]`。

## 7. Recommendation（喂 RCP-v03-003）

1. 全部 14 个新前缀可保留，无冲突。
2. parser 实现须处理 D1–D7 七个歧义点（见上）。
3. `MOD-ANL-` 双段前缀与 `ANL-` 单段的 parser 分派测试须在 WP-102 纳入单测。
4. `INS-<market>-<ticker>` 的 `market` 定长约束写入 RCP-v03-003。
5. 不需改任何 v0.3 现有新前缀提议。

## 8. 不做的事

- 不改代码、不改 registry.py（属 WP-102）。
- 不创建任何实体。
- 不注册前缀（RCP-v03-003 批准后由 WP-102 落地）。