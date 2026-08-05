# 阶段 6：规模化与 Ontology 升级

## 原则

Markdown 文件继续作为当前事实源。数据库和图结构是可重建的派生视图，不得成为无法回写、无法审计的第二套事实。

当前规模：

- 20 个 Source。
- 15 个 Event。
- 5 个 Thesis。
- 8 个 Company。
- 1 个 Report。

当前规模明显低于数据库必要阈值，因此本阶段建立迁移能力，但不把生产事实源迁入数据库。

## 规模触发条件

### 保持 file-first

同时满足以下大部分条件时继续使用 Markdown：

- Event 少于 500。
- 活跃研究主题少于 10。
- 主要由单一研究者维护。
- 常见查询可以通过索引、全文搜索和一至两跳引用完成。
- 全量校验和索引重建仍能在日常工作流中快速完成。

### 启用 SQLite 派生索引

出现任一持续性条件时评估启用：

- Event 达到或超过 500。
- Source 达到或超过 1,000。
- 活跃研究主题达到或超过 10。
- 同一对象需要频繁进行多字段筛选、时间区间聚合和去重。
- 全量索引或常用查询的文件扫描成本明显影响日常研究。
- 两名以上研究者需要稳定共享查询结果。

SQLite 最初只作为从 Markdown 重建的派生数据库。任何写回必须通过对象文件和现有审核流程。

### 评估图数据库

只有同时满足以下条件才评估 Neo4j 或其他图存储：

- Ontology 关系类型已稳定经过至少两个复盘周期。
- 每周多次需要三跳以上影响查询。
- 需要解释“某技术变化通过哪些 Event、Company、Thesis 和 Report 传播”。
- SQLite 递归查询或内存图已成为明确瓶颈。
- 有可验证的同步、备份和回写策略。

对象数量本身不是引入图数据库的充分条件。

## Ontology v0.1

### 节点

- `source`
- `event`
- `thesis`
- `company`
- `report`

Technology 和 Product 目前继续作为 Taxonomy 或稳定 ID 属性；形成独立对象生命周期后再升级为节点。

### 关系

| From | Relation | To | 含义 |
|---|---|---|---|
| Source | `SUPPORTS_EVENT` | Event | Event 的事实可追溯到 Source |
| Event | `AFFECTS` | Company | Event 涉及或影响 Company |
| Event | `SUPPORTS` | Thesis | Event 支持 Thesis |
| Event | `CONTRADICTS` | Thesis | Event 构成 Thesis 反面证据 |
| Event | `CONTEXTUALIZES` | Thesis | Event 提供背景但不直接改变方向 |
| Event | `RELATES_TO` | Thesis | front matter 有链接但正文关系未解析 |
| Thesis | `CONCERNS` | Company | Thesis 适用于 Company |
| Company | `RELATED_TO` | Company | 显式记录的公司关系 |
| Company | `USES_SOURCE` | Source | 公司画像引用 Source |
| Company | `EVIDENCED_BY` | Event | 公司画像引用 Event |
| Report | `CITES` | Event | Report 使用 Event |
| Report | `SYNTHESIZES` | Thesis | Report 综合 Thesis |

### 关系约束

- 每条边的两端必须对应现有永久 ID。
- Event→Thesis 关系优先读取 Thesis impact 表。
- supporting、contradicting 和 contextual 不得合并为一个无方向“相关”关系。
- 同一 source、target、relation 组合必须唯一。
- 派生边不得反向修改对象。

## 导出与迁移

统一命令输出：

```bash
python3 09_Automation/research_os.py export --format jsonl
python3 09_Automation/research_os.py impact --id THS-002
python3 09_Automation/research_os.py scale
```

写入派生文件必须提供输出路径及 `--apply`：

```bash
python3 09_Automation/research_os.py export \
  --format sqlite \
  --output 09_Automation/derived/research-os.sqlite \
  --apply
```

派生数据库：

- 可以随时删除并从 Markdown 重建。
- 不进入人工审核对象生命周期。
- 不作为报告引用源。
- 不接受直接研究写入。

## 阶段 6 验收标准

- [ ] 明确定义 file-first、SQLite 和图数据库触发条件。
- [ ] 定义稳定节点、关系与约束。
- [ ] JSONL 导出确定且所有边可解析。
- [ ] SQLite 派生视图可以从同一导出重建。
- [ ] 影响查询可以展示对象的一至多跳关系。
- [ ] 当前规模评估给出明确模式建议。
- [ ] 迁移演练不改变 Markdown 事实源。
- [ ] 自动化测试与真实仓库验证通过。

