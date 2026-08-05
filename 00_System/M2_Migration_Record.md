# M2 Schema Migration Record

日期：2026-07-29  
批准：`RCP-20260729-003`

| Migration ID | Changed objects | Field | Value | Body hash |
|---|---:|---|---|---|
| MIG-20260729-001-schema-version | 49 | `schema_version` | `1` | 49/49 unchanged |
| MIG-20260729-002-project-scope | 49 | `project_ids` | `[PRJ-001]` | 49/49 unchanged |

执行约束：

- Migration Framework 先 plan，后 apply。
- 每个 change 记录 before/after file SHA-256。
- apply 生成本地 backup files 与 manifest；backup store 由 `.gitignore` 排除，
  原版本同时可由 Git commit `c01ed3e` 恢复。
- 两次 migration apply 均写入 49 个对象、49 个备份和一个 manifest。
- 迁移后 formal Schema 56/56，validation error 0，index drift 0。
