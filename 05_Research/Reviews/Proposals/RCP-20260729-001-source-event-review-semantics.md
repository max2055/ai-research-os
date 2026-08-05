# Rule Change Proposal

Proposal ID：RCP-20260729-001

状态：approved

创建日期：2026-07-29

提议人：Codex

## Target

受影响范围：

- `00_System/Research_Rules.md`
- `00_System/Source_Policy.md`
- `00_System/Workflow.md`
- Source Processing checklist
- `REV003` validation warning
- Status / Review Queue 展示语义

## Observed problem

系统中 15 个 reviewed Event 引用了 18 个 pending Source，产生 18 条 `REV003` warning。同时，这 18 个 Source 已经形成 Event，但正文中的 `Event extraction completed` 仍未勾选。

此前没有明确区分：

1. Source processing 是否完成；
2. Source 记录是否完成独立审核；
3. Event 中的具体事实和推断是否完成审核。

这导致已完成的处理动作、待完成的 Source 级审核和 Event 权威状态在 Status 与正文中容易被误读为同一件事。

## Evidence

- Metrics snapshot: `05_Research/Reviews/Snapshots/METRICS-20260729.json`
- Review: `05_Research/Reviews/Monthly/REV-20260729-M01-initial-system-review.md`
- Affected object IDs: 18 个被 reviewed Event 引用的 Source；15 个 reviewed Event
- Test or validation output: 变更前为 18 条 `REV003`；所有 Source 的 Processing checklist 均未勾选

## Proposed change

采用三层独立语义：

1. **Processing state** 记录机器或人工流程是否执行，例如是否已经提取 Event。它不代表内容获得批准。
2. **Source `review_status`** 记录 Source 作为完整来源记录是否经过人工核验，包括身份、发布信息、可访问位置、等级、摘要、限制和上游关系。
3. **Event `review_status`** 记录 Event 中列出的具体 Fact、Inference、Judgment、Source anchor 和 Thesis impact 是否经过人工审核。

规则结果：

- 从 Source 创建 Event 后，Source 的 `Event extraction completed` 必须同步为已完成。
- reviewed Event 可以临时引用 pending Source，因为 Event 审核包含对“本 Event 所使用片段和主张”的范围内核对；这不会把整个 Source 记录自动批准为 reviewed。
- 此状态继续产生 `REV003` warning，表示 Source 级治理债务，而不是 Event 权威化失败。
- final/reviewed Report 可以使用 reviewed Event；若底层 Source 级审核仍未完成，报告应披露该治理缺口。
- Source 只能由明确的人工作出 reviewed/rejected 决定；处理完成或被 Event 引用都不能自动批准 Source。

## Alternatives considered

1. **自动把所有被 reviewed Event 使用的 Source 标为 reviewed。** 拒绝，因为这会把 Event 的范围内审核扩大为对整个 Source 记录的无条件批准。
2. **禁止 reviewed Event 引用 pending Source。** 暂不采用，因为会使现有研究闭环失效，而且 Source 级目录治理与具体 Event 主张审核并非同一工作。
3. **删除 `REV003`。** 拒绝，因为 Source 级审核积压仍应持续可见。

## Risks

- 研究者可能把 warning 当作可永久忽略的状态。
- Event 范围内审核若记录不足，可能无法证明具体核验了 Source 的哪些部分。
- final Report 可能忘记披露底层 Source review backlog。

控制措施：

- 保留 `REV003` 和 Metrics。
- Status 同时显示 Review 与 Processing。
- v0.2 的 Review Decision 对象记录审核范围。
- `ACT-20260729-001` 继续要求完成 18 个 Source 的独立审核。

## Migration

1. 将已被 Event 引用的 18 个 Source 标记为 `Event extraction completed`。
2. 不修改任何 Source 的 `review_status`。
3. 不修改 Event、Thesis 或 Report 的研究结论和置信度。
4. 更新 final Report 对 Source review backlog 的披露。
5. 增加自动校验，防止未来出现“已有 Event 但未标记提取完成”的漂移。

## Acceptance tests

- 被 Event 引用且 extraction 未完成的 Source 产生 `SRC007` error。
- `new-event --apply` 同步 Source extraction 状态，但不修改 Source `review_status`。
- Status 对 pending Source 分别显示 Review 与 Processing 状态。
- reviewed Event 引用 pending Source 仍产生且只产生解释明确的 `REV003` warning。
- final/reviewed Report 不包含与自身状态冲突的“待审核”表述。

## Human decision

- Decision: approve
- Reviewer: max
- Date: 2026-07-29
- Reason: 用户已批准按照产品化路线图实施全部 P0/P1 修复；本变更保留人工审核边界，并消除状态语义歧义。

## Implementation record

- Changed files: Research Rules、Source Policy、Workflow、Workflow Runbook、Report、18 个 Source、validator、Status、tests
- Test result: 33 tests passed
- Validation result: 0 errors；18 个预期 `REV003` governance warnings；0 index drift
- Effective date: 2026-07-29
