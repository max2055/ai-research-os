# M3 Source Provenance Migration Record

日期：2026-07-29  
批准：`RCP-20260729-004`

| Migration ID | Changed Sources | 目的 | Body hash |
|---|---:|---|---|
| MIG-20260729-003-source-provenance | 20 | 增加 canonical URL、asset、hash、upstream、processing 与 date proposal 字段 | 20/20 unchanged |
| MIG-20260729-003b-source-null-fields | 20 | 修复初版 migration 未显式写入 absent/null 字段的问题 | 20/20 unchanged |
| MIG-20260729-003c-processing-error | 20 | 增加显式处理失败原因字段 | 20/20 unchanged |

迁移结果：

- 20 个既有 Source 均保持 `processing_status: registered`。
- canonical URL 仅由既有 HTTP(S) URL 规范化得到。
- 没有下载既有链接，没有伪造 raw asset、hash、采集时间或发布日期。
- `asset_paths`、`upstream_source_ids` 初始为空；未知值保持显式 null。
- 三次 migration 均使用 plan/apply、原子事务、本地 ignored backup 与 manifest。
- 最终 20/20 Source 人工正文 hash 相对 M2 commit `0c51d9a` 不变。

缺陷记录：

初版 migration 暴露 `MarkdownDocument.set_metadata` 对“字段不存在”和“字段值为
null”判断相同的问题，导致显式 null 字段未写出。实现已改为先判断 key 是否存在，
并加入 `test_source_migration_writes_explicit_null_fields` 回归测试；修复未修改正文。
