# 阶段 4：Codex 自动化设计

文档状态：`implemented`。以下设计验收项已由
`00_System/Stage_4_Acceptance.md` 的正式验收结果关闭。

## 目标

把阶段 3 已经由人工验证的研究闭环编码为可重复、可审计、默认安全的本地工作流：

```text
Source
→ Event draft
→ Thesis links
→ Company links
→ Indexes
→ Report draft
→ Human review
```

自动化负责降低整理和一致性维护成本，不替代研究者对事实解释、Thesis 置信度和最终报告的判断。

## 本阶段范围

### 1. 统一仓库校验

- 校验五类核心对象的 YAML front matter。
- 校验 ID 格式、唯一性和文件名一致性。
- 校验 Source、Event、Thesis、Company 和 Report 的跨对象引用。
- 校验 Event 与 Thesis 置信度范围。
- 校验 `review_status` 生命周期。
- 保证 reviewed Report 只引用 reviewed Event。
- 保证 reviewed Thesis 的支持与反面 Evidence 已审核。
- 校验 Taxonomy 标签和研究对象必要章节。

### 2. 确定性索引

- 从对象文件生成 Source、Event、Thesis 和 Company 索引。
- 支持只读 `--check`，检测索引漂移。
- 只有显式 `--apply` 才覆盖机器维护的索引。

### 3. 对象脚手架

- 从标准模板生成 Source 和 Event 草稿。
- 自动寻找当日下一个可用序号。
- 默认输出预览；显式 `--apply` 才创建文件。
- 新对象固定为 `review_status: pending`。

### 4. 报告草稿

- 仅基于明确选定的 Event 和 Thesis 生成 Report 骨架。
- reviewed 输出只能使用 reviewed Event。
- 自动输出必须保持 `draft/pending`，人工审核后才能权威化。

## 明确不做

- 不自动批准 Source、Event、Thesis 或 Report。
- 不自动改变 Thesis 置信度。
- 不自动修改 Taxonomy。
- 不覆盖原始材料或人工笔记。
- 不在本阶段引入数据库、知识图谱、多 Agent 或全网抓取。
- 不把公司宣传、预览功能或技术发布自动升级为商业采用事实。

## 命令设计

统一入口：

```bash
python3 09_Automation/research_os.py <command>
```

计划命令：

- `validate`：仓库全量校验。
- `index --check|--apply`：检查或更新索引。
- `new-source`：创建 Source 草稿。
- `new-event`：创建 Event 草稿。
- `new-report`：创建 Report 草稿。

## 安全原则

1. 默认只读。
2. 写操作必须显式使用 `--apply`。
3. 写入前必须完成目标解析和冲突检查。
4. 不修改已存在的永久 ID。
5. 不覆盖已存在文件。
6. 所有机器生成的研究对象均为 `pending`。
7. 校验失败时不继续下游写入。

## 阶段 4 验收标准

- [x] 一个命令可以校验整个仓库。
- [x] 校验器能发现缺失字段、重复 ID、悬空引用和非法审核状态。
- [x] reviewed Report 的 Evidence 权威化约束被自动验证。
- [x] 四类索引可以确定性重建并检测漂移。
- [x] Source、Event 和 Report 草稿可以安全生成。
- [x] 所有写入命令默认 dry-run，且不会覆盖现有文件。
- [x] 自动化有单元测试和真实仓库端到端测试。
- [x] 自动化规则与 `AGENTS.md`、Metadata Schema 和 Workflow 一致。
