# 阶段 6 验收

## 当前结论

截至 2026-07-29，规模触发条件、Ontology、派生导出、影响查询和协作协议均已建立并完成迁移演练，阶段状态为 `completed`。

当前推荐模式仍为 `file-first`。这不是未完成数据库建设，而是依据 15 个 Event 与 20 个 Source 的真实规模，明确选择不提前启用生产数据库。

## 规模策略

- [x] 定义 file-first 持续条件。
- [x] 定义 SQLite 自动与人工触发条件。
- [x] 定义图数据库评估条件。
- [x] 明确 Markdown 是当前单一事实源。
- [x] 明确数据库和 JSONL 是可丢弃派生视图。
- [x] 当前评估结果为 File-first。

## Ontology

- [x] 定义 Source、Event、Thesis、Company、Report 五类节点。
- [x] 定义 12 类有方向关系。
- [x] 保留 supporting、contradicting、contextual 的语义差异。
- [x] Event Thesis impact 表与 `thesis_links` 自动一致性校验。
- [x] 每条导出边的 source 和 target 均对应现有永久 ID。
- [x] 同一 source、relation、target 组合唯一。

## 规模化能力

- [x] JSONL 导出确定性生成。
- [x] SQLite 派生数据库可从 Markdown 重建。
- [x] SQLite 启用外键并完成 `foreign_key_check`。
- [x] 一至四跳影响查询可用。
- [x] 建立研究项目注册表。
- [x] 建立协作、冲突处理和合并闸门协议。
- [x] 建立 Research Project 和 Research Handoff 模板。

## 真实迁移演练

- [x] 导出 49 个节点。
- [x] 导出 147 条唯一关系。
- [x] JSONL manifest 与导出数量一致。
- [x] 临时 SQLite 包含 49 个节点和 147 条关系。
- [x] SQLite 外键错误为 0。
- [x] SQLite metadata 明确 `source_of_truth=Markdown`。
- [x] 临时数据库在验证后删除，项目中未留下生产数据库。
- [x] THS-002 影响查询同时显示支持、反面、报告和公司关系。

## 验证结果

- [x] 29 项单元与集成测试全部通过。
- [x] 真实仓库 validation error 为 0。
- [x] 真实仓库保留 18 条已知 Source 审核 warning。
- [x] 四个机器索引 drift 为 0。

## 后续触发

达到以下任一持续条件时，在 Monthly Review 建立正式存储升级提案：

- Event ≥ 500。
- Source ≥ 1,000。
- Active topic ≥ 10。
- 多研究者或多字段聚合成为日常需求。
- 每周多次需要三跳以上影响查询。

在触发前不创建常驻 SQLite 或图数据库。

