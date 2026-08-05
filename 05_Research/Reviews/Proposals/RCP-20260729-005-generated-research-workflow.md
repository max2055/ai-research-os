# Rule Change Proposal

Proposal ID：RCP-20260729-005

状态：approved

创建日期：2026-07-29

提议人：Codex

## Target

- structured Source→Event draft contract
- citation anchors and Source independence groups
- reviewed Evidence→Report synthesis and incremental Weekly Report
- Report version/supersession lifecycle
- Company update proposal
- generated-draft validation and human review gate

## Observed problem

现有自动化只能创建带 TODO 的 Event/Report 骨架，不能机器验证 Fact 是否有原文
定位、Thesis link 是否一致、反方是否保留，也不能防止同一输入重复创建对象。

## Evidence

- Roadmap：`00_System/Productization_Roadmap_v1.md` M4-01～M4-10。
- M3 已提供 immutable raw asset、extracted text、hash 和 upstream Source graph。
- M2 已提供通用 Review Decision 与 pending/reviewed lifecycle。
- 当前 15 个 Event 和 1 个 Report 是人工形成的兼容基线。

## Proposed change

新生成 Event 可以增加：

```yaml
generation_method: structured|ai-assisted
generation_fingerprint:
citation_anchors:
  - fact_id:
    source_id:
    asset_path:
    locator:
    quote:
    quote_sha256:
source_independence_groups: []
```

新生成 Report 可以增加：

```yaml
version:
supersedes:
superseded_by:
generation_method: structured|ai-assisted
generation_fingerprint:
baseline_snapshot:
```

约束：

- 每个生成 Fact 必须精确匹配 processed text 中的 quote 和行号。
- Facts、Inferences、Research judgment 必须分区。
- Alternative explanations 与 Unknowns 缺失或含 TODO 时拒绝生成。
- Thesis metadata links 必须与 impact table 一致。
- upstream 相同的 Source 进入同一 independence group，不重复计证据。
- Report synthesis 只接受 reviewed Event，并保留所有 contradicting rows。
- 同 generation fingerprint 拒绝重复创建。
- 新 Report 被人工 approve 时，才在同一事务中 supersede 前一 reviewed/final
  Report；pending draft 不改变旧报告。
- Company proposal 只从 reviewed Event 生成，且不能直接修改 Company。
- 所有生成 Event/Report 均为 pending/draft；自动化不得 review/final。

## Alternatives considered

- 继续生成 TODO 骨架：拒绝；无法形成可重复、可验证产品工作流。
- 让模型直接写 Markdown：拒绝；难以稳定验证输入契约、引用和幂等性。
- 自动更新 Thesis confidence 或 Company：拒绝；违反人工判断边界。
- 在 Report draft 创建时立即 supersede 旧版：拒绝；未审核草稿不能替代权威版本。

## Risks

- Quote 存在但并不语义支持 Fact。
- 结构化 spec 可能由模型错误生成。
- 同一新闻稿转载可能仍缺少 upstream 标注。
- 自动综合可能压缩语境或夸大结论。

控制：

- anchor 只解决可定位性，不宣称语义准确；10-Source field packet 必须人工抽查。
- generated content 永远 pending。
- validator 检查 anchor、hash、行号、反面 Evidence、review 状态和 fingerprint。
- Source independence 结果在 Event/Report 正文中显式披露。

## Migration

新字段带兼容默认值；15 个既有 Event 和 1 个既有 Report 不迁移、不重写。

## Acceptance tests

- processed Source 可生成带 anchor 的 pending Event。
- 缺 quote、alternative、unknown 或 processed asset 时失败且不写文件。
- 重复输入被 fingerprint 拒绝。
- contradicting Event 在 Report 中不可静默省略。
- metrics snapshot 可选择增量 reviewed Events。
- approve 新 Report 时原子更新新旧版本；draft 阶段不更新旧版。
- Company proposal 拒绝 pending 或未关联 Event。
- CLI dry-run/apply 与直接 service 路径一致。

## Human decision

- Decision: approve
- Reviewer: max
- Date: 2026-07-29
- Reason: 用户已批准完整产品化路线；本提案落实 M4 且保留人审与 Thesis 判断边界。

## Implementation record

- Changed files: Event/Report Schema、workflow service、validation、Review
  supersession、metrics state、CLI、spec templates、prompts、runbook 与 tests。
- Migration: none；15 个既有 Event 和 1 个既有 Report 未重写。
- Test result: 80/80；83% coverage；Ruff 与 mypy strict 通过。
- Validation result: 56/56 formal Schema；0 error；18 个既有 REV003 warning；
  global/PRJ-001 index drift 0。
- Human field Gate: pending，0/10；见 `M4_Field_Review_Packet.md`。
- Effective date: 2026-07-29
