# Rule Change Proposal RCP-v03-010

Proposal ID：RCP-v03-010

状态：proposed（待 max 批准）

创建日期：2026-08-09

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Schema、永久 ID、Agent 边界：

- Phase 6（`07_Phase_6_Productization_and_Scale.md`）产品组装、Dashboard 写边界、30-day Pilot 与 v0.3 发布 Gate
- Dashboard 是否允许 Web mutation（权威写入走浏览器）的边界
- Product IA v2（`07_Phase_6` §2/§3）页面与查询范围
- 规模化触发条件（PostgreSQL / 图数据库 / 向量索引）与备份、安全、许可 Gate

## Observed problem

- Dashboard 目前已有多个只读页面 + 3 个写端点（`/llm/config`、`/llm/models`、`/llm/test`，均为 LLM 供应商本地配置），尚未引入任何“浏览器直接写权威研究对象”的端点。Phase 6 要把分散能力组装成每日可用的产品，若不事先钉死写边界，实现中容易漂移到“UI 直接改 Source/Event/Review”而绕过 CLI 的 dry-run/`--apply` 与审计链路。
- Phase 6 §9 F-001 的“页面/查询/边界批准”是明确的治理前置，但目前没有承载该批准的 RCP。
- v0.3 发布（F-023~025）需要机器可验证 checklist + 命名 reviewer 的人工 release packet，缺一个统一的批准载体。
- D9（2026-08-05）已把 RCP-v03-010 排定到 Wave 6（统一产品与发布）；Wave 5 工程已收口（WP-530 除外，future-date），Wave 6 需在此 RCP 批准后开工。

## Proposed change

1. **Dashboard 写边界（Web mutation）**：v0.3 默认 Dashboard 保持**只读浏览**（GET-only），所有权威写入（Source/Event/Impact/Thesis/Forecast/Valuation/Recommendation/Review/Index rebuild）继续走 **CLI + Markdown + dry-run/`--apply`**，保留审计与回滚。**Web mutation（浏览器直接提交权威对象）必须另行批准**，v0.3 默认不引入。现有 3 个 `/llm` 写端点（供应商本地配置）是唯一例外：仅写本地 config store，不写权威研究对象，不受此边界影响。
2. **Product IA v2 批准**：接受 Phase 6 §2 信息架构（Industry Home → Daily Brief / Sector Map / Company Radar / Candidate Queue / Evidence Review Queue / Impact Explorer / Analysis Workspace / Forecast & Decision Desk / Operations / System Health）与 §3 页面要求；F-001 据此落地，页面/查询/边界以本 RCP + F-001 spec 为准。
3. **30-day Pilot 范围固定**：按 Phase 6 §10（8–10 Pilot Sector、30–50 Core Company、20–40 enabled Channel、每日 Candidate triage、每周 Evidence/Impact/Forecast review、一次 Monthly coverage/calibration review、3 家 Company Decision Pilot）。**不在 Pilot 中途无审批扩大 Universe**。
4. **v0.3 Release Gate**：Phase 6 §11 的 checklist（Evidence/Universe、Ingestion、Impact/Analysis、Decision、Engineering、Human 六组）为**机器可验证**基线（F-023）；F-024 人工 release packet 含命名 reviewer/日期/approve 决定；**F-025 tag/release 仅在全部 Gate 通过后执行**。
5. **规模化触发条件**：保持当前分层（Markdown 权威 + assets + SQLite operational + Git + 加密离机备份）。PostgreSQL / 图数据库 / 向量索引**仅在 Phase 6 §4 对应触发条件满足且实测瓶颈后评估**，不主动迁移；向量仅用于 Candidate/Source 语义检索与近似去重，不得作为来源权威、事实确认或 Thesis 更新依据。
6. **备份、安全与许可 Gate**：接受 Phase 6 §6–8——P0/P1/P2/P3 告警分级；备份 6 项分别恢复（Git / assets 加密归档 / Candidate snapshot / secrets / launchd / 可重建 index）；恢复演练记录 RTO（<4h）/RPO（≤24h）；secrets 不进 Git/Markdown/log；外部内容视为不可信输入；每个 enabled Channel 的 license/robots 状态进入 F-015 license audit。

## 不做的事

- v0.3 不引入 Dashboard 写权威研究对象（Web mutation 另行批准，默认只读）。
- 不主动迁移 PostgreSQL / 图数据库 / 向量索引（仅按 §4 触发条件）。
- 不把 Candidate 全量保存为正式 Source。
- 不引入 buy/sell/position size 或自动执行（延续 RCP-v03-009 边界）。
- 不在 30-day Pilot 中途无审批扩大 Universe。
- 不由 Agent 自动做 v0.3 发布决定（F-024 人工 packet 决策）。

## Review points（reviewer：max）

1. Dashboard 写边界：权威写入保持 CLI + Markdown + dry-run/`--apply`；Web mutation 必须另行批准；`/llm` 本地配置端点是唯一例外
2. Product IA v2（Phase 6 §2/§3）作为 Phase 6 页面/查询/边界基线批准
3. 30-day Pilot 范围固定（§10），Pilot 中途不得无审批扩 Universe
4. v0.3 Release Gate：§11 checklist 机器可验证（F-023）+ 人工 release packet（F-024）+ tag 仅全 Gate 后（F-025）
5. 规模化触发条件（§4）：PostgreSQL/图/向量仅按实测瓶颈触发，不主动迁移
6. 备份/安全/许可 Gate（§6–8）：RTO/RPO、secrets 治理、license audit 纳入 Phase 6 验收

## Implementation record

- Changed files：本文件（proposed → approved 待 max 拍板）；生效后由 WP-600（F-001~003）落地 IA/read model/Industry Home
- Test result：not run（治理边界批准，无代码变更）
- Validation result：`research-os validate` 0 errors / 0 warnings（无对象变更）
- Effective date：待批准（批准即生效；WP-600 起实施）

## 参考

- `07_Phase_6_Productization_and_Scale.md` §1–§12
- RCP-v03-009（Recommendation 边界先例）、RCP-v03-007（Analysis Mode 先例）
- 决策日志 D9（`09_Master_Backlog.md` §13.1，RCP-v03-010 → Wave 6 排期）
