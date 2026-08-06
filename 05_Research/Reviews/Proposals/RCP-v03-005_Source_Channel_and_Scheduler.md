# Rule Change Proposal RCP-v03-005

Proposal ID：RCP-v03-005

状态：proposed

创建日期：2026-08-06

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Schema、永久 ID、Agent 边界：

- Phase 2（`03_Phase_2_Intelligence_Ingestion.md`）Source Channel Schema + scheduler
- `00_System/Source_Policy.md` 采集边界（robots、许可、频率、付费墙）
- 新增 `source_channel` 对象类型（CHN-<slug>），补 RCP-v03-003 的 ID 占位
- Agent 边界：Agent 可创建 Channel 草稿，但 **Channel 必须 reviewed + `enabled: true`
  才可被 scheduler 调用**；Agent 不自动启用未审 Channel

## Observed problem

只记录可引用的失败、warning、返工或研究质量问题：

- **`source_channel` 类型未实现**（RCP-v03-003 仅 ID 占位）：Company 的
  `source_channel_ids` 字段存在但无对象可引用，59/59 Company 该字段空。来源
  核验只能退而用 evidence_ids，无法登记"该公司应从哪些渠道采集"。
- 无 Channel Registry：采集来源（SEC、SK hynix IR、TrendForce、arXiv 等）没有
  结构化登记，无法实现"按 Channel 定时发现"。
- 无调度与许可管控：若直接开发 scheduler，需先明确每个来源的 robots/许可/频率
  边界，否则违反 Source_Policy 采集约束。

## Evidence

- Metrics snapshot：`METRICS-20260806.json`（source coverage 39%，需规模化采集）
- Review：`03_Phase_2_Intelligence_Ingestion.md` §3（Channel schema 草案）、
  §7（采集约束）
- Affected object IDs：新建 `CHN-*` 对象；Company `source_channel_ids` 补引用
- Test or validation output：`research-os validate` 0 errors / 0 warnings；
  本 RCP 不创建对象，不影响 validation

## Proposed change

1. **Source Channel Schema（CHN-<slug>）落为正式对象**（Phase 2 §3 草案）：
   `channel_type: rss|web_page|github_release|arxiv|sec|journal|api|manual`、
   `allow_hosts`、`license_status`、`robots_checked_at`、`enabled`、
   `review_status` 等字段。
2. **reviewed + enabled 才可调度**：scheduler 只调用 `review_status: reviewed`
   且 `enabled: true` 的 Channel；未审 Channel 不采集。
3. **许可边界（Source_Policy 扩展）**：每个 Channel 记录 `license_status:
   reviewed|pending|restricted` + `license_notes`；`restricted` 不采集；采集前
   核验 robots；不绕过登录/付费墙。
4. **采集约束**：`rate_limit`、`max_candidates_per_run`、`schedule`、
   `timezone`；同 Channel 无重叠运行锁；失败重试有上限。
5. **Company 关联**：Company `source_channel_ids` 补引用其应采集的 Channel，
   供 coverage 指标使用。

## Impact and risks

- 新增 `CHN-*` 正式对象类型：需 OBJECT_PATTERNS、ID_PATTERNS、schema registry、
  validation 接入（同 Sector/Security 先例）。
- 需为既有手动来源（SEC、SK hynix IR 等）建立首批 Channel 并 reviewed。
- 调度器实现属 WP-231（launchd + Daily Brief），本 RCP 只定边界。

## 不做的事

- 不自动创建 Source/Event。
- 不绕过登录、付费墙、robots 或访问控制。
- 不抓取未配置来源。
- 不把 Candidate 摘要当 reviewed Fact 混排。
- 不引入分布式任务队列（单机 scheduler 足够时）。

## Review points（reviewer：max）

1. 首批 Channel 清单（SEC EDGAR / SK hynix IR / TrendForce / arXiv / GitHub 等）
   与各自许可/robots 状态。
2. `restricted` Channel 的处理（是否保留登记但不采集）。
3. 调度频率与每日候选上限的默认值（建议每 Channel 20/run）。
4. 是否同意"Channel reviewed 是采集前置条件"。

## 参考

- `03_Phase_2_Intelligence_Ingestion.md` §3/§7
- `00_System/Source_Policy.md`
- RCP-v03-003（`CHN-` 占位 ID 补全）
