# AI Research OS 协作与交接协议

## 目标

在增加主题、来源或研究者时，保证永久 ID、事实源、人工判断边界和审阅责任不被并行工作破坏。

## 单一事实源

- Markdown 研究对象是事实源。
- `08_Indexes`、JSONL 和 SQLite 是可重建派生物。
- 原始 Source 不覆盖。
- 同一永久 ID 只能对应一个文件。
- 派生数据库不接受直接研究写入。

## 项目注册

每个研究主题必须先进入 `05_Research/Project_Registry.md`，并指定：

- Project ID。
- Research question。
- Owner。
- Charter。
- Queue。
- Active Thesis。
- Current Report。
- Review cadence。
- Status。

未经注册的临时探索可以留在 Inbox，但不得生成 final Report。

## 工作包

适合并行的工作包：

- 注册一组明确 Source。
- 从指定 Source 提取 Event 草稿。
- 检查一组 Event 的来源映射。
- 更新单一公司画像草稿。
- 搜索单一 Thesis 的反面 Evidence。

不适合无人协调并行修改：

- 同一个 Thesis 的置信度。
- 同一个 Event 的 Facts 或 Thesis impact。
- Research Rules、Taxonomy 或 Metadata Schema。
- 同一篇 final Report。

## 交接要求

每次交接必须说明：

- 工作包范围。
- 已读取的规则和模板。
- 创建或修改的对象 ID。
- 使用的 Source ID。
- 尚未解决的冲突与 unknowns。
- validation、index 和测试结果。
- 是否需要人工决定。

交接模板：`07_Templates/Research_Handoff.md`。

## 冲突处理

1. 保留双方修改和证据，不静默选择一方。
2. 先判断是否为事实冲突、解释冲突或元数据冲突。
3. 事实冲突回到 Source。
4. 解释冲突同时写入 Alternative explanations。
5. Thesis 方向或置信度冲突进入人工 Review。
6. 规则冲突建立 Rule Change Proposal。

## 合并闸门

工作包完成前必须：

```bash
python3 09_Automation/research_os.py validate
python3 09_Automation/research_os.py index --check
python3 -m unittest discover -s 09_Automation/tests -v
```

若对象发生变化，应先执行 `index --apply` 再检查。pending 对象不得因为合并方便而自动批准。

