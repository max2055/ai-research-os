# Rule Change Proposal RCP-v03-011

Proposal ID：RCP-v03-011

状态：approved（2026-08-12，reviewer：max）

创建日期：2026-08-12

提议人：max（草稿由 Agent 根据产品方向决定整理）

## Target

受影响的产品、自动化和人工审核边界：

- 网站作为唯一用户产品界面；
- 权威研究对象的 Web 创建、编辑、审核和批准流程；
- CLI 用户产品面的退役与内部兼容层迁移；
- Dashboard 安全、审计、预览、提交、冲突检测和回滚要求；
- `RCP-v03-010` 与 `RCP-20260729-006` 中只读 Web / CLI 权威写入条款。

## Observed problem

- 已批准的 `RCP-v03-010` 把 Dashboard 固定为 GET-only，并把权威写入留给
  CLI + Markdown。这与“项目所有用户功能通过网站实现、取消 CLI 产品入口”的最新
  产品决定直接冲突。
- 当前网站只有查询页面和 3 个 LLM 本地配置 POST，尚不能完成 Candidate triage、
  Source/Event/Impact/Forecast/Recommendation 审核、Thesis 变更、备份恢复或发布检查
  等完整工作流。立即删除 CLI 会破坏现有调度、备份、恢复和工程诊断能力。
- “入口改为网站”不能被解释为“自动任务获得人工权限”。研究对象审批、Thesis 结论与
  confidence 仍必须遵守现有研究规则和具名人工审核边界。

## Evidence

- Product decision：max 于 2026-08-12 明确“该项目所有功能将通过网站实现，取消 CLI”，
  并批准本 RCP 草案。
- Current implementation：`00_System/Dashboard_Design_v2.md` 记录现有非 GET 路由仅为
  `/llm/config`、`/llm/models`、`/llm/test`；当前研究写入尚无 Web parity。
- Conflicting rule：`RCP-v03-010` Proposed change §1、`不做的事` §1 和 Review point §1
  要求 Dashboard GET-only、权威写入走 CLI。
- Release state：F-023 当前 16/21；本治理决定不伪造 Pilot、自然 Resolution、cadence、
  Known Limitations 阅读确认或 F-024 发布批准。

## Proposed change

1. **唯一用户界面**：网站是 AI Research OS 唯一面向研究者的产品界面。查询、创建、
   修改、审核、批准、运行、监控、备份、恢复和发布检查必须最终在网站完成；用户文档
   不再把 CLI 作为正常产品操作入口。
2. **事实源不变**：Markdown 继续是权威研究事实源，Source assets 保持不可覆盖，
   Candidate SQLite 继续是 operational store。Web 必须调用现有领域 service，不得建立
   浏览器数据库、隐藏副本或绕开对象 validation 的第二事实源。
3. **Web 写入合同**：每个权威写入流程必须具备服务器端 validation、变更预览、显式确认、
   具名 actor、时间戳、目标 ID、前后版本或 diff、并发冲突检测、原子提交、审计记录和
   可验证回滚。对等继承现有 dry-run/`--apply` 的安全语义，但不要求在 UI 暴露 CLI 术语。
4. **人工权限不变**：自动任务可以发现、提取、评分、生成 pending 草稿、维护 operational
   状态和派生索引；不得批准 Source、Event、Impact Assertion、Analysis Run、Forecast、
   Resolution、Valuation、Recommendation、Review 或其他研究对象，不得改变 Thesis
   结论或 confidence。批准动作必须由网站中的具名人工明确提交，不能由 scheduler、Agent、
   模型输出、批处理或默认选项代行。
5. **安全边界**：当前部署继续 local-first、single-user、loopback-only。Web mutation 必须
   使用明确的非 GET 方法，并覆盖 CSRF/Origin、防重复提交、输入验证、path traversal、
   secret redaction、prompt injection、权限边界和事务失败测试。远程或多用户部署仍需独立
   的身份认证、授权与部署 RCP。
6. **CLI 退役语义**：CLI 自本 RCP 生效起退出用户产品面，不再新增用户专属 CLI 工作流。
   现有命令可在迁移期作为内部兼容、scheduler、诊断、测试和 disaster-recovery adapter
   保留，但不得成为网站缺失功能的长期产品替代。内部自动化应优先调用 service/API，而非
   解析人类 CLI 输出。
7. **分阶段迁移**：先建立共享 Web mutation 与审计合同，再按 Candidate → Evidence →
   Impact/Analysis → Forecast/Decision → Operations/Backup/Recovery/Release 的顺序补齐
   Web parity；每批迁移通过验收后，从用户文档移除对应 CLI 操作。CLI 代码仅在全部 parity、
   scheduler/service 改接和 recovery rehearsal 通过后删除。
8. **发布状态独立**：本 RCP 只批准产品方向与迁移合同，不把尚未实现的 Web 写入描述为
   已完成，不改变 F-023 当前 16/21，也不构成 Known Limitations 已读或 F-024 发布批准。

## Supersession scope

本 RCP 自批准日起取代：

- `RCP-v03-010` Proposed change §1、`不做的事` §1、Review point §1 及相关理由中的
  “Dashboard GET-only / 权威写入走 CLI / Web mutation 另行批准”；
- `RCP-20260729-006` 中把 HTMX 和 Dashboard 永久限制为只读产品面的条款；
- 当前规划和运行文档中把 CLI 描述为用户权威写入入口的现行表述。

历史 RCP、验收记录与 release evidence 保留原文，继续证明其当时状态。RCP-v03-010 的
IA、Pilot、Release Gate、规模化、备份、安全、许可和成本条款不受影响。

## Alternatives considered

1. **维持只读网站 + CLI 写入**：审计边界已实现，但不符合唯一 Web 产品界面的决定。
2. **立即删除所有 CLI 代码**：表面上最快，但当前网站无功能对等，会破坏 scheduler、备份、
   恢复、诊断和发布 Gate，因此拒绝。
3. **Web 直接编辑文件且不复用 service**：实现简单，但会绕过 validation、事务与审计，
   形成第二套写入语义，因此拒绝。

## Risks

- Web mutation 扩大攻击面。缓解：保持 loopback，逐流程 threat model 与负向测试，敏感操作
  显式确认并记录审计。
- Web 与内部 adapter 行为漂移。缓解：共用领域 service 和同一 validation，建立 service-level
  contract tests，不复制业务规则。
- 迁移期双入口造成不一致。缓解：CLI 标记 internal compatibility；同一行为只有一个 service
  owner；每批 parity 后移除对应用户文档入口。
- 把人工点击误当自动批准。缓解：批准提交必须携带具名 actor、显式 decision 和目标版本；
  background job token 不具备审批能力。
- 过早删除恢复工具造成数据风险。缓解：CLI 删除必须晚于 Web recovery parity 和一次完整
  disposable recovery rehearsal。

## Migration

1. M-WEB-0：同步治理、路线图、Known Limitations 和文档契约；现状仍为 Web parity 未完成。
2. M-WEB-1：实现统一 mutation preview/commit、actor、audit、optimistic concurrency 和
   rollback 基础设施。
3. M-WEB-2：迁移日常研究流，包括 Candidate、Source/Event、Review、Impact 与 Analysis。
4. M-WEB-3：迁移 Forecast/Resolution/Valuation/Recommendation/Thesis 人工决策流。
5. M-WEB-4：迁移 Operations、Channel、scheduler、backup、restore、validation、index 和
   release check；完成 recovery rehearsal。
6. M-WEB-5：确认用户文档无 CLI 依赖、后台任务不解析 CLI 输出、Web parity matrix 全通过后，
   删除产品 CLI entry point；必要的非交互内部 adapter 另行命名并限制权限。

## Acceptance tests

- 网站覆盖当前用户 Runbook 的全部日常、每周、每月、审核、运维、备份、恢复和发布检查流程。
- 权威写入均有 preview、explicit confirm、named actor、target version、audit 和 rollback evidence。
- Web 与内部 service 对同一输入产生一致 validation、diff 和结果；失败不产生半写状态。
- 自动任务和 Agent 无审批 capability；负向测试证明其不能批准对象或改变 Thesis confidence。
- Web security 覆盖 CSRF/Origin、重复提交、输入/路径、secret、prompt injection 和并发冲突。
- scheduler、backup、restore 与 release evaluation 不依赖解析用户 CLI 输出。
- 一次 disposable recovery rehearsal 可完全从网站发起并在网站核验结果。
- 用户文档与导航不要求执行 CLI；CLI removal 后完整 repository Gate 通过。

## Human decision

- Decision：批准（accept RCP-v03-011 as drafted）
- Reviewer：max
- Date：2026-08-12
- Reason：产品所有功能统一通过网站实现，取消 CLI 用户产品面；保留人工研究审批边界，
  并以有验收条件的迁移避免破坏现有调度与恢复能力。

## Implementation record

- Governance baseline：本 RCP、Rule Change Log、当前 v0.3 roadmap/backlog、Phase 6、
  Dashboard Design v2、README、User Runbook 和 Known Limitations 已同步 Web-only 决定。
- F-026（2026-08-12）：Candidate dismiss 已实现 Web detail → preview → dedicated confirm
  → atomic commit → `303` result；fixed local actor、session CSRF、10-minute signed token、
  one-use nonce、target-version conflict、replay/expiry/restart protection 与 redacted audit
  已落地。Candidate schema v3 同一 transaction 写 Candidate、action 和 committed audit，
  v3→v2 rollback 保留 Candidate/action 数据。
- Verification：当前 quality/security baseline commit `6337ccda9b2087b5a58c25cffc14304002f47647`；
  non-local suite 755 passed / 1 skipped，branch coverage 80.66%，Ruff/mypy/compileall、strict
  validation、index/doctor、10-route GET smoke、disposable mutation smoke、schema v3 recovery
  与 10,000-row p95 1.090937s benchmark 均通过。F-023 保持 16/21、5 个既有 blocker，
  未产生研究审批、Thesis confidence 或发布状态变化。
- Effective date：2026-08-12；产品方向与“不新增用户 CLI”立即生效，CLI 物理删除以 Web
  parity 和 recovery Gate 为前置。
