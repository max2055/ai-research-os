# Codex 自动化运行手册

以下命令假设已按 `README.md` 安装并激活产品虚拟环境。

## 每次研究开始前

```bash
python3 09_Automation/research_os.py status
python3 09_Automation/research_os.py validate
python3 09_Automation/research_os.py index --check
```

先处理 validation error；warning 必须可解释，但不必通过自动改状态来消除。

## 注册 Source

1. 可用 `source discover rss|github|arxiv|sec` 在显式 allowlist/query 中生成
   有上限的候选清单；此步骤只读，不自动注册。
2. 对明确选定的 URL 或本地文件运行 `source add` dry-run，检查 canonical URL、
   hash、日期 proposal、ID、元数据和资产路径。
3. 明确批准后使用 `--apply`，原子保存 Source、raw bytes 与 manifest。
4. 运行 `source process --id <SRC-ID> --apply` 生成可复核提取文本。
5. 如有日期 proposal，由研究者用 `source confirm-date` 明确确认。
6. 补全 Source summary、Relevant sections 和 Reliability notes。
7. 运行 `source verify-assets` 和仓库校验。

`new-source` 仅保留为不抓取资产的兼容入口；新材料优先走 `source add`。

## 提取 Event

1. 使用 `prompts/source_to_event.md` 处理明确选定且已 processed 的 Source。
2. 检查是否与现有 Event 重复。
3. 按 `Event_Draft_Spec.json` 为每个 Fact 提供 exact quote，运行
   `workflow event --spec <file>` 生成带行号与 hash 的 dry-run。
4. 明确批准创建后使用 `--apply`。
5. `--apply` 会同步勾选 Source 的 Event extraction，但不会改变 Source 审核状态。
6. 保持 Event 为 pending，进入人工审阅。

## 维护 Thesis 和公司画像

- 自动化可以提出链接，但不能自动改变 Thesis 置信度。
- 只有 reviewed Evidence 才能用于权威 Thesis 和稳定公司画像。
- 支持证据与反面证据必须同时保留。
- 人工批准的置信度变化必须写入 Evidence IDs 和 Review history。

## 生成 Report

1. 使用 `prompts/report_synthesis.md` 选择 Thesis 和 Event。
2. `workflow report` 只接受 reviewed Event，并生成无 TODO 的
   `draft/pending` 综合稿。
3. Weekly Report 使用 metrics snapshot 只选择 baseline 后新增的 reviewed
   Event。
4. 人工审核后再修改 Report 状态并记录 reviewer、日期和决定。
5. 新版只有在人工 approve 时才原子 supersede 旧版。

## 每次研究结束后

```bash
python3 09_Automation/research_os.py index --apply
python3 09_Automation/research_os.py index --check
python3 09_Automation/research_os.py validate
python3 -m unittest discover -s 09_Automation/tests -v
```

也可由 OS scheduler 调用：

```bash
research-os jobs run refresh --project PRJ-001
```

每次运行都会记录 Job Run；`jobs list --status failed` 与 Dashboard Health
用于检查失败。调度器不得直接执行 Review Decision。

## 故障处理

- `REF001`：引用对象不存在，修正 ID 或先注册对象。
- `REV001`：reviewed Report 引用了未审核 Event，降回 pending 或完成人工审核。
- `REV002`：reviewed Thesis 引用了未审核 Event，不能权威化。
- `REV003`：Event 内具体主张已审核，但完整 Source 记录仍待 Source 级审核；这是治理积压，不会自动改变任何对象状态。
- `TAX001`：使用了未定义标签；不要让自动化直接修改 Taxonomy。
- Index drift：确认对象元数据正确后运行 `index --apply`。
- `MISSING/HASH_MISMATCH`：停止处理该 Source，从加密备份恢复或调查未授权改写。
- 网络、feed/API 解析或 PDF 提取失败：不得把失败候选写成已处理 Source；保留
  原始错误，并在修复访问或格式问题后显式重试。
