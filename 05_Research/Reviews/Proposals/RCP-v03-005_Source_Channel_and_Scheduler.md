# Rule Change Proposal RCP-v03-005

Proposal ID：RCP-v03-005

状态：approved（2026-08-06，reviewer：max）

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

## Review points（reviewer：max，2026-08-06，全部采纳默认）

1. ✅ 首批 6 个 Channel 按许可分级：SEC EDGAR / SK hynix IR / TrendForce 新闻稿
   （禁报告页）/ arXiv / GitHub Releases / 各公司官方 IR 分站；每个 Channel
   记录 license_status + robots_checked_at
2. ✅ `restricted` Channel 保留登记（status=restricted, enabled=false）但不采集，
   作为许可治理审计痕迹
3. ✅ 调度频率默认：SEC/IR/公司分站每 6h，arXiv 每日 1 次，GitHub 每日 2 次；
   每 Channel 每 run 上限 20；溢出靠 novelty/quality 评分截断，不提高硬上限
4. ✅ Channel reviewed 是采集前置条件（scheduler 只调 reviewed + enabled: true）

- Decision：批准（accept RCP-v03-005 as drafted，4 项人审点全部采纳默认）
- Reviewer：max
- Date：2026-08-06
- Reason：与 Phase 2 §3/§7 草案、Source_Policy 采集边界一致；补全 RCP-v03-003
  的 `CHN-` 占位 ID；"reviewed 才采集"防"先抓再治理"。

## Implementation record

- Changed files：本文件（proposed → approved）；生效后由 WP-201 起落地
  source_channel schema + Channel Registry + 首批 Channel reviewed
- Test result：not run（本 RCP 为治理边界批准，无代码变更；测试在 WP-201 落地后运行）
- Validation result：`research-os validate` 0 errors / 0 warnings（批准前后一致，
  因无对象变更）
- Effective date：2026-08-06（批准即生效；WP-201 起实施）

## 参考

- `03_Phase_2_Intelligence_Ingestion.md` §3/§7
- `00_System/Source_Policy.md`
- RCP-v03-003（`CHN-` 占位 ID 补全）
