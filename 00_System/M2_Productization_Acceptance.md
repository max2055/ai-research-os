# M2 多项目与通用审核验收

验收日期：2026-07-29  
结论：`accepted`

## 1. 验收范围

覆盖 `Productization_Roadmap_v1.md` 的 M2-01 至 M2-08。Schema 与治理变更
由 `RCP-20260729-003` 批准。

## 2. 交付确认

| ID | 结果 | 交付 |
|---|---|---|
| M2-01 | PASS | PRJ-001 已迁移为 `05_Research/Projects/PRJ-001.md` 正式对象，可由 CLI list/status |
| M2-02 | PASS | 49 个核心对象增加 `schema_version: 1` 与 `project_ids: [PRJ-001]` |
| M2-03 | PASS | immutable Review Decision Schema、模板、索引和原子 apply |
| M2-04 | PASS | Review Queue 支持 project/type/status 过滤 |
| M2-05 | PASS | 同一审核服务覆盖 Source、Event、Thesis、Company、Report |
| M2-06 | PASS | 六项既有 Action 无损迁移；支持 project/owner/status/overdue 查询与有证据关闭 |
| M2-07 | PASS | status、metrics 与七类 index 支持 Project 作用域 |
| M2-08 | PASS | Stage 3 helper 保留解析兼容，apply 转接通用 Review 服务 |

## 3. 数据迁移验证

- `MIG-20260729-001-schema-version`：49 changes。
- `MIG-20260729-002-project-scope`：49 changes。
- 两次 migration 均通过 plan/apply，备份与 manifest 位于本地 ignored backup store。
- 49/49 人工正文 hash 在迁移前后完全一致。
- 49/49 文件均存在 `schema_version: 1` 和 `project_ids: [PRJ-001]`。
- 没有改变 Review history、Thesis confidence、事实、推断或研究判断。

## 4. 多项目 Gate

隔离仓库的真实 subprocess 测试使用 CLI 创建 PRJ-002，并完成：

```text
Project
→ Source
→ Event
→ Review Decision
→ Action
→ Project Metrics
→ Report
```

同一测试确认：

- PRJ-001 与 PRJ-002 可分别查询。
- PRJ-002 对象不会进入 PRJ-001 作用域。
- 跨项目 Source 使用两个 `project_ids` 复用，仓库中只有一个永久 Source ID。
- 真实第二研究主题仍由 M6 选择；M2 不创建无章程的权威研究项目。

## 5. 质量结果

- tests：56/56。
- coverage：81.97%，高于 80% Gate。
- Ruff：通过。
- mypy strict：39 个 source files 通过。
- formal Schema：56/56（49 核心对象、1 Project、6 Action）。
- validation：0 error、18 个已解释 `REV003` warning。
- global index drift：0。
- PRJ-001 index drift：0。
- `research-os doctor`：全部检查通过。

## 6. 人工审核边界

- 仓库没有因 M2 自动新增真实 Review Decision；现有权威状态未被重新裁决。
- CLI `review apply` 必须显式提供 target、decision、reviewer 和 apply。
- `edit`/`reject` 必须提供 notes。
- reviewed Thesis/Report 仍只能引用 reviewed Evidence。
- Review 创建与目标状态更新使用同一文件事务。

## 7. Gate 决策

M2 Gate 通过。后续开发进入 M3 Source 采集、原文归档与溯源。
