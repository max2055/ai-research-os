# Rule Change Proposal

Proposal ID：RCP-20260729-003

状态：approved

创建日期：2026-07-29

提议人：Codex

## Target

- `00_System/Metadata_Schema.md`
- 核心对象公共字段
- Project、Review Decision 与 Action 对象
- 项目作用域、通用审核和 Action 生命周期

## Observed problem

当前 Project Registry 和 Action Register 是 Markdown 表格，无法由统一 Schema、
生命周期和 CLI 安全管理。49 个核心对象没有项目作用域，PRJ-001 与未来项目无法
独立查询；Stage 3 审核逻辑也不能复用于 Source、Thesis、Company 和 Report。

## Evidence

- Roadmap: `00_System/Productization_Roadmap_v1.md` M2
- Project Registry: `05_Research/Project_Registry.md`
- Action Register: `05_Research/Reviews/Action_Register.md`
- Affected object IDs: 当前 49 个核心对象、PRJ-001、ACT-20260729-001 至 006
- Baseline: M1 49 tests、86.27% coverage、0 validation error、0 index drift

## Proposed change

1. 为核心对象增加 `schema_version: 1` 与 `project_ids: []`。
2. 将 PRJ-001 登记为正式 Project 对象。
3. 将现有六项 Action 无损迁移为正式 Action 对象。
4. 新增追加式 Review Decision 对象；审核 apply 必须创建 Review 记录并与目标
   状态更新在同一事务完成。
5. 项目过滤只改变派生查询，不复制或隐藏跨项目对象。
6. 旧 Registry、Action Register 和 Stage 3 helper 保留一个兼容周期，但由正式
   对象派生或转接，不再作为唯一事实源。

## Alternatives considered

- 继续使用表格：拒绝；无法可靠校验引用、生命周期和逾期状态。
- 每个项目复制目录与脚本：拒绝；会复制跨项目 Source 并造成状态漂移。
- 直接建立数据库：拒绝；当前规模未触发，Markdown 仍应为事实源。

## Risks

- 批量 front matter 写入产生无意义 diff。
- 项目过滤遗漏共享对象。
- 审核命令错误改变权威状态。
- 将现有表格迁移为对象时丢失原始措辞。

控制措施：

- 使用 Migration Framework dry-run/apply/rollback 和 Git 基线。
- round-trip writer 只增加字段，不改正文。
- Review apply 使用生命周期校验和单事务写入。
- 现有 Registry/Action 表保留为兼容索引并做 drift 检查。

## Migration

1. 添加 Project、Review、Action Schema 和对象路径。
2. dry-run 生成 49 个对象的 `schema_version`/`project_ids` 迁移清单。
3. apply 前确认 0 validation error 和 0 index drift。
4. 创建 PRJ-001 与六个 Action 对象。
5. 重建 Registry、Action Register 和派生索引。
6. 验证 PRJ-001 全局结果除新增作用域字段外无语义变化。

## Acceptance tests

- 49 个既有对象全部属于 PRJ-001，正文 hash 不变。
- PRJ-001 可由 CLI 查询。
- Review Queue 可按项目、类型和状态筛选。
- Review apply 对所有核心对象使用同一服务，失败时无半写入。
- Action 可查询 owner、project、status 和 overdue。
- PRJ-001 的 validate、metrics、index、ontology 结果保持受控。

## Human decision

- Decision: approve
- Reviewer: max
- Date: 2026-07-29
- Reason: 用户已批准完整产品化计划及实施；本变更是 M2 的明确范围，并保持 Markdown 事实源与人工审核边界。

## Implementation record

- Changed files: Schema、migration、49 个核心 front matter、Project/Review/Action services、CLI、templates、indexes、tests
- Test result: 56 tests passed；81.97% coverage；Ruff 和 mypy strict 通过
- Validation result: formal Schema 56/56；0 error；18 个已解释 warning；global/PRJ-001 drift 均为 0
- Effective date: 2026-07-29
