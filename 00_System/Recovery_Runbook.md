# AI Research OS 恢复手册

版本：v1.0  
生效日期：2026-07-29

## 1. 恢复目标

从 Git 中恢复 Markdown 事实源、规则、模板和自动化，并重新生成全部派生索引。Source 原始资产单独从加密备份恢复。

## 2. 备份边界

Git 跟踪：

- `00_System` 至 `09_Automation` 中的 Markdown、Python 和测试文件；
- `AGENTS.md`、`README.md`；
- 研究对象、审核记录、不可覆盖指标快照。

Git 默认不跟踪：

- Python cache、测试 cache；
- SQLite、临时导出和可重建派生数据库；
- `.env`、密钥和证书；
- `01_Inbox/_assets/` 中可能受许可或隐私约束的原始材料。

`01_Inbox/_assets/` 必须使用单独的加密备份。恢复后以 Source metadata 中的路径和 SHA-256 校验完整性。

## 3. 从 Git 恢复

```bash
git clone <PRIVATE_REPOSITORY_URL> AI-Research-OS
cd AI-Research-OS
python3 -m venv ../ai-research-os-venv
../ai-research-os-venv/bin/pip install -e ".[dev,ui]"
../ai-research-os-venv/bin/pytest --cov=research_os --cov-fail-under=80
../ai-research-os-venv/bin/research-os validate
../ai-research-os-venv/bin/research-os index --apply
../ai-research-os-venv/bin/research-os index --check
../ai-research-os-venv/bin/python -B 09_Automation/research_os.py validate
```

验收：

- 测试全部通过；
- validation error 为 0；
- index drift 为 0；
- 对象数量与最近一次 Metrics snapshot 或发布记录一致。
- `research-os ui` 可在 loopback 启动，删除 Home Dashboard 后 `index --apply`
  可重建。

## 4. 恢复 Source assets

1. 将加密备份恢复到 `01_Inbox/_assets/`。
2. 不覆盖已存在且 hash 不同的文件。
3. 运行 `research-os source verify-assets`，按 Source metadata、manifest 与实际
   bytes 的 SHA-256 核对路径和 hash。
4. 缺失资产必须保留 Source 记录并标为恢复异常，不得删除引用关系。

## 5. iCloud 与 Git 冲突处理

- 只在一个工作目录中执行写操作。
- Git 操作前等待 iCloud 同步完成。
- 出现 “conflicted copy” 时保留双方文件，比较 front matter、正文和 Git history 后人工合并。
- 不使用 `git reset --hard` 或批量覆盖解决 iCloud 冲突。
- 索引和数据库可以重建；研究对象与原始资产不可用派生物反向覆盖。

## 6. 定期恢复演练

- 每个正式版本执行一次干净 clone 演练。
- 每月验证 Source asset 备份可读取。
- 每季度抽样核对 Source 文件 hash。
- 演练结果写入 Monthly Review 或 Release Checklist。

## 7. 当前基线

- Repository mode: local private Git repository
- Default branch: `main`
- Remote: 尚未配置；配置远程时必须使用 private repository
- Baseline validation: 见首个 Git commit 及 M0 验收记录
