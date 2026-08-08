# C-020 Phase 3 验收与恢复记录

状态：`passed`
日期：2026-08-08
工作包：C-020（`04_Phase_3_Impact_Engine.md` §12 回滚 / §7 验收）
前置：C-018 Gate APPROVED（`99a5b24`）、多跳激活（`1be5ffe`）

## 验收范围（Phase 3 §7 C-020）

export / rebuild / rollback 通过。

## 验收记录

| 项 | 验证 | 结果 |
|---|---|---|
| 对象可校验 | `research-os validate` | 0 error / 0 warning（16 个 IMP-* 全部通过 schema）|
| 索引可重建（C-013） | `research-os index --apply` → Impact_Index.md + 项目级 | 9 canonical indexes 重建，无 drift |
| 多跳激活（C-006） | `expand_impact_paths` 默认 max_depth=3，50k 边 0.02s | 通过（C-019 benchmark）|
| 50k 边性能（C-019） | `test_impact_benchmark` | 333 paths / maxdepth 3 / 0.02s |
| rollback（§12） | Impact 为权威 Markdown + git 版本化；可 disable 多跳（max_depth=1）；误生成 reject/supersede 不物理删除 | 通过 |
| export | Impact_Index.md + SQLite/JSONL ontology 导出（WP-104 先例）| 通过 |

## C-019 benchmark 发现并修复的 bug

`expand_impact_paths` 的 `frontier = paths` 别名了增长中的列表，BFS 会迭代到新 append 的路径，超过 max_depth 无限展开——稀疏图靠节点耗尽侥幸终止，稠密/环图爆炸（50k 边 >120s 卡死）。修复 `frontier = list(paths)` 后 0.02s 完成。这是 C-019 性能门真实捕获的问题。

## 回滚说明（Phase 3 §12）

- Impact Assertion 是新增对象，不反向修改 Event/Company。
- 可禁用 path expansion（`max_depth=1`）只保留 reviewed direct assertion。
- 派生图可删除重建。
- 误生成对象用 reject/supersede，不物理删除。
- 真实 Gate 不通过时退回"人工 direct impact only"（C-018 已通过，未触发）。
