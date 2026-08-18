# Legacy launchd Rollback Artifact

状态：已退出生产，禁止与网站 Worker 并行运行。

本目录中的 plist、`run_daily.sh` 和历史日志仅用于保留 B-021 的实现与运行证据。
当前生产调度由 `python -m research_os.ui` 启动的网站进程托管，计划只在
`/operations/schedules` 管理，运行状态与审计只写入 `operations.db`。

## 强制边界

- 正常运行时，旧 LaunchAgent 必须保持 unloaded，且不得设置登录启动。
- 网站运行时绝不能加载旧 LaunchAgent，也不能直接执行 `run_daily.sh`。
- 不得把旧 Channel Markdown 的 `schedule`/`enabled` 字段重新作为运行权威。
- 不得删除 plist、脚本、历史 `JOB-*.md` 或 `launchd/logs/*`；它们是迁移前证据。
- 旧 scheduler 不认识 `operations.db` 的租约和队列，并行运行会造成重复发现、重复
  retention 与不完整审计。

## 仅限灾难回滚

只有在网站 Worker 无法恢复、用户明确批准回到预切换架构，并且已经选择了完整的
预切换快照时，才允许临时启用本目录内容。回滚必须按以下顺序执行：

1. 停止网站服务，并确认网站 Worker PID 已退出。
2. 保存当前 `operations.db`、Candidate DB、Source assets 和 durable receipt，禁止覆盖。
3. 在 disposable directory 恢复并验证预切换快照；确认旧 Job Markdown 与 Candidate DB
   属于同一恢复点。
4. 由 operator 审核 plist 中的绝对路径和环境，确认不会访问当前网站使用的数据目录。
5. 仅在隔离的回滚目录中加载旧 LaunchAgent，并记录批准人、时间、快照 ID 和原因。

旧命令仅供上述受控回滚使用：

```bash
plutil -lint 09_Automation/launchd/com.aioresearchos.discovery.plist
cp 09_Automation/launchd/com.aioresearchos.discovery.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.aioresearchos.discovery.plist
launchctl list | grep aioresearchos
```

退出回滚时先卸载旧调度，再恢复当前数据库集合，最后启动网站：

```bash
launchctl unload ~/Library/LaunchAgents/com.aioresearchos.discovery.plist
rm ~/Library/LaunchAgents/com.aioresearchos.discovery.plist
python -m research_os.ui
```

## 历史证据

- plist：`09_Automation/launchd/com.aioresearchos.discovery.plist`
- wrapper：`09_Automation/launchd/run_daily.sh`
- 历史日志：`09_Automation/launchd/logs/*`
- 历史 Job：`05_Research/Operations/Jobs/JOB-*.md`

这些文件不定义当前产品行为。当前故障处理、备份和恢复流程见
`00_System/Recovery_Runbook.md` 与网站 `/health`、`/operations/backups`。
