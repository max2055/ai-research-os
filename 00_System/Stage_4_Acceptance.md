# 阶段 4 验收

## 当前结论

截至 2026-07-29，阶段 4 的 Codex 自动化流水线已实现并通过验收，阶段状态为 `completed`。

## 自动化交付

- [x] 建立统一命令入口 `09_Automation/research_os.py`。
- [x] 建立仓库全量校验命令 `validate`。
- [x] 建立研究状态与待审队列命令 `status`。
- [x] 建立确定性索引命令 `index --check|--apply`。
- [x] 建立 Source 草稿脚手架 `new-source`。
- [x] 建立 Event 草稿脚手架 `new-event`。
- [x] 建立 Report 草稿脚手架 `new-report`。
- [x] 建立 Source→Event 和 Evidence→Report 两套 Codex 提示词。
- [x] 建立日常运行与故障处理手册。

## 安全验收

- [x] 所有写入命令默认 dry-run。
- [x] 新对象始终为 `pending`。
- [x] 永久 ID 自动避冲突。
- [x] 已存在文件拒绝覆盖。
- [x] 校验失败时不生成下游对象或索引。
- [x] 自动化不会批准对象、改变 Thesis 置信度或修改 Taxonomy。
- [x] reviewed Report 只能引用 reviewed Event。
- [x] reviewed Thesis 只能引用 reviewed Event。

## 验证结果

- [x] 23 项单元与集成测试全部通过。
- [x] 临时仓库完成 Source→Event→Report→Index→Validate 端到端测试。
- [x] 真实仓库识别 49 个核心对象（20 Source、15 Event、5 Thesis、8 Company、1 Report）。
- [x] 真实仓库 validation error 为 0。
- [x] 四个机器索引 drift 为 0。
- [x] Source、Event 和 Report 真实 dry-run 前后文件数均为 37。
- [x] Python 测试缓存已清理。

## 已知警告

真实仓库存在 18 条 `REV003` warning：已审核 Event 所引用的底层 Source 仍为 `pending`。这些 warning 不影响引用解析或阶段 3 已完成的 Event 人工审核，但会保留在状态面板，等待后续 Source 质量复盘；自动化不会自行把 Source 标为 reviewed。

## 主要入口

```bash
python3 09_Automation/research_os.py status
python3 09_Automation/research_os.py validate
python3 09_Automation/research_os.py index --check
python3 -m unittest discover -s 09_Automation/tests -v
```

运行手册：`09_Automation/Workflow_Runbook.md`

## 进入阶段 5 的条件

条件已满足。阶段 5 将围绕当前 status、warning、人工审阅结果和 Thesis 变化建立可量化的反馈、复盘与规则改进闭环。
