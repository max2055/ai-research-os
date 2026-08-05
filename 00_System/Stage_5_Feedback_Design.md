# 阶段 5：反馈与复盘设计

文档状态：`implemented`。以下设计验收项已由
`00_System/Stage_5_Acceptance.md` 的正式验收结果关闭。

## 目标

让 AI Research OS 不只积累对象，还能持续发现：

- 哪些研究对象堆积未审；
- 哪些 Thesis 缺少支持或反面 Evidence；
- 哪些来源没有进入 Event；
- 哪些判断长期未复盘；
- 哪些自动化规则造成错误、warning 或索引漂移；
- 哪些研究动作没有按期关闭；
- 哪些规则需要正式修改。

## 反馈闭环

```text
Repository state
→ Quality metrics
→ Immutable snapshot
→ Weekly / monthly review
→ Action items
→ Human-approved rule or workflow change
→ Next metrics snapshot
```

## 指标体系

### 1. 对象与积压

- 各对象类型总数。
- `pending`、`reviewed`、`rejected`、`superseded` 数量。
- 待审队列数量。

### 2. Source 转化

- Source 总数。
- 被至少一个 Event 引用的 Source 数量。
- Source→Event 转化率。
- Source grade 分布。
- reviewed Event 引用 pending Source 的数量。

### 3. Evidence 质量

- Event 总数及 reviewed 比例。
- Event 平均 Source 数。
- 没有 Thesis link 的 Event 数量。
- 审阅决定分布。

### 4. Thesis 健康度

- 每个 Thesis 的置信度。
- 支持与反面 Evidence 数量。
- 缺少支持或直接反面的 Thesis 数量。
- 超过复盘期限的 Thesis 数量。

### 5. Knowledge 与 Report

- 有 reviewed Evidence 的公司覆盖率。
- pending 公司画像数量。
- final/reviewed Report 数量。
- reviewed Report 的 Evidence 权威化违规数量。

### 6. 系统质量

- validation error 和 warning。
- index drift。
- 测试通过数量。
- 规则例外和未关闭行动项。

## 复盘周期

### Weekly

- 审阅 pending Event。
- 检查 conflicting Evidence。
- 处理 Thesis 置信度建议。
- 更新研究队列。
- 记录 validation error、warning 和索引漂移。

### Monthly

- 评估 Source 质量和来源结构。
- 检查 Thesis 盲点、反证缺口和复盘日期。
- 检查公司画像与报告是否过时。
- 评估自动化误报、漏报和人工返工。
- 通过正式变更记录修改规则。

## 快照规则

- 快照文件使用 `METRICS-YYYYMMDD.json`。
- 同一天的快照不可静默覆盖。
- 快照只记录可从仓库重算的事实。
- 人工解释写入 Review，不写入指标 JSON。
- 比较两个快照时必须保留指标定义版本。

## 规则变更

Research Rules、Source Policy、Taxonomy、Metadata Schema 和 Agent 边界的修改必须：

1. 建立变更提案。
2. 写明观察到的问题和证据。
3. 说明受影响对象及迁移方案。
4. 由研究者批准。
5. 写入规则变更日志。
6. 重新运行测试和仓库校验。

## 阶段 5 验收标准

- [x] 质量指标可以从仓库自动计算。
- [x] 指标覆盖对象积压、来源转化、Evidence、Thesis、Report 和系统健康。
- [x] 指标快照默认只读且拒绝覆盖。
- [x] 建立 Weekly、Monthly 和 Rule Change 模板。
- [x] 建立规则变更日志和未关闭行动项机制。
- [x] 生成首个指标基线。
- [x] 完成首次月度复盘并设置下一次复盘日期。
- [x] 复盘结论明确区分系统事实、解释和行动。
- [x] 阶段 5 自动化通过测试和真实仓库验证。
